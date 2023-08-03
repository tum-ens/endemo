from endemo2.enumerations import DemandType
from endemo2.preprocessing import preprocessing_step_one as pp1
from endemo2.output.output_utility import FileGenerator, generate_timeseries_output, shortcut_coef_output
from endemo2.data_analytics.prediction_models import Coef, Timeseries
from endemo2.input import input


def generate_preprocessing_output(folder_name: str, input_manager, preprocessor):
    generate_amount_timeseries_output(folder_name, input_manager, preprocessor.countries_pp)
    generate_amount_per_gdp_coef_output(folder_name, input_manager, preprocessor.countries_pp)
    generate_specific_consumption_output(folder_name, input_manager, preprocessor.countries_pp)


def generate_graphics_output():
    # TODO
    pass

def generate_amount_timeseries_output(folder, input_manager: input.Input, countries_pp: dict[str, pp1.CountryPreprocessed]):

    filename = "ind_ts_coef_product_amount_per_year.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_year
                    generate_timeseries_output(fg, ts, 1965, 2019)
                else:
                    generate_timeseries_output(fg, Timeseries([]), 1965, 2019)

    filename = "ind_ts_coef_product_amount_per_capita_per_year.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_capita_per_year
                    generate_timeseries_output(fg, ts, 1965, 2019)
                else:
                    generate_timeseries_output(fg, Timeseries([]), 1965, 2019)


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


def generate_specific_consumption_output(folder, input_manager: input.Input, countries_pp: dict[str, pp1.CountryPreprocessed]):
    products_has_his_sc = input_manager.industry_input.sc_historical_data_file_names.keys()

    filename = "ind_ts_specific_consumption.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name in products_has_his_sc:
            fg.start_sheet(product_name + "_heat")
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
                    generate_timeseries_output(fg, ts, 1990, 2019)
                else:
                    generate_timeseries_output(fg, Timeseries([]), 1990, 2019)

            fg.start_sheet(product_name + "_electricity")
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    sc_pp = products_pp[product_name].specific_consumption_pp
                    ts: Timeseries
                    if DemandType.ELECTRICITY in sc_pp.specific_consumption_historical.keys():
                        ts = sc_pp.specific_consumption_historical[DemandType.ELECTRICITY]
                    else:
                        ts = Timeseries([])
                    generate_timeseries_output(fg, ts, 1990, 2019)
                else:
                    generate_timeseries_output(fg, Timeseries([]), 1990, 2019)
