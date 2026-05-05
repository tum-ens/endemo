"""
Loader for ECU and DDet inputs.

This loader reads yearly hist/scenario sheets for ECU + DDet data, filters
them by active energy settings, and maps the rows into hierarchy objects.

Mapping model in short:
- First, workbook tables are loaded and pre-filtered globally.
- Then, for each (Region, Sector, Subsector, Technology, Variable) path,
  the best matching rows are selected with "exact first, default as fallback".
- Settings rows ("Forecast data", "Function", DDr*, Factor, Lower limit, ...)
  are attached to Variable.settings.
- Time series rows are split into Variable.historical and Variable.user
  according to settings and availability.
"""

from __future__ import annotations
import pandas as pd
from endemo2.Input.hierarchy.hierachy_classes import Technology, Variable
from endemo2.Input.loaders.common import select_rows_with_default, is_default_value
from endemo2.Input.model_config import (
    META_COLUMNS,
)


class DDetEcuLoader:
    """Read and map ECU/DDet input data onto the hierarchy."""

    def __init__(self, data_manager):
        self.data = data_manager
        self.data_yearly_hist = pd.DataFrame()
        self.data_yearly_scenario = pd.DataFrame()
        self.sector_hist_data = {}
        self.sector_user_data = {}

    def read_ecu_ddet_data(self, active_regions, active_sectors, ue_type_list, heat_levels_list):
        """
        Read and pre-filter yearly ECU/DDet input data.
        Just loads cache for fast mapping
        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: (hist, scenario)
        """
        # Step 1: load hist/scenario sheets with flexible sheet-name fallback.
        input_data_paths = self.data.input_manager.sector_paths
        hist_data, scenario_data = self._load_sector_data(input_data_paths, active_regions=active_regions)
        # Step 2: keep only selected UE/Temp scope from Model_Settings.
        hist_data, scenario_data = self._filter_sector_data(
            hist_data, scenario_data, ue_type_list, heat_levels_list
        )
        self.data_yearly_hist = hist_data
        self.data_yearly_scenario = scenario_data
        # Build per-sector caches (including sector-level "default" rows).
        self.sector_hist_data = {
            sector: (
                hist_data[hist_data["Sector"].isin([sector, "default"])]
                if "Sector" in hist_data.columns else hist_data
            )
            for sector in active_sectors
        }
        self.sector_user_data = {
            sector: (
                scenario_data[scenario_data["Sector"].isin([sector, "default"])]
                if "Sector" in scenario_data.columns else scenario_data
            )
            for sector in active_sectors
        }
        return hist_data, scenario_data

    def get_sector_data(self, sector_name):
        """Return pre-filtered (hist, scenario) data for one sector."""
        return (
            self.sector_hist_data.get(sector_name, pd.DataFrame()),
            self.sector_user_data.get(sector_name, pd.DataFrame()),
        )

    def attach_subsector_inputs(self, region_name, sector_name, subsector, row):
        """
        Map ECU and DDet variables to the given subsector and its technologies.
        """
        # Get already pre-filtered data for the current sector.
        hist_data_by_sector, user_set_data_by_sector = self.get_sector_data(sector_name)
        # Technologies come from settings row (comma-separated string) or "default".
        technology_names = self._parse_technologies(row)
        ecu_name = row.get("ECU")
        # DDet columns are dynamic (DDet1..DDetN in settings sheet).
        ddet_columns = {col: row[col] for col in row.index if col.startswith("DDet") and pd.notna(row[col])}
        ddet_names = list(ddet_columns.values())
        subsector_variables = [ecu_name] + ddet_names
        for index, variable_name in enumerate(subsector_variables):
            if index == 0:
                # First variable is ECU -> attach directly to Subsector.ecu.
                variable = self.map_region_data(
                    region_name=region_name,
                    sector_name=sector_name,
                    variable_name=variable_name,
                    hist_data=hist_data_by_sector,
                    user_set_data=user_set_data_by_sector,
                    subsector_name=subsector.name,
                )
                subsector.add_ecu(variable)
            else:
                # Remaining variables are DDets -> attached under each matching technology.
                for tech_name in technology_names:
                    variable_user_df = self._resolve_scope_rows(
                        df=user_set_data_by_sector,
                        criteria={
                            "Sector": sector_name,
                            "Subsector": subsector.name,
                        },
                        ordered_columns=["Sector", "Subsector"],
                    )
                    variable_user_df = self._filter_variable_rows(variable_user_df, variable_name)
                    variable_user_df = self._filter_technology_rows(variable_user_df, tech_name)
                    if variable_user_df.empty:
                        # Skip creating technology nodes that have no matching scenario/settings rows.
                        continue
                    technology = next((tech for tech in subsector.technologies if tech.name == tech_name), None)
                    if not technology:
                        technology = Technology(name=tech_name)
                        subsector.add_technology(technology)
                    variable = self.map_region_data(
                        region_name=region_name,
                        sector_name=sector_name,
                        variable_name=variable_name,
                        hist_data=hist_data_by_sector,
                        user_set_data=user_set_data_by_sector,
                        tech_name=tech_name,
                        subsector_name=subsector.name,
                    )
                    if self.data.input_manager.general_settings.timeseries_forecast == 1:
                        # Load profile lookup also uses default fallback per hierarchy level.
                        technology.load_profile = self.data.get_load_profiles(
                            region_name, sector_name, subsector.name, tech_name
                        )
                    technology.add_variable(variable)

    def get_final_energy_variable_inputs(self):
        """Build Variable objects for final-energy efficiency/share inputs."""
        fe_type_list = self.data.input_manager.general_settings.final_energy_types
        user_set = self.data_yearly_scenario
        if user_set is None or user_set.empty:
            return [Variable("EFFICIENCY"), Variable("FE_SHARE_FOR_UE")]
        # FE helper variables are filtered by FE_Type whitelist from Energy_Types.
        filtered = user_set[user_set["FE_Type"].isin(fe_type_list)] if "FE_Type" in user_set.columns else user_set
        fe_dfs = {
            "EFFICIENCY": filtered[filtered["Variable"] == "EFFICIENCY"],
            "FE_SHARE_FOR_UE": filtered[filtered["Variable"] == "FE_SHARE_FOR_UE"],
        }
        var_ef = Variable("EFFICIENCY")
        var_ef.user = fe_dfs.get("EFFICIENCY")
        var_share = Variable("FE_SHARE_FOR_UE")
        var_share.user = fe_dfs.get("FE_SHARE_FOR_UE")
        return [var_ef, var_share]

    # ------------------------------------------------------------------ #
    # Internal helpers 
    # ------------------------------------------------------------------ #

    def map_region_data(
        self,
        region_name,
        sector_name,
        variable_name,
        hist_data,
        user_set_data,
        subsector_name,
        tech_name=None,
    ):
        variable = Variable(variable_name)
        variable.region_name = region_name
        scope = {"Sector": sector_name, "Subsector": subsector_name}
        ordered_scope_cols = ["Sector", "Subsector"]

        # 1) Strict variable match first (no default fallback on Variable itself).
        user_base = self._filter_variable_rows(user_set_data, variable_name)
        hist_base = self._filter_variable_rows(hist_data, variable_name)
        # 2) Resolve sector/subsector scope with exact>default logic.
        variable_user_df = self._resolve_scope_rows(user_base, scope, ordered_scope_cols)
        variable_hist_df = self._resolve_scope_rows(hist_base, scope, ordered_scope_cols)
        if tech_name:
            # 3) Resolve technology with exact + default rows kept.
            variable_user_df = self._filter_technology_rows(variable_user_df, tech_name)
            variable_hist_df = self._filter_technology_rows(variable_hist_df, tech_name)

        # "settings_columns" are metadata rows that define forecasting behavior.
        settings_columns = [
            col for col in [
                "Region", "UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive",
                "Unit", "Factor", "Function", "Equation", "Forecast data",
                META_COLUMNS["LOWER_LIMIT"],
                META_COLUMNS["UPPER_LIMIT"]
            ] if col in variable_user_df.columns
        ] + [col for col in variable_user_df.columns if str(col).startswith("DDr")]

        # These columns define matching granularity between settings and time-series rows.
        filter_columns = ["UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive"]
        if "Region" in variable_user_df.columns:
            default_set_rows = variable_user_df[variable_user_df["Region"] == "default"]
        else:
            default_set_rows = variable_user_df.iloc[0:0].copy()
        if "Region" in variable_hist_df.columns:
            default_hist_rows = variable_hist_df[variable_hist_df["Region"] == "default"]
        else:
            default_hist_rows = variable_hist_df.iloc[0:0].copy()
        variable_set_df = variable_user_df[settings_columns] if settings_columns else variable_user_df.iloc[0:0].copy()

        # Region-level settings (exact region rows, with default completion where needed).
        region_set_df = self._get_region_data(variable_set_df, region_name, default_set_rows, filter_columns)
        if "Forecast data" not in region_set_df.columns:
            default_mode = "Historical" if variable_hist_df is not None and not variable_hist_df.empty else "User"
            region_set_df = region_set_df.copy()
            region_set_df["Forecast data"] = default_mode
        if region_set_df.empty:
            default_mode = "Historical" if variable_hist_df is not None and not variable_hist_df.empty else "User"
            region_set_df = pd.DataFrame([{"Region": region_name, "Forecast data": default_mode}])
        variable.settings = region_set_df
        filtered_list = [col for col in filter_columns if col in region_set_df.columns]

        # Split output rows into historical/user based on settings row mode.
        if any(col in region_set_df.columns for col in filtered_list):
            historical_rows = region_set_df[region_set_df["Forecast data"] == "Historical"]
            user_rows = region_set_df[region_set_df["Forecast data"] != "Historical"]
            if not historical_rows.empty:
                filter_keys = [
                    col for col in filtered_list if col in historical_rows.columns and col in variable_hist_df.columns
                ]
                region_types_levels = historical_rows[filter_keys]
                hist_data_region = variable_hist_df[
                    (variable_hist_df["Region"] == region_name)
                    & variable_hist_df[filter_keys].apply(tuple, axis=1).isin(region_types_levels.apply(tuple, axis=1))
                ]
                missing_combinations = region_types_levels.apply(tuple, axis=1)[
                    ~region_types_levels.apply(tuple, axis=1).isin(hist_data_region[filter_keys].apply(tuple, axis=1))
                ]
                if not missing_combinations.empty:
                    # Fill missing combinations with default region rows.
                    default_data = variable_hist_df[
                        ("Region" in variable_hist_df.columns)
                        & (variable_hist_df["Region"] == "default")
                        & variable_hist_df[filter_keys].apply(tuple, axis=1).isin(missing_combinations)
                    ]
                    hist_data_region = pd.concat([hist_data_region, default_data], ignore_index=True)
                variable.historical = hist_data_region if not hist_data_region.empty else None
            if not user_rows.empty:
                filter_keys = [
                    col for col in filtered_list if col in user_rows.columns and col in variable_user_df.columns
                ]
                region_types_levels = user_rows[filter_keys]
                user_data_region = variable_user_df[
                    (variable_user_df["Region"] == region_name)
                    & variable_user_df[filter_keys].apply(tuple, axis=1).isin(region_types_levels.apply(tuple, axis=1))
                ]
                missing_combinations = region_types_levels.apply(tuple, axis=1)[
                    ~region_types_levels.apply(tuple, axis=1).isin(user_data_region[filter_keys].apply(tuple, axis=1))
                ]
                if not missing_combinations.empty:
                    # Fill missing combinations with default region rows.
                    default_data = variable_user_df[
                        ("Region" in variable_user_df.columns)
                        & (variable_user_df["Region"] == "default")
                        & variable_user_df[filter_keys].apply(tuple, axis=1).isin(missing_combinations)
                    ]
                    user_data_region = pd.concat([user_data_region, default_data], ignore_index=True)
                variable.user = user_data_region if not user_data_region.empty else None
        else:
            # No granular keys available -> choose one mode for whole variable.
            if "Forecast data" not in variable.settings.columns or variable.settings.empty:
                forecast_data = "Historical" if variable_hist_df is not None and not variable_hist_df.empty else "User"
            else:
                forecast_data = variable.settings["Forecast data"].iloc[0]
            if forecast_data == "Historical":
                hist_data_region = self._get_region_data(variable_hist_df, region_name, default_hist_rows, filtered_list)
                variable.historical = hist_data_region
            else:
                user_data_region = self._get_region_data(variable_user_df, region_name, default_set_rows, filtered_list)
                variable.user = user_data_region
        return variable

    def _resolve_scope_rows(self, df: pd.DataFrame, criteria: dict, ordered_columns: list[str]) -> pd.DataFrame:
        """
        Resolve rows hierarchically for scope columns (Sector/Subsector) with
        combination-aware fallback.

        Behavior:
        - exact values are preferred
        - default rows are retained for combinations that have no exact row
        - duplicates are allowed and resolved later by the model pipeline
        """
        if df is None or df.empty:
            return pd.DataFrame()
        current = df.copy()
        key_candidates = [
            "Region", "Sector", "Subsector", "Variable", "Technology",
            "UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive",
        ]

        def _norm_value(v):
            if pd.isna(v):
                return "__nan__"
            text = str(v).strip()
            if text == "":
                return "__blank__"
            return text.casefold()

        for column in ordered_columns:
            if column not in current.columns:
                continue
            target = criteria.get(column)
            if is_default_value(target):
                # If target itself is default-like, keep current scope unchanged.
                continue

            target_norm = str(target).strip().casefold()
            col_norm = current[column].astype(str).str.strip().str.casefold()
            exact_df = current[col_norm == target_norm]
            default_df = current[current[column].apply(is_default_value)]

            if exact_df.empty and default_df.empty:
                return current.iloc[0:0]
            if exact_df.empty:
                current = default_df
                continue
            if default_df.empty:
                current = exact_df
                continue

            sig_cols = [c for c in key_candidates if c in current.columns and c != column]
            if not sig_cols:
                current = exact_df
                continue

            # Keep default rows only for signatures that have no exact counterpart.
            exact_sigs = set(
                exact_df[sig_cols]
                .apply(lambda r: tuple(_norm_value(r[c]) for c in sig_cols), axis=1)
                .tolist()
            )
            default_sigs = default_df[sig_cols].apply(
                lambda r: tuple(_norm_value(r[c]) for c in sig_cols), axis=1
            )
            default_keep = default_df.loc[~default_sigs.isin(exact_sigs)]
            current = pd.concat([exact_df, default_keep], ignore_index=True)
        return current

    def _filter_variable_rows(self, df: pd.DataFrame, variable_name: str) -> pd.DataFrame:
        """
        Keep only rows for the requested variable.

        Variable assignment is strict by name; defaults are handled only on
        hierarchy columns (Sector/Subsector/Region), not on Variable.
        """
        if df is None or df.empty:
            return pd.DataFrame()
        if "Variable" not in df.columns:
            return pd.DataFrame()
        target = str(variable_name).strip()
        return df[df["Variable"].astype(str).str.strip() == target].copy()

    def _filter_technology_rows(self, df: pd.DataFrame, tech_name: str) -> pd.DataFrame:
        """
        Filter by technology while keeping both exact and default rows.

        This avoids dropping default technology rows when exact rows exist for
        only a subset of UE/Temp combinations.
        """
        if df is None or df.empty:
            return pd.DataFrame()
        if "Technology" not in df.columns:
            return df
        target = str(tech_name).strip()
        col = df["Technology"]
        exact_mask = col.astype(str).str.strip() == target
        default_mask = col.apply(is_default_value)
        out = df[exact_mask | default_mask].copy()
        if out.empty:
            return pd.DataFrame()
        return out

    def _get_region_data(self, df, region_name, default_data, filter_columns):
        """
        Resolve one dataframe to a single target region.

        Behavior:
        - Prefer exact region rows.
        - If region rows are missing, clone default rows for that region.
        - If granular combinations are partially missing, add missing rows from default.
        """
        if df is None or df.empty:
            return pd.DataFrame()
        if "Region" not in df.columns:
            return self._clean_dataframe(df)
        region_data = df[df["Region"] == region_name].copy()
        if region_data.empty:
            if default_data.empty:
                # Keep legacy fallback object shape to avoid downstream crashes.
                return pd.DataFrame([{
                    "Region": region_name,
                    "Coefficients/intp_points": "None",
                    "Equation": "None",
                    "UE_Type": "None",
                    "Factor": "None",
                    "2000": 0,
                }])
            out = self._clean_dataframe(default_data.copy())
            if "Region" in out.columns:
                out["Region"] = region_name
            return out

        filtered_cols = [col for col in filter_columns if col in region_data.columns]
        if not filtered_cols:
            return self._clean_dataframe(region_data)

        default_data = default_data.reset_index(drop=True)
        region_data = region_data.reset_index(drop=True)

        if "FE_Type" in filtered_cols:
            # FE_Type has special handling: rows with FE_Type and rows without FE_Type
            # are treated separately to avoid accidental over-matching.
            default_with_fe = default_data[default_data["FE_Type"].notna()]
            default_without_fe = default_data[default_data["FE_Type"].isna()]

            merged_fe = default_with_fe.merge(region_data, on=filtered_cols, how="left", indicator=True)
            missing_fe = merged_fe[merged_fe["_merge"] == "left_only"].drop(columns="_merge")

            non_null_fe_pairs = region_data[region_data["FE_Type"].notna()][["UE_Type", "Temp_level"]].drop_duplicates()
            default_without_fe_filtered = default_without_fe.merge(
                non_null_fe_pairs, on=["UE_Type", "Temp_level"], how="left", indicator=True
            ).query('_merge == "left_only"').drop(columns="_merge")

            merged_no_fe = default_without_fe_filtered.merge(region_data, on=filtered_cols, how="left", indicator=True)
            missing_no_fe = merged_no_fe[merged_no_fe["_merge"] == "left_only"].drop(columns="_merge")

            missing_rows = pd.concat([missing_fe, missing_no_fe], ignore_index=True)
        else:
            merged = default_data.merge(region_data, on=filtered_cols, how="left", indicator=True)
            missing_rows = merged[merged["_merge"] == "left_only"].drop(columns="_merge")

        if not missing_rows.empty:
            missing_rows.columns = missing_rows.columns.str.replace("_x$", "", regex=True)
            missing_rows = missing_rows[[col for col in missing_rows if not col.endswith("_y")]]
            for col in region_data.columns:
                if col not in missing_rows:
                    missing_rows[col] = None
            region_data = pd.concat([region_data, missing_rows], ignore_index=True)

        return self._clean_dataframe(region_data)

    def _clean_dataframe(self, df):
        if df is None:
            return df
        return df.dropna(axis=0, how="all").dropna(axis=1, how="all")

    def _read_first_available_sheet(self, path, sheet_names):
        if not path:
            return pd.DataFrame()
        for sheet in sheet_names:
            try:
                return pd.read_excel(path, sheet_name=sheet)
            except Exception:
                continue
        return pd.DataFrame()

    def _normalize_fe_type_column(self, df):
        if df is None or df.empty:
            return df
        rename_map = {}
        for col in df.columns:
            if str(col).strip().lower() == "fe_typ":
                rename_map[col] = "FE_Type"
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    def _normalize_common_columns(self, df):
        if df is None or df.empty:
            return df
        rename_map = {}

        def _norm(text):
            return str(text).strip().lower().replace(" ", "").replace("_", "").replace("-", "")

        aliases = {
            "forecastdata": "Forecast data",
            "forecast_data": "Forecast data",
        }
        for col in df.columns:
            key = _norm(col)
            if key in aliases:
                rename_map[col] = aliases[key]
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    def _load_sector_data(self, data_paths, active_regions=None):
        """
        Load yearly ECU/DDet tables with flexible sheet-name fallback and
        normalize important aliases (e.g. FE_Typ -> FE_Type).
        """
        hist_path = data_paths["hist_path"]
        user_set_path = data_paths["user_set_path"]
        hist_data = self._read_first_available_sheet(
            hist_path, ["ECU_DDET_Region", "Data", "ECU_DDets", "ECU_DDets_Region"]
        )
        user_set_data = self._read_first_available_sheet(
            user_set_path, ["ECUs_DDets_Region", "ECU_DDets_Region", "ECU_DDets"]
        )
        if not hist_data.empty:
            hist_data.columns = hist_data.columns.astype(str)
            hist_data = self._normalize_fe_type_column(hist_data)
            hist_data = self._normalize_common_columns(hist_data)
        if not user_set_data.empty:
            user_set_data.columns = user_set_data.columns.astype(str)
            user_set_data = self._normalize_fe_type_column(user_set_data)
            user_set_data = self._normalize_common_columns(user_set_data)

        if active_regions:
            # Keep active regions + default rows only.
            allowed = set(active_regions)
            allowed.add("default")
            if "Region" in hist_data.columns:
                hist_data = hist_data[hist_data["Region"].isin(allowed)]
            if "Region" in user_set_data.columns:
                user_set_data = user_set_data[user_set_data["Region"].isin(allowed)]
        return hist_data, user_set_data

    def _filter_sector_data(self, hist_data, user_set_data, ue_type_list, heat_levels_list):
        """
        Filter input rows by selected UE/Temp lists while preserving "default" wildcard rows.
        """
        ue_filter = None if not ue_type_list else ue_type_list
        heat_filter = None if not heat_levels_list else heat_levels_list
        if ue_filter is None and heat_filter is None:
            return hist_data, user_set_data

        def _is_default_marker(series: pd.Series) -> pd.Series:
            """
            Treat 'default' (case-insensitive), empty string and NaN as wildcard values.
            Wildcards must survive filtering so they can be used as hierarchical fallbacks.
            """
            text = series.astype(str).str.strip().str.lower()
            return series.isna() | (text == "") | (text == "default")

        hist_data_filtered = hist_data
        if ue_filter is not None and "UE_Type" in hist_data_filtered.columns:
            ue_default = _is_default_marker(hist_data_filtered["UE_Type"])
            hist_data_filtered = hist_data_filtered[
                ue_default | (hist_data_filtered["UE_Type"].isin(ue_filter))
            ]
        if heat_filter is not None and "Temp_level" in hist_data_filtered.columns:
            heat_default = _is_default_marker(hist_data_filtered["Temp_level"])
            hist_data_filtered = hist_data_filtered[
                heat_default | (hist_data_filtered["Temp_level"].isin(heat_filter))
            ]

        user_set_data_filtered = user_set_data
        if ue_filter is not None and "UE_Type" in user_set_data_filtered.columns:
            ue_default = _is_default_marker(user_set_data_filtered["UE_Type"])
            user_set_data_filtered = user_set_data_filtered[
                ue_default | (user_set_data_filtered["UE_Type"].isin(ue_filter))
            ]
        if heat_filter is not None and "Temp_level" in user_set_data_filtered.columns:
            heat_default = _is_default_marker(user_set_data_filtered["Temp_level"])
            user_set_data_filtered = user_set_data_filtered[
                heat_default | (user_set_data_filtered["Temp_level"].isin(heat_filter))
            ]
        return hist_data_filtered, user_set_data_filtered

    def _parse_technologies(self, row):
        if "Technology" in row and pd.notna(row["Technology"]) and row["Technology"].strip():
            return [tech.strip() if tech.strip() else "default" for tech in row["Technology"].split(",")]
        return ["default"]

