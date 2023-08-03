from endemo2.model_instance.instance_filter import CountryInstanceFilter, IndustryInstanceFilter, ProductInstanceFilter
from endemo2.input import input
from endemo2.general import country
from endemo2.output import preprocessing_output
from endemo2.preprocessing.preprocessor import Preprocessor


class Endemo:
    """
    This is the instance of the model. From here we control what the model does on the highest level.

    :ivar Input input_manager: holds all the processed input from the Excel sheets for the current run of the program.
    :ivar dict[str, Country] countries: holds all the country objects, accessible by the countries english name.
    :ivar Preprocessor preprocessor: holds an additional layer of preprocessed data, building upon the input_manager.
    """

    def __init__(self):
        self.input_manager = None
        self.countries = dict()
        self.preprocessor = None

    def execute_with_preprocessing(self):
        """
        Executes the whole program from start to end.
        """
        # read input
        self.input_manager = input.Input()
        print("Input was successfully read.")

        # do preprocessing
        self.preprocessor = Preprocessor(self.input_manager)
        print("Preprocessing was successfully completed.")

        # create model instance
        self.create_instance()

        # generate output files
        self.write_output()

    def execute_without_preprocessing(self):
        """
        Executes only the model with the updated settings.
        Builds upon, but does not recalculate preprocessing.
        """
        self.update_settings()
        self.create_instance()
        self.write_output()

    def update_settings(self):
        """ Rereads the instance settings. """
        # read input, TODO: separate the instance settings from pre-preprocessing settings
        self.input_manager = input.Input()
        print("Settings were successfully updated.")

    def create_instance(self):
        # create instance filters
        prepro = self.preprocessor
        ctrl = self.input_manager.ctrl
        general_input = self.input_manager.general_input
        industry_input = self.input_manager.industry_input
        country_instance_filter = CountryInstanceFilter(ctrl, general_input, prepro)
        industry_instance_filter = IndustryInstanceFilter(ctrl, industry_input, prepro, country_instance_filter)
        product_instance_filter = ProductInstanceFilter(ctrl, prepro)

        print("Instance filters were successfully created.")

        # create countries
        for country_name in self.input_manager.ctrl.general_settings.active_countries:
            self.countries[country_name] = country.Country(country_name, country_instance_filter,
                                                           industry_instance_filter, product_instance_filter)

        print("Model was successfully initiated.")

    def write_preprocessing_output(self, folder_name: str):
        """ Writes all the output that comes from preprocessing. """
        preprocessing_output.generate_output(folder_name, self.input_manager, self.preprocessor)
        print("Preprocessing output was successfully written.")

    def write_model_output(self, folder_name: str):
        """ Writes all the output that comes from preprocessing. """

        print("Model output was successfully written.")

    def write_output(self):
        """ Writes the models' output to the output folder. """
        self.write_preprocessing_output("preprocessing")
        #self.write_industry_output("industry")
        #self.write_general_output("general")


