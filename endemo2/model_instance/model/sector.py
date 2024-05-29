import warnings

from endemo2.data_structures.containers import Demand
from endemo2.model_instance.instance_filter.general_instance_filter import InstanceFilter


class Sector:
    """
    The parent class for all sectors.
    Contains what different sectors have in common.

    :ivar str _country_name: The name of the country this sector belongs to.
    :ivar InstanceFilter _instance_filter: The instance filter of the sector.
    """
    def __init__(self, country_name: str, instance_filter):
        self._country_name = country_name
        self._instance_filter = instance_filter

    def calculate_demand(self) -> Demand:
        """
        Calculate demand of the transport sector.

        :return: The demand summed over all _subsectors in this transport sector.
        """
        warnings.warn("Somehow the function of the sector parent was called. Make sure to call this function on a child "
                      "class, where it is implemented.")
        pass

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate demand distributed by nuts2 regions.

        :return: The demand summed over all subsector in this households sector, split by nuts2 regions.
        """
        warnings.warn(
            "Somehow the function of the sector parent was called. Make sure to call this function on a child "
            "class, where it is implemented.")
        pass
