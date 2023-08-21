from enum import Enum
from pathlib import Path

import pandas as pd

from endemo2.data_structures.containers import Interval, HisProg
from endemo2.input_and_settings.control_parameters import ControlParameters

from endemo2 import utility as uty


class HouseholdsSubsectorId(Enum):
    SPACE_HEATING = 0,
    SPACE_COOLING = 1,
    WATER_HEATING = 2,
    COOKING = 3,
    LIGHTING_AND_APPLIANCES = 4


class HouseholdsInput:
    hh_subsectors = [
        HouseholdsSubsectorId.SPACE_HEATING,
        HouseholdsSubsectorId.SPACE_COOLING,
        HouseholdsSubsectorId.WATER_HEATING,
        HouseholdsSubsectorId.COOKING,
        HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES
    ]

    hh_input_sheet_names = {
        HouseholdsSubsectorId.SPACE_HEATING: "1a_SpaceHeating",
        HouseholdsSubsectorId.SPACE_COOLING: "1b_SpaceCooling",
        HouseholdsSubsectorId.WATER_HEATING: "1c_WaterHeating",
        HouseholdsSubsectorId.COOKING: "1d_Cooking",
        HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES: "1e_LightingAndAppliances"
    }

    hh_energy_carrier_unit_conversion = {
        "electricity": 1 / 1000,  # GWh -> TWh
        "derived heat": 1 / 3600,  # TJ -> TWh
        "gas": 1 / 3600,  # TJ -> TWh
        "solid fossil fuels": 28157.5373355095 / 1000 / 3600,  # kt -> TWh; considering MJ/t = GJ/kt
        "total oil & petroleum products": 43208.3523702321 / 1000 / 3600,  # kt -> TWh; considering MJ/t = GJ/kt
        "total renew. & wastes": 1 / 3600  # TJ -> TWh
    }

    hh_his_sheets_skip_rows = [0, 1, 2, 3]

    def __init__(self, ctrl: ControlParameters, hh_path: Path):

        # read historical input data
        self.historical_consumption = None      # {country_name -> {subsector_id -> {energy_carrier -> data}}}
        self.read_historical_consumption(ctrl, hh_path)

        # read input for hot water (hw)
        self.hw_dict_hot_water_per_person_per_day = None   # dict{country_name -> liters}
        self.hw_dict_hot_water_calibration = None          # dict{country_name -> calibration values}
        self.hw_specific_capacity = None                   # float
        self.hw_outlet_temperature = None                  # float
        self.hw_inlet_temperature = None                   # dict{country_name -> float}
        self.hw_read_hot_water_input(ctrl, hh_path)

        # read input for space heating (sh)
        self.sh_specific_heat = None           # {country_name -> (start_point, change_rate)}
        self.sh_area_per_household = None      # {country_name -> (start_point, change_rate)}
        self.sh_persons_per_household = None   # {country_name -> [start(year, value), end(year, value)]}
        self.sh_read_space_heating_input(ctrl, hh_path)

        if ctrl.general_settings.toggle_hourly_forecast:
            # todo: read load profile stuff
            pass

    def read_historical_consumption(self, ctrl, hh_path):
        self.historical_consumption = dict[str, dict[HouseholdsSubsectorId, dict[str, [(float, float)]]]]()
        for country_name in ctrl.general_settings.active_countries:
            # read input timelines
            file_rel_path = Path("energy_consumption_households") / (country_name + "_2018.xlsm")
            ex_hh_consumption_his = pd.ExcelFile(hh_path / file_rel_path)

            self.historical_consumption[country_name] = dict[HouseholdsSubsectorId, dict[str, [(float, float)]]]()
            for subsector, sheet_name in HouseholdsInput.hh_input_sheet_names.items():
                df_subsector_historical = pd.read_excel(ex_hh_consumption_his, sheet_name=sheet_name,
                                                        skiprows=HouseholdsInput.hh_his_sheets_skip_rows)

                self.historical_consumption[country_name][subsector] = dict[str, [(float, float)]]()
                # get each row
                years = df_subsector_historical.columns[2:]
                for _, row in df_subsector_historical.iterrows():
                    energy_carrier = str(row["Product"]).lower()

                    if energy_carrier not in HouseholdsInput.hh_energy_carrier_unit_conversion.keys():
                        # skip rows other than defined energy carriers
                        continue

                    data = row[2:]
                    zipped = list(zip(years, data))
                    his_data = uty.filter_out_nan_and_inf(zipped)
                    his_data = \
                        uty.map_data_y(his_data,
                                       lambda x: x * HouseholdsInput.hh_energy_carrier_unit_conversion[energy_carrier])
                    if len(his_data) == 0:
                        # todo: is this correct? Example: Denmark SpaceCooling
                        his_data = [(2018, 0.0)]    # assume 0.0 if no data is present in file

                    self.historical_consumption[country_name][subsector][energy_carrier] = his_data

    def hw_read_hot_water_input(self, ctrl: ControlParameters, hh_path: Path):
        ex_hot_water = pd.ExcelFile(hh_path / "Warm_Water.xlsx")

        # read liter per person per day
        df_hot_water = pd.read_excel(ex_hot_water, "WaterPerPers")

        self.hw_dict_hot_water_per_person_per_day = dict[str, float]()  # country_name -> liters
        for _, row in df_hot_water.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries or rows without data
                continue
            self.hw_dict_hot_water_per_person_per_day[country_name] = float(row["Warm water [liter/d/per]"])

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

        self.hw_inlet_temperature = dict[str, float]() # country_name -> temperature
        for country_name in ctrl.general_settings.active_countries:
            parameter_name = "Inlet temperature " + country_name
            if parameter_name not in df_parameters["Parameter"].to_list():
                # use default inlet temperature
                parameter_name = "Inlet temperature all"
            self.hw_inlet_temperature[country_name] = \
                df_parameters[df_parameters["Parameter"] == parameter_name].get("Value").iloc[0]

    def sh_read_space_heating_input(self, ctrl: ControlParameters, hh_path: Path):
        ex_space_heating = pd.ExcelFile(hh_path / "Space_Heating.xlsx")

        # read specific heat
        df_spec_heat = pd.read_excel(ex_space_heating, "SpecificEnergyUse")

        self.sh_specific_heat = dict[str, ((float, float), float)]()   # country_name -> (start_point, change_rate)
        for _, row in df_spec_heat.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries and invalid rows
                continue
            start_year = 2019   # hardcode; todo: maybe this can be done differently?
            start_value = float(row[start_year])
            change_rate = row["Trend Rate [%] calc"]/100.0
            self.sh_specific_heat[country_name] = (start_year, start_value), change_rate

        # read area per household
        df_area_per_household = pd.read_excel(ex_space_heating, "AreaPerHousehold")

        self.sh_area_per_household = dict[str, ((float, float), float)]()  # country_name -> (start_point, change_rate)
        for _, row in df_area_per_household.iterrows():
            country_name = row["Country"]
            if country_name not in ctrl.general_settings.active_countries:
                # skip inactive countries and invalid rows
                continue
            start_year = 2012   # hardcode; todo: maybe this can be done differently?
            start_value = float(row["Area per household [m2/HH] (" + str(start_year) + ")"])
            change_rate = row["Trend Rate [%]"]/100.0
            self.sh_area_per_household[country_name] = (start_year, start_value), change_rate

        # read persons per household
        df_persons_per_household = pd.read_excel(ex_space_heating, "PersPerHousehold")

        self.sh_persons_per_household = HisProg(dict[str, [(float, float)]](),  # historical
                                                dict[str, [Interval[(float, float), (float, float)]]]())    # prognosis
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
                self.sh_persons_per_household.historical[country_name].append((year, row[year]))

            # prognosis
            first_year_to_read = 2020
            last_year_to_read = 2050    # should be first year + multiple of step_size
            step_size = 10

            self.sh_persons_per_household.prognosis[country_name] = []
            for year in range(first_year_to_read, last_year_to_read, step_size):
                x1 = year
                y1 = float(row[x1])
                x2 = year + step_size
                y2 = float(row[x2])
                self.sh_persons_per_household.prognosis[country_name].append(Interval((x1, y1), (x2, y2)))


