from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter \
    import IndustryInstanceFilter, ProductInstanceFilter
from endemo2.input_and_settings import input
from endemo2.model_instance.model import country
from endemo2.output.instance_output import generate_instance_output
from endemo2.output.preprocessing_output import generate_preprocessing_output
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

    def execute_with_preprocessing(self):
        """
        Executes the whole program from start to end.
        """
        # read input_and_settings
        self.input_manager = input.Input()
        print("Input was successfully read.")

        # do preprocessing
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
        self.input_manager = input.Input()
        print("Settings were successfully updated.")

    def create_instance(self):
        """ Creates an instance of the model. """

        # create instance filters
        prepro = self.preprocessor
        ctrl = self.input_manager.ctrl
        general_input = self.input_manager.general_input
        industry_input = self.input_manager.industry_input
        self.country_instance_filter = CountryInstanceFilter(ctrl, general_input, prepro)
        self.industry_instance_filter = \
            IndustryInstanceFilter(ctrl, industry_input, prepro, self.country_instance_filter)
        self.product_instance_filter = \
            ProductInstanceFilter(ctrl, prepro, industry_input, general_input, self.country_instance_filter)

        print("Instance filters were successfully created.")

        # create countries_in_group
        self.countries = dict[str, country.Country]()
        for country_name in self.input_manager.ctrl.general_settings.active_countries:
            self.countries[country_name] = country.Country(country_name, self.country_instance_filter,
                                                           self.industry_instance_filter, self.product_instance_filter)

        print("Model was successfully initiated.")

    def write_all_output(self):
        """ Writes the whole output to the output folder. """
        self.write_preprocessing_output()
        self.write_model_output()

    def write_preprocessing_output(self):
        """ Writes all the output that comes from preprocessing. """
        generate_preprocessing_output(self.input_manager, self.preprocessor)
        print("Preprocessing output was successfully written.")

    def write_model_output(self):
        """ Writes all the output that comes from the model instance. """
        generate_instance_output(self.input_manager, self.countries,
                                 self.country_instance_filter, self.product_instance_filter)
        print("Model output was successfully written.")
