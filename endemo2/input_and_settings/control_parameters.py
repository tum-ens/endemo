"""
This module contains the in-model representation of all settings found in Set_and_Control_Parameters.xlsx
"""
from __future__ import annotations
import pandas as pd

class ControlParameters:
    """
    The ControlParameter class holds the data given by the Set_and_Control_Parameters.xlsx file.
    It is split in general settings, and settings for each sector, indicating non-overlapping parameters for our model.

    :ivar GeneralSettings general_settings: The settings contained in the "GeneralSettings"-sheet.
    :ivar IndustrySettings industry_settings: The settings contained in the "IND_*"-sheets.
    """

    def __init__(self, gen_settings: GeneralSettings,):
        self.gen_settings = gen_settings

class GeneralSettings:
    """
        The GeneralSettings contain the parameters for the model given in Set_and_Control_Parameters.xlsx in the
        GeneralSettings and Countries sheets, as well as the additional UE_Set and UE->FE sheets.

        :param ctrl_ex: The Excel file Set_and_Control_Parameters.xlsx

        """

    def __init__(self, ctrl_ex):

        self.active_sectors = pd.read_excel(ctrl_ex, sheet_name="Sectors").query("Value == True")["Sector"].tolist() # it is the list of active sectors
        self.general_set =  pd.read_excel(ctrl_ex, sheet_name="GeneralSet")  # contain a df of parameters Sheet name General_set
        self.active_regions = pd.read_excel(ctrl_ex, sheet_name="Regions").query("Active == True")["Region"].tolist()
        self.region_code_map = pd.read_excel(ctrl_ex, sheet_name="Regions").query("Active == True").set_index("Region")[
            "Code"].to_dict()
        self.active_subsectors = {}

        # Extract forecast-related parameters
        self.forecast_year_range = self.get_forecast_year_range(self.general_set)

        self.UE_marker = self.general_set.query("Parameter == 'Useful energy demand'")["Value"].values[0]
        self.FE_marker = self.general_set.query("Parameter == 'Final energy demand'")["Value"].values[0]
        self.timeseries_forecast = self.general_set.query("Parameter == 'Timeseries forecast'")["Value"].values[0]
        self.timeseries_per_region = self.general_set.query("Parameter == 'Timeseries output per sector'")["Value"].values[0]
        self.graphical_out = self.general_set.query("Parameter == 'Graphical output'")["Value"].values[0]

        self.dropdown_settings = pd.read_excel(ctrl_ex, sheet_name="Dropdown_lists")
        self.sectors_settings = self.read_active_sector_settings(ctrl_ex)

    def get_forecast_year_range(self, general_set) -> range:
        """
        Retrieve the range of years for the forecast.
        :return: A range object representing the forecast years.
        """
        forecast_year_start = general_set.query("Parameter == 'Forecast year start'")["Value"].values[0]
        forecast_year_end = general_set.query("Parameter == 'Forecast year end'")["Value"].values[0]
        forecast_year_step = general_set.query("Parameter == 'Forecast year step'")["Value"].values[0]
        return range(forecast_year_start, forecast_year_end + 1, forecast_year_step)

    def read_active_sector_settings(self,ctrl_ex):
        ctrl_ex = pd.ExcelFile(ctrl_ex)
        sectors_settings = {}
        for sector_name in self.active_sectors:
            sheet_name = f"{sector_name}_subsectors"
            if sheet_name in ctrl_ex.sheet_names:
                try:
                    # Read the sheet and store only rows where 'Active' is True
                    df = pd.read_excel(ctrl_ex, sheet_name=sheet_name)
                    df = df[df['Active'] == True] # this ensures that we are processing only active subsecors
                    df = df.set_index('Subsector')
                    sectors_settings[sector_name] = df
                    self.active_subsectors[sector_name] = df.index.tolist()
                except Exception as e:
                    print(f"Error reading sheet {sheet_name}: {e}")
            else:
                print(f"Sheet {sheet_name} not found in control file. No data for {sector_name}.")
        return sectors_settings
