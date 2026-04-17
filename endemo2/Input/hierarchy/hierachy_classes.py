"""
Hierarchical model objects used throughout endemo.

These classes represent the in-memory structure of the model:
Region -> Sector -> Subsector -> Technology -> Variable.
They store forecast results.
"""

#definition of all the class specific methods

from __future__ import annotations

from typing import Union
import numpy as np
import pandas as pd


class Region:
    """
    Region node in the hierarchy.

    Holds sectors, demand drivers, subregions and region-level results.
    """

    def __init__(self, region_name: str, country_code: str):
        self.region_name = region_name
        self.code = country_code
        self.sectors: list[Sector] = []
        self.energy_ue = None
        self.energy_fe = None
        self.demand_drivers = {}
        self.demand_driver_variables = []
        self.subregions = {}
        self.timeseries_results = {"profiles": {}}

    def add_demand_driver(self, variable: "Variable") -> None:
        """Attach a demand driver variable to this region."""
        variable.parent = self
        variable.region_name = self.region_name
        self.demand_drivers[variable.name] = variable
        self.demand_driver_variables.append(variable)

    def get_demand_driver(self, driver_name: str):
        """Return the demand driver variable for this region."""
        if driver_name is None:
            return None
        direct = self.demand_drivers.get(driver_name)
        if direct is not None:
            return direct
        lookup = str(driver_name).strip().lower()
        for key, value in self.demand_drivers.items():
            if str(key).strip().lower() == lookup:
                return value
        return None

    def add_sector(self, sector: "Sector") -> None:
        """Attach a sector node to this region."""
        self.sectors.append(sector)
        sector.parent = self

class Sector:
    """Sector node in the hierarchy."""

    def __init__(self, name: str):
        self.name = name
        self.subsectors: list[Subsector] = []
        self.energy_ue = None
        self.energy_fe = None
        self.timeseries_results = {"profiles": {}}
        self.settings = None

    def add_subsector(self, subsector: "Subsector") -> None:
        """Attach a subsector node to this sector."""
        self.subsectors.append(subsector)
        subsector.parent = self

class Subsector:
    """Subsector node in the hierarchy."""

    def __init__(self, name: str):
        self.name = name
        self.ecu = None
        self.technologies: list[Technology] = []
        self.energy_ue = None
        self.energy_fe = None
        self.timeseries_results = {"profiles": {}}

    def add_ecu(self, ecu: "Variable") -> None:
        """Attach ECU variable to this subsector."""
        self.ecu = ecu
        ecu.parent = self

    def add_technology(self, technology: "Technology") -> None:
        """Attach a technology node to this subsector."""
        self.technologies.append(technology)
        technology.parent = self

class Technology:
    """Technology node in the hierarchy (within a subsector)."""

    def __init__(self, name: str):
        self.name = name
        self.ddets: list[Variable] = []
        self.energy_ue = None
        self.energy_fe = None
        self.load_profile = None
        self.timeseries_results = {}

    def add_variable(self, variable: "Variable") -> None:
        """Attach a DDet variable to this technology."""
        self.ddets.append(variable)
        variable.parent = self

class Variable:
    """Generic model variable (ECU, DDet, or DDr)."""

    def __init__(self, name: str):
        self.name = name
        self.region_name = None
        self.settings = None
        self.historical = None
        self.user = None
        self.forecast = None
        self.demand_driver_data = None
        self.ddr_spec = None

    def get_hierarchy(self) -> dict:
        """Return the full hierarchy path for this variable."""
        hierarchy = {
            "Variable": self.name,
            "Technology": None,
            "Subsector": None,
            "Sector": None,
            "Region": None
        }
        current = getattr(self, 'parent', None)
        while current is not None:
            if isinstance(current, Technology):
                hierarchy["Technology"] = current.name
            elif isinstance(current, Subsector):
                hierarchy["Subsector"] = current.name
            elif isinstance(current, Sector):
                hierarchy["Sector"] = current.name
            elif isinstance(current, Region):
                hierarchy["Region"] = getattr(current, 'region_name', None)
                break
            current = getattr(current, 'parent', None)
        return hierarchy


class DemandDriverData:
    """Encapsulates time series data for a single demand driver."""

    def __init__(self, driver_name: str, demand_driver_df: pd.DataFrame):
        self.name = driver_name
        driver_df = demand_driver_df.copy()
        driver_df.columns = [str(col).strip() for col in driver_df.columns]
        self.data = driver_df[driver_df["Variable"] == driver_name].reset_index(drop=True)
        self._region_cache = {
            region: group.reset_index(drop=True)
            for region, group in self.data.groupby("Region", dropna=False)
        }

    def get_data_for_region(self, region_name: str):
        """Return the time series for a given region."""
        if region_name is None:
            return None
        return self._region_cache.get(region_name)

    def get_dependent_specs(self, region_name: str):
        """Return dependent DDr metadata for the given region (if available)."""
        key = (self.name, region_name)
        parent = getattr(self, "parent", None)
        if parent and hasattr(parent, "dependent_demand_driver_specs"):
            return parent.dependent_demand_driver_specs.get(key, {})
        return {}


class LoadProfile:
    """Container for hourly load profiles and their metadata."""

    def __init__(self, values: Union[list, np.ndarray]):
        """
        Initialize a load profile.

        Args:
            values: Hourly profile values as list or numpy array.
        """
        self.values = self.validate_values(values)
        self.temp_levels = ["default"]
        self.ue_types = ["default"]

    def validate_values(self, values: Union[list, np.ndarray]) -> np.ndarray:
        """Validate and convert input values to a 1D numpy array."""
        if not isinstance(values, (list, np.ndarray)):
            raise TypeError("Values must be a list or numpy array")
        arr = np.array(values)
        if arr.ndim != 1:
            raise ValueError("Load profile values must be 1-dimensional")
        return arr
