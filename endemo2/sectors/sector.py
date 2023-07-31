from enum import Enum

from endemo2.general import demand_containers as dc


class SectorIdentifier(Enum):
    """
    The enum class to quickly discern sectors.
    :todo: Add more sectors later
    """
    INDUSTRY = 0


class Sector:
    """
    The parent class for all sectors.
    Contains what different sectors have in common.
    """

    def calculate_forecasted_demand(self, year: int) -> dc.Demand:
        # calculate useful energy demand of sector
        # has to be overwritten by child class
        raise NotImplementedError
