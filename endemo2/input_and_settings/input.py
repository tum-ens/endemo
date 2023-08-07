"""
This module is responsible for reading the input data form files.
(except the Set_and_Control_Parameters. That would be in control_parameters.)
"""

from __future__ import annotations

import math
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from endemo2.data_structures.enumerations import GroupType, DemandType
from endemo2 import utility as uty
from endemo2.data_structures import containers as dc
from endemo2.input_and_settings import control_parameters as cp


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

    # Future TODO: add other sector inputs

    def __init__(self):
        ctrl_ex = pd.ExcelFile(self.input_path / 'Set_and_Control_Parameters.xlsx')

        # read control parameters
        general_settings = cp.GeneralSettings(pd.read_excel(ctrl_ex, sheet_name="GeneralSettings"),
                                              pd.read_excel(ctrl_ex, sheet_name="Countries"))
        industry_settings = \
            cp.IndustrySettings(
                pd.read_excel(ctrl_ex, sheet_name="IND_general"),
                pd.read_excel(ctrl_ex, sheet_name="IND_subsectors"))

        self.ctrl = cp.ControlParameters(general_settings, industry_settings)

        # read general
        self.general_input = GeneralInput(self.ctrl, self.general_path)

        # read industry
        self.industry_input = IndustryInput(self.industry_path, industry_settings, self.general_input.abbreviations,
                                            self.ctrl.general_settings.active_countries)


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
        It is of the form {country_name -> historical: [(float, float)], prognosis: [(float, float)]}
    :ivar dict[str, [(str, [float, float])]] nuts2_population: Data for the population of NUTS2 regions.
        It is of the form {country_name -> (code -> (historical: [(float,float)], prognosis: [interval, growth rate]))}
    """

    def __init__(self, ctrl: cp.ControlParameters, nuts2_valid_regions: set, abbreviations: dict,
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
            abbrev = abbreviations[country_name].alpha2
            self.nuts2_population[country_name] = \
                dc.HisProg(dict_nuts2_pop_his[abbrev], dict_nuts2_pop_prog[abbrev])


class GeneralInput:
    """
    General Input contains all preprocessing that is read from the "preprocessing/general" folder.

    :param ControlParameters ctrl: The parsed Set_and_Control_Parameters.xlsx
    :param Path path: The path to the preprocessing/general folder

    :ivar dict[str, ("alpha2", "alpha3", "german_name")] abbreviations: The abbreviations for each country.
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
            # fill abbreviations
            self.abbreviations[country_name] = \
                dc.CA(df_abbr[df_abbr["Country_en"] == country_name].get("alpha-2").iloc[0],
                      df_abbr[df_abbr["Country_en"] == country_name].get("alpha-3").iloc[0],
                      df_abbr[df_abbr["Country_en"] == country_name].get("Country_de").iloc[0])

            # read gdp historical
            years = df_gdp_his.columns[3:]
            gdp_data = df_gdp_his[df_gdp_his["Country Code"] == self.abbreviations[country_name].alpha3].iloc[0][3:]
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
    The Product Input summarizes all preprocessing data, that is specific to a certain product type, but holds the
    information for all countries_in_group. Example product type: steel_prim

    :param sc: specific_consumption_default
    :param bat: bat
    :param prod: production
    :param sc_h: specific_consumption_historical
    :param sc_h_active: Indicates whether specific consumption should be calculated from historical data.
    :param heat_levels: heat_levels
    :param manual_exp_change_rate: manual_exp_change_rate
    :param perc_used: perc_used

    :ivar str product_name: The name of the product.
    :ivar dict[str, containers.SC] specific_consumption_default: Default specific consumption value for this product.
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
        Structure {country_name -> {nuts2_region_name -> capacity_value}}
    :ivar dict[str, [[str]]] country_groups: Input from country group file,
        structured as {group_type -> list_of_groups}.
    """

    def __init__(self, name, sc, bat, prod, sc_h, sc_h_active, heat_levels, manual_exp_change_rate, perc_used,
                 nuts2_installed_capacity, country_groups):
        self.product_name = name
        self.specific_consumption_default = sc
        self.bat = bat
        self.production = prod
        if sc_h_active:
            self.specific_consumption_historical = sc_h
        else:
            self.specific_consumption_historical = dict()
        self.heat_levels = heat_levels
        self.manual_exp_change_rate = manual_exp_change_rate

        self.perc_used = float(perc_used) if not math.isnan(float(perc_used)) else 1
        self.nuts2_installed_capacity = nuts2_installed_capacity
        self.country_groups = country_groups

    def __str__(self):
        return "\n\tSpecific Consumption: " + uty.str_dict(self.specific_consumption_default) + \
            "\n\t BAT: " + uty.str_dict(self.bat) + \
            "\n\t Historical: " + uty.str_dict(self.production) + "\n"


class RestSectorInput:
    """
    A container for the preprocessing data regarding the rest sectors_to_do.

    :ivar dict[str, dict[DemandType, (float, float)]] rest_calc_data: Used for the calculation of the rest sector.
        It has the following structure: {country_name -> {demand_type -> (rest_sector_percent, demand_2018)}}
    :ivar int rest_calc_basis_year: Year used as a starting point for calculating the rest sector demand.
    :ivar (float, float, float, float) rest_sector_heat_levels: The heat levels used to separate the heat demand in the
        rest sector into the different heat levels.
    """

    def __init__(self, df_rest_calc: pd.DataFrame, dict_heat_levels: dict[str, dc.Heat]):
        self.rest_calc_basis_year = 2018  # change here, if another year should be used for rest sector (also path)
        self.rest_sector_heat_levels = dict_heat_levels["rest"]
        self.rest_calc_data = dict()
        for _, row in df_rest_calc.iterrows():
            self.rest_calc_data[row["Country"]] = dict()
            self.rest_calc_data[row["Country"]][DemandType.ELECTRICITY] = \
                (row["Rest el"] / 100, row["electricity " + str(self.rest_calc_basis_year)])
            self.rest_calc_data[row["Country"]][DemandType.HEAT] = \
                (row["Rest heat"] / 100, row["heat " + str(self.rest_calc_basis_year)])


class FileReadingHelper:
    """
    A helper class to read products historical data. It provides some fixed transformation operations.

    :ivar str file_name: The files name, relative to the path variable.
    :ivar str sheet_name: The name of the sheet that is to be read from the file.
    :ivar [int] skip_rows: These rows(!) will be skipped when reading the dataframe. Done by numerical index.
    :ivar lambda[pd.Dataframe -> pd.Dataframe] sheet_transform: A transformation operation on the dataframe
    :ivar pd.Dataframe df: The current dataframe.
    :ivar Path path: The path to the folder, where the file is.
        It can to be set after constructing the FileReadingHelper Object.
    """

    def __init__(self, file_name: str, sheet_name: str, skip_rows: [int], sheet_transform):
        self.file_name = file_name
        self.sheet_name = sheet_name
        self.skip_rows = skip_rows
        self.sheet_transform = sheet_transform
        self.df = None
        self.path = None

    def set_path_and_read(self, path: Path) -> None:
        """
        Sets the path variable and reads the file with name self.file_name in the path folder.

        :param path: The path, where the file lies.
        """
        self.path = path
        self.df = self.sheet_transform(pd.read_excel(self.path / self.file_name, self.sheet_name,
                                                     skiprows=self.skip_rows))

    def skip_years(self, skip_years: [int]) -> None:
        """
        Filters the skip years from the current dataframe.

        :param skip_years: The list of years to skip.
        """
        if self.df is None:
            warnings.warn("Trying to skip years in products historical data without having called set_path_and_read"
                          " on the Retrieve object.")
        # skip years
        for skip_year in skip_years:
            if skip_year in self.df.columns:
                self.df.drop(skip_year, axis=1, inplace=True)

    def get(self) -> pd.DataFrame:
        """
        Getter for the dataframe.

        :return: The current dataframe, which is filtered depending on previous function calls on this class.
        """
        if self.df is None:
            warnings.warn("Trying to retrieve products historical data without having called set_path_and_read on "
                          "the Retrieve object.")
        return self.df


class IndustryInput:
    """
    Industry Input denoted preprocessing that is read from the "preprocessing/industry" folder.

    :param industry_path: The path to the industry folder.
    :param industry_settings: The parsed sector-specific settings for the industry sector.

    :ivar dict[str, ProductInput] active_products: Stores the product specific preprocessing for all active products.
    :ivar IndustrySettings settings: Stores the sector-specific settings for industry.
    :ivar dict[str, Retrieve] product_data_access: Specify how data sheets for each product should be accessed
    :ivar dict[str, str] sc_historical_data_file_names: The file names of the files used for certain products to read
        historical information on specific consumption.
    :ivar [str] sc_historical_sheet_names: The sheet names for the files used to read
        historical information on specific consumption for certain products.
    :ivar RestSectorInput rest_sector_input: All preprocessing data relating to the rest sector.
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

    def __init__(self, industry_path: Path, industry_settings: cp.IndustrySettings, abbreviations: dict,
                 active_countries: [str]):
        self.settings = industry_settings
        self.active_products = dict[str, ProductInput]()

        ex_spec = pd.ExcelFile(industry_path / "Specific_Consumption.xlsx")
        ex_bat = pd.ExcelFile(industry_path / "BAT_Consumption.xlsx")
        ex_nuts2_ic = pd.ExcelFile(industry_path / "Installed_capacity_NUTS2.xlsx")
        ex_country_groups = pd.ExcelFile(industry_path / "Country_Groups.xlsx")

        # read heat levels
        df_heat_levels = pd.read_excel(industry_path / "Heat_levels.xlsx")
        dict_heat_levels = dict()

        for _, row in df_heat_levels.iterrows():
            dict_heat_levels[row["Industry"]] = dc.Heat(row["Q1"] / 100, row["Q2"] / 100, row["Q3"] / 100,
                                                        row["Q4"] / 100)

        # read rest sector calculation data
        df_rest_calc = pd.read_excel(industry_path / "Ind_energy_demand_2018_Trend_Restcalcul.xlsx")
        self.rest_sector_input = RestSectorInput(df_rest_calc, dict_heat_levels)

        # read the active sectors_to_do sheets
        for product_name in self.settings.active_product_names:
            if product_name == 'unspecified industry':
                continue

            # read production data
            retrieve_prod = self.product_data_access[product_name]
            retrieve_prod.set_path_and_read(industry_path)
            retrieve_prod.skip_years(industry_settings.skip_years)
            df_product_his = retrieve_prod.get()

            dict_prod_his = dict()

            production_it = pd.DataFrame(df_product_his).itertuples()
            for row in production_it:
                if str(row.Country) == 'nan':
                    continue
                years = df_product_his.columns[1:]
                data = df_product_his[df_product_his["Country"] == row.Country].iloc[0][1:]
                if uty.is_zero(data):
                    # country did not product this product at all => skip product for this country
                    # print("skipped " + product_name + " for country " + row.Country)
                    continue
                zipped = list(zip(years, data))
                his_data = uty.filter_out_nan_and_inf(zipped)
                his_data = uty.cut_after_x(his_data, industry_settings.last_available_year - 1)
                dict_prod_his[row.Country] = his_data

            # read specific consumption default data
            prod_sc = pd.read_excel(ex_spec, sheet_name=product_name)
            dict_prod_sc_country = dict()

            for _, row in pd.DataFrame(prod_sc).iterrows():
                dict_prod_sc_country[row.Country] = \
                    dc.SC(row["Spec electricity consumption [GJ/t]"],
                          row["Spec heat consumption [GJ/t]"],
                          row["Spec hydrogen consumption [GJ/t]"],
                          row["max. subst. of heat with H2 [%]"])

            # create country_name_de -> country_name_en mapping
            dict_de_en_map = dict()
            for name_en, (alpha2, alpha3, name_de) in abbreviations.items():
                dict_de_en_map[name_de] = name_en

            # read specific demand historical data
            dict_sc_his = dict()
            sc_his_calc = False
            if product_name in self.sc_historical_data_file_names.keys():
                sc_his_calc = True

                sc_his_file_name = self.sc_historical_data_file_names[product_name]
                ex_sc_his = pd.ExcelFile(industry_path / sc_his_file_name)

                for sheet_name in self.sc_historical_sheet_names:
                    df_sc = pd.read_excel(ex_sc_his, sheet_name)
                    for _, row in df_sc.iterrows():
                        country_name_de = row["GEO/TIME"]
                        years = df_sc.columns[1:]
                        data = df_sc[df_sc["GEO/TIME"] == country_name_de].iloc[0][1:]

                        # convert country name to model-intern english representation
                        if country_name_de in dict_de_en_map.keys():
                            country_name_en = dict_de_en_map[country_name_de]
                        else:
                            continue

                        if not uty.is_zero(data):
                            # data exists -> fill into dictionary
                            zipped = list(zip(years, data))
                            his_data = uty.filter_out_nan_and_inf(zipped)
                            # his_data = uty.cut_after_x(his_data, industry_settings.last_available_year)

                            if country_name_en not in dict_sc_his.keys():
                                dict_sc_his[country_name_en] = dict()

                            dict_sc_his[country_name_en][sheet_name] = his_data

            # read bat consumption data
            df_prod_bat = pd.read_excel(ex_bat, sheet_name=product_name)
            dict_prod_bat_country = dict()

            for _, row in df_prod_bat.iterrows():
                dict_prod_bat_country[row.Country] = \
                    dc.EH(row["Spec electricity consumption [GJ/t]"],
                          row["Spec heat consumption [GJ/t]"])

            # create alpha2 -> country_name_en mapping
            dict_2_en_map = dict()
            for name_en, (alpha2, alpha3, name_de) in abbreviations.items():
                dict_2_en_map[alpha2] = name_en

            # read NUTS2 installed capacity
            dict_installed_capacity_nuts2 = dict[str, dict[str, float]]()

            product_name_general = product_name
            if product_name_general.endswith("_classic"):
                product_name_general = product_name_general.removesuffix("_classic")
            if product_name_general in ["steel_prim", "steel_sec"]:
                # PLACEHOLDER until steel is finished in sheets. TODO: remove when steel is correct in sheet
                product_name_general = "steel"
            df_nuts2_ic = pd.read_excel(ex_nuts2_ic, product_name_general)
            for _, row in df_nuts2_ic.iterrows():
                nuts2 = row["NUTS2"]
                alpha2 = nuts2[:2]
                if alpha2 not in dict_2_en_map.keys():
                    continue
                country_name_en = dict_2_en_map[nuts2[:2]]
                if country_name_en not in dict_installed_capacity_nuts2.keys():
                    dict_installed_capacity_nuts2[country_name_en] = dict[str, float]()
                perc_value = row[product_name_general + " %"]
                dict_installed_capacity_nuts2[country_name_en][nuts2] = perc_value if not np.isnan(perc_value) else 0.0

            # read country groups
            country_groups = dict[str, [[str]]](
                {GroupType.SEPARATE: [], GroupType.JOINED: [], GroupType.JOINED_DIVERSIFIED: []})

            df_country_groups = pd.read_excel(ex_country_groups, sheet_name="Example")  # sheet_name=product_name)

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
                country_groups[group_type].append(new_group)
                grouped_countries |= set(new_group)
            if all_others_group_type is not None:
                country_groups[all_others_group_type] = [country for country in all_countries if
                                                         country not in grouped_countries]

            # finally store in product data class
            self.active_products[product_name] = \
                ProductInput(product_name, dict_prod_sc_country, dict_prod_bat_country, dict_prod_his, dict_sc_his,
                             sc_his_calc, dict_heat_levels[product_name],
                             industry_settings.product_settings[product_name].manual_exp_change_rate,
                             industry_settings.product_settings[product_name].perc_used,
                             dict_installed_capacity_nuts2, country_groups)


