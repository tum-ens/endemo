"""
This module holds any information and utility functions related to unit conversion.
"""
import warnings
from enum import Enum


class Unit(Enum):
    """ Enum for any unity that are used in the model. """
    TWh = 0
    GWh = 1
    MWh = 2
    kWh = 3
    TJ = 4
    GJ = 5
    liter = 6
    m3 = 7
    Standard = 8
    Million = 9
    Billion = 10


# holds all scalars that are used for unit conversion
unit_conversion_scalar_table = {
    (Unit.GWh, Unit.TWh): 1 / 1000,
    (Unit.TJ, Unit.TWh): 1 / 3600,
    (Unit.kWh, Unit.TWh): 1 / 10**9,
    (Unit.TWh, Unit.kWh): 10**9,
    (Unit.GJ, Unit.TWh): 1 / (3600 * 1000),
    (Unit.liter, Unit.m3): 1 / 1000,
    (Unit.Billion, Unit.Million): 1000,
    (Unit.Standard, Unit.Million): 1/10**6,
    (Unit.Million, Unit.Standard): 10**6
}


def get_conversion_scalar(from_unit: Unit, to_unit: Unit) -> float:
    """
    Get the scalar that converts one unit to another.

    :param from_unit: The unit of the value that should be converted.
    :param to_unit: The resulting unit.
    :return: The scalar for unit conversion.
    """
    if (from_unit, to_unit) not in unit_conversion_scalar_table.keys():
        warnings.warn("Please add the unit conversion scalar to the table for conversion: "
                      + str(from_unit) + " to " + str(to_unit))
    if from_unit == to_unit:
        return 1.0
    return unit_conversion_scalar_table[(from_unit, to_unit)]


def convert(from_unit: Unit, to_unit: Unit, value: float) -> float:
    """
    Converts a value from one unit to another.

    :param from_unit: The unit the input value is.
    :param to_unit: The unit the output value should be
    :param value: The value to convert.
    :return: The converted value.
    """
    if (from_unit, to_unit) not in unit_conversion_scalar_table.keys():
        warnings.warn("Please add the unit conversion scalar to the table for conversion: "
                      + str(from_unit) + " to " + str(to_unit))
    if from_unit == to_unit:
        return value
    return unit_conversion_scalar_table[(from_unit, to_unit)] * value

