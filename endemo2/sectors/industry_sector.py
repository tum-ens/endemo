from endemo2.general.demand_containers import Demand
from endemo2.enumerations import DemandType
from endemo2.industry.products import Product
from endemo2.model_instance.instance_filter import IndustryInstanceFilter, ProductInstanceFilter
from endemo2.sectors.sector import Sector


class Industry(Sector):
    """
    The Industry class represents the industry sector of one country. It holds all products produced by this industry.

    :ivar str country_name: Name of the country this industry is located in.
    :ivar dict[str, Product] _products: All products in this industry.
    """

    def __init__(self, country_name, industry_instance_filter: IndustryInstanceFilter,
                 product_instance_filter: ProductInstanceFilter):
        super().__init__()

        self._industry_instance_filter = industry_instance_filter
        self._country_name = country_name

        active_products = industry_instance_filter.get_active_product_names()

        self._products = dict[str, Product]()
        for product_name in active_products:
            self._products[product_name] = Product(country_name, product_name, product_instance_filter)

    def get_product(self, name: str) -> Product:
        """
        Getter for a product from the industry.

        :param str name: Name of the product. Example: "steel_prim".
        :return: Product object with the matching name.
        """
        return self._products[name]

    def calculate_rest_sector_demand(self) -> Demand:
        """
        Calculate the rest sector demand for a certain year.

        .. math::
            rest_{\\text{start_year}}[TWh]=perc_{\\text{start_year}}*demand_{\\text{start_year}}[TWh]\\\\
            rest(y)[TWh] = rest_{\\text{start_year}}[TWh]*(1+r)^{y-\\text{start_year}}

        :return: The demand of the rest sector in given year rest(y).
        """

        rest_calc_data = self._industry_instance_filter.get_rest_calc_data(self._country_name)
        rest_growth_rate = self._industry_instance_filter.get_rest_sector_growth_rate()
        rest_heat_levels = self._industry_instance_filter.get_rest_heat_levels()

        start_year = self._industry_instance_filter.get_rest_basis_year()
        target_year = self._industry_instance_filter.get_target_year()

        result = Demand()

        for demand_type, (perc_start_year, demand_start_year) in rest_calc_data:
            rest_start_year = perc_start_year * demand_start_year
            rest_target_year = \
                rest_start_year * (1 + rest_growth_rate) ** (target_year - start_year)
            if demand_type == DemandType.HEAT:
                rest_target_year = rest_heat_levels.copy_multiply_scalar(rest_start_year)
            result.set(demand_type, rest_target_year)

        return result

    def calculate_rest_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calls the calculate_rest_sector_demand function and splits the result according to capacity for each NUTS2
        region.

        :return: The dictionary of {nuts2_region -> demand}.
        """
        rest_demand = self.calculate_rest_sector_demand()
        nuts2_capacities = self._industry_instance_filter.get_nuts2_rest_sector_capacities(self._country_name)

        resulting_distributed_demand = dict[str, Demand]()
        for region_name, capacity in nuts2_capacities:
            resulting_distributed_demand[region_name] = rest_demand.copy_scale(capacity)

        return resulting_distributed_demand

    def calculate_forecasted_demand(self) -> Demand:
        """
        Sums over the forecasted demand of each product.

        :return: The demand summed over all products in this industry.
        """
        result = Demand()

        for (product_name, _) in self._products.items():
            product_demand = self._products[product_name].calculate_demand()
            result.add(product_demand)

        return result

    def calculate_forecasted_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calls the calculate_demand_split_by_nuts2 function and sums over all products.

        :return: The dictionary of {nuts2_region -> demand}.
        """
        result = dict[str, Demand]()

        for (product_name, product_obj) in self._products.items():
            dict_product_demand_nuts2 = product_obj.get_demand_distributed_by_nuts2()
            for (region_name, nuts2_product_demand) in dict_product_demand_nuts2.items():
                if region_name not in result.keys():
                    result[region_name] = Demand()
                result[region_name].add(nuts2_product_demand)

        return result

    def calculate_total_demand(self) -> Demand:
        """
        Calculate total demand, including the forecasted demand and rest sector.

        :return: The total demand summed over all products in this industry and rest sector.
        """
        total_demand = Demand()
        total_demand.add(self.calculate_forecasted_demand())
        total_demand.add(self.calculate_rest_sector_demand())
        return total_demand

    def calculate_total_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate total demand, including the forecasted demand and rest sector.

        :return: The total demand summed over all products in this industry and rest sector, split by nuts2 regions.
        """
        result = dict[str, Demand]()
        forecasted_demand = self.calculate_forecasted_demand_distributed_by_nuts2()
        rest_demand = self.calculate_rest_demand_distributed_by_nuts2()

        for region_name in forecasted_demand.keys():
            if region_name not in rest_demand.keys():
                continue
            total_demand = Demand()
            total_demand.add(forecasted_demand[region_name])
            total_demand.add(rest_demand[region_name])
            result[region_name] = total_demand
        return result


