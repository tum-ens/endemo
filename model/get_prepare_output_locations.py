###############################################################################                                                                                   
# Filepath and Filenames
###############################################################################
"""The module initiates the filepath and filenames of the data sets.

"""
###############################################################################
#Imports
###############################################################################
import os
from datetime import datetime
import shutil


class LOCATIONS():

    
    def __init__(self, FILE_PATH, forecast_year, ind_volume_prognos, logger):

        # Define input and output file structure
        self.FILE_PATH_INPUT_DATA = os.path.join(
            FILE_PATH, "input") 
        self.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES = os.path.join(
            self.FILE_PATH_INPUT_DATA, "commercial_trade_and_services") 
        self.FILE_PATH_INPUT_DATA_HOUSEHOLDS = os.path.join(
            self.FILE_PATH_INPUT_DATA, "households")
        self.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES = os.path.join(
            self.FILE_PATH_INPUT_DATA_HOUSEHOLDS, "energy_consumption_households")   
        self.FILE_PATH_INPUT_DATA_INDUSTRY = os.path.join(
            self.FILE_PATH_INPUT_DATA, "industry")
        self.FILE_PATH_INPUT_DATA_TRAFFIC = os.path.join(
            self.FILE_PATH_INPUT_DATA, "traffic")
        self.FILE_PATH_INPUT_DATA_GENERAL = os.path.join(
            self.FILE_PATH_INPUT_DATA, "general")
        self.FILE_PATH_SOURCES = os.path.join(
            self.FILE_PATH_INPUT_DATA, "energy_consumption_households")

        self.FILE_PATH_OUTPUT_DATA = os.path.join(
            FILE_PATH, "results" + os.sep + "results_" + str(forecast_year) + "_" + datetime.now().strftime('%Y_%m_%d') )
        # datetime.now().strftime('%Y_%m_%d__%H_%M')
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA)
            # copy input file in the result folder
        else:
            logger.warning("Folder" + " _results_ " + "already exist!")
        shutil.copyfile(os.path.join(self.FILE_PATH_INPUT_DATA, "Set_and_Control_Parameters.xlsx"), os.path.join(self.FILE_PATH_OUTPUT_DATA, "Set_and_Control_Parameters.xlsx"))
            
        self.FILE_PATH_OUTPUT_DATA_INDUSTRY = os.path.join(
            self.FILE_PATH_OUTPUT_DATA, "Industrial_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_INDUSTRY):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_INDUSTRY)
        else:
            logger.warning("Folder" + " _Industrial_ " + "already exist!")
        self.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL = os.path.join(self.FILE_PATH_OUTPUT_DATA_INDUSTRY, "Graphical_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL)
        
        self.FILE_PATH_OUTPUT_DATA_CTS = os.path.join(
            self.FILE_PATH_OUTPUT_DATA, "CTS_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_CTS):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_CTS)
        else:
            logger.warning("Folder" + " _Commertial, trade and services_ " + "already exist!")

        self.FILE_PATH_OUTPUT_DATA_TRAFFIC = os.path.join(
            self.FILE_PATH_OUTPUT_DATA, "Traffic_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_TRAFFIC):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_TRAFFIC)
        else:
            logger.warning("Folder" + " _Traffic_ " + "already exist!")
        
        self.FILE_PATH_OUTPUT_DATA_HOUSEHOLD = os.path.join(
            self.FILE_PATH_OUTPUT_DATA, "Household_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_HOUSEHOLD):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_HOUSEHOLD)
        else:
            logger.warning("Folder" + " _Traffic_ " + "already exist!")
            
        
        # Define output file names
        self.FILENAME_OUTPUT_POPULATION = "Population_NUTS2_Country.xlsx"
        self.FILENAME_OUTPUT_GDP = "GDP_Projections_"+str(forecast_year)+".xlsx"
        
        self.FILENAME_OUTPUT_DEMAND = "_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_DEMAND_NUTS2 = "_energy_demand_NUTS2_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_DEMAND_IND = "IND_energy_demand_" + str(forecast_year) + "_"+ ind_volume_prognos +".xlsx"
        self.FILENAME_OUTPUT_DEMAND_IND_NUTS2 = "IND_energy_demand_NUTS2_" + str(forecast_year) + "_"+ ind_volume_prognos +".xlsx"
        
        self.FILENAME_OUTPUT_DEMAND_TOTAL = 'Energy_demand_'+str(forecast_year)
        self.FILENAME_OUTPUT_DEMAND_TOTAL_NUTS2 = 'Energy_demand_NUTS2_'+str(forecast_year)+'.csv'
        
        self.FILENAME_OUTPUT_TIMESERIES = '_energy_demand_timeseries_'+str(forecast_year)+'.xlsx'
        self.FILENAME_OUTPUT_TIMESERIES_TRA_PKM_TKM = "TRA_pkm_tkm_demand_timeseries"+str(forecast_year) + ".xlsx"
        
        self.FILENAME_OUTPUT_CHARACTERISTICS_HOUSEHOLDS = 'HH_household_characteristics.xlsx'
        self.FILENAME_OUTPUT_ENERGYDEMAND_HIS_HOUSEHOLDS = 'HH_subsectors_energy_demand_2018_his.xlsx'
        self.FILENAME_OUTPUT_DEMAND_HOUSEHOLD_SUBSECTORS = "HH_subsectors_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_HH_DEMAND_SUBSECTORS_NUTS2 = 'HH_energy_demand_NUTS2_subsector_'+str(forecast_year)+'.xlsx'
        
        self.FILENAME_OUTPUT_KILOMETERS_TRAFFIC = "TRA_traffickilometers_" + str(forecast_year) + ".xlsx" # front page
        self.FILENAME_OUTPUT_DEMAND_PERSONTRAFFIC = "TRA_persontraffic_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_MODALSPLIT_TRAFFIC = "TRA_modalsplit_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_DEMAND_FREIGHTTRAFFIC = "TRA_freighttraffic_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_PRODUCTION_VOLUME_TOTAL = "TRA_production_volume.xlsx" 
        
        self.FILENAME_OUTPUT_CTS_EMPLOYEE = 'CTS_employee_number.xlsx'
        self.FILENAME_OUTPUT_CTS_EMPL_COEF = 'CTS_employee_coeff.xlsx'
        
        self.FILENAME_OUTPUT_IND_VOLUME_FORECAST = "IND_prod_quantity_" + str(forecast_year) + "_"+ ind_volume_prognos +".xlsx" # front page
        self.FILENAME_OUTPUT_IND_VOLUME_KOEF = "Prod_quantity_coeff_"+ind_volume_prognos+".xlsx"
