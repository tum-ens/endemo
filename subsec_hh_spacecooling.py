###############################################################################                                                                                   
# Forecast of the subsector space cooling for households
###############################################################################
"""The module calculates the energy demand of the subsector space cooling for 
households.
"""
###############################################################################
#Imports
###############################################################################

import load_excel
import logging
import pandas as pd
import math
import subsec_hh_sources

def spacecooling(CTRL, FILE, hh_data, gen_data):

    energy_demand_hisvalue = []

    for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

        FILENAME_SOURCES = CTRL.CONSIDERED_COUNTRIES[country] + "_2018.xlsm"
        sources_percent_per_country = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, FILENAME_SOURCES, '1b_SpaceCooling')

        #get the ratio for the sources of water heating per country
        sources_rel_stop_year_cooling, sources_prog_value_cooling = subsec_hh_sources.load_sources_values_private_household(CTRL.CONSIDERED_COUNTRIES, country, CTRL.FORECAST_YEAR, 
            sources_percent_per_country)

        #get the consumption per main sector for private households
        energy_cooling_countries_temp, sum_stop_year = subsec_hh_sources.load_sector_data_countries(CTRL, CTRL.CONSIDERED_COUNTRIES, country, CTRL.FORECAST_YEAR, sources_percent_per_country)

        if country == 0:
            energy_cooling_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (energy_cooling_countries_temp)]]) # unit TJ

            for sources_per_country in range(0, len(sources_prog_value_cooling)):

                if sources_per_country == 0:
                    sources_per_country_table_cooling = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_cooling[1][sources_per_country], ((sources_prog_value_cooling[2][sources_per_country]/100)*energy_cooling_countries_temp)]]) # unit TJ single sources
                else: 
                    sources_per_country_table_cooling = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_cooling[1][sources_per_country], ((sources_prog_value_cooling[2][sources_per_country]/100)*energy_cooling_countries_temp)]], \
                        ).append(sources_per_country_table_cooling, ignore_index=True)  

        else: #unit TJ
            energy_cooling_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (energy_cooling_countries_temp)]], \
                ).append(energy_cooling_countries, ignore_index=True) 

            for sources_per_country in range(0, len(sources_prog_value_cooling)):
                sources_per_country_table_cooling = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_cooling[1][sources_per_country], ((sources_prog_value_cooling[2][sources_per_country]/100)*energy_cooling_countries_temp)]], \
                    ).append(sources_per_country_table_cooling, ignore_index=True) # unit TJ single sources

        energy_demand_hisvalue = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sum_stop_year*0.000277777777778]], \
            ).append(energy_demand_hisvalue, ignore_index=True)

    hh_sc = SPACE_COOLING(energy_cooling_countries, sources_per_country_table_cooling, energy_demand_hisvalue)

    return hh_sc

class SPACE_COOLING():

    def __init__(self, energy_cooling_countries, sources_per_country_table_cooling, energy_demand_hisvalue):

        self.energy_cooling_countries = energy_cooling_countries.rename({0:"Country", 1:"Consumption Prog Year [TJ]"}, axis='columns')
        self.sources_per_country_table_cooling = sources_per_country_table_cooling.rename({0:"Country", 1:"Source", 3:"Consumption Prog Year [TJ]"}, axis='columns')
        self.energy_demand_hisvalue = energy_demand_hisvalue.rename({0:"Country", 1:"Consumption Prog Year [TWh]"}, axis='columns')