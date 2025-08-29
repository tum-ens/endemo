import os
from pathlib import Path

import pandas as pd
from endemo2.input_and_settings import control_parameters as cp
from endemo2.input_and_settings.control_parameters import ControlParameters

class InputManager:
    """
    The InputManager class connects all types of run data, that is in the form of Excel sheets in the
    'input' folder.
    """
    super_path = Path(os.path.abspath(''))
    input_path = super_path / 'input'
    output_path = super_path / 'output'
    ctrl_file = input_path / 'Model_Set_and_Control.xlsx'
    timeseries_file = input_path / 'timeseries.xlsx'

    def __init__(self):
        # Read set and control parameters
        self.ctrl: ControlParameters = InputManager.read_set_and_control_parameters()
        self.general_settings = self.ctrl.gen_settings
        self.sector_paths = self.get_data_paths()

    def get_data_paths(self):
        """
        Generate input paths for active sectors.

        Args:
        Returns:
            dict: A dictionary with sector names as keys and their paths as values.
        """
        # Store paths in a dictionary
        sector_paths = {
                "hist_path": self.input_path / f"Data_Historical.xlsx",
                "user_set_path": self.input_path / f"Data_User_set.xlsx"
            }

        return sector_paths

    @classmethod
    def read_set_and_control_parameters(cls) -> cp.ControlParameters:
        """ Reads Set_and_Control_Parameters.xlsx """
        try:
            # Load the control Excel file
            ctrl_ex = pd.ExcelFile(InputManager.ctrl_file)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Control file not found: {InputManager.ctrl_file}. Error: {e}")
        except Exception as e:
            raise Exception(f"Error loading control file {InputManager.ctrl_file}: {e}")
        # read control parameters
        gen_settings = cp.GeneralSettings(ctrl_ex)
        return cp.ControlParameters(gen_settings)



