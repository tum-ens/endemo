from typing import Union

from endemo2.data_structures.enumerations import TransportModal, TransportModalSplitMethod, ForecastMethod, TrafficType
from endemo2.input_and_settings.input_transport import TransportInput
from endemo2.model_instance.instance_filter.general_instance_filter import InstanceFilter, CountryInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter import IndustryInstanceFilter
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2 import utility as uty


class TransportInstanceFilter(InstanceFilter):
    def __init__(self, ctrl, transport_input: TransportInput, preprocessor: Preprocessor,
                 country_instance_filter: CountryInstanceFilter, industry_instance_filter: IndustryInstanceFilter):
        super().__init__(ctrl, preprocessor)

        self.transport_input = transport_input
        self.country_if = country_instance_filter
        self.industry_if = industry_instance_filter

    def get_population_in_target_year(self, country_name) -> float:
        """ Get the population in target year. """
        return self.country_if.get_population_country_in_target_year(country_name)

    def get_historical_population_in_certain_year(self, country_name, year) -> float:
        """ Get the population of a country in a given year. """
        ts_pop_his = self.preprocessor.countries_pp[country_name].population_pp.population_historical_whole_country
        return ts_pop_his.get_value_at_year(year)

    def get_unit_km_in_target_year(self, country_name, traffic_type: TrafficType, modal_id: TransportModal) -> float:
        """ Get the total amount of kilometres of a traffic type and modal in the target year. """
        modal_group_parent = self.get_modal_group_parent(traffic_type, modal_id)
        if modal_group_parent is None:
            modal_group_parent = modal_id

        modal_share = self.get_modal_share_in_target_year(country_name, traffic_type, modal_id)

        modal_shared_historical_value_total = \
            self.transport_input.kilometres[traffic_type][country_name][modal_group_parent]

        year_of_historical_value = modal_shared_historical_value_total.x

        modal_shared_historical_specific = 0
        target_year_amount = 0
        if traffic_type == TrafficType.PERSON:
            modal_shared_historical_specific = \
                modal_shared_historical_value_total.y \
                / self.get_historical_population_in_certain_year(country_name, year_of_historical_value)
            target_year_amount = self.get_population_in_target_year(country_name)
        elif traffic_type == TrafficType.FREIGHT:
            reference_year = self.ctrl.transport_settings.ind_production_reference_year
            reference_amount = self.industry_if.get_product_amount_historical_in_year(country_name, reference_year)
            target_year = self.ctrl.general_settings.target_year
            # todo: take forecast instead of historical value here
            target_year_amount = self.industry_if.get_product_amount_historical_in_year(country_name, target_year)
            modal_shared_historical_specific = modal_shared_historical_value_total.y / reference_amount

        return modal_shared_historical_specific * target_year_amount * modal_share

    def get_modal_share_in_target_year(self, country_name, traffic_type: TrafficType, modal_id: TransportModal) \
            -> float:
        """ Get the share of a modal of transport in their group. If the modal is not grouped, returns 1.0 (100%). """
        transport_pp = self.preprocessor.countries_pp[country_name].transport_pp

        match self.ctrl.transport_settings.split_method:
            case TransportModalSplitMethod.HISTORICAL_TIME_TREND:
                modal_group_parent = self.get_modal_group_parent(traffic_type, modal_id)
                if modal_group_parent is None:
                    # not in split group -> return 100%
                    return 1.0
                modal_share = \
                    self.get_modal_group_percentages_in_target_year(country_name, traffic_type,
                                                                           modal_group_parent)[modal_id]
                return modal_share
            case TransportModalSplitMethod.HISTORICAL_CONSTANT:
                modal_group_parent = self.get_modal_group_parent(traffic_type, modal_id)
                if modal_group_parent is None:
                    # not in split group -> take historical value directly
                    return 1.0
                modal_share = transport_pp.modal_split_timeseries[traffic_type][modal_id].get_last_data_entry().y

                return modal_share

            case TransportModalSplitMethod.USER_DEFINED:
                target_year = self.ctrl.general_settings.target_year

                # find interval in supporting points and interpolate
                interval = uty.find_interval_between_datapoints(self.transport_input.modal_split_user_def[traffic_type],
                                                                target_year)
                interpolated_value = uty.exponential_interpolation(interval.start, interval.end, target_year)

                return interpolated_value

    def get_modal_group_parent(self, traffic_type: TrafficType, modal_id: TransportModal) \
            -> Union[TransportModal, None]:
        """ Get the parent modal of the group the given modal_id belongs to. """
        for modal_parent_id, modal_list in TransportInput.tra_modal_split_groups[traffic_type].items():
            if modal_id in modal_list:
                return modal_parent_id
        return None

    def get_modal_group_percentages_in_target_year(self, country_name, traffic_type: TrafficType,
                                                   modal_group_parent_id: TransportModal) \
            -> dict[TransportModal, float]:
        """ Get the forecasted shares of each modal in the group of the given modal parent. """
        transport_pp = self.preprocessor.countries_pp[country_name].transport_pp
        target_year = self.ctrl.general_settings.target_year

        forecast_dict = dict[TransportModal, float]()
        percentage_sum = 0.0

        # do forecast for each modal in group
        for modal_id in TransportInput.tra_modal_split_groups[traffic_type][modal_group_parent_id]:
            his_modal_share = transport_pp.modal_split_timeseries[traffic_type][modal_id]

            coef_modal_share = his_modal_share.get_coef()
            coef_modal_share.set_method(ForecastMethod.LINEAR)

            forecasted_share = max(0.0, coef_modal_share.get_function_y(target_year))

            percentage_sum += forecasted_share
            forecast_dict[modal_id] = forecasted_share

        # make all entries sum up to 1
        res_dict = uty.multiply_dictionary_with_scalar(forecast_dict, 1 / percentage_sum)

        return res_dict

