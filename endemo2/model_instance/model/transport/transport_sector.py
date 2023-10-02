from endemo2.data_structures.containers import Demand
from endemo2.data_structures.enumerations import TrafficType, TransportModal
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
            # todo: calculate demand from ukm per modal in traffic type
            demand: Demand = None
            result[modal_id] = demand

        return result

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate demand distributed by nuts2 regions.

        :return: The demand summed over all subsector in this households sector, split by nuts2 regions.
        """
        pass
