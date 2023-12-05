###############################################################################                                                                                   
# Filepath and Filenames
###############################################################################
"""The module initiates the filepath and filenames of the data sets.

"""
###############################################################################
#Imports
###############################################################################

import os

class LOCATIONS():

    def __init__(self, FILE_PATH_USER_SPECIFIC, forecast_year, logger):

        # Input and output file path.
        self.FILE_PATH_INPUT_DATA = os.path.join(FILE_PATH_USER_SPECIFIC, "endemo", "input") 
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
        self.FILE_PATH_INPUT_DATA_POPULATION = os.path.join(
            self.FILE_PATH_INPUT_DATA, "general")
        self.FILE_PATH_SOURCES = os.path.join(self.FILE_PATH_INPUT_DATA, "energy_consumption_households")

        self.FILE_PATH_OUTPUT_DATA = os.path.join(FILE_PATH_USER_SPECIFIC, "endemo", "results"+"_"+str(forecast_year))
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA)
        else:
            logger.warning("Folder" + " _results_ " + "already exist!")
            
        self.FILE_PATH_OUTPUT_DATA_INDUSTRY = os.path.join(FILE_PATH_USER_SPECIFIC, "endemo", "results"+"_"+str(forecast_year), "Industrial_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_INDUSTRY):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_INDUSTRY)
        else:
            logger.warning("Folder" + " _Industrial_ " + "already exist!")
        
        self.FILE_PATH_OUTPUT_DATA_CTS = os.path.join(FILE_PATH_USER_SPECIFIC, "endemo", "results"+"_"+str(forecast_year), "CTS_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_CTS):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_CTS)
        else:
            logger.warning("Folder" + " _Commertial, trade and services_ " + "already exist!")

        self.FILE_PATH_OUTPUT_DATA_TRAFFIC = os.path.join(FILE_PATH_USER_SPECIFIC, "endemo", "results"+"_"+str(forecast_year), "Traffic_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_TRAFFIC):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_TRAFFIC)
        else:
            logger.warning("Folder" + " _Traffic_ " + "already exist!")
        
        self.FILE_PATH_OUTPUT_DATA_HOUSEHOLD = os.path.join(FILE_PATH_USER_SPECIFIC, "endemo", "results"+"_"+str(forecast_year), "Household_output")
        if not os.path.exists(self.FILE_PATH_OUTPUT_DATA_HOUSEHOLD):
            os.makedirs(self.FILE_PATH_OUTPUT_DATA_HOUSEHOLD)
        else:
            logger.warning("Folder" + " _Traffic_ " + "already exist!")

        # Input and output filenames.
        # Inputs based on historical data which are used for the forecast.
        self.FILENAME_INPUT_POPULATION_HISTORICAL = "Population_historical.xls"
        self.FILENAME_INPUT_ABBREVIATIONS = "Abbreviations.csv"
        self.FILENAME_INPUT_GDP_FORECAST = "GDP_Forecast.xlsx"
        self.FILENAME_INPUT_NUTS_CODE = "NUTS2_from_Model.xlsx"
        self.FILENAME_INPUT_POPULATION_CURRENT_NUTS = "Population_current_nuts2_v2.csv"
        self.FILENAME_INPUT_POPULATION_PROJECTIONS = "Populationprojection_Nuts2.xlsx"
        self.FILENAME_INPUT_CAPACITIES = "Kapazitäten 2030-2050.xlsx"
        self.FILENAME_INPUT_GDP_wKKS = "GDP_wKKS.xls"
        self.FILENAME_INPUT_GDP_KKS = "GDP_KKS.xls"

        self.FILENAME_INPUT_SPACE_HEATING = "Space_Heating_OTH.xlsx" 
        self.FILENAME_INPUT_WARM_WATER = "Warm_Water.xlsx"
        self.FILENAME_INPUT_HOUSEHOLD_SOURCES = "Hh_energy_sources_set.xlsx"
        self.FILENAME_INPUT_HOUSEHOLD_TIMESERIES = "hh_timeseries.xlsx"

        self.FILENAME_INPUT_PERSON_TRAFFIC ="Persontraffic.xlsx"
        self.FILENAME_INPUT_FREIGHT_TRAFFIC ="Freighttraffic.xlsx"
        self.FILENAME_INPUT_PERSON_TRAFFIC_ELECTRICAL = "Pt_EnergySources_electrical.xlsx"
        self.FILENAME_INPUT_PERSON_TRAFFIC_HYDROGEN = "Pt_EnergySources_hydrogen.xlsx"
        self.FILENAME_INPUT_FREIGHT_TRAFFIC_ELECTRICAL = "Ft_EnergySources_electrical.xlsx"
        self.FILENAME_INPUT_FREIGHT_TRAFFIC_HYDROGEN = "Ft_EnergySources_hydrogen.xlsx"
        self.FILENAME_INPUT_PRODUCTION_VOLUME_HIS = "production_volume_his_flight_2018.xlsx"
        self.FILENAME_INPUT_TRAFFIC_TIMESERIES = "tra_timeseries.xlsx"
        self.FILENAME_INPUT_FREIGHT_TRAFFIC_REST = "rest_industry.xlsx"

        self.FILENAME_INPUT_STEEL_PRODUCTION = "Steel_Production.xlsx"
        self.FILENAME_INPUT_ALUMINUM_PRODUCTION = "Aluminum_Production.xlsx"
        self.FILENAME_INPUT_CEMENT_PRODUCTION = "Cement_Production.xlsx"
        self.FILENAME_INPUT_PAPER_PRODUCTION = "Paper_Production.xlsx"
        self.FILENAME_INPUT_AMMONIA_PRODUCTION = "Ammonia_Production.xls"
        self.FILENAME_INPUT_GLASS_PRODUCTION = "Glass_Production.xlsx"
        self.FILENAME_INPUT_SPECIFIC_CONSUMPTION = "Specific_Consumption.xlsx"

        self.FILENAME_OUTPUT_POPULATION_CALCULATED_YEAR = "Population_Nuts2_Country.xlsx"
        self.FILENAME_OUTPUT_DEMAND_HOUSEHOLDS = 'Demand_Households.xlsx'
        self.FILENAME_OUTPUT_CHARACTERISTICS_HOUSEHOLDS = 'Characteristics_Households.xlsx'
        self.FILENAME_OUTPUT_ENERGYDEMAND_HIS_HOUSEHOLDS = 'HH_energy_demand_2016_2018.xlsx'
        self.FILENAME_OUTPUT_DEMAND_HOUSEHOLD_SUBSECTORS = "HH_subsectors_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_DEMAND_PERSONTRAFFIC = "TRA_persontraffic_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_KILOMETERS_TRAFFIC = "TRA_traffickilometers_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_MODALSPLIT_TRAFFIC = "TRA_modalsplit_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_DEMAND_FREIGHTTRAFFIC = "TRA_freighttraffic_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_PRODUCTION_VOLUME_TOTAL = "TRA_production_volume.xlsx" 
        self.FILENAME_OUTPUT_DEMAND_TRAFFIC = "TRA_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_DEMAND_HOUSEHOLD = "HH_energy_demand_" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_TIMESERIES_TRAFFIC_RAIL = "TRA_traffic_timeseries_rail.xlsx"
        self.FILENAME_OUTPUT_ENERGY_DEMAND_TIMESERIES_ELEC = "TRA_energy_demand_timeseries_elec" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_ENERGY_DEMAND_TIMESERIES_HYDROGEN = "TRA_energy_demand_timeseries_hydrogen" + str(forecast_year) + ".xlsx"
        self.FILENAME_OUTPUT_ENERGY_DEMAND_TIMESERIES_TRAFFIC_TOTAL = "TRA_energy_demand_timeseries_total" + str(forecast_year) + ".xlsx"

        self.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME = "Ind_volume_" + str(forecast_year) + "_Trend.xlsx" #depending on scenario in industry changing name with if..IND_VOLUM_PROGNOS = "Trend" # "U-shape" or "Trend"
