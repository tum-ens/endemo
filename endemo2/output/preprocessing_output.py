from endemo2.data_structures.enumerations import DemandType
from endemo2.preprocessing import preprocessing_step_one as pp1
from endemo2.output.output_utility import FileGenerator, generate_timeseries_output, shortcut_coef_output, \
    get_year_range
from endemo2.data_structures.prediction_models import Coef, Timeseries
from endemo2.input_and_settings import input
from endemo2.preprocessing.preprocessing_step_one import CountryPreprocessed, ProductPreprocessed


def generate_preprocessing_output(folder_name: str, input_manager, preprocessor):
    generate_amount_timeseries_output(folder_name, input_manager, preprocessor.countries_pp)
    generate_amount_per_gdp_coef_output(folder_name, input_manager, preprocessor.countries_pp)
    generate_specific_consumption_output(folder_name, input_manager, preprocessor.countries_pp)


def generate_graphics_output():
    # TODO
    pass


def _get_all_product_pps(product_name: str, countries_pp) -> [ProductPreprocessed]:
    return [country_pp.industry_pp.products_pp[product_name]
            for country_pp in countries_pp.values()
            if product_name in country_pp.industry_pp.products_pp.keys()]


def generate_amount_timeseries_output(folder, input_manager: input.Input, countries_pp: dict[str, CountryPreprocessed]):

    filename = "ind_ts_coef_product_amount_per_year.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)

            all_tss = \
                [product_pp.amount_per_year for product_pp in _get_all_product_pps(product_name, countries_pp)]
            year_range = get_year_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_year
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([]), year_range)

    filename = "ind_ts_coef_product_amount_per_capita_per_year.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)

            all_tss = \
                [product_pp.amount_per_capita_per_year for product_pp in _get_all_product_pps(product_name, countries_pp)]
            year_range = get_year_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_capita_per_year
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([]), year_range)


def generate_amount_per_gdp_coef_output(folder, input_manager: input.Input, countries_pp: dict[str, pp1.CountryPreprocessed]):

    filename = "ind_coef_product_amount_per_gdp.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_gdp
                    shortcut_coef_output(fg, ts.get_coef())
                else:
                    shortcut_coef_output(fg, Coef())

    filename = "ind_coef_product_amount_per_capita_per_gdp.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_capita_per_gdp
                    shortcut_coef_output(fg, ts.get_coef())
                else:
                    shortcut_coef_output(fg, Coef())


def generate_specific_consumption_output(folder, input_manager: input.Input,
                                         countries_pp: dict[str, CountryPreprocessed]):
    products_has_his_sc = input_manager.industry_input.sc_historical_data_file_names.keys()

    filename = "ind_ts_specific_consumption.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name in products_has_his_sc:
            fg.start_sheet(product_name + "_heat")
            all_tss = \
                [product_pp.specific_consumption_pp.specific_consumption_historical[DemandType.HEAT]
                 for product_pp in _get_all_product_pps(product_name, countries_pp)
                 if DemandType.HEAT in product_pp.specific_consumption_pp.specific_consumption_historical.keys()]
            year_range = get_year_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp

                if product_name in products_pp.keys():
                    sc_pp = products_pp[product_name].specific_consumption_pp
                    ts: Timeseries
                    if DemandType.HEAT in sc_pp.specific_consumption_historical.keys():
                        ts = sc_pp.specific_consumption_historical[DemandType.HEAT]
                    else:
                        ts = Timeseries([])
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([]), year_range)

            fg.start_sheet(product_name + "_electricity")
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                all_tss = \
                    [product_pp.specific_consumption_pp.specific_consumption_historical[DemandType.ELECTRICITY]
                     for product_pp in _get_all_product_pps(product_name, countries_pp)
                     if DemandType.ELECTRICITY
                     in product_pp.specific_consumption_pp.specific_consumption_historical.keys()]
                year_range = get_year_range(all_tss)

                if product_name in products_pp.keys():
                    sc_pp = products_pp[product_name].specific_consumption_pp
                    ts: Timeseries
                    if DemandType.ELECTRICITY in sc_pp.specific_consumption_historical.keys():
                        ts = sc_pp.specific_consumption_historical[DemandType.ELECTRICITY]
                    else:
                        ts = Timeseries([])
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([]), year_range)
