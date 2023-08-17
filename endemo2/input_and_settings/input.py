"""
This module is responsible for reading the input data form files.
(except the Set_and_Control_Parameters. That would be in control_parameters.)
"""

from __future__ import annotations

import math
import os
import warnings
from array import array
from typing import Union, Any
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import ExcelFile

from endemo2.data_structures.containers import Heat
from endemo2.data_structures.enumerations import GroupType, DemandType, SubsectorGroup
from endemo2 import utility as uty
from endemo2.data_structures import containers as dc
from endemo2.input_and_settings import control_parameters as cp
from endemo2.input_and_settings.control_parameters import ControlParameters, IndustrySettings
from endemo2.input_and_settings.input_utility import FileReadingHelper, skip_years_in_df


class Abbreviations:
    # create country_abbr -> country_name_en mapping
    dict_alpha2_en_map = dict[str, str]()
    # create country_name_de -> country_name_en mapping
    dict_de_en_map = dict[str, str]()
    # create country_name_en -> country_abbr mapping
    dict_en_alpha2_map = dict[str, str]()


class Input:
    """
    The Input class connects all types of preprocessing data, that is in the form of excel/csv sheets in the 'preprocessing' folder.

    :ivar str super_path: Path of project folder
    :ivar str input_path: Path of preprocessing files
    :ivar str output_path: Path for output files
    :ivar str general_path: Path for preprocessing files in "general" folder
    :ivar str industry_path: Path for preprocessing files in "industry" folder

    :ivar ControlParameters ctrl: Holds all information received from Set_and_Control_Parameters.xlsx
    :ivar GeneralInput general_input: Holds all information of the preprocessing files from the "preprocessing/general" folder.
    :ivar IndustryInput industry_input: Holds all information of the preprocessing files from the "preprocessing/industry" folder.
    """

    super_path = Path(os.path.abspath(''))
    input_path = super_path / 'input'
    output_path = super_path / 'output'
    general_path = input_path / 'general'
    industry_path = input_path / 'industry'
    cts_path = input_path / 'commercial_trade_and_services'

    ctrl_path = input_path / 'Set_and_Control_Parameters.xlsx'

    # Future TODO: add other sector inputs

    def __init__(self):
        # read set and control parameters
        self.ctrl: ControlParameters = Input.read_set_and_control_parameters()

        # read general
        self.general_input = GeneralInput(self.ctrl, Input.general_path)

        # read industry
        self.industry_input = IndustryInput(self.ctrl, Input.industry_path,
                                            self.general_input.nuts2_valid_regions,
                                            self.ctrl.general_settings.active_countries)

        # read commercial_trade_and_services
        self.cts_input = CtsInput(self.ctrl, Input.cts_path)

    def update_set_and_control_parameters(self):
        """ Updates Set_and_Control_Parameters.xlsx """
        self.ctrl = Input.read_set_and_control_parameters()

    @classmethod
    def read_set_and_control_parameters(cls) -> cp.ControlParameters:
        """ Reads Set_and_Control_Parameters.xlsx """
        ctrl_ex = pd.ExcelFile(Input.ctrl_path)

        # read control parameters
        general_settings = cp.GeneralSettings(pd.read_excel(ctrl_ex, sheet_name="GeneralSettings"),
                                              pd.read_excel(ctrl_ex, sheet_name="Countries"))
        industry_settings = \
            cp.IndustrySettings(
                pd.read_excel(ctrl_ex, sheet_name="IND_general"),
                pd.read_excel(ctrl_ex, sheet_name="IND_subsectors"))

        cts_settings = cp.CtsSettings(pd.read_excel(ctrl_ex, sheet_name="CTS"))

        return cp.ControlParameters(general_settings, industry_settings, cts_settings)


class PopulationInput:
    """
    Holds all data on population. That includes historical data, prognosis data for each country and nuts2 region.

    :param ControlParameters ctrl: The parsed Set_and_Control_Parameters.xlsx file.
    :param set nuts2_valid_regions: The set of nuts2 regions that are recognized.
        They are used to filter the preprocessing data.
    :param dict abbreviations: The countries_in_group abbreviations, used to access nuts2 data.
    :param pd.DataFrame df_country_pop_his: The sheet containing data of population history per country.
    :param pd.DataFrame df_country_pop_prog: The sheet containing the manual prognosis of population amount per country.
    :param pd.DataFrame df_nuts2_pop_his: The sheet containing data of population history per NUTS2 region.
    :param pd.DataFrame df_nuts2_pop_prog:
        The sheet containing the prognosis intervals and growth rate for nuts2 regions.

    :ivar dict[str, HisProg] country_population: Data for the population of whole countries_in_group.
        It is of the form historical:{country_name -> [(float, float)]}, prognosis:{country_name -> [(float, float)]}
    :ivar dict[str, [(str, [float, float])]] nuts2_population: Data for the population of NUTS2 regions.
        It is of the form {country_name -> (code -> (historical: [(float,float)], prognosis: [interval, growth rate]))}
    """

    def __init__(self, ctrl: cp.ControlParameters, nuts2_valid_regions: set, abbreviations: dict[str, dc.CA],
                 df_country_pop_his: pd.DataFrame, df_country_pop_prog: pd.DataFrame,
                 df_nuts2_pop_his: pd.DataFrame, df_nuts2_pop_prog: pd.DataFrame):
        self.country_population = dict[str, dc.HisProg]()
        self.nuts2_population = dict[str, [(str, [float, float])]]()

        # preprocess country population historical data
        dict_c_pop_his = uty.convert_table_to_filtered_data_series_per_country(df_country_pop_his)

        # preprocess country population prognosis
        dict_c_pop_prog = uty.convert_table_to_filtered_data_series_per_country(df_country_pop_prog)

        # preprocess nuts2 population historical data
        df_nuts2_pop_his = df_nuts2_pop_his.drop('GEO/TIME', axis=1)
        dict_nuts2_pop_his = dict[str, dict[str, [(float, float)]]]()
        it = df_nuts2_pop_his.itertuples()
        for row in it:
            region_name = str(row[1]).strip()  # read region code from rows
            if region_name.endswith("-"):
                region_name = region_name[:-2]
            if region_name not in nuts2_valid_regions:
                continue
            if region_name[-1] == "X":
                # its a non-region
                continue
            zipped = list(zip(list(df_nuts2_pop_his)[1:], row[2:]))
            his_data = uty.filter_out_nan_and_inf(zipped)
            abbrev = region_name[:2]
            if abbrev not in dict_nuts2_pop_his.keys():
                dict_nuts2_pop_his[abbrev] = dict()
            dict_nuts2_pop_his[abbrev][region_name] = his_data

        # preprocess nuts2 population prognosis: interval 2015-2050
        df_nuts2_pop_prog = df_nuts2_pop_prog.drop(["Region name", "for 35 years"], axis=1) \
            .rename(columns={'per year': '2015-2050'})
        interval_conv = lambda xs: [dc.Interval(int(x.split('-')[0]), int(x.split('-')[1])) for x in xs]
        intervals = interval_conv(df_nuts2_pop_prog.columns[1:])

        dict_nuts2_pop_prog = dict[str, dict[str, [(dc.Interval, float)]]]()
        it = df_nuts2_pop_prog.itertuples()
        for row in it:
            region_name = str(row[1]).strip()
            if region_name not in nuts2_valid_regions:
                continue
            alpha2 = region_name[:2]

            values = df_nuts2_pop_prog[df_nuts2_pop_prog["Code"] == region_name].iloc[0][1:]
            zipped_prog = list(zip(intervals, values))

            if alpha2 not in dict_nuts2_pop_prog.keys():
                dict_nuts2_pop_prog[alpha2] = dict()

            dict_nuts2_pop_prog[alpha2][region_name] = zipped_prog

        for country_name in ctrl.general_settings.active_countries:
            # fill country population
            self.country_population[country_name] = \
                dc.HisProg(dict_c_pop_his[country_name], dict_c_pop_prog[country_name])

            # fill nuts2 population
            if country_name not in self.nuts2_population.keys():
                self.nuts2_population[country_name] = dict()
            abbrev = Abbreviations.dict_en_alpha2_map[country_name]
            self.nuts2_population[country_name] = \
                dc.HisProg(dict_nuts2_pop_his[abbrev], dict_nuts2_pop_prog[abbrev])


class GeneralInput:
    """
    General Input contains all preprocessing that is read from the "preprocessing/general" folder.

    :param ControlParameters ctrl: The parsed Set_and_Control_Parameters.xlsx
    :param Path path: The path to the preprocessing/general folder

    :ivar PopulationData population: All data from the population preprocessing.
    :ivar dict[str, HisProg[[(float, float)], [Interval, float]]] gdp: The gdp for each country.
    :ivar dict[str, ("electricity", "heat")] efficiency: The efficiency for each energy carrier.
    :ivar set nuts2_valid_regions: The set of valid nuts2 regions within the selected NUTS2 code.
    """

    def __init__(self, ctrl: cp.ControlParameters, path: Path):
        self.abbreviations = dict[str, dc.CA]()
        self.gdp = dict[str, dc.HisProg[[(float, float)], [dc.Interval, float]]]()
        self.efficiency = dict[str, dc.EH]()

        df_abbr = pd.read_excel(path / "Abbreviations.xlsx")
        df_world_pop_his = pd.read_excel(path / "Population_historical_world.xls")
        df_world_pop_prog = pd.read_excel(path / "Population_projection_world.xlsx")
        df_nuts2_pop_his = pd.read_csv(path / "Population_historical_NUTS2.csv")
        df_nuts2_pop_prog = \
            pd.read_excel(path / "Population_projection_NUTS2.xlsx",
                          sheet_name="Populationprojection_NUTS2_" + str(ctrl.general_settings.nuts2_version))
        df_gdp_his = pd.read_excel(path / "GDP_per_capita_historical.xlsx", sheet_name="constant 2015 USD")
        df_gdp_prog_europa = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data")
        df_gdp_prog_world = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data_world")
        df_efficiency = pd.read_excel(path / "Efficiency_Combustion.xlsx")
        df_nuts2_labels = pd.read_excel(path / "NUTS2_from_Model.xlsx")

        # fill nuts2 valid regions
        column_name = "Code " + str(ctrl.general_settings.nuts2_version)
        self.nuts2_valid_regions = set([x.strip() for x in df_nuts2_labels[column_name] if len(x.strip()) == 4])

        # fill efficiency
        for _, row in df_efficiency.iterrows():
            self.efficiency[row["Energy carrier"]] = \
                dc.EH(row["Electricity production [-]"], row["Heat production [-]"])

        for country_name in ctrl.general_settings.active_countries:
            # fill abbreviations class for easy access from anywhere
            alpha2 = df_abbr[df_abbr["Country_en"] == country_name].get("alpha-2").iloc[0]
            german_name = df_abbr[df_abbr["Country_en"] == country_name].get("Country_de").iloc[0]
            alpha3 = df_abbr[df_abbr["Country_en"] == country_name].get("alpha-3").iloc[0]
            Abbreviations.dict_alpha2_en_map[alpha2] = country_name
            Abbreviations.dict_de_en_map[german_name] = country_name
            Abbreviations.dict_en_alpha2_map[country_name] = alpha2

            # read gdp historical
            years = df_gdp_his.columns[3:]
            gdp_data = df_gdp_his[df_gdp_his["Country Code"] == alpha3].iloc[0][3:]
            zipped = list(zip(years, gdp_data))
            gdp_his = uty.filter_out_nan_and_inf(zipped)

            # read gdp prognosis
            interval_conv = lambda xs: [dc.Interval(int(x.split('-')[0]), int(x.split('-')[1])) for x in xs]
            intervals_europa = interval_conv(df_gdp_prog_europa.columns[1:-1])
            intervals_world = interval_conv(df_gdp_prog_world.columns[1:-1])

            zipped_gdp_prog: list[dc.Interval, float]
            if country_name in list(df_gdp_prog_europa["Country"]):
                gdp_prog = df_gdp_prog_europa[df_gdp_prog_europa["Country"] == country_name].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_europa, gdp_prog))
            elif country_name in list(df_gdp_prog_world["Country"]):
                gdp_prog = df_gdp_prog_world[df_gdp_prog_world["Country"] == country_name].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_world, gdp_prog))
            else:
                warnings.warn("Attention! For country \"" + country_name
                              + "\" no gdp prognosis data was found. Data from \"all\" is used instead now.")
                gdp_prog = df_gdp_prog_europa[df_gdp_prog_europa["Country"] == "all"].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_europa, gdp_prog))

            self.gdp[country_name] = dc.HisProg(gdp_his, zipped_gdp_prog)

        # create PopulationData object
        self.population = PopulationInput(ctrl, self.nuts2_valid_regions, self.abbreviations,
                                          df_world_pop_his, df_world_pop_prog, df_nuts2_pop_his,
                                          df_nuts2_pop_prog)


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
    :ivar dict[str, (float, float)] specific_consumption_historical: Historical specific consumption data
        for this product. Accessible per country.
    :ivar dict[str, containers.EH] bat: The best-available-technology consumption for this product.
        Accessible per country.
    :ivar dict[str, (float, float)] production: The historical amount data for this product. Accessible per country.
    :ivar Heat heat_levels: How heat demand should be distributed across heat levels for this product.
    :ivar float manual_exp_change_rate: If product amount projection will be calculated exponentially,
        this will be the change rate.
    :ivar float perc_used: A scalar for the amount of a product.
        This is used to model modern technologies replacing old ones.
    :ivar dict[str, dict[str, float]]: Installed capacity in %/100 for each NUTS2 Region.
        Structure {back_label -> {nuts2_region_name -> capacity_value}}
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
            -> Union[None, dict[str, [(float, float)]]]:
        """
        Reads the historical consumption data for this subsector split by energy carriers.

        :param industry_path: The path to the industry input folder.
        :return: If present, the historical quantity of energy carrier in subsector.
            Of form: {country_name -> {energy_carrier -> [(float, float)]}}
        """

        if self.product_name not in IndustryInput.sc_historical_data_file_names.keys():
            return None

        sc_his_file_name = IndustryInput.sc_historical_data_file_names[self.product_name]
        return CtsInput.read_energy_carrier_consumption_historical(industry_path, sc_his_file_name)

    def read_production_data(self, industry_path: Path, industry_settings: IndustrySettings) \
            -> dict[str, [(float, float)]]:
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

        dict_prod_his = dict[str, [(float, float)]]()

        production_it = pd.DataFrame(df_product_his).itertuples()
        for row in production_it:
            if str(row.Country) == 'nan':
                continue
            years = df_product_his.columns[1:]
            data = df_product_his[df_product_his["Country"] == row.Country].iloc[0][1:]
            if uty.is_zero(data):
                # country did not product this product at all => skip product for this country
                # print("skipped " + front_label + " for country " + row.Country)
                continue
            zipped = list(zip(years, data))
            his_data = uty.filter_out_nan_and_inf(zipped)
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

        if product_name_general in ["steel_prim", "steel_sec"]:
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
    A container for the preprocessing data regarding the rest sectors_to_do.

    :param Path industry_path: The path to the industry input folder.
    :param dict[str, dc.Heat] dict_heat_levels: The heat levels.

    :ivar dict[str, dict[DemandType, (float, float)]] rest_demand_proportion_basis_year: Used for the calculation of the rest sector.
        It has the following structure: {back_label -> {demand_type -> (rest_sector_percent, demand_2018)}}
    :ivar int rest_calc_basis_year: Year used as a starting point for calculating the rest sector demand.
    :ivar (float, float, float, float) rest_sector_heat_levels: The heat levels used to separate the heat demand in the
        rest sector into the different heat levels.
    """

    def __init__(self, industry_path: Path, dict_heat_levels: dict[str, dc.Heat]):
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
        "steel_direct": FileReadingHelper("Steel_Production.xlsx", "Data_total", [], lambda x: x),
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
    sc_historical_sheet_names = ["Feste fossile Brennstoffe", "Synthetische Gase", "Erdgas", "Oel",
                                 "Erneuerbare Energien", "Abfaelle", "Elektrizitaet", "Waerme"]

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

    subsector_names = [#"Land- und Forstwirtschaft, Fischerei", ???
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
            self.read_energy_carrier_consumption_historical(cts_path, "nrg_bal_s_GHD.xls")

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

    @classmethod
    def read_energy_carrier_consumption_historical(cls, path: Path, filename: str) \
            -> dict[str, [(float, float)]]:
        """
        Reads the historical consumption data split by energy carriers from a nrg_bal file.

        :todo: put this in a spot in the code base that makes sense.
        :param path: The path to the folder of the file
        :param filename: The filename of the file to read.

        :return: If present, the historical quantity of energy carrier in subsector.
            Of form: {country_name -> {energy_carrier -> [(float, float)]}}
        """

        dict_sc_his = dict[str, dict[str, [(float, float)]]]()

        ex_sc_his = pd.ExcelFile(path / filename)

        for sheet_name in IndustryInput.sc_historical_sheet_names:
            df_sc = pd.read_excel(ex_sc_his, sheet_name)
            for _, row in df_sc.iterrows():
                country_name_de = row["GEO/TIME"]
                years = df_sc.columns[1:]
                data = df_sc[df_sc["GEO/TIME"] == country_name_de].iloc[0][1:]

                # convert country name to model-intern english representation
                if country_name_de in Abbreviations.dict_de_en_map.keys():
                    country_name_en = Abbreviations.dict_de_en_map[country_name_de]
                else:
                    continue

                if not uty.is_zero(data):
                    # data exists -> fill into dictionary
                    zipped = list(zip(years, data))
                    his_data = uty.filter_out_nan_and_inf(zipped)
                    if country_name_en not in dict_sc_his.keys():
                        dict_sc_his[country_name_en] = dict()

                    dict_sc_his[country_name_en][sheet_name] = his_data

        return dict_sc_his
