from __future__ import annotations

from endemo2.general.demand_containers import Demand
from endemo2.model_instance.instance_filter import CountryInstanceFilter, ProductInstanceFilter, IndustryInstanceFilter
from endemo2.sectors.industry_sector import Industry
from endemo2.sectors.sector import SectorIdentifier, Sector


class Country:
    """
    The Country connects all sectors and data from a single country. It is a completely self-contained unit.

    :param str country_name: Name of the country.
    :param CountryInstanceFilter country_instance_filter: The instance filter for the country.
    :param IndustryInstanceFilter iif: The instance filter for the industry. Is passed on to the industry object.
    :param ProductInstanceFilter pif: The instance filter for the products. Is passed on to the industry object.

    :ivar str _country_name: The name of the country (en).
    :ivar dict[SectorIdentifier, Sector] _sectors: The sector objects for this country, accessible by the sector
        identifier.
    """

    def __init__(self, country_name: str,
                 country_instance_filter: CountryInstanceFilter,
                 iif: IndustryInstanceFilter, pif: ProductInstanceFilter):

        self._country_name = country_name
        self._sectors = dict[SectorIdentifier, Sector]()

        # fill sectors
        active_sectors = country_instance_filter.get_active_sectors()
        if SectorIdentifier.INDUSTRY in active_sectors:
            self._sectors[SectorIdentifier.INDUSTRY] = Industry(country_name, iif, pif)

    def calculate_total_demand(self) -> Demand:
        """
        Sum the demand over all sectors of the country.

        :return: The demand for a country summed over all sectors.
        """
        # TODO: implement when more sectors are available. Use the sector parent class to call the same functions in a
        #  loop.
        pass

    def get_sector(self, sector_id: SectorIdentifier) -> Sector:
        """
        Getter for the sectors of a country. Accessed by the sectors' identifier.

        :param sector_id: Identifies Sector by enum value from SectorIdentifier.
        :return: The countries sector corresponding to the sector id.
        """
        return self._sectors[sector_id]

