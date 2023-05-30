import warnings
from functools import reduce

import pandas as pd


class InvalidCountryName(UserWarning):
    pass


class Country:
    # static part of class start----------------------------------------
    _valid_country_names = set()

    @classmethod
    def __init__(cls, excel: pd.DataFrame):
        Country._valid_country_names = set(excel.get('Country'))

    @classmethod
    def __str__(cls):
        return "valid countries: " + str(Country._valid_country_names)

    @classmethod
    def _is_country_valid(cls, name: str):
        return name in Country._valid_country_names

    @classmethod
    def _is_country_list_valid(cls, names: [str]):
        return all(map(Country._is_country_valid, names))

    @classmethod
    def check_for_wrong_countries_in_file(cls, file_name: str, countries: [str]):
        countries_valid = Country._is_country_list_valid(countries)

        if not countries_valid:
            invalid_countries = []

            for c in countries:
                if not Country._is_country_valid(c):
                    invalid_countries.append(c)

            warnings.warn("unidentified countries found in file " + file_name + "\n\tUnidentified Countries: " + str(invalid_countries), InvalidCountryName)
            return False

        return True

    # static part of class end------------------------------------------
    # instantiated part of class start----------------------------------


