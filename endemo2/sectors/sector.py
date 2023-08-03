from enum import Enum

from endemo2.general import demand_containers as dc


class SectorIdentifier(Enum):
    """
    The enum class to quickly discern sectors.
    """
    INDUSTRY = 0
    HOUSEHOLDS = 1
    TRANSPORT = 2
    COMMERCIAL_TRADE_SERVICES = 3


class Sector:
    """
    The parent class for all sectors.
    Contains what different sectors have in common.
    """
    def __init__(self):
        pass
