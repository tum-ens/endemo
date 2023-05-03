from collections import namedtuple

import pandas as pd
from countries import Countries


class Product:
    _name: str
    _product_data: pd.DataFrame


    def __init__(self, product_name: str, excel: pd.DataFrame, countries: Countries):
        self._name = product_name
        print(str(type(excel.get("Country"))) + product_name)
        countries.check_for_wrong_countries_in_file(product_name + "_Production.xlsx", excel.get("Country"))
        self._product_data = excel

    def predict_amount_for_year(self, year: int):
        pass




