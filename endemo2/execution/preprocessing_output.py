from endemo2.general.demand_containers import DemandType
from endemo2.preprocessing import preprocessing_step_one as pp1
from endemo2.utility.file_utility import FileGenerator
from endemo2.utility.prediction_models import Coef, Timeseries
from endemo2.preprocessing import input

folder = "preprocessing"

def shortcut_coef_output(fg: FileGenerator, coef: Coef):
    exp_coef = coef._exp
    lin_coef = coef._lin
    quadr_coef = coef._quadr
    offset = coef._offset

    fg.add_entry("EXP Start Point", "(" + str(exp_coef[0][0]) + ", " + str(exp_coef[0][1]) + ")")
    fg.add_entry("EXP Change Rate", exp_coef[1])
    fg.add_entry("L k0", lin_coef[0])
    fg.add_entry("L k1", lin_coef[1])
    fg.add_entry("Q k0", quadr_coef[0])
    fg.add_entry("Q k1", quadr_coef[1])
    fg.add_entry("Q k2", quadr_coef[2])
    fg.add_entry("Offset", offset)


def shortcut_save_timeseries_print(fg, from_year, to_year, data: [(float, float)]):
    """ To correctly print, when data does potentially not cover every year."""

    i = from_year
    for (year, value) in data:
        while i < year:
            fg.add_entry(i, "-")
            i += 1
        fg.add_entry(year, value)
        i += 1

    while i <= to_year:
        fg.add_entry(i, "-")
        i += 1


def generate_timeseries_output(fg: FileGenerator, ts: Timeseries, year_from: int, year_to: int):
    # output coef
    coef = ts.get_coef()
    shortcut_coef_output(fg, coef)

    # output data
    shortcut_save_timeseries_print(fg, year_from, year_to, ts.get_data())


def generate_amount_timeseries_output(input_manager: input.Input, countries_pp: dict[str, pp1.CountryPreprocessed]):

    filename = "ind_ts_coef_amount_per_year.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    fg.add_entry("Country", country_name)
                    ts = products_pp[product_name].amount_per_year
                    generate_timeseries_output(fg, ts, 1960, 2019)

    filename = "ind_ts_coef_amount_per_capita_per_year.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    fg.add_entry("Country", country_name)
                    ts = products_pp[product_name].amount_per_capita_per_year
                    generate_timeseries_output(fg, ts, 1960, 2019)


def generate_amount_per_gdp_coef_output(input_manager: input.Input, countries_pp: dict[str, pp1.CountryPreprocessed]):

    filename = "ind_ts_coef_amount_per_gdp.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    fg.add_entry("Country", country_name)
                    ts = products_pp[product_name].amount_per_gdp
                    shortcut_coef_output(fg, ts.get_coef())

    filename = "ind_ts_coef_amount_per_capita_per_gdp.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.active_products.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    fg.add_entry("Country", country_name)
                    ts = products_pp[product_name].amount_per_capita_per_gdp
                    shortcut_coef_output(fg, ts.get_coef())


def generate_specific_consumption_output(input_manager: input.Input, countries_pp: dict[str, pp1.CountryPreprocessed]):
    products_has_his_sc = input_manager.industry_input.sc_historical_data_file_names.keys()

    filename = "ind_timeseries_specific_consumption.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name in products_has_his_sc:
            fg.start_sheet(product_name + "_heat")
            for country_name, country_pp in countries_pp.items():
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    fg.add_entry("Country", country_name)
                    sc_pp = products_pp[product_name].specific_consumption_pp
                    ts: Timeseries
                    if DemandType.HEAT in sc_pp.specific_consumption_historical.keys():
                        ts = sc_pp.specific_consumption_historical[DemandType.HEAT]
                    else:
                        ts = Timeseries([])
                    generate_timeseries_output(fg, ts, 1990, 2019)

            fg.start_sheet(product_name + "_electricity")
            for country_name, country_pp in countries_pp.items():
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    fg.add_entry("Country", country_name)
                    sc_pp = products_pp[product_name].specific_consumption_pp
                    ts: Timeseries
                    if DemandType.ELECTRICITY in sc_pp.specific_consumption_historical.keys():
                        ts = sc_pp.specific_consumption_historical[DemandType.ELECTRICITY]
                    else:
                        ts = Timeseries([])
                    generate_timeseries_output(fg, ts, 1990, 2019)
