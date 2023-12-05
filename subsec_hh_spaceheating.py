###############################################################################                                                                                   
# Forecast of the subsector space heating for households
###############################################################################
"""The module calculates the energy demand of the subsector space heating for 
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

def spaceheating(CTRL, FILE, hh_data, gen_data):

    #Space heating: m^2/household / Pers/household  * Population * kWh/m^2 * %sources
    table_area_prog_country = []
    table_specific_energy_use_prog_country = []
    table_person_prog_country = []
    table_total_area_country = []
    energy_demand_hisvalue = []

    # general without source sectors
    for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

        FILENAME_SOURCES = CTRL.CONSIDERED_COUNTRIES[country] + "_2018.xlsm"
        sources_percent_per_country = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, FILENAME_SOURCES,'1a_SpaceHeating')

        #get the ratio for the sources of space heating per country
        sources_rel_stop_year_space_heating, sources_prog_value_space_heating = subsec_hh_sources.load_sources_values_private_household(CTRL.CONSIDERED_COUNTRIES, country, 
            CTRL.FORECAST_YEAR, sources_percent_per_country)

        temp, sum_stop_year = subsec_hh_sources.load_sector_data_countries(CTRL, CTRL.CONSIDERED_COUNTRIES, country, CTRL.FORECAST_YEAR, sources_percent_per_country)

        for area in range(0, len(hh_data.area_per_household)):

            if CTRL.CONSIDERED_COUNTRIES[country] == hh_data.area_per_household["country_en"][area]:

                area_prog_country = hh_data.area_per_household[CTRL.FORECAST_YEAR][area]

                table_area_prog_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], area_prog_country]], \
                    ).append(table_area_prog_country, ignore_index=True) 

                for person in range(0, len(hh_data.person_per_household)):

                    if CTRL.CONSIDERED_COUNTRIES[country] == hh_data.person_per_household["country_en"][person]:

                        person_prog_country = hh_data.person_per_household[CTRL.FORECAST_YEAR][person]
                        
                        table_person_prog_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], person_prog_country]], \
                            ).append(table_person_prog_country, ignore_index=True) 

                        for specific_energy in range(0, len(hh_data.specific_energy_use)):

                            if CTRL.CONSIDERED_COUNTRIES[country] == hh_data.specific_energy_use["country_en"][specific_energy]:

                                if CTRL.CONSIDERED_COUNTRIES[country] == "Germany":                                    
                                    specific_energy_use_prog_country = (hh_data.specific_energy_use["y_2015"][specific_energy]*((1+(hh_data.specific_energy_use["trend"][specific_energy]/100))**(CTRL.FORECAST_YEAR-2015)))  # unit kWh
                                    
                                    table_specific_energy_use_prog_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], specific_energy_use_prog_country]], \
                                        ).append(table_specific_energy_use_prog_country, ignore_index=True)                                
                                else:

                                    if hh_data.specific_energy_use["trend"][specific_energy] == 0:
                                        specific_energy_use_prog_country = hh_data.specific_energy_use["y_2012"][specific_energy]
                                    else: 
                                        specific_energy_use_prog_country = (hh_data.specific_energy_use["y_2000"][specific_energy]*((1+(hh_data.specific_energy_use["trend"][specific_energy]/100))**(CTRL.FORECAST_YEAR-2012)))  #unit kWh
                                    
                                    table_specific_energy_use_prog_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], specific_energy_use_prog_country]], \
                                        ).append(table_specific_energy_use_prog_country, ignore_index=True)

                                for abbreviation in range(0, len(gen_data.gen_abbreviations)):

                                    if CTRL.CONSIDERED_COUNTRIES[country] == gen_data.gen_abbreviations["Country"][abbreviation]:

                                        #if CTRL.CONSIDERED_COUNTRIES[country] == "Bosnia and Herzegovina":
                                            #print("B+H")

                                        for population_prognos_total in range(0, len(gen_data.pop.pop_forecast_total_country)):

                                            if gen_data.pop.pop_forecast_total_country["Country"][population_prognos_total] == gen_data.gen_abbreviations["Internationale Abkuerzung"][abbreviation]:

                                                energy_space_heating_country = (area_prog_country/person_prog_country)*gen_data.pop.pop_forecast_total_country["Population Prog Year [Pers.]"][population_prognos_total]*specific_energy_use_prog_country
                                                
                                                table_total_area_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (area_prog_country/person_prog_country)*gen_data.pop.pop_forecast_total_country["Population Prog Year [Pers.]"][population_prognos_total]]], \
                                                    ).append(table_total_area_country, ignore_index=True) 

                                                if country == 0:
                                                    energy_space_heating_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (energy_space_heating_country/277778)]]) # unit TJ # all sources

                                                    for sources_per_country in range(0, len(sources_prog_value_space_heating)):

                                                        if sources_per_country == 0: 
                                                            sources_per_country_table_space_heating = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_space_heating[1][sources_per_country], ((sources_prog_value_space_heating[2][sources_per_country]/100)*(energy_space_heating_country/277778))]]) # unit TJ single sources
                                                        else: 
                                                            sources_per_country_table_space_heating = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_space_heating[1][sources_per_country], ((sources_prog_value_space_heating[2][sources_per_country]/100)*(energy_space_heating_country/277778))]], \
                                                                ).append(sources_per_country_table_space_heating, ignore_index=True)

                                                else: #unit TJ
                                                    energy_space_heating_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (energy_space_heating_country/277778)]], \
                                                        ).append(energy_space_heating_countries, ignore_index=True)    # all sources

                                                    for sources_per_country in range(0, len(sources_prog_value_space_heating)):
                                                        sources_per_country_table_space_heating = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_space_heating[1][sources_per_country], ((sources_prog_value_space_heating[2][sources_per_country]/100)*(energy_space_heating_country/277778))]], \
                                                                ).append(sources_per_country_table_space_heating, ignore_index=True) # unit TJ single sources

        energy_demand_hisvalue = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sum_stop_year*0.000277777777778]], \
            ).append(energy_demand_hisvalue, ignore_index=True)

    hh_sh = SPACE_HEATING(energy_space_heating_countries, sources_per_country_table_space_heating, table_area_prog_country, 
        table_specific_energy_use_prog_country, table_person_prog_country, table_total_area_country, energy_demand_hisvalue)

    return hh_sh

class SPACE_HEATING():

    def __init__(self, energy_space_heating_countries, sources_per_country_table_space_heating, table_area_prog_country, table_specific_energy_use_prog_country, table_person_prog_country,
        table_total_area_country, energy_demand_hisvalue):

        self.energy_space_heating_countries = energy_space_heating_countries.rename({0:"Country", 1:"Consumption Prog Year [TJ]"}, axis='columns')
        self.sources_per_country_table_space_heating = sources_per_country_table_space_heating.rename({0:"Country", 1:"Source", 3:"Consumption Prog Year [TJ]"}, axis='columns')
        self.table_area_prog_country = table_area_prog_country.rename({0:"Country", 1:"Area per Household [m^2/Household]"}, axis='columns')
        self.table_specific_energy_use_prog_country = table_specific_energy_use_prog_country.rename({0:"Country", 1:"Specific energy consumption [kWh/m^2]"}, axis='columns')
        self.table_person_prog_country = table_person_prog_country.rename({0:"Country", 1:"Person per Household [Pers./Household]"}, axis='columns')
        self.table_total_area_country = table_total_area_country.rename({0:"Country", 1:"Living area total [m^2]"}, axis='columns')
        self.energy_demand_hisvalue = energy_demand_hisvalue.rename({0:"Country", 1:"Consumption Prog Year [TWh]"}, axis='columns')


