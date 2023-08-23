from endemo2.data_structures.enumerations import SectorIdentifier
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.input_and_settings.input_manager import InputManager
from endemo2.model_instance.instance_filter.cts_instance_filter import CtsInstanceFilter
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter \
    import IndustryInstanceFilter, ProductInstanceFilter
from endemo2.input_and_settings import input_general
from endemo2.model_instance.instance_filter.transport_instance_filter import TransportInstanceFilter
from endemo2.model_instance.model import country
from endemo2.output.output_instance import generate_instance_output
from endemo2.output.output_preprocessing import generate_preprocessing_output
from endemo2.preprocessing.preprocessor import Preprocessor


class Endemo:
    """
    This is the whole program. From here we control what the model does on the highest level.

    :ivar Input input_manager: holds all the processed input_and_settings from the Excel sheets for the current run of
        the program.
    :ivar dict[str, Country] countries_in_group: holds all the country objects, accessible by the countries_in_group english name.
    :ivar Preprocessor preprocessor: holds an additional layer of preprocessed data, building upon the input_manager.
    """

    def __init__(self, ):
        self.input_manager = None
        self.countries = None
        self.preprocessor = None
        self.country_instance_filter = None
        self.industry_instance_filter = None
        self.product_instance_filter = None
        self.cts_instance_filter = None
        self.hh_instance_filter = None
        self.transport_instance_filter = None

    def execute_with_preprocessing(self):
        """
        Executes the whole program from start to end.
        """
        # read input_and_settings
        print("Reading Input ...")
        self.input_manager = InputManager()
        print("Input was successfully read.")

        # do preprocessing
        print("Preprocessing Data ...")
        self.preprocessor = Preprocessor(self.input_manager)
        print("Preprocessing was successfully completed.")

        # create model instance
        self.create_instance()

        # generate output files
        self.write_all_output()

    def execute_without_preprocessing(self):
        """
        Executes only the model with the updated settings.
        Builds upon, but does not recalculate preprocessing.
        """
        self.update_settings()
        self.create_instance()
        self.write_model_output()

    def update_settings(self):
        """ Rereads the instance settings. """
        # read input_and_settings, TODO: separate the instance settings from pre-preprocessing settings
        print("Updating settings for new scenario...")
        self.input_manager.update_set_and_control_parameters()
        print("Settings were successfully updated.")

    def create_instance(self):
        """ Creates an instance of the model. """

        # create instance filters
        print("Creating instance filters...")
        prepro = self.preprocessor

        ctrl: ControlParameters = self.input_manager.ctrl
        general_input = self.input_manager.general_input

        self.country_instance_filter = CountryInstanceFilter(ctrl, general_input, prepro)

        # create instances for active sectors
        active_subsectors = ctrl.general_settings.get_active_sectors()
        if SectorIdentifier.INDUSTRY in active_subsectors:
            industry_input = self.input_manager.industry_input
            self.industry_instance_filter = \
                IndustryInstanceFilter(ctrl, industry_input, prepro, self.country_instance_filter)
            self.product_instance_filter = \
                ProductInstanceFilter(ctrl, prepro, industry_input, general_input, self.country_instance_filter)

        if SectorIdentifier.COMMERCIAL_TRADE_SERVICES in active_subsectors:
            cts_input = self.input_manager.cts_input
            self.cts_instance_filter = CtsInstanceFilter(ctrl, general_input, cts_input, prepro,
                                                         self.country_instance_filter)

        if SectorIdentifier.HOUSEHOLDS in active_subsectors:
            hh_input = self.input_manager.hh_input
            self.hh_instance_filter = HouseholdsInstanceFilter(ctrl, general_input, hh_input, prepro,
                                                               self.country_instance_filter)

        if SectorIdentifier.TRANSPORT in active_subsectors:
            transport_input = self.input_manager.transport_input
            self.transport_instance_filter = TransportInstanceFilter(ctrl, transport_input, prepro,
                                                                     self.country_instance_filter,
                                                                     self.industry_instance_filter)

        print("Instance filters were successfully created.")

        print("Initiating model scenario...")
        # create countries_in_group
        self.countries = dict[str, country.Country]()
        for country_name in self.input_manager.ctrl.general_settings.active_countries:
            self.countries[country_name] = country.Country(country_name, self.country_instance_filter,
                                                           self.industry_instance_filter, self.product_instance_filter,
                                                           self.cts_instance_filter, self.hh_instance_filter)

        print("Model scenario was successfully initiated.")

    def write_all_output(self):
        """ Writes the whole output to the output folder. """
        self.write_preprocessing_output()
        self.write_model_output()

    def write_preprocessing_output(self):
        """ Writes all the output that comes from preprocessing. """
        print("Writing preprocessing output...")
        generate_preprocessing_output(self.input_manager, self.preprocessor)
        print("Preprocessing output was successfully written.")

    def write_model_output(self):
        """ Writes all the output that comes from the model instance. """
        print("Writing scenario output...")
        generate_instance_output(self.input_manager, self.countries,
                                 self.country_instance_filter, self.product_instance_filter,
                                 self.cts_instance_filter, self.hh_instance_filter)
        print("Model output was successfully written.")
