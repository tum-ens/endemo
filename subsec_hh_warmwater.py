###############################################################################                                                                                   
# Forecast of the subsector warm water for households
###############################################################################
"""The module calculates the energy demand of the subsector warm heating for 
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

def warmwater(CTRL, FILE, hh_data, gen_data):

    #Warm water: m^3/E*d  * kWh/m^3  * %source
    energy_demand_hisvalue = []

    for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

        FILENAME_SOURCES = CTRL.CONSIDERED_COUNTRIES[country] + "_2018.xlsm"
        sources_percent_per_country = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, FILENAME_SOURCES, '1c_WaterHeating')

        #get the ratio for the sources of water heating per country
        sources_rel_stop_year_water_heating, sources_prog_value_water_heating = subsec_hh_sources.load_sources_values_private_household(CTRL.CONSIDERED_COUNTRIES, country, CTRL.FORECAST_YEAR, 
           sources_percent_per_country)
        
        temp, sum_stop_year = subsec_hh_sources.load_sector_data_countries(CTRL, CTRL.CONSIDERED_COUNTRIES, country, CTRL.FORECAST_YEAR, sources_percent_per_country)

        for demand_per_pers in range(0, len(hh_data.demand_per_person)):

            if CTRL.CONSIDERED_COUNTRIES[country] == hh_data.demand_per_person["country_en"][demand_per_pers]: 

                for abbreviation in range(0, len(gen_data.gen_abbreviations)):

                    if CTRL.CONSIDERED_COUNTRIES[country] == gen_data.gen_abbreviations["Country"][abbreviation]:

                        for population_prognos_total in range(0, len(gen_data.pop.pop_forecast_total_country)):

                            if gen_data.pop.pop_forecast_total_country["Country"][population_prognos_total] == gen_data.gen_abbreviations["Internationale Abkuerzung"][abbreviation]:

                                energy_warm_water_country = (hh_data.demand_per_person["dem_per_pers"][demand_per_pers]*(10**-3)*365*gen_data.pop.pop_forecast_total_country["Population Prog Year [Pers.]"][population_prognos_total]*
                                    hh_data.techn_data["data"][0]*(hh_data.techn_data["data"][2] - hh_data.techn_data["data"][1])) #365 d/a
                                                
                                if country == 0:
                                    energy_warm_water_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (energy_warm_water_country/277778)]]) # unit TJ
                                    
                                    for sources_per_country in range(0, len(sources_prog_value_water_heating)):

                                        if sources_per_country == 0:
                                            sources_per_country_table_water_heating = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_water_heating[1][sources_per_country], ((sources_prog_value_water_heating[2][sources_per_country])/100*(energy_warm_water_country/277778))]]) # unit TJ single sources
                                        else: 
                                            sources_per_country_table_water_heating = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_water_heating[1][sources_per_country], ((sources_prog_value_water_heating[2][sources_per_country])/100*(energy_warm_water_country/277778))]], \
                                                ).append(sources_per_country_table_water_heating, ignore_index=True)                                
                                else:
                                    energy_warm_water_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (energy_warm_water_country/277778)]], \
                                        ).append(energy_warm_water_countries, ignore_index=True)    #unit TJ

                                    for sources_per_country in range(0, len(sources_prog_value_water_heating)):
                                        sources_per_country_table_water_heating = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_prog_value_water_heating[1][sources_per_country], ((sources_prog_value_water_heating[2][sources_per_country]/100)*(energy_warm_water_country/277778))]], \
                                            ).append(sources_per_country_table_water_heating, ignore_index=True) # unit TJ single sources

        energy_demand_hisvalue = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sum_stop_year*0.000277777777778]], \
            ).append(energy_demand_hisvalue, ignore_index=True)

    hh_ww = WARM_WATER(energy_warm_water_countries, sources_per_country_table_water_heating, energy_demand_hisvalue)

    return hh_ww

class WARM_WATER():

    def __init__(self, energy_warm_water_countries, sources_per_country_table_water_heating, energy_demand_hisvalue):

        self.energy_warm_water_countries = energy_warm_water_countries.rename({0:"Country", 1:"Consumption Prog Year [TJ]"}, axis='columns')
        self.sources_per_country_table_water_heating = sources_per_country_table_water_heating.rename({0:"Country", 1:"Source", 3:"Consumption Prog Year [TJ]"}, axis='columns')
        self.energy_demand_hisvalue = energy_demand_hisvalue.rename({0:"Country", 1:"Consumption Prog Year [TWh]"}, axis='columns')