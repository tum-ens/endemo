"""
Subregional loader.

This module reads subregion definitions and their time series inputs from the
settings and scenario Excel files. It then attaches the resolved data frames
to Region objects, enabling downstream subregional forecasting and FE splits.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np

from endemo2.Input.loaders.common import (
    parse_cell_content,
    match_any,
    keep_only_matching,
    select_rows_with_default,
    extract_long_series_columns,
    parse_year_label,
)
from endemo2.Input.model_config import (
    SHEET_SUBREGIONAL_DIVISION,
)


def _is_default_like(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "default", "none", "nan"}


class SubregionLoader:
    """Loader for subregional definitions and time series."""

    def __init__(self, data_manager):
        self.data = data_manager

    def read_subregions(self, active_regions):
        """
        Read subregion definitions from Model_Settings.xlsx (sheet 'Subregions').

        - Supports both legacy column names and the newer "Subregion 2024"
        - Applies optional SkipSubregion flags
        - Builds alias mappings when old/new codes differ
        """
        ctrl_path = self.data.input_manager.ctrl_file
        if not ctrl_path.exists():
            return
        xls = pd.ExcelFile(ctrl_path)
        try:
            df = pd.read_excel(ctrl_path, sheet_name="Subregions")
        except Exception:
            fallback_sheet = next((s for s in xls.sheet_names if "subregion" in s.lower()), None)
            if fallback_sheet:
                df = pd.read_excel(xls, sheet_name=fallback_sheet)
            else:
                return

        def norm_col(name: str) -> str:
            return str(name).strip().lower().replace(" ", "").replace("_", "").replace("/", "")

        def find_col(df, names):
            for col in df.columns:
                if norm_col(col) in names:
                    return col
            return None

        def is_truthy(val):
            if pd.isna(val):
                return False
            if isinstance(val, str):
                return val.strip().lower() in {"1", "true", "yes", "y", "x", "wahr", "ja"}
            return bool(val)

        region_col = find_col(df, {"region"})
        subregion_col = find_col(df, {"subregion"})
        subregion_2024_col = find_col(df, {"subregion2024"})
        skip_col = find_col(df, {"skipsubregion"})
        name_col = find_col(df, {"subregionname"})

        if region_col is None or (subregion_col is None and subregion_2024_col is None):
            return

        self.data.subregions = {}
        self.data.subregion_aliases = {}
        allowed_regions = set(active_regions or [])
        allowed_regions.add("default")

        for _, row in df.iterrows():
            if skip_col and is_truthy(row.get(skip_col)):
                continue
            region = str(row[region_col]).strip() if pd.notna(row.get(region_col)) else None
            if not region or region not in allowed_regions:
                continue
            code = None
            code_2024 = None
            code_old = None
            if subregion_2024_col is not None:
                val = row.get(subregion_2024_col)
                if pd.notna(val):
                    code_2024 = str(val).strip()
            if subregion_col is not None:
                val = row.get(subregion_col)
                if pd.notna(val):
                    code_old = str(val).strip()
            code = code_2024 or code_old
            if not code:
                continue
            name = str(row.get(name_col)).strip() if name_col and pd.notna(row.get(name_col)) else code
            self.data.subregions.setdefault(region, {})[code] = {"code": code, "name": name}
            if code_old and code_2024 and code_old != code_2024:
                self.data.subregion_aliases[(region, code_old)] = code_2024

    def read_subregion_timeseries(self, active_regions):
        """
        Read historical subregion time series from Data_yearly_Hist.xlsx.

        The sheet is expected to be named "Subregional_division" (fallbacks are
        supported). Only active regions (plus "default") are retained.
        """
        hist_path = Path(self.data.input_manager.sector_paths["hist_path"])
        if not hist_path.exists():
            return

        def read_subregion_sheet(path: Path) -> pd.DataFrame:
            if not path.exists():
                return pd.DataFrame()
            xls = pd.ExcelFile(path)
            sheet_name = SHEET_SUBREGIONAL_DIVISION
            if sheet_name in xls.sheet_names:
                return pd.read_excel(path, sheet_name=sheet_name)
            fallback_sheet = next((s for s in xls.sheet_names if "subregion" in s.lower()), None)
            if fallback_sheet:
                return pd.read_excel(xls, sheet_name=fallback_sheet)
            return pd.DataFrame()

        df = read_subregion_sheet(hist_path)
        if df is None or df.empty:
            return

        def norm_col(name: str) -> str:
            return str(name).strip().lower().replace(" ", "").replace("_", "").replace("/", "")

        def find_col(df, names):
            for col in df.columns:
                if norm_col(col) in names:
                    return col
            return None

        region_col = find_col(df, {"region"})
        subregion_2024_col = find_col(df, {"subregion2024"})
        subregion_col = find_col(df, {"subregion"})
        subregion_name_col = find_col(df, {"subregionname"})
        variable_col = find_col(df, {"variable"})
        if region_col is None or (subregion_col is None and subregion_2024_col is None) or variable_col is None:
            return

        df = df.copy()
        subregion_col_to_use = subregion_2024_col or subregion_col
        df["Region"] = df[region_col].astype(str).str.strip()
        df["Subregion"] = df[subregion_col_to_use].astype(str).str.strip()
        if subregion_name_col is not None:
            df["Subregion_name"] = df[subregion_name_col].astype(str).str.strip()

        if self.data.subregion_aliases:
            alias_map = self.data.subregion_aliases
            df["Subregion"] = df.apply(
                lambda r: alias_map.get((r["Region"], r["Subregion"]), r["Subregion"]), axis=1
            )

        allowed_regions = set(active_regions or [])
        allowed_regions.add("default")
        df = df[df["Region"].isin(allowed_regions)]

        active_subregions = getattr(self.data, "subregions", {}) or {}
        if active_subregions:
            keep_mask = df.apply(
                lambda r: (
                    r["Region"] == "default"
                    or _is_default_like(r.get("Subregion"))
                    or r["Subregion"] in (active_subregions.get(r["Region"]) or {})
                ),
                axis=1,
            )
            df = df.loc[keep_mask]

        self.data.subregion_hist_data = df.reset_index(drop=True)

    def read_subregion_scenario(self, active_regions):
        """
        Read subregion scenario settings from Data_yearly_Scenario.xlsx.

        This captures the distribution-variable configuration (function, forecast
        settings, and long time series right of "Lower limit").
        """
        scen_key = "scen_path" if "scen_path" in self.data.input_manager.sector_paths else "user_set_path"
        scen_path = Path(self.data.input_manager.sector_paths[scen_key])
        if not scen_path.exists():
            return

        def read_subregion_sheet(path: Path) -> pd.DataFrame:
            if not path.exists():
                return pd.DataFrame()
            xls = pd.ExcelFile(path)
            sheet_name = SHEET_SUBREGIONAL_DIVISION
            if sheet_name in xls.sheet_names:
                return pd.read_excel(path, sheet_name=sheet_name)
            fallback_sheet = next((s for s in xls.sheet_names if "subregion" in s.lower()), None)
            if fallback_sheet:
                return pd.read_excel(xls, sheet_name=fallback_sheet)
            return pd.DataFrame()

        df = read_subregion_sheet(scen_path)
        if df is None or df.empty:
            return

        def norm_col(name: str) -> str:
            return str(name).strip().lower().replace(" ", "").replace("_", "").replace("/", "")

        def find_col(df, names):
            for col in df.columns:
                if norm_col(col) in names:
                    return col
            return None

        region_col = find_col(df, {"region"})
        subregion_col = find_col(df, {"subregion", "subregion2024"})
        if region_col is None:
            return
        df = df.copy()
        df["Region"] = df[region_col].astype(str).str.strip()
        if subregion_col is None:
            df["Subregion"] = np.nan
        else:
            df["Subregion"] = df[subregion_col]
        df["Subregion"] = df["Subregion"].astype(str).str.strip()
        df.loc[df["Subregion"].isin({"nan", "None", ""}), "Subregion"] = np.nan

        if self.data.subregion_aliases:
            alias_map = self.data.subregion_aliases
            df["Subregion"] = df.apply(
                lambda r: alias_map.get((r["Region"], r["Subregion"]), r["Subregion"]), axis=1
            )

        allowed_regions = set(active_regions or [])
        allowed_regions.add("default")
        df = df[df["Region"].isin(allowed_regions)]

        active_subregions = getattr(self.data, "subregions", {}) or {}
        if active_subregions:
            keep_mask = df.apply(
                lambda r: (
                    r["Region"] == "default"
                    or _is_default_like(r.get("Subregion"))
                    or r["Subregion"] in (active_subregions.get(r["Region"]) or {})
                ),
                axis=1,
            )
            df = df.loc[keep_mask]

        # Preserve both original raw sheet and a "long" variant used for interpolation points.
        # The loader keeps year columns in-place; downstream uses build_interpolation_points on these rows.
        self.data.subregion_scenario_raw = df.reset_index(drop=True)
        self.data.subregion_scenario_long = df.reset_index(drop=True)


    def attach_region_subregions(self, region):
        """
        Attach subregion metadata and time series to a Region object.

        For each subregion code, this method resolves:
        - historical rows (from hist sheet)
        - scenario rows (raw)
        - long scenario rows (right of "Lower limit")
        It also performs alias mapping and applies defaults when needed.
        """
        region_defs = self.data.subregions.get(region.region_name)
        if not region_defs:
            return

        def _year_cols(df):
            if df is None or df.empty:
                return []
            return [c for c in df.columns if str(c).isdigit()]

        def _template_rows(df, region_name):
            if df is None or df.empty:
                return pd.DataFrame()
            df_region = df[df["Region"] == region_name]
            if df_region.empty:
                df_region = df[df["Region"] == "default"]
            if df_region.empty:
                return pd.DataFrame()
            years = _year_cols(df_region)
            keep = [c for c in df_region.columns if c not in years]
            if "Subregion" in keep:
                keep.remove("Subregion")
            tmpl = df_region[keep].drop_duplicates()
            return tmpl

        def _resolve_rows(df, region_name, subregion_code, templates):
            if df is None or df.empty:
                return pd.DataFrame()
            df_region = select_rows_with_default(
                df=df,
                criteria={"Region": region_name},
                ordered_columns=["Region"],
            )
            if df_region.empty:
                return pd.DataFrame()
            sub_df = select_rows_with_default(
                df=df_region,
                criteria={"Subregion": subregion_code},
                ordered_columns=["Subregion"],
            )
            if not sub_df.empty:
                out_df = sub_df.copy()
                out_df["Region"] = region_name
                out_df["Subregion"] = subregion_code
                return out_df
            if templates is None or templates.empty:
                return pd.DataFrame()
            years = _year_cols(df_region)
            placeholder = templates.copy()
            placeholder["Region"] = region_name
            placeholder["Subregion"] = subregion_code
            for y in years:
                placeholder[y] = np.nan
            return placeholder

        region.subregions = {}
        hist_templates = _template_rows(self.data.subregion_hist_data, region.region_name)
        scen_templates = _template_rows(self.data.subregion_scenario_raw, region.region_name)
        scen_long_templates = _template_rows(self.data.subregion_scenario_long, region.region_name)

        for code, meta in region_defs.items():
            entry = {
                "code": code,
                "name": meta.get("name") or code,
                "hist_data": pd.DataFrame(),
                "scenario_raw": pd.DataFrame(),
                "scenario_long": pd.DataFrame(),
            }
            if not self.data.subregion_hist_data.empty:
                sub_df = _resolve_rows(self.data.subregion_hist_data, region.region_name, code, hist_templates)
                if not sub_df.empty and "Subregion_name" in sub_df.columns and sub_df["Subregion_name"].notna().any():
                    try:
                        entry["name"] = str(sub_df["Subregion_name"].dropna().iloc[0]).strip()
                    except Exception:
                        pass
                entry["hist_data"] = sub_df.reset_index(drop=True)

            if not self.data.subregion_scenario_raw.empty:
                scen_df = _resolve_rows(self.data.subregion_scenario_raw, region.region_name, code, scen_templates)
                entry["scenario_raw"] = scen_df.reset_index(drop=True) if scen_df is not None else pd.DataFrame()

            if not self.data.subregion_scenario_long.empty:
                scen_long_df = _resolve_rows(self.data.subregion_scenario_long, region.region_name, code, scen_long_templates)
                entry["scenario_long"] = scen_long_df.reset_index(drop=True) if scen_long_df is not None else pd.DataFrame()

            region.subregions[code] = entry

        # no debug output

    # --- helper ---
    def _enforce_scenario_timeseries(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Keep only the detected long time-series block.

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
        selected_cols = metadata_cols + long_year_cols
        df2 = df.loc[:, [c for c in selected_cols if c in df.columns]]
        rename_map = {c: parse_year_label(c) for c in long_year_cols if parse_year_label(c) is not None}
        if rename_map:
            df2 = df2.rename(columns=rename_map)
        df2 = df2.loc[:, ~pd.Index(df2.columns).duplicated()]
        return df2



