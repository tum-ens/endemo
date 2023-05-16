from pathlib import Path


class Sector:

    input_path: Path

    def calculate_demand(self) -> (float, float, float):
        # calculate useful energy demand of sector
        # has to be overwritten by child class
        raise NotImplementedError
