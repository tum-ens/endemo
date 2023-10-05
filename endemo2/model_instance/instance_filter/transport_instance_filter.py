from typing import Union

from endemo2.data_structures.containers import Demand
from endemo2.data_structures.enumerations import TransportModal, TransportModalSplitMethod, ForecastMethod, TrafficType, \
    TransportFinalEnergyDemandScenario
from endemo2.input_and_settings.input_transport import TransportInput
from endemo2.model_instance.instance_filter.general_instance_filter import InstanceFilter, CountryInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter import IndustryInstanceFilter, \
    ProductInstanceFilter
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2 import utility as uty


class TransportInstanceFilter(InstanceFilter):
    def __init__(self, ctrl, transport_input: TransportInput, preprocessor: Preprocessor,
                 country_instance_filter: CountryInstanceFilter, industry_instance_filter: IndustryInstanceFilter,
                 product_instance_filter: ProductInstanceFilter):
        super().__init__(ctrl, preprocessor)

        self.transport_input = transport_input
        self.country_if = country_instance_filter
        self.industry_if = industry_instance_filter
        self.product_if = product_instance_filter

    def get_nuts2_region_names(self, country_name) -> [str]:
        """ Get the nuts2 region names of a country. """
        return self.industry_if.get_nuts2_regions(country_name)

    def get_energy_consumption_of_modal(self, traffic_type, modal_id) -> Demand:
        """ Get the energy consumption per ukm for a modal. """
        return self.transport_input.modal_ukm_energy_consumption[traffic_type][modal_id]

    def get_perc_modal_to_demand_type_in_target_year(self, country_name, traffic_type, modal_id, demand_type) -> float:
        """ Get the percentage of ukm that contribute to a demand type. """

        final_energy_scenario = self.ctrl.transport_settings.scenario_selection_final_energy_demand
        datapoints = []

        if final_energy_scenario == TransportFinalEnergyDemandScenario.REFERENCE:
            datapoints = self.transport_input.modal_energy_split_ref[traffic_type][modal_id][demand_type][country_name]
        elif final_energy_scenario == TransportFinalEnergyDemandScenario.USER_DEFINED:
            datapoints = self.transport_input.modal_energy_split_user[traffic_type][modal_id][demand_type][country_name]

        target_year = self.ctrl.general_settings.target_year

        (d1, d2) = uty.find_interval_between_datapoints(datapoints, target_year)
        return uty.exponential_interpolation(d1, d2, target_year)

    def get_modals_for_traffic_type(self, traffic_type) -> [TransportModal]:
        """ Returns a list of all modals for the given traffic type. """
        return TransportInput.tra_modal_lists[traffic_type]

    def get_population_country_in_target_year(self, country_name) -> float:
        """ Get the country population in target year. """
        return self.country_if.get_population_country_in_target_year(country_name)

    def get_population_nuts2_in_target_year(self, country_name) -> dict[str, float]:
        """ Get the nuts2 population in target year. """
        return self.country_if.get_population_nuts2_in_target_year(country_name)

    def get_historical_population_in_certain_year(self, country_name, year) -> float:
        """ Get the population of a country in a given year. """
        ts_pop_his = self.preprocessor.countries_pp[country_name].population_pp.population_historical_whole_country
        return ts_pop_his.get_value_at_year(year)

    def get_specific_unit_km_in_reference_year(self, country_name, traffic_type, modal_id) -> float:
        """ Get the kilometers per person or per ton in reference year. """
        modal_group_parent = self.get_modal_group_parent(traffic_type, modal_id)
        if modal_group_parent is None:
            modal_group_parent = modal_id

        modal_shared_historical_value_total = \
            self.transport_input.kilometres[traffic_type][country_name][modal_group_parent]

        year_of_historical_value = modal_shared_historical_value_total.x

        specific_ukm = 0
        if traffic_type == TrafficType.PERSON:
            specific_ukm = \
                modal_shared_historical_value_total.y \
                / self.get_historical_population_in_certain_year(country_name, year_of_historical_value)
        elif traffic_type == TrafficType.FREIGHT:
            reference_year = self.ctrl.transport_settings.ind_production_reference_year
            reference_amount = self.product_if.get_product_amount_historical_in_year(country_name, reference_year)

            specific_ukm = modal_shared_historical_value_total.y / reference_amount

        return specific_ukm

    def get_unit_km_country_in_target_year(self, country_name, traffic_type: TrafficType, modal_id: TransportModal) \
            -> float:
        """ Get the total amount of kilometres of a traffic type and modal for a country in the target year. """

        modal_share_target_year = self.get_modal_share_in_target_year(country_name, traffic_type, modal_id)

        specific_ukm = self.get_specific_unit_km_in_reference_year(country_name, traffic_type, modal_id)
        target_year_amount = 0
        if traffic_type == TrafficType.PERSON:
            target_year_amount = self.get_population_country_in_target_year(country_name)
        elif traffic_type == TrafficType.FREIGHT:
            # take product amount forecast from industry
            target_year_amount = self.product_if.get_product_amount_sum_country_in_target_year(country_name)

        return specific_ukm * target_year_amount * modal_share_target_year

    def get_unit_km_nuts2_in_target_year(self, country_name, region_name: str, traffic_type: TrafficType,
                                         modal_id: TransportModal) -> float:
        """ Get the total amount of kilometres of a traffic type and modal for a country in the target year. """

        ukm_country = self.get_unit_km_country_in_target_year(country_name, traffic_type, modal_id)
        distribution_scalars = self.get_nuts2_distribution_scalars(country_name, traffic_type)

        return ukm_country * distribution_scalars[region_name]

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

    def get_nuts2_distribution_scalars(self, country_name, traffic_type) -> dict[str, float]:
        """ Get the scalars for distributing results across nuts2 regions. """

        if traffic_type == TrafficType.PERSON:
            return self.country_if.get_population_nuts2_percentages_in_target_year(country_name)
        if traffic_type == TrafficType.FREIGHT:
            return self.country_if.get_population_nuts2_percentages_in_target_year(country_name)
