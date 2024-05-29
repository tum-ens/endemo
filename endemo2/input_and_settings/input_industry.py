from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

from endemo2 import utility as uty
from endemo2.data_structures import containers as dc
from endemo2.data_structures.containers import Heat, Datapoint
from endemo2.data_structures.enumerations import GroupType, DemandType, SubsectorGroup
from endemo2.input_and_settings import control_parameters as cp
from endemo2.input_and_settings.control_parameters import IndustrySettings
from endemo2.input_and_settings.input_general import Abbreviations
from endemo2.input_and_settings.input_utility import FileReadingHelper, read_energy_carrier_consumption_historical


class ProductInput:
    """
    The ProductInput holds all input data that is specific to a subsector. Most of the input is also read within this
    class, except input that is more efficient to be read for all products at once. That input is read in the
    IndustryInput class.

    :param str product_name: The name of the product this input is for.
    :param Path industry_path: The path to the industry input folder.
    :param IndustrySettings industry_settings: The settings for the industry sector.
    :param ExcelFile ex_specific_consumption: The Excel sheet for specific consumption default values.
    :param ExcelFile ex_bat: The Excel sheet for best available technology.
    :param ExcelFile ex_nuts2_ic: The Excel sheet for nuts2 installed capacities.
    :param ExcelFile ex_country_groups: The Excel sheet of the country groups.
    :param [str] active_countries: The list of english names of the active countries.
    :param dict[str, Heat] dict_heat_levels: The dictionary holding the heat levels for all products.
        Of form {front_label -> heat_levels}.

    :ivar str front_label: The name of the product.
    :ivar dict[str, containers.SpecConsum] specific_consumption_default: Default specific consumption value for this
        product.
    :ivar dict[str, Datapoint] specific_consumption_historical: Historical specific consumption data
        for this product. Accessible per country.
    :ivar dict[str, containers.EH] bat: The best-available-technology consumption for this product.
        Accessible per country.
    :ivar dict[str, Datapoint] production: The historical amount data for this product. Accessible per country.
    :ivar Heat heat_levels: How heat demand should be distributed across heat levels for this product.
    :ivar float manual_exp_change_rate: If product amount projection will be calculated exponentially,
        this will be the change rate.
    :ivar float perc_used: A scalar for the amount of a product.
        This is used to model modern technologies replacing old ones.
    :ivar dict[str, dict[str, float]] nuts2_installed_capacity: Installed capacity in %/100 for each NUTS2 Region.
        Structure {country_name -> {nuts2_region_name -> capacity_value}}
    :ivar dict[str, [[str]]] country_groups: Input from country group file,
        structured as {group_type -> list_of_groups}.
    """

    def __init__(self, product_name: str, industry_path: Path, industry_settings: IndustrySettings,
                 ex_specific_consumption: pd.ExcelFile, ex_bat: pd.ExcelFile, ex_nuts2_ic: pd.ExcelFile,
                 ex_country_groups: pd.ExcelFile, active_countries, dict_heat_levels: dict[str, Heat],
                 nuts2_valid_regions: set[str]):
        self.product_name = product_name

        # read product input from industry dictionaries
        self.heat_levels = dict_heat_levels[self.product_name]

        # read production data
        self.production = self.read_production_data(industry_path, industry_settings)

        # read specific consumption default data
        self.specific_consumption_default = self.read_specific_consumption_default(ex_specific_consumption)

        # read specific demand historical data
        if industry_settings.trend_calc_for_spec:
            self.specific_consumption_historical = \
                self.read_energy_carrier_consumption_historical(industry_path)
        else:
            self.specific_consumption_historical = None

        # read bat consumption data
        self.bat = self.read_best_available_technology(ex_bat)

        # read NUTS2 installed capacity
        self.nuts2_installed_capacity = \
            self.read_nuts2_installed_capacities(ex_nuts2_ic, nuts2_valid_regions)

        # read country groups
        self.country_groups = self.read_country_groups(ex_country_groups, active_countries)

    def __str__(self):
        return "\n\tSpecific Consumption: " + uty.str_dict(self.specific_consumption_default) + \
            "\n\t BAT: " + uty.str_dict(self.bat) + \
            "\n\t Historical: " + uty.str_dict(self.production) + "\n"

    def read_specific_consumption_default(self, ex_specific_consumption: pd.ExcelFile) -> dict[str, dc.SpecConsum]:
        """
        Reads the default specific consumption data for this subsector.

        :param ex_specific_consumption: The Excel sheet for specific consumption default values.
        :return: The default specific consumptions for this subsector. Of form: {back_label -> specific_consumption}
        """
        prod_sc = pd.read_excel(ex_specific_consumption, sheet_name=self.product_name)
        dict_prod_sc_country = dict[str, dc.SpecConsum]()

        for _, row in pd.DataFrame(prod_sc).iterrows():
            dict_prod_sc_country[row.Country] = \
                dc.SpecConsum(row["Spec electricity consumption [GJ/t]"],
                              row["Spec heat consumption [GJ/t]"],
                              row["Spec hydrogen consumption [GJ/t]"],
                              row["max. subst. of heat with H2 [%]"])

        return dict_prod_sc_country

    def read_energy_carrier_consumption_historical(self, industry_path: Path) \
            -> dict[str, [Datapoint]]:
        """
        Reads the historical consumption data for this subsector split by energy carriers.

        :param industry_path: The path to the industry input folder.
        :return: If present, the historical quantity of energy carrier in subsector.
            Of form: {country_name -> {energy_carrier -> [Datapoint]}}
        """

        if self.product_name not in IndustryInput.sc_historical_data_file_names.keys():
            return None

        sc_his_file_name = IndustryInput.sc_historical_data_file_names[self.product_name]
        return read_energy_carrier_consumption_historical(industry_path, sc_his_file_name)

    def read_production_data(self, industry_path: Path, industry_settings: IndustrySettings) \
            -> dict[str, [Datapoint]]:
        """
        Reads historical production quantities for this subsector.

        :param industry_path: The path to the industry input folder.
        :param industry_settings: The industry settings.
        :return: The historical production data of all _subsectors for all countries.
        """
        retrieve_prod = IndustryInput.product_data_access[self.product_name]
        retrieve_prod.set_path_and_read(industry_path)
        retrieve_prod.skip_years(industry_settings.skip_years)
        df_product_his = retrieve_prod.get()

        dict_prod_his = dict[str, [Datapoint]]()

        production_it = pd.DataFrame(df_product_his).itertuples()
        for row in production_it:
            if str(row.Country) == 'nan':
                continue
            years = df_product_his.columns[1:]
            data = df_product_his[df_product_his["Country"] == row.Country].iloc[0][1:]
            zipped = uty.float_lists_to_datapoint_list(years, data)
            his_data = uty.filter_out_nan_and_inf(zipped)
            if uty.is_tuple_list_zero(his_data):
                # country did not product this product at all => skip product for this country
                # print("skipped " + front_label + " for country " + row.Country)
                continue
            his_data = uty.cut_after_x(his_data, industry_settings.last_available_year - 1)
            his_data = uty.map_data_y(his_data, lambda x: x * 1000)  # convert kt to t
            dict_prod_his[row.Country] = his_data

        return dict_prod_his

    def read_nuts2_installed_capacities(self, ex_nuts2_ic: pd.ExcelFile,
                                        nuts2_valid_regions: set[str]) -> dict[str, dict[str, float]]:
        """
        Reads all the installed capacities for the nuts2 regions.

        :param ex_nuts2_ic: The Excel sheet holding the installed capacities percentages.
        :param set[str] nuts2_valid_regions: The valid nuts2 regions according to the currently chosen nuts2 version.
        :return: The installed capacities for all nuts2 regions in an active country.
            Is of form: {back_label -> {nuts2_region_name -> installed_capacity}}
        """
        dict_installed_capacity_nuts2 = dict[str, dict[str, float]]()

        product_name_general = self.product_name
        if product_name_general.endswith("_classic"):
            product_name_general = product_name_general.removesuffix("_classic")

        if product_name_general in ["steel_prim", "steel_sec", "steel_direct"]:
            # PLACEHOLDER until steel is finished in sheets. TODO: remove when steel is correct in sheet
            product_name_general = "steel"

        df_nuts2_ic = pd.read_excel(ex_nuts2_ic, product_name_general)
        for _, row in df_nuts2_ic.iterrows():
            nuts2 = row["NUTS2"]
            alpha2 = nuts2[:2]
            if nuts2 not in nuts2_valid_regions:
                # not the currently chosen nuts2 code version
                continue
            if alpha2 not in Abbreviations.dict_alpha2_en_map.keys():
                # country not active
                continue

            country_name_en = Abbreviations.dict_alpha2_en_map[nuts2[:2]]
            if country_name_en not in dict_installed_capacity_nuts2.keys():
                dict_installed_capacity_nuts2[country_name_en] = dict[str, float]()

            perc_value = row[product_name_general + " %"]  # automatically %/100
            dict_installed_capacity_nuts2[country_name_en][nuts2] = perc_value if not np.isnan(perc_value) else 0.0

        return dict_installed_capacity_nuts2

    def read_best_available_technology(self, ex_bat: pd.ExcelFile) -> dict[str, dc.EH]:
        """
        Reads the specific consumption input of the best available technology.

        :param ex_bat: The Excel file of the best available technology.
        :return: The bat consumption for each country. Of the form: {back_label -> EH}
        """
        df_prod_bat = pd.read_excel(ex_bat, sheet_name=self.product_name)
        dict_prod_bat_country = dict()

        for _, row in df_prod_bat.iterrows():
            dict_prod_bat_country[row.Country] = \
                dc.EH(row["Spec electricity consumption [GJ/t]"],
                      row["Spec heat consumption [GJ/t]"])

        return dict_prod_bat_country

    def read_country_groups(self, ex_country_groups: pd.ExcelFile, active_countries: [str]) -> dict[GroupType, [[str]]]:
        """
        Reads the input for the country groups.

        :param ex_country_groups: The Excel file that gives the country groups.
        :param active_countries: The list of active countries.
        :return: The country groups of form: {group_type -> [ grp1[country1, country2, ...], grp2[country4, ...], ... ]}
        """

        country_groups = dict[GroupType, [[str]]](
            {GroupType.SEPARATE: [], GroupType.JOINED: [], GroupType.JOINED_DIVERSIFIED: []})

        # if product sheet exists take that, else take default
        try:
            df_country_groups = pd.read_excel(ex_country_groups, sheet_name=self.product_name)
        except ValueError:
            df_country_groups = pd.read_excel(ex_country_groups, sheet_name="default")

        map_group_type = {"joined": GroupType.JOINED,
                          "joined_diversified": GroupType.JOINED_DIVERSIFIED,
                          "separate": GroupType.SEPARATE}

        all_countries = active_countries
        grouped_countries = set()
        all_others_group_type = None

        for _, row in df_country_groups.iterrows():
            group_type = map_group_type[row["Combination Type"]]
            new_group = [entry for entry in row[1:] if str(entry) != "nan"]
            if "all_others" in new_group:
                all_others_group_type = group_type
                continue
            new_group_only_active_countries = [country for country in new_group if country in active_countries]
            if len(new_group_only_active_countries) > 0:
                country_groups[group_type].append(new_group_only_active_countries)
            grouped_countries |= set(new_group_only_active_countries)

        if all_others_group_type is not None:
            rest_countries = [country for country in all_countries if country not in grouped_countries]
            if len(rest_countries) > 0:
                # empty groups lead to errors
                country_groups[all_others_group_type] += [rest_countries]

        return country_groups


class RestSectorInput:
    """
    A container for the preprocessing data regarding the rest transport.

    :param Path industry_path: The path to the industry input folder.
    :param dict[str, Heat] dict_heat_levels: The heat levels.

    :ivar dict[str, dict[DemandType, Datapoint]] rest_demand_proportion_basis_year: Used for the calculation of the rest sector.
        It has the following structure: {back_label -> {demand_type -> (rest_sector_percent, demand_2018)}}
    :ivar int rest_calc_basis_year: Year used as a starting point for calculating the rest sector demand.
    :ivar (float, float, float, float) rest_sector_heat_levels: The heat levels used to separate the heat demand in the
        rest sector into the different heat levels.
    """

    def __init__(self, industry_path: Path, dict_heat_levels: dict[str, Heat]):
        df_rest_calc = pd.read_excel(industry_path / "Ind_energy_demand_2018_Trend_Restcalcul.xlsx")
        self.rest_calc_basis_year = 2018  # change here, if another year should be used for rest sector (also path)
        self.rest_sector_heat_levels = dict_heat_levels["rest"]
        self.rest_demand_proportion_basis_year = dict()
        for _, row in df_rest_calc.iterrows():
            self.rest_demand_proportion_basis_year[row["Country"]] = dict()
            self.rest_demand_proportion_basis_year[row["Country"]][DemandType.ELECTRICITY] = \
                (row["Rest el"] / 100, row["electricity " + str(self.rest_calc_basis_year)])
            self.rest_demand_proportion_basis_year[row["Country"]][DemandType.HEAT] = \
                (row["Rest heat"] / 100, row["heat " + str(self.rest_calc_basis_year)])


class IndustryInput:
    """
    Industry Input denoted input that is read from the "input/industry" folder.

    :param ctrl: ControlSettings object.
    :param industry_path: The path to the industry input folder.
    :param nuts2_valid_regions: The valid nuts2 regions of set version.
    :param active_countries: The currently active countries.

    :ivar dict[str, ProductInput] dict_product_input: Stores the product specific preprocessing for all active products.
    :ivar dict[str, Retrieve] product_data_access: Specify how data sheets for each product should be accessed
    :ivar dict[str, str] sc_historical_data_file_names: The file names of the files used for certain products to read
        historical information on specific consumption.
    :ivar [str] sc_historical_sheet_names: The sheet names for the files used to read
        historical information on specific consumption for certain products.
    :ivar RestSectorInput rest_sector_input: All preprocessing data relating to the rest sector.
    :ivar dict[str, [float]] dict_electricity_profiles: The hourly profiles for electricity demand for each country.
    :ivar dict[SubsectorGroup, dict[str, [float]]] dict_heat_profiles: The hourly profiles for heat demand for each
        subsector group and each country. Is of form {subsector_group -> {back_label -> [hourly_profile in %/100]}}
    :ivar dict[str, SubsectorGroup] subsector_to_group_map: Maps a certain subsector to their subsector group enum.
    """

    product_data_access = {
        "steel": FileReadingHelper("Steel_Production.xlsx", "Data_total", [], lambda x: x),
        "steel_prim": FileReadingHelper("Steel_Production.xlsx", "Steel_prim", [], lambda x: x),
        "steel_sec": FileReadingHelper("Steel_Production.xlsx", "Steel_sec", [], lambda x: x),
        "steel_direct": FileReadingHelper("Steel_Production.xlsx", "Steel_sec", [], lambda x: x),
        "alu_prim": FileReadingHelper("Aluminium_Production.xlsx", "Prim_Data", [], lambda x: x),
        "alu_sec": FileReadingHelper("Aluminium_Production.xlsx", "Sec_Data", [], lambda x: x),
        "copper_prim": FileReadingHelper("Copper_Production.xlsx", "Copper_WSP", [0, 1],
                                         lambda x: x.loc[x["Type"] == "Primary"].drop("Type", axis=1)),
        "copper_sec": FileReadingHelper("Copper_Production.xlsx", "Copper_WSP", [0, 1],
                                        lambda x: x.loc[x["Type"] == "Secondary"].drop("Type", axis=1)),
        "chlorine": FileReadingHelper("Chlorine_Production.xlsx", "Data", [], lambda x: x),
        "ammonia": FileReadingHelper("Ammonia_Production.xlsx", "Data", [], lambda x: x),
        "methanol": FileReadingHelper("Methanol_Production.xlsx", "Data", [], lambda x: x),
        "ethylene": FileReadingHelper("Ethylene_Production.xlsx", "Data", [], lambda x: x),
        "propylene": FileReadingHelper("Propylene_Production.xlsx", "Data", [], lambda x: x),
        "aromate": FileReadingHelper("Aromate_Production.xlsx", "Data", [], lambda x: x),
        "ammonia_classic": FileReadingHelper("Ammonia_Production.xlsx", "Data", [], lambda x: x),
        "methanol_classic": FileReadingHelper("Methanol_Production.xlsx", "Data", [], lambda x: x),
        "ethylene_classic": FileReadingHelper("Ethylene_Production.xlsx", "Data", [], lambda x: x),
        "propylene_classic": FileReadingHelper("Propylene_Production.xlsx", "Data", [], lambda x: x),
        "aromate_classic": FileReadingHelper("Aromate_Production.xlsx", "Data", [], lambda x: x),
        "paper": FileReadingHelper("Paper_Production.xlsx", "Data", [], lambda x: x),
        "cement": FileReadingHelper("Cement_Production.xlsx", "Data", [], lambda x: x),
        "glass": FileReadingHelper("Glass_Production.xlsx", "Data", [], lambda x: x),
    }
    sc_historical_data_file_names = {
        "steel": "nrg_bal_s_steel.xls",
        "paper": "nrg_bal_s_paper.xls"
    }

    subsector_groups_str_to_enum_map = {
        "non_metalic_minerals": SubsectorGroup.NON_METALIC_MINERALS,
        "chemicals_and_petrochemicals": SubsectorGroup.CHEMICALS_AND_PETROCHEMICALS,
        "food_and_tobacco": SubsectorGroup.FOOD_AND_TOBACCO,
        "iron_and_steel": SubsectorGroup.IRON_AND_STEEL,
        "paper": SubsectorGroup.PAPER
    }

    subsector_groups_hotmaps_filenames = {
        SubsectorGroup.NON_METALIC_MINERALS:
            "hotmaps_task_2.7_load_profile_industry_non_metalic_minerals_yearlong_2018.csv",
        SubsectorGroup.CHEMICALS_AND_PETROCHEMICALS:
            "hotmaps_task_2.7_load_profile_industry_chemicals_and_petrochemicals_yearlong_2018.csv",
        SubsectorGroup.FOOD_AND_TOBACCO: "hotmaps_task_2.7_load_profile_industry_food_and_tobacco_yearlong_2018.csv",
        SubsectorGroup.IRON_AND_STEEL: "hotmaps_task_2.7_load_profile_industry_iron_and_steel_yearlong_2018.csv",
        SubsectorGroup.PAPER: "hotmaps_task_2.7_load_profile_industry_paper_yearlong_2018.csv",
    }

    def __init__(self, ctrl: cp.ControlParameters, industry_path: Path,
                 nuts2_valid_regions: set[str], active_countries: [str]):
        self.dict_product_input = dict[str, ProductInput]()

        # read heat levels
        dict_heat_levels = IndustryInput.read_heat_levels(industry_path)

        # read rest sector calculation data
        self.rest_sector_input = RestSectorInput(industry_path, dict_heat_levels)

        # read subsector groups for time profile
        self.subsector_to_group_map = IndustryInput.read_subsector_groups(industry_path)

        if ctrl.general_settings.toggle_hourly_forecast:
            # read other files for time profile
            (electricity_profiles, heat_profiles) = \
                IndustryInput.read_load_timeseries(industry_path, active_countries)
            self.dict_electricity_profiles = electricity_profiles
            self.dict_heat_profiles = heat_profiles
        else:
            self.dict_electricity_profiles = None
            self.dict_heat_profiles = None

        # read files for the product input (faster to read only once for all products)
        ex_spec = pd.ExcelFile(industry_path / "Specific_Consumption.xlsx")
        ex_bat = pd.ExcelFile(industry_path / "BAT_Consumption.xlsx")
        ex_nuts2_ic = pd.ExcelFile(industry_path / "Installed_capacity_NUTS2.xlsx")
        ex_country_groups = pd.ExcelFile(industry_path / "Country_Groups.xlsx")

        # read the active _subsectors sheets
        for product_name in ctrl.industry_settings.active_product_names:
            if product_name == 'unspecified industry':
                continue

            # finally store in product data class
            self.dict_product_input[product_name] = \
                ProductInput(product_name, industry_path, ctrl.industry_settings,
                             ex_spec, ex_bat, ex_nuts2_ic, ex_country_groups,
                             active_countries, dict_heat_levels, nuts2_valid_regions)

    @classmethod
    def read_heat_levels(cls, industry_path: Path) -> dict[str, Heat]:
        df_heat_levels = pd.read_excel(industry_path / "Heat_levels.xlsx")
        dict_heat_levels = dict[str, Heat]()

        for _, row in df_heat_levels.iterrows():
            dict_heat_levels[row["Industry"]] = Heat(row["Q1"] / 100, row["Q2"] / 100, row["Q3"] / 100,
                                                     row["Q4"] / 100)
        return dict_heat_levels

    @classmethod
    def read_subsector_groups(cls, industry_path: Path) -> dict[str, SubsectorGroup]:
        df_subsector_group = pd.read_excel(industry_path / "Subsector_groups.xlsx")
        groups_as_enum = [IndustryInput.subsector_groups_str_to_enum_map[str_group] for str_group in
                          df_subsector_group["Group"]]
        return dict(zip(df_subsector_group["Subsectors"], groups_as_enum))

    @classmethod
    def read_load_timeseries(cls, industry_path: Path, active_countries: [str]) \
            -> (dict[str, [float]], dict[SubsectorGroup, dict[str, [float]]]):

        # read electricity profiles
        df_electricity_profiles = pd.read_excel(industry_path / "IND_Elec_Loadprofile.xlsx")
        dict_electricity_profiles = dict[str, [float]]()
        for country_name in active_countries:
            country_column_name = country_name + "-Electricity"
            if country_name + "-Electricity" not in list(df_electricity_profiles):
                country_column_name = "Default-Electricity"
            country_column = list(df_electricity_profiles[country_column_name])
            dict_electricity_profiles[country_name] = country_column[1:]

        # read heat profiles
        dict_heat_profiles = dict[SubsectorGroup, dict[str, [float]]]()
        for subsec_group, filename in IndustryInput.subsector_groups_hotmaps_filenames.items():
            df_hotmaps = pd.read_csv(industry_path / filename)
            for _, row in df_hotmaps.iterrows():
                country_abbr = row["NUTS0_code"]
                if country_abbr not in Abbreviations.dict_alpha2_en_map.keys():
                    # non-active country, skip
                    continue
                country_en = Abbreviations.dict_alpha2_en_map[country_abbr]
                new_value = row["load"]
                if subsec_group not in dict_heat_profiles.keys():
                    dict_heat_profiles[subsec_group] = dict()
                if country_en not in dict_heat_profiles[subsec_group].keys():
                    dict_heat_profiles[subsec_group][country_en] = []
                dict_heat_profiles[subsec_group][country_en].append(new_value / 1000000.0)

        return dict_electricity_profiles, dict_heat_profiles
