from __future__ import annotations

import math
import os
import warnings
from collections import namedtuple
from pathlib import Path
from typing import Tuple, Any

import output
import utility as uty

import pandas as pd

import control_parameters as cp
import products as prd

CA = namedtuple("CA", ["alpha2", "alpha3", "german_name"])
HisProg = namedtuple("HisProg", ["historical", "prognosis"])
Interval = namedtuple("Interval", ["start", "end"])


class Input:
    """
    The Input class connects all types of input data, that is in the form of excel/csv sheets in the 'input' folder.
    """
    super_path = Path(os.path.abspath(''))
    input_path = super_path / 'input'
    output_path = super_path / 'output'
    general_path = input_path / 'general'
    industry_path = input_path / 'industry'

    ctrl: cp.ControlParameters
    general_input: GeneralInput
    industry_input: IndustryInput
    # Future: add other sector inputs

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
        self.industry_input = IndustryInput(self.industry_path, industry_settings)



class GeneralInput:
    """
    General Input denoted input that is read from the "input/general" folder.
    """
    class PopulationData:
        """
        Holds all data on population. That includes historical data, prognosis data for each country and nuts2 region.
        """

        class Nuts2Region:
            """
            Represents one NUTS2 Region according to individual codes.
            It is build as a tree structure to include sub-regions as child nodes.
            """
            region_name: str
            sub_regions = dict()    # str -> Nuts2Region (python doesn't allow to indicate the type directly)
            historical_data: [(float, float)]
            
            def __init__(self, region_name, historical_data: [(float, float)]):
                self.region_name = region_name
                self.historical_data = historical_data

            def add_child_region(self, region_name: str, nuts2region_obj):
                if len(self.region_name) + 1 is len(region_name):
                    # region is direct subregion
                    self.sub_regions[region_name] = nuts2region_obj
                    return
                elif len(self.region_name) + 1 < len(region_name):
                    # region is a subregion of a subregion, search for right one to insert
                    for key, value in self.sub_regions.items():
                        if region_name.startswith(key):
                            # found parent region
                            self.sub_regions[key].add_child_region(region_name, nuts2region_obj)
                            return
                warnings.warn("Something went wrong when trying to insert the nuts2 subregion " + region_name)

            def get_prog(self, year: int):
                """ Recursively calculate the prognosis for all leaf regions"""
                pass






        country_population: dict[str, HisProg]  # country_name -> historical: [(float, float)], prognosis: [(float, float)]
        nuts2_population: dict[str, Nuts2Region]    # country_name -> (code -> (historical: [(,)], prognosis: [interval, data]))

        def __init__(self, ctrl, df_country_pop_his, df_country_pop_prog, df_nuts2_pop_his, df_nuts2_pop_prog):
            self.country_population = dict[str, HisProg]()
            self.nuts2_population = dict[str, HisProg]()

            # preprocess country population historical data
            dict_c_pop_his = uty.convert_table_to_filtered_data_series_per_country(df_country_pop_his)

            # preprocess country population prognosis
            dict_c_pop_prog = uty.convert_table_to_filtered_data_series_per_country(df_country_pop_prog)

            # preprocess nuts2 population historical data
            df_nuts2_pop_his = df_nuts2_pop_his.drop('GEO/TIME', axis=1)
            dict_nuts2_pop_code_his = uty.convert_table_to_filtered_data_series_per_country(df_nuts2_pop_his)


            for country_name in ctrl.general_settings.active_countries:
                # fill population
                self.country_population[country_name] = HisProg(uty.filter_out_nan_and_inf(dict_c_pop_his[country_name]),
                                                                uty.filter_out_nan_and_inf(dict_c_pop_prog[country_name]))

                # get nuts2 regions data and fill historical as well as prognosis like gdp




    abbreviations: dict[str, CA]
    population: PopulationData
    gdp: dict[str, HisProg[[(float, float)], [Interval, float]]]
    efficiency: dict[str, prd.BAT]

    def __init__(self, ctrl: cp.ControlParameters, path: Path):
        self.abbreviations = dict[str, CA]()
        self.gdp = dict[str, HisProg[[(float, float)], [Interval, float]]]()
        self.efficiency = dict[str, prd.BAT]()

        df_abbr = pd.read_excel(path / "Abbreviations.xlsx")
        df_world_pop_his = pd.read_excel(path / "Population_historical_world.xls")
        df_world_pop_prog = pd.read_excel(path / "Population_projection_world.xlsx")
        df_nuts2_pop_his = pd.read_csv(path / "Population_historical_NUTS2.csv")
        df_nuts2_pop_prog = pd.read_excel(path / "Population_projection_NUTS2.xlsx")
        df_gdp_his = pd.read_excel(path / "GDP_per_capita_historical.xlsx", sheet_name="constant 2015 USD")
        df_gdp_prog_europa = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data")
        df_gdp_prog_world = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data_world")
        df_efficiency = pd.read_excel(path / "Efficiency_Combustion.xlsx")

        # create PopulationData object
        self.population = self.PopulationData(ctrl,
                                              df_world_pop_his, df_world_pop_prog,
                                              df_nuts2_pop_his, df_nuts2_pop_prog)

        # fill efficiency
        for _, row in df_efficiency.iterrows():
            self.efficiency[row["Energy carrier"]] = \
                prd.BAT(row["Electricity production [-]"], row["Heat production [-]"])

        for country_name in ctrl.general_settings.active_countries:
            # fill abbreviations
            self.abbreviations[country_name] = \
                CA(df_abbr[df_abbr["Country_en"] == country_name].get("alpha-2").iloc[0],
                   df_abbr[df_abbr["Country_en"] == country_name].get("alpha-3").iloc[0],
                   df_abbr[df_abbr["Country_en"] == country_name].get("Country_de").iloc[0])

            # read gdp historical
            years = df_gdp_his.columns[3:]
            gdp_data = df_gdp_his[df_gdp_his["Country Code"] == self.abbreviations[country_name].alpha3].iloc[0][3:]
            zipped = list(zip(years, gdp_data))
            gdp_his = uty.filter_out_nan_and_inf(zipped)

            # read gdp prognosis
            interval_conv = lambda xs: [Interval(int(x.split('-')[0]), int(x.split('-')[1])) for x in xs]
            intervals_europa = interval_conv(df_gdp_prog_europa.columns[1:-1])
            intervals_world = interval_conv(df_gdp_prog_world.columns[1:-1])

            zipped_gdp_prog: list[Interval, float]
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

            self.gdp[country_name] = HisProg(gdp_his, zipped_gdp_prog)


class IndustryInput:
    """
        Industry Input denoted input that is read from the "input/industry" folder.
    """
    class ProductInput:
        """
        The Product Input summarizes all input data, that is specific to a certain product type, but holds the
        information for all countries.
        Example product type: steel_prim
        """
        specific_consumption_default: dict[str, prd.SC]
        specific_consumption_historical: dict[str, (float, float)]
        bat: dict[str, prd.BAT]
        production: dict[str, (float, float)]
        heat_levels: output.Heat
        manual_exp_change_rate: float
        perc_used: float

        def __init__(self, sc, bat, prod, sc_h, sc_h_active, heat_levels, manual_exp_change_rate, perc_used):
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

        def __str__(self):
            return "\n\tSpecific Consumption: " + uty.str_dict(self.specific_consumption_default) + \
                "\n\t BAT: " + uty.str_dict(self.bat) + \
                "\n\t Historical: " + uty.str_dict(self.production) + "\n"

    settings: cp.IndustrySettings
    active_products = dict[str, ProductInput]()

    # specify how to access files
    Retrieve = namedtuple("Retrieve", ["file_name", "sheet_name", "skip_rows", "sheet_transform"])
    product_data_access = {
        "steel": Retrieve("Steel_Production.xlsx", "Data_total", [], lambda x: x),
        "steel_prim": Retrieve("Steel_Production.xlsx", "Steel_prim", [], lambda x: x),
        "steel_sec": Retrieve("Steel_Production.xlsx", "Steel_sec", [], lambda x: x),
        "steel_direct": Retrieve("Steel_Production.xlsx", "Data_total", [], lambda x: x),
        "alu_prim": Retrieve("Aluminium_Production.xlsx", "Prim_Data", [], lambda x: x),
        "alu_sec": Retrieve("Aluminium_Production.xlsx", "Sec_Data", [], lambda x: x),
        "copper_prim": Retrieve("Copper_Production.xlsx", "Copper_WSP", [0, 1],
                                lambda x: x.loc[x["Type"] == "Primary"].drop("Type", axis=1)),
        "copper_sec": Retrieve("Copper_Production.xlsx", "Copper_WSP", [0, 1],
                               lambda x: x.loc[x["Type"] == "Secondary"].drop("Type", axis=1)),
        "chlorine": Retrieve("Chlorine_Production.xlsx", "Data", [], lambda x: x),
        "ammonia": Retrieve("Ammonia_Production.xlsx", "Data", [], lambda x: x),
        "methanol": Retrieve("Methanol_Production.xlsx", "Data", [], lambda x: x),
        "ethylene": Retrieve("Ethylene_Production.xlsx", "Data", [], lambda x: x),
        "propylene": Retrieve("Propylene_Production.xlsx", "Data", [], lambda x: x),
        "aromate": Retrieve("Aromate_Production.xlsx", "Data", [], lambda x: x),
        "ammonia_classic": Retrieve("Ammonia_Production.xlsx", "Data", [], lambda x: x),
        "methanol_classic": Retrieve("Methanol_Production.xlsx", "Data", [], lambda x: x),
        "ethylene_classic": Retrieve("Ethylene_Production.xlsx", "Data", [], lambda x: x),
        "propylene_classic": Retrieve("Propylene_Production.xlsx", "Data", [], lambda x: x),
        "aromate_classic": Retrieve("Aromate_Production.xlsx", "Data", [], lambda x: x),
        "paper": Retrieve("Paper_Production.xlsx", "Data", [], lambda x: x),
        "cement": Retrieve("Cement_Production.xlsx", "Data", [], lambda x: x),
        "glass": Retrieve("Glass_Production.xlsx", "Data", [], lambda x: x),
    }
    sc_historical_data_file_names = {
        "steel": "nrg_bal_s_steel.xls",
        "paper": "nrg_bal_s_paper.xls"
    }
    sc_historical_sheet_names = ["Feste fossile Brennstoffe", "Synthetische Gase", "Erdgas", "Oel",
                                 "Erneuerbare Energien", "Abfaelle", "Elektrizitaet", "Waerme"]

    def __init__(self, industry_path: Path, industry_settings: cp.IndustrySettings):
        self.settings = industry_settings

        ex_spec = pd.ExcelFile(industry_path / "Specific_Consumption.xlsx")
        ex_bat = pd.ExcelFile(industry_path / "BAT_Consumption.xlsx")

        # read heat levels
        df_heat_levels = pd.read_excel(industry_path / "Heat_levels.xlsx")
        dict_heat_levels = dict()

        for _, row in df_heat_levels.iterrows():
            dict_heat_levels[row["Industry"]] = output.Heat(row["Q1"], row["Q2"], row["Q3"], row["Q4"])

        # read the active sectors sheets
        for product_name in self.settings.active_product_names:
            if product_name == 'unspecified industry':
                continue

            # read production data
            retrieve_prod = self.product_data_access[product_name]
            ex_product_his = \
                self.product_data_access[product_name].sheet_transform(
                    pd.read_excel(industry_path / retrieve_prod.file_name, retrieve_prod.sheet_name,
                                  skiprows=retrieve_prod.skip_rows))

            dict_prod_his = dict()

            production_it = pd.DataFrame(ex_product_his).itertuples()
            for row in production_it:
                if str(row.Country) == 'nan':
                    continue
                years = ex_product_his.columns[1:]
                data = ex_product_his[ex_product_his["Country"] == row.Country].iloc[0][1:]
                if uty.is_zero(data):
                    # country did not product this product at all => skip product for this country
                    # print("skipped " + product_name + " for country " + row.Country)
                    continue
                zipped = list(zip(years, data))
                his_data = uty.filter_out_nan_and_inf(zipped)
                his_data = uty.cut_after_x(his_data, industry_settings.last_available_year)
                dict_prod_his[row.Country] = his_data

            # read specific consumption default data
            prod_sc = pd.read_excel(ex_spec, sheet_name=product_name)
            dict_prod_sc_country = dict()

            for _, row in pd.DataFrame(prod_sc).iterrows():
                dict_prod_sc_country[row.Country] = \
                    prd.SC(row["Spec electricity consumption [GJ/t]"],
                           row["Spec heat consumption [GJ/t]"],
                           row["Spec hydrogen consumption [GJ/t]"],
                           row["max. subst. of heat with H2 [%]"])

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
                        country_name = row["GEO/TIME"]
                        years = df_sc.columns[1:]
                        data = df_sc[df_sc["GEO/TIME"] == country_name].iloc[0][1:]

                        if not uty.is_zero(data):
                            # data exists -> fill into dictionary
                            zipped = list(zip(years, data))
                            his_data = uty.filter_out_nan_and_inf(zipped)
                            his_data = uty.cut_after_x(his_data, industry_settings.last_available_year)

                            if country_name not in dict_sc_his.keys():
                                dict_sc_his[country_name] = dict()

                            dict_sc_his[country_name][sheet_name] = his_data

            # read bat consumption data
            df_prod_bat = pd.read_excel(ex_bat, sheet_name=product_name)
            dict_prod_bat_country = dict()

            for _, row in df_prod_bat.iterrows():
                dict_prod_bat_country[row.Country] = \
                    prd.BAT(row["Spec electricity consumption [GJ/t]"],
                            row["Spec heat consumption [GJ/t]"])

            self.active_products[product_name] = \
                self.ProductInput(dict_prod_sc_country, dict_prod_bat_country, dict_prod_his, dict_sc_his, sc_his_calc,
                                  dict_heat_levels[product_name],
                                  industry_settings.product_settings[product_name].manual_exp_change_rate,
                                  industry_settings.product_settings[product_name].perc_used)

        print("Input was successfully read.")
