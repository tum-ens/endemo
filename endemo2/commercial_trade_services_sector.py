from endemo2 import containers as ctn

from endemo2 import sector


class CommercialTradeServices(sector.Sector):
    def calculate_forecasted_demand(self, year: int) -> ctn.Demand:
        """ Not implemented yet. calculate commercial, trade, services sector """
        print("Commercial_Trade_Services sector is not implemented yet.")
        pass
