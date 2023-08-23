from endemo2.input_and_settings.input_transport import TransportInput
from endemo2.model_instance.instance_filter.general_instance_filter import InstanceFilter, CountryInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter import IndustryInstanceFilter
from endemo2.preprocessing.preprocessor import Preprocessor


class TransportInstanceFilter(InstanceFilter):
    def __init__(self, ctrl, transport_input: TransportInput, preprocessor: Preprocessor,
                 country_instance_filter: CountryInstanceFilter, industry_instance_filter: IndustryInstanceFilter):
        super().__init__(ctrl, preprocessor)

        self.transport_input = transport_input
        self.country_if = country_instance_filter
        self.industry_if = industry_instance_filter


