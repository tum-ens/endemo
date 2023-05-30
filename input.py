import os
from pathlib import Path

import pandas as pd

from control_parameters import ControlParameters, GeneralSettings, CountrySettings, IndustrySettings


class Input:

    super_path = Path(os.path.abspath(''))
    input_path = super_path / 'input'
    general_path = input_path / 'general'
    industry_path = input_path / 'industry'

    ctrl: ControlParameters

    def __init__(self):
        # read control parameters
        general_settings = GeneralSettings(pd.read_excel(self.input_path / 'Set_and_Control_Parameters.xlsx'))
        country_settings = \
            CountrySettings(pd.read_excel(self.input_path / 'Set_and_Control_Parameters.xlsx', sheet_name="Countries"))
        industry_settings = \
            IndustrySettings(
                pd.read_excel(self.input_path / 'Set_and_Control_Parameters.xlsx', sheet_name="IND_general"),
                pd.read_excel(self.input_path / 'Set_and_Control_Parameters.xlsx', sheet_name="IND_subsectors"))

        ctrl = ControlParameters(general_settings, country_settings, industry_settings)

        



