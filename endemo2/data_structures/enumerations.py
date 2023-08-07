"""
This module contains all Enums of endemo.
"""

from __future__ import annotations

from enum import Enum


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


class DemandType(Enum):
    """ Enum to easily differentiate the type of demand. """
    ELECTRICITY = 0
    HEAT = 1
    HYDROGEN = 2


class StartPoint(Enum):
    """ Denotes the type of start points used for the exponential forecast method. """
    LAST_AVAILABLE = 0
    AVERAGE_VALUE = 1
    MANUAL = 2


class SectorIdentifier(Enum):
    """
    The enum class to quickly discern sectors_to_do.
    """
    INDUSTRY = 0
    HOUSEHOLDS = 1
    TRANSPORT = 2
    COMMERCIAL_TRADE_SERVICES = 3
