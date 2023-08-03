from endemo2.general.demand_containers import Demand


class Product:

    def __init__(self, country_name, product_name, product_instance_filter):
        self._product_instance_filter = product_instance_filter
        self._country_name = country_name
        self._product_name = product_name

    def calculate_demand(self) -> Demand:
        """
        Calculates the demand for this product. Returns zero demand when the _empty attribute is true.

        .. math::
            D(y)[TWh/T] = p*A(y)[T]*(c_{electricity}, c_{heat_{split}}, c_{hydrogen})[TWh/T]

        :return: The calculated demand.
        """

        sc = self._product_instance_filter.get_specific_consumption_po(self._country_name, self._product_name)
        perc = self._product_instance_filter.get_perc_used(self._product_name)

        # choose which type of amount based on settings
        amount = self._product_instance_filter.get_amount(self._country_name, self._product_name)

        # calculate demand after all variables are available
        cached_perc_amount = perc * amount
        electricity = cached_perc_amount * sc.electricity
        hydrogen = cached_perc_amount * sc.hydrogen
        heat_total = cached_perc_amount * sc.heat

        # split heat levels
        heat_levels = self._product_instance_filter.get_heat_levels()
        heat_in_levels = heat_levels.copy_multiply_scalar(heat_total)  # separate heat levels

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

