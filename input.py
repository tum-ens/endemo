from __future__ import annotations
import os
import warnings
from collections import namedtuple
from pathlib import Path
from typing import Tuple, Any
import utility as uty

import pandas as pd

import control_parameters as cp
import products as prd

CA = namedtuple("CA", ["alpha2", "alpha3", "german_name"])
HisProg = namedtuple("HisProg", ["historical", "prognosis"])
Interval = namedtuple("Interval", ["start", "end"])


class Input:
    super_path = Path(os.path.abspath(''))
    input_path = super_path / 'input'
    general_path = input_path / 'general'
    industry_path = input_path / 'industry'

    ctrl: cp.ControlParameters
    general_input: GeneralInput
    industry_input: IndustryInput

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
    abbreviations = dict[str, CA]()
    population = dict[str, HisProg]()
    gdp = dict[str, HisProg[[(float, float)], [Interval, float]]]()
    efficiency = dict[str, prd.BAT]

    def __init__(self, ctrl: cp.ControlParameters, path: Path):
        ex_abbr = pd.read_excel(path / "Abbreviations.xlsx")
        ex_pop_his = pd.read_excel(path / "Population_historical_world.xls")
        ex_pop_prog = pd.read_excel(path / "Population_projection_world.xlsx")
        ex_gdp_his = pd.read_excel(path / "GDP_per_capita_historical.xlsx", sheet_name="constant 2015 USD")
        ex_gdp_prog_europa = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data")
        ex_gdp_prog_world = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data_world")
        ex_efficiency = pd.read_excel(path / "Efficiency_Combustion.xlsx")

        # fill efficiency
        for _, row in ex_efficiency.iterrows():
            self.efficiency[row["Energy carrier"]] = \
                prd.BAT(row["Electricity production [-]"], row["Heat production [-]"])

        # preprocess population historical data
        dict_pop_his = dict()
        pop_it = pd.DataFrame(ex_pop_his).itertuples()
        for row in pop_it:
            country_name = row[1]
            zipped = list(zip(list(ex_pop_his)[1:], row[2:]))
            his_data = uty.filter_out_nan_and_inf(zipped)
            dict_pop_his[country_name] = his_data

        # preprocess population prognosis
        dict_pop_prog = dict()
        pop_it = pd.DataFrame(ex_pop_prog).itertuples()
        for row in pop_it:
            country_name = row[1]
            zipped = list(zip(list(ex_pop_prog)[1:], row[2:]))
            prog_data = uty.filter_out_nan_and_inf(zipped)
            dict_pop_prog[country_name] = prog_data

        for country_name in ctrl.general_settings.active_countries:
            # fill abbreviations
            self.abbreviations[country_name] = \
                CA(ex_abbr[ex_abbr["Country_en"] == country_name].get("alpha-2").iloc[0],
                   ex_abbr[ex_abbr["Country_en"] == country_name].get("alpha-3").iloc[0],
                   ex_abbr[ex_abbr["Country_en"] == country_name].get("Country_de").iloc[0])

            # fill population
            self.population[country_name] = HisProg(uty.filter_out_nan_and_inf(dict_pop_his[country_name]),
                                                    uty.filter_out_nan_and_inf(dict_pop_prog[country_name]))

            # read gdp historical
            years = ex_gdp_his.columns[3:]
            gdp_data = ex_gdp_his[ex_gdp_his["Country Code"] == self.abbreviations[country_name].alpha3].iloc[0][3:]
            zipped = list(zip(years, gdp_data))
            gdp_his = uty.filter_out_nan_and_inf(zipped)

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
        specific_consumption_default: dict[str, prd.SC]
        specific_consumption_historical: dict[str, (float, float)]
        bat: dict[str, prd.BAT]
        production: dict[str, (float, float)]

        def __init__(self, sc, bat, prod, sc_h, sc_h_active):
            self.specific_consumption_default = sc
            self.bat = bat
            self.production = prod
            if sc_h_active:
                self.specific_consumption_historical = sc_h
            else:
                self.specific_consumption_historical = dict()

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

    def __init__(self, path: Path, industry_settings):
        self.settings = industry_settings

        ex_spec = pd.ExcelFile(path / "Specific_Consumption.xlsx")
        ex_bat = pd.ExcelFile(path / "BAT_Consumption.xlsx")

        # read the active sectors sheets
        for product_name in self.settings.active_product_names:
            if product_name == 'unspecified industry':
                continue

            # read production data
            retrieve_prod = self.product_data_access[product_name]
            ex_product_his = \
                self.product_data_access[product_name].sheet_transform(
                    pd.read_excel(path / retrieve_prod.file_name, retrieve_prod.sheet_name,
                                  skiprows=retrieve_prod.skip_rows))

            dict_prod_his = dict()

            production_it = pd.DataFrame(ex_product_his).itertuples()
            for row in production_it:
                years = ex_product_his.columns[1:]
                data = ex_product_his[ex_product_his["Country"] == row.Country].iloc[0][1:]
                if uty.is_zero(data):
                    # country did not product this product at all => skip product for this country
                    print("skipped " + product_name + " for country " + row.Country)
                    continue
                zipped = list(zip(years, data))
                his_data = uty.filter_out_nan_and_inf(zipped)
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
                ex_sc_his = pd.ExcelFile(path / sc_his_file_name)

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

                            if country_name not in dict_sc_his.keys():
                                dict_sc_his[country_name] = dict()

                            dict_sc_his[country_name][sheet_name] = his_data

            # read bat consumption data
            prod_bat = pd.read_excel(ex_bat, sheet_name=product_name)
            dict_prod_bat_country = dict()

            for _, row in pd.DataFrame(prod_bat).iterrows():
                dict_prod_bat_country[row.Country] = \
                    prd.BAT(row["Spec electricity consumption [GJ/t]"],
                            row["Spec heat consumption [GJ/t]"])

            self.active_products[product_name] = \
                self.ProductInput(dict_prod_sc_country, dict_prod_bat_country, dict_prod_his, dict_sc_his, sc_his_calc)
