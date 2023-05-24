import pandas as pd

from products import Product
from sector import Sector


class Industry(Sector):
    _products: dict[str, Product]

    #def __init__(self, country: Country, product_data: dict[str, list[float, float]]):
     #   for [product_name, data] in product_data:
      #      self._products[product_name] = Product()


    def calculate(self) -> int:
        # calculate industry sector
        print("Calculating industry sector...")
        pass
