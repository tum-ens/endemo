from itertools import repeat

from endemo2.data_structures.containers import Demand, Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.input_and_settings.input_households import HouseholdsSubsectorId
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2.model_instance.model.households.hh_subsectors import HouseholdsSubsector, HotWater, SpaceHeating
from endemo2.model_instance.model.sector import Sector
from endemo2 import utility as uty


class Households(Sector):
    """
    The CommercialTradeServices class represents the cts sector of one country. It holds als subsectors.

    :ivar str _country_name: Name of the country this sector is located in.
    :ivar HouseholdsInstanceFilter _hh_if: The instance filter for the households sector.
    :ivar dict[str, HouseholdsSubsector] _subsectors: All subsectors in this cts sector.
    """

    def __init__(self, country_name: str, households_instance_filter: HouseholdsInstanceFilter):
        super().__init__(country_name, households_instance_filter)

        # create subsectors
        subsector_ids = households_instance_filter.get_subsectors()

        self._subsectors = dict[HouseholdsSubsectorId, HouseholdsSubsector]()
        for subsector_id in subsector_ids:
            if subsector_id in [HouseholdsSubsectorId.SPACE_COOLING,
                                HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES,
                                HouseholdsSubsectorId.COOKING]:
                self._subsectors[subsector_id] = \
                    HouseholdsSubsector(country_name, subsector_id, households_instance_filter)
            if subsector_id == HouseholdsSubsectorId.WATER_HEATING:
                self._subsectors[subsector_id] = HotWater(country_name, subsector_id, households_instance_filter)
            if subsector_id == HouseholdsSubsectorId.SPACE_HEATING:
                self._subsectors[subsector_id] = SpaceHeating(country_name, subsector_id, households_instance_filter)

    def calculate_demand(self) -> Demand:
        """
        Calculate demand of the households sector.

        :return: The demand summed over all _subsectors in this households sector.
        """
        demand = Demand()

        # sum over all subsectors
        for subsector_id, subsector_obj in self._subsectors.items():
            demand.add(subsector_obj.calculate_demand())

        return demand

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate demand distributed by nuts2 regions.

        :return: The demand summed over all subsector in this households sector, split by nuts2 regions.
        """
        demand = self.calculate_demand()
        nuts2_distribution = self._instance_filter.get_nuts2_distribution(self._country_name)
        return uty.multiply_dictionary_with_demand(nuts2_distribution, demand)

    def calculate_hourly_demand_efh(self) -> dict[DemandType, [float]]:
        """
        Calculate the hourly demand for the single person households in this sector.

        :return: The hourly demand in a list in order by demand type.
        """
        efh_share = self._instance_filter.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self._instance_filter.get_load_profile_efh()
        demand_efh = self.calculate_demand().copy_scale(efh_share)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [demand_efh.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [demand_efh.heat.copy_multiply(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [demand_efh.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict

    def calculate_hourly_demand_mfh(self) -> dict[DemandType, [float]]:
        """
        Calculate the hourly demand for the multiple person households in this sector.

        :return: The hourly demand in a list in order by demand type.
        """
        mfh_share = 1 - self._instance_filter.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self._instance_filter.get_load_profile_mfh()
        demand_mfh = self.calculate_demand().copy_scale(mfh_share)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [demand_mfh.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [demand_mfh.heat.copy_multiply(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [demand_mfh.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict

    def calculate_hourly_demand_efh_distributed_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
        """
        Calculate the hourly demand for the single person households in this sector.

        :return: The hourly demand in a list in order by demand type.
        """
        demand_efh = self.calculate_hourly_demand_efh()

        nuts2_distribution_scalars = self._instance_filter.get_nuts2_distribution(self._country_name)

        res_dict = dict[str, dict[DemandType, [float]]]()

        for region_name, distribution_scalar in nuts2_distribution_scalars.items():
            res_dict[region_name] = dict[DemandType, [float]]()

            res_dict[region_name][DemandType.ELECTRICITY] = [hourly_demand * distribution_scalar
                                                             for hourly_demand in demand_efh[DemandType.ELECTRICITY]]
            res_dict[region_name][DemandType.HEAT] = [hourly_demand.copy_multiply_scalar(distribution_scalar)
                                                      for hourly_demand in demand_efh[DemandType.HEAT]]
            res_dict[region_name][DemandType.HYDROGEN] = [hourly_demand * distribution_scalar
                                                          for hourly_demand in demand_efh[DemandType.HYDROGEN]]

        return res_dict

    def calculate_hourly_demand_mfh_distributed_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
        """
        Calculate the hourly demand for the single person households in this sector.

        :return: The hourly demand in a list in order by demand type.
        """
        demand_mfh = self.calculate_hourly_demand_mfh()

        nuts2_distribution_scalars = self._instance_filter.get_nuts2_distribution(self._country_name)

        res_dict = dict[str, dict[DemandType, [float]]]()

        for region_name, distribution_scalar in nuts2_distribution_scalars.items():
            res_dict[region_name] = dict[DemandType, [float]]()

            res_dict[region_name][DemandType.ELECTRICITY] = [hourly_demand * distribution_scalar
                                                             for hourly_demand in demand_mfh[DemandType.ELECTRICITY]]
            res_dict[region_name][DemandType.HEAT] = [hourly_demand.copy_multiply_scalar(distribution_scalar)
                                                      for hourly_demand in demand_mfh[DemandType.HEAT]]
            res_dict[region_name][DemandType.HYDROGEN] = [hourly_demand * distribution_scalar
                                                          for hourly_demand in demand_mfh[DemandType.HYDROGEN]]

        return res_dict


