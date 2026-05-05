"""
This Skript reads and validates Model_Settings.xlsx, resolves scenario/input file paths, 
and builds the unified forecast/full-year timeline used by the rest of the model.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from endemo2.Input.loaders.common import (
    parse_year_label,
    extract_years_from_selected_long_block,
)

# --- Metadata column names --- (shared across loaders/forecasts)
# das hier dringend umbauen
META_COLUMNS = {
    "FORECAST_DATA": "Forecast data",
    "FUNCTION": "Function",
    "EQUATION": "Equation",
    "UNIT": "Unit",
    "FACTOR": "Factor",
    "LOWER_LIMIT": "Lower limit",
    "UPPER_LIMIT": "Upper limit",
}

# Fallback full-year range (runtime values are determined dynamically) 
DEFAULT_FULL_YEAR_START = 1960
DEFAULT_FULL_YEAR_END = 2100

# Sheet names 
SHEET_DEMAND_DRIVERS = "Demand_Drivers"
SHEET_SUBREGIONAL_DIVISION = "Subregional_division"
SHEET_HOURLY = "Data"

# Input file names / patterns 
FILE_YEARLY_HIST = "Data_yearly_Hist.xlsx"
FILE_YEARLY_SCENARIO = "Data_yearly_Scenario.xlsx"
FILE_YEARLY_SCENARIO_TEMPLATE = "Data_yearly_Scenario_{scenario}.xlsx"
FILE_HOURLY = "Data_hourly.xlsx"


class ControlParameters:
    """Container that exposes parsed global settings to the rest of the model."""

    def __init__(self, gen_settings: "GeneralSettings"):
        # Store one shared settings object (already parsed from the control workbook).
        self.gen_settings = gen_settings


class GeneralSettings:
    """Read, validate, and normalize all runtime settings from Model_Settings.xlsx."""

    def __init__(self, ctrl_ex):
        # Load global control sheet and keep a fast key->value lookup.
        self.general_set = pd.read_excel(ctrl_ex, sheet_name="GeneralSet")
        self.general_set.columns = self.general_set.columns.map(str)
        self.general_set_map = self.build_general_set_map(self.general_set)

        # Load the key activation/configuration sheets.
        sectors_df = pd.read_excel(ctrl_ex, sheet_name="Sectors")
        regions_df = pd.read_excel(ctrl_ex, sheet_name="Regions")
        energy_types_df = self._read_energy_types_sheet(ctrl_ex)

        # Resolve active sectors/regions from flexible "Activate/Active/Value" columns.
        self.active_sectors = self._get_active_items(
            sectors_df, label_col="Sector", active_candidates=["Activate", "Active", "Value"]
        )
        self.active_regions = self._get_active_items(
            regions_df, label_col="Region", active_candidates=["Activate", "Active", "Value"]
        )

        self.region_names_yearly_output = self._get_param("Region names in yearly output")
        self.region_names_timeseries_output = self._get_param("Region names in timeseries output")
        code_col = find_region_code_column(regions_df, self.region_names_timeseries_output)
        if code_col is None:
            self.region_code_map = {r: r for r in self.active_regions}
        else:
            region_codes = regions_df.set_index("Region")[code_col].to_dict()
            self.region_code_map = {r: region_codes.get(r, r) for r in self.active_regions}

        self.active_subsectors = {}
        self.forecast_year_range = self.get_forecast_year_range()
        self.full_year_start = DEFAULT_FULL_YEAR_START
        self.full_year_end = DEFAULT_FULL_YEAR_END
        self.full_year_range = range(self.full_year_start, self.full_year_end + 1)
        self.UE_marker = self._get_param("Useful energy demand")
        self.FE_marker = self._get_param("Final energy demand")
        self.timeseries_forecast = self._get_param("Timeseries forecast")
        self.timeseries_per_region = self._get_param("Timeseries output per sector")
        self.timeseries_csv = self._get_param("Output hourly in .cvs format")
        self.graphical_out = self._get_param("Graphical output")
        self.trace_output = self._get_param("Trace")
        self.scenario = self._get_param("Scenario")
        self.subregional_resolution = self._get_param("Subregional geographical resolution")

        self.sectors_settings = self.read_active_sector_settings(ctrl_ex)
        self.useful_energy_types, self.heat_levels, self.final_energy_types = (
            self._parse_energy_types(energy_types_df)
        )

    def build_general_set_map(self, general_set: pd.DataFrame) -> dict:
        """Create a dict-based lookup for GeneralSet parameters."""
        if general_set is None or general_set.empty:
            return {}
        if "Parameter" not in general_set.columns or "Value" not in general_set.columns:
            return {}
        cleaned = general_set[["Parameter", "Value"]].copy()
        cleaned = cleaned.dropna(subset=["Parameter"])
        cleaned["Parameter"] = cleaned["Parameter"].astype(str).str.strip()
        return cleaned.set_index("Parameter")["Value"].to_dict()

    def _get_param(self, key: str, default=None):
        """Read one parameter from GeneralSet with fallback handling."""
        if self.general_set_map and key in self.general_set_map:
            value = self.general_set_map.get(key)
            if not pd.isna(value):
                return value
        if self.general_set is not None and not self.general_set.empty:
            rows = self.general_set[self.general_set["Parameter"] == key]
            if not rows.empty and "Activate" in rows.columns:
                act = rows.iloc[0].get("Activate")
                if not pd.isna(act):
                    return act
        return default

    def _get_active_items(self, df: pd.DataFrame, label_col: str, active_candidates: list[str]) -> list[str]:
        """Return labels of rows marked active in a sheet."""
        if df is None or df.empty or label_col not in df.columns:
            return []
        active_col = select_first_available_column(df, active_candidates)
        if active_col is None:
            return []
        active_mask = df[active_col].apply(is_truthy)
        return df.loc[active_mask, label_col].dropna().astype(str).tolist()

    def get_forecast_year_range(self) -> range:
        """Build the forecast year range from start/end/step settings."""
        forecast_year_start = self._get_param("Forecast year start")
        forecast_year_end = self._get_param("Forecast year end")
        forecast_year_step = self._get_param("Forecast year step")
        if forecast_year_start is None or forecast_year_end is None or forecast_year_step is None:
            raise ValueError(
                "Missing forecast settings in GeneralSet: "
                "'Forecast year start', 'Forecast year end', and 'Forecast year step' must be set."
            )
        return range(int(forecast_year_start), int(forecast_year_end) + 1, int(forecast_year_step))

    def read_active_sector_settings(self, ctrl_ex):
        """Read active subsector rows for each active sector sheet."""
        if not isinstance(ctrl_ex, pd.ExcelFile):
            ctrl_ex = pd.ExcelFile(ctrl_ex)
        sectors_settings = {}
        for sector_name in self.active_sectors:
            sheet_name = f"{sector_name}_subsectors"
            if sheet_name in ctrl_ex.sheet_names:
                try:
                    df = pd.read_excel(ctrl_ex, sheet_name=sheet_name)
                    active_col = select_first_available_column(df, ["Activate", "Active", "Value"])
                    if active_col is None:
                        df = df.iloc[0:0]
                    else:
                        df = df[df[active_col].apply(is_truthy)]
                    df = df.set_index("Subsector")
                    sectors_settings[sector_name] = df
                    self.active_subsectors[sector_name] = df.index.tolist()
                except Exception as e:
                    print(f"Error reading sheet {sheet_name}: {e}")
            else:
                print(f"Sheet {sheet_name} not found in control file. No data for {sector_name}.")
        return sectors_settings

    def _read_energy_types_sheet(self, ctrl_ex):
        """Load the Energy_Types sheet and enforce that it exists."""
        try:
            return pd.read_excel(ctrl_ex, sheet_name="Energy_Types")
        except Exception:
            raise ValueError("Missing required sheet 'Energy_Types' in Model_Settings.xlsx")

    def _parse_energy_types(self, df: pd.DataFrame):
        """Parse and validate UE/heat/FE type lists from Energy_Types."""
        if df is None or df.empty:
            raise ValueError("Sheet 'Energy_Types' is empty.")

        required_cols = [
            "Useful Energy Types",
            "Heat levels",
            "Final Energy Types",
        ]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Energy_Types: missing required column '{col}'.")

        def read_list(col):
            values = df[col].dropna().astype(str).tolist()
            values = [v.strip() for v in values if v.strip()]
            seen = set()
            unique = []
            for v in values:
                if v not in seen:
                    seen.add(v)
                    unique.append(v)
            return unique

        useful = read_list("Useful Energy Types")
        heat = read_list("Heat levels")
        fe = read_list("Final Energy Types")
        if not useful:
            raise ValueError("Energy_Types: column 'Useful Energy Types' is empty.")
        if not heat:
            raise ValueError("Energy_Types: column 'Heat levels' is empty.")
        if not fe:
            raise ValueError("Energy_Types: column 'Final Energy Types' is empty.")
        return useful, heat, fe


class InputManager:
    """
    Manage Excel input sheets and expose parsed control settings.
    """

    super_path = Path(os.path.abspath(""))
    input_path = super_path / "input"
    output_path = super_path / "output"
    ctrl_file = input_path / "Model_Settings.xlsx"
    timeseries_file = input_path / FILE_HOURLY

    def __init__(self):
        # Load control settings and resolve concrete input workbook paths.
        self.ctrl: ControlParameters = InputManager.read_control_parameters()
        self.general_settings = self.ctrl.gen_settings
        self.sector_paths = self.get_data_paths()
        # Determine model-wide full year range from actual input year columns.
        self.set_dynamic_full_year_range()

    def get_data_paths(self):
        """Resolve historical/scenario workbook paths based on selected scenario."""
        scenario_value = (self.general_settings.scenario or "").strip()
        scenario_file = self.input_path / FILE_YEARLY_SCENARIO
        if scenario_value:
            cleaned = scenario_value.replace(" ", "")
            candidate = self.input_path / FILE_YEARLY_SCENARIO_TEMPLATE.format(scenario=cleaned)
            if candidate.exists():
                scenario_file = candidate
            else:
                candidate_upper = self.input_path / FILE_YEARLY_SCENARIO_TEMPLATE.format(scenario=cleaned.upper())
                if candidate_upper.exists():
                    scenario_file = candidate_upper
        sector_paths = {
            "hist_path": self.input_path / FILE_YEARLY_HIST,
            "user_set_path": scenario_file,
        }
        return sector_paths

    @classmethod
    def read_control_parameters(cls) -> ControlParameters:
        """Read and parse Model_Settings.xlsx into ControlParameters."""
        ctrl_ex = pd.ExcelFile(cls.ctrl_file)
        gen_settings = GeneralSettings(ctrl_ex)
        return ControlParameters(gen_settings)

    @staticmethod
    def parse_year_from_column(col) -> Optional[int]:
        """Return an integer year from a column label, if present."""
        base = parse_year_label(col)
        if base is not None:
            return int(base)
        return None

    def extract_years_from_workbook(self, path: Path) -> set[int]:
        """Collect year columns from the detected long year block of each sheet."""
        if not path.exists():
            return set()
        years: set[int] = set()
        xls = pd.ExcelFile(path)
        for sheet in xls.sheet_names:
            try:
                cols = pd.read_excel(xls, sheet_name=sheet, nrows=0).columns
            except Exception:
                continue
            cols_list = list(cols)
            long_block_years = extract_years_from_selected_long_block(cols_list)
            if long_block_years:
                years.update(long_block_years)
                continue
            # Fallback for sheets without a clear long block.
            for col in cols_list:
                year = self.parse_year_from_column(col)
                if year is not None:
                    years.add(year)
        return years

    def set_dynamic_full_year_range(self):
        """Set full_year_range dynamically from historical min year to scenario max year."""
        hist_path = Path(self.sector_paths["hist_path"])
        scen_key = "scen_path" if "scen_path" in self.sector_paths else "user_set_path"
        scen_path = Path(self.sector_paths[scen_key])

        hist_years = self.extract_years_from_workbook(hist_path)
        scen_years = self.extract_years_from_workbook(scen_path)

        if not hist_years:
            raise ValueError(
                f"Could not determine first year from historical workbook '{hist_path.name}'. "
                "At least one year column is required."
            )
        if not scen_years:
            raise ValueError(
                f"Could not determine last year from scenario workbook '{scen_path.name}'. "
                "At least one year column is required."
            )

        full_start = min(hist_years)
        full_end = max(scen_years)
        if full_start > full_end:
            raise ValueError(
                f"Invalid dynamic full-year range: start year {full_start} is greater than end year {full_end}."
            )

        self.general_settings.full_year_start = int(full_start)
        self.general_settings.full_year_end = int(full_end)
        self.general_settings.full_year_range = range(full_start, full_end + 1)
def norm(col: str) -> str:
    """Normalize text keys for robust column-name matching."""
    return str(col).strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def is_truthy(val) -> bool:
    """Interpret common truthy markers used in Excel control sheets."""
    if pd.isna(val):
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "y", "x", "wahr", "ja"}
    return False


def select_first_available_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return first existing candidate column name (preferring non-empty columns)."""
    if df is None or df.empty:
        return None
    normalized = {norm(c): c for c in df.columns}
    for cand in candidates:
        col = normalized.get(norm(cand))
        if col is not None and df[col].notna().any():
            return col
    for cand in candidates:
        col = normalized.get(norm(cand))
        if col is not None:
            return col
    return None


def find_region_code_column(df: pd.DataFrame, preference: str | None) -> str | None:
    """Choose the region-code column (2-letter/3-letter/full-name) based on user preference."""
    pref = (preference or "").strip().lower()
    candidates = []
    if "2" in pref and "letter" in pref:
        candidates = ["2-letter code", "2lettercode", "iso2", "code2"]
    elif "3" in pref and "letter" in pref:
        candidates = ["3-letter code", "3lettercode", "iso3", "code3"]
    elif "full" in pref or "region" in pref:
        return None
    else:
        candidates = ["code", "2-letter code", "3-letter code", "2lettercode", "3lettercode"]
    return select_first_available_column(df, candidates)
