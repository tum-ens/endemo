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

        # create population timeseries
        self._population = \
            PredictedTimeseries(historical_data=input_manager.general_input.population[self._name].historical,
                                prediction_data=input_manager.general_input.population[self._name].prognosis)

        # create gdp timeseries
        self._gdp = TimeStepSequence(historical_data=input_manager.general_input.gdp[self._name].historical,
                                     progression_data= input_manager.general_input.gdp[self._name].prognosis)

        print(self._name)
        print("prog 2045: " + str(self._gdp.get_manual_prog(2045)))

        # TODO: create sectors and pass on data required to create products