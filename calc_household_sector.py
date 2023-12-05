###############################################################################                                                                                   
# Forecast of the household sector
###############################################################################
"""The module calculates the energy demand of the household sector.

The script calculates an energy demand development for the household sector 
based on user-specific inputs. A forecast should be made for the energy sources 
heat and electricity.
"""
###############################################################################
#Imports
###############################################################################

import load_excel
import logging
import os
import subsec_hh_spaceheating
import subsec_hh_warmwater
import subsec_hh_cooking
import subsec_hh_lighting
import subsec_hh_spacecooling
from op_methods import *
import pandas as pd

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def start_calc(CTRL, FILE, hh_data, gen_data):

    sol = SUBSEC(CTRL, FILE, hh_data, gen_data)

    return sol

class SUBSEC():

    def __init__(self, CTRL, FILE, hh_data, gen_data):

        #------------------------------------------------------------------------------
        # Space heating (sh).

        logger.info(" - Space heating")
        self.hh_sh = subsec_hh_spaceheating.spaceheating(CTRL, FILE, hh_data, gen_data) #ergänze Version Trendprojektion und Stützjahre!!

        #------------------------------------------------------------------------------
        # Warm water (ww).

        logger.info(" - Warm water")
        self.hh_ww = subsec_hh_warmwater.warmwater(CTRL, FILE, hh_data, gen_data)

        #------------------------------------------------------------------------------
        # Cooking (co).

        logger.info(" - Cooking")
        self.hh_co = subsec_hh_cooking.cooking(CTRL, FILE, hh_data, gen_data)

        #------------------------------------------------------------------------------
        # Lighting and electrical appliances (liandap).

        logger.info(" - Lighting and electrical appliances")
        self.hh_liandap = subsec_hh_lighting.lighting(CTRL, FILE, hh_data, gen_data)

        #------------------------------------------------------------------------------
        # Space cooling (sc).

        logger.info(" - Space cooling")
        self.hh_sc = subsec_hh_spacecooling.spacecooling(CTRL, FILE, hh_data, gen_data)

        #------------------------------------------------------------------------------
        # Total, sources and timeseries.

        self.energy_demand_household_total_country = []

        for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

            for i_country in range(0, len(self.hh_sh.energy_space_heating_countries)):

                #print(str(self.hh_sh.energy_space_heating_countries["Country"][i_country]))
                #print(str(self.hh_sh.energy_space_heating_countries["Country"][i_country]))
                #print(str(CTRL.CONSIDERED_COUNTRIES[country]))

                if self.hh_sh.energy_space_heating_countries["Country"][i_country]==CTRL.CONSIDERED_COUNTRIES[country]:

                    #print(str(self.hh_sh.energy_space_heating_countries["Country"][i_country]))
                    #print(str(CTRL.CONSIDERED_COUNTRIES[country]))
                    #print(str(self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3))
                    #print(str(self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3))

                    self.energy_demand_household_total_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], self.hh_sh.energy_space_heating_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778,
                        self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778, self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778,
                        self.hh_sc.energy_cooling_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778, self.hh_liandap.energy_electricity_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778,
                        self.hh_sh.energy_space_heating_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+self.hh_sc.energy_cooling_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_liandap.energy_electricity_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778]], \
                        ).append(self.energy_demand_household_total_country, ignore_index=True)
            
        self.energy_demand_household_total_country = self.energy_demand_household_total_country.rename({0:"Country", 1:"spaceheating [TWh]", 
            2:"warmwater [TWh]", 3:"cooking [TWh]", 4:"spacecooling [TWh]", 5:"electronicaldevices [TWh]", 6:"total [TWh]"}, axis='columns')
        
        # Useful energy
        self.energy_demand_household_usefulenergy_country = []

        for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

            for i_country in range(0, len(self.hh_sh.energy_space_heating_countries)):

                if self.hh_sh.energy_space_heating_countries["Country"][i_country]==CTRL.CONSIDERED_COUNTRIES[country]:

                    #print(str(self.hh_sh.energy_space_heating_countries["Country"][i_country]))
                    #print(str(CTRL.CONSIDERED_COUNTRIES[country]))

                    self.energy_demand_household_usefulenergy_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country],
                        self.hh_sh.energy_space_heating_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778, self.hh_sc.energy_cooling_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_liandap.energy_electricity_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778, 
                        self.hh_sh.energy_space_heating_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+self.hh_sc.energy_cooling_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_liandap.energy_electricity_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778]], \
                        ).append(self.energy_demand_household_usefulenergy_country, ignore_index=True)
            
        self.energy_demand_household_usefulenergy_country = self.energy_demand_household_usefulenergy_country.rename({0:"Country", 1:"Heat [TWh]", 
            2:"Electricity [TWh]", 3:"Total [TWh]"}, axis='columns')
        
        # Final Energy: because of efficiency near by 100% for all same like useful energy
        value_forecast_year_districtheat = hh_data.sources_split[CTRL.FORECAST_YEAR][1]
        value_forecast_year_hydrogen = hh_data.sources_split[CTRL.FORECAST_YEAR][3] # gas theoretical x% hydrogen possible
        value_forecast_year_elec = hh_data.sources_split[CTRL.FORECAST_YEAR][4]
    
        self.energy_demand_household_finalenergy_country = []

        for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

            for i_country in range(0, len(self.hh_sh.energy_space_heating_countries)):

                if self.hh_sh.energy_space_heating_countries["Country"][i_country]==CTRL.CONSIDERED_COUNTRIES[country]:

                    #print(str(self.hh_sh.energy_space_heating_countries["Country"][i_country]))
                    #print(str(CTRL.CONSIDERED_COUNTRIES[country]))
                    heat = ((self.hh_sh.energy_space_heating_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778)+ 
                        self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778)
                    hydrogen = ((self.hh_sh.energy_space_heating_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778)*(value_forecast_year_hydrogen/100))
                    #self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778
                    elec = (self.hh_sc.energy_cooling_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                        self.hh_liandap.energy_electricity_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778)
                    #total = (self.hh_sh.energy_space_heating_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                    #    self.hh_ww.energy_warm_water_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                    #    self.hh_co.energy_chocking_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                    #    self.hh_sc.energy_cooling_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778+
                    #    self.hh_liandap.energy_electricity_countries["Consumption Prog Year [TJ]"][i_country]*10**-3*0.27777777777778)

                    self.energy_demand_household_finalenergy_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], elec, heat, hydrogen]], \
                        ).append(self.energy_demand_household_finalenergy_country, ignore_index=True)  #with the assumption cooking 100% electro
            
        self.energy_demand_household_finalenergy_country = self.energy_demand_household_finalenergy_country.rename({0:"Country", 1:"Electricity [TWh]", 
            2:"Heat [TWh]", 3:"Hydrogen [TWh]"}, axis='columns')

        #------------------------------------------------------------------------------
        # Nuts2 for traffic 

        pop_prognosis=pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"Population_Nuts2_Country.xlsx"),
            sheet_name=["Population_NUTS2", "Population_Countries"],skiprows=0)         

        if CTRL.NUTS2_ACTIVATED == True:
    
            hh_energy_demand_NUTS2 = redistribution_NUTS2(self.energy_demand_household_finalenergy_country, pop_prognosis, gen_data.gen_abbreviations) #ind_sol.energy_demand
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'HH_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            result_hh_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            hh_energy_demand_NUTS2.to_excel(result_hh_energy_demand_NUTS2,sheet_name="HH", index=False, startrow=0)
            result_hh_energy_demand_NUTS2.save()

            hh_energy_demand_NUTS2_subsector = redistribution_NUTS2(self.energy_demand_household_total_country, pop_prognosis, gen_data.gen_abbreviations) #ind_sol.energy_demand
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD,'HH_energy_NUTS2_subsector_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            result_hh_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            hh_energy_demand_NUTS2_subsector.to_excel(result_hh_energy_demand_NUTS2,sheet_name="HH", index=False, startrow=0)
            result_hh_energy_demand_NUTS2.save()

        #------------------------------------------------------------------------------
        # Timeseries for household

        if CTRL.ACTIVATE_TIMESERIES == True:

            if CTRL.NUTS2_ACTIVATED == True:

                logger.info(" - Timeseries traffic: Nuts2")

                sheet = pd.read_excel(pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'HH_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx'), engine='xlsxwriter'), "HH")
                consideredcountries = sheet["NUTS2"]

                result_energy_profiles = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\HH_energy_demand_timeseries_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
                energy_profiles_df = energy_profiles_calc(consideredcountries, CTRL, hh_energy_demand_NUTS2, hh_data.timeseries)
                #print(energy_profiles_df)
                energy_profiles_df.to_excel(result_energy_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
                result_energy_profiles.save()                

            elif CTRL.NUTS2_ACTIVATED == False:    

                logger.info(" - Timeseries traffic: Country")
            
                # change direction of considered countries
                consideredcountries = []
                for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):
                    consideredcountries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country]]], \
                        ).append(consideredcountries, ignore_index=True)  #with the assumption cooking 100% electro

                #timeseries: split in mfh and efh (building stock)
                #hh_data.building_stock[efh][i_country]
                #hh_data.building_stock[mfh][i_country]
                result_energy_profiles = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\HH_energy_demand_timeseries_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
                energy_profiles_df = energy_profiles_calc(consideredcountries, CTRL, self.energy_demand_household_finalenergy_country, hh_data.timeseries)
                #print(energy_profiles_df)
                energy_profiles_df.to_excel(result_energy_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
                result_energy_profiles.save()

def energy_profiles_calc(consideredcountries, CTRL, energy_df, load_profile):
    content = []
    idx_time = 0
    for time in load_profile["t"]:
        row = [time]
        for energy_type in load_profile.columns[1:len(load_profile.columns)]:

            #print(str(load_profile.columns))

            if energy_type == "Elec":
                energy_type_name = "Electricity [TWh]"
                distribution = 1
                buildingstock = 1

            elif energy_type == "EFH_Heat_Q1":
                energy_type_name = "Heat [TWh]"
                distribution = CTRL.HH_HEAT_Q1
                buildingstock = CTRL.HH_HEAT_EFH

                energy_type2 = "MFH_Heat_Q1"
                distribution2 = CTRL.HH_HEAT_Q1
                buildingstock2 = 1 - CTRL.HH_HEAT_EFH                

            elif energy_type == "EFH_Heat_Q2":
                energy_type_name = "Heat [TWh]"
                distribution = 1 - CTRL.HH_HEAT_Q1
                buildingstock = CTRL.HH_HEAT_EFH

                energy_type2 = "MFH_Heat_Q2"
                distribution2 = 1 - CTRL.HH_HEAT_Q1
                buildingstock2 = 1 - CTRL.HH_HEAT_EFH                

            elif energy_type == "EFH_H2":
                energy_type_name = "Hydrogen [TWh]"
                buildingstock = 1
                distribution = 1

                energy_type2 = "MFH_H2"
                buildingstock2 = 1     
                distribution2 = 1
            
            if (energy_type != "MFH_Heat_Q1") and (energy_type != "MFH_Heat_Q2") and (energy_type != "MFH_H2"):
                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))
                    
                    if energy_type == "Elec":
                        row.append(energy_df[energy_type_name][idx_country] * distribution * buildingstock * load_profile[energy_type][idx_time])
                    else:
                        row.append(energy_df[energy_type_name][idx_country] * distribution * buildingstock * load_profile[energy_type][idx_time]+
                            energy_df[energy_type_name][idx_country] * distribution2 * buildingstock2 * load_profile[energy_type2][idx_time])                        
                    
                    idx_country += 1
                #print(energy_type , " finished")
        content.append(row)       
        idx_time += 1
    
    energy_profiles_col = ["t"]
    for energy_type in load_profile.columns[1:len(load_profile.columns)]:
        for country in range(0, len(consideredcountries)):

            if (energy_type != "MFH_Heat_Q1") and (energy_type != "MFH_Heat_Q2") and (energy_type != "MFH_H2") and (energy_type != "Elec"):

                #print(energy_type.split("H."))
                if CTRL.NUTS2_ACTIVATED == True:
                    #energy_profiles_col.append(consideredcountries[country]+ "." + energy_type)
                    energy_profiles_col.append(consideredcountries[country]+ "." + energy_type.split("H_")[1])
                else:
                    energy_profiles_col.append(consideredcountries[0][country]+ "." + energy_type.split("H_")[1])

            elif (energy_type == "Elec"):
                #print(consideredcountries[0][country])
                if CTRL.NUTS2_ACTIVATED == True:
                    energy_profiles_col.append(consideredcountries[country]+ "." + energy_type)
                else:    
                    energy_profiles_col.append(consideredcountries[0][country]+ "." + energy_type)

    print("Calculated profiles. Df is making")
    energy_profiles_df = pd.DataFrame(content, columns = energy_profiles_col)
    return energy_profiles_df