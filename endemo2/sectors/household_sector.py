from endemo2.general import demand_containers as dc
from endemo2.sectors import sector


class Household(sector.Sector):
    def calculate_forecasted_demand(self, year: int) -> dc.Demand:
        """ Not implemented yet. calculate household sector """
        print("Household sector is not implemented yet.")
        pass
