import math

from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter import ProductInstanceFilter
from endemo2.model_instance.model.country import Country
from endemo2.data_structures.containers import Demand, SC
from endemo2.model_instance.model.industry.products import Product
from endemo2.output.output_utility import FileGenerator, shortcut_demand_table
from endemo2.model_instance.model.industry.industry_sector import Industry
from endemo2.model_instance.model.sector import SectorIdentifier
from input.input import Input


def generate_instance_output(input_manager: Input, countries: dict[str, Country],
                             country_instance_filter: CountryInstanceFilter,
                             product_instance_filter: ProductInstanceFilter):
    generate_demand_output(input_manager, countries)
    generate_gdp_output(input_manager, countries, country_instance_filter)
    generate_population_prognosis_output(input_manager, countries, country_instance_filter)
    generate_specific_consumption_output(input_manager, countries, product_instance_filter)
    generate_amount_output(input_manager, countries, product_instance_filter)

def generate_amount_output(input_manager: Input, countries, product_instance_filter: ProductInstanceFilter):

    target_year = input_manager.ctrl.general_settings.target_year

    filename = "ind_product_amount_prognosis.xlsx"
    fg = FileGenerator(input_manager, "", filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country in countries.items():
                fg.add_entry("Country", country_name)
                try:
                    fg.add_entry("Amount [kt]", product_instance_filter.get_amount(country_name, product_name) / 1000)
                except KeyError:
                    # country doesn't have product
                    fg.add_entry("Amount [kt]", "")

def generate_demand_output(input_manager: Input, countries):

    filename = "ind_demand_projections_per_country.xlsx"
    fg = FileGenerator(input_manager, "", filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country in countries.items():
                fg.add_entry("Country", country_name)
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                product: Product = industry.get_product(product_name)
                demand: Demand = product.calculate_demand()
                shortcut_demand_table(fg, demand)

        fg.start_sheet("forecasted")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            demand: Demand = \
                country.get_sector(SectorIdentifier.INDUSTRY).calculate_forecasted_demand()
            shortcut_demand_table(fg, demand)

        fg.start_sheet("rest")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
            demand: Demand = industry.calculate_rest_sector_demand()
            shortcut_demand_table(fg, demand)

        fg.start_sheet("IND")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
            demand: Demand = industry.calculate_total_demand()
            shortcut_demand_table(fg, demand)

    filename = "ind_demand_projections_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, "", filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                product: Product = industry.get_product(product_name)
                dict_nuts2_demand: dict[str, Demand] = product.get_demand_distributed_by_nuts2()
                for (nuts2_region_name, demand) in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("forecasted")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_forecasted_demand_distributed_by_nuts2()
                for (nuts2_region_name, demand) in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("rest")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_rest_demand_distributed_by_nuts2()
                for (nuts2_region_name, demand) in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("IND")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_total_demand_distributed_by_nuts2()
                for (nuts2_region_name, demand) in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)


def generate_gdp_output(input_manager: Input, countries, country_instance_filter: CountryInstanceFilter):
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "general_gdp_prognosis.xlsx"
    fg = FileGenerator(input_manager, "", filename)
    with fg:
        fg.start_sheet("Prognosis")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_gdp_in_target_year(country_name))


def generate_population_prognosis_output(input_manager: Input, countries, country_instance_filter: CountryInstanceFilter):
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "general_population_prognosis.xlsx"
    fg = FileGenerator(input_manager, "", filename)
    with fg:
        fg.start_sheet("Country Prognosis")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_country_population_in_target_year(country_name))

        fg.start_sheet("Country Prognosis Distributed by NUTS2 Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_nuts2_population_percentages(country_name)
            country_pop = country_instance_filter.get_country_population_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, country_pop * value)

        fg.start_sheet("NUTS2 Separate Prognosis")
        for country_name in countries.keys():
            regions_pop = country_instance_filter.get_nuts2_population_in_target_year(country_name)
            for region_name, value in regions_pop.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)

        fg.start_sheet("NUTS2 Sum")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            regions_pop = country_instance_filter.get_nuts2_population_in_target_year(country_name)
            fg.add_entry(target_year, math.fsum(regions_pop.values()))

        fg.start_sheet("NUTS2 Population Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_nuts2_population_percentages(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)


def generate_specific_consumption_output(input_manager: Input, countries, product_if: ProductInstanceFilter):

    filename = "ind_specific_consumption_prognosis.xlsx"
    fg = FileGenerator(input_manager, "", filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name in countries.keys():
                fg.add_entry("Country", country_name)
                try:
                    sc: SC = product_if.get_specific_consumption_po(country_name, product_name)
                    fg.add_entry("Electricity [TWh/t]", sc.electricity)
                    fg.add_entry("Heat [TWh/t]", sc.heat)
                    fg.add_entry("Hydrogen [TWh/t]", sc.hydrogen)
                    fg.add_entry("max. subst. of heat with H2 [%]", sc.max_subst_h2)
                except KeyError:
                    # country doesn't product product
                    fg.add_entry("Electricity [TWh/t]", "")
                    fg.add_entry("Heat [TWh/t]", "")
                    fg.add_entry("Hydrogen [TWh/t]", "")
                    fg.add_entry("max. subst. of heat with H2 [%]", "")

