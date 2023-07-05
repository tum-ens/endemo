from __future__ import annotations

import collections as coll


SC = coll.namedtuple("SC", ["electricity", "heat", "hydrogen", "max_subst_h2"])
EH = coll.namedtuple("EH", ["electricity", "heat"])

CA = coll.namedtuple("CA", ["alpha2", "alpha3", "german_name"])
HisProg = coll.namedtuple("HisProg", ["historical", "prognosis"])
Interval = coll.namedtuple("Interval", ["start", "end"])


class Heat:
    """
    A container for heat split into heat levels. Offers arithmetic operations.

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

    def mutable_add(self, heat: Heat):
        self.q1 += heat.q1
        self.q2 += heat.q2
        self.q3 += heat.q3
        self.q4 += heat.q4

    def copy_add(self, heat: Heat) -> Heat:
        return Heat(self.q1 + heat.q1, self.q2 + heat.q2, self.q3 + heat.q3, self.q4 + heat.q4)

    def mutable_multiply_scalar(self, scalar: float):
        self.q1 *= scalar
        self.q2 *= scalar
        self.q3 *= scalar
        self.q4 *= scalar

    def copy_multiply_scalar(self, scalar: float) -> Heat:
        return Heat(self.q1 * scalar, self.q2 * scalar, self.q3 * scalar, self.q4 * scalar)


class Demand:
    """
    A container for the amount of demand split into different categories. Provides arithmetic operations.

    :ivar float electricity: Amount of electricity demand.
    :ivar Heat heat: Amount of heat demand.
    :ivar float hydrogen: Amount of hydrogen demand.
    """
    def __init__(self, electricity: float = 0, heat: Heat = Heat(), hydrogen: float = 0):
        self.electricity = electricity
        self.heat = heat
        self.hydrogen = hydrogen

    def __str__(self):
        return "<Demand: " + "electricity: " + str(self.electricity) + ", heat: " + str(self.heat) + ", hydrogen: " + \
            str(self.hydrogen) + ">"

    def add(self, other: Demand):
        """ Add the values of "other" demand component-wise to own member variables. """
        self.electricity += other.electricity
        self.heat.mutable_add(other.heat)
        self.hydrogen += other.hydrogen

    def scale(self, scalar: float):
        """ Scale member variables component-wise with scalar. """
        self.electricity *= scalar
        self.hydrogen *= scalar
        self.heat.mutable_multiply_scalar(scalar)
