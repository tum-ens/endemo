from __future__ import annotations
from collections import namedtuple

Heat = namedtuple("Heat", ["q1", "q2", "q3", "q4"])


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
