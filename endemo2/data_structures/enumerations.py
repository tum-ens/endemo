"""
This module contains all Enums of endemo.
"""

from __future__ import annotations

from enum import Enum


class SubsectorGroup(Enum):
    """
    Enum to group the industry _subsectors.
    """
    CHEMICALS_AND_PETROCHEMICALS = 0
    FOOD_AND_TOBACCO = 1
    IRON_AND_STEEL = 2
    NON_METALIC_MINERALS = 3
    PAPER = 4


class GroupType(Enum):
    """
    Enum to differentiate different country group types.

    :ivar SEPARATE: All countries in this type of group are calculated separately.
    :ivar JOINED: The data of all countries in a group of type joined is lumped together and shared coefficients are
        calculated.
    :ivar JOINED_DIVERSIFIED: The data of all countries in a group of type joined_diversified is lumped together and
        shared coefficients are calculated. But each country has a differing offset additionally.
    :ivar EMPTY: Indicates that no group type is chosen.
    """
    SEPARATE = 0
    JOINED = 1
    JOINED_DIVERSIFIED = 2
    EMPTY = 3


class ForecastMethod(Enum):
    """
    The ForecastMethod indicates the preferred way to extrapolate historical data.

    :ivar LINEAR: The forecast method utilizing linear regression.
    :ivar QUADRATIC: The forecast method utilizing quadratic regression.
    :ivar EXPONENTIAL: The forecast method utilizing exponential growth.
    :ivar QUADRATIC_OFFSET: The forecast method utilizing quadratic regression and an additional offset.
    """
    LINEAR = 0
    QUADRATIC = 1
    EXPONENTIAL = 2
    QUADRATIC_OFFSET = 3
    LOGARITHMIC = 4


class ScForecastMethod(Enum):
    """ The ScForecastMethod indicates type of forecast for specific consumption, primarily in the CTS sector. """
    LINEAR = 0
    LOGARITHMIC = 1
    CONST_MEAN = 2
    CONST_LAST = 3


class DemandType(Enum):
    """ Enum to easily differentiate the type of demand. """
    ELECTRICITY = 0
    HEAT = 1
    HYDROGEN = 2
    FUEL = 3


class StartPoint(Enum):
    """ Denotes the type of start points used for the exponential forecast method. """
    LAST_AVAILABLE = 0
    AVERAGE_VALUE = 1
    MANUAL = 2


class SectorIdentifier(Enum):
    """
    The enum class to quickly discern sectors.
    """
    INDUSTRY = 0
    HOUSEHOLDS = 1
    TRANSPORT = 2
    COMMERCIAL_TRADE_SERVICES = 3


class HouseholdsSubsectorId(Enum):
    """
    The enum class to quickly recognise the different household sectors.
    """
    SPACE_HEATING = 0,
    SPACE_COOLING = 1,
    WATER_HEATING = 2,
    COOKING = 3,
    LIGHTING_AND_APPLIANCES = 4
    OTHER = 5


class TransportModalSplitMethod(Enum):
    """
    The enum indicating how the modal split for the transport sector should be obtained.
    """
    HISTORICAL_TIME_TREND = 0
    HISTORICAL_CONSTANT = 1
    USER_DEFINED = 2


class TransportFinalEnergyDemandScenario(Enum):
    """
    The enum indicating how the final energy demand should be split.
    Either by the given reference or user defined values.
    """
    REFERENCE = 0
    USER_DEFINED = 1


class TrafficType(Enum):
    """ The type of traffic. """
    PERSON = 0
    FREIGHT = 1
    BOTH = 2


class TransportModal(Enum):
    """
    The enum to differentiate different modes of transport or combinations of them.
    """
    road = 0
    car = 1
    bus = 2
    rail = 3
    road_rail = 4
    ship = 5
    flight = 6
    road_rail_ship = 7
