from endemo2.data_structures.containers import Demand, SpecConsum, Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.model_instance.instance_filter.cts_instance_filter import CtsInstanceFilter


class CtsSubsector:
    """
    The CtsSubsector represents a subsector of the Commercial Trades and Services sector.

    :ivar str _country_name: The name of the country this subsector belongs to.
    :ivar str _subsector_name: The name of the subsector.
    :ivar CtsInstanceFilter _cts_if: The instance filter of the cts sector.
    """

    def __init__(self, country_name, subsector_name: str, cts_instance_filter: CtsInstanceFilter):
        self._country_name = country_name
        self._subsector_name = subsector_name
        self._cts_if = cts_instance_filter

    def calculate_demand(self) -> Demand:
        """ Calculate demand for this subsector. """
        # get values from instance filter
        specific_consumption: SpecConsum = self._cts_if.get_specific_consumption(self._country_name)
        specific_consumption.scale(1 / 1000)  # TWh/thousand employees -> TWh/employee
        employees_perc_of_population: float = \
            self._cts_if.get_employee_share_of_population_country(self._country_name, self._subsector_name)
        population_country: float = self._cts_if.get_population_country(self._country_name)
        heat_levels: Heat = self._cts_if.get_heat_levels()

        # calculate demand
        employees = employees_perc_of_population * population_country
        electricity = employees * specific_consumption.electricity
        heat = employees * specific_consumption.heat
        hydrogen = 0.0

        # substitution
        substitution_perc: dict[DemandType, float] = self._cts_if.get_heat_substitution()
        electricity_subst_amount = heat * substitution_perc[DemandType.ELECTRICITY]
        hydrogen_subst_amount = heat * substitution_perc[DemandType.HYDROGEN]

        heat -= electricity_subst_amount
        heat -= hydrogen_subst_amount
        electricity += electricity_subst_amount
        hydrogen += hydrogen_subst_amount

        # split heat levels
        heat = heat_levels.copy_multiply_scalar(heat)

        # final demand
        demand = Demand(electricity, heat, hydrogen)

        return demand

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """ Calculate demand for this subsector distributed by nuts2 regions. """
        # get values from instance filter
        specific_consumption: SpecConsum = self._cts_if.get_specific_consumption(self._country_name)
        specific_consumption.scale(1 / 1000)  # TWh/thousand employees -> TWh/employee
        spec_scalar_for_nuts2: dict[str, float] = \
            self._cts_if.get_nuts2_spec_demand_scalar(self._country_name, self._subsector_name)
        heat_levels: Heat = self._cts_if.get_heat_levels()

        # calculate per nuts2 region
        demand_nuts2 = dict[str, Demand]()

        for region_name, spec_scalar in spec_scalar_for_nuts2.items():
            # calculate demand
            electricity = spec_scalar * specific_consumption.electricity
            heat = spec_scalar * specific_consumption.heat

            # split heat levels
            heat = heat_levels.copy_multiply_scalar(heat)

            # final demand
            demand = Demand(electricity, heat, 0.0)
            demand_nuts2[region_name] = demand

        return demand_nuts2

    def calculate_hourly_demand(self) -> dict[DemandType, [float]]:
        """ Distribute demand hourly according to load profile."""
        hourly_profile = self._cts_if.get_load_profile()
        subsector_demand = self.calculate_demand()

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [subsector_demand.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [subsector_demand.heat.copy_multiply(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [subsector_demand.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict

    def calculate_hourly_demand_distributed_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
        """ Distribute nuts2 demand hourly according to load profile."""
        nuts2_demands = self.calculate_demand_distributed_by_nuts2()
        hourly_profile = self._cts_if.get_load_profile()

        res_dict = dict[str, dict[DemandType, [float]]]()

        for region_name, region_demand in nuts2_demands.items():
            res_dict[region_name] = dict[DemandType, [float]]()
            res_dict[region_name][DemandType.ELECTRICITY] = [region_demand.electricity * hour_perc
                                                             for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
            res_dict[region_name][DemandType.HEAT] = [region_demand.heat.copy_multiply(hour_perc)
                                                      for hour_perc in hourly_profile[DemandType.HEAT]]
            res_dict[region_name][DemandType.HYDROGEN] = [region_demand.hydrogen * hour_perc
                                                          for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict
