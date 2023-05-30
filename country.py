from prediction_models import PredictedTimeseries, TimeStepSequence
from sector import Sector


class Country:
    _name: str
    _abbreviations: [str]
    _population: PredictedTimeseries
    _gdp: TimeStepSequence
    _sectors: dict[str, Sector]

    def __init__(self, name: str, abbreviations: [str]):
        self._name = name
        self._abbreviations = abbreviations