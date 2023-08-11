"""
This module contains the in-model representation of all settings found in Set_and_Control_Parameters.xlsx
"""

from __future__ import annotations
from collections import namedtuple
import pandas as pd

from endemo2.data_structures.containers import Heat
from endemo2.data_structures.enumerations import ForecastMethod, SectorIdentifier, DemandType

ProductSettings = \
    namedtuple("ProductSettings", ("active", "manual_exp_change_rate", "perc_used", "efficiency_improvement"))


class ControlParameters:
    """
    The ControlParameter class holds the data given by the Set_and_Control_Parameters.xlsx file.
    It is split in general settings, and settings for each sector, indicating non-overlapping parameters for our model.

    :ivar GeneralSettings general_settings: The settings contained in the "GeneralSettings"-sheet.
    :ivar IndustrySettings industry_settings: The settings contained in the "IND_*"-sheets.
    """

    def __init__(self, general_settings: GeneralSettings, industry_settings: IndustrySettings):
        self.general_settings = general_settings
        self.industry_settings = industry_settings


class GeneralSettings:
    """
    The GeneralSettings contain the parameters for the model given in Set_and_Control_Parameters.xlsx in the
    GeneralSettings and Countries sheets.

    :param pd.DataFrame ex_general: The dataframe of the "GeneralSettings"-sheet in Set_and_Control_Parameters.xlsx
    :param pd.DataFrame ex_country: The dataframe of the "Countries"-sheet in Set_and_Control_Parameters.xlsx

    :ivar dict[str, bool] _sectors_active_values: Contains information, whether a sector is activ,
        as indicated by the settings.
    :ivar dict[str, bool] _parameter_values: Holds the values from the GeneralSettings
        table in a dictionary {Parameter_string -> bool}

    :ivar int target_year: This is the year, the model makes predictions for.
    :ivar [str] recognized_countries:
        This is the list of countries_in_group that are in the "Countries"-sheet of Set_and_Control_Parameters.xlsx
    :ivar [str] active_countries: This is the list of active countries_in_group.
        Only for these countries_in_group, calculations are performed.
    :ivar int nuts2_version: The version of NUTS2 used for reading the files that hold information per NUTS2 Region.
        Currently, it should be either 2016 or 2021.
    :ivar bool toggle_hourly_forecast: Indicates whether to distribute demand over hours according to load profiles.
    :ivar bool toggle_nuts2_resolution: Indicates whether to distribute demand over nuts2 regions.
    :ivar bool toggle_graphical_output: Indicates whether to generate visual output.
    """

    sector_id_map = {"Sector: industry": SectorIdentifier.INDUSTRY,
                     "Sector: households": SectorIdentifier.HOUSEHOLDS,
                     "Sector: transport": SectorIdentifier.TRANSPORT,
                     "Sector: commertial, trade, services": SectorIdentifier.COMMERCIAL_TRADE_SERVICES}

    def __init__(self, ex_general: pd.DataFrame, ex_country: pd.DataFrame):
        self._sectors_active_values = dict()
        self._parameter_values = dict()
        self.target_year = int(ex_general[ex_general["Parameter"] == "Forecast year"].get("Value").iloc[0])
        self.recognized_countries = ex_country.get("Country")
        self.active_countries = list(ex_country[ex_country["Active"] == 1].get("Country"))
        self.nuts2_version = int(ex_general[ex_general["Parameter"] == "NUTS2 classification"].get("Value").iloc[0])

        self.toggle_hourly_forecast = ex_general[ex_general["Parameter"] == "Timeseries forecast"].get("Value").iloc[0]
        self.toggle_nuts2_resolution = \
            ex_general[ex_general["Parameter"] == "NUTS2 geographical resolution"].get("Value").iloc[0]
        self.toggle_graphical_output = ex_general[ex_general["Parameter"] == "Graphical output"].get("Value").iloc[0]

        rows_it = pd.DataFrame(ex_general).itertuples()
        for row in rows_it:
            if row.Parameter.startswith('Sector: '):
                self._sectors_active_values[GeneralSettings.sector_id_map[row.Parameter]] = row.Value
            else:
                self._parameter_values[row.Parameter] = row.Value

    def __str__(self):
        return ("sectors_active_values: " + str(self._sectors_active_values) + "\n" +
                "parameter_values: " + str(self._parameter_values))

    def get_active_sectors(self) -> [SectorIdentifier]:
        """
        :return: The list of sectors_to_do activated for calculation.
        """
        return [sector for (sector, isActive) in self._sectors_active_values.items() if isActive]

    def get_parameter(self, name: str):
        """
        :return: The parameter value by parameter name with meaningful error message.
        """
        try:
            return self._parameter_values[name]
        except KeyError:
            KeyError(
                "Parameter name not found. Does the parameter access string in the code match a parameter in the "
                "Set_and_Control_Parameters.xlsx preprocessing table?")


class IndustrySettings:
    """
    The IndustrySettings contain the parameters for the model given in Set_and_Control_Parameters.xlsx in the
    IND_general and IND_subsectors sheets.

    :ivar dict[str, ForecastMethod] forecast_map: Maps the forecast method string, used in the setting tables,
        to the internal enum representation.
    :ivar ForecastMethod forecast_method: Contains the currently selected forecast method.
    :ivar bool time_trend_model_activation_quadratic:
        "If the time trend model is deactivated, the traditional approach is selected"
    :ivar bool production_quantity_calc_per_capita:
        Decides, whether the production quantity prognosis should use per-capita projection.
    :ivar bool trend_calc_for_spec:
        Decides, whether specific consumption should be predicted from historical data, when available.
    :ivar bool nuts2_distribution_based_on_installed_ind_capacity: "If false, distribution per population density."
    :ivar [int] skip_years: Years that are skipped while reading files, to remove outliers.
    :ivar int last_available_year: Last year that's read from historical production files (exclusive).
    :ivar dict[str, ProductSettings] product_settings: Contains settings for each product.
        Of the form {product_name -> product_settings_obj}
    :ivar [str] active_product_names: A list of the names of active products.
        Only for these products, calculations are performed.
    :ivar float rest_sector_growth_rate: The growth rate of the rest sector.
    :ivar bool use_gdp_as_x: Indicates that prediction x-axis should be gdp instead of time.
    :ivar dict[DemandType, Heat] heat_substitution: The percentage/100 of heat that is substituted by another
        demand type.
    """
    forecast_map = dict({"Linear time trend": ForecastMethod.LINEAR,
                         "Linear GDP function": ForecastMethod.LINEAR,
                         "Quadratic GDP function": ForecastMethod.QUADRATIC,
                         "Exponential": ForecastMethod.EXPONENTIAL})

    def __init__(self, df_general: pd.DataFrame, df_subsectors: pd.DataFrame):
        self.product_settings = dict()
        self.active_product_names = []
        forecast_method_string = df_general[df_general["Parameter"] == "Forecast method"].get("Value").iloc[0]
        self.forecast_method = IndustrySettings.forecast_map[forecast_method_string]
        self.use_gdp_as_x = True if "GDP" in forecast_method_string else False

        self.time_trend_model_activation_quadratic = \
            df_general[df_general["Parameter"] == "Time trend model activation for U-shape method"].get("Value").iloc[0]

        self.production_quantity_calc_per_capita = \
            df_general[df_general["Parameter"] == "Production quantity calculated per capita"].get("Value").iloc[0]

        self.trend_calc_for_spec = \
            df_general[df_general["Parameter"] == "Trend calculation for specific energy requirements"].get(
                "Value").iloc[0]

        self.nuts2_distribution_based_on_installed_ind_capacity = \
            df_general[df_general["Parameter"] == "NUTS2 distribution based on installed industrial capacity"].get(
                "Value").iloc[0]

        skip_years_string = str(df_general[df_general["Parameter"] == "Skip years"].get("Value").iloc[0])
        self.skip_years = [int(i) for i in skip_years_string.split(",")]

        self.last_available_year = \
            df_general[df_general["Parameter"] == "Last available year"].get("Value").iloc[0]

        self.rest_sector_growth_rate = \
            df_subsectors[df_subsectors["Subsectors"] == "unspecified industry"].get(
                "Parameter: production quantity change in %/year").iloc[0]

        # read substitution of heat by electricity and hydrogen
        self.heat_substitution = dict[DemandType, Heat]()
        str1 = "Proportion of "
        str2 = " usage for heat supply at "
        str3 = " level"
        str_electricity = str1 + "electricity" + str2
        self.heat_substitution[DemandType.ELECTRICITY] = \
            Heat(df_general[df_general["Parameter"] == str_electricity + "Q1" + str3].get("Value").iloc[0],
                 df_general[df_general["Parameter"] == str_electricity + "Q2" + str3].get("Value").iloc[0],
                 df_general[df_general["Parameter"] == str_electricity + "Q3" + str3].get("Value").iloc[0],
                 df_general[df_general["Parameter"] == str_electricity + "Q4" + str3].get("Value").iloc[0])
        str_hydrogen = str1 + "hydrogen" + str2
        self.heat_substitution[DemandType.HYDROGEN] = \
            Heat(df_general[df_general["Parameter"] == str_hydrogen + "Q1" + str3].get("Value").iloc[0],
                 df_general[df_general["Parameter"] == str_hydrogen + "Q2" + str3].get("Value").iloc[0],
                 df_general[df_general["Parameter"] == str_hydrogen + "Q3" + str3].get("Value").iloc[0],
                 df_general[df_general["Parameter"] == str_hydrogen + "Q4" + str3].get("Value").iloc[0])

        product_list = df_subsectors.get("Subsectors")
        for product in product_list:
            if product == "unspecified industry":
                continue
            active = \
                df_subsectors[df_subsectors["Subsectors"] == product].get(
                    "Active subsectors").iloc[0]
            prod_quant_change = \
                df_subsectors[df_subsectors["Subsectors"] == product].get(
                    "Parameter: production quantity change in %/year").iloc[0]
            sub_perc_used_string = \
                df_subsectors[df_subsectors["Subsectors"] == product].get(
                    "Parameter: technology substitution in %").iloc[0]
            try:
                sub_perc_used_float = float(sub_perc_used_string)
                sub_perc_used = sub_perc_used_float / 100
            except ValueError:
                sub_perc_used = 1
            efficiency_improvement_string = \
                df_subsectors[df_subsectors["Subsectors"] == product].get(
                    "Parameter: efficiency improvement in %/year").iloc[0]
            try:
                efficiency_improvement_float = float(efficiency_improvement_string)
                efficiency_improvement = efficiency_improvement_float / 100
            except ValueError:
                efficiency_improvement = 1

            self.product_settings[product] = \
                ProductSettings(active, prod_quant_change, sub_perc_used, efficiency_improvement)

            if self.product_settings[product].active:
                self.active_product_names.append(product)
