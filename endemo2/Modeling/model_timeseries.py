import numpy as np
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor


def _channel_attr(channel: str) -> str:
    return "timeseries_results" if channel == "UE" else "timeseries_results_fe"


def _enabled_channels(data) -> list[str]:
    channels = []
    settings = data.input_manager.general_settings
    if settings.UE_marker == 1:
        channels.append("UE")
    if settings.FE_marker == 1:
        channels.append("FE")
    return channels



def _normalize_token_list(values) -> list[str]:
    if values is None:
        return []
    out = []
    for v in values:
        s = str(v).strip().upper()
        if s:
            out.append(s)
    return out


def _unique_load_profiles(profiles):
    """Keep first occurrence order and remove exact duplicates."""
    if not profiles:
        return []

    unique = []
    seen = set()
    for profile in profiles:
        ue = tuple(sorted(_normalize_token_list(getattr(profile, "ue_types", []))))
        temp = tuple(sorted(_normalize_token_list(getattr(profile, "temp_levels", []))))
        all_sub = bool(getattr(profile, "all_subsectors", False))
        values = np.asarray(getattr(profile, "values", []), dtype=np.float64)
        signature = (ue, temp, all_sub, values.tobytes())
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(profile)
    return unique


def _calc_timeseries_tech_channel(tech, forecast_year_range, channel: str, allowed_heat_levels: list[str]):
    if tech.load_profile is None:
        return {}

    energy_source = tech.energy_ue if channel == "UE" else tech.energy_fe
    if energy_source is None or energy_source.empty:
        return {}

    profiles = {}

    def _tok(value):
        if value is None:
            return "default"
        try:
            if pd.isna(value):
                return "default"
        except Exception:
            pass
        s = str(value).strip()
        return s if s else "default"

    allowed_heat_set = {str(x).strip().upper() for x in (allowed_heat_levels or []) if str(x).strip()}

    for l_profile in _unique_load_profiles(tech.load_profile):
        calc_data = energy_source.copy()
        if calc_data.empty:
            continue

        ue_col = calc_data['UE_Type'].fillna("").astype(str).str.strip().str.upper()
        tl_col = calc_data['Temp_level'].fillna("").astype(str).str.strip().str.upper()

        # Never use HEAT/TOTAL in hourly allocation.
        calc_data = calc_data[~((ue_col == "HEAT") & (tl_col == "TOTAL"))]
        if calc_data.empty:
            continue

        ue_col = calc_data['UE_Type'].fillna("").astype(str).str.strip().str.upper()
        tl_col = calc_data['Temp_level'].fillna("").astype(str).str.strip().str.upper()

        profile_ue = _normalize_token_list(getattr(l_profile, 'ue_types', []))
        if profile_ue and 'DEFAULT' not in profile_ue:
            calc_data = calc_data[ue_col.isin(profile_ue)]
            if calc_data.empty:
                continue
            ue_col = calc_data['UE_Type'].fillna("").astype(str).str.strip().str.upper()
            tl_col = calc_data['Temp_level'].fillna("").astype(str).str.strip().str.upper()

        profile_tl = _normalize_token_list(getattr(l_profile, 'temp_levels', []))
        if profile_tl and 'DEFAULT' not in profile_tl:
            calc_data = calc_data[tl_col.isin(profile_tl)]
            if calc_data.empty:
                continue
        else:
            # temp_level=default -> use configured heat levels (without TOTAL) for HEAT rows.
            if allowed_heat_set:
                is_heat = ue_col == 'HEAT'
                keep_heat = tl_col.isin(allowed_heat_set)
                calc_data = calc_data[(~is_heat) | keep_heat]
                if calc_data.empty:
                    continue

        group_cols = ['Region', 'Sector', 'Subsector', 'Technology', 'Subtech', 'Drive', 'Temp_level', 'UE_Type']
        if channel == "FE":
            group_cols.append('FE_Type')
        year_columns = [str(y) for y in forecast_year_range]
        calc_data[year_columns] = calc_data[year_columns].apply(pd.to_numeric, errors="coerce")
        grouped = calc_data.groupby(group_cols, as_index=False)[year_columns].sum()
        if grouped.empty:
            continue

        components = grouped[group_cols].to_dict("records")
        energy_matrix = grouped[year_columns].to_numpy(dtype=float)

        for idx, comp in enumerate(components):
            if channel == "FE":
                profile_id = (
                    f"{_tok(comp.get('Sector'))}_{_tok(comp.get('Subsector'))}_{_tok(comp.get('Technology'))}_"
                    f"{_tok(comp.get('Subtech'))}_{_tok(comp.get('Drive'))}_{_tok(comp.get('FE_Type'))}_"
                    f"{_tok(comp.get('Temp_level'))}_{_tok(comp.get('UE_Type'))}"
                )
            else:
                profile_id = (
                    f"{_tok(comp.get('Sector'))}_{_tok(comp.get('Subsector'))}_{_tok(comp.get('Technology'))}_"
                    f"{_tok(comp.get('Subtech'))}_{_tok(comp.get('Drive'))}_{_tok(comp.get('Temp_level'))}_"
                    f"{_tok(comp.get('UE_Type'))}"
                )
            if profile_id not in profiles:
                profiles[profile_id] = {
                    'components': {
                        'Channel': channel,
                        'UE_Type': comp.get('UE_Type'),
                        'FE_Type': comp.get('FE_Type'),
                        'Temp_level': comp.get('Temp_level'),
                        'Region': comp.get('Region'),
                        'Sector': comp.get('Sector'),
                        'Subsector': comp.get('Subsector'),
                        'Technology': comp.get('Technology'),
                        'Subtech': comp.get('Subtech'),
                        'Drive': comp.get('Drive')
                    },
                    'contributors': {
                        'technologies': set(),
                        'subtechs': set(),
                        'drives': set()
                    },
                    'years': {}
                }
            tech_profile = profiles[profile_id]
            tech_profile['contributors']['technologies'].add(_tok(comp.get('Technology')))
            tech_profile['contributors']['subtechs'].add(_tok(comp.get('Subtech')))
            tech_profile['contributors']['drives'].add(_tok(comp.get('Drive')))

            for year_idx, year in enumerate(year_columns):
                energy_val = energy_matrix[idx, year_idx]
                if np.isnan(energy_val):
                    continue
                hourly_vals = l_profile.values * energy_val
                if year not in tech_profile['years']:
                    tech_profile['years'][year] = {
                        'hourly_values': hourly_vals,
                        'annual_energy': energy_val
                    }
                else:
                    tech_profile['years'][year]['hourly_values'] += hourly_vals
                    tech_profile['years'][year]['annual_energy'] += energy_val
    return profiles


def _calc_timeseries_tech(tech, forecast_year_range, channels: list[str], allowed_heat_levels: list[str]):
    tech.timeseries_results = {}
    tech.timeseries_results_fe = {}
    for channel in channels:
        channel_profiles = _calc_timeseries_tech_channel(tech, forecast_year_range, channel, allowed_heat_levels)
        setattr(tech, _channel_attr(channel), channel_profiles)


def _calc_timeseries_sub(subsector, forecast_year_range, channels: list[str], allowed_heat_levels: list[str]):
    subsector.timeseries_results = {"profiles": {}}
    subsector.timeseries_results_fe = {"profiles": {}}
    for tech in subsector.technologies:
        _calc_timeseries_tech(tech, forecast_year_range, channels, allowed_heat_levels)
        for channel in channels:
            tech_profiles = getattr(tech, _channel_attr(channel), {}) or {}
            if not tech_profiles:
                continue
            target = getattr(subsector, _channel_attr(channel))['profiles']
            for profile_id, tech_data in tech_profiles.items():
                if profile_id not in target:
                    target[profile_id] = {
                        'components': tech_data['components'],
                        'years': {},
                        'contributors': {
                            'technologies': set(),
                            'subtechs': set(),
                            'drives': set()
                        }
                    }
                subsector_profile = target[profile_id]
                subsector_profile['contributors']['technologies'].update(
                    tech_data['contributors']['technologies'])
                subsector_profile['contributors']['subtechs'].update(
                    tech_data['contributors']['subtechs'])
                subsector_profile['contributors']['drives'].update(
                    tech_data['contributors']['drives'])
                for year, year_data in tech_data['years'].items():
                    if year in subsector_profile['years']:
                        subsector_profile['years'][year]['hourly_values'] += year_data['hourly_values']
                        subsector_profile['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        subsector_profile['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }
    for channel in channels:
        target = getattr(subsector, _channel_attr(channel))['profiles']
        for profile in target.values():
            for key in profile['contributors']:
                profile['contributors'][key] = list(profile['contributors'][key])


def _calc_timeseries_sec(sector, forecast_year_range, channels: list[str], allowed_heat_levels: list[str]):
    sector.timeseries_results = {"profiles": {}}
    sector.timeseries_results_fe = {"profiles": {}}
    for subsector in sector.subsectors:
        _calc_timeseries_sub(subsector, forecast_year_range, channels, allowed_heat_levels)
        for channel in channels:
            subsector_profiles = getattr(subsector, _channel_attr(channel), {}).get('profiles', {})
            if not subsector_profiles:
                continue
            target = getattr(sector, _channel_attr(channel))['profiles']
            for profile_id, subsector_data in subsector_profiles.items():
                if profile_id not in target:
                    target[profile_id] = {
                        'components': subsector_data['components'],
                        'years': {},
                        'contributors': {
                            'subsectors': set(),
                            'technologies': set(),
                            'subtechs': set(),
                            'drives': set()
                        }
                    }
                sector_profile = target[profile_id]
                sector_profile['contributors']['subsectors'].add(subsector.name)
                sector_profile['contributors']['technologies'].update(
                    subsector_data['contributors']['technologies'])
                sector_profile['contributors']['subtechs'].update(
                    subsector_data['contributors']['subtechs'])
                sector_profile['contributors']['drives'].update(
                    subsector_data['contributors']['drives'])
                for year, year_data in subsector_data['years'].items():
                    if year in sector_profile['years']:
                        sector_profile['years'][year]['hourly_values'] += year_data['hourly_values']
                        sector_profile['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        sector_profile['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }
    for channel in channels:
        target = getattr(sector, _channel_attr(channel))['profiles']
        for profile in target.values():
            for key in profile['contributors']:
                profile['contributors'][key] = list(profile['contributors'][key])


def _calc_timeseries_reg(region, forecast_year_range, channels: list[str], allowed_heat_levels: list[str]):
    region.timeseries_results = {"profiles": {}}
    region.timeseries_results_fe = {"profiles": {}}
    for sector in region.sectors:
        _calc_timeseries_sec(sector, forecast_year_range, channels, allowed_heat_levels)
        for channel in channels:
            sector_profiles = getattr(sector, _channel_attr(channel), {}).get('profiles', {})
            if not sector_profiles:
                continue
            target = getattr(region, _channel_attr(channel))['profiles']
            for profile_id, sector_data in sector_profiles.items():
                if profile_id not in target:
                    target[profile_id] = {
                        'components': sector_data['components'],
                        'years': {},
                        'contributors': {
                            'sectors': set(),
                            'subsectors': set(),
                            'technologies': set(),
                            'subtechs': set(),
                            'drives': set()
                        }
                    }
                region_profile = target[profile_id]
                region_profile['contributors']['sectors'].add(sector.name)
                region_profile['contributors']['subsectors'].update(
                    sector_data['contributors']['subsectors'])
                region_profile['contributors']['technologies'].update(
                    sector_data['contributors']['technologies'])
                region_profile['contributors']['subtechs'].update(
                    sector_data['contributors']['subtechs'])
                region_profile['contributors']['drives'].update(
                    sector_data['contributors']['drives'])
                for year, year_data in sector_data['years'].items():
                    if year in region_profile['years']:
                        region_profile['years'][year]['hourly_values'] += year_data['hourly_values']
                        region_profile['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        region_profile['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }
    for channel in channels:
        target = getattr(region, _channel_attr(channel))['profiles']
        for profile in target.values():
            for level in profile['contributors']:
                profile['contributors'][level] = list(profile['contributors'][level])


def calculate_timeseries(data):
    """
    Calculate hourly time series for all regions, if timeseries forecast is enabled.
    """
    if data.input_manager.general_settings.timeseries_forecast == 0:
        print("Calculation Timeseries is not activated")
        return None

    channels = _enabled_channels(data)
    if not channels:
        print("Calculation Timeseries is not activated")
        return None

    forecast_year_range = [str(year) for year in data.input_manager.general_settings.forecast_year_range]
    raw_heat_levels = getattr(data.input_manager.general_settings, 'heat_levels', []) or []
    allowed_heat_levels = [
        str(level).strip().upper()
        for level in raw_heat_levels
        if str(level).strip() and str(level).strip().upper() != 'TOTAL'
    ]

    regions = list(data.regions)
    if not regions:
        return None
    max_workers = min(max(1, (os.cpu_count() or 1)), len(regions))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(lambda reg: _calc_timeseries_reg(reg, forecast_year_range, channels, allowed_heat_levels), regions))

