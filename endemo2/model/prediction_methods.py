"""
This module contains method for the prediction of the processed variable (row) .
"""
import pandas as pd
from typing import List
from endemo2.data_structures.conversions_string import  map_forecast_method_to_string

class Method:
    def __init__(self):
        self.name = None  # Method used for forecasting
        self.equation = None  # Holds the regression equation
        self.coefficients: List[float] = []  # Coefficients first element is k0
        self.interp_points = None # A list of known data points (tuples), where each entry is a tuple of coordinates and the function value at that point.
        self.demand_drivers_names = None # list of DDr names used in the method
        self.factor = None # multiplication factor to get the standard units
        self.lower_limit = None # Lower boundary for the processing variable
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
        self.demand_drivers_names = [
            settings_data.iloc[0][col].strip()
            for col in settings_data.columns
            if col.startswith("DDr") and not pd.isna(settings_data.iloc[0][col])
        ]
        self.factor = (
            settings_data.iloc[0]['Factor']
            if 'Factor' in settings_data.columns else None
        )
        self.lower_limit = float((
            settings_data.iloc[0]['Lower limit']
            if 'Lower limit' in settings_data.columns else None
        ))
