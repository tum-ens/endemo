"""
This module contains all functions that generate output files from a model instance.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

from endemo2.data_structures.conversions_unit import convert, Unit
from endemo2.input_and_settings.input_households import HouseholdsSubsectorId
from endemo2.input_and_settings.input_manager import InputManager
from endemo2.model_instance.instance_filter.cts_instance_filter import CtsInstanceFilter
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter import ProductInstanceFilter
from endemo2.model_instance.model.country import Country
from endemo2.data_structures.containers import Demand, SpecConsum
from endemo2.model_instance.model.cts.cts_sector import CommercialTradeServices
from endemo2.model_instance.model.households.household_sector import Households
from endemo2.model_instance.model.industry.products import Product
from endemo2.output.output_utility import FileGenerator, shortcut_demand_table, get_day_folder_path, \
    ensure_directory_exists
from endemo2.model_instance.model.industry.industry_sector import Industry
from endemo2.data_structures.enumerations import SectorIdentifier, ForecastMethod, DemandType
from endemo2.data_structures.conversions_string import map_hh_subsector_to_string

# toggles to further control which output is written, maybe adapt them into settings later
IND_HOURLY_DEMAND_DISABLE = False
CTS_HOURLY_DEMAND_DISABLE = False
HH_HOURLY_DEMAND_DISABLE = False

TOGGLE_GEN_OUTPUT = True
TOGGLE_DETAILED_OUTPUT = True


def generate_instance_output(input_manager: InputManager, countries: dict[str, Country],
                             country_instance_filter: CountryInstanceFilter,
                             product_instance_filter: ProductInstanceFilter,
                             cts_instance_filter: CtsInstanceFilter,
                             hh_instance_filter: HouseholdsInstanceFilter):
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
        "scenario_" + str_target_year + "_ind_" + str_forecast_method + "_" + x_axis + "_" + geo_res

    # create directory when not present
    day_folder = get_day_folder_path(input_manager)
    scenario_folder = ensure_directory_exists(day_folder / scenario_output_folder_name)
    if TOGGLE_DETAILED_OUTPUT:
        details_folder = ensure_directory_exists(scenario_folder / "details")
    input_output_folder = input_manager.input_output_path

    # copy Set_and_Control_Parameters that lead to this instance output to output folder
    shutil.copy(InputManager.ctrl_path, scenario_folder / "Set_and_Control_Parameters.xlsx")

    # shortcut toggles
    toggle_nuts2 = input_manager.ctrl.general_settings.toggle_nuts2_resolution
    toggle_hourly = input_manager.ctrl.general_settings.toggle_hourly_forecast
    active_sectors = input_manager.ctrl.general_settings.get_active_sectors()

    # generate all outputs according to settings
    if TOGGLE_GEN_OUTPUT:
        output_gen_gdp(scenario_folder, input_manager, countries, country_instance_filter)
        output_gen_population_forecast(scenario_folder, input_manager, countries, country_instance_filter)
        if TOGGLE_DETAILED_OUTPUT:
            output_gen_population_forecast_details(details_folder, input_manager, countries, country_instance_filter)
    if SectorIdentifier.INDUSTRY in active_sectors:
        output_ind_product_amount(input_output_folder, input_manager, countries, product_instance_filter)

        if not toggle_nuts2:
            output_ind_demand_country(scenario_folder, input_manager, countries)
        if toggle_nuts2:
            output_ind_demand_nuts2(scenario_folder, input_manager, countries)
        if toggle_hourly and not toggle_nuts2 and not IND_HOURLY_DEMAND_DISABLE:
            output_ind_demand_hourly_country(scenario_folder, input_manager, countries)
        if toggle_hourly and toggle_nuts2 and not IND_HOURLY_DEMAND_DISABLE:
            output_ind_demand_hourly_nuts2(scenario_folder, input_manager, countries)
        if TOGGLE_DETAILED_OUTPUT:
            output_ind_specific_consumption(details_folder, input_manager, countries, product_instance_filter)
    if SectorIdentifier.COMMERCIAL_TRADE_SERVICES in active_sectors:
        if not toggle_nuts2:
            output_cts_demand_country(scenario_folder, input_manager, countries)
        if toggle_nuts2:
            output_cts_demand_nuts2(scenario_folder, input_manager, countries)
        if toggle_hourly and not toggle_nuts2 and not CTS_HOURLY_DEMAND_DISABLE:
            output_cts_demand_hourly_country(scenario_folder, input_manager, countries)
        if toggle_hourly and toggle_nuts2 and not CTS_HOURLY_DEMAND_DISABLE:
            output_cts_demand_hourly_nuts2(scenario_folder, input_manager, countries)
        if TOGGLE_DETAILED_OUTPUT:
            output_cts_employee_number(details_folder, input_manager, countries, cts_instance_filter)
            output_cts_specific_consumption(details_folder, input_manager, countries, cts_instance_filter)
    if SectorIdentifier.HOUSEHOLDS in active_sectors:
        if not toggle_nuts2:
            output_hh_demand_country(scenario_folder, input_manager, countries)
        if toggle_nuts2:
            output_hh_demand_nuts2(scenario_folder, input_manager, countries)
        if toggle_hourly and not toggle_nuts2 and not HH_HOURLY_DEMAND_DISABLE:
            output_hh_demand_hourly_country(scenario_folder, input_manager, countries)
        if toggle_hourly and toggle_nuts2 and not HH_HOURLY_DEMAND_DISABLE:
            pass
        if TOGGLE_DETAILED_OUTPUT:
            output_hh_characteristics(details_folder, input_manager, countries, hh_instance_filter)
            output_hh_subsectors_demand(details_folder, input_manager, countries, hh_instance_filter)


def output_gen_gdp(folder: Path, input_manager: InputManager, countries,
                   country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the gdp of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "gen_gdp_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Prognosis")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_gdp_in_target_year(country_name))


def output_gen_population_forecast(folder: Path, input_manager: InputManager, countries,
                                   country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the population of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "gen_population_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
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


def output_gen_population_forecast_details(folder: Path, input_manager: InputManager, countries,
                                           country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the population of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "gen_population_forecast_details.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Country Forecast")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_population_country_in_target_year(country_name))

        fg.start_sheet("Country Forecast Distributed by NUTS2 Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            country_pop = country_instance_filter.get_population_country_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, country_pop * value)

        fg.start_sheet("NUTS2 Separate Forecast")
        for country_name in countries.keys():
            regions_pop = country_instance_filter.get_population_nuts2_in_target_year(country_name)
            for region_name, value in regions_pop.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)

        fg.start_sheet("NUTS2 Sum")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            nuts2_sum = country_instance_filter.get_population_nuts2_sum(country_name)
            fg.add_entry(target_year, nuts2_sum)

        fg.start_sheet("NUTS2 Population Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)


def output_ind_product_amount(folder: Path, input_manager: InputManager, countries,
                              product_instance_filter: ProductInstanceFilter):
    """ Generates all output related to amount of a subsector. """

    filename = "ind_product_amount_forecast_" + str(input_manager.ctrl.general_settings.target_year) + ".xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        dict_sum = dict[str, float]()
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name, country in countries.items():
                if country_name not in dict_sum.keys():
                    dict_sum[country_name] = 0.0
                fg.add_entry("Country", country_name)
                try:
                    product_amount = product_instance_filter.get_amount(country_name, product_name) / 1000
                    dict_sum[country_name] += product_amount
                    fg.add_entry("Amount [kt]", product_amount)
                except KeyError:
                    # country doesn't have product
                    fg.add_entry("Amount [kt]", "")
        fg.start_sheet("IND")
        for country_name, amount_sum in dict_sum.items():
            fg.add_entry("Country", country_name)
            fg.add_entry("Amount [kt]", amount_sum)


def output_ind_demand_country(folder: Path, input_manager: InputManager, countries):
    """ Generates industry demand output of a countries. """

    filename = "ind_demand_forecast_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
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


def output_ind_demand_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates industry demand output for nuts2 regions. """

    filename = "ind_demand_forecast_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                product: Product = industry.get_product(product_name)
                dict_nuts2_demand: dict[str, Demand] = product.get_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("forecasted")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_forecasted_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("rest")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_rest_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("IND")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_total_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)


def output_cts_employee_number(folder: Path, input_manager: InputManager, countries,
                               cts_instance_filter: CtsInstanceFilter):
    """ Generates output for the number of employees in the cts sector. """

    filename = "cts_employee_number_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Employees Country")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            cts_sector: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            population = cts_instance_filter.get_population_country(country_name)
            employee_sum = 0
            for subsector in cts_sector.get_subsectors():
                employee_pop_share = \
                    cts_instance_filter.get_employee_share_of_population_country(country_name, subsector)
                num_employees_in_sector = employee_pop_share * population
                employee_sum += num_employees_in_sector
                fg.add_entry(subsector, num_employees_in_sector)
            fg.add_entry("Employees total", employee_sum)

        fg.start_sheet("Employees NUTS2")
        for country_name, country in countries.items():
            cts_sector: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            nuts2_population = cts_instance_filter.get_population_nuts2(country_name)
            for region_name, population in nuts2_population.items():
                fg.add_entry("NUTS2", region_name)
                employee_sum = 0
                for subsector in cts_sector.get_subsectors():
                    employee_pop_share = \
                        cts_instance_filter.get_employee_share_of_population_nuts2(country_name, subsector)[
                            region_name]
                    num_employees_in_sector = employee_pop_share * population
                    employee_sum += num_employees_in_sector
                    fg.add_entry(subsector, num_employees_in_sector)
                fg.add_entry("Employees total", employee_sum)


def output_cts_demand_country(folder: Path, input_manager: InputManager, countries):
    """ Generates all demand output for the cts sector. """

    filename = "cts_demand_forecast_by_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            cts: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            demand = cts.calculate_demand()
            shortcut_demand_table(fg, demand)


def output_cts_demand_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates all demand output for the cts sector. """

    filename = "cts_demand_forecast_by_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        for country_name, country in countries.items():
            cts: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            dict_nuts2_demand = cts.calculate_demand_distributed_by_nuts2()
            for nuts2_region_name, demand in dict_nuts2_demand.items():
                fg.add_entry("NUTS2 Region", nuts2_region_name)
                shortcut_demand_table(fg, demand)


def output_ind_demand_hourly_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for each country. """

    filename = "ind_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
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


def output_ind_demand_hourly_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for nuts2 regions. """

    filename = "ind_demand_forecast_hourly_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("IND")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_nuts2 = \
                country.get_sector(
                    SectorIdentifier.INDUSTRY).calculate_total_hourly_demand_distributes_by_nuts2()
            for region_name, hourly_demand in hourly_demand_nuts2.items():
                fg.add_complete_column(region_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
                fg.add_complete_column(region_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q3", [h.q3 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q4", [h.q4 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def output_cts_demand_hourly_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for each country. """

    filename = "cts_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand = country.get_sector(
                SectorIdentifier.COMMERCIAL_TRADE_SERVICES).calculate_hourly_demand()
            fg.add_complete_column(country_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
            fg.add_complete_column(country_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def output_cts_demand_hourly_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for nuts2 regions. """

    filename = "cts_demand_forecast_hourly_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_nuts2 = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES) \
                .calculate_hourly_demand_distributed_by_nuts2()
            for region_name, hourly_demand in hourly_demand_nuts2.items():
                fg.add_complete_column(region_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
                fg.add_complete_column(region_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def output_ind_specific_consumption(folder: Path, input_manager: InputManager, countries,
                                    product_if: ProductInstanceFilter):
    """ Generates all output related to the specific consumption of products. """

    filename = "ind_specific_consumption_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
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


def output_cts_specific_consumption(folder: Path, input_manager: InputManager, countries,
                                    cts_if: CtsInstanceFilter):
    """ Generates all output related to the specific consumption of employees. """

    filename = "cts_specific_consumption_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            try:
                sc: SpecConsum = cts_if.get_specific_consumption(country_name)
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


def output_hh_characteristics(folder: Path, input_manager: InputManager, countries, hh_if: HouseholdsInstanceFilter):
    """ Generates the households characteristics output. """
    filename = "hh_characteristics.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Test")  # todo remove?
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            pers_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            fg.add_entry("Person per Household [Pers./Household]", pers_per_household)
            area_per_household = hh_if.get_area_per_household_in_target_year(country_name)
            fg.add_entry("Area per Household [m^2/Household]", area_per_household)
            spec_energy = hh_if.get_space_heating_specific_heat_in_target_year(country_name)
            fg.add_entry("Specific energy consumption [kWh/m^2]", convert(Unit.TWh, Unit.kWh, spec_energy))
            population = hh_if.get_population_in_target_year(country_name)
            avg_num_person_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            num_households = population / avg_num_person_per_household
            area_total = hh_if.get_area_per_household_in_target_year(country_name) * num_households
            fg.add_entry("Living area total [m^2]", area_total)
            fg.add_entry("Population", population)

        fg.start_sheet("Pers per Household")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            pers_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            fg.add_entry("Person per Household [Pers./Household]", pers_per_household)

        fg.start_sheet("Area per Household")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            area_per_household = hh_if.get_area_per_household_in_target_year(country_name)
            fg.add_entry("Area per Household [m^2/Household]", area_per_household)

        fg.start_sheet("Specific energy consumption")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            spec_energy = hh_if.get_space_heating_specific_heat_in_target_year(country_name)
            fg.add_entry("Specific energy consumption [kWh/m^2]", convert(Unit.TWh, Unit.kWh, spec_energy))

        fg.start_sheet("Living area total")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            population = hh_if.get_population_in_target_year(country_name)
            avg_num_person_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            num_households = population / avg_num_person_per_household
            area_total = hh_if.get_area_per_household_in_target_year(country_name) * num_households
            fg.add_entry("Living area total [m^2]", area_total)


def output_hh_subsectors_demand(folder: Path, input_manager: InputManager, countries, hh_if: HouseholdsInstanceFilter):
    """ Generates the simplified demand output of the subsectors. """

    filename = "hh_subsectors_energy_demand.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Energy_PerSubsector")
        for country_name, country_obj in countries.items():
            fg.add_entry("Country", country_name)

            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)

            total_demand = 0
            for subsector_id in hh_if.get_subsectors():
                subsector_name = map_hh_subsector_to_string[subsector_id].replace("_", " ")

                subsector_demand = households_sector._subsectors[subsector_id].calculate_demand()
                energy_demand = subsector_demand.get_sum()

                fg.add_entry(subsector_name + " [TWh]", energy_demand)
                total_demand += energy_demand

            fg.add_entry("total [TWh]", total_demand)

        fg.start_sheet("Energy_Useful_Total")
        for country_name, country_obj in countries.items():
            fg.add_entry("Country", country_name)

            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)
            households_demand = households_sector.calculate_demand()

            fg.add_entry("Electricity [TWh]", households_demand.electricity)
            fg.add_entry("Heat [TWh]", households_demand.heat.get_sum())
            fg.add_entry("Hydrogen [TWh]", households_demand.hydrogen)
            fg.add_entry("Total [TWh]", households_demand.get_sum())


def output_hh_demand_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by country. """

    filename = "hh_demand_forecast_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("HH")
        for country_name, country_obj in countries.items():
            fg.add_entry("Country", country_name)

            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)
            hh_demand = households_sector.calculate_demand()
            shortcut_demand_table(fg, hh_demand)


def output_hh_demand_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by nuts2 regions. """

    filename = "hh_demand_forecast_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("HH")
        for country_name, country_obj in countries.items():
            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)
            hh_demand_nuts2 = households_sector.calculate_demand_distributed_by_nuts2()
            for region_name, demand in hh_demand_nuts2.items():
                fg.add_entry("NUTS2 Region", region_name)
                shortcut_demand_table(fg, demand)


def output_hh_demand_hourly_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by country. """

    filename = "hh_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_efh = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_efh()
            hourly_demand_mfh = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_mfh()

            electricity = [he + hm for (he, hm)
                           in zip(hourly_demand_efh[DemandType.ELECTRICITY], hourly_demand_mfh[DemandType.ELECTRICITY])]

            fg.add_complete_column(country_name + ".Elec", electricity)
            fg.add_complete_column(country_name + ".EFH_Q1", [h.q1 for h in hourly_demand_efh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".EFH_Q2", [h.q2 for h in hourly_demand_efh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".EFH_H2", hourly_demand_efh[DemandType.HYDROGEN])
            fg.add_complete_column(country_name + ".MFH_Q1", [h.q1 for h in hourly_demand_mfh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".MFH_Q2", [h.q2 for h in hourly_demand_mfh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".MFH_H2", hourly_demand_mfh[DemandType.HYDROGEN])


def output_hh_demand_hourly_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by nuts2 regions. """

    filename = "hh_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_efh_nuts2 = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_efh_distributed_by_nuts2()
            hourly_demand_mfh_nuts2 = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_mfh_distributed_by_nuts2()

            for region_name in hourly_demand_efh_nuts2.keys():
                hourly_demand_efh = hourly_demand_efh_nuts2[region_name]
                hourly_demand_mfh = hourly_demand_mfh_nuts2[region_name]

                electricity = [he + hm for (he, hm)
                               in zip(hourly_demand_efh[DemandType.ELECTRICITY],
                                      hourly_demand_mfh[DemandType.ELECTRICITY])]

                fg.add_complete_column(region_name + ".Elec", electricity)
                fg.add_complete_column(region_name + ".EFH_Q1", [h.q1 for h in hourly_demand_efh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".EFH_Q2", [h.q2 for h in hourly_demand_efh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".EFH_H2", hourly_demand_efh[DemandType.HYDROGEN])
                fg.add_complete_column(region_name + ".MFH_Q1", [h.q1 for h in hourly_demand_mfh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".MFH_Q2", [h.q2 for h in hourly_demand_mfh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".MFH_H2", hourly_demand_mfh[DemandType.HYDROGEN])
