"""
This module contains all functions that generate output files from a model instance.
"""

import math
import shutil
from pathlib import Path

from endemo2.input_and_settings.input import Input
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter import ProductInstanceFilter
from endemo2.model_instance.model.country import Country
from endemo2.data_structures.containers import Demand, SpecConsum
from endemo2.model_instance.model.industry.products import Product
from endemo2.output.output_utility import FileGenerator, shortcut_demand_table, get_day_folder_path, \
    ensure_directory_exists
from endemo2.model_instance.model.industry.industry_sector import Industry
from endemo2.data_structures.enumerations import SectorIdentifier, ForecastMethod, DemandType


def generate_instance_output(input_manager: Input, countries: dict[str, Country],
                             country_instance_filter: CountryInstanceFilter,
                             product_instance_filter: ProductInstanceFilter):
    """
    Calls all generate_x_output functions of this module that should be used to generate output.
    """

    # decide output folder name for scenario
    str_forecast_method = ""
    match input_manager.ctrl.industry_settings.forecast_method:
        case ForecastMethod.LINEAR:
            str_forecast_method = "lin"
        case ForecastMethod.QUADRATIC:
            str_forecast_method = "quadr"

    x_axis = ""
    match input_manager.ctrl.industry_settings.use_gdp_as_x:
        case True:
            x_axis = "gdp"
        case False:
            x_axis = "time"

    geo_res = ""
    match input_manager.ctrl.general_settings.toggle_nuts2_resolution:
        case True:
            geo_res = "nuts2"
        case False:
            geo_res = "country"

    str_target_year = str(input_manager.ctrl.general_settings.target_year)
    scenario_output_folder_name = \
        "scenario_" + str_target_year + "_ind_" + str_forecast_method + "front_label" + x_axis + "front_label" + geo_res

    # copy instance settings to output folder
    day_folder = get_day_folder_path(input_manager)
    # create directory when not present
    scenario_output_folder = ensure_directory_exists(day_folder / scenario_output_folder_name)
    shutil.copy(Input.ctrl_path, scenario_output_folder / "Set_and_Control_Parameters.xlsx")

    # generate all outputs
    generate_demand_output(scenario_output_folder_name, input_manager, countries)
    generate_gdp_output(scenario_output_folder_name, input_manager, countries, country_instance_filter)
    generate_population_prognosis_output(scenario_output_folder_name, input_manager, countries, country_instance_filter)
    generate_specific_consumption_output(scenario_output_folder_name, input_manager, countries, product_instance_filter)
    generate_amount_output(scenario_output_folder_name, input_manager, countries, product_instance_filter)

    if input_manager.ctrl.general_settings.toggle_hourly_forecast:
        generate_demand_hourly_output(scenario_output_folder_name, input_manager, countries)


def generate_amount_output(scenario_output_folder: str, input_manager: Input, countries,
                           product_instance_filter: ProductInstanceFilter):
    """ Generates all output related to amount of a product. """

    filename = "ind_product_amount_forecast.xlsx"
    fg = FileGenerator(input_manager, scenario_output_folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name, country in countries.items():
                fg.add_entry("Country", country_name)
                try:
                    fg.add_entry("Amount [kt]", product_instance_filter.get_amount(country_name, product_name) / 1000)
                except KeyError:
                    # country doesn't have product
                    fg.add_entry("Amount [kt]", "")


def generate_demand_output(scenario_output_folder: str, input_manager: Input, countries):
    """ Generates all output related to demand of a countries. """

    if not input_manager.ctrl.general_settings.toggle_nuts2_resolution:
        filename = "ind_demand_forecast_per_country.xlsx"
        fg = FileGenerator(input_manager, scenario_output_folder, filename)
        with fg:
            for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
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

    if input_manager.ctrl.general_settings.toggle_nuts2_resolution:
        filename = "ind_demand_forecast_per_nuts2.xlsx"
        fg = FileGenerator(input_manager, scenario_output_folder, filename)
        with fg:
            for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
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

def generate_demand_hourly_output(scenario_output_folder: str, input_manager: Input, countries):
    """ Generates the output that splits the demand into the hourly timeseries. """

    if not input_manager.ctrl.general_settings.toggle_nuts2_resolution:
    # per country
        filename = "ind_demand_forecast_hourly_per_country.xlsx"
        fg = FileGenerator(input_manager, scenario_output_folder, filename)
        with fg:
            fg.start_sheet("IND")
            fg.add_complete_column("t", list(range(1, 8760 + 1)))
            for country_name, country in countries.items():
                hourly_demand = country.get_sector(SectorIdentifier.INDUSTRY).calculate_total_hourly_demand()
                fg.add_complete_column(country_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
                fg.add_complete_column(country_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(country_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(country_name + ".Q3", [h.q3 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(country_name + ".Q4", [h.q4 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(country_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])

    if input_manager.ctrl.general_settings.toggle_nuts2_resolution:
        # per nuts2
        filename = "ind_demand_forecast_hourly_per_nuts2.xlsx"
        fg = FileGenerator(input_manager, scenario_output_folder, filename)
        with fg:
            fg.start_sheet("IND")
            fg.add_complete_column("t", list(range(1, 8760 + 1)))
            for country_name, country in countries.items():
                hourly_demand_nuts2 = \
                    country.get_sector(SectorIdentifier.INDUSTRY).calculate_total_hourly_demand_distributes_by_nuts2()
                for region_name, hourly_demand in hourly_demand_nuts2.items():
                    fg.add_complete_column(region_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
                    fg.add_complete_column(region_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
                    fg.add_complete_column(region_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
                    fg.add_complete_column(region_name + ".Q3", [h.q3 for h in hourly_demand[DemandType.HEAT]])
                    fg.add_complete_column(region_name + ".Q4", [h.q4 for h in hourly_demand[DemandType.HEAT]])
                    fg.add_complete_column(region_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def generate_gdp_output(scenario_output_folder: str, input_manager: Input, countries, country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the gdp of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "general_gdp_forecast.xlsx"
    fg = FileGenerator(input_manager, scenario_output_folder, filename)
    with fg:
        fg.start_sheet("Prognosis")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_gdp_in_target_year(country_name))


def generate_population_prognosis_output(scenario_output_folder: str, input_manager: Input, countries,
                                         country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the population of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "general_population_forecast.xlsx"
    fg = FileGenerator(input_manager, scenario_output_folder, filename)
    with fg:
        fg.start_sheet("Country Forecast")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_population_country_in_target_year(country_name))

        fg.start_sheet("NUTS2 Forecast")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            country_pop = country_instance_filter.get_population_country_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, country_pop * value)

    filename = "general_population_forecast.xlsx"
    fg = FileGenerator(input_manager, scenario_output_folder / Path("details"), filename)
    with fg:
        fg.start_sheet("Country Prognosis")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_population_country_in_target_year(country_name))

        fg.start_sheet("Country Prognosis Distributed by NUTS2 Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            country_pop = country_instance_filter.get_population_country_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, country_pop * value)

        fg.start_sheet("NUTS2 Separate Prognosis")
        for country_name in countries.keys():
            regions_pop = country_instance_filter.get_population_nuts2_in_target_year(country_name)
            for region_name, value in regions_pop.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)

        fg.start_sheet("NUTS2 Sum")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            regions_pop = country_instance_filter.get_population_nuts2_in_target_year(country_name)
            fg.add_entry(target_year, math.fsum(regions_pop.values()))

        fg.start_sheet("NUTS2 Population Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)


def generate_specific_consumption_output(scenario_output_folder: str, input_manager: Input, countries,
                                         product_if: ProductInstanceFilter):
    """ Generates all output related to the specific consumption of products. """

    filename = "ind_specific_consumption_forecast.xlsx"
    fg = FileGenerator(input_manager, scenario_output_folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name in countries.keys():
                fg.add_entry("Country", country_name)
                try:
                    sc: SpecConsum = product_if.get_specific_consumption(country_name, product_name)
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

