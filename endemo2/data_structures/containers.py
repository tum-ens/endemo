"""
This module contains all simple data containers used in endemo.
"""

from __future__ import annotations

import collections as coll
from typing import Any

import numpy as np

from endemo2.data_structures.enumerations import DemandType

EH = coll.namedtuple("EH", ["electricity", "heat"])     # tuple for only electricity and heat

CA = coll.namedtuple("CA", ["alpha2", "alpha3", "german_name"])     # abbreviation container
HisProg = coll.namedtuple("HisProg", ["historical", "prognosis"])   # container for historical and prognosis data
Interval = coll.namedtuple("Interval", ["start", "end"])            # representation of an interval


class SpecConsum:
    """
    A container for specific consumption. Offers arithmetic operations.

    :param float electricity: Amount of electricity consumption.
    :param float heat: Amount of heat consumption.
    :param float hydrogen: Amount of hydrogen consumption.
    :param float max_subst_h2: TODO: what is this?

    :ivar float electricity: Amount of electricity consumption.
    :ivar float heat: Amount of heat consumption.
    :ivar float hydrogen: Amount of hydrogen consumption.
    :ivar float max_subst_h2: TODO: what is this?
    """
    def __init__(self, electricity, heat, hydrogen=0.0, max_subst_h2=0):
        self.electricity = electricity
        self.heat = heat
        self.hydrogen = hydrogen
        self.max_subst_h2 = max_subst_h2

    def __str__(self):
        return "SC(" + str(self.electricity) + ", " + str(self.heat) + ", " + str(self.hydrogen) + ")"

    def scale(self, scalar: float) -> None:
        """
        Scales member variables component-wise with scalar.

        :param scalar: The scalar to scale the components.
        """
        self.electricity *= scalar
        self.heat *= scalar
        self.hydrogen *= scalar

    def cap_at_bat(self, bat: EH) -> None:
        """
        Caps the specific consumption, as it cannot be better than the best available technology.

        :param bat: The best available technology consumption to cap this specific consumption.
        """
        if np.isnan(bat.electricity) or np.isnan(bat.heat):
            self.electricity = max(0.0, self.electricity)
            self.heat = max(0.0, self.heat)
            self.hydrogen = max(0.0, self.hydrogen)
        self.electricity = max(bat.electricity, self.electricity)
        self.heat = max(bat.heat, self.heat)
        self.hydrogen = max(0.0, self.hydrogen)


class Heat:
    """
    A container for heat split into heat levels. Offers arithmetic operations.

    :param float q1: Amount for heat level Q1
    :param float q2: Amount for heat level Q2
    :param float q3: Amount for heat level Q3
    :param float q4: Amount for heat level Q4

    :ivar float q1: Amount for heat level Q1
    :ivar float q2: Amount for heat level Q2
    :ivar float q3: Amount for heat level Q3
    :ivar float q4: Amount for heat level Q4
    """
    def __init__(self, q1: float = 0, q2: float = 0, q3: float = 0, q4: float = 0):
        self.q1 = float(q1)
        self.q2 = float(q2)
        self.q3 = float(q3)
        self.q4 = float(q4)

    def __str__(self):
        return "Heat:[" + str(self.q1) + ", " + str(self.q2) + ", " + str(self.q3) + ", " + str(self.q4) + ")"

    def mutable_add(self, heat: Heat) -> None:
        """
        Adds the parameter heat component-wise to self.

        :param heat: The heat that is added to self.
        """
        self.q1 += heat.q1
        self.q2 += heat.q2
        self.q3 += heat.q3
        self.q4 += heat.q4

    def copy_add(self, heat: Heat) -> Heat:
        """
        Performs addition between self and parameter heat and returns the result as a fresh object.
        Does not change self.

        :param heat: The other heat that is part of the addition.
        :return: The result of the addition.
        """
        return Heat(self.q1 + heat.q1, self.q2 + heat.q2, self.q3 + heat.q3, self.q4 + heat.q4)

    def mutable_sub(self, heat: Heat) -> None:
        """
        Subtracts the parameter heat component-wise from self.

        :param heat: The heat that is subtracted from self.
        """
        self.q1 -= heat.q1
        self.q2 -= heat.q2
        self.q3 -= heat.q3
        self.q4 -= heat.q4

    def mutable_multiply_scalar(self, scalar: float) -> None:
        """
        Scales the heat by a scalar.

        :param scalar: The scalar to scale the heat.
        """
        self.q1 *= scalar
        self.q2 *= scalar
        self.q3 *= scalar
        self.q4 *= scalar

    def copy_multiply_scalar(self, scalar: float) -> Heat:
        """
        Performs scaling between self and parameter scalar and returns the result as a fresh object.
        Does not change self.

        :param scalar: The scalar to scale the heat.
        :return: The result of the scaling.
        """
        return Heat(self.q1 * scalar, self.q2 * scalar, self.q3 * scalar, self.q4 * scalar)

    def copy_multiply(self, heat: Heat) -> Heat:
        """
        Performs multiplication between self and parameter heat and returns the result as a fresh object.
        Does not change self.

        :param heat: The other heat that is part of the multiplication.
        :return: The result of the multiplication.
        """
        return Heat(self.q1 * heat.q1, self.q2 * heat.q2, self.q3 * heat.q3, self.q4 * heat.q4)

    def get_sum(self) -> float:
        """ Sums all heat levels and returns the result. """
        return self.q1 + self.q2 + self.q3 + self.q4


class Demand:
    """
    A container for the amount of demand split into different categories. Provides arithmetic operations.

    :param float electricity: Amount of electricity demand.
    :param Heat heat: Amount of heat demand.
    :param float hydrogen: Amount of hydrogen demand.

    :ivar float electricity: Amount of electricity demand.
    :ivar Heat heat: Amount of heat demand.
    :ivar float hydrogen: Amount of hydrogen demand.
    """
    def __init__(self, electricity: float = 0, heat: Heat = None, hydrogen: float = 0):
        self.electricity = electricity
        if heat is None:
            self.heat = Heat()
        else:
            self.heat = heat
        self.hydrogen = hydrogen

    def __str__(self):
        return "<Demand: " + "electricity: " + str(self.electricity) + ", heat: " + str(self.heat) + ", hydrogen: " + \
            str(self.hydrogen) + ">"

    def set(self, dt: DemandType, value: Any) -> None:
        """
        Set the attribute value according to demand type.

        :param dt: The type of demand that should be set.
        :param value: The value the demand should be set to.
        """
        match dt:
            case DemandType.ELECTRICITY:
                assert(isinstance(value, float) or isinstance(value, int))
                self.electricity = value
            case DemandType.HEAT:
                assert (isinstance(value, Heat))
                self.heat = value
            case DemandType.HYDROGEN:
                assert (isinstance(value, float) or isinstance(value, int))
                self.hydrogen = value

    def get(self, dt: DemandType) -> Any:
        """
        Get the attribute value according to demand type.

        :param dt: The type of demand that should be returned.
        """
        match dt:
            case DemandType.ELECTRICITY:
                return self.electricity
            case DemandType.HEAT:
                return self.heat
            case DemandType.HYDROGEN:
                return self.hydrogen

    def add(self, other: Demand) -> None:
        """ Add the values of "other" demand component-wise to own member variables. """
        self.electricity += other.electricity
        self.heat.mutable_add(other.heat)
        self.hydrogen += other.hydrogen

    def scale(self, scalar: float) -> None:
        """ Scale member variables component-wise with scalar. """
        self.electricity *= scalar
        self.hydrogen *= scalar
        self.heat.mutable_multiply_scalar(scalar)

    def copy_scale(self, scalar: float) -> Demand:
        """ Create a new Demand object, that is the scaled version of self. """
        return Demand(self.electricity * scalar, self.heat.copy_multiply_scalar(scalar), self.hydrogen * scalar)
