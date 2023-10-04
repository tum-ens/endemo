from endemo2.data_structures.containers import Demand
from endemo2.data_structures.enumerations import TrafficType, TransportModal, DemandType
from endemo2.model_instance.instance_filter.transport_instance_filter import TransportInstanceFilter
from endemo2.model_instance.model.sector import Sector


class Transport(Sector):
    def __init__(self, country_name: str, transport_instance_filter: TransportInstanceFilter):
        super().__init__(country_name, transport_instance_filter)

        self._country_name = country_name
        self._transport_if = transport_instance_filter

    def calculate_demand(self) -> Demand:
        """
        Calculate demand of the transport sector.

        :return: The demand summed over all _subsectors in this transport sector.
        """
        pass

    def calculate_subsector_demand(self, traffic_type: TrafficType) -> dict[TransportModal, Demand]:
        """
        Calculate demand for a traffic type in the transport sector.

        :param traffic_type: The traffic type whose demand should be calculated.
        :return: The demand of the traffic type split in modals.
        """
        result = dict[TransportModal, Demand]()

        # iterate through all modals
        for modal_id in self._transport_if.get_modals_for_traffic_type(traffic_type):
            ukm_modal = self._transport_if.get_unit_km_in_target_year(self._country_name, traffic_type, modal_id)

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

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate demand distributed by nuts2 regions.

        :return: The demand summed over all subsector in this households sector, split by nuts2 regions.
        """
        pass
