from endemo2.data_structures.containers import Demand
from endemo2.data_structures.enumerations import TrafficType, TransportModal, DemandType
from endemo2.model_instance.instance_filter.transport_instance_filter import TransportInstanceFilter
from endemo2.model_instance.model.sector import Sector
import endemo2.utility as uty


class Transport(Sector):
    def __init__(self, country_name: str, transport_instance_filter: TransportInstanceFilter):
        super().__init__(country_name, transport_instance_filter)

        self._country_name = country_name
        self._transport_if = transport_instance_filter

    def calculate_demand(self) -> Demand:
        """
        Calculate demand of the transport sector.

        :return: The demand summed over all subsectors demand in this transport sector.
        """
        demand = Demand()

        demand.add(self.calculate_demand_for_traffic_type(TrafficType.PERSON))
        demand.add(self.calculate_demand_for_traffic_type(TrafficType.FREIGHT))

        return demand

    def calculate_demand_for_traffic_type(self, traffic_type: TrafficType) -> Demand:
        """
        Calculate demand of a traffic type in the transport sector.

        :return: The demand summed over all subsectors for a traffic type in this transport sector.
        """
        demand = Demand()

        dict_subsector_demand = self.calculate_subsector_demand(traffic_type)
        for _, subsector_demand in dict_subsector_demand.items():
            demand.add(subsector_demand)

        return demand

    def calculate_subsector_demand(self, traffic_type: TrafficType) -> dict[TransportModal, Demand]:
        """
        Calculate demand for a traffic type in the transport sector.

        :param traffic_type: The traffic type whose demand should be calculated.
        :return: The demand of the traffic type split in modals.
        """
        result = dict[TransportModal, Demand]()

        # iterate through all modals
        for modal_id in self._transport_if.get_modals_for_traffic_type(traffic_type):
            ukm_modal = \
                self._transport_if.get_unit_km_in_target_year_country(self._country_name, traffic_type, modal_id)

            elec_perc = \
                self._transport_if.get_perc_modal_to_demand_type_in_target_year(self._country_name, traffic_type,
                                                                                modal_id, DemandType.ELECTRICITY)
            hydrogen_perc = \
                self._transport_if.get_perc_modal_to_demand_type_in_target_year(self._country_name, traffic_type,
                                                                                modal_id, DemandType.HYDROGEN)
            fuel_perc = 1.0 - elec_perc - hydrogen_perc

            demand_type_perc = Demand(electricity=elec_perc, hydrogen=hydrogen_perc, fuel=fuel_perc)
            ukm_per_demand_type = demand_type_perc.copy_scale(ukm_modal)

            energy_consumption: Demand = self._transport_if.get_energy_consumption_of_modal(traffic_type, modal_id)

            result[modal_id] = ukm_per_demand_type.copy_multiply(energy_consumption)

        return result

    def calculate_subsector_demand_distributed_by_nuts2(self, traffic_type: TrafficType) \
            -> dict[str, dict[TransportModal, Demand]]:
        """
        Calculate demand for a traffic type in the transport sector distributed by nuts2 regions

        :param traffic_type: The traffic type whose demand should be calculated.
        :return: The demand of the traffic type split in modals distributed by nuts2 regions.
        """
        dict_demand = self.calculate_subsector_demand(traffic_type)

        nuts2_distribution_scalars = \
            self._transport_if.get_nuts2_distribution_scalars(self._country_name, traffic_type)

        distributed_demand = dict[str, dict[TransportModal, Demand]]()

        for (nuts2_region_name, distribution_scalar) in nuts2_distribution_scalars.items():
            scaled_demand = uty.multiply_demand_dictionary_with_scalar(dict_demand, distribution_scalar)
            distributed_demand[nuts2_region_name] = scaled_demand

        return distributed_demand


    def calculate_demand_for_traffic_type_distributed_by_nuts2(self, traffic_type) -> dict[str, Demand]:
        """
        Calculate demand of transport sector distributed by nuts2 regions for a traffic type.

        :return: The demand of a traffic type summed over all subsector in this transport sector,
            split by nuts2 regions.
        """
        demand = self.calculate_demand_for_traffic_type(traffic_type)

        nuts2_distribution_scalars = \
            self._transport_if.get_nuts2_distribution_scalars(self._country_name, traffic_type)

        distributed_demand = uty.multiply_dictionary_with_demand(nuts2_distribution_scalars, demand)

        return distributed_demand

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate demand of transport sector distributed by nuts2 regions.

        :return: The demand summed over all subsector in this transport sector, split by nuts2 regions.
        """

        person_demand_split_by_nuts2 = self.calculate_demand_for_traffic_type_distributed_by_nuts2(TrafficType.PERSON)
        freight_demand_split_by_nuts2 = self.calculate_demand_for_traffic_type_distributed_by_nuts2(TrafficType.FREIGHT)

        demand = dict[str, Demand]()

        for nuts2_region, person_demand in person_demand_split_by_nuts2.items():
            freight_demand = freight_demand_split_by_nuts2[nuts2_region]
            demand[nuts2_region] = Demand()
            demand[nuts2_region].add(person_demand)
            demand[nuts2_region].add(freight_demand)

        return demand
