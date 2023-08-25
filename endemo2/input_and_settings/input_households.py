from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd

from endemo2.data_structures.containers import Interval, HisProg, Heat, Datapoint
from endemo2.data_structures.enumerations import DemandType, HouseholdsSubsectorId
from endemo2.data_structures.conversions_unit import Unit, get_conversion_scalar
from endemo2.input_and_settings.control_parameters import ControlParameters

from endemo2 import utility as uty


hh_subsectors = [
        HouseholdsSubsectorId.SPACE_HEATING,
        HouseholdsSubsectorId.SPACE_COOLING,
        HouseholdsSubsectorId.WATER_HEATING,
        HouseholdsSubsectorId.COOKING,
        HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES,
        HouseholdsSubsectorId.OTHER

]

hh_visible_subsectors = hh_subsectors[:-1]


class HouseholdsInput:
    """
    The HouseholdInput is responsible for reading all input data related to the Households sector.

    :ivar dict[str, dict[HouseholdsSubsectorId, dict[str, [Datapoint]]]] historical_consumption:
        The historical energy consumption for each subsector in each country.
        Is of form {country_name -> {subsector_id -> {energy_carrier -> data}}}.

    :ivar dict[str, float] hw_dict_hot_water_per_person_per_day: The amount of hot water per person per day in liter
        for each country. Is of form {country_name -> liters}.
    :ivar dict[str, float] hw_dict_hot_water_calibration: The hot water calibration value for each country.
        Is of form {country_name -> calibration value}.
    :ivar float hw_specific_capacity: The hot water specific capacity.
    :ivar float hw_outlet_temperature: The hot water outlet temperature.
    :ivar dict[str, float] hw_inlet_temperature: The hot water inlet temperature for each country.
        Is of form {country_name -> float}.

    :ivar dict[str, (Datapoint, float)] sh_specific_heat: The specific heat forecast start point and change rate
        for each country. Is of form {country_name -> (start_point, change_rate)}
    :ivar dict[str, (Datapoint, float)] sh_area_per_household: The area per household forecast start point and
        change rate for each country. Is of form {country_name -> (start_point, change_rate)}
    :ivar HisProg(dict[str, [Datapoint]](), dict[str, [Datapoint]]()) sh_persons_per_household:
        The datapoints for the persons per household in every year to interpolate between.
        Is of form {country_name -> [(year, value)]}.
    :ivar dict[str, float] hw_dict_space_heating_calibration: The space heating calibration value for each country.
        Is of form {country_name -> calibration value}.
    """

    hh_input_sheet_names = {
        HouseholdsSubsectorId.SPACE_HEATING: "1a_SpaceHeating",
        HouseholdsSubsectorId.SPACE_COOLING: "1b_SpaceCooling",
        HouseholdsSubsectorId.WATER_HEATING: "1c_WaterHeating",
        HouseholdsSubsectorId.COOKING: "1d_Cooking",
        HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES: "1e_LightingAndAppliances",
        HouseholdsSubsectorId.OTHER: "1f_OtherEndUses"
    }

    hh_energy_carrier_unit_conversion = {
        "electricity": get_conversion_scalar(Unit.GWh, Unit.TWh),  # GWh -> TWh
        "derived heat": get_conversion_scalar(Unit.TJ, Unit.TWh),  # TJ -> TWh
        "gas": get_conversion_scalar(Unit.TJ, Unit.TWh),  # TJ -> TWh
        "solid fossil fuels": 28157.5373355095 / 1000 / 3600,  # kt -> TWh; considering MJ/t = GJ/kt
        "total oil & petroleum products": 43208.3523702321 / 1000 / 3600,  # kt -> TWh; considering MJ/t = GJ/kt
        "total renew. & wastes": get_conversion_scalar(Unit.TJ, Unit.TWh)  # TJ -> TWh
    }

    hh_his_sheets_skip_rows = [0, 1, 2, 3]

    def __init__(self, ctrl: ControlParameters, hh_path: Path):

        # read historical input data
        self.historical_consumption = None      # {country_name -> {subsector_id -> {energy_carrier -> data}}}
        self.read_historical_consumption(ctrl, hh_path)

        # read input for hot water (hw)
        self.hw_dict_hot_water_per_person_per_day = None   # dict{country_name -> liters}
        self.hw_dict_hot_water_calibration = None          # dict{country_name -> calibration value}
        self.hw_specific_capacity = None                   # float
        self.hw_outlet_temperature = None                  # float
        self.hw_inlet_temperature = None                   # dict{country_name -> float}
        self.hw_read_hot_water_input(ctrl, hh_path)

        # read input for space heating (sh)
        self.sh_specific_heat = None                    # {country_name -> (start_point, change_rate)}
        self.sh_area_per_household = None               # {country_name -> (start_point, change_rate)}
        self.sh_persons_per_household = None            # {country_name -> [Datapoint]}
        self.sh_dict_space_heating_calibration = None   # {country_name -> calibration value
        self.sh_read_space_heating_input(ctrl, hh_path)

        # read load profile
        if ctrl.general_settings.toggle_hourly_forecast:
            df_load_profile = pd.read_excel(hh_path / "hh_timeseries.xlsx", sheet_name="timeseries")

            electricity = list(df_load_profile["Elec"])[1:]
            efh_heat_q1 = list(df_load_profile["EFH_Heat_Q1"])[1:]
            efh_heat_q2 = list(df_load_profile["EFH_Heat_Q2"])[1:]
            efh_h2 = list(df_load_profile["EFH_H2"])[1:]
            mfh_heat_q1 = list(df_load_profile["MFH_Heat_Q1"])[1:]
            mfh_heat_q2 = list(df_load_profile["MFH_Heat_Q2"])[1:]
            mfh_h2 = list(df_load_profile["MFH_H2"])[1:]

            self.load_profile_single_households = dict[DemandType, [Any]]()
            self.load_profile_single_households[DemandType.ELECTRICITY] = electricity
            self.load_profile_single_households[DemandType.HEAT] = \
                [Heat(q1, q2) for q1, q2 in zip(efh_heat_q1, efh_heat_q2)]
            self.load_profile_single_households[DemandType.HYDROGEN] = efh_h2

            self.load_profile_multiple_households = dict[DemandType, [Any]]()
            self.load_profile_multiple_households[DemandType.ELECTRICITY] = electricity
            self.load_profile_multiple_households[DemandType.HEAT] = \
                [Heat(q1, q2) for q1, q2 in zip(mfh_heat_q1, mfh_heat_q2)]
            self.load_profile_multiple_households[DemandType.HYDROGEN] = mfh_h2
        else:
            self.load_profile_single_households = None
            self.load_profile_multiple_households = None

    def read_historical_consumption(self, ctrl, hh_path):
        """ Read the files for the historical energy consumption of each country in the households sector. """
        self.historical_consumption = dict[str, dict[HouseholdsSubsectorId, dict[str, [Datapoint]]]]()
        for country_name in ctrl.general_settings.active_countries:
            # read input timelines
            file_rel_path = Path("energy_consumption_households") / (country_name + "_2018.xlsm")
            ex_hh_consumption_his = pd.ExcelFile(hh_path / file_rel_path)

            self.historical_consumption[country_name] = dict[HouseholdsSubsectorId, dict[str, [Datapoint]]]()
            for subsector, sheet_name in HouseholdsInput.hh_input_sheet_names.items():
                df_subsector_historical = pd.read_excel(ex_hh_consumption_his, sheet_name=sheet_name,
                                                        skiprows=HouseholdsInput.hh_his_sheets_skip_rows)

                self.historical_consumption[country_name][subsector] = dict[str, [Datapoint]]()
                # get each row
                years = df_subsector_historical.columns[2:]
                for _, row in df_subsector_historical.iterrows():
                    energy_carrier = str(row["Product"]).lower()

                    if energy_carrier not in HouseholdsInput.hh_energy_carrier_unit_conversion.keys():
                        # skip rows other than defined energy carriers
                        continue

                    data = row[2:]
                    zipped = uty.float_lists_to_datapoint_list(years, data)
                    his_data = uty.filter_out_nan_and_inf(zipped)
                    his_data = \
                        uty.map_data_y(his_data,
                                       lambda x: x * HouseholdsInput.hh_energy_carrier_unit_conversion[energy_carrier])
                    if len(his_data) == 0:
                        # todo: is this correct? Example: Denmark SpaceCooling
                        his_data = [(2018, 0.0)]    # assume 0.0 if no data is present in file

                    self.historical_consumption[country_name][subsector][energy_carrier] = his_data

    def hw_read_hot_water_input(self, ctrl: ControlParameters, hh_path: Path):
        """ Reads the input file for hot water in the households sector. """
        ex_hot_water = pd.ExcelFile(hh_path / "Hot_Water.xlsx")

        # read liter per person per day
        df_hot_water = pd.read_excel(ex_hot_water, "WaterPerPers")

        self.hw_dict_hot_water_per_person_per_day = dict[str, float]()  # country_name -> liters
        for _, row in df_hot_water.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries or rows without data
                continue
            self.hw_dict_hot_water_per_person_per_day[country_name] = float(row["Hot water [liter/d/per]"])

        # read calibration value
        df_calibration_values = pd.read_excel(ex_hot_water, "Calibration")

        self.hw_dict_hot_water_calibration = dict[str, float]()  # country_name -> calibration values
        for _, row in df_calibration_values.iterrows():
            country_name = row["Country"]
            self.hw_dict_hot_water_calibration[country_name] = float(row["Calibration parameter [-]"])

        # read other parameters
        df_parameters = pd.read_excel(ex_hot_water, "TechnData")
        self.hw_specific_capacity = \
            float(df_parameters[df_parameters["Parameter"] == "Specific capacity"].get("Value").iloc[0])

        self.hw_outlet_temperature = \
            float(df_parameters[df_parameters["Parameter"] == "Outlet temperature"].get("Value").iloc[0])

        self.hw_inlet_temperature = dict[str, float]()  # country_name -> temperature
        for country_name in ctrl.general_settings.active_countries:
            parameter_name = "Inlet temperature " + country_name
            if parameter_name not in df_parameters["Parameter"].to_list():
                # use default inlet temperature
                parameter_name = "Inlet temperature all"
            self.hw_inlet_temperature[country_name] = \
                df_parameters[df_parameters["Parameter"] == parameter_name].get("Value").iloc[0]

    def sh_read_space_heating_input(self, ctrl: ControlParameters, hh_path: Path):
        """ Reads the input file for space heating in the households sector. """
        ex_space_heating = pd.ExcelFile(hh_path / "Space_Heating.xlsx")

        # read specific heat
        df_spec_heat = pd.read_excel(ex_space_heating, "SpecificEnergyUse")

        self.sh_specific_heat = dict[str, (Datapoint, float)]()   # country_name -> (start_point, change_rate)
        for _, row in df_spec_heat.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries and invalid rows
                continue
            start_year = 2019
            start_value = float(row[start_year])
            change_rate = row["Trend Rate [%] calc"]/100.0
            self.sh_specific_heat[country_name] = Datapoint(start_year, start_value), change_rate

        # read area per household
        df_area_per_household = pd.read_excel(ex_space_heating, "AreaPerHousehold")

        self.sh_area_per_household = dict[str, (Datapoint, float)]()  # country_name -> (start_point, change_rate)
        for _, row in df_area_per_household.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries and invalid rows
                continue
            start_year = 2012
            start_value = float(row["Area per household [m2/HH] (" + str(start_year) + ")"])
            change_rate = row["Trend Rate [%]"]/100.0
            self.sh_area_per_household[country_name] = Datapoint(start_year, start_value), change_rate

        # read persons per household
        df_persons_per_household = pd.read_excel(ex_space_heating, "PersPerHousehold")

        self.sh_persons_per_household = HisProg(dict[str, [Datapoint]](),  # historical
                                                dict[str, [Datapoint]]())    # prognosis
        for _, row in df_persons_per_household.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries and invalid rows
                continue

            # historical
            first_year_to_read = 2006
            last_year_to_read = 2020
            self.sh_persons_per_household.historical[country_name] = []
            for year in range(first_year_to_read, last_year_to_read + 1):
                self.sh_persons_per_household.historical[country_name].append(Datapoint(year, row[year]))

            # prognosis
            first_year_to_read = 2020
            last_year_to_read = 2050    # should be first year + multiple of step_size
            step_size = 10

            self.sh_persons_per_household.prognosis[country_name] = []
            for year in range(first_year_to_read, last_year_to_read + 1, step_size):
                x = year
                y = float(row[x])
                self.sh_persons_per_household.prognosis[country_name].append(Datapoint(x, y))

        # read calibration value
        df_calibration_values = pd.read_excel(ex_space_heating, "Calibration")

        self.sh_dict_space_heating_calibration = dict[str, float]()  # country_name -> calibration values
        for _, row in df_calibration_values.iterrows():
            country_name = row["Country"]
            self.sh_dict_space_heating_calibration[country_name] = float(row["Calibration parameter [-]"])


