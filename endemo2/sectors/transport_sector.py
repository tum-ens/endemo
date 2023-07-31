from endemo2.general import demand_containers as dc
from endemo2.sectors import sector


class Transport(sector.Sector):
    def calculate_forecasted_demand(self, year: int) -> dc.Demand:
        # calculate transport sector
        print("Transport sector is not implemented yet.")
        pass
