import pandas as pd


class ControlParameters:

    _sectors_active_values = dict()
    _parameter_values = dict()

    def __init__(self, excel):
        assert isinstance(excel, pd.DataFrame)

        rows_it = pd.DataFrame(excel).itertuples()

        for row in rows_it:
            if row.Parameter.startswith('Sector: '):
                self._sectors_active_values[row.Parameter.removeprefix('Sector: ')] = row.Value
            else:
                self._parameter_values[row.Parameter] = row.Value

    def __str__(self):
        return ("sectors_active_values: " + str(self._sectors_active_values) + "\n" +
                "parameter_values: " + str(self._parameter_values))

    def get_active_sectors(self):
        # returns a list of sectors activated for calculation
        return [sector for (sector, isActive) in self._sectors_active_values.items() if isActive is 1 ]

    def get_parameter(self, name):
        # return the parameter value by parameter name with meaningful error message
        try:
            return self._parameter_values[name]
        except KeyError:
            KeyError("Parameter name not found. Does the parameter access string in the code match a parameter in the Set_and_Control_Parameters.xlsx input table?")
