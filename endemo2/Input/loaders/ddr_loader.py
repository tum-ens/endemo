"""
Demand driver (DDr) loader.

Reads historical + scenario DDr sheets, merges time series, detects dependent
drivers and prepares metadata required for forecasting.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

from endemo2.Input.hierarchy.hierachy_classes import DemandDriverData
from endemo2.Input.loaders.common import (
    extract_long_series_columns,
    parse_year_label,
    select_rows_with_default,
)
from endemo2.Input.model_config import META_COLUMNS, SHEET_DEMAND_DRIVERS
from endemo2.Modeling.Methods.prediction_methods import build_interpolation_points


class DdrLoader:
    """Loader for demand drivers and dependent DDr metadata."""

    def __init__(self, data_manager):
        self.data = data_manager

    def _full_year_range(self):
        return self.data.input_manager.general_settings.full_year_range

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def build_dependent_ddr_export(self) -> pd.DataFrame:
        """
        Build a DataFrame with metadata and calculated time series for dependent DDrs.

        This is used for debugging/inspection and for exporting a unified view
        of dependent driver definitions (equation, coefficients, dependencies)
        together with their resolved time series.
        """
        if not self.data.dependent_demand_driver_specs:
            return pd.DataFrame()

        years = [str(y) for y in self._full_year_range()]
        active_regions = set(self.data.input_manager.general_settings.active_regions or [])

        max_deps = self._max_dependency_count(self.data.dependent_demand_driver_specs)
        ddr_cols = [f"DDr{idx}" for idx in range(1, max_deps + 1)]

        rows = []
        for (driver, region_name), spec in self.data.dependent_demand_driver_specs.items():
            if active_regions and region_name not in active_regions:
                continue

            row = self._build_dependent_export_row(spec, driver, region_name, ddr_cols)
            region_df = self._get_region_driver_table(region_name, driver)
            for year in years:
                row[year] = self._pick_export_year_value(region_df, year)
            rows.append(row)

        columns = ["Region", "Variable", "Forecast data", "Function", "Equation", "Trace"] + ddr_cols + ["Unit"] + years
        return pd.DataFrame(rows, columns=columns)

    def read_all_demand_drivers(self, active_regions):
        """
        Read DDr time series from historical + scenario sheets.

        - Merges historical and scenario inputs
        - Applies long-time-series extraction
        - Detects dependent drivers and stores their metadata
        - Creates DemandDriverData objects per driver
        """
        allowed_regions = set(active_regions or [])
        allowed_regions.add("default")

        hist_path = Path(self.data.input_manager.sector_paths["hist_path"])
        scen_key = "scen_path" if "scen_path" in self.data.input_manager.sector_paths else "user_set_path"
        scen_path = Path(self.data.input_manager.sector_paths[scen_key])

        hist_data = self._read_ddr_sheet(hist_path)
        scen_data_raw = self._read_ddr_sheet(scen_path, keep_dependency_rows=True)
        scen_data = self._enforce_scenario_timeseries(scen_data_raw)

        self.data.dependent_demand_drivers = self._collect_dependent_ddrs(scen_data_raw)
        self.data.dependent_demand_driver_specs = self._collect_dependent_specs(scen_data)

        hist_data = self._filter_regions(hist_data, allowed_regions)
        scen_data = self._filter_regions(scen_data, allowed_regions)

        if hist_data.empty and scen_data.empty:
            print("No demand drivers found in the yearly input files.")
            return

        driver_names = self._collect_driver_names(hist_data, scen_data)
        if not driver_names:
            print("No valid demand driver names found.")
            return

        for name in sorted(driver_names):
            combined = self._build_driver_dataset(name, hist_data, scen_data)
            if combined.empty:
                print(f"Demand driver '{name}' not found or empty after merge.")
                continue

            dd_obj = DemandDriverData(name, combined)
            dd_obj.parent = self.data
            self.data.demand_drivers[name] = dd_obj

    def attach_region_demand_drivers(self, region):
        """
        Populate a Region with Variable objects representing each demand driver.

        - Keeps exact-region rows plus default rows.
        - For dependent drivers, ensures full year columns are present.
        - Attaches dependent-driver metadata when available.
        """
        if not self.data.demand_drivers:
            return

        from endemo2.Input.hierarchy.hierachy_classes import Variable as RegionVariable

        for driver_name, driver_data in self.data.demand_drivers.items():
            region_df = self._region_plus_default_rows(driver_data.data, region.region_name)
            if region_df is None or region_df.empty:
                continue

            region_df = self._ensure_full_years_for_dependent(region_df, driver_name, region.region_name)

            variable = RegionVariable(driver_name)
            variable.region_name = region.region_name
            variable.demand_driver_data = region_df.reset_index(drop=True)
            variable.ddr_spec = self._resolve_ddr_spec(driver_name, region.region_name)
            region.add_demand_driver(variable)

    # ------------------------------------------------------------------ #
    # Dependent DDr collection and export
    # ------------------------------------------------------------------ #

    def _max_dependency_count(self, specs: dict) -> int:
        max_deps = 0
        for spec in specs.values():
            max_deps = max(max_deps, len(spec.get("Dependencies") or []))
        return max_deps

    def _build_dependent_export_row(self, spec: dict, driver: str, region_name: str, ddr_cols: list[str]) -> dict:
        deps = spec.get("Dependencies") or []
        deps_txt = ",".join(str(d) for d in deps) if deps else "none"
        row = {
            "Region": region_name,
            "Variable": driver,
            "Forecast data": spec.get("Forecast data"),
            "Function": spec.get("Function"),
            "Equation": spec.get("Equation"),
            "Trace": (
                f"Context=DDr | Region={region_name} | Variable={driver} | "
                f"ForecastData={spec.get('Forecast data')} | Function={spec.get('Function')} | "
                f"Drivers={deps_txt} | Equation={spec.get('Equation')}"
            ),
            "Unit": spec.get("Unit"),
        }
        for idx, col in enumerate(ddr_cols):
            row[col] = deps[idx] if idx < len(deps) else None
        return row

    def _get_region_driver_table(self, region_name: str, driver: str):
        region_obj = self.data.region_lookup.get(region_name)
        region_var = region_obj.get_demand_driver(driver) if region_obj else None
        region_df = region_var.demand_driver_data if region_var else None

        if (region_df is None or region_df.empty) and driver in self.data.demand_drivers:
            driver_obj = self.data.demand_drivers.get(driver)
            region_df = driver_obj.get_data_for_region(region_name) if driver_obj else None

        return region_df

    def _is_default_value(self, val) -> bool:
        if pd.isna(val):
            return True
        text = str(val).strip().lower()
        return text in {"", "default", "none", "nan"}

    def _pick_export_year_value(self, df: pd.DataFrame, year_col: str):
        if df is None or df.empty or year_col not in df.columns:
            return np.nan

        key_cols = [c for c in ["Sector", "Subsector", "Region"] if c in df.columns]
        ranked = df.copy()
        if key_cols:
            ranked["__spec"] = ranked[key_cols].apply(
                lambda r: sum(0 if self._is_default_value(v) else 1 for v in r), axis=1
            )
            ranked = ranked.sort_values("__spec", ascending=False)

        for _, row in ranked.iterrows():
            value = pd.to_numeric(row.get(year_col), errors="coerce")
            if not pd.isna(value):
                return float(value)
        return np.nan

    # ------------------------------------------------------------------ #
    # Core loading workflow
    # ------------------------------------------------------------------ #

    def _filter_regions(self, df: pd.DataFrame, allowed_regions: set[str]) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        if "Region" not in df.columns:
            return df
        return df[df["Region"].isin(allowed_regions)]

    def _collect_driver_names(self, hist_data: pd.DataFrame, scen_data: pd.DataFrame) -> set[str]:
        driver_names = set()
        if not hist_data.empty:
            driver_names.update(hist_data["Variable"].dropna().unique())
        if not scen_data.empty:
            driver_names.update(scen_data["Variable"].dropna().unique())
        return {str(n) for n in driver_names if pd.notna(n) and str(n) != "TIME"}

    def _region_plus_default_rows(self, data_df: pd.DataFrame, region_name: str) -> pd.DataFrame:
        if data_df is None or data_df.empty:
            return pd.DataFrame()
        if "Region" in data_df.columns:
            return data_df[data_df["Region"].isin([region_name, "default"])].copy()
        return data_df.copy()

    def _ensure_full_years_for_dependent(self, region_df: pd.DataFrame, driver_name: str, region_name: str) -> pd.DataFrame:
        dep_regions = self.data.dependent_demand_drivers.get(driver_name, set())
        if region_name not in dep_regions:
            return region_df

        years_full = [str(y) for y in self._full_year_range()]
        for year in years_full:
            if year not in region_df.columns:
                region_df[year] = np.nan
        region_df[years_full] = region_df[years_full].apply(pd.to_numeric, errors="coerce")
        return region_df

    def _resolve_ddr_spec(self, driver_name: str, region_name: str):
        spec_key = (driver_name, region_name)
        default_spec_key = (driver_name, "default")
        if spec_key in self.data.dependent_demand_driver_specs:
            return self.data.dependent_demand_driver_specs[spec_key]
        if default_spec_key in self.data.dependent_demand_driver_specs:
            return self.data.dependent_demand_driver_specs[default_spec_key]
        return None

    # ------------------------------------------------------------------ #
    # Dependency metadata parsing
    # ------------------------------------------------------------------ #

    def _get_dependency_columns(self, df: pd.DataFrame):
        """Return sorted DDr dependency columns (DDr1, DDr2, ...)."""
        if df is None or df.empty:
            return []

        dep_cols = [str(col) for col in df.columns if str(col).lower().startswith("ddr")]

        def sort_key(col_name):
            suffix = col_name[3:]
            try:
                return 0, int(suffix)
            except Exception:
                return 1, suffix

        return sorted(dep_cols, key=sort_key)

    def _normalize_empty_dependency_cells(self, df: pd.DataFrame, dep_cols: list[str]) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        normalized = df.copy()
        for col in dep_cols:
            normalized[col] = normalized[col].apply(
                lambda x: np.nan if isinstance(x, str) and not str(x).strip() else x
            )
        return normalized

    def _collect_dependent_ddrs(self, df: pd.DataFrame):
        """Return mapping driver -> set(regions) for rows with DDr dependencies."""
        dep_cols = self._get_dependency_columns(df)
        if df is None or df.empty or not dep_cols:
            return {}

        normalized = self._normalize_empty_dependency_cells(df, dep_cols)
        mask = normalized[dep_cols].notna().any(axis=1)
        dependent_rows = normalized.loc[mask, ["Variable", "Region"]].dropna(subset=["Variable", "Region"])

        dep_map = {}
        for _, row in dependent_rows.iterrows():
            driver = str(row["Variable"])
            region = str(row["Region"])
            dep_map.setdefault(driver, set()).add(region)

        active_regions = list(self.data.input_manager.general_settings.active_regions or [])
        for _, regions in dep_map.items():
            if "default" in regions:
                regions.update(active_regions)

        return dep_map

    def _collect_dependent_specs(self, df: pd.DataFrame):
        """
        Collect full metadata for dependent DDr rows.

        Captures equation, coefficients, dependencies and interpolation points.
        """
        if df is None or df.empty:
            return {}

        dep_cols = self._get_dependency_columns(df)
        if not dep_cols:
            return {}

        coef_indices, coef_cols_by_idx = self._detect_coef_columns(df.columns)

        normalized = self._normalize_empty_dependency_cells(df, dep_cols)
        mask_dep = normalized[dep_cols].notna().any(axis=1)
        mask_hist_nodep = self._build_hist_nodep_mask(normalized, mask_dep)
        rows = df.loc[mask_dep | mask_hist_nodep]

        specs = {}
        for _, row in rows.iterrows():
            key, spec = self._build_dependent_spec_row(row, dep_cols, coef_indices, coef_cols_by_idx)
            # Duplicate keys are overwritten by later rows (same behavior as before).
            specs[key] = spec

        return self._expand_default_specs_to_active_regions(specs)

    def _normalize_meta_name(self, name: str) -> str:
        return str(name).strip().lower().replace(" ", "").replace("_", "").replace("/", "")

    def _detect_coef_columns(self, columns):
        coef_cols_by_idx = {}
        for col in columns:
            col_str = self._normalize_meta_name(col)
            if len(col_str) >= 2 and col_str[0].lower() == "k" and col_str[1:].isdigit():
                try:
                    coef_cols_by_idx[int(col_str[1:])] = col
                except Exception:
                    continue
        coef_indices = sorted(coef_cols_by_idx.keys())
        return coef_indices, coef_cols_by_idx

    def _build_hist_nodep_mask(self, normalized: pd.DataFrame, mask_dep: pd.Series) -> pd.Series:
        mask_hist_nodep = pd.Series(False, index=normalized.index)
        if "Forecast data" not in normalized.columns:
            return mask_hist_nodep

        fcast_norm = normalized["Forecast data"].astype(str).str.strip().str.lower()
        hist_flag = fcast_norm.isin({"historical", "hist"})

        func_ok = pd.Series(True, index=normalized.index)
        if "Function" in normalized.columns:
            func_norm = normalized["Function"].astype(str).str.strip().str.lower()
            func_ok = func_norm.isin({"const_last", "const_mean", "const"})

        return (~mask_dep) & hist_flag & func_ok

    def _build_dependent_spec_row(self, row, dep_cols, coef_indices, coef_cols_by_idx):
        driver = str(row["Variable"])
        region = str(row["Region"])
        key = (driver, region)

        dependencies = [str(row[c]) for c in dep_cols if pd.notna(row[c])]
        interpolation_points = build_interpolation_points(row)

        spec = {
            "Region": region,
            "Variable": driver,
            "Forecast data": row.get("Forecast data"),
            "Function": row.get("Function"),
            "Unit": row.get("Unit"),
            "Factor": row.get("Factor"),
            "Equation": row.get("Equation"),
            META_COLUMNS["LOWER_LIMIT"]: row.get(META_COLUMNS["LOWER_LIMIT"]),
            "Dependencies": dependencies,
            "Interpolation_points": interpolation_points,
            "Coefficients": {f"k{i}": row.get(coef_cols_by_idx[i]) for i in coef_indices},
        }
        return key, spec

    def _expand_default_specs_to_active_regions(self, specs: dict):
        active_regions = list(self.data.input_manager.general_settings.active_regions or [])
        default_specs = [
            (driver, spec_data)
            for (driver, region), spec_data in specs.items()
            if region == "default"
        ]

        for driver, default_spec in default_specs:
            for region_name in active_regions:
                key = (driver, region_name)
                if key in specs:
                    continue
                cloned = deepcopy(default_spec)
                cloned["Region"] = region_name
                specs[key] = cloned

        return specs

    # ------------------------------------------------------------------ #
    # Raw file reading / sheet normalization
    # ------------------------------------------------------------------ #

    def _read_ddr_sheet(self, path: Path, keep_dependency_rows: bool = False):
        """
        Read the DDr sheet from an Excel file.

        When keep_dependency_rows is False, DDr dependency columns are stripped
        to avoid mixing them into time-series data.
        """
        if not path.exists():
            return pd.DataFrame()

        xls = pd.ExcelFile(path)
        sheet_name = SHEET_DEMAND_DRIVERS

        if sheet_name in xls.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet_name)
        else:
            fallback_sheet = next((s for s in xls.sheet_names if "driver" in s.lower()), None)
            if not fallback_sheet:
                return pd.DataFrame()
            df = pd.read_excel(xls, sheet_name=fallback_sheet)

        if keep_dependency_rows:
            return df

        drop_cols = [col for col in df.columns if self._normalize_meta_name(col).startswith("ddr")]
        return df.drop(columns=drop_cols, errors="ignore")

    def _enforce_scenario_timeseries(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Keep only the detected long time-series block in scenario data.

        The long block is selected dynamically from contiguous year columns,
        independent of absolute column positions.
        """
        if df is None or df.empty:
            return df

        cols = list(df.columns)
        if not cols:
            return df

        metadata_cols, long_year_cols = extract_long_series_columns(cols)
        if not long_year_cols:
            return df

        selected_cols = [c for c in metadata_cols + long_year_cols if c in df.columns]
        df2 = df.loc[:, selected_cols]

        rename_map = {c: parse_year_label(c) for c in long_year_cols if parse_year_label(c) is not None}
        if rename_map:
            df2 = df2.rename(columns=rename_map)

        df2 = df2.loc[:, ~pd.Index(df2.columns).duplicated()]
        return df2

    # ------------------------------------------------------------------ #
    # Driver dataset merge (hist + scenario)
    # ------------------------------------------------------------------ #

    def _build_driver_dataset(self, driver_name, hist_data, scenario_data):
        """
        Merge historical and scenario rows for a single driver.

        Scenario values override historical values when they are non-NaN.
        """
        hist_data = self._as_dataframe(hist_data)
        scenario_data = self._as_dataframe(scenario_data)

        if hist_data.empty and scenario_data.empty:
            return pd.DataFrame()

        hist_subset = hist_data[hist_data["Variable"] == driver_name] if not hist_data.empty else pd.DataFrame()
        scen_subset = scenario_data[scenario_data["Variable"] == driver_name] if not scenario_data.empty else pd.DataFrame()

        scen_subset = self._blank_hist_forecast_years_in_scenario(scen_subset)
        hist_subset = self._compact_rows(hist_subset)
        scen_subset = self._compact_rows(scen_subset)

        if hist_subset.empty and scen_subset.empty:
            return pd.DataFrame()

        combined = self._merge_hist_and_scenario(hist_subset, scen_subset)
        if combined.empty:
            return combined

        years = sorted([c for c in combined.columns if str(c).isdigit()], key=lambda x: int(str(x)))
        non_year = [c for c in combined.columns if c not in years]
        return combined.loc[:, non_year + years]

    def _as_dataframe(self, df) -> pd.DataFrame:
        if df is None or not hasattr(df, "empty"):
            return pd.DataFrame()
        return df

    def _blank_hist_forecast_years_in_scenario(self, scen_subset: pd.DataFrame) -> pd.DataFrame:
        if scen_subset is None or scen_subset.empty:
            return pd.DataFrame() if scen_subset is None else scen_subset

        if "Forecast data" not in scen_subset.columns:
            return scen_subset

        year_cols_all = [c for c in scen_subset.columns if str(c).isdigit()]
        if not year_cols_all:
            return scen_subset

        scen_subset = scen_subset.copy()
        fcast_norm = scen_subset["Forecast data"].astype(str).str.strip().str.lower()
        hist_mask = fcast_norm.isin({"historical", "hist"})
        if hist_mask.any():
            scen_subset.loc[hist_mask, year_cols_all] = np.nan

        return scen_subset

    def _normalize_year_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        df2 = df.copy()
        renamed = {}
        for col in df2.columns:
            col_str = str(col).strip()
            base = col_str.split(".", 1)[0].strip()
            if base.isdigit():
                renamed[col] = base
        if renamed:
            df2 = df2.rename(columns=renamed)

        year_bases = sorted({c for c in df2.columns if str(c).isdigit()}, key=lambda x: int(str(x)))
        if not year_bases:
            return df2

        non_year_cols = [c for c in df2.columns if not str(c).isdigit()]
        out = df2[non_year_cols].copy()

        for year in year_bases:
            year_dup_cols = [c for c in df2.columns if str(c) == str(year)]
            subset = df2.loc[:, year_dup_cols]
            if subset.shape[1] == 1:
                out[year] = pd.to_numeric(subset.iloc[:, 0], errors="coerce")
            else:
                subset_num = subset.apply(pd.to_numeric, errors="coerce")
                out[year] = subset_num.bfill(axis=1).iloc[:, 0]

        return out

    def _collapse_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        years = [c for c in df.columns if str(c).isdigit()]

        if not years:
            key_cols = [c for c in df.columns if c not in years]
            if not key_cols:
                return df.tail(1).reset_index(drop=True)
            return df.drop_duplicates(subset=key_cols, keep="last")

        def last_non_nan(series):
            vals = pd.to_numeric(series, errors="coerce").dropna()
            if vals.empty:
                return np.nan
            return vals.iloc[-1]

        agg = {year: last_non_nan for year in years}
        key_cols = [c for c in df.columns if c not in years]

        if not key_cols:
            return pd.DataFrame([{year: last_non_nan(df[year]) for year in years}])

        return df.groupby(key_cols, as_index=False, dropna=False).agg(agg)

    def _compact_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        df2 = self._normalize_year_columns(df)
        years = [c for c in df2.columns if str(c).isdigit()]
        key_cols = [c for c in df2.columns if c not in years]
        keep_cols = [c for c in key_cols + years if c in df2.columns]
        df2 = df2[keep_cols].copy()
        return self._collapse_rows(df2)

    def _merge_hist_and_scenario(self, hist_subset: pd.DataFrame, scen_subset: pd.DataFrame) -> pd.DataFrame:
        key_cols = ["Region", "Variable"]

        if hist_subset.empty and scen_subset.empty:
            return pd.DataFrame()
        if hist_subset.empty:
            return scen_subset.set_index(key_cols).reset_index()
        if scen_subset.empty:
            return hist_subset.set_index(key_cols).reset_index()

        hist_idx = hist_subset.set_index(key_cols)
        scen_idx = scen_subset.set_index(key_cols)

        # Keep original precedence behavior:
        # 1) combine_first to build union
        # 2) update with scenario so non-NaN scenario values overwrite hist values.
        combined_idx = hist_idx.combine_first(scen_idx)
        combined_idx.update(scen_idx)
        return combined_idx.reset_index()
