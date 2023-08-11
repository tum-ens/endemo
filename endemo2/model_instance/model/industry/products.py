from endemo2.data_structures.containers import Demand, Heat
from endemo2.data_structures.enumerations import DemandType


class Product:

    def __init__(self, country_name, product_name, product_instance_filter, is_empty=False):
        self._product_instance_filter = product_instance_filter
        self._country_name = country_name
        self._product_name = product_name
        self._is_empty = is_empty

    def calculate_demand(self) -> Demand:
        """
        Calculates the demand for this product. Returns zero demand when the _empty attribute is true.

        .. math::
            D(y)[TWh/T] = p*A(y)[T]*(c_{electricity}, c_{heat_{split}}, c_{hydrogen})[TWh/T]

        :return: The calculated demand.
        """
        if self._is_empty:
            return Demand(0, Heat(), 0)

        sc = self._product_instance_filter.get_specific_consumption(self._country_name, self._product_name)
        perc = self._product_instance_filter.get_perc_used(self._product_name)

        # choose which type of amount based on settings
        amount = self._product_instance_filter.get_amount(self._country_name, self._product_name)

        # calculate demand after all variables are available
        cached_perc_amount = perc * amount
        electricity = cached_perc_amount * sc.electricity
        hydrogen = cached_perc_amount * sc.hydrogen
        heat_total = cached_perc_amount * sc.heat

        # split heat levels
        heat_levels = self._product_instance_filter.get_heat_levels(self._product_name)
        heat_in_levels = heat_levels.copy_multiply_scalar(heat_total)  # separate heat levels

        # substitution
        substitution_perc: dict[DemandType, Heat] = self._product_instance_filter.get_heat_substitution()
        electricity_subst_amount = substitution_perc[DemandType.ELECTRICITY].copy_multiply(heat_in_levels)
        hydrogen_subst_amount = substitution_perc[DemandType.HYDROGEN].copy_multiply(heat_in_levels)

        heat_in_levels.mutable_sub(electricity_subst_amount)
        heat_in_levels.mutable_sub(hydrogen_subst_amount)
        electricity += electricity_subst_amount.get_sum()
        hydrogen += hydrogen_subst_amount.get_sum()

        return Demand(electricity, heat_in_levels, hydrogen)

    def get_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculated demand and distributes result according to installed capacities of nuts2

        :return: The demand distributed by nuts2 regions as a dictionary {region_name -> region_demand}
        """
        product_demand = self.calculate_demand()
        installed_capacities = \
            self._product_instance_filter.get_nuts2_capacities(self._country_name, self._product_name)

        distributed_demand = dict[str, Demand]()

        for (nuts2_region_name, installed_capacity) in installed_capacities.items():
            region_demand = product_demand.copy_scale(installed_capacity)
            distributed_demand[nuts2_region_name] = region_demand

        return distributed_demand

    def calculate_hourly_demand(self) -> dict[DemandType, [float]]:
        """
        Calculate the hourly demand for this product.

        :return: The hourly demand in a list in order by demand type.
        """

        product_demand = self.calculate_demand()
        hourly_profile = self._product_instance_filter.get_hourly_profile(self._country_name, self._product_name)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [product_demand.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [product_demand.heat.copy_multiply_scalar(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [product_demand.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]

        return res_dict

    def calculate_hourly_demand_distributed_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
        """
        Calculate the hourly demand for this product distributed to nuts2 regions.

        :return: The hourly demand in a list in order by demand type for every nuts2 region.
        """

        nuts2_demands = self.get_demand_distributed_by_nuts2()
        hourly_profile = self._product_instance_filter.get_hourly_profile(self._country_name, self._product_name)

        res_dict = dict[str, dict[DemandType, [float]]]()

        for region_name, region_demand in nuts2_demands.items():
            res_dict[region_name] = dict[DemandType, [float]]()
            res_dict[region_name][DemandType.ELECTRICITY] = [region_demand.electricity * hour_perc
                                                             for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
            res_dict[region_name][DemandType.HEAT] = [region_demand.heat.copy_multiply_scalar(hour_perc)
                                                      for hour_perc in hourly_profile[DemandType.HEAT]]
            res_dict[region_name][DemandType.HYDROGEN] = [region_demand.hydrogen * hour_perc
                                                          for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict
