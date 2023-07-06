import warnings

from endemo2 import population as pop
from endemo2 import prediction_models as pm
from endemo2 import products as prd
from endemo2 import sector, input
from endemo2 import containers as ctn


class Industry(sector.Sector):
    """
    The Industry class represents the industry sector of one country. It holds all products produced by this industry.

    :param str country_name: Name of the country this industry is located in.
    :param Population population: The population object of the country.
    :param TimeStepSequence country_gdp: The countries' GDP Timeseries
    :param Input input_manager: The models input data from the Excel files.

    :ivar dict[str, Product] _products: All products in this industry.
    """

    def __init__(self, country_name: str, population: pop.Population, country_gdp: pm.TimeStepSequence,
                 input_manager: input.Input):
        self._products = dict()
        active_products = input_manager.industry_input.active_products

        for (product_name, product_input) in active_products.items():
            self._products[product_name] = prd.Product(product_name, product_input, input_manager,
                                                       country_name, population, country_gdp)

        # create warnings
        if not self._products:
            warnings.warn("Industry Sector in Country " + country_name + " has an empty list of products.")

    def get_product(self, name: str) -> prd.Product:
        """
        Getter for a product from the industry.

        :param name: Name of the product. Example: "steel_prim".
        :return: Product object with the matching name.
        """
        return self._products[name]

    def calculate_total_demand(self, year: int) -> ctn.Demand:
        """
        Sums over the demand of each product.

        :param year: Target year the demand should be calculated for.
        :return: The demand summed over all products in this industry.
        """
        result = ctn.Demand()

        for (name, obj) in self._products.items():
            result.add(obj.calculate_demand(year))

        return result

    def calculate_product_demand(self, product_name: str, year: int) -> ctn.Demand:
        """
        Getter for a products demand by product name and for the year.
        If the product is not in the industry, a Demand object indicating zero demand is returned.

        :param product_name: The name of the product, whose demand should be returned.
        :param year: Target year the demand should be calculated for.
        :return: The demand of the product in this industry.
        """
        if product_name in self._products.keys():
            return self._products[product_name].calculate_demand(year)
        else:
            # if product not in industry, there is no demand -> return 0ed demand
            return ctn.Demand()

    def prog_product_amount(self, product_name: str, year: int) -> float:
        """
        Getter for the predicted amount of a product within this industry.

        :param product_name: Name of the product. Example: "steel_prim".
        :param year: Target year, which the amount should be calculated for.
        :return: The products predicted amount in target year.
        """
        if product_name in self._products.keys():
            return self._products[product_name].get_amount_prog(year)
        else:
            # if product not in industry, there is no amount -> return 0
            return 0
