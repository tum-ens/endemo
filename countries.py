import pandas as pd


class Countries:
    _valid_country_names: set

    def __init__(self, excel: pd.DataFrame):
        assert isinstance(excel, pd.DataFrame)
        self._valid_country_names = set(excel.get('Country'))

    def __str__(self):
        return "valid countries: " + str(self._valid_country_names)

    def is_valid(self, name: str):
        return str in self._valid_country_names


