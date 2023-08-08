"""
This module contains all classed used for the first stage of preprocessing.
"""

import warnings

from endemo2 import utility as uty
from endemo2.data_structures.enumerations import GroupType, ForecastMethod
from endemo2.data_structures.prediction_models import Coef, TwoDseries
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.preprocessing.preprocessing_step_one import CountryPreprocessed, ProductPreprocessed


class CountryGroup:
    """
    A group of countries.

    :ivar [str] _countries_in_group: List of countries that belong to this group.
    """

    def __init__(self, countries_in_group: [str]):
        self._countries_in_group = countries_in_group

class CountryGroupJoined(CountryGroup):
    """
    Represents one country group of type "joined".

    :ivar Coef _group_coef: The coefficients calculated for the whole group.
    :ivar TwoDseries _joined_data: The TwoDseries combining the data from all countries in this group.
    """
    def __init__(self, ctrl: ControlParameters, product_name: str, countries_in_group: [str],
                 countries_pp: dict[str, CountryPreprocessed]):
        super().__init__(countries_in_group)
        self._group_coef = Coef()

        # combine timeseries
        # merge all data of countries_in_group within group
        self._joined_data = TwoDseries([])
        for country_name in self._countries_in_group:
            country_pp: CountryPreprocessed = countries_pp[country_name]

            # if country doesn't have product, skip
            if product_name not in country_pp.industry_pp.products_pp.keys():
                continue

            product_pp: ProductPreprocessed = country_pp.industry_pp.products_pp[product_name]

            gdp_as_x = ctrl.industry_settings.use_gdp_as_x
            y_per_capita = ctrl.industry_settings.production_quantity_calc_per_capita

            # decide which data to use
            if not gdp_as_x and not y_per_capita:
                self._joined_data.append_others_data(product_pp.amount_vs_year)
            elif gdp_as_x and not y_per_capita:
                self._joined_data.append_others_data(product_pp.amount_vs_gdp)
            elif not gdp_as_x and y_per_capita:
                self._joined_data.append_others_data(product_pp.amount_per_capita_vs_year)
            elif gdp_as_x and y_per_capita:
                self._joined_data.append_others_data(product_pp.amount_per_capita_vs_gdp)

        # calculate group coefficients and save result
        self._group_coef = self._joined_data.get_coef()

    def get_coef(self) -> Coef:
        return self._group_coef


class CountryGroupJoinedDiversified(CountryGroup):
    """
    Represents one country group of type "joined diversified".

    :ivar [TwoDseries] _joined_data: The TwoDseries combining the data from all countries in this group.
    :ivar (float, float, float) _coef_tuple: The coefficients calculated for the whole group.
    :ivar dict[str, float] _offset_dict: The offsets for each country in this group.
    """
    def __init__(self, ctrl: ControlParameters, product_name: str, countries_in_group: [str],
                 countries_pp: dict[str, CountryPreprocessed]):
        super().__init__(countries_in_group)

        # combine timeseries
        self._joined_data = dict[str, TwoDseries]()
        for country_name in self._countries_in_group:
            country_pp: CountryPreprocessed = countries_pp[country_name]

            # if country doesn't have product, skip
            if product_name not in country_pp.industry_pp.products_pp.keys():
                continue

            product_pp: ProductPreprocessed = country_pp.industry_pp.products_pp[product_name]

            gdp_as_x = ctrl.industry_settings.use_gdp_as_x
            y_per_capita = ctrl.industry_settings.production_quantity_calc_per_capita

            # decide which data to use
            if not gdp_as_x and not y_per_capita:
                self._joined_data[country_name] = product_pp.amount_vs_year
            elif not gdp_as_x and y_per_capita:
                self._joined_data[country_name] = product_pp.amount_per_capita_vs_year
            elif gdp_as_x and not y_per_capita:
                self._joined_data[country_name] = product_pp.amount_vs_gdp
            elif gdp_as_x and y_per_capita:
                self._joined_data[country_name] = product_pp.amount_per_capita_vs_gdp

        # calculate group coefficients and save result
        # (self._coef_tuple, self._offset_dict) = uty.quadratic_regression_delta(self._joined_data)

    def get_coef_for_country(self, country_name) -> Coef:
        country_coef = Coef()
        country_coef.set_quadr(self._coef_tuple[0], self._coef_tuple[1], self._coef_tuple[2])
        country_coef.set_offset(self._offset_dict[country_name])
        return country_coef


class GroupManager:
    """
    The group manager is responsible for pre-processing the coefficients for all country groups and providing the
    results. These can be obtained via calling the provided methods.

    :ivar dict[str, set[str]] separate_countries_group: The countries calculated seperately for each product.
        Is of the form {product_name -> [separate countries]}.
    :ivar dict[str, [CountryGroupJoined]] joined_groups: The dictionary containing all joined groups for a product.
        Is of form {product_name -> [grp1, grp2, ...]}
    :ivar dict[str, [CountryGroupJoinedDiversified]] joined_groups: The dictionary containing all joined_diversified
        groups for a product. Is of form {product_name -> [grp1, grp2, ...]}
    :ivar dict[str, dict[str, (GroupType, int)]] country_to_group_map: A dictionary that for each products maps a
        country name to its group_id and group_type. Is of form {product_name -> country_name -> (group_type, group_id)}
    """

    def __init__(self, input_manager, countries_pp: dict[str, CountryPreprocessed]):
        self.separate_countries_group = dict[str, set[str]]()
        self.joined_groups = dict[str, [CountryGroupJoined]]()
        self.joined_div_groups = dict[str, [CountryGroupJoinedDiversified]]()
        self.country_to_group_map = dict[str, dict[str, (GroupType, int)]]()

        forecast_method = input_manager.ctrl.industry_settings.forecast_method
        group_input = dict[str, dict[GroupType, [[str]]]]()    # product -> {grp_type -> [grp1[cntry1, cntry2,..], grp2[cntry4,..]]}
        for product_name, product_input_obj in input_manager.industry_input.active_products.items():
            group_input[product_name] = product_input_obj.country_groups

        for product_name, group_dict in group_input.items():
            self.country_to_group_map[product_name] = dict[str, (GroupType, int)]()

            # save separate countries_in_group for easy check
            self.separate_countries_group[product_name] = \
                set([country for sublist in group_dict[GroupType.SEPARATE] for country in sublist])  # flatten

            # process joined groups for this product
            in_joined_groups_country_names: [[str]] = group_dict[GroupType.JOINED]
            res_joined_groups: [CountryGroupJoined] = []

            for joined_group in in_joined_groups_country_names:
                group_id = len(res_joined_groups)

                res_joined_groups.append(
                    CountryGroupJoined(input_manager.ctrl, product_name, joined_group, countries_pp))

                for country_name in joined_group:
                    # fill map to more efficiently access group with country_name
                    self.country_to_group_map[product_name][country_name] = (GroupType.JOINED, group_id)

            # save joined groups for this product
            self.joined_groups[product_name] = res_joined_groups

            # process joined_diversified groups for this product
            in_joined_div_groups_country_names: [[str]] = group_dict[GroupType.JOINED_DIVERSIFIED]
            res_joined_div_groups = [CountryGroupJoinedDiversified]

            for joined_div_group in in_joined_div_groups_country_names:
                group_id = len(res_joined_div_groups)

                res_joined_groups.append(
                    CountryGroupJoinedDiversified(input_manager.ctrl, product_name, joined_div_group, countries_pp))

                for country_name in joined_div_group:
                    # fill map to more efficiently access group with country_name
                    self.country_to_group_map[product_name][country_name] = (GroupType.JOINED_DIVERSIFIED, group_id)

            # save joined groups for this product
            self.joined_div_groups[product_name] = res_joined_div_groups

    def is_in_separate_group(self, country_name, product_name) -> bool:
        """
        Return whether country should be calculated separately or is member of a group and should therefore
        use the group coefficients.

        :param country_name: The name of the country.
        :param product_name: The name of the product.
        :return: The bool indicating whether the country is not in a country group for the given product.
        """
        return country_name in self.separate_countries_group[product_name]

    def get_coef_for_country_and_product(self, country_name, product_name) -> Coef:
        """
        Get the calculated group coefficient for a certain country and a certain product.

        :param country_name: The name of the country.
        :param product_name: The name of the product.
        :return: The group-calculated coefficients.
        """
        if self.is_in_separate_group(country_name, product_name):
            warnings.warn("Attention! Check if country is separate before checking group coefficients.")

        (group_type, group_id) = self.country_to_group_map[product_name][country_name]

        match group_type:
            case GroupType.JOINED:
                return self.joined_groups[group_id].get_coef()
            case GroupType.JOINED_DIVERSIFIED:
                return self.joined_div_groups[group_id].get_coef_for_country(country_name)
