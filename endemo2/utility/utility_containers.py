from __future__ import annotations

from enum import Enum


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
