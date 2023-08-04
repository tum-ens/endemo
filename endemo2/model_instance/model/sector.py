from enum import Enum


class SectorIdentifier(Enum):
    """
    The enum class to quickly discern sectors_to_do.
    """
    INDUSTRY = 0
    HOUSEHOLDS = 1
    TRANSPORT = 2
    COMMERCIAL_TRADE_SERVICES = 3


class Sector:
    """
    The parent class for all sectors_to_do.
    Contains what different sectors_to_do have in common.
    """
    def __init__(self):
        pass
