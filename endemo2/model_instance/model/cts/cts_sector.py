from itertools import repeat

from endemo2.data_structures.containers import Demand, Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.model_instance.instance_filter.cts_instance_filter import CtsInstanceFilter
from endemo2.model_instance.model.cts.cts_subsector import CtsSubsector
from endemo2.model_instance.model.sector import Sector


class CommercialTradeServices(Sector):
    """
    The CommercialTradeServices class represents the cts sector of one country. It holds als subsectors.

    :ivar str _country_name: Name of the country this sector is located in.
    :ivar dict[str, CtsSubsector] _subsectors: All subsectors in this cts sector.
    """

    def __init__(self, country_name: str, cts_instance_filter: CtsInstanceFilter):
        super().__init__(country_name, cts_instance_filter)

        # create _subsectors
        subsectors = cts_instance_filter.get_cts_subsector_names()
        self._subsectors = dict[str, CtsSubsector]()
        for subsector in subsectors:
            self._subsectors[subsector] = CtsSubsector(country_name, subsector, cts_instance_filter)

    def get_subsectors(self) -> dict[str, CtsSubsector]:
        """ Getter for the subsectors attribute. """
        return self._subsectors

    def calculate_demand(self) -> Demand:
        """
        Calculate demand of the cts sector.

        :return: The demand summed over all _subsectors in this cts sector.
        """
        final_demand = Demand()

        for subsector in self._subsectors.values():
            final_demand.add(subsector.calculate_demand())

        return final_demand

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """
        Calculate demand distributed by nuts2 regions.

        :return: The demand summed over all subsector in this cts sector, split by nuts2 regions.
        """
        final_demand = dict[str, Demand]()

        for subsector in self._subsectors.values():
            nuts2_demand_subsector = subsector.calculate_demand_distributed_by_nuts2()
            for region_name, demand in nuts2_demand_subsector.items():
                if region_name not in final_demand.keys():
                    final_demand[region_name] = Demand()
                final_demand[region_name].add(nuts2_demand_subsector[region_name])

        return final_demand

    def calculate_hourly_demand(self) -> dict[DemandType, [float]]:
        """
        Calculate the hourly demand for this cts sector.

        :return: The hourly demand in a list in order by demand type.
        """

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = list(repeat(0.0, 8760))
        res_dict[DemandType.HEAT] = list(repeat(Heat(), 8760))
        res_dict[DemandType.HYDROGEN] = list(repeat(0.0, 8760))

        for subsector_name, subsector in self._subsectors.items():
            subsector_hourly_demand = subsector.calculate_hourly_demand()
            res_dict[DemandType.ELECTRICITY] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.ELECTRICITY], subsector_hourly_demand[DemandType.ELECTRICITY]))]
            res_dict[DemandType.HEAT] = \
                [res_value.copy_add(new_value) for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HEAT], subsector_hourly_demand[DemandType.HEAT]))]
            res_dict[DemandType.HYDROGEN] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HYDROGEN], subsector_hourly_demand[DemandType.HYDROGEN]))]
        return res_dict

    def calculate_hourly_demand_distributed_by_nuts2(self) -> dict[str, dict[DemandType, [float]]]:
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

            for subsector_name, subsector_obj in self._subsectors.items():
                subsector_hourly_demand = subsector_obj.calculate_hourly_demand_distributed_by_nuts2()

                res_dict[region_name][DemandType.ELECTRICITY] = \
                    [res_value + new_value for (res_value, new_value)
                     in zip(res_dict[region_name][DemandType.ELECTRICITY],
                            subsector_hourly_demand[region_name][DemandType.ELECTRICITY])]
                res_dict[region_name][DemandType.HEAT] = \
                    [res_value.copy_add(new_value) for (res_value, new_value)
                     in zip(res_dict[region_name][DemandType.HEAT],
                            subsector_hourly_demand[region_name][DemandType.HEAT])]
                res_dict[region_name][DemandType.HYDROGEN] = \
                    [res_value + new_value for (res_value, new_value)
                     in zip(res_dict[region_name][DemandType.HYDROGEN],
                            subsector_hourly_demand[region_name][DemandType.HYDROGEN])]
        return res_dict
