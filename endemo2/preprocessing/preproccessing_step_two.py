import warnings

from endemo2 import utility as uty
from endemo2.enumerations import GroupType, ForecastMethod
from endemo2.data_analytics.prediction_models import Coef


class CountryGroupJoined:
    def __init__(self, group_id: int, countries: [str]):
        self._group_type = GroupType.JOINED
        self._group_id = group_id
        self._countries_in_group = countries
        self._calculated = False
        self._group_coef = Coef()

    def _calc_coef(self):
        pass

    def get_coef(self):
        if not self._calculated:
            self._calculated = True
        pass


class GroupManager:
    """
    The group manager is responsible for pre-processing the coefficients for all country groups and providing the
    results. These can be obtained via calling the provided methods.
    """

    class ProductGroupCoefficients:
        """
        Holds all the group coefficients of different group types for a product.
        """

        def __init__(self, country_joined_group_map: dict, separate: set[str], joined: [(Coef, [str])],
                     joined_div: dict):

            self._separate_countries: set[str] = separate  # {country_name}
            self._country_joined_group_map = country_joined_group_map  # {country_name -> group_id}
            self._joined_groups: [(Coef, [str])] = joined  # {group_id -> (Coef, [country_name])}
            self._joined_div_groups: dict[str, (Coef, [str])] = joined_div  # {country_name -> Coef}

        def is_in_separate_group(self, country_name) -> bool:
            return country_name in self._separate_countries

        def get_country_coef(self, country_name) -> Coef:
            if country_name in self._country_joined_group_map.keys():
                return self._joined_groups[self._country_joined_group_map[country_name]]
            if country_name in self._joined_div_groups.keys():
                return self._joined_div_groups[country_name]
            if country_name in self._separate_countries:
                warnings.warn("This should not be reached! Check if a country is separate beforehand.")
                return Coef()

    def __init__(self, input_manager):
        self.product_groups = dict[str, self.ProductGroupCoefficients]()

        forecast_method = input_manager.ctrl.industry_settings.forecast_method
        group_input = dict()
        for product_name, product_input_obj in input_manager.industry_input.active_products.items():
            group_input[product_name] = product_input_obj.country_groups
        print(uty.str_dict(group_input))

        for product_name, group_dict in group_input.items():
            product_input_obj = input_manager.industry_input.active_products[product_name]

            # save separate countries for easy check
            separate_countries_group = \
                set([country for sublist in group_dict[GroupType.SEPARATE] for country in sublist])  # flatten

            # process joined groups for this product
            joined_groups_country_names: [[str]] = group_dict[GroupType.JOINED]

            country_joined_group_map = dict()
            joined_groups: [(Coef, [str])] = []

            for joined_group in joined_groups_country_names:
                group_id = len(joined_groups)

                # merge all data of countries within group
                joined_data: [(float, float)] = []
                for country_name in joined_group:
                    # fill map to more efficiently access group from country
                    country_joined_group_map[country_name] = group_id

                    # if country doesn't product, skip
                    if country_name not in product_input_obj.production.keys():
                        continue

                    # get data from input
                    product_his_data_of_country = product_input_obj.production[country_name]
                    gdp_his_data_of_country = input_manager.general_input.gdp[country_name].historical

                    # decide which data to use for regression
                    if input_manager.ctrl.industry_settings.use_gdp_as_x:
                        gdp_x_product_y = uty.zip_data_on_x(gdp_his_data_of_country, product_his_data_of_country)
                        joined_data += gdp_x_product_y
                    else:
                        joined_data += product_his_data_of_country

                # apply regression according to method
                result_coef = uty.apply_all_regressions(joined_data)
                result_coef.set_method(forecast_method)

                # save results
                joined_groups.append((result_coef, joined_group))

            # process joined_diversified groups for this product
            joined_div_groups_country_names: [[str]] = group_dict[GroupType.JOINED_DIVERSIFIED]
            joined_div_groups = dict[str, Coef]()

            for joined_div_group in joined_div_groups_country_names:
                # merge all data of countries within group
                joined_div_data = dict[str, [(float, float)]]()
                for country_name in joined_div_group:
                    # get data from input
                    if country_name not in product_input_obj.production.keys():
                        continue
                    product_his_data_of_country = product_input_obj.production[country_name]
                    gdp_his_data_of_country = input_manager.general_input.gdp[country_name].historical

                    # decide which data to use for regression
                    if input_manager.ctrl.industry_settings.use_gdp_as_x:
                        gdp_x_product_y = uty.zip_data_on_x(gdp_his_data_of_country, product_his_data_of_country)
                        joined_div_data[country_name] = gdp_x_product_y
                    else:
                        joined_div_data[country_name] = product_his_data_of_country

                # apply delta regression to group
                (quadr_coef, offsets) = uty.quadratic_regression_delta(joined_div_data)

                # save results
                for country_name, offset in offsets:
                    joined_div_groups[country_name] = \
                        Coef(quadr=quadr_coef, offset=offset, method=ForecastMethod.QUADRATIC_OFFSET)

            # fill all groups into product object
            self.product_groups[product_name] = \
                self.ProductGroupCoefficients(country_joined_group_map, separate_countries_group,
                                              joined_groups, joined_div_groups)

    def is_in_separate_group(self, country_name, product_name) -> bool:
        """
        Return whether country should be calculated separately or is member of a group and should therefore
        use the group coefficients.
        """
        return self.product_groups[product_name].is_in_separate_group(country_name)

    def get_coef_for_country_and_product(self, country_name, product_name) -> pm.Coef:
        """
        Get the calculated group coefficient for a certain country and a certain product.

        :param country_name: The name of the country.
        :param product_name: The name of the product.
        :return: The group-calculated coefficients.
        """
        return self.product_groups[product_name].get_country_coef(country_name)
