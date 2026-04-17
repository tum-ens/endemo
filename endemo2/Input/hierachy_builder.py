"""
Hierarchy bootstrap for one model run.

This module does two things:
1) Load input tables into DataManager.
2) Build Region -> Sector -> Subsector objects and attach data.
"""

import pandas as pd

from endemo2.Input.hierarchy import (
    Region,
    Sector,
    Subsector,
    DataManager,
)
from endemo2.Input.hierarchy.hierachy_classes import Variable
from endemo2.Input.model_config import SHEET_HOURLY


def initialize_hierarchy_and_load_input(input_manager):
    """
    Build the region/sector/subsector hierarchy and attach all loaded inputs.

    Loading logic (DDr, Subregions, ECU/DDet, timeseries profiles) is delegated
    to dedicated loaders via DataManager.
    """
    # Central container for loaded data and hierarchy objects.
    data = DataManager(input_manager)

    # Read active settings once.
    active_sectors = input_manager.general_settings.active_sectors
    active_regions = input_manager.general_settings.active_regions
    region_code_map = input_manager.general_settings.region_code_map
    sectors_settings = input_manager.general_settings.sectors_settings
    timeseries_forecast = input_manager.general_settings.timeseries_forecast

    ue_type_list = input_manager.general_settings.useful_energy_types
    heat_levels_list = input_manager.general_settings.heat_levels

    # Load input tables first.
    data.read_all_demand_drivers(active_regions)
    data.read_subregions(active_regions)
    data.read_subregion_timeseries(active_regions)
    data.read_subregion_scenario(active_regions)
    data.read_ecu_ddet_data(
        active_regions=active_regions,
        active_sectors=active_sectors,
        ue_type_list=ue_type_list,
        heat_levels_list=heat_levels_list,
    )

    # Optional: load hourly profiles.
    if timeseries_forecast == 1:
        timeseries = pd.read_excel(input_manager.timeseries_file, sheet_name=SHEET_HOURLY, header=None).set_index(0)
        data.read_and_filter_load_profiles(timeseries)

    # Build hierarchy and attach loaded data.
    for region_name in active_regions:
        region = Region(region_name=region_name, country_code=region_code_map[region_name])
        data.attach_region_demand_drivers(region)
        data.attach_region_subregions(region)

        for sector_name in active_sectors:
            sector = Sector(name=sector_name)
            sector.settings = sectors_settings[sector_name]

            # Create subsectors and map ECU/DDet input.
            for subsector_name, row in sector.settings.iterrows():
                subsector = Subsector(name=subsector_name)
                data.attach_subsector_ecu_ddets(
                    region_name=region_name,
                    sector_name=sector_name,
                    subsector=subsector,
                    row=row,
                )
                sector.add_subsector(subsector)

            region.add_sector(sector)

        data.add_region(region)

    # FE helper inputs (efficiency and shares).
    fe_inputs = data.get_final_energy_variable_inputs()
    if not fe_inputs:
        fe_inputs = [Variable("EFFICIENCY"), Variable("FE_SHARE_FOR_UE")]
    data.efficiency_data = fe_inputs

    return data


