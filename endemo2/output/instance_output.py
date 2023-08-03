from endemo2.general.country import Country
from endemo2.general.demand_containers import Demand
from endemo2.industry.products import Product
from endemo2.output.output_utility import FileGenerator, shortcut_demand_table
from endemo2.sectors.industry_sector import Industry
from endemo2.sectors.sector import SectorIdentifier
from input.input import Input


def generate_instance_output(input_manager: Input, countries: dict[str, Country]):
    generate_demand_output(input_manager, countries)


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

def generate_gdp_output():
    # TODO: für target year
    pass

def generate_population_prognosis_output():
    # TODO: country und nuts2
    pass