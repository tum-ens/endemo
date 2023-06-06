from input import Input
from prediction_models import PredictedTimeseries, TimeStepSequence
from sector import Sector


class Country:
    _name: str
    _abbreviations: [str]   # not implemented yet
    _population: PredictedTimeseries
    _gdp: TimeStepSequence
    _sectors: dict[str, Sector]

    def __init__(self, name: str, input_manager: Input):
        self._name = name

        # fill abbreviations
        self._abbreviations = input_manager.general_input.abbreviations[self._name]



        # TODO: fill population timeseries
        # TODO: fill gdp timeseries
        # TODO: create sectors and pass on data required to create products