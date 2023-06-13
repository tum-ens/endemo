from __future__ import annotations
from collections import namedtuple


class Heat:
    q1: float
    q2: float
    q3: float
    q4: float

    def __int__(self, q1=0, q2=0, q3=0, q4=0):
        self.q1 = q1
        self.q2 = q2
        self.q3 = q3
        self.q4 = q4

    def add(self, heat: Heat):
        self.q1 += heat.q1
        self.q2 += heat.q2
        self.q3 += heat.q3
        self.q4 += heat.q4


class Demand:
    electricity: float
    heat: Heat
    hydrogen: float

    def __init__(self):
        self.electricity = 0
        self.heat = Heat(0, 0, 0, 0)
        self.hydrogen = 0

    def __init__(self, electricity: float, heat: (float, float, float, float), hydrogen: float):
        self.electricity = electricity
        self.heat = heat
        self.hydrogen = hydrogen

    def add(self, other: Demand):
        self.electricity += other.electricity
        self.heat += other.heat
        self.hydrogen += other.hydrogen
