import pandas as pd
import numpy as np
from enum import Enum, auto
from typing import List, Mapping, Tuple, Optional
from endemo2.Input.model_config import META_COLUMNS

"""
This module contains method for the prediction of the processed variable (row) .
"""

class ForecastMethod(Enum):
    LIN = auto()
    EXP = auto()
    LOG = auto()
    LOG_SUM = auto()
    EXP_SUM = auto()
    POWER_SUM = auto()
    BASE_EXP_SUM = auto()
    CONST = auto()
    CONST_MEAN = auto()
    CONST_LAST = auto()
    QUADR = auto()
    POLY = auto()
    CONST_MULT_DIV = auto()
    LIN_MULT_DIV = auto()
    LIN_SHARE = auto()
    EXP_MULT_DIV = auto()
    INTERP_LIN = auto()
    MULT = auto()
    MULT_K0_ZERO = auto()
    USER_FUNCTION = auto()


# Mapping ForecastMethod enum to Excel strings
map_forecast_method_to_string = {
    ForecastMethod.LIN: "lin",
    ForecastMethod.EXP: "exp",
    ForecastMethod.LOG: "log",
    ForecastMethod.LOG_SUM: "log_sum",
    ForecastMethod.EXP_SUM: "exp_sum",
    ForecastMethod.POWER_SUM: "power_sum",
    ForecastMethod.BASE_EXP_SUM: "base_exp_sum",
    ForecastMethod.CONST_MEAN: "const_mean",
    ForecastMethod.CONST_LAST: "const_last",
    ForecastMethod.CONST: "const",
    ForecastMethod.QUADR: "quadr",
    ForecastMethod.POLY: "poly",
    ForecastMethod.LIN_MULT_DIV: "lin_mult_div",
    ForecastMethod.EXP_MULT_DIV: "exp_mult_div",
    ForecastMethod.CONST_MULT_DIV: "const_mult_div",
    ForecastMethod.INTERP_LIN: "interp_lin",
    ForecastMethod.MULT: "mult",
    ForecastMethod.MULT_K0_ZERO: "mult_k0_zero",
    ForecastMethod.LIN_SHARE: "lin_share",
    ForecastMethod.USER_FUNCTION: "user_function",
}

class Method:
    def __init__(self):
        self.name = None  # Method used for forecasting
        self.equation = None  # Holds the regression equation
        self.coefficients: List[float] = []  # Coefficients first element is k0
        self.interp_points = None # A list of known data points (tuples), where each entry is a tuple of coordinates and the function value at that point.
        self.demand_drivers_names = None # list of DDr names used in the method
        self.factor = None # multiplication factor to get the standard units
        self.lower_limit = -np.inf # Lower boundary for the processing variable
        self.upper_limit = np.inf # Upper boundary for the processing variable
        self.ue_type = None
        self.fe_type = None
        self.temp_level = None  # New field
        self.subtech = None  # New field
        self.drive = None

        # efficiency_variable parameters for forecast
        self.efficiency_variable = 0
        self.region = None
        self.sector = None
        self.subsector = None
        self.tech = None

    def save_coef(self, coefficients: List[float], equation: str):
        """
        Save coefficients and the regression equation to the Method object.

        Args:
            coefficients (List[float]): Coefficients for the regression.
            equation (str): Regression equation.
        """
        self.coefficients = coefficients
        self.equation = equation

    def extract_forecast_settings(self, settings_data):
        forecast_method_str = (
            settings_data.iloc[0]['Function'].strip().lower()
            if 'Function' in settings_data.columns else None
        )
        if forecast_method_str is None:
            print(settings_data)
        self.name  = next(
            (method for method, method_str in map_forecast_method_to_string.items()
             if method_str == forecast_method_str),
            None
        )
        if self.name is None and forecast_method_str.startswith("user_"):
            self.name = ForecastMethod.USER_FUNCTION
        self.demand_drivers_names = [
            settings_data.iloc[0][col].strip()
            for col in settings_data.columns
            if col.startswith("DDr") and not pd.isna(settings_data.iloc[0][col])
        ]
        self.factor = (
            settings_data.iloc[0]['Factor']
            if 'Factor' in settings_data.columns else None
        )
        lower_raw = (
            settings_data.iloc[0][META_COLUMNS["LOWER_LIMIT"]]
            if META_COLUMNS["LOWER_LIMIT"] in settings_data.columns else None
        )
        upper_raw = (
            settings_data.iloc[0][META_COLUMNS["UPPER_LIMIT"]]
            if META_COLUMNS["UPPER_LIMIT"] in settings_data.columns else None
        )

        try:
            self.lower_limit = float(lower_raw)
        except (TypeError, ValueError):
            self.lower_limit = -np.inf

        try:
            self.upper_limit = float(upper_raw)
        except (TypeError, ValueError):
            self.upper_limit = np.inf


def base_year(col) -> Optional[str]:
    """
    Normalize a column label to a base year string (e.g. '2100.1' -> '2100').
    Returns None if the column does not represent a year.
    """
    base = str(col).strip().split(".", 1)[0].strip()
    return base if base.isdigit() else None


def extract_year_values(row: Mapping) -> Mapping[str, float]:
    """
    Build a mapping {year_str: value} from a row-like object.
    Prefers the first non-NaN value if duplicate year labels exist.
    """
    year_values = {}
    for col, val in row.items():
        year = base_year(col)
        if year is None:
            continue
        num = pd.to_numeric(val, errors="coerce")
        if year in year_values:
            if pd.isna(year_values[year]) and not pd.isna(num):
                year_values[year] = num
        else:
            year_values[year] = num
    return year_values


def sanitize_interpolation_points(points: List[Tuple[int, float]], atol: float = 1e-12) -> List[Tuple[int, float]]:
    """
    Sanitize interpolation points before forecasting.

    - drops NaN/non-finite values
    - sorts by year
    - keeps one point per year (last non-NaN wins)
    - keeps equal values across different years (needed for piecewise-constant
      segments in linear interpolation)
    """
    if not points:
        return []

    # Keep one value per year (latest non-NaN wins)
    by_year: dict[int, float] = {}
    for year, value in points:
        y = int(year)
        v = pd.to_numeric(value, errors="coerce")
        if pd.isna(v) or not np.isfinite(float(v)):
            continue
        by_year[y] = float(v)

    ordered = sorted(by_year.items(), key=lambda t: t[0])
    return ordered


def select_interpolation_years(row: Mapping) -> List[int]:
    """
    Select interpolation years from a long time series row.
    Only years with non-NaN values are used. No hard-coded year list is applied.
    """
    year_values = extract_year_values(row)
    valid_years = [int(y) for y, v in year_values.items() if not pd.isna(v)]
    return sorted(valid_years)


def build_interpolation_points(row: Mapping) -> List[Tuple[int, float]]:
    """
    Build (year, value) interpolation points from a long time series row.
    Uses select_interpolation_years to pick years (only non-NaN points).
    """
    year_values = extract_year_values(row)
    years = select_interpolation_years(row)
    points: List[Tuple[int, float]] = []
    for y in years:
        val = year_values.get(str(y))
        if pd.isna(val):
            continue
        points.append((int(y), float(val)))
    return sanitize_interpolation_points(points)
