from endemo2 import containers as ctn
from endemo2 import sector


class Transport(sector.Sector):
    def calculate_total_demand(self, year: int) -> ctn.Demand:
        # calculate transport sector
        print("Transport sector is not implemented yet.")
        pass
