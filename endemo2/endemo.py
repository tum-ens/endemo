from endemo2 import input, output, country


class Endemo:
    """
    This is the instance of the model. From here we control what the model does on the highest level.

    :ivar Input input_manager: holds all the input from the Excel sheets for the current run of the program.
    :ivar dict[str, Country] countries: holds all the country objects, accessible by the countries english name.
    """

    def __init__(self):
        self.input_manager = None
        self.countries = dict()

    def read_input(self):
        """ Reads all the input files from the input folder and stores it in the input_manager member variable. """
        self.input_manager = input.Input()

        for country_name in self.input_manager.ctrl.general_settings.active_countries:
            self.countries[country_name] = country.Country(country_name, self.input_manager)

    def load_model(self):
        """ Future todo """
        pass

    def save_model(self):
        """ Future todo """
        pass

    def write_debug_output(self):
        """ Writes all the output that is useful for debugging, but not necessary for the results. """
        output.generate_coefficient_output(self)
        output.generate_population_prognosis_output(self)
        output.generate_gdp_prognosis_output(self)
        output.generate_amount_prognosis_output(self)
        output.generate_specific_consumption_output(self)
        output.generate_demand_output(self)

    def write_output(self):
        """ Writes the models' output to the output folder. """
        # TODO
        pass
