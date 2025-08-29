from endemo2.input_and_settings.input_manager import InputManager
from endemo2.input_and_settings.input_loader import  initialize_hierarchy_input_from_settings_data
from endemo2.model.model_forecast import do_forecast
from endemo2.model.model_useful_energy import calculate_useful_energy
from endemo2.output.output_to_excel import ExcelWriter

class Endemo:
    """
    This is the whole program. From here we control what the model does on the highest level.

    :ivar Input input_manager: holds all the processed input_and_settings from the Excel sheets for the current run of
        the program.
    :ivar dict[str, Country] countries_in_group: holds all the country objects, accessible by the countries_in_group english name.
    :ivar Preprocessor preprocessor: holds an additional layer of preprocessed data, building upon the input_manager.
    """

    def __init__(self):
        self.input_manager = None
        self.data = None
        self.output_to_excel = None
    def execute_with_preprocessing(self):
        """
        Executes the whole program from start to end.
        """
        # Initialize Input
        print("Reading settings...")
        self.input_manager = InputManager()
        print("Settings successfully read.")

        # Read input data for active_regions in active sectors
        print("Reading input data for active sectors...")
        self.data = initialize_hierarchy_input_from_settings_data(self.input_manager)
        print("Input data successfully read.")

        # #Calculate the forecast
        print("Do Predictions...")
        do_forecast(self.data)
        print("Predictions successfully done")

        # Calculate useful energy
        print("Calculate useful energy ...")
        calculate_useful_energy(self.data)
        print("Calculate useful energy successfully done...")

        # Calculate final energy
        print("Calculate Final energy ...")
        self.data.calc_fe()
        print("Calculate Final energy successfully done...")

        print("Calculate Timeseries ...")
        self.data.calc_timeseries()
        print("Calculate Timeseries successfully done...")

        # generate output files
        print("Export output to excel ...")
        self.output_to_excel = ExcelWriter(self.data)
        print("Exporting successfully done...")