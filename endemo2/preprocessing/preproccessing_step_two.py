import warnings

from endemo2 import utility as uty
from endemo2.data_structures.enumerations import GroupType, ForecastMethod
from endemo2.data_structures.prediction_models import Coef, TwoDseries
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.preprocessing.preprocessing_step_one import CountryPreprocessed, ProductPreprocessed


class CountryGroupJoined:
    def __init__(self, ctrl: ControlParameters, group_id: int, product_name: str, countries_in_group: [str],
                 countries_pp: dict[str, CountryPreprocessed]):
        self._group_type = GroupType.JOINED
        self._group_id = group_id
        self._countries_in_group = countries_in_group
        self.combined_timeseries = None
        self._calculated = False
        self._group_coef = Coef()

        # combine timeseries
        # merge all data of countries_in_group within group
        self.joined_data = TwoDseries([])
        for country_name in countries_in_group:
            country_pp: CountryPreprocessed = countries_pp[country_name]

            # if country doesn't product, skip
            if product_name not in country_pp.industry_pp.products_pp.keys():
                continue

            product_pp: ProductPreprocessed = country_pp.industry_pp.products_pp[product_name]

            gdp_as_x = ctrl.industry_settings.use_gdp_as_x
            y_per_capita = ctrl.industry_settings.production_quantity_calc_per_capita

            # decide which data to use
            if not gdp_as_x and not y_per_capita:
                self.joined_data.append_others_data(product_pp.amount_per_year)
            elif gdp_as_x and not y_per_capita:
                self.joined_data.append_others_data(product_pp.amount_per_gdp)
            elif not gdp_as_x and y_per_capita:
                self.joined_data.append_others_data(product_pp.amount_per_capita_per_year)
            elif gdp_as_x and y_per_capita:
                self.joined_data.append_others_data(product_pp.amount_per_capita_per_gdp)

        # calculate group coefficients and save result
        self.group_coef = self.joined_data.get_coef()

class CountryGroupJoinedDiversified:
    def __init__(self, ctrl: ControlParameters, group_id: int, product_name: str, countries_in_group: [str],
                 countries_pp: dict[str, CountryPreprocessed]):
        pass

class ProductCountryGroupCoefficients:
    """
    Holds all the group coefficients of different group types for a product.
    """
    def __init__(self, country_joined_group_map: dict, country_joined_div_group_map: dict,
                 separate: set[str], joined: dict[int, CountryGroupJoined], joined_div: dict):

        self.separate_countries: set[str] = separate  # {country_name}
        self.country_joined_group_map = country_joined_group_map  # {country_name -> group_id}
        self.country_joined_div_map = country_joined_div_group_map  # {country_name -> group_id}
        self.joined_groups: dict[int, CountryGroupJoined] = joined  # {group_id -> CountryGroupJoined}
        self.joined_div_groups: dict[str, CountryGroupJoinedDiversified] = joined_div  # {country_name -> CountryGroupJoinedDiversified}

    def is_in_separate_group(self, country_name) -> bool:
        return country_name in self.separate_countries

    def get_group_coef_for_country(self, country_name) -> Coef:
        if country_name in self.country_joined_group_map.keys():
            # return joined coef
            pass
        if country_name in self.country_joined_div_map.keys():
            # return joined diversified coef
            pass
        if country_name in self.separate_countries:
            warnings.warn("This should not be reached! Check if a country is separate beforehand.")
            return Coef()

class GroupManager:
    """
    The group manager is responsible for pre-processing the coefficients for all country groups and providing the
    results. These can be obtained via calling the provided methods.
    """

    def __init__(self, input_manager, countries_pp: dict[str, CountryPreprocessed]):
        self.product_groups = dict[str, self.ProductGroupCoefficients]()

        forecast_method = input_manager.ctrl.industry_settings.forecast_method
        group_input = dict()
        for product_name, product_input_obj in input_manager.industry_input.active_products.items():
            group_input[product_name] = product_input_obj.country_groups
        print(uty.str_dict(group_input))

        for product_name, group_dict in group_input.items():
            product_input_obj = input_manager.industry_input.active_products[product_name]

            # save separate countries_in_group for easy check
            separate_countries_group = \
                set([country for sublist in group_dict[GroupType.SEPARATE] for country in sublist])  # flatten

            # process joined groups for this product
            joined_groups_country_names: [[str]] = group_dict[GroupType.JOINED]

            res_country_joined_group_map = dict()
            joined_groups: [(Coef, [str])] = []

            for joined_group in joined_groups_country_names:
                group_id = len(joined_groups)

                CountryGroupJoined(group_id, product_name, joined_group, countries_pp)

                for country_name in joined_group:
                    # fill map to more efficiently access group with country_name
                    country_joined_group_map[country_name] = group_id

            # process joined_diversified groups for this product
            joined_div_groups_country_names: [[str]] = group_dict[GroupType.JOINED_DIVERSIFIED]
            joined_div_groups = dict[str, Coef]()

            for joined_div_group in joined_div_groups_country_names:
                # merge all data of countries_in_group within group
                joined_div_data = dict[str, [(float, float)]]()
                for country_name in joined_div_group:
                    # get data from input_and_settings
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
                ProductCountryGroupCoefficients(res_country_joined_group_map, res_separate_countries_group,
                                              res_joined_groups, res_joined_div_groups)

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
