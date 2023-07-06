from endemo2 import containers as ctn
from endemo2 import sector


class Household(sector.Sector):
    def calculate_total_demand(self, year: int) -> ctn.Demand:
        """ Not implemented yet. calculate household sector """
        print("Household sector is not implemented yet.")
        pass
