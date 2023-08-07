from __future__ import annotations

from endemo2.data_structures.containers import Demand
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter \
    import ProductInstanceFilter, IndustryInstanceFilter
from endemo2.model_instance.model.industry.industry_sector import Industry
from endemo2.model_instance.model.sector import Sector
from endemo2.data_structures.enumerations import SectorIdentifier


class Country:
    """
    The Country connects all sectors_to_do and data from a single country. It is a completely self-contained unit.

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

        # fill sectors_to_do
        active_sectors = country_instance_filter.get_active_sectors()
        if SectorIdentifier.INDUSTRY in active_sectors:
            self._sectors[SectorIdentifier.INDUSTRY] = Industry(country_name, iif, pif)

    def calculate_total_demand(self) -> Demand:
        """
        Sum the demand over all sectors_to_do of the country.

        :return: The demand for a country summed over all sectors_to_do.
        """
        # TODO: implement when more sectors_to_do are available. Use the sector parent class to call the same functions
        #  in a loop.
        pass

    def get_sector(self, sector_id: SectorIdentifier) -> Sector:
        """
        Getter for the sectors_to_do of a country. Accessed by the sectors_to_do' identifier.

        :param sector_id: Identifies Sector by enum value from SectorIdentifier.
        :return: The countries_in_group sector corresponding to the sector id.
        """
        return self._sectors[sector_id]

