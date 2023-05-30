from __future__ import annotations

from collections import namedtuple
from enum import Enum

import numpy as np
import pandas as pd

ProductSettings = namedtuple("ProductSettings", ("active", "prod_quant_change", "sub_perc_used"))

class ForecastMethod(Enum):
    LINEAR = 0
    QUADRATIC = 1
    EXPONENTIAL = 2


class ControlParameters:
    general_settings: GeneralSettings
    country_settings: CountrySettings
    industry_settings: IndustrySettings

    def __init__(self, general_settings: GeneralSettings, country_settings: CountrySettings, industry_settings: IndustrySettings):
        self.general_settings = general_settings
        self.country_settings = country_settings
        self.industry_settings = industry_settings


class IndustrySettings:

    forecast_map = {"Trend":ForecastMethod.LINEAR, "U-shape": ForecastMethod.QUADRATIC, "Exponential": ForecastMethod.EXPONENTIAL}

    forecast_method: ForecastMethod
    time_trend_model_activation_quadratic: bool
    production_quantity_calc_per_capita: bool
    trend_calc_for_spec: bool
    h2_subst_of_heat: float
    skip_years: [int]
    last_available_year: int
    products: dict[str, ProductSettings]

    def __init__(self, general_ex: pd.DataFrame, subsectors_ex: pd.DataFrame):
        forecast_method_string = general_ex[general_ex["Parameter"] == "Forecast method"].get("Value")
        self.forecast_method = IndustrySettings.forecast_map[forecast_method_string]

        self.time_trend_model_activation_quadratic = \
            general_ex[general_ex["Parameter"] == "Time trend model activation for U-shape method"].get("Value")

        self.production_quantity_calc_per_capita = \
            general_ex[general_ex["Parameter"] == "Production quantity calculated per capita"].get("Value")

        self.trend_calc_for_spec = \
            general_ex[general_ex["Parameter"] == "Trend calculation for specific energy requirements"].get("Value")

        self.h2_subst_of_heat = \
            general_ex[general_ex["Parameter"] == "H2 substitution of heat"].get("Value")

        skip_years_string = general_ex[general_ex["Parameter"] == "Skip years"].get("Value")
        self.skip_years = [int(i) for i in skip_years_string.split(",")]

        self.last_available_year = \
            general_ex[general_ex["Parameter"] == "Last available year"].get("Value")

        product_list = subsectors_ex.get("Subsectors")

        for product in product_list:
            settings = ProductSettings(False, 0, 100)
            settings.active = \
                subsectors_ex[subsectors_ex["Subsectors"] == product].get("Active subsectors")
            settings.prod_quant_change = \
                subsectors_ex[subsectors_ex["Subsectors"] == product].get("Parameter: production quantity change in %/year")
            sub_perc_used_string = \
                subsectors_ex[subsectors_ex["Subsectors"] == product].get("Parameter: technology substitution in %")
            sub_perc_used_float = float(sub_perc_used_string)
            settings.sub_perc_used = sub_perc_used_float / 100 if sub_perc_used_float != np.NaN else 100


class CountrySettings:
    recognized_countries: [str]
    active_countries: [str]

    def __init__(self, excel: pd.DataFrame):
        self.recognized_countries = excel.get("Country")
        self.active_countries = excel[excel["Active"] == 1].get("Country")
        print(self.active_countries)


class GeneralSettings:

    _sectors_active_values = dict()
    _parameter_values = dict()

    def __init__(self, excel: pd.DataFrame):
        rows_it = pd.DataFrame(excel).itertuples()

        for row in rows_it:
            if row.Parameter.startswith('Sector: '):
                self._sectors_active_values[row.Parameter.removeprefix('Sector: ')] = row.Value
            else:
                self._parameter_values[row.Parameter] = row.Value

    def __str__(self):
        return ("sectors_active_values: " + str(self._sectors_active_values) + "\n" +
                "parameter_values: " + str(self._parameter_values))

    def get_active_sectors(self):
        # returns a list of sectors activated for calculation
        return [sector for (sector, isActive) in self._sectors_active_values.items() if isActive is 1]

    def get_parameter(self, name: str):
        # return the parameter value by parameter name with meaningful error message
        try:
            return self._parameter_values[name]
        except KeyError:
            KeyError("Parameter name not found. Does the parameter access string in the code match a parameter in the Set_and_Control_Parameters.xlsx input table?")