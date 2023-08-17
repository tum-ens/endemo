import warnings
from pathlib import Path

import pandas as pd

from endemo2.input_and_settings.input_general import Abbreviations, GeneralInput
from endemo2 import utility as uty


def skip_years_in_df(df: pd.DataFrame, skip_years: [int]):
    for skip_year in skip_years:
        if skip_year in df.columns:
            df.drop(skip_year, axis=1, inplace=True)


def read_energy_carrier_consumption_historical(path: Path, filename: str) \
        -> dict[str, [(float, float)]]:
    """
    Reads the historical consumption data split by energy carriers from a nrg_bal file.

    :param path: The path to the folder of the file
    :param filename: The filename of the file to read.

    :return: If present, the historical quantity of energy carrier in subsector.
        Of form: {country_name -> {energy_carrier -> [(float, float)]}}
    """

    dict_sc_his = dict[str, dict[str, [(float, float)]]]()

    ex_sc_his = pd.ExcelFile(path / filename)

    for sheet_name in GeneralInput.sc_historical_sheet_names:
        df_sc = pd.read_excel(ex_sc_his, sheet_name)
        for _, row in df_sc.iterrows():
            country_name_de = row["GEO/TIME"]
            years = df_sc.columns[1:]
            data = df_sc[df_sc["GEO/TIME"] == country_name_de].iloc[0][1:]

            # convert country name to model-intern english representation
            if country_name_de in Abbreviations.dict_de_en_map.keys():
                country_name_en = Abbreviations.dict_de_en_map[country_name_de]
            else:
                continue

            if not uty.is_zero(data):
                # data exists -> fill into dictionary
                zipped = list(zip(years, data))
                his_data = uty.filter_out_nan_and_inf(zipped)
                if country_name_en not in dict_sc_his.keys():
                    dict_sc_his[country_name_en] = dict()

                dict_sc_his[country_name_en][sheet_name] = his_data

    return dict_sc_his


class FileReadingHelper:
    """
    A helper class to read products historical data. It provides some fixed transformation operations.

    :ivar str file_name: The files name, relative to the path variable.
    :ivar str sheet_name: The name of the sheet that is to be read from the file.
    :ivar [int] skip_rows: These rows(!) will be skipped when reading the dataframe. Done by numerical index.
    :ivar lambda[pd.Dataframe -> pd.Dataframe] sheet_transform: A transformation operation on the dataframe
    :ivar pd.Dataframe df: The current dataframe.
    :ivar Path path: The path to the folder, where the file is.
        It can to be set after constructing the FileReadingHelper Object.
    """

    def __init__(self, file_name: str, sheet_name: str, skip_rows: [int], sheet_transform):
        self.file_name = file_name
        self.sheet_name = sheet_name
        self.skip_rows = skip_rows
        self.sheet_transform = sheet_transform
        self.df = None
        self.path = None

    def set_path_and_read(self, path: Path) -> None:
        """
        Sets the path variable and reads the file with name self.file_name in the path folder.

        :param path: The path, where the file lies.
        """
        self.path = path
        self.df = self.sheet_transform(pd.read_excel(self.path / self.file_name, self.sheet_name,
                                                     skiprows=self.skip_rows))

    def skip_years(self, skip_years: [int]) -> None:
        """
        Filters the skip years from the current dataframe.

        :param skip_years: The list of years to skip.
        """
        if self.df is None:
            warnings.warn("Trying to skip years in products historical data without having called set_path_and_read"
                          " on the Retrieve object.")
        skip_years_in_df(self.df, skip_years)

    def get(self) -> pd.DataFrame:
        """
        Getter for the dataframe.

        :return: The current dataframe, which is filtered depending on previous function calls on this class.
        """
        if self.df is None:
            warnings.warn("Trying to retrieve products historical data without having called set_path_and_read on "
                          "the Retrieve object.")
        return self.df
