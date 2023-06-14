from __future__ import annotations
from collections import namedtuple

import input


class Heat:
    q1: float
    q2: float
    q3: float
    q4: float

    def __init__(self, q1=0, q2=0, q3=0, q4=0):
        self.q1 = float(q1)
        self.q2 = float(q2)
        self.q3 = float(q3)
        self.q4 = float(q4)

    def __str__(self):
        return "Heat:[" + str(self.q1) + ", " + str(self.q2) + ", " + str(self.q3) + ", " + str(self.q4) + ")"

    def add(self, heat: Heat):
        self.q1 += heat.q1
        self.q2 += heat.q2
        self.q3 += heat.q3
        self.q4 += heat.q4

    def multiply_scalar(self, scalar: float):
        self.q1 *= scalar
        self.q2 *= scalar
        self.q3 *= scalar
        self.q4 *= scalar


class Demand:
    electricity: float
    heat: Heat
    hydrogen: float

    def __init__(self, electricity: float = 0, heat: Heat = Heat(), hydrogen: float = 0):
        self.electricity = electricity
        self.heat = heat
        self.hydrogen = hydrogen

    def __str__(self):
        return "<Demand: " + "electricity: " + str(self.electricity) + ", heat: " + str(self.heat) + ", hydrogen: " + \
            str(self.hydrogen) + ">"

    def add(self, other: Demand):
        self.electricity += other.electricity
        self.heat.add(other.heat)
        self.hydrogen += other.hydrogen


def generate_output(input_manager: input.Input):
    pass