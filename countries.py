import warnings
from functools import reduce

import pandas as pd


class InvalidCountryName(UserWarning):
    pass


class Countries:
    _valid_country_names: set

    def __init__(self, excel: pd.DataFrame):
        assert isinstance(excel, pd.DataFrame)
        self._valid_country_names = set(excel.get('Country'))

    def __str__(self):
        return "valid countries: " + str(self._valid_country_names)

    def _is_country_valid(self, name: str):
        return name in self._valid_country_names

    def _is_country_list_valid(self, names: [str]):
        return all(map(self._is_country_valid, names))

    def check_for_wrong_countries_in_file(self, file_name: str, countries: [str]):
        countries_valid = self._is_country_list_valid(countries)

        if not countries_valid:
            invalid_countries = []

            for c in countries:
                if not self._is_country_valid(c):
                    invalid_countries.append(c)

            warnings.warn("unidentified countries found in file " + file_name + "\n\tUnidentified Countries: " + str(invalid_countries), InvalidCountryName)
            return False

        return True



