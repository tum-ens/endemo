from enum import Enum
from pathlib import Path

from endemo2 import containers as ctn


class SectorIdentifier(Enum):
    INDUSTRY = 0


class Sector:
    save_path: Path

    def calculate_total_demand(self, year: int) -> ctn.Demand:
        # calculate useful energy demand of sector
        # has to be overwritten by child class
        raise NotImplementedError
