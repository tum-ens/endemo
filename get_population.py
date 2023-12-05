###############################################################################                                                                                   
# Data loader for population Forecast Nuts2-Level
###############################################################################
"""The module predicts the population development.

Script to determine the population data for a desired year to generate data 
for an energy demand model.
"""
###############################################################################
#Imports
###############################################################################

import os
import numpy as np
import pandas as pd
from openpyxl import load_workbook
import xlrd
import logging
import xlsxwriter 
from xlrd import open_workbook
import load_excel

logger = logging.getLogger(__name__)
level = logging.DEBUG
#level = logging.Warning
logging.basicConfig(level=level)

def __open_sheet(sheet_name, ignored_countries, nuts_code, population_current, population_projections, 
     new_nuts_code_name, space, german_states, germany_regions, PROGNOS_YEAR, FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR, NUTS2_CLASSIFICATION):
    #try:
        # Non EU countries are not considered,
        # Norway is somehow not in the list either nor Liechtenstein, Iceland or Switzerland
        # for Germany exist extra data processing therefore this country is also not in the list
    exist_ignored_countries = sheet_name in ignored_countries
    if exist_ignored_countries == False:

        country_code = sheet_name

        if country_code == "EL":
            sheet_name = "GR"
           
        col_name = "Code " + NUTS2_CLASSIFICATION
     
        #Get full sheet with new input values
        for row in range(0, len(nuts_code[col_name])):
            #Some cases in Nuts2 are special cases, there characterized by zero
            if country_code in nuts_code[col_name][row][0:2] and nuts_code["Model"][row] == 'x':
               #logger.warning('The nuts level (new name) ' + nuts_code[col_name][row]  + ' (' + country_code + ')' + ' is not considered!')
               pass

            elif country_code in nuts_code[col_name][row][0:2] and nuts_code["Model"][row] == '!':                 
               #logger.warning('Look at the nuts level (new name) ' + nuts_code[col_name][row] + ' (' + country_code + ')' + ' separately!')
               pass
  
            elif (country_code in nuts_code[col_name][row][0:2] and nuts_code[col_name][row] != '!'):
               
                #Calculation of the absolute proportions of the nuts levels in the capacity 
                #distribution of individual energy sources in a country using the population 
                #distribution and development
                for row_country_pop in range(0, len(population_current)):
                    if nuts_code[col_name][row] in population_current[:][row_country_pop][0]:
                        temp_nuts = population_current[:][row_country_pop][31]
                        population_current_temp_nuts  = float(temp_nuts.split("\n")[0])
                        number_years = PROGNOS_YEAR - 2019  #Change Date here!!!!!!!!!!!!!!!!!!!!!!!
 
                        if population_current_temp_nuts == 0:
                            temp_nuts = population_current[:][row_country_pop][29]
                            population_current_temp_nuts  = float(temp_nuts.split("\n")[0])
                            number_years = PROGNOS_YEAR - 2017 #Change Date here!!!!!!!!!!!!!!!!!!!!!
                                
                        #population projections per year
                        for row_nuts_proj in range(0, len(population_projections["Code"])):
                            if nuts_code[col_name][row] in population_projections["Code"][row_nuts_proj]: #if nuts_code[0][row] in population_projections[:][row_nuts_proj][0]:
                                temp_projection_nuts = (float(population_projections["per Year"][row_nuts_proj])) #temp_projection_nuts = (float(population_projections[:][row_nuts_proj][2]))
                               
                                #population in calculated year
                                population_calculated_year = population_current_temp_nuts*((1+(temp_projection_nuts/100))**number_years)
                                is_global = "data_population_temp" in locals()
                                if is_global == False:
                                   data_population_temp = pd.DataFrame([[nuts_code[col_name][row], population_calculated_year]])
  
                                else:
                                   data_population_temp = pd.DataFrame([[nuts_code[col_name][row], population_calculated_year]], \
                                     ).append(data_population_temp, ignore_index=True)
  
                                data_population_table = data_population_temp
                            
                                #print(str(nuts_code[col_name][row]) + "," + str(population_calculated_year))

            else: 
                pass

        if 'data_population_table' in locals():
            #Form the sum of the forecast Nuts2 data for a country here
            total_population_country_calculated_year = 0
            for sum_population in range(0,len(data_population_temp)):
                total_population_country_temp = data_population_temp[1][sum_population]
                total_population_country_calculated_year = total_population_country_calculated_year + total_population_country_temp

            data_total_population = pd.DataFrame([[country_code, total_population_country_calculated_year]])
            data_population_germany = []

        if 'data_population_table' in locals() and country_code == "DE":

            data_population_germany = []

            for row_state in range(0, len(german_states)):

                total_population_country_calculated_year = 0

                for row_country_state in range(0, len(germany_regions)):

                    if germany_regions['Unnamed: 0'][row_country_state] == german_states[row_state]:
                       
                       for sum_population in range(0,len(data_population_temp)):

                           if germany_regions['Unnamed: 3'][row_country_state] == data_population_temp[0][sum_population]:

                              total_population_country_temp = data_population_temp[1][sum_population]
                              total_population_country_calculated_year = total_population_country_calculated_year + total_population_country_temp

                is_global = "data_population_germany" in locals()
                if is_global == False:
                   data_population_germany = pd.DataFrame([[german_states[row_state], total_population_country_calculated_year]])
                else: 
                   data_population_germany = pd.DataFrame([[german_states[row_state], total_population_country_calculated_year]], \
                     ).append(data_population_germany, ignore_index=True)
                
                #print(str(german_states[row_state]) + "," + str(total_population_country_calculated_year))

        if 'data_population_table' in locals():
            pass
        else:
            data_population_table = []
            data_total_population = []
            data_population_germany = []

        return data_population_table, data_total_population, data_population_germany

    else: 
        logger.warning(space)
        logger.warning("Sheet " + sheet_name + " not loaded (non EU country/ Germany)!")
        data_population_table =  []
        data_total_population = []
        data_population_germany = []
        return data_population_table, data_total_population, data_population_germany
        
    # except:
    #    logger.warning(space)
    #    logger.warning("Sheet " + sheet_name + " not loaded!")
    #    data_population_table = []
    #    data_total_population = []
    #    data_population_germany = []
    #    return data_population_table, data_total_population, data_population_germany

def __open_sheets(sheet_names, ignored_countries, nuts_code, population_current, 
     population_projections, new_nuts_code_name, space, german_states, germany_regions, PROGNOS_YEAR, FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR, NUTS2_CLASSIFICATION):
    
    for sheet_name in sheet_names:
        data_population_table, data_total_population, data_population_germany = __open_sheet(sheet_name, ignored_countries, nuts_code, population_current,
           population_projections, new_nuts_code_name, space, german_states, germany_regions, PROGNOS_YEAR, FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR, NUTS2_CLASSIFICATION)
        if len(data_population_table) > 0:

           if 'data_population' in locals():          
              data_population = data_population.append(data_population_table, ignore_index=True)
              data_total_population_countries = data_total_population_countries.append(data_total_population, ignore_index=True)
           else:
              data_population = data_population_table
              data_total_population_countries = data_total_population
              
           if 'data_population' in locals() and sheet_name =="DE":          
              #data_population = data_population.append(data_population_table, ignore_index=True)
              data_total_german_population_states = (data_population_germany)
   
        else: 
            pass 

    return data_population, data_total_population_countries, data_total_german_population_states

def load_abbreviations(file_path, file_name, space):
    """Opens csv-file with abbreviation list.

    Returns list with abbreviations.
    """
    csv_file = []
    path = os.path.join(file_path, file_name)
    content = open(path, "r")

    for line in content:
        csv_file.append(line.split(",")[0])
    content.close()
    csv_file = sorted(csv_file[1:])
    logger.info(space)
    logger.info("Loaded abbreviations: " + str(csv_file))
    return csv_file

def load_csv_file(file_path, file_name):
    """Opens csv-file with list.

    Returns list.
    """
    csv_file = []
    path = os.path.join(file_path, file_name)
    content = open(path, "r")
    
    for line in content:
        csv_file.append(line.split(","))
    content.close()
    csv_file = sorted(csv_file[1:])
    return csv_file

def load_scenario(path, sheet_names, ignored_countries, nuts_code, population_current, population_projections, new_nuts_code_name, space, german_states, germany_regions, PROGNOS_YEAR, FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR, NUTS2_CLASSIFICATION):
    data_population, data_total_population_countries, data_total_german_population_states = __open_sheets(sheet_names, ignored_countries, nuts_code, 
      population_current, population_projections, new_nuts_code_name, space, german_states, germany_regions, PROGNOS_YEAR, FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR, NUTS2_CLASSIFICATION)
    return data_population, data_total_population_countries, data_total_german_population_states

def load_Nuts_code(filepath, filename):
    path = os.path.join(filepath, filename)
    nuts_code = pd.read_excel(path, sheet_name='Sheet',skiprows=0)
    #sheet = sheet.rename({0: "Type", 1: "Data"}, axis='columns')
    return nuts_code   

def load_german_regions(filepath, filename):
    path = os.path.join(filepath, filename)
    german_regions = pd.read_excel(path, sheet_name='Regionen', skiprows=None, nrows=None)
    return german_regions

def load_population(ctrl, file):

    #Activated new Nuts2 level code = 1
    #Deactivated new Nuts2 level code = 0
    new_nuts_code_name_use = 0

    space = "-"*79

    file_path = file.FILE_PATH_INPUT_DATA_POPULATION 
    file_path_out_file = file.FILE_PATH_OUTPUT_DATA

    file_name_abbrevitations = file.FILENAME_INPUT_ABBREVIATIONS
    file_name_nuts_code = file.FILENAME_INPUT_NUTS_CODE
    filename_population_current_nuts = file.FILENAME_INPUT_POPULATION_CURRENT_NUTS
    filename_population_projections = file.FILENAME_INPUT_POPULATION_PROJECTIONS
    excel_name_german_population = file.FILENAME_INPUT_CAPACITIES

    logger.info(space)
    logger.info("Run: " + __file__)

    abbreviations = load_abbreviations(file.FILE_PATH_INPUT_DATA_GENERAL, file_name_abbrevitations, space)

    nuts_code = load_Nuts_code(file_path, file_name_nuts_code)

    population_current = load_csv_file(file_path, filename_population_current_nuts)

    population_projections = pd.read_excel(os.path.join(file_path, filename_population_projections),
                                      sheet_name=['Populationprojection_Nuts2_'+str(ctrl.NUTS2_CLASSIFICATION)],skiprows=0)['Populationprojection_Nuts2_'+str(ctrl.NUTS2_CLASSIFICATION)]

    germany_regions = load_german_regions(file_path, excel_name_german_population)

    data_population, data_total_population_countries, data_total_german_population_states = load_scenario(file_path, abbreviations, ctrl.IGNORED_COUNTRIES, nuts_code, 
     population_current, population_projections, new_nuts_code_name_use, space, ctrl.GERMAN_STATES, germany_regions, ctrl.FORECAST_YEAR, file.FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR, ctrl.NUTS2_CLASSIFICATION)

    data_population = data_population.rename({0:"Nuts_2", 1:"Population Prog Year [Pers.]"}, axis='columns')
    data_total_population_countries = data_total_population_countries.rename({0:"Country", 1:"Population Prog Year [Pers.]"}, axis='columns')
    data_total_german_population_states = data_total_german_population_states.rename({0:"Federal state", 1:"Population Prog year [Pers.]"}, axis='columns')
    
    path = os.path.join(file_path_out_file, file.FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR)
    data = {'Population_NUTS2': data_population, 'Population_Countries': data_total_population_countries, 'Population_German_States': data_total_german_population_states}
    with pd.ExcelWriter(path) as ew: 

      for sheet_name in data.keys():
          data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

    #logger.info(space)
    #logger.info("Population data load finished.")
    #logger.info(space) 

class POPULATION():

    def __init__(self, CTRL, FILE):

        load_population(CTRL, FILE)

        self.pop_forecast_nuts2 = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, 
            FILE.FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR, 'Population_NUTS2')
        self.pop_forecast_total_country = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, 
            FILE.FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR,'Population_Countries')
        self.pop_forecast = pd.read_excel(FILE.FILE_PATH_OUTPUT_DATA+"\\"+
            FILE.FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR,sheet_name=
            ["Population_Countries"],skiprows=0)["Population_Countries"]

        self.pop_historical = pop_book = open_workbook(FILE.FILE_PATH_INPUT_DATA_POPULATION+"\\"+
            FILE.FILENAME_INPUT_POPULATION_HISTORICAL,on_demand=True)
        self.pop_historical_data = self.pop_historical.sheet_by_name("Data")         