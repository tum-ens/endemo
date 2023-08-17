from pathlib import Path
from typing import Any

import pandas as pd

from endemo2 import utility as uty
from endemo2.data_structures.containers import Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.input_and_settings.input_general import Abbreviations
from endemo2.input_and_settings.input_utility import skip_years_in_df, read_energy_carrier_consumption_historical


class CtsInput:
    """
    CtsInput denoted input that is read from the "input/industry" folder.

    :param ControlParameters ctrl: The control parameters object.
    :param Path cts_path: The path to the input files for the CTS sector.

    :ivar dict[str, dict[str, [(float, float)] dict_employee_number_country: Contains the number ob employees per
        subsector for every country. Is of form {country_name -> {subsector -> [(float, float)]}}
    :ivar dict[str, dict[str, dict[str, [(float, float)]] dict_employee_number_nuts2: Contains the number ob employees
        per subsector for every NUTS2 region. Is of form
        {country_name -> {nuts2_region -> {subsector -> [(float, float)]}}}
    :ivar dict[str, [(float, float)]] dict_employee_number_country_cts: Contains the number of employees in the whole
        cts sector.
    :ivar dict[str, [(float, float)]] energy_carrier_consumption: The historical quantity of energy carrier in
        subsector. Of form: {country_name -> {energy_carrier -> [(float, float)]}}
    :ivar dict[DemandType, Any] load_profile: The load profile for the cts sector.
    """

    subsector_names = [  # "Land- und Forstwirtschaft, Fischerei", ???
        "Groß- und Einzelhandel",
        "Private Büros",
        "Hotel und Restaurants",
        "Öffentliche Büros",
        "Gesundheits- und Sozialwesen",
        "Bildung",
        "Sonstige"]

    def __init__(self, ctrl: ControlParameters, cts_path: Path):

        # read per country per subsector employee numbers
        self.dict_employee_number_country = \
            dict([(Abbreviations.dict_alpha2_en_map[code], content) for (code, content) in
                  self.read_employee_per_subsector(ctrl,
                                                   cts_path / "Employee_Nuts0.xlsx", "Employee_per_sector").items()
                  if code in Abbreviations.dict_alpha2_en_map.keys()])  # if code is from an active country

        # read per nuts2 region per subsector employee numbers
        dict_employee_number_nuts2_unstructured = \
            self.read_employee_per_subsector(ctrl, cts_path / "Employee_Nuts2.xlsx", "Employee_per_sector")
        self.dict_employee_number_nuts2 = \
            dict[str, dict[str, dict[str]]]()  # country_name -> nuts2_region -> subsector -> [(float, float)]
        for region_name, dict_subsec_data in dict_employee_number_nuts2_unstructured.items():
            if region_name[:2] not in Abbreviations.dict_alpha2_en_map.keys():
                # skip inactive countries
                continue
            country_name = Abbreviations.dict_alpha2_en_map[region_name[:2]]
            if country_name not in self.dict_employee_number_nuts2.keys():
                self.dict_employee_number_nuts2[country_name] = dict()
            self.dict_employee_number_nuts2[country_name][region_name] = dict_subsec_data

        # read total number of employees per country (for specific consumption calculation)
        self.dict_employee_number_country_cts = \
            CtsInput.read_number_employees_cts(ctrl, cts_path / "Employee_Nuts0.xlsx", "Raw data Eurostat")

        # read energy carrier historical data
        self.energy_carrier_consumption = \
            read_energy_carrier_consumption_historical(cts_path, "nrg_bal_s_GHD.xls")

        # read load profile
        if ctrl.general_settings.toggle_hourly_forecast:
            df_load_profile = pd.read_excel(cts_path / "CTS_Loadprofile.xlsx", sheet_name="Data")

            electricity = list(df_load_profile["Elec"])[1:]
            heat_q1 = list(df_load_profile["Heat_Q1"])[1:]
            heat_q2 = list(df_load_profile["Heat_Q2"])[1:]
            h2 = list(df_load_profile["H2"])[1:]

            self.load_profile = dict[DemandType, Any]()
            self.load_profile[DemandType.ELECTRICITY] = electricity
            self.load_profile[DemandType.HEAT] = [Heat(q1, q2) for q1, q2 in zip(heat_q1, heat_q2)]
            self.load_profile[DemandType.HYDROGEN] = h2
        else:
            self.load_profile = None

    @classmethod
    def read_number_employees_cts(cls, ctrl: ControlParameters, path_to_file: Path, sheet_name: str) \
            -> dict[str, [(float, float)]]:
        """
        Reads employees per subsector from the eurostats input sheets.

        :param ctrl: The control Parameters
        :param path_to_file: Path of the file that should be read.
        :param sheet_name: The name of the sheet that should be read.
        :return: The data on number of employees (in thousands) in the whole cts sector of a country.
            Is of form {country_name -> data}.
        """
        df_employee_num = pd.read_excel(path_to_file, sheet_name)

        # skip years
        skip_years_in_df(df_employee_num, ctrl.cts_settings.skip_years)

        dict_employee_number = dict[str, dict[str]]()  # country_name -> subsector -> [(float, float)]
        years = df_employee_num.columns[2:]
        for _, row in df_employee_num.iterrows():
            # only take the GUD lines and skip everything else
            if row["NACE_R2 (Codes)"] != "GHD":
                continue
            alpha2 = row["Country"].strip()
            if alpha2 not in Abbreviations.dict_alpha2_en_map.keys():
                # inactive country, skip
                continue
            country_name = Abbreviations.dict_alpha2_en_map[row["Country"].strip()]

            # get values over time
            data = row[2:]
            zipped = list(zip(years, data))
            his_data = uty.filter_out_nan_and_inf(zipped)
            his_data = uty.cut_after_x(his_data, ctrl.cts_settings.last_available_year - 1)

            # save
            dict_employee_number[country_name] = his_data

        return dict_employee_number

    @classmethod
    def read_employee_per_subsector(cls, ctrl, path_to_file: Path, sheet_name: str) \
            -> dict[str, dict[str]]():
        """
        Reads employees per subsector from the Employee...xlsx input sheets

        :param ctrl: The control Parameters
        :param path_to_file: Path of the file that should be read.
        :param sheet_name: The name of the sheet that should be read.
        :return: The data on number of employees in each subsector of form {region_name -> {subsector_name -> data}},
            where region_name can be a country or a nuts2 region, depending on input file.
        """
        df_employee_num_per_subsector = pd.read_excel(path_to_file, sheet_name)

        # skip years
        skip_years_in_df(df_employee_num_per_subsector, ctrl.cts_settings.skip_years)

        dict_employee_number = dict[str, dict[str]]()  # country_name -> subsector -> [(float, float)]
        years = df_employee_num_per_subsector.columns[4:]
        for _, row in df_employee_num_per_subsector.iterrows():
            region_column = "Land" if "Land" in df_employee_num_per_subsector.columns else "NUTS2"
            region_name = row[region_column].strip()
            subsector = row["Sektor"]

            # get values over time
            data = row[4:]
            zipped = list(zip(years, data))
            his_data = uty.filter_out_nan_and_inf(zipped)
            his_data = uty.map_data_y(his_data, lambda x: x * 1000)
            his_data = uty.cut_after_x(his_data, ctrl.cts_settings.last_available_year - 1)

            # save
            if region_name not in dict_employee_number.keys():
                dict_employee_number[region_name] = dict()
            dict_employee_number[region_name][subsector] = his_data

        return dict_employee_number
