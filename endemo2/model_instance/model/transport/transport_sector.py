from endemo2.data_structures.containers import Demand
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

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate demand distributed by nuts2 regions.

        :return: The demand summed over all subsector in this households sector, split by nuts2 regions.
        """
        pass
