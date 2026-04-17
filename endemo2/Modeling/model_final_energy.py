import pandas as pd
import numpy as np
import logging
from endemo2.Input.loaders.common import select_rows_with_default

logger = logging.getLogger(__name__)


def _is_default_like(value):
    """Return True for default-like values used in hierarchy fallback."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    text = str(value).strip()
    return text == "" or text.lower() == "default"


def _norm_value(value):
    """Normalize values for stable exact comparisons."""
    if _is_default_like(value):
        return None
    return str(value).strip().casefold()


def _rank_matches(matches: pd.DataFrame, row, ordered_keys: list[str]) -> pd.DataFrame:
    """Rank candidate rows by specificity against row context (exact > default)."""
    if matches is None or matches.empty:
        return matches

    ranked = matches.copy()

    def _score_one(candidate):
        score = 0
        for key in ordered_keys:
            if key not in ranked.columns:
                continue
            cand = candidate.get(key)
            target = row.get(key)
            if _is_default_like(cand):
                continue
            if _norm_value(cand) == _norm_value(target):
                score += 1
        return score

    ranked["__spec_score"] = ranked.apply(_score_one, axis=1)
    ranked = ranked.sort_values(["__spec_score"], ascending=False).drop(columns=["__spec_score"])
    return ranked


def _best_match(matches: pd.DataFrame, row, ordered_keys: list[str]) -> pd.DataFrame:
    """Return exactly one best-ranked row (or empty DataFrame)."""
    if matches is None or matches.empty:
        return pd.DataFrame()
    ranked = _rank_matches(matches, row=row, ordered_keys=ordered_keys)
    return ranked.head(1).copy()


def _best_share_matches_per_fe(share_matches: pd.DataFrame, ue_row, rank_keys: list[str]) -> pd.DataFrame:
    """Keep one best share row per FE_Type after ranking."""
    if share_matches is None or share_matches.empty:
        return pd.DataFrame()
    if "FE_Type" not in share_matches.columns:
        return _best_match(share_matches, row=ue_row, ordered_keys=rank_keys)

    out = []
    for _, grp in share_matches.groupby("FE_Type", dropna=False):
        best = _best_match(grp, row=ue_row, ordered_keys=rank_keys)
        if not best.empty:
            out.append(best)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()

def _calc_fe_tech(tech, eff_forecast, share_forecast, forecast_year_range):
    tech.energy_fe = calc_fe_types(tech.energy_ue, eff_forecast, share_forecast, forecast_year_range)


def _calc_fe_subsector(subsector, eff_forecast, share_forecast, forecast_year_range):
    fe_energy = []
    for tech in subsector.technologies:
        _calc_fe_tech(tech, eff_forecast, share_forecast, forecast_year_range)
        if tech.energy_fe is not None and not tech.energy_fe.empty:
            fe_energy.append(tech.energy_fe)
    subsector.energy_fe = pd.concat(fe_energy, axis=0, ignore_index=True) if fe_energy else pd.DataFrame()


def _calc_fe_sector(sector, eff_forecast, share_forecast, forecast_year_range):
    fe_energy = []
    for subsector in sector.subsectors:
        _calc_fe_subsector(subsector, eff_forecast, share_forecast, forecast_year_range)
        if subsector.energy_fe is not None and not subsector.energy_fe.empty:
            fe_energy.append(subsector.energy_fe)
    sector.energy_fe = pd.concat(fe_energy, axis=0, ignore_index=True) if fe_energy else pd.DataFrame()


def _calc_fe_region(region, eff_forecast, share_forecast, forecast_year_range):
    fe_energy = []
    for sector in region.sectors:
        _calc_fe_sector(sector, eff_forecast, share_forecast, forecast_year_range)
        if sector.energy_fe is not None and not sector.energy_fe.empty:
            fe_energy.append(sector.energy_fe)
    region.energy_fe = pd.concat(fe_energy, axis=0, ignore_index=True) if fe_energy else pd.DataFrame()


def calculate_final_energy(data):
    """
    Calculate final energy for all regions, if FE calculation is enabled.

    This is part of the forecast/modeling pipeline and should be called
    after useful energy has been computed.
    """
    if data.input_manager.general_settings.FE_marker == 0:
        print("Calculation Final energy is not activated")
        return None
    forecast_year_range = [str(year) for year in data.input_manager.general_settings.forecast_year_range]
    var_ef, var_share = data.efficiency_data
    eff_forecast = var_ef.forecast
    eff_forecast.columns = eff_forecast.columns.astype(str)
    share_forecast = var_share.forecast
    share_forecast.columns = share_forecast.columns.astype(str)
    for region in data.regions:
        _calc_fe_region(region, eff_forecast, share_forecast, forecast_year_range)


def _build_fe_trace(ue_row, share_row, ef_row):
    """Build compact per-row trace text for final-energy rows."""
    base = str(ue_row.get("Trace", "")).strip()
    share_info = f"ShareFE={share_row.get('FE_Type')}"
    eff_info = f"EfficiencyFE={ef_row.get('FE_Type')}"
    parts = [p for p in [base, share_info, eff_info] if p]
    return " | ".join(parts)

def calc_fe_types(energy_ue, eff_forecast, share_forecast, forecast_year_range):

    """
    Calculate final energy by:
    1. Finding matching share records
    2. Finding matching efficiency records for each FE_Type
    3. For HEAT: build TOTAL strictly as sum of FE heat levels (Q-levels).
       If no heat levels exist for a group, emit HEAT/TOTAL as zeros.
    """
    keys = ['Region', 'Sector', 'Subsector', 'Technology', 'UE_Type',
            'Temp_level', 'Subtech', 'Drive']
    rank_keys_share = ['Region', 'Sector', 'Subsector', 'Technology', 'UE_Type', 'Temp_level', 'Subtech', 'Drive']
    rank_keys_eff = ['Region', 'Sector', 'Subsector', 'Technology', 'UE_Type', 'Temp_level', 'Subtech', 'Drive', 'FE_Type']
    year_cols = [str(y) for y in forecast_year_range]

    results = []
    # Target map for synthetic HEAT/TOTAL rows: one per group and FE_Type.
    # key=(Region,Sector,Subsector,Technology,Subtech,Drive) -> set(FE_Type)
    heat_total_targets = {}

    def _heat_group_key(row):
        return (
            row.get('Region'),
            row.get('Sector'),
            row.get('Subsector'),
            row.get('Technology'),
            row.get('Subtech') if not pd.isna(row.get('Subtech')) else 'default',
            row.get('Drive') if not pd.isna(row.get('Drive')) else 'default',
        )

    def _is_heat_total_like(row):
        ue_type = str(row.get('UE_Type', '')).strip().upper()
        if ue_type != 'HEAT':
            return False
        temp = row.get('Temp_level')
        if _is_default_like(temp):
            return True
        return str(temp).strip().upper() == 'TOTAL'

    for _, ue_row in energy_ue.iterrows():
        share_matches = get_matches(share_forecast, ue_row, keys)
        share_matches = _best_share_matches_per_fe(share_matches, ue_row=ue_row, rank_keys=rank_keys_share)
        if len(share_matches) == 0:
            continue

        # Record FE targets for HEAT groups so TOTAL can always be created.
        if str(ue_row.get('UE_Type', '')).strip().upper() == 'HEAT':
            gk = _heat_group_key(ue_row)
            fe_set = heat_total_targets.setdefault(gk, set())
            for _, sr in share_matches.iterrows():
                fe_t = sr.get('FE_Type')
                if not pd.isna(fe_t):
                    fe_set.add(fe_t)

        # HEAT/TOTAL is synthetic later (sum of FE heat levels) -> skip direct calculation here.
        if _is_heat_total_like(ue_row):
            continue

        for _, share_row in share_matches.iterrows():
            search_row = ue_row.copy()
            search_row['FE_Type'] = share_row['FE_Type']
            ef_match = get_matches(eff_forecast, search_row, keys + ['FE_Type'])
            ef_match = _best_match(ef_match, row=search_row, ordered_keys=rank_keys_eff)
            if len(ef_match) == 0:
                continue
            ef_row = ef_match.iloc[0]

            ue_years = pd.to_numeric(ue_row[year_cols], errors='coerce').astype(float)
            share_years = pd.to_numeric(share_row[year_cols], errors='coerce').astype(float).fillna(0.0)
            ef_years = pd.to_numeric(ef_row[year_cols], errors='coerce').astype(float)

            invalid_eff = ef_years.isna() | (ef_years <= 0)
            if invalid_eff.any():
                logger.warning(
                    "Invalid efficiency (<=0 or NaN) for %s/%s/%s/%s UE=%s FE=%s; setting FE to NaN for affected years.",
                    ue_row.get('Region'),
                    ue_row.get('Sector'),
                    ue_row.get('Subsector'),
                    ue_row.get('Technology'),
                    ue_row.get('UE_Type'),
                    share_row.get('FE_Type'),
                )
                ef_years = ef_years.mask(invalid_eff, np.nan)

            fe_values = ue_years.mul(share_years).div(ef_years)
            result = {
                **ue_row[keys].to_dict(),
                'FE_Type': share_row['FE_Type'],
                'Trace': _build_fe_trace(ue_row, share_row, ef_row),
                **fe_values.to_dict(),
            }
            results.append(result)

    base_df = pd.DataFrame(results)
    if base_df.empty and not heat_total_targets:
        return base_df

    # Keep only non-total rows from direct computation.
    if not base_df.empty:
        ue_col = base_df['UE_Type'].fillna('').astype(str).str.strip().str.upper()
        tl_col = base_df['Temp_level'].fillna('').astype(str).str.strip()
        total_like = (ue_col == 'HEAT') & (
            (tl_col.str.upper() == 'TOTAL') | (tl_col == '') | (tl_col.str.lower() == 'default')
        )
        base_df = base_df[~total_like].copy()

    # Aggregate FE heat levels to FE HEAT/TOTAL.
    heat_totals_df = pd.DataFrame()
    if not base_df.empty:
        ue_col = base_df['UE_Type'].fillna('').astype(str).str.strip().str.upper()
        tl_col = base_df['Temp_level'].fillna('').astype(str).str.strip()
        is_heat_level = (ue_col == 'HEAT') & (~(
            (tl_col.str.upper() == 'TOTAL') | (tl_col == '') | (tl_col.str.lower() == 'default')
        ))
        heat_levels_df = base_df[is_heat_level].copy()

        if not heat_levels_df.empty:
            agg_keys = ['Region', 'Sector', 'Subsector', 'Technology', 'Subtech', 'Drive', 'FE_Type']
            heat_totals_df = (
                heat_levels_df.groupby(agg_keys, dropna=False)[year_cols]
                .sum(min_count=1)
                .reset_index()
            )
            heat_totals_df[year_cols] = heat_totals_df[year_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)

    # Build synthetic HEAT/TOTAL rows for all target groups. If no level exists -> zeros.
    total_rows = []
    for gk, fe_types in heat_total_targets.items():
        region, sector, subsector, technology, subtech, drive = gk
        for fe_type in sorted(fe_types, key=lambda x: str(x)):
            vals = pd.Series(0.0, index=year_cols, dtype=float)
            if not heat_totals_df.empty:
                mask = (
                    (heat_totals_df['Region'] == region)
                    & (heat_totals_df['Sector'] == sector)
                    & (heat_totals_df['Subsector'] == subsector)
                    & (heat_totals_df['Technology'] == technology)
                    & (heat_totals_df['Subtech'] == subtech)
                    & (heat_totals_df['Drive'] == drive)
                    & (heat_totals_df['FE_Type'] == fe_type)
                )
                m = heat_totals_df[mask]
                if not m.empty:
                    vals = pd.to_numeric(m.iloc[0][year_cols], errors='coerce').fillna(0.0)

            total_rows.append({
                'Region': region,
                'Sector': sector,
                'Subsector': subsector,
                'Technology': technology,
                'UE_Type': 'HEAT',
                'Temp_level': 'TOTAL',
                'Subtech': subtech,
                'Drive': drive,
                'FE_Type': fe_type,
                'Trace': (
                    f"Region={region} | Sector={sector} | Subsector={subsector} | Technology={technology} | "
                    f"UE_Type=HEAT | Temp_level=TOTAL | Subtech={subtech} | Drive={drive} | "
                    f"DerivedFrom=SumHeatLevelsFE"
                ),
                **vals.to_dict(),
            })

    totals_df = pd.DataFrame(total_rows)
    if base_df.empty:
        return totals_df
    if totals_df.empty:
        return base_df
    return pd.concat([base_df, totals_df], ignore_index=True)


def get_matches(source_df, row, keys):
    """
    Returns rows from source_df that match all keys in `row`,
    prioritizing exact matches and falling back to 'default' only if no exact match exists.
    Args:
        source_df (pd.DataFrame): DataFrame to filter
        row (dict): Dictionary containing key-value pairs to match
        keys (list): List of columns to match against
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    if source_df is None or source_df.empty:
        return pd.DataFrame()
    ordered_columns = [key for key in keys if key in source_df.columns]
    if not ordered_columns:
        return source_df
    criteria = {key: row.get(key) for key in ordered_columns}
    resolved = select_rows_with_default(
        source_df,
        criteria=criteria,
        ordered_columns=ordered_columns,
    )
    if resolved is None:
        return pd.DataFrame()
    return resolved


