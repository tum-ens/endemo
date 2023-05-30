import pandas as pd

from output import Demand
from products import Product
from sector import Sector


class Industry(Sector):
    _products: dict[str, Product]

    #def __init__(self, country: Country, product_data: dict[str, list[float, float]]):
     #   for [product_name, data] in product_data:
      #      self._products[product_name] = Product()

    def __init__(self, products : dict[str, Product]):
        self._products = products

    def calculate_demand(self, year: int) -> Demand:
        # calculate industry sector for country by summing up all products
        result = Demand()

        for (name, obj) in self._products:
            result.add(obj.calculate_demand(year))

        return result
