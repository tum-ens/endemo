"""
DataManager: central data container for endemo.

This class stores regions, drivers, efficiency inputs and subregion data,
and delegates all reading/processing to dedicated loader classes.
"""

from __future__ import annotations

import pandas as pd

from endemo2.Input.loaders.ddr_loader import DdrLoader
from endemo2.Input.loaders.ddet_ecu_loader import DDetEcuLoader
from endemo2.Input.loaders.subregion_loader import SubregionLoader
from endemo2.Input.loaders.timeseries_loader import TimeseriesLoader
from endemo2.Input.hierarchy.hierachy_classes import Region, Sector, Subsector, Technology, Variable, DemandDriverData, LoadProfile


class DataManager:
    """
    Central data container and API for loader operations.

    - Holds all Region objects and their hierarchy
    - Stores DDrs, efficiency data and subregion data
    - Delegates reading/parsing to loader classes
    """

    def __init__(self, input_manager):
        self.input_manager = input_manager
        self.regions = []
        self.demand_drivers = {}
        self.dependent_demand_drivers = {}
        self.dependent_demand_driver_specs = {}
        self.efficiency_data = []
        self.load_profiles = {}
        self.timeseries_total_results = {"profiles": {}}
        self.region_lookup = {}
        self.subregions = {}
        self.subregion_aliases = {}
        self.subregion_hist_data = pd.DataFrame()
        self.subregion_scenario_raw = pd.DataFrame()
        self.subregion_scenario_long = pd.DataFrame()
        self.subregion_division_forecast = pd.DataFrame()

        # Loader components
        self.ddr_loader = DdrLoader(self)
        self.ddet_ecu_loader = DDetEcuLoader(self)
        self.subregion_loader = SubregionLoader(self)
        self.timeseries_loader = TimeseriesLoader(self)

    # ---- loader delegations ----

    def read_and_filter_load_profiles(self, timsereis_file_df):
        """Load and store hourly load profiles for active regions/sectors/subsectors."""
        return self.timeseries_loader.read_and_filter_load_profiles(timsereis_file_df)

    def get_load_profiles(self, region_name, sector_name, subsector_name, tech_name):
        """Return load profiles for a specific hierarchy path with defaults."""
        return self.timeseries_loader.get_load_profiles(region_name, sector_name, subsector_name, tech_name)

    def timeseries_total(self):
        """Aggregate hourly profiles across all regions into a global summary."""
        return self.timeseries_loader.timeseries_total()

    def build_dependent_ddr_export(self):
        """Create an export table for dependent DDrs and their computed time series."""
        return self.ddr_loader.build_dependent_ddr_export()

    def read_ecu_ddet_data(self, active_regions, active_sectors, ue_type_list, heat_levels_list):
        """Read and pre-filter ECU/DDet input data."""
        return self.ddet_ecu_loader.read_ecu_ddet_data(
            active_regions=active_regions,
            active_sectors=active_sectors,
            ue_type_list=ue_type_list,
            heat_levels_list=heat_levels_list,
        )

    def attach_subsector_ecu_ddets(self, region_name, sector_name, subsector, row):
        """Attach ECU/DDet variables for one subsector path to the hierarchy."""
        return self.ddet_ecu_loader.attach_subsector_inputs(
            region_name=region_name,
            sector_name=sector_name,
            subsector=subsector,
            row=row,
        )

    def get_final_energy_variable_inputs(self):
        """Return prebuilt Variable objects for FE efficiency and shares."""
        return self.ddet_ecu_loader.get_final_energy_variable_inputs()

    def read_all_demand_drivers(self, active_regions):
        """Read and merge historical + scenario demand drivers for active regions."""
        return self.ddr_loader.read_all_demand_drivers(active_regions)

    def attach_region_demand_drivers(self, region):
        """Attach demand driver variables to a specific Region."""
        return self.ddr_loader.attach_region_demand_drivers(region)

    def read_subregions(self, active_regions):
        """Read subregion definitions from settings for active regions."""
        return self.subregion_loader.read_subregions(active_regions)

    def read_subregion_timeseries(self, active_regions):
        """Read historical subregion time series and store them in the data container."""
        return self.subregion_loader.read_subregion_timeseries(active_regions)

    def read_subregion_scenario(self, active_regions):
        """Read scenario subregion definitions (division variables and functions)."""
        return self.subregion_loader.read_subregion_scenario(active_regions)

    def attach_region_subregions(self, region):
        """Attach all subregion rows (hist + scenario) to a region object."""
        return self.subregion_loader.attach_region_subregions(region)

    # ---- region registry ----

    def add_region(self, region: Region):
        """Register a Region object and index it by name."""
        self.regions.append(region)
        self.region_lookup[region.region_name] = region

    def get_region(self, region_name: str):
        """Return a Region object by name (or None if missing)."""
        return self.region_lookup.get(region_name)

    def get_demand_driver(self, driver_name):
        """Return a DemandDriverData object by name."""
        return self.demand_drivers.get(driver_name)

 

