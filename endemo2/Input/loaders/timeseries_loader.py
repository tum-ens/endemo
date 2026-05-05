"""
Timeseries (hourly load profile) loader.

This module reads hourly profiles from Data_hourly.xlsx and stores them in the
DataManager for later hourly timeseries generation. It was previously named
SectorLoader and is now renamed for clarity.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from endemo2.Input.loaders.common import match_any, keep_only_matching, parse_cell_content
from endemo2.Input.hierarchy.hierachy_classes import LoadProfile


class TimeseriesLoader:
    """Loader and utilities for hourly time series (load) profiles."""

    def __init__(self, data_manager):
        self.data = data_manager

    @staticmethod
    def _norm_label(value) -> str:
        return str(value).strip().lower().replace(" ", "").replace("_", "").replace("-", "")

    def _resolve_row_label(self, df, candidates, required=True):
        label_map = {self._norm_label(idx): idx for idx in df.index}
        for candidate in candidates:
            found = label_map.get(self._norm_label(candidate))
            if found is not None:
                return found
        if required:
            raise ValueError(f"[Timeseries] Missing required row label. Expected one of: {candidates}")
        return None

    @staticmethod
    def _contains_all(tokens) -> bool:
        return any(str(t).strip().lower() == "all" for t in (tokens or []))

    @staticmethod
    def _contains_default(tokens) -> bool:
        return any(str(t).strip().lower() == "default" for t in (tokens or []))

    def _clone_profile_with_ue_types(self, profile: LoadProfile, ue_types: list[str]) -> LoadProfile:
        cloned = LoadProfile(np.array(profile.values, copy=True))
        cloned.temp_levels = list(getattr(profile, "temp_levels", ["default"]))
        cloned.ue_types = ue_types
        cloned.all_subsectors = False
        return cloned

    def _apply_all_subsector_override(self, profiles: list[LoadProfile]) -> list[LoadProfile]:
        if not profiles:
            return profiles
        all_profiles = [p for p in profiles if getattr(p, "all_subsectors", False)]
        if not all_profiles:
            return profiles

        override_all = any(self._contains_default(getattr(p, "ue_types", [])) for p in all_profiles)
        override_set = set()
        if not override_all:
            for profile in all_profiles:
                for ue in getattr(profile, "ue_types", []):
                    ue_str = str(ue).strip()
                    if ue_str and ue_str.lower() != "default":
                        override_set.add(ue_str.upper())

        result = list(all_profiles)
        for profile in profiles:
            if getattr(profile, "all_subsectors", False):
                continue

            ue_types = [str(u).strip() for u in getattr(profile, "ue_types", []) if str(u).strip()]
            has_default = self._contains_default(ue_types)

            if override_all:
                continue

            if has_default:
                all_ue_types = [
                    str(u).strip() for u in self.data.input_manager.general_settings.useful_energy_types
                    if str(u).strip()
                ]
                remaining = [u for u in all_ue_types if u.upper() not in override_set]
            else:
                remaining = [u for u in ue_types if u.upper() not in override_set]

            if not remaining:
                continue
            if not has_default and len(remaining) == len(ue_types):
                result.append(profile)
                continue
            result.append(self._clone_profile_with_ue_types(profile, remaining))

        return result

    def read_and_filter_load_profiles(self, timsereis_file_df):
        """
        Read hourly profiles and keep only active regions/sectors/subsectors.

        This method filters metadata headers, converts numeric values, applies
        factors and stores the resulting load profiles for later use.
        """
        active_regions = self.data.input_manager.general_settings.active_regions
        active_sectors = self.data.input_manager.general_settings.active_sectors
        active_subsectors = self.data.input_manager.general_settings.active_subsectors
        filter_reg = active_regions + ["default", "all"]
        filter_sec = active_sectors + ["default", "all"]
        filter_ss = [sub for subs in active_subsectors.values() for sub in subs] + ["default", "all"]
        region_row = self._resolve_row_label(timsereis_file_df, ["Region"])
        sector_row = self._resolve_row_label(timsereis_file_df, ["Sector"])
        subsector_row = self._resolve_row_label(timsereis_file_df, ["Subsector"])
        technology_row = self._resolve_row_label(timsereis_file_df, ["Technology", "Tech"])
        ue_type_row = self._resolve_row_label(timsereis_file_df, ["UE_Type", "UE Type", "Useful Energy Type"])
        temp_level_row = self._resolve_row_label(timsereis_file_df, ["Temp_level", "Temp level", "Heat level"])
        factor_row = self._resolve_row_label(timsereis_file_df, ["Factor"], required=False)

        metadata_rows = {
            region_row,
            sector_row,
            subsector_row,
            technology_row,
            ue_type_row,
            temp_level_row,
        }
        if factor_row is not None:
            metadata_rows.add(factor_row)

        filtered_df = timsereis_file_df.copy()
        final_cols = []
        for col in timsereis_file_df.columns:
            region = timsereis_file_df.loc[region_row, col]
            sector = timsereis_file_df.loc[sector_row, col]
            subsector = timsereis_file_df.loc[subsector_row, col]
            match_r = match_any(region, filter_reg)
            match_s = match_any(sector, filter_sec)
            match_ss = match_any(subsector, filter_ss)
            if match_r and match_s and match_ss:
                filtered_df.at[region_row, col] = keep_only_matching(region, filter_reg)
                filtered_df.at[sector_row, col] = keep_only_matching(sector, filter_sec)
                filtered_df.at[subsector_row, col] = keep_only_matching(subsector, filter_ss)
                final_cols.append(col)
        final_df = filtered_df.loc[:, final_cols]
        final_df.index.name = None

        value_rows = [idx for idx in final_df.index if idx not in metadata_rows]
        for col in final_df.columns:
            regions = parse_cell_content(final_df.loc[region_row, col])
            sectors = parse_cell_content(final_df.loc[sector_row, col])
            subsectors = parse_cell_content(final_df.loc[subsector_row, col])
            technologies = parse_cell_content(final_df.loc[technology_row, col])
            ue_types = parse_cell_content(final_df.loc[ue_type_row, col])
            temp_levels = parse_cell_content(final_df.loc[temp_level_row, col])
            all_subsectors = self._contains_all(subsectors)
            if self._contains_all(regions):
                regions = active_regions
            if self._contains_all(sectors):
                sectors = active_sectors
            if self._contains_all(subsectors):
                subsectors = [sub for sector in sectors if sector in active_subsectors for sub in
                              active_subsectors[sector]]
            if factor_row is None:
                factor = 1.0
            else:
                factor = pd.to_numeric(
                    str(final_df.loc[factor_row, col]).replace(",", "."),
                    errors="coerce",
                )
                factor = float(factor) if not pd.isna(factor) else 1.0
            time_series = pd.to_numeric(
                final_df.loc[value_rows, col].astype(str).str.replace(",", "."),
                errors="coerce",
            ).dropna().values
            if len(time_series) == 0:
                continue
            time_series *= factor
            load_profile = LoadProfile(time_series)
            load_profile.temp_levels = temp_levels
            load_profile.ue_types = ue_types
            load_profile.all_subsectors = all_subsectors
            for region in regions:
                for sector in sectors:
                    for subsector in subsectors:
                        for tech in technologies:
                            self.data.load_profiles \
                                .setdefault(region, {}) \
                                .setdefault(sector, {}) \
                                .setdefault(subsector, {}) \
                                .setdefault(tech, []) \
                                .append(load_profile)

    def _resolve_profiles_for_region(self, region_key, sector_name, subsector_name, tech_name):
        """Resolve profiles inside one region scope with sector/subsector/tech default fallback."""
        region_data = self.data.load_profiles.get(region_key)
        if region_data is None:
            return None

        sector_data = region_data.get(sector_name)
        if sector_data is None:
            sector_data = region_data.get("default")
        if sector_data is None:
            return None

        subsector_data = sector_data.get(subsector_name)
        if subsector_data is None:
            subsector_data = sector_data.get("default")
        if subsector_data is None:
            return None

        profiles = subsector_data.get(tech_name)
        if profiles is None:
            profiles = subsector_data.get("default")
        if profiles is None:
            return None

        return list(profiles)

    @staticmethod
    def _profile_signature(profile):
        """Signature for exact-vs-default precedence merge."""
        ue_types = tuple(sorted(str(u).strip().upper() for u in (getattr(profile, "ue_types", []) or [])))
        temp_levels = tuple(sorted(str(t).strip().upper() for t in (getattr(profile, "temp_levels", []) or [])))
        all_sub = bool(getattr(profile, "all_subsectors", False))
        return (ue_types, temp_levels, all_sub)

    def get_load_profiles(self, region_name, sector_name, subsector_name, tech_name):
        """
        Return load profiles with additive default-region mapping:
        - exact region profiles are loaded first
        - default-region profiles are additionally loaded
        - if both define the same profile signature, exact region wins
        """
        try:
            exact_profiles = self._resolve_profiles_for_region(region_name, sector_name, subsector_name, tech_name) or []
            default_profiles = self._resolve_profiles_for_region("default", sector_name, subsector_name, tech_name) or []

            if not exact_profiles and not default_profiles:
                return None

            merged = list(exact_profiles)
            exact_signatures = {self._profile_signature(p) for p in exact_profiles}
            for p in default_profiles:
                if self._profile_signature(p) in exact_signatures:
                    continue
                merged.append(p)

            if not merged:
                return None
            return self._apply_all_subsector_override(merged)
        except (KeyError, AttributeError):
            return None


    def timeseries_total(self):
        """
        Aggregate timeseries profiles across all regions.

        Returns a structure compatible with the previous output format,
        including contributor lists for traceability.
        """
        for region in self.data.regions:
            if not region.timeseries_results['profiles']:
                continue
            for profile_id, region_profile_data in region.timeseries_results['profiles'].items():
                if profile_id not in self.data.timeseries_total_results['profiles']:
                    self.data.timeseries_total_results['profiles'][profile_id] = {
                        'years': {},
                        'regions_contributed': set(),
                        'sectors_contributed': set(),
                        'subsectors_contributed': set(),
                        'techs_contributed': set()
                    }
                profile_data = self.data.timeseries_total_results['profiles'][profile_id]
                profile_data['regions_contributed'].add(region.name)
                profile_data['sectors_contributed'].update(
                    region_profile_data.get('sectors_contributed', set()))
                profile_data['subsectors_contributed'].update(
                    region_profile_data.get('subsectors_contributed', set()))
                profile_data['techs_contributed'].update(
                    region_profile_data.get('techs_contributed', set()))
                for year, year_data in region_profile_data['years'].items():
                    if year in profile_data['years']:
                        profile_data['years'][year]['hourly_values'] = np.add(
                            profile_data['years'][year]['hourly_values'],
                            year_data['hourly_values']
                        )
                        profile_data['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        profile_data['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }
        for profile_data in self.data.timeseries_total_results['profiles'].values():
            for key in ['regions_contributed', 'sectors_contributed',
                        'subsectors_contributed', 'techs_contributed']:
                profile_data[key] = list(profile_data[key])
        return self.data.timeseries_total_results

