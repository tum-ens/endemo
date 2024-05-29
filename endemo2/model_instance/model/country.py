from __future__ import annotations

from endemo2.data_structures.containers import Demand
from endemo2.model_instance.instance_filter.cts_instance_filter import CtsInstanceFilter
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter \
    import ProductInstanceFilter, IndustryInstanceFilter
from endemo2.model_instance.instance_filter.transport_instance_filter import TransportInstanceFilter
from endemo2.model_instance.model.cts.cts_sector import CommercialTradeServices
from endemo2.model_instance.model.households.household_sector import Households
from endemo2.model_instance.model.industry.industry_sector import Industry
from endemo2.model_instance.model.sector import Sector
from endemo2.data_structures.enumerations import SectorIdentifier
from endemo2.model_instance.model.transport.transport_sector import Transport


class Country:
    """
    The Country connects all transport and data from a single country. It is a completely self-contained unit.

    :param str country_name: Name of the country.
    :param CountryInstanceFilter country_instance_filter: The instance filter for the country.
    :param IndustryInstanceFilter ind_if: The instance filter for the industry. Is passed on to the industry object.
    :param ProductInstanceFilter prod_if: The instance filter for the products. Is passed on to the industry object.

    :ivar str _country_name: The name of the country (en).
    :ivar dict[SectorIdentifier, Sector] _sectors: The sector objects for this country, accessible by the sector
        identifier.
    """

    def __init__(self, country_name: str,
                 country_instance_filter: CountryInstanceFilter,
                 ind_if: IndustryInstanceFilter, prod_if: ProductInstanceFilter, cts_if: CtsInstanceFilter,
                 hh_if: HouseholdsInstanceFilter, tra_if: TransportInstanceFilter):

        self._country_name = country_name
        self._sectors = dict[SectorIdentifier, Sector]()

        # fill transport
        active_sectors = country_instance_filter.get_active_sectors()
        if SectorIdentifier.INDUSTRY in active_sectors:
            self._sectors[SectorIdentifier.INDUSTRY] = Industry(country_name, ind_if, prod_if)

        if SectorIdentifier.COMMERCIAL_TRADE_SERVICES in active_sectors:
            self._sectors[SectorIdentifier.COMMERCIAL_TRADE_SERVICES] = CommercialTradeServices(country_name, cts_if)

        if SectorIdentifier.HOUSEHOLDS in active_sectors:
            self._sectors[SectorIdentifier.HOUSEHOLDS] = Households(country_name, hh_if)

        if SectorIdentifier.TRANSPORT in active_sectors:
            self._sectors[SectorIdentifier.TRANSPORT] = Transport(country_name, tra_if)

    def calculate_total_demand(self) -> Demand:
        """
        Sum the demand over all transport of the country.

        :return: The demand for a country summed over all transport.
        """
        # TODO: implement when more sectors available. Use the sector parent class to call the same functions
        #  in a loop.
        pass

    def get_sector(self, sector_id: SectorIdentifier) -> Sector:
        """
        Getter for the transport of a country. Accessed by the transport' identifier.

        :param sector_id: Identifies Sector by enum value from SectorIdentifier.
        :return: The countries_in_group sector corresponding to the sector id.
        """
        return self._sectors[sector_id]

