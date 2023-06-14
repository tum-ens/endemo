import warnings

import pandas as pd

import country as cty
import input
import output
import prediction_models as pm
import products as prd
import sector
import input


class Industry(sector.Sector):
    _products: dict[str, prd.Product]

    def __init__(self, country_name: str, country_population: pm.PredictedTimeseries, country_gdp: pm.TimeStepSequence,
                 input_manager: input.Input):
        self._products = dict()
        active_products = input_manager.industry_input.active_products

        for (product_name, product_input) in active_products.items():
            self._products[product_name] = prd.Product(product_name, product_input, input_manager,
                                                       country_name, country_population, country_gdp)

        # create warnings
        if not self._products:
            warnings.warn("Industry Sector in Country " + country_name + " has an empty list of products.")

    def calculate_total_demand(self, year: int) -> output.Demand:
        # calculate industry sector for country by summing up all products
        result = output.Demand()

        for (name, obj) in self._products.items():
            result.add(obj.calculate_demand(year))

        return result

    def calculate_product_demand(self, product_name: str, year: int) -> output.Demand:
        if product_name in self._products.keys():
            return self._products[product_name].calculate_demand(year)
        else:
            # if product not in industry, there is no demand -> return 0ed demand
            return output.Demand()

    def prog_product_amount(self, product_name: str, year: int) -> float:
        if product_name in self._products.keys():
            return self._products[product_name].get_amount_prog(year)
        else:
            # if product not in industry, there is no demand -> return 0ed demand
            return 0
