from __future__ import annotations

from enum import Enum


class GroupType(Enum):
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
