from __future__ import annotations

import os
import pandas as pd

from endemo2 import containers, sector, endemo
from endemo2 import industry_sector as ind


class FileGenerator(object):
    """
    A tool to more easily generate output files.

    :ivar Input input_manager: A reference to the input_manager that holds all input.
    :ivar pd.ExcelWriter excel_writer: The excel writer used for writing the file.
    :ivar str current_sheet_name: Keeps track of the current sheet name that new entries (add_entry) will be written to.
    :ivar dict current_out_dict: Keeps the entries that are added.
        When writing the file, these are converted to a table.
    """

    # Example usage:
    #    fg = FileGenerator(input_manager, out.xlsx)
    #    with fg
    #        fg.start_sheet("Data")
    #        fg.add_entry("Country", "Belgium")
    #        fg.add_entry("Value", 0.5)
    #        fg.start_sheet("Info")
    #        fg.add_entry("Sources", "[1] ...")
    #        ...

    def __init__(self, input_manager, filename):
        if not os.path.exists(input_manager.output_path):
            os.makedirs(input_manager.output_path)
        self.input_manager = input_manager
        out_file_path = input_manager.output_path / filename
        self.excel_writer = pd.ExcelWriter(out_file_path)
        self.current_sheet_name = ""
        self.current_out_dict = dict()

    def __enter__(self):
        self.current_sheet_name = ""
        self.current_out_dict = dict()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_file()

    def start_sheet(self, name):
        if self.current_sheet_name != "":
            self.end_sheet()
        self.current_sheet_name = name
        self.current_out_dict = dict()

    def end_sheet(self):
        df_out = pd.DataFrame(self.current_out_dict)
        df_out.to_excel(self.excel_writer, index=False, sheet_name=self.current_sheet_name, float_format="%.2f")
        self.current_sheet_name = ""
        self.current_out_dict = dict()

    def add_entry(self, column_name, value):
        if column_name not in self.current_out_dict.keys():
            self.current_out_dict[column_name] = []
        self.current_out_dict[column_name].append(value)

    def save_file(self):
        if self.current_sheet_name != "":
            self.end_sheet()
        self.excel_writer.close()


def generate_coefficient_output(model: endemo.Endemo) -> None:
    """
    Generates the output that displays debug information related to the coefficients of the predictions within the
    model.

    :param model: The model instance which provides the information that is written to the files.
    """

    input_manager = model.input_manager
    countries = model.countries

    def shortcut_coef_table(fg, product, year_coef, gdp_coef):
        fg.add_entry("Production is empty", product.is_empty())
        fg.add_entry("Last Data Entry", product.get_active_timeseries().get_last_data_entry())
        fg.add_entry("EXP Start Point", "(" + str(year_coef.exp.x0) + ", " + str(year_coef.exp.y0) + ")")
        fg.add_entry("EXP Change Rate", year_coef.exp.r)
        fg.add_entry("L0-per Time", year_coef.lin.k0)
        fg.add_entry("L1-per Time", year_coef.lin.k1)
        fg.add_entry("Q0-per Time", year_coef.quadr.k0)
        fg.add_entry("Q1-per Time", year_coef.quadr.k1)
        fg.add_entry("Q2-per Time", year_coef.quadr.k2)
        fg.add_entry("L0-per GDP", gdp_coef.lin.k0)
        fg.add_entry("L1-per GDP", gdp_coef.lin.k1)
        fg.add_entry("Q0-per GDP", gdp_coef.quadr.k0)
        fg.add_entry("Q1-per GDP", gdp_coef.quadr.k1)
        fg.add_entry("Q2-per GDP", gdp_coef.quadr.k2)

    filename = "endemo2_industry_coef_current_settings.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                fg.add_entry("Country", country.get_name())
                product = country.get_sector(sector.SectorIdentifier.INDUSTRY).get_product(product_name)
                coef = product.get_coef()
                fg.add_entry("Per Capita", product.is_per_capita())
                fg.add_entry("Per GDP", product.is_per_gdp())
                shortcut_coef_table(fg, product, coef, coef)

    filename = "endemo2_industry_coef_total.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                fg.add_entry("Country", country.get_name())
                product = country.get_sector(sector.SectorIdentifier.INDUSTRY).get_product(product_name)
                year_coef = product.get_timeseries_amount_per_year().get_coef()
                gdp_coef = product.get_timeseries_amount_per_gdp().get_coef()
                shortcut_coef_table(fg, product, year_coef, gdp_coef)

    filename = "endemo2_industry_coef_per_capita.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                fg.add_entry("Country", country.get_name())
                product = country.get_sector(sector.SectorIdentifier.INDUSTRY).get_product(product_name)
                year_coef = product.get_timeseries_amount_per_capita_per_year().get_coef()
                gdp_coef = product.get_timeseries_amount_per_capita_per_gdp().get_coef()
                shortcut_coef_table(fg, product, year_coef, gdp_coef)


def generate_population_prognosis_output(model: endemo.Endemo):
    """
    Generates the output that displays debug information related to the population.

    :param model: The model instance which provides the information that is written to the files.
    """

    input_manager = model.input_manager
    countries = model.countries
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "endemo2_population_prognosis.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        fg.start_sheet("Country Population calculated per Country")
        for country in countries.values():
            fg.add_entry("Country", country.get_name())
            fg.add_entry(target_year, country.get_population().get_country_prog(target_year))

        fg.start_sheet("Country Population calculated per NUTS2")
        for country in countries.values():
            fg.add_entry("Country", country.get_name())
            fg.add_entry(target_year, country.get_population().get_nuts2_prog(target_year))

        fg.start_sheet("NUTS2 Population")
        all_regions = []
        for country in countries.values():
            all_regions += country.get_population().get_nuts2_root().get_nodes_dfs()
        all_regions.sort(key=lambda x: x.region_name)
        for region in all_regions:
            if len(region.region_name) == 4:
                fg.add_entry("NUTS2 Region", region.region_name)
                fg.add_entry(target_year, region.get_pop_prog(target_year))


def generate_gdp_prognosis_output(model: endemo.Endemo):
    """
    Generates the output that displays debug information related to the gdp.

    :param model: The model instance which provides the information that is written to the files.
    """

    input_manager = model.input_manager
    countries = model.countries
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "endemo2_gdp_prognosis.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        fg.start_sheet("Prognosis")
        for country in countries.values():
            fg.add_entry("Country", country.get_name())
            fg.add_entry(target_year, country.get_gdp().get_prog(target_year))


def generate_amount_prognosis_output(model: endemo.Endemo):
    """
    Generates the output that displays debug information related to the production amount.

    :param model: The model instance which provides the information that is written to the files.
    """

    input_manager = model.input_manager
    countries = model.countries
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "endemo2_amount_prognosis.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                fg.add_entry("Country", country.get_name())

                industry_sector: ind.Industry = country.get_sector(sector.SectorIdentifier.INDUSTRY)
                product = industry_sector.get_product(product_name)

                amount_per_year_proj = \
                    product.get_timeseries_amount_per_year().get_prog(target_year)
                amount_per_gdp_proj = \
                    product.get_timeseries_amount_per_gdp().get_prog(target_year)
                amount_per_year_per_capita_proj = \
                    product.get_timeseries_amount_per_capita_per_year().get_prog(target_year)
                amount_per_gdp_per_capita_proj = \
                    product.get_timeseries_amount_per_capita_per_year().get_prog(target_year)

                country_pop = country.get_population().get_country_prog(target_year)

                str_amount_per_year_per_capita_proj = ""
                str_amount_per_gdp_per_capita_proj = ""
                if amount_per_year_per_capita_proj > 0:
                    str_amount_per_year_per_capita_proj = "{:10.20f}".format(amount_per_year_per_capita_proj)
                if amount_per_gdp_per_capita_proj > 0:
                    str_amount_per_gdp_per_capita_proj = "{:10.20f}".format(amount_per_gdp_per_capita_proj)

                fg.add_entry("YEAR for " + str(target_year) + "[kt]", amount_per_year_proj)
                fg.add_entry("GDP for " + str(target_year) + "[kt]", amount_per_gdp_proj)
                fg.add_entry("YEAR/CAPITA for " + str(target_year) + "[kt]", str_amount_per_year_per_capita_proj)
                fg.add_entry("GDP/CAPITA for " + str(target_year) + "[kt]", str_amount_per_gdp_per_capita_proj)
                fg.add_entry("County POP * YEAR/CAPITA for " + str(target_year) + "[kt]",
                             amount_per_year_per_capita_proj * country_pop)
                fg.add_entry("Country POP * GDP/CAPITA for " + str(target_year) + "[kt]",
                             amount_per_gdp_per_capita_proj * country_pop)


def generate_specific_consumption_output(model: endemo.Endemo):
    """
    Generates the output that displays debug information related to the specific consumption of products.

    :param model: The model instance which provides the information that is written to the files.
    """

    input_manager = model.input_manager
    countries = model.countries
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "endemo2_specific_consumption_projections.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                fg.add_entry("Country", country.get_name())
                sc_obj = country.get_sector(sector.SectorIdentifier.INDUSTRY).get_product(product_name) \
                    .get_specific_consumption()
                sc: containers.SC = sc_obj.get(target_year)
                fg.add_entry("Electricity [GJ/t]", sc.electricity)
                fg.add_entry("Heat [GJ/t]", sc.heat)
                fg.add_entry("Hydrogen [GJ/t]", sc.hydrogen)
                fg.add_entry("max. subst. of heat with H2 [%]", sc.max_subst_h2)


def generate_demand_output(model: endemo.Endemo):
    """
    Generates the output that displays debug information related to the demand of products.

    :param model: The model instance which provides the information that is written to the files.
    """

    input_manager = model.input_manager
    countries = model.countries
    target_year = input_manager.ctrl.general_settings.target_year
    per_capita = input_manager.ctrl.industry_settings.production_quantity_calc_per_capita

    def shortcut_demand_table(fg: FileGenerator, demand: containers.Demand):
        # scale per capita demand to be total amount
        fg.add_entry("Electricity [TWh]", demand.electricity)
        fg.add_entry("Heat [TWh]", demand.heat.q1 + demand.heat.q2 + demand.heat.q3 + demand.heat.q4)
        fg.add_entry("Hydrogen [TWh]", demand.hydrogen)
        fg.add_entry("Heat Q1 [TWh]", demand.heat.q1)
        fg.add_entry("Heat Q2 [TWh]", demand.heat.q2)
        fg.add_entry("Heat Q3 [TWh]", demand.heat.q3)
        fg.add_entry("Heat Q4 [TWh]", demand.heat.q4)

    filename = "endemo2_demand_projections.xlsx"
    fg = FileGenerator(input_manager, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                fg.add_entry("Country", country.get_name())
                demand: containers.Demand = country.get_sector(sector.SectorIdentifier.INDUSTRY) \
                    .calculate_product_demand(product_name, target_year)
                shortcut_demand_table(fg, demand)

        fg.start_sheet("forecasted")
        for country in countries.values():
            fg.add_entry("Country", country.get_name())
            demand: containers.Demand = \
                country.get_sector(sector.SectorIdentifier.INDUSTRY).calculate_total_demand(target_year)
            shortcut_demand_table(fg, demand)

        fg.start_sheet("rest")
        for country in countries.values():
            fg.add_entry("Country", country.get_name())
            demand: containers.Demand = \
                country.get_sector(sector.SectorIdentifier.INDUSTRY).calculate_rest_sector_demand(target_year)
            shortcut_demand_table(fg, demand)
