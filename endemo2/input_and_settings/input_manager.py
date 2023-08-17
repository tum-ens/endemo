import os
from pathlib import Path

import pandas as pd

from endemo2.input_and_settings import control_parameters as cp
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.input_and_settings.input_cts import CtsInput
from endemo2.input_and_settings.input_industry import IndustryInput
from endemo2.input_and_settings.input_general import GeneralInput


class InputManager:
    """
    The InputManager class connects all types of preprocessing data, that is in the form of excel/csv sheets in the
    'preprocessing' folder.

    :ivar str super_path: Path of project folder
    :ivar str input_path: Path of preprocessing files
    :ivar str output_path: Path for output files
    :ivar str general_path: Path for preprocessing files in "general" folder
    :ivar str industry_path: Path for preprocessing files in "industry" folder

    :ivar ControlParameters ctrl: Holds all information received from Set_and_Control_Parameters.xlsx
    :ivar GeneralInput general_input: Holds all information of the preprocessing files from the "preprocessing/general"
        folder.
    :ivar IndustryInput industry_input: Holds all information of the preprocessing files from the
        "preprocessing/industry" folder.
    """

    super_path = Path(os.path.abspath(''))
    input_path = super_path / 'input'
    output_path = super_path / 'output'
    general_path = input_path / 'general'
    industry_path = input_path / 'industry'
    cts_path = input_path / 'commercial_trade_and_services'

    ctrl_path = input_path / 'Set_and_Control_Parameters.xlsx'

    # Future TODO: add other sector inputs

    def __init__(self):
        # read set and control parameters
        self.ctrl: ControlParameters = InputManager.read_set_and_control_parameters()

        # read general
        self.general_input = GeneralInput(self.ctrl, InputManager.general_path)

        # read industry
        self.industry_input = IndustryInput(self.ctrl, InputManager.industry_path,
                                            self.general_input.nuts2_valid_regions,
                                            self.ctrl.general_settings.active_countries)

        # read commercial_trade_and_services
        self.cts_input = CtsInput(self.ctrl, InputManager.cts_path)

    def update_set_and_control_parameters(self):
        """ Updates Set_and_Control_Parameters.xlsx """
        self.ctrl = InputManager.read_set_and_control_parameters()

    @classmethod
    def read_set_and_control_parameters(cls) -> cp.ControlParameters:
        """ Reads Set_and_Control_Parameters.xlsx """
        ctrl_ex = pd.ExcelFile(InputManager.ctrl_path)

        # read control parameters
        general_settings = cp.GeneralSettings(pd.read_excel(ctrl_ex, sheet_name="GeneralSettings"),
                                              pd.read_excel(ctrl_ex, sheet_name="Countries"))
        industry_settings = \
            cp.IndustrySettings(
                pd.read_excel(ctrl_ex, sheet_name="IND_general"),
                pd.read_excel(ctrl_ex, sheet_name="IND_subsectors"))

        cts_settings = cp.CtsSettings(pd.read_excel(ctrl_ex, sheet_name="CTS"))

        return cp.ControlParameters(general_settings, industry_settings, cts_settings)
