from __future__ import annotations
import os
from collections import namedtuple
from pathlib import Path
from typing import Tuple, Any
import utility as uty

import pandas as pd

from control_parameters import ControlParameters, GeneralSettings, CountrySettings, IndustrySettings
from products import Product, SC, BAT

CA = namedtuple("CA", ["abbreviation", "german"])
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
        general_settings = GeneralSettings(pd.read_excel(ctrl_ex, sheet_name="GeneralSettings"))
        country_settings = \
            CountrySettings(pd.read_excel(ctrl_ex, sheet_name="Countries"))
        industry_settings = \
            IndustrySettings(
                pd.read_excel(ctrl_ex, sheet_name="IND_general"),
                pd.read_excel(ctrl_ex, sheet_name="IND_subsectors"))

        self.ctrl = ControlParameters(general_settings, country_settings, industry_settings)

        # read general
        self.general_input = GeneralInput(self.ctrl, self.general_path)

        # read industry
        self.industry_input = IndustryInput(self.industry_path, industry_settings)


class GeneralInput:
    abbreviations: dict[str, CA]
    population: dict[str, HisProg]
    gpa: dict[str, HisProg[[(float, float)], [Interval, float]]]

    def __init__(self, ctrl: ControlParameters, path: Path):
        abbr_ex = pd.read_excel(path / "Abbreviations.xlsx")
        pop_his_ex = pd.read_excel(path / "Population_historical_world.xls")
        pop_prog_ex = pd.read_excel(path / "Population_projection_world.xlsx")
        gdp_his_ex = pd.read_excel(path / "GDP_per_capita_historical.xlsx")
        gdp_prog_ex = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx")

        pop_his_dict = dict()
        pop_prog_dict = dict()

        pop_it = pd.DataFrame(pop_his_ex).itertuples()
        for row in pop_it:
            country_name = row[1]
            zipped = list(zip(list(pop_his_ex)[1:], row[2:]))
            his_data = uty.filter_out_NaN_and_Inf(zipped)
            pop_his_dict[country_name] = his_data

        pop_it = pd.DataFrame(pop_prog_ex).itertuples()
        for row in pop_it:
            country_name = row[1]
            zipped = list(zip(list(pop_prog_ex)[1:], row[2:]))
            prog_data = uty.filter_out_NaN_and_Inf(zipped)
            pop_prog_dict[country_name] = prog_data

        for country_name in ctrl.country_settings.active_countries:
            # fill abbreviations
            self.abbreviations = dict()
            self.abbreviations[country_name] = \
                CA(abbr_ex[abbr_ex["Country"] == country_name].get("Abbreviation").iloc[0],
                   abbr_ex[abbr_ex["Country"] == country_name].get("Country_de").iloc[0])

            # fill population
            self.population = dict()
            self.population[country_name] = HisProg(pop_his_dict[country_name], pop_prog_dict[country_name])


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

        spec_ex = pd.ExcelFile(path / "Specific_Consumption.xlsx")
        bat_ex = pd.ExcelFile(path / "BAT_Consumption.xlsx")

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
            prod_sc = pd.read_excel(spec_ex, sheet_name=product_name)
            prod_sc_country_dict = dict()

            sc_it = pd.DataFrame(prod_sc).itertuples()
            for row in sc_it:
                prod_sc_country_dict[row.Country] = SC(row._3, row._4, row._6, row._5)

            # read bat consumption data
            prod_bat = pd.read_excel(bat_ex, sheet_name=product_name)
            prod_bat_country_dict = dict()

            bat_it = pd.DataFrame(prod_bat).itertuples()
            for row in bat_it:
                prod_bat_country_dict[row.Country] = BAT(row._3, row._4)
