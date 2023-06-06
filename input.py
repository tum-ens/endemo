from __future__ import annotations
import os
import warnings
from collections import namedtuple
from pathlib import Path
from typing import Tuple, Any
import utility as uty

import pandas as pd

from control_parameters import ControlParameters, GeneralSettings, IndustrySettings
from products import Product, SC, BAT

CA = namedtuple("CA", ["alpha2", "alpha3", "german_name"])
HisProg = namedtuple("HisProg", ["historical", "prognosis"])
Interval = namedtuple("Interval", ["start", "end"])


class Input:
    super_path = Path(os.path.abspath(''))
    input_path = super_path / 'input'
    general_path = input_path / 'general'
    industry_path = input_path / 'industry'

    ctrl: ControlParameters
    general_input: GeneralInput
    industry_input: IndustryInput

    def __init__(self):
        ctrl_ex = pd.ExcelFile(self.input_path / 'Set_and_Control_Parameters.xlsx')

        # read control parameters
        general_settings = GeneralSettings(pd.read_excel(ctrl_ex, sheet_name="GeneralSettings"),
                                           pd.read_excel(ctrl_ex, sheet_name="Countries"))
        industry_settings = \
            IndustrySettings(
                pd.read_excel(ctrl_ex, sheet_name="IND_general"),
                pd.read_excel(ctrl_ex, sheet_name="IND_subsectors"))

        self.ctrl = ControlParameters(general_settings, industry_settings)

        # read general
        self.general_input = GeneralInput(self.ctrl, self.general_path)

        # read industry
        self.industry_input = IndustryInput(self.industry_path, industry_settings)


class GeneralInput:
    abbreviations = dict[str, CA]()
    population = dict[str, HisProg]()
    gdp = dict[str, HisProg[[(float, float)], [Interval, float]]]()

    def __init__(self, ctrl: ControlParameters, path: Path):
        ex_abbr = pd.read_excel(path / "Abbreviations.xlsx")
        ex_pop_his = pd.read_excel(path / "Population_historical_world.xls")
        ex_pop_prog = pd.read_excel(path / "Population_projection_world.xlsx")
        ex_gdp_his = pd.read_excel(path / "GDP_per_capita_historical.xlsx", sheet_name="constant 2015 USD")
        ex_gdp_prog_europa = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data")
        ex_gdp_prog_world = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data_world")

        # preprocess population historical data
        dict_pop_his = dict()
        pop_it = pd.DataFrame(ex_pop_his).itertuples()
        for row in pop_it:
            country_name = row[1]
            zipped = list(zip(list(ex_pop_his)[1:], row[2:]))
            his_data = uty.filter_out_NaN_and_Inf(zipped)
            dict_pop_his[country_name] = his_data

        # preprocess population prognosis
        dict_pop_prog = dict()
        pop_it = pd.DataFrame(ex_pop_prog).itertuples()
        for row in pop_it:
            country_name = row[1]
            zipped = list(zip(list(ex_pop_prog)[1:], row[2:]))
            prog_data = uty.filter_out_NaN_and_Inf(zipped)
            dict_pop_prog[country_name] = prog_data

        for country_name in ctrl.general_settings.active_countries:
            # fill abbreviations
            self.abbreviations[country_name] = \
                CA(ex_abbr[ex_abbr["Country_en"] == country_name].get("alpha-2").iloc[0],
                   ex_abbr[ex_abbr["Country_en"] == country_name].get("alpha-3").iloc[0],
                   ex_abbr[ex_abbr["Country_en"] == country_name].get("Country_de").iloc[0])

            # fill population
            self.population[country_name] = HisProg(dict_pop_his[country_name], dict_pop_prog[country_name])

            # read gdp historical
            years = ex_gdp_his.columns[3:]
            gdp_data = ex_gdp_his[ex_gdp_his["Country Code"] == self.abbreviations[country_name].alpha3].iloc[0][3:]
            zipped = list(zip(years, gdp_data))
            gdp_his = uty.filter_out_NaN_and_Inf(zipped)

            # read gdp prognosis
            interval_conv = lambda xs: [Interval(int(x.split('-')[0]), int(x.split('-')[1])) for x in xs]
            intervals_europa = interval_conv(ex_gdp_prog_europa.columns[1:-1])
            intervals_world = interval_conv(ex_gdp_prog_world.columns[1:-1])

            zipped_gdp_prog: list[Interval, float]
            if country_name in list(ex_gdp_prog_europa["Country"]):
                gdp_prog = ex_gdp_prog_europa[ex_gdp_prog_europa["Country"] == country_name].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_europa, gdp_prog))
            elif country_name in list(ex_gdp_prog_world["Country"]):
                gdp_prog = ex_gdp_prog_world[ex_gdp_prog_world["Country"] == country_name].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_world, gdp_prog))
            else:
                warnings.warn("Attention! For country \"" + country_name
                              + "\" no gdp prognosis data was found. Data from \"all\" is used instead now.")
                gdp_prog = ex_gdp_prog_europa[ex_gdp_prog_europa["Country"] == "all"].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_europa, gdp_prog))

            self.gdp[country_name] = HisProg(gdp_his, zipped_gdp_prog)


class IndustryInput:
    class ProductInput:
        specific_consumption: dict[str, SC]
        bat: dict[str, BAT]
        production: dict[str, (float, float)]

    settings: IndustrySettings
    active_products: dict[str, ProductInput]

    def __init__(self, path: Path, industry_settings):
        self.settings = industry_settings

        # specify how to access files
        Retrieve = namedtuple("Retrieve", ["file_name", "sheet_name", "sheet_transform"])
        data_access_spec = {"steel": Retrieve("Steel_Production.xlsx", "Data_total", lambda x: x),
                            "steel_prim": Retrieve("Steel_Production.xlsx", "Steel_prim", lambda x: x),
                            "steel_sec": Retrieve("Steel_Production.xlsx", "Steel_sec", lambda x: x),
                            "steel_direct": Retrieve("Steel_Production.xlsx", "Data_total", lambda x: x),
                            "alu_prim": Retrieve("Aluminium_Production.xlsx", "Prim_Data", lambda x: x),
                            "alu_sec": Retrieve("Aluminium_Production.xlsx", "Sec_Data_const", lambda x: x),
                            "copper_prim": Retrieve("Copper_Production.xlsx", "Copper_WSP",
                                                    lambda x: x.loc[x["Type"] == "Primary"].drop("Type", axis=1)),
                            "copper_sec": Retrieve("Copper_Production.xlsx", "Copper_WSP",
                                                   lambda x: x.loc[x["Type"] == "Secondary"].drop("Type", axis=1)),
                            "chlorine": Retrieve("Chlorin_Production.xlsx", "Data", lambda x: x),
                            "ammonia": Retrieve("Ammonia_Production.xlsx", "Data_const", lambda x: x),
                            "methanol": Retrieve("Methanol_Production.xlsx", "Data_const", lambda x: x),
                            "ethylene": Retrieve("Ethylene_Production.xlsx", "Data_const", lambda x: x),
                            "propylene": Retrieve("Propylene_Production.xlsx", "Data_const", lambda x: x),
                            "aromate": Retrieve("Aromate_Production.xlsx", "Data_const", lambda x: x),
                            "ammonia_classic": Retrieve("Ammonia_Production.xlsx", "Data_const", lambda x: x),
                            "methanol_classic": Retrieve("Methanol_Production.xlsx", "Data_const", lambda x: x),
                            "ethylene_classic": Retrieve("Ethylene_Production.xlsx", "Data_const", lambda x: x),
                            "propylene_classic": Retrieve("Propylene_Production.xlsx", "Data_const", lambda x: x),
                            "aromate_classic": Retrieve("Aromate_Production.xlsx", "Data_const", lambda x: x),
                            "paper": Retrieve("Paper_Production.xlsx", "Data", lambda x: x),
                            "cement": Retrieve("Cement_Production.xlsx", "Data", lambda x: x),
                            "glass": Retrieve("Glass_Production.xlsx", "Data_const",
                                              lambda x: x.drop('Comment', axis=1)),
                            }

        ex_spec = pd.ExcelFile(path / "Specific_Consumption.xlsx")
        ex_bat = pd.ExcelFile(path / "BAT_Consumption.xlsx")

        # read the active sectors sheets
        for product_name in self.settings.active_product_names:
            if product_name == 'unspecified industry':
                continue

            # read production data
            retrieve_prod = data_access_spec[product_name]
            product_historical_data = \
                data_access_spec[product_name].sheet_transform(
                    pd.read_excel(path / retrieve_prod.file_name, retrieve_prod.sheet_name))

            # read specific consumption data
            prod_sc = pd.read_excel(ex_spec, sheet_name=product_name)
            dict_prod_sc_country = dict()

            sc_it = pd.DataFrame(prod_sc).itertuples()
            for row in sc_it:
                dict_prod_sc_country[row.Country] = SC(row._3, row._4, row._6, row._5)

            # read bat consumption data
            prod_bat = pd.read_excel(ex_bat, sheet_name=product_name)
            dict_prod_bat_country = dict()

            bat_it = pd.DataFrame(prod_bat).itertuples()
            for row in bat_it:
                dict_prod_bat_country[row.Country] = BAT(row._3, row._4)
