"""
This module is responsible for reading the input data form files.
(except the Set_and_Control_Parameters. That would be in control_parameters.)
"""
import warnings
from pathlib import Path

import pandas as pd

from endemo2 import utility as uty
from endemo2.data_structures import containers as dc
from endemo2.input_and_settings import control_parameters as cp
from endemo2.input_and_settings.control_parameters import ControlParameters


class Abbreviations:
    # create country_abbr -> country_name_en mapping
    dict_alpha2_en_map = dict[str, str]()
    # create country_name_de -> country_name_en mapping
    dict_de_en_map = dict[str, str]()
    # create country_name_en -> country_abbr mapping
    dict_en_alpha2_map = dict[str, str]()


class PopulationInput:
    """
    Holds all data on population. That includes historical data, prognosis data for each country and nuts2 region.

    :param ControlParameters ctrl: The parsed Set_and_Control_Parameters.xlsx file.
    :param set nuts2_valid_regions: The set of nuts2 regions that are recognized.
        They are used to filter the preprocessing data.
    :param dict abbreviations: The countries_in_group abbreviations, used to access nuts2 data.
    :param pd.DataFrame df_country_pop_his: The sheet containing data of population history per country.
    :param pd.DataFrame df_country_pop_prog: The sheet containing the manual prognosis of population amount per country.
    :param pd.DataFrame df_nuts2_pop_his: The sheet containing data of population history per NUTS2 region.
    :param pd.DataFrame df_nuts2_pop_prog:
        The sheet containing the prognosis intervals and growth rate for nuts2 regions.

    :ivar dict[str, HisProg] country_population: Data for the population of whole countries_in_group.
        It is of the form historical:{country_name -> [(float, float)]}, prognosis:{country_name -> [(float, float)]}
    :ivar dict[str, [(str, [float, float])]] nuts2_population: Data for the population of NUTS2 regions.
        It is of the form {country_name -> (code -> (historical: [(float,float)], prognosis: [interval, growth rate]))}
    """

    def __init__(self, ctrl: cp.ControlParameters, nuts2_valid_regions: set, abbreviations: dict[str, dc.CA],
                 df_country_pop_his: pd.DataFrame, df_country_pop_prog: pd.DataFrame,
                 df_nuts2_pop_his: pd.DataFrame, df_nuts2_pop_prog: pd.DataFrame):
        self.country_population = dict[str, dc.HisProg]()
        self.nuts2_population = dict[str, [(str, [float, float])]]()

        # preprocess country population historical data
        dict_c_pop_his = uty.convert_table_to_filtered_data_series_per_country(df_country_pop_his)

        # preprocess country population prognosis
        dict_c_pop_prog = uty.convert_table_to_filtered_data_series_per_country(df_country_pop_prog)

        # preprocess nuts2 population historical data
        df_nuts2_pop_his = df_nuts2_pop_his.drop('GEO/TIME', axis=1)
        dict_nuts2_pop_his = dict[str, dict[str, [(float, float)]]]()
        it = df_nuts2_pop_his.itertuples()
        for row in it:
            region_name = str(row[1]).strip()  # read region code from rows
            if region_name.endswith("-"):
                region_name = region_name[:-2]
            if region_name not in nuts2_valid_regions:
                continue
            if region_name[-1] == "X":
                # its a non-region
                continue
            zipped = list(zip(list(df_nuts2_pop_his)[1:], row[2:]))
            his_data = uty.filter_out_nan_and_inf(zipped)
            abbrev = region_name[:2]
            if abbrev not in dict_nuts2_pop_his.keys():
                dict_nuts2_pop_his[abbrev] = dict()
            dict_nuts2_pop_his[abbrev][region_name] = his_data

        # preprocess nuts2 population prognosis: interval 2015-2050
        df_nuts2_pop_prog = df_nuts2_pop_prog.drop(["Region name", "for 35 years"], axis=1) \
            .rename(columns={'per year': '2015-2050'})
        interval_conv = lambda xs: [dc.Interval(int(x.split('-')[0]), int(x.split('-')[1])) for x in xs]
        intervals = interval_conv(df_nuts2_pop_prog.columns[1:])

        dict_nuts2_pop_prog = dict[str, dict[str, [(dc.Interval, float)]]]()
        it = df_nuts2_pop_prog.itertuples()
        for row in it:
            region_name = str(row[1]).strip()
            if region_name not in nuts2_valid_regions:
                continue
            alpha2 = region_name[:2]

            values = df_nuts2_pop_prog[df_nuts2_pop_prog["Code"] == region_name].iloc[0][1:]
            zipped_prog = list(zip(intervals, values))

            if alpha2 not in dict_nuts2_pop_prog.keys():
                dict_nuts2_pop_prog[alpha2] = dict()

            dict_nuts2_pop_prog[alpha2][region_name] = zipped_prog

        for country_name in ctrl.general_settings.active_countries:
            # fill country population
            self.country_population[country_name] = \
                dc.HisProg(dict_c_pop_his[country_name], dict_c_pop_prog[country_name])

            # fill nuts2 population
            if country_name not in self.nuts2_population.keys():
                self.nuts2_population[country_name] = dict()
            abbrev = Abbreviations.dict_en_alpha2_map[country_name]
            self.nuts2_population[country_name] = \
                dc.HisProg(dict_nuts2_pop_his[abbrev], dict_nuts2_pop_prog[abbrev])


class GeneralInput:
    """
    General Input contains all preprocessing that is read from the "preprocessing/general" folder.

    :param ControlParameters ctrl: The parsed Set_and_Control_Parameters.xlsx
    :param Path path: The path to the preprocessing/general folder

    :ivar PopulationData population: All data from the population preprocessing.
    :ivar dict[str, HisProg[[(float, float)], [Interval, float]]] gdp: The gdp for each country.
    :ivar dict[str, ("electricity", "heat")] efficiency: The efficiency for each energy carrier.
    :ivar dict[str, ("electricity", "heat")] efficiency_hh: The efficiency for each energy carrier using the households
        names.
    :ivar set nuts2_valid_regions: The set of valid nuts2 regions within the selected NUTS2 code.
    """

    sc_historical_sheet_names = ["Feste fossile Brennstoffe", "Synthetische Gase", "Erdgas", "Oel",
                                 "Erneuerbare Energien", "Abfaelle", "Elektrizitaet", "Waerme"]

    def __init__(self, ctrl: cp.ControlParameters, path: Path):
        self.abbreviations = dict[str, dc.CA]()
        self.gdp = dict[str, dc.HisProg[[(float, float)], [dc.Interval, float]]]()
        self.efficiency = dict[str, dc.EH]()
        self.efficiency_hh = dict[str, dc.EH]()

        df_abbr = pd.read_excel(path / "Abbreviations.xlsx")
        df_world_pop_his = pd.read_excel(path / "Population_historical_world.xls")
        df_world_pop_prog = pd.read_excel(path / "Population_projection_world.xlsx")
        df_nuts2_pop_his = pd.read_csv(path / "Population_historical_NUTS2.csv")
        df_nuts2_pop_prog = \
            pd.read_excel(path / "Population_projection_NUTS2.xlsx",
                          sheet_name="Populationprojection_NUTS2_" + str(ctrl.general_settings.nuts2_version))
        df_gdp_his = pd.read_excel(path / "GDP_per_capita_historical.xlsx", sheet_name="constant 2015 USD")
        df_gdp_prog_europa = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data")
        df_gdp_prog_world = pd.read_excel(path / "GDP_per_capita_change_rate_projection.xlsx", sheet_name="Data_world")
        df_efficiency = pd.read_excel(path / "Efficiency_Combustion.xlsx", sheet_name="Data")
        df_nuts2_labels = pd.read_excel(path / "NUTS2_from_Model.xlsx")

        # fill nuts2 valid regions
        column_name = "Code " + str(ctrl.general_settings.nuts2_version)
        self.nuts2_valid_regions = set([x.strip() for x in df_nuts2_labels[column_name] if len(x.strip()) == 4])

        # fill efficiency
        for _, row in df_efficiency.iterrows():
            self.efficiency[row["Energy carrier"]] = \
                dc.EH(row["Electricity production [-]"], row["Heat production [-]"])
            self.efficiency_hh[row["Energy carrier HH"]] = \
                dc.EH(row["Electricity production [-]"], row["Heat production [-]"])

        for country_name in ctrl.general_settings.active_countries:
            # fill abbreviations class for easy access from anywhere
            alpha2 = df_abbr[df_abbr["Country_en"] == country_name].get("alpha-2").iloc[0]
            german_name = df_abbr[df_abbr["Country_en"] == country_name].get("Country_de").iloc[0]
            alpha3 = df_abbr[df_abbr["Country_en"] == country_name].get("alpha-3").iloc[0]
            Abbreviations.dict_alpha2_en_map[alpha2] = country_name
            Abbreviations.dict_de_en_map[german_name] = country_name
            Abbreviations.dict_en_alpha2_map[country_name] = alpha2

            # read gdp historical
            years = df_gdp_his.columns[3:]
            gdp_data = df_gdp_his[df_gdp_his["Country Code"] == alpha3].iloc[0][3:]
            zipped = list(zip(years, gdp_data))
            gdp_his = uty.filter_out_nan_and_inf(zipped)

            # read gdp prognosis
            interval_conv = lambda xs: [dc.Interval(int(x.split('-')[0]), int(x.split('-')[1])) for x in xs]
            intervals_europa = interval_conv(df_gdp_prog_europa.columns[1:-1])
            intervals_world = interval_conv(df_gdp_prog_world.columns[1:-1])

            zipped_gdp_prog: list[dc.Interval, float]
            if country_name in list(df_gdp_prog_europa["Country"]):
                gdp_prog = df_gdp_prog_europa[df_gdp_prog_europa["Country"] == country_name].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_europa, gdp_prog))
            elif country_name in list(df_gdp_prog_world["Country"]):
                gdp_prog = df_gdp_prog_world[df_gdp_prog_world["Country"] == country_name].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_world, gdp_prog))
            else:
                warnings.warn("Attention! For country \"" + country_name
                              + "\" no gdp prognosis data was found. Data from \"all\" is used instead now.")
                gdp_prog = df_gdp_prog_europa[df_gdp_prog_europa["Country"] == "all"].iloc[0][1:-1]
                zipped_gdp_prog = list(zip(intervals_europa, gdp_prog))

            self.gdp[country_name] = dc.HisProg(gdp_his, zipped_gdp_prog)

        # create PopulationData object
        self.population = PopulationInput(ctrl, self.nuts2_valid_regions, self.abbreviations,
                                          df_world_pop_his, df_world_pop_prog, df_nuts2_pop_his,
                                          df_nuts2_pop_prog)


