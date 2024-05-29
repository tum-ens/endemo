from itertools import repeat

from endemo2.data_structures.containers import Demand, Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.model_instance.model.industry.products import Product
from endemo2.model_instance.instance_filter.industry_instance_filter \
    import IndustryInstanceFilter, ProductInstanceFilter
from endemo2.model_instance.model.sector import Sector


class Industry(Sector):
    """
    The Industry class represents the industry sector of one country. It holds all products produced by this industry.

    :ivar str _country_name: Name of the country this industry is located in.
    :ivar dict[str, Product] _products: All products in this industry.
    """

    def __init__(self, country_name, industry_instance_filter: IndustryInstanceFilter,
                 product_instance_filter: ProductInstanceFilter):
        super().__init__(country_name, industry_instance_filter)

        active_products = industry_instance_filter.get_active_product_names()
        active_products_country = industry_instance_filter.get_active_products_for_this_country(country_name)

        self._products = dict[str, Product]()
        for product_name in active_products:
            if product_name in active_products_country:
                self._products[product_name] = Product(country_name, product_name, product_instance_filter)
            else:
                self._products[product_name] = \
                    Product(country_name, product_name, product_instance_filter, is_empty=True)

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

        rest_calc_data = self._instance_filter.get_rest_sector_proportion_in_basis_year(self._country_name)
        rest_growth_rate = self._instance_filter.get_rest_sector_growth_rate()
        rest_heat_levels = self._instance_filter.get_rest_sector_heat_levels()

        start_year = self._instance_filter.get_rest_sector_basis_year()
        target_year = self._instance_filter.get_target_year()

        result = Demand()

        for demand_type, (perc_start_year, demand_start_year) in rest_calc_data.items():
            rest_start_year = perc_start_year * demand_start_year
            rest_target_year = \
                rest_start_year * (1 + rest_growth_rate) ** (target_year - start_year)
            if demand_type == DemandType.HEAT:
                rest_target_year = rest_heat_levels.copy_multiply_scalar(rest_target_year)
            result.set(demand_type, rest_target_year)

        return result

    def calculate_rest_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calls the calculate_rest_sector_demand function and splits the result according to capacity for each NUTS2
        region.

        :return: The dictionary of {nuts2_region -> demand}.
        """
        rest_demand = self.calculate_rest_sector_demand()
        nuts2_capacities = self._instance_filter.get_nuts2_rest_sector_distribution(self._country_name)

        resulting_distributed_demand = dict[str, Demand]()
        for region_name, capacity in nuts2_capacities.items():
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

    def calculate_forecasted_hourly_demand(self) -> dict[DemandType, [float]]:
        """
        Calculate the hourly demand for this industry.

        :return: The hourly demand in a list in order by demand type.
        """

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = list(repeat(0.0, 8760))
        res_dict[DemandType.HEAT] = list(repeat(Heat(), 8760))
        res_dict[DemandType.HYDROGEN] = list(repeat(0.0, 8760))

        for product_name, product_obj in self._products.items():
            product_hourly_demand = product_obj.calculate_hourly_demand()
            res_dict[DemandType.ELECTRICITY] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.ELECTRICITY], product_hourly_demand[DemandType.ELECTRICITY]))]
            res_dict[DemandType.HEAT] = \
                [res_value.copy_add(new_value) for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HEAT], product_hourly_demand[DemandType.HEAT]))]
            res_dict[DemandType.HYDROGEN] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HYDROGEN], product_hourly_demand[DemandType.HYDROGEN]))]
        return res_dict

    def calculate_forecasted_hourly_demand_distributed_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
        """
        Calculate the hourly demand for this industry distributed by NUTS2 regions.

        :return: The hourly demand in a list in order by demand type.
        """

        res_dict = dict[str, dict[DemandType, [float]]]()

        for region_name in self._instance_filter.get_nuts2_regions(self._country_name):
            res_dict[region_name] = dict[DemandType, [float]]()
            res_dict[region_name][DemandType.ELECTRICITY] = list(repeat(0.0, 8760))
            res_dict[region_name][DemandType.HEAT] = list(repeat(Heat(), 8760))
            res_dict[region_name][DemandType.HYDROGEN] = list(repeat(0.0, 8760))

            for product_name, product_obj in self._products.items():
                product_hourly_demand = product_obj.calculate_hourly_demand_distributed_by_nuts2()

                res_dict[region_name][DemandType.ELECTRICITY] = \
                    [res_value + new_value for (res_value, new_value)
                     in zip(res_dict[region_name][DemandType.ELECTRICITY],
                            product_hourly_demand[region_name][DemandType.ELECTRICITY])]
                res_dict[region_name][DemandType.HEAT] = \
                    [res_value.copy_add(new_value) for (res_value, new_value)
                     in zip(res_dict[region_name][DemandType.HEAT],
                            product_hourly_demand[region_name][DemandType.HEAT])]
                res_dict[region_name][DemandType.HYDROGEN] = \
                    [res_value + new_value for (res_value, new_value)
                     in zip(res_dict[region_name][DemandType.HYDROGEN],
                            product_hourly_demand[region_name][DemandType.HYDROGEN])]
        return res_dict

    def calculate_rest_sector_hourly_demand(self) -> dict[DemandType, [float]]:
        """
        Calculate the hourly demand for the rest sector of this industry.

        :return: The hourly demand in a list in order by demand type.
        """

        rest_demand = self.calculate_rest_sector_demand()
        hourly_profile = self._instance_filter.get_rest_sector_hourly_profile(self._country_name)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [rest_demand.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [rest_demand.heat.copy_multiply_scalar(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [rest_demand.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict

    def calculate_rest_sector_hourly_demand_distributed_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
        """
        Calculate the hourly demand for the rest sector of this industry distributed.

        :return: The hourly demand in a list in order by demand type.
        """

        rest_demands = self.calculate_rest_demand_distributed_by_nuts2()
        hourly_profile = self._instance_filter.get_rest_sector_hourly_profile(self._country_name)

        res_dict = dict[str, dict[DemandType, [float]]]()

        for region_name, region_demand in rest_demands.items():
            res_dict[region_name] = dict[DemandType, [float]]()
            res_dict[region_name][DemandType.ELECTRICITY] = [region_demand.electricity * hour_perc
                                                             for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
            res_dict[region_name][DemandType.HEAT] = [region_demand.heat.copy_multiply_scalar(hour_perc)
                                                      for hour_perc in hourly_profile[DemandType.HEAT]]
            res_dict[region_name][DemandType.HYDROGEN] = [region_demand.hydrogen * hour_perc
                                                          for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict

    def calculate_total_hourly_demand(self) -> dict[DemandType, [float]]:
        """
        Calculate total hourly demand, including the forecasted hourly demand and rest sector.

        :return: The total hourly demand summed over all products in this industry and rest sector.
        """
        forecasted_hourly = self.calculate_forecasted_hourly_demand()
        rest_hourly = self.calculate_rest_sector_hourly_demand()

        zipped_hourly_demands = dict[DemandType, [(float, float)]]()
        for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
            zipped_hourly_demands[demand_type] = list(zip(forecasted_hourly[demand_type], rest_hourly[demand_type]))

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [f + r for (f, r) in zipped_hourly_demands[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [f.copy_add(r) for (f, r) in zipped_hourly_demands[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [f + r for (f, r) in zipped_hourly_demands[DemandType.HYDROGEN]]

        return res_dict

    def calculate_total_hourly_demand_distributes_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
        """
        Calculate total hourly demand, including the forecasted hourly demand and rest sector.

        :return: The total hourly demand summed over all products in this industry and rest sector.
        """
        forecasted_hourly = self.calculate_forecasted_hourly_demand_distributed_by_nuts2()
        rest_hourly = self.calculate_forecasted_hourly_demand_distributed_by_nuts2()

        res_dict = dict[str, dict[DemandType, [float]]]()

        for region_name in forecasted_hourly.keys():
            zipped_hourly_demands = dict[DemandType, [(float, float)]]()
            for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                zipped_hourly_demands[demand_type] = list(zip(forecasted_hourly[region_name][demand_type],
                                                              rest_hourly[region_name][demand_type]))

            res_dict[region_name] = dict()
            res_dict[region_name][DemandType.ELECTRICITY] = \
                [f + r for (f, r) in zipped_hourly_demands[DemandType.ELECTRICITY]]
            res_dict[region_name][DemandType.HEAT] = \
                [f.copy_add(r) for (f, r) in zipped_hourly_demands[DemandType.HEAT]]
            res_dict[region_name][DemandType.HYDROGEN] = \
                [f + r for (f, r) in zipped_hourly_demands[DemandType.HYDROGEN]]

        return res_dict








