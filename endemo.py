import output
import country
import input


class Endemo:
    """
    This is the instance of the model. From here we control what the model does on the highest level.
    """
    input_manager: input.Input
    countries: dict[country.Country]

    def read_input(self):
        self.input_manager = input.Input()

        self.countries = dict()
        for country_name in self.input_manager.ctrl.general_settings.active_countries:
            self.countries[country_name] = country.Country(country_name, self.input_manager)

    def load_model(self):
        # Future todo
        pass

    def save_model(self):
        # Future todo
        pass

    def write_debug_output(self):
        output.generate_coefficient_output(self)
        output.generate_population_prognosis_output(self)
        output.generate_gdp_prognosis_output(self)
        output.generate_amount_prognosis_output(self)
        output.generate_specific_consumption_output(self)
        output.generate_demand_output(self)

    def write_output(self):
        # TODO
        pass
