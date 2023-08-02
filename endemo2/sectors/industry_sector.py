import warnings

from endemo2.utility import prediction_models as pm
from endemo2.industry import products as prd
from endemo2.sectors import sector
from endemo2.general import demand_containers as dc
from endemo2.general import country_containers as cc
from endemo2.preprocessing import preprocessor as pp


class Industry(sector.Sector):
    """
    The Industry class represents the industry sector of one country. It holds all products produced by this industry.

    :param Population population: The population object of the country.
    :param DataStepSequence country_gdp: The countries' GDP DataAnalyzer
    :param Input input_manager: The models preprocessing data from the Excel files.


    :ivar str country_name: Name of the country this industry is located in.
    :ivar dict[str, Product] _products: All products in this industry.
    :ivar int rest_calc_basis_year: Year that is used as the starting point for the rest sector percentage prediction.
    :ivar dict[DemandType, (float, float)] rest_calc_data: rest sector start-percentage and rest sector start-demand,
        used to forecast the rest sector demand for a certain year.
    :ivar float rest_growth_rate: Growth rate percentage of the rest sector as specified in
        Set_and_Control_Parameters.xlsx in interval [0,1].
    :ivar Population country_population: The population of the country, this industry belongs to.
    :ivar bool nuts2_distribution_by_installed_capacities: If true, distribution of (forecasted) demand over nuts2
        regions is calculated by percentages given in the installed_capacities file, otherwise distribution is
        calculated according to population density.
    """

    def __init__(self, country_name: str, population: cc.Population,
                 country_gdp: pm.DataStepSequence, preprocessor: pp.Preprocessor):
        input_manager = preprocessor.input_manager
        self._products = dict()
        self.country_name = country_name
        self.country_population = population
        active_products = input_manager.industry_input.active_products
        self.nuts2_distribution_by_installed_capacities = \
            input_manager.ctrl.industry_settings.nuts2_distribution_based_on_installed_ind_capacity

        for (product_name, _) in active_products.items():
            self._products[product_name] = prd.Product(product_name, preprocessor,
                                                       country_name, population, country_gdp)

        # store rest sector calculation parameters
        rest_sector_input = input_manager.industry_input.rest_sector_input
        self.rest_calc_basis_year = rest_sector_input.rest_calc_basis_year
        self.rest_calc_data = rest_sector_input.rest_calc_data[country_name]
        self.rest_heat_levels = rest_sector_input.rest_sector_heat_levels
        self.rest_growth_rate = input_manager.ctrl.industry_settings.rest_sector_growth_rate

        # create warnings
        if not self._products:
            warnings.warn("Industry Sector in Country " + country_name + " has an empty list of products.")

    def get_product(self, name: str) -> prd.Product:
        """
        Getter for a product from the industry.

        :param str name: Name of the product. Example: "steel_prim".
        :return: Product object with the matching name.
        """
        return self._products[name]

    def calculate_rest_sector_demand(self, target_year: int) -> dc.Demand:
        """
        Calculate the rest sector demand for a certain year.

        .. math::
            rest_{\\text{start_year}}[TWh]=perc_{\\text{start_year}}*demand_{\\text{start_year}}[TWh]\\\\
            rest(y)[TWh] = rest_{\\text{start_year}}[TWh]*(1+r)^{y-\\text{start_year}}


        :param int target_year: The year, the rest sector demand should be calculated for.
        :return: The demand of the rest sector in given year rest(y).
        """
        result = dc.Demand()

        for dt, (perc_sy, demand_sy) in self.rest_calc_data.items():
            rest_start_year = perc_sy * demand_sy
            rest_target_year = \
                rest_start_year * (1 + self.rest_growth_rate) ** (target_year - self.rest_calc_basis_year)
            if dt == dc.DemandType.HEAT:
                rest_target_year = self.rest_heat_levels.copy_multiply_scalar(rest_start_year)
            result.set(dt, rest_target_year)

        return result

    def calculate_forecasted_demand(self, year: int) -> dc.Demand:
        """
        Sums over the demand of each product.

        :param int year: Target year the demand should be calculated for.
        :return: The demand summed over all products in this industry.
        """
        result = dc.Demand()

        for (name, _) in self._products.items():
            result.add(self.calculate_product_demand(name, year))

        return result

    def calculate_total_demand(self, year: int) -> dc.Demand:
        """
        Calculate total demand, including the forecasted demand and rest sector.

        :param int year: Target year the demand should be calculated for.
        :return: The total demand summed over all products in this industry and rest sector.
        """
        total_demand = dc.Demand()
        total_demand.add(self.calculate_forecasted_demand(year))
        total_demand.add(self.calculate_rest_sector_demand(year))
        return total_demand

    def calculate_product_demand(self, product_name: str, year: int) -> dc.Demand:
        """
        Getter for a products demand by product name and for the year.
        If the product is not in the industry, a Demand object indicating zero demand is returned.

        :param str product_name: The name of the product, whose demand should be returned.
        :param int year: Target year the demand should be calculated for.
        :return: The demand of the product in this industry.
        """
        if product_name in self._products.keys():
            product_obj = self._products[product_name]
            product_demand = product_obj.calculate_demand(year)
            if product_obj.is_per_capita():
                product_demand.scale((self.country_population.get_country_prog(year)))
            return product_demand
        else:
            # if product not in industry, there is no demand -> return 0ed demand
            return dc.Demand()

    def calculate_demand_split_by_nuts2(self, product_name: str, year: int) -> dict[str, dc.Demand]:
        """
        Calls the calculate_product_demand function and splits the result according to capacity for each NUTS2 region.

        :param str product_name: Name of product to calculate demand for.
        :param int year: The target year, the demand should be calculated for.
        :return: The dictionary of {nuts2_region -> demand}.
        """
        country_demand = self.calculate_product_demand(product_name, year)

        result = dict[str, dc.Demand]()

        if self.nuts2_distribution_by_installed_capacities:
            product_obj = self._products[product_name]
            nuts2_installed_capacity = product_obj.get_nuts2_installed_capacities()

            for (nuts2_region_name, perc) in nuts2_installed_capacity.items():
                region_demand = country_demand.copy_scale(perc)
                result[nuts2_region_name] = region_demand
        else:
            nuts2_root = self.country_population.get_nuts2_root()
            nuts2_objs = nuts2_root.get_all_leaf_nodes()
            for nuts2_obj in nuts2_objs:
                region_demand = country_demand.copy_scale(nuts2_root.get_pop_perc_of_subregion_in_year(nuts2_obj, year))
                result[nuts2_obj.get_region_name()] = region_demand

        return result

    def calculate_rest_demand_split_by_nuts2(self, year: int) -> dict[str, dc.Demand]:
        """
        Calls the calculate_rest_sector_demand function and splits the result according to capacity for each NUTS2
        region.

        :param int year: The target year, the demand should be calculated for.
        :return: The dictionary of {nuts2_region -> demand}.
        """
        rest_demand = self.calculate_rest_sector_demand(year)
        nuts2_root = self.country_population.get_nuts2_root()
        nuts2_objs = nuts2_root.get_all_leaf_nodes()

        result = dict[str, dc.Demand]()

        for nuts2_obj in nuts2_objs:
            region_demand = rest_demand.copy_scale(nuts2_root.get_pop_perc_of_subregion_in_year(nuts2_obj, year))
            result[nuts2_obj.get_region_name()] = region_demand

        return result

    def calculate_forecasted_demand_split_by_nuts2(self, year: int) -> dict[str, dc.Demand]:
        """
        Calls the calculate_demand_split_by_nuts2 function and sums over all products.

        :param int year: The target year, the demand should be calculated for.
        :return: The dictionary of {nuts2_region -> demand}.
        """
        result = dict[str, dc.Demand]()

        for (product_name, _) in self._products.items():
            dict_product_demand_nuts2 = self.calculate_demand_split_by_nuts2(product_name, year)
            for (nuts2_name, nuts2_product_demand) in dict_product_demand_nuts2.items():
                if nuts2_name not in result.keys():
                    result[nuts2_name] = dc.Demand()
                result[nuts2_name].add(nuts2_product_demand)

        return result

    def calculate_total_demand_split_by_nuts2(self, year: int) -> dict[str, dc.Demand]:
        """
        Calculate total demand, including the forecasted demand and rest sector.

        :param int year: Target year the demand should be calculated for.
        :return: The total demand summed over all products in this industry and rest sector, split by nuts2 regions.
        """
        result = dict[str, dc.Demand]()
        forecasted_demand = self.calculate_forecasted_demand_split_by_nuts2(year)
        rest_demand = self.calculate_rest_demand_split_by_nuts2(year)

        for nuts2_code in forecasted_demand.keys():
            if nuts2_code not in rest_demand.keys():
                continue
            total_demand = dc.Demand()
            total_demand.add(forecasted_demand[nuts2_code])
            total_demand.add(rest_demand[nuts2_code])
            result[nuts2_code] = total_demand
        return result

    def prog_product_amount(self, product_name: str, year: int) -> float:
        """
        Getter for the predicted amount of a product within this industry.

        :param str product_name: Name of the product. Example: "steel_prim".
        :param int year: Target year, which the amount should be calculated for.
        :return: The products predicted amount in target year.
        """
        if product_name in self._products.keys():
            return self._products[product_name].get_amount_prog(year)
        else:
            # if product not in industry, there is no amount -> return 0
            return 0
