import pandas as pd
import numpy as np
from typing import Union
from endemo2.model.model_final_energy import calc_fe_types



class DataManager:
    """Manages Regions, Demand Drivers, and Efficiency Data."""
    def __init__(self, input_manager):
        self.input_manager = input_manager
        self.regions = []  # List of Region objects
        self.demand_drivers = {}  # Dictionary of DemandDriverData #TODO delet at the end
        self.efficiency_data = []  # List of Variable objects for FE [var_ef, var_share]
        self.load_profiles = {} # List of Load_profile objects for the regions
        self.timeseries_total_results = {}

    def read_and_filter_load_profiles(self, timsereis_file_df):
        active_regions = self.input_manager.general_settings.active_regions
        active_sectors = self.input_manager.general_settings.active_sectors
        active_subsectors = self.input_manager.general_settings.active_subsectors
        filter_reg = active_regions + ["default", "all"]
        filter_sec = active_sectors + ["default", "all"]
        filter_ss = [sub for subs in active_subsectors.values() for sub in subs] + ["default", "all"]
        sector_row = 1
        subsector_row = 2
        region_row = 0
        filtered_df = timsereis_file_df.copy()
        final_cols = [] # is containing the name of rows
        for col in timsereis_file_df.columns:
            region = timsereis_file_df.loc["Region", col]
            sector = timsereis_file_df.loc["Sector", col]
            subsector = timsereis_file_df.loc["Subsector", col]
            match_r = match_any(region, filter_reg)
            match_s = match_any(sector, filter_sec)
            match_ss = match_any(subsector, filter_ss)
            if match_r and match_s and match_ss:
                # Keep only matching parts in metadata
                col_pos = timsereis_file_df.columns.get_loc(col)
                filtered_df.iat[region_row, col_pos] = keep_only_matching(region, filter_reg)
                filtered_df.iat[sector_row, col_pos] = keep_only_matching(sector, filter_sec)
                filtered_df.iat[subsector_row, col_pos] = keep_only_matching(subsector, filter_ss)
                final_cols.append(col)
        # filtered data to be organised
        final_df = filtered_df.loc[:, final_cols]
        final_df.index.name = None
        # filtered data to be organised
        for col in final_df.columns:
            # Extract metadata
            regions = parse_cell_content(final_df.loc["Region", col])
            sectors = parse_cell_content(final_df.loc["Sector", col])
            subsectors = parse_cell_content(final_df.loc["Subsector", col])
            technologies = parse_cell_content(final_df.loc["Technology", col])
            ue_types = parse_cell_content(final_df.loc["UE_Type", col])
            temp_levels = parse_cell_content(final_df.loc["Temp_level", col])
            if "all" in regions: #TODO "default"
                regions = active_regions # as elec in ind shoudl be applied to all regions.
            if "all" in sectors:
                sectors = active_sectors
            if "all" in subsectors:
                subsectors = [sub for sector in sectors if sector in active_subsectors for sub in
                              active_subsectors[sector]]
            #extarct timeseries
            factor = float(final_df.loc["Factor", col])  #"Factor"
            time_series = (
                final_df.loc[1:, col]
                .astype(str)
                .str.replace(',', '.')
                .astype(float)
                .values  #convert to np array
            )
            time_series *= factor
            load_profile = LoadProfile(time_series)
            load_profile.temp_levels = temp_levels
            load_profile.ue_types = ue_types
            # Initialize storage structure with list if not exists
            for region in regions:
                for sector in sectors:
                    for subsector in subsectors:
                        for tech in technologies:
                            self.load_profiles \
                                .setdefault(region, {}) \
                                .setdefault(sector, {}) \
                                .setdefault(subsector, {}) \
                                .setdefault(tech, []) \
                                .append(load_profile)

    def get_load_profiles(self, region_name, sector_name, subsector_name, tech_name):
        """
        Get load profile with fallback logic that checks for 'default' at each level:
        1. Try exact match for region, then fall back to 'default' region
        2. Try exact match for sector, then fall back to 'default' sector
        3. Try exact match for subsector, then fall back to 'default' subsector
        4. Try exact match for technology, then fall back to 'default' technology
        5. Return None if any level is missing without default
        """
        try:
            # Check region level (exact or default)
            region_data = self.load_profiles.get(region_name) or self.load_profiles.get("default")
            if region_data is None:
                return None
            # Check sector level (exact or default)
            sector_data = region_data.get(sector_name) or region_data.get("default")
            if sector_data is None:
                return None
            # Check subsector level (exact or default)
            subsector_data = sector_data.get(subsector_name) or sector_data.get("default")
            if subsector_data is None:
                return None
            # Check technology level (exact or default)
            return subsector_data.get(tech_name) or subsector_data.get("default")
        except (KeyError, AttributeError):
            return None

    def timeseries_total(self):
        for region in self.regions:
            if not region.timeseries_results['profiles']:
                continue
            for profile_id, region_profile_data in region.timeseries_results['profiles'].items():
                # Initialize profile if not exists
                if profile_id not in self.timeseries_total_results['profiles']:
                    self.timeseries_total_results['profiles'][profile_id] = {
                        'years': {},
                        'regions_contributed': set(),
                        'sectors_contributed': set(),
                        'subsectors_contributed': set(),
                        'techs_contributed': set()
                    }
                profile_data = self.timeseries_total_results['profiles'][profile_id]
                # Update contributors
                profile_data['regions_contributed'].add(region.name)
                profile_data['sectors_contributed'].update(
                    region_profile_data.get('sectors_contributed', set()))
                profile_data['subsectors_contributed'].update(
                    region_profile_data.get('subsectors_contributed', set()))
                profile_data['techs_contributed'].update(
                    region_profile_data.get('techs_contributed', set()))
                # Aggregate yearly data
                for year, year_data in region_profile_data['years'].items():
                    if year in profile_data['years']:
                        # Use numpy arrays for efficient summation
                        profile_data['years'][year]['hourly_values'] = np.add(
                            profile_data['years'][year]['hourly_values'],
                            year_data['hourly_values']
                        )
                        profile_data['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        profile_data['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }
        # Convert sets to lists
        for profile_data in self.timeseries_total_results['profiles'].values():
            for key in ['regions_contributed', 'sectors_contributed',
                        'subsectors_contributed', 'techs_contributed']:
                profile_data[key] = list(profile_data[key])
        return self.timeseries_total_results

    def read_all_demand_drivers(self, ddr_names):
        """Load only the required demand driver data from a single file."""
        input_path = self.input_manager.input_path / "Data_Demand_drivers.xlsx"
        if not input_path.exists():
            print(f"Demand drivers data file not found: {input_path}")
            return
        # Load the full dataset ONCE
        full_data = pd.read_excel(input_path, sheet_name="Data")
        # Filter and store only the needed demand drivers
        for driver_name in ddr_names:
            if driver_name == "TIME":
                continue  # No external data needed for 'TIME'
            driver_data = full_data[full_data["Variable"] == driver_name]
            self.demand_drivers[driver_name] = DemandDriverData(driver_name, driver_data)

    def add_region(self, region):
        """Add a Subsector child to this Sector"""
        self.regions.append(region)
        region.parent = self  # Set this Sector as parent of the Subsector

    def get_demand_driver(self, driver_name):
        """Retrieve a specific demand driver."""
        return self.demand_drivers.get(driver_name)

    def calc_fe(self):
        if self.input_manager.general_settings.FE_marker == 0:
            print("Calculation Final energy is not activated")
            return None
        else:
            forecast_year_range = self.input_manager.general_settings.forecast_year_range
            forecast_year_range = [str(year) for year in forecast_year_range]
            var_ef, var_share = self.efficiency_data
            eff_forecast = var_ef.forecast
            eff_forecast.columns = eff_forecast.columns.astype(str)
            share_forecast = var_share.forecast
            share_forecast.columns = share_forecast.columns.astype(str)
            for region in self.regions:
                region.calc_fe_region(eff_forecast,share_forecast,forecast_year_range)

    def calc_timeseries(self):
        if self.input_manager.general_settings.timeseries_forecast == 0:
            print("Calculation Timeseries is not activated")
            return None
        else:
            forecast_year_range = self.input_manager.general_settings.forecast_year_range
            forecast_year_range = [str(year) for year in forecast_year_range]
            for region in self.regions:
                region.calc_timeseries_reg(forecast_year_range)

    def load_efficiency_data(self,fe_df):
        """Load efficiency data (a single DataFrame)."""
        var_ef = Variable("EFFICIENCY")
        var_ef.user = fe_df["EFFICIENCY"]
        var_share = Variable("FE_SHARE_FOR_UE")
        var_share.user = fe_df["FE_SHARE_FOR_UE"]
        self.efficiency_data = [var_ef, var_share]

class Region:
    def __init__(self, region_name, country_code):
        """
         Args:
            region_name (str): Name of the region.
        """
        self.region_name = region_name
        self.code = country_code
        self.sectors = []
        self.energy_ue = None
        self.energy_fe = None
        # self.DDr_data = DataFrame #TODO
        self.timeseries_results = {
            'profiles': {}
        }

    def calc_fe_region(self, eff_forecast, share_forecast, forecast_year_range):
        fe_energy = []
        for sector in self.sectors:
            sector.calc_fe_subsector(eff_forecast,share_forecast,forecast_year_range)
            fe_energy.append(sector.energy_fe)
        self.energy_fe = pd.concat(fe_energy, axis=0, ignore_index=True)

    def calc_timeseries_reg(self,forecast_year_range):
        for sector in self.sectors:
            sector.calc_timeseries_sec(forecast_year_range)
            if not sector.timeseries_results['profiles']:
                continue
            for profile_id, sector_data in sector.timeseries_results['profiles'].items():
                if profile_id not in self.timeseries_results['profiles']:
                    self.timeseries_results['profiles'][profile_id] = {
                        'components': sector_data['components'],
                        'years': {},
                        'contributors': {
                            'sectors': set(),
                            'subsectors': set(),
                            'technologies': set(),
                            'subtechs': set(),
                            'drives': set()
                        }
                    }
                # Update contributors
                region_profile = self.timeseries_results['profiles'][profile_id]
                region_profile['contributors']['sectors'].add(sector.name)
                region_profile['contributors']['subsectors'].update(sector_data['contributors']['subsectors'])
                region_profile['contributors']['technologies'].update(sector_data['contributors']['technologies'])
                region_profile['contributors']['subtechs'].update(sector_data['contributors']['subtechs'])
                region_profile['contributors']['drives'].update(sector_data['contributors']['drives'])
                # Aggregate yearly data
                for year, year_data in sector_data['years'].items():
                    if year in region_profile['years']:
                        region_profile['years'][year]['hourly_values'] += year_data['hourly_values']
                        region_profile['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        region_profile['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }
         # Convert sets to lists for serialization
        for profile in self.timeseries_results['profiles'].values():
            for level in profile['contributors']:
                profile['contributors'][level] = list(profile['contributors'][level])

    def add_sector(self, sector):
        """Add a Subsector child to this Sector"""
        self.sectors.append(sector)
        sector.parent = self


class Sector:
    """
    Represents a sector and holds multiple Subsector objects.
    """
    def __init__(self, name):
        """
         Args:
            name (str): Name of the sector.
        """
        self.name = name
        self.settings = None
        self.subsectors = []
        self.energy_ue = None
        self.energy_fe = None
        self.timeseries_results = {
            'profiles': {}
        }

    def calc_fe_subsector(self,eff_forecast, share_forecast, forecast_year_range):
        fe_energy = []
        for subsector in self.subsectors:
            subsector.calc_fe_techonology(eff_forecast,share_forecast,forecast_year_range)
            fe_energy.append(subsector.energy_fe)
        self.energy_fe = pd.concat(fe_energy, axis=0, ignore_index=True)

    def calc_timeseries_sec(self, forecast_year_range):
        for subsector in self.subsectors:
            subsector.calc_timeseries_sub(forecast_year_range)
            if not subsector.timeseries_results['profiles']:
                continue
            for profile_id, subsector_data in subsector.timeseries_results['profiles'].items():
                if profile_id not in self.timeseries_results['profiles']:
                    self.timeseries_results['profiles'][profile_id] = {
                        'components': subsector_data['components'],
                        'years': {},
                        'contributors': {
                            'subsectors': set(),
                            'technologies': set(),
                            'subtechs': set(),
                            'drives': set()
                        }
                    }
                # Update contributors
                sector_profile = self.timeseries_results['profiles'][profile_id]
                sector_profile['contributors']['subsectors'].add(subsector.name)
                sector_profile['contributors']['technologies'].update(subsector_data['contributors']['technologies'])
                sector_profile['contributors']['subtechs'].update(subsector_data['contributors']['subtechs'])
                sector_profile['contributors']['drives'].update(subsector_data['contributors']['drives'])

                # Aggregate yearly data
                for year, year_data in subsector_data['years'].items():
                    if year in sector_profile['years']:
                        sector_profile['years'][year]['hourly_values'] += year_data['hourly_values']
                        sector_profile['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        sector_profile['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }

        # Convert sets to lists
        for profile in self.timeseries_results['profiles'].values():
            for level in profile['contributors']:
                profile['contributors'][level] = list(profile['contributors'][level])


    def add_subsector(self, subsector):
        """Add a Subsector child to this Sector"""
        self.subsectors.append(subsector)
        subsector.parent = self  # Set this Sector as parent of the Subsector


class Subsector:
    def __init__(self, name):
        self.name = name
        self.ecu = None  #  ECU as a variable object
        self.technologies = []  # List of Technology objects which will contain DDet variables
        self.energy_ue = None
        self.energy_fe = None
        self.timeseries_results = {
            'profiles': {} # Structure: {profile_id: {components, years, contributors}}
        }
    def calc_fe_techonology(self,eff_forecast,share_forecast,forecast_year_range):
        fe_energy = []
        for tech in self.technologies:
            tech.calc_fe_tech(eff_forecast, share_forecast, forecast_year_range)
            fe_energy.append(tech.energy_fe)
        self.energy_fe = pd.concat(fe_energy, axis=0, ignore_index=True)

    def calc_timeseries_sub(self, forecast_year_range):
        # Process each technology
        for tech in self.technologies:
            tech.calc_timeseries_tech(forecast_year_range)
            if not tech.timeseries_results:
                continue
            for profile_id, tech_data in tech.timeseries_results.items():
                # Initialize profile if it doesn't exist
                if profile_id not in self.timeseries_results['profiles']:
                    self.timeseries_results['profiles'][profile_id] = {
                        'components': tech_data['components'],
                        'years': {},
                        'contributors': {
                            'technologies': set(),
                            'subtechs': set(),
                            'drives': set()
                        }
                    }
                # Get reference to the profile
                subsector_profile = self.timeseries_results['profiles'][profile_id]
                # Update contributors
                subsector_profile['contributors']['technologies'].update(
                    tech_data['contributors']['technologies'])
                subsector_profile['contributors']['subtechs'].update(
                    tech_data['contributors']['subtechs'])
                subsector_profile['contributors']['drives'].update(
                    tech_data['contributors']['drives'])
                # Aggregate yearly data
                for year, year_data in tech_data['years'].items():
                    if year in subsector_profile['years']:
                        # Sum existing values
                        subsector_profile['years'][year]['hourly_values'] += year_data['hourly_values']
                        subsector_profile['years'][year]['annual_energy'] += year_data['annual_energy']
                    else:
                        # Create new entry (with copy of arrays to prevent reference issues)
                        subsector_profile['years'][year] = {
                            'hourly_values': np.array(year_data['hourly_values']),
                            'annual_energy': year_data['annual_energy']
                        }
            # Convert sets to lists for serialization
        for profile in self.timeseries_results['profiles'].values():
            for key in profile['contributors']:
                profile['contributors'][key] = list(profile['contributors'][key])

    def add_ecu(self, ecu):
        """Add ECU child to this Subsector"""
        self.ecu = ecu
        ecu.parent = self

    def add_technology(self, technology):
        """Add a Technology child to this Subsector"""
        self.technologies.append(technology)
        technology.parent = self

class Technology:
    def __init__(self, name):
        self.name = name
        self.ddets = []  # List of Variable objects
        self.energy_ue = None
        self.energy_fe = None
        self.load_profile = None
        self.timeseries_results = {}

    def add_variable(self, variable):
        """Add a Variable child to this Technology"""
        self.ddets.append(variable)
        variable.parent = self

    def calc_fe_tech(self, eff_forecast, share_forecast, forecast_year_range):
        self.energy_fe = calc_fe_types(self.energy_ue, eff_forecast, share_forecast, forecast_year_range)

    def calc_timeseries_tech(self, forecast_year_range):
        if self.load_profile is None:
            return
        self.timeseries_results = {}
        for l_profile in self.load_profile:
            # Apply filters
            energy_source = self.energy_fe if self.energy_fe is not None else self.energy_ue
            calc_data = energy_source.copy()
            calc_data = calc_data[~((calc_data["UE_Type"] == "HEAT") & (calc_data["Temp_level"] == "TOTAL"))]
            if 'default' not in l_profile.ue_types :
                calc_data = calc_data[calc_data['UE_Type'].isin(l_profile.ue_types)]
            if 'default' not in l_profile.temp_levels:
                calc_data = calc_data[calc_data['Temp_level'].isin(l_profile.temp_levels)]
            if calc_data.empty:
                continue
            # Group by dimensions (excluding Subtech and Drive)
            group_cols = ['Region', 'Sector', 'Subsector', 'Technology', 'Temp_level', 'UE_Type']
            grouped = calc_data.groupby(group_cols, as_index=False)[[str(y) for y in forecast_year_range]].sum()
            # Get unique contributors
            subtechs = calc_data['Subtech'].unique().tolist()
            drives = calc_data['Drive'].unique().tolist()
            # Melt for processing
            melted = grouped.melt(
                id_vars=group_cols,
                value_vars=[str(y) for y in forecast_year_range],
                var_name='Year',
                value_name='Energy'
            )
            for _, row in melted.iterrows():
                profile_id = f"{row['Temp_level']}_{row['UE_Type']}"
                year = row['Year']
                if profile_id not in self.timeseries_results:
                    self.timeseries_results[profile_id] = {
                        'components': {
                            'temp_level': row['Temp_level'],
                            'ue_type': row['UE_Type']
                        },
                        'years': {},
                        'contributors': {
                            'technologies': set(),
                            'subtechs': set(),
                            'drives': set()
                        }
                    }
                # Update contributors
                self.timeseries_results[profile_id]['contributors']['technologies'].add(self.name)
                self.timeseries_results[profile_id]['contributors']['subtechs'].update(subtechs)
                self.timeseries_results[profile_id]['contributors']['drives'].update(drives)
                # Calculate hourly profile (applied to raw energy, not summed)
                hourly_values = np.array(row['Energy'] * l_profile.values)
                if year in self.timeseries_results[profile_id]['years']:
                    self.timeseries_results[profile_id]['years'][year]['annual_energy'] += row['Energy']
                    self.timeseries_results[profile_id]['years'][year]['hourly_values'] += hourly_values
                else:
                    self.timeseries_results[profile_id]['years'][year] = {
                        'hourly_values': hourly_values,
                        'annual_energy': row['Energy']
                    }

class Variable:
    def __init__(self,name):
        self.name = name
        self.region_name = None
        self.settings = None # df
        self.historical = None
        self.user = None
        self.forecast = None

    def get_hierarchy(self):
        """
        Traverse up the parent hierarchy to collect names for a variable
        Returns a dictionary with all hierarchical levels
        Returns:
            dict: {
                "Variable": str,
                "Technology": str or None,
                "Subsector": str,
                "Sector": str,
                "Region": str
            }
        """
        hierarchy = {
            "Variable": self.name,
            "Technology": None,
            "Subsector": None,
            "Sector": None,
            "Region": None
        }
        current = getattr(self, 'parent', None)  # Safely get parent (returns None if attr doesn't exist)
        while current is not None:
            if isinstance(current, Technology):
                hierarchy["Technology"] = current.name
            elif isinstance(current, Subsector):
                hierarchy["Subsector"] = current.name
            elif isinstance(current, Sector):
                hierarchy["Sector"] = current.name
            elif isinstance(current, Region):
                hierarchy["Region"] = getattr(current, 'region_name', None)
                break  # Region is top level, can exit early
            current = getattr(current, 'parent', None)
        return hierarchy

class DemandDriverData:
    """
    Encapsulates data for a specific single demand driver.
    """

    def __init__(self, driver_name, demand_driver_df):
        self.name = driver_name
        # self.historical = None #TODO
        # self.user = None
        self.data = demand_driver_df[demand_driver_df["Variable"] == driver_name]

    def get_data_for_region(self, region_name):
        """Retrieve data for a specific region."""
        return self.data[self.data["Region"] == region_name]


class LoadProfile:
    """
    A class to represent electrical load profiles with associated settings.

    Attributes:
        values (np.ndarray): The load profile values as a time series
    """

    def __init__(self, values: Union[list, np.ndarray]):

        """
        Initialize the LoadProfile object.
        Args:
            values: Load profile values (will be converted to numpy array)
        """
        self.values = self._validate_values(values)
        self.temp_levels = None
        self.ue_types = None

    def _validate_values(self, values: Union[list, np.ndarray]) -> np.ndarray:
        """Validate and convert input values to numpy array."""
        if not isinstance(values, (list, np.ndarray)):
            raise TypeError("Values must be a list or numpy array")
        arr = np.array(values)
        if arr.ndim != 1:
            raise ValueError("Load profile values must be 1-dimensional")
        return arr


def match_any(cell, target_list):
    """Returns True if any value from target_list is in the comma-separated cell"""
    if pd.isna(cell):
        return False
    values = [v.strip() for v in str(cell).split(',')]
    return any(val in values for val in target_list)

def keep_only_matching(cell, target_list):
    """Keeps only matching values from the cell (comma-separated)"""
    if pd.isna(cell):
        return ''
    values = [v.strip() for v in str(cell).split(',')]
    filtered = [v for v in values if v in target_list]
    return ', '.join(filtered)

def parse_cell_content(cell_value):
    if isinstance(cell_value, str) and "," in cell_value:
        return [s.strip() for s in cell_value.split(",")]
    else:
        return [cell_value] if pd.notna(cell_value) else []