###############################################################################                                                                                   
# Forecast of the subsector lighting and electrical appliances for households
###############################################################################
"""The module calculates the energy demand of the subsector lighting and 
electrical appliances for households.
"""
###############################################################################
#Imports
###############################################################################

import load_excel
import logging
import pandas as pd
import math
import subsec_hh_sources

def lighting(CTRL, FILE, hh_data, gen_data):

    energy_demand_hisvalue = []

    #eletrical demand (e.g. light, appliances)
    for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

        FILENAME_SOURCES = CTRL.CONSIDERED_COUNTRIES[country] + "_2018.xlsm"
        sources_percent_per_country = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, FILENAME_SOURCES,'1e_LightingAndAppliances') 

        if (CTRL.CONSIDERED_COUNTRIES[country] == 'Belgium' or CTRL.CONSIDERED_COUNTRIES[country] == 'Cyprus' or CTRL.CONSIDERED_COUNTRIES[country] == 'Czechia'
                or CTRL.CONSIDERED_COUNTRIES[country] == 'Denmark' or CTRL.CONSIDERED_COUNTRIES[country] == 'Finland' or CTRL.CONSIDERED_COUNTRIES[country] == 'Georgia'
                or CTRL.CONSIDERED_COUNTRIES[country] == 'Greece'or CTRL.CONSIDERED_COUNTRIES[country] == 'Hungary'or CTRL.CONSIDERED_COUNTRIES[country] == 'Ireland'
                or CTRL.CONSIDERED_COUNTRIES[country] == 'Italy' or CTRL.CONSIDERED_COUNTRIES[country] == 'Lithuania' or CTRL.CONSIDERED_COUNTRIES[country] == 'Malta'
                or CTRL.CONSIDERED_COUNTRIES[country] == 'Poland' or CTRL.CONSIDERED_COUNTRIES[country] == 'Romania'
                or CTRL.CONSIDERED_COUNTRIES[country] == 'Sweden' or CTRL.CONSIDERED_COUNTRIES[country] == 'Slovakia'):
            row_start = 'Unnamed: 9'
            year_start = 2016 #higher than 2010
            row_stop = 'Unnamed: 11'
            year_stop = 2018
        else: 
            row_start = 'Unnamed: 3'
            year_start = 2010
            row_stop = 'Unnamed: 11'
            year_stop = 2018

        if math.isnan(sources_percent_per_country[row_start][4]) == True:
            sources_percent_start = 0
        else: 
            sources_percent_start = sources_percent_per_country[row_start][4]
                
        if math.isnan(sources_percent_per_country[row_stop][4]) == True:
            sources_percent_stop = 0
        else: 
            sources_percent_stop = sources_percent_per_country[row_stop][4]

        calculation_factor = 3.6
        sources_start_year = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (sources_percent_start*calculation_factor)]]) # unit TJ
        sources_stop_year = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (sources_percent_stop*calculation_factor)]]) # unit TJ

        # prognose rate 
        if year_start == 2010 and CTRL.HH_METHOD_REST == "trend":
            prog_rate_temp = (((((sources_percent_stop*calculation_factor)/(sources_percent_start*calculation_factor))**(1/(year_stop-year_start))))-1)*100  # unit %/a
            sources_prog_value_electricity = (sources_percent_stop*calculation_factor)*((1+(prog_rate_temp/100))**(CTRL.FORECAST_YEAR-year_stop)) #unit TJ

        else: 
            prog_rate_temp = 0
            sources_prog_value_electricity = (sources_percent_stop*calculation_factor) #unit TJ

        if country == 0:
            energy_electricity_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (sources_prog_value_electricity)]]) # unit TJ

        else: #unit TJ
            energy_electricity_countries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], (sources_prog_value_electricity)]], \
                ).append(energy_electricity_countries, ignore_index=True) 
        
        energy_demand_hisvalue = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], sources_percent_stop*0.001]], \
            ).append(energy_demand_hisvalue, ignore_index=True)

    hh_liandap = LIGHTING(energy_electricity_countries, energy_demand_hisvalue)

    return hh_liandap

class LIGHTING():

    def __init__(self, energy_electricity_countries, energy_demand_hisvalue):

        self.energy_electricity_countries = energy_electricity_countries.rename({0:"Country", 1:"Consumption Prog Year [TJ]"}, axis='columns')
        self.energy_demand_hisvalue = energy_demand_hisvalue.rename({0:"Country", 1:"Consumption Prog Year [TWh]"}, axis='columns')