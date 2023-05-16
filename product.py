from collections import namedtuple

import pandas as pd
from countries import Country

#completely rework
class Product:
    _name: str
    _amount_series: pd.DataFrame
    _specific_demand: pd.DataFrame


    def __init__(self, product_name: str, excel: pd.DataFrame, specific_demand: pd.DataFrame):
        self._name = product_name
        Country.check_for_wrong_countries_in_file(product_name + "_Production.xlsx", excel.get("Country"))
        self._amount_series = excel
        self._specific_demand = specific_demand

    def __str__(self):
        return "<Product Name: " + self._name + ">"

    def predict_amount_for_year(self, year: int):
        pass

    def predict_spec_dem_for_year(self, year: int):
        pass

class Product_extended(Product):
    _other_properties : str





