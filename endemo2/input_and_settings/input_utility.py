import warnings
from pathlib import Path

import pandas as pd


def skip_years_in_df(df: pd.DataFrame, skip_years: [int]):
    for skip_year in skip_years:
        if skip_year in df.columns:
            df.drop(skip_year, axis=1, inplace=True)


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
