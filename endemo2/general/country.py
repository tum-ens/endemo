from __future__ import annotations

import warnings

from endemo2.sectors import industry_sector, sector
from endemo2.utility import prediction_models as pm
from endemo2.general.country_containers import Population, NutsRegion
from endemo2.general import demand_containers as dc
from endemo2.preprocessing import preprocessor as pp


class Country:
    """
    The Country connects all sectors and data from a single country. It is a completely self-contained unit.

    :param name: Name of the country.
    :param preprocessor: The preprocessing manager containing all the preprocessing files,
    so country can fill the variables in its constructor.

    :ivar str _name: The name of the country (en).
    :ivar [str] _abbreviations: Possible abbreviations for this country.
    :ivar Population[DataManualPrediction, NutsRegion] _population: Population object, containing important data and
        the prediction of the countries' population.
    :ivar DataStepSequence _gdp: The data (and prediction) for the GDP of this country.
    :ivar dict[SectorIdentifier, Sector] _sectors: The sector objects for this country, accessible by the sector
        identifier.
    """

    def __init__(self, name: str, preprocessor: pp.Preprocessor):
        input_manager = preprocessor.input_manager

        self._name = name
        self._sectors = dict()

        # fill abbreviations
        self._abbreviations = input_manager.general_input.abbreviations[self._name]

        # TODO: gets nuts2 trees from preprocessing

        # TODO: get country population form pp

        # TODO: get gdp from pp

        # TODO: get pp industry sector


    def calculate_total_demand(self, year: int) -> dc.Demand:
        """
        Sum the demand over all sectors of the country.

        :param year: Target year for which the prediction should be calculated.
        :return: The demand for a country summed over all sectors.
        """
        total_demand = dc.Demand()

        for sector_name, obj_sector in self._sectors.items():
            total_demand.add(obj_sector.calculate_forecasted_demand(year))

        return total_demand

    def get_name(self) -> str:
        """
        Getter for the country name.

        :return: The country name (en).
        """
        return self._name

    def get_population(self) -> Population:
        """
        Getter for the population container object.

        :return: The countries' population container object.
        """
        return self._population

    def get_gdp(self) -> pm.DataStepSequence:
        """
        Getter for the countries' GDP DataStepSequence

        :return: The GDP DataStepSequence for this country.
        """
        return self._gdp

    def get_sector(self, sector_id: sector.SectorIdentifier) -> sector.Sector:
        """
        Getter for the sectors of a country. Accessed by the sectors' identifier.

        :param sector_id: Identifies Sector by enum value from SectorIdentifier.
        :return: The countries sector corresponding to the sector id.
        """
        return self._sectors[sector_id]

    def get_nuts2_root(self) -> NutsRegion:
        """ Getter for the root NutsRegion. """
        return self._population.get_nuts2_root()

