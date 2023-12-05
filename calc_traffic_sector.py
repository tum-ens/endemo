###############################################################################                                                                                   
# Forecast of the traffic sector
###############################################################################
"""The module calculates the energy demand of the traffic sector.

The script calculates an energy demand development for the traffic sector 
based on user-specific inputs. A forecast should be made for the energy sources 
heat and electricity.
"""
###############################################################################
#Imports
###############################################################################

import load_excel
import logging
import pandas as pd
import os
from op_methods import *
import subsec_tra_persontraffic
import subsec_tra_freighttraffic

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def start_calc(CTRL, FILE, tra_data, gen_data, ind_data):

    sol = SUBSEC(CTRL, FILE, tra_data, gen_data, ind_data)

    return sol

class SUBSEC():

    def __init__(self, CTRL, FILE, tra_data, gen_data, ind_data):

        #------------------------------------------------------------------------------
        # Person traffic (pt).

        logger.info(" - Person traffic")
        self.tra_pt = subsec_tra_persontraffic.persontraffic(CTRL, FILE, tra_data, gen_data)   #person traffic = pt

        #------------------------------------------------------------------------------
        # Freight traffic (ft).

        logger.info(" - Freight traffic")
        self.tra_ft = subsec_tra_freighttraffic.freighttraffic(CTRL, FILE, tra_data, gen_data, ind_data)   #freight traffic = ft

        #------------------------------------------------------------------------------
        # Absolute values of energy sources for both subsectors

        self.tra_ft_pt_energy_demand = []
        #self.tra_ft_pt_energy_demand_single = []

        for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

            for i_pt_country in range(0, len(self.tra_pt.energy_demand_person_traffic_energycarriers_totalvalues)):
        
                if self.tra_pt.energy_demand_person_traffic_energycarriers_totalvalues["Country"][i_pt_country] == CTRL.CONSIDERED_COUNTRIES[country]:
                
                    for i_ft_country in range(0, len(self.tra_ft.energy_demand_freight_traffic_energycarriers_totalvalues)):

                        if self.tra_ft.energy_demand_freight_traffic_energycarriers_totalvalues["Country"][i_ft_country] == self.tra_pt.energy_demand_person_traffic_energycarriers_totalvalues["Country"][i_pt_country]:       
            
                            self.tra_ft_pt_energy_demand = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], 
                                self.tra_ft.energy_demand_freight_traffic_energycarriers_totalvalues["ft_total_elec [TWh]"][i_ft_country]+
                                self.tra_pt.energy_demand_person_traffic_energycarriers_totalvalues["pt_total_elec [TWh]"][i_pt_country], 0, 
                                self.tra_ft.energy_demand_freight_traffic_energycarriers_totalvalues["ft_total_hydrogen [TWh]"][i_ft_country]+
                                self.tra_pt.energy_demand_person_traffic_energycarriers_totalvalues["pt_total_hydrogen [TWh]"][i_pt_country]
                                ]], \
                                ).append(self.tra_ft_pt_energy_demand, ignore_index=True)
                            #break
                
        self.tra_ft_pt_energy_demand = self.tra_ft_pt_energy_demand.rename({0:"Country", 1:"Electricity [TWh]", 
            2:"Heat [TWh]", 3:"Hydrogen [TWh]"}, axis='columns')

        #------------------------------------------------------------------------------
        # Nuts2 for traffic

        pop_prognosis=pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"Population_Nuts2_Country.xlsx"),
            sheet_name=["Population_NUTS2", "Population_Countries"],skiprows=0)

        if CTRL.NUTS2_ACTIVATED == True:
        
            tra_energy_demand_NUTS2 = redistribution_NUTS2(self.tra_ft_pt_energy_demand, pop_prognosis, gen_data.gen_abbreviations) #ind_sol.energy_demand
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            result_tra_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            tra_energy_demand_NUTS2.to_excel(result_tra_energy_demand_NUTS2,sheet_name="TRA", index=False, startrow=0)
            result_tra_energy_demand_NUTS2.save()

            # energy per modal and nuts2
            energy_demand_per_modal_person_traffic_electrical_nuts2 = redistribution_NUTS2(self.tra_pt.energy_demand_person_traffic_electrical_country, pop_prognosis, gen_data.gen_abbreviations)
            energy_demand_per_modal_person_traffic_hydrogen_nuts2 = redistribution_NUTS2(self.tra_pt.energy_demand_person_traffic_hydrogen_country, pop_prognosis, gen_data.gen_abbreviations)
            energy_demand_per_modal_freight_traffic_electrical_nuts2 = redistribution_NUTS2(self.tra_ft.energy_demand_freight_traffic_electrical_country, pop_prognosis, gen_data.gen_abbreviations)
            energy_demand_per_modal_freight_traffic_hydrogen_nuts2 = redistribution_NUTS2(self.tra_ft.energy_demand_freight_traffic_hydrogen_country, pop_prognosis, gen_data.gen_abbreviations)

            # path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            # result_tra_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            # tra_energy_demand_NUTS2.to_excel(result_tra_energy_demand_NUTS2,sheet_name="TRA", index=False, startrow=0)
            # result_tra_energy_demand_NUTS2.save()

            # Nuts 2 Level pkm an tkm
            tra_energy_demand_NUTS2 = redistribution_NUTS2(self.tra_pt.energy_demand_person_traffic_total_country, pop_prognosis, gen_data.gen_abbreviations) #ind_sol.energy_demand
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_pkm_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            result_tra_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            tra_energy_demand_NUTS2.to_excel(result_tra_energy_demand_NUTS2,sheet_name="pkm", index=False, startrow=0)
            result_tra_energy_demand_NUTS2.save()

            tra_energy_demand_NUTS2 = redistribution_NUTS2(self.tra_ft.energy_demand_freight_traffic_total_country, pop_prognosis, gen_data.gen_abbreviations) #ind_sol.energy_demand
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_tkm_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            result_tra_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            tra_energy_demand_NUTS2.to_excel(result_tra_energy_demand_NUTS2,sheet_name="tkm", index=False, startrow=0)
            result_tra_energy_demand_NUTS2.save()

        #------------------------------------------------------------------------------
        # Timeseries for traffic

        if CTRL.ACTIVATE_TIMESERIES == True:

            if CTRL.NUTS2_ACTIVATED == True:

                logger.info(" - Timeseries traffic: Nuts2")

                sheet = pd.read_excel(pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx'), engine='xlsxwriter'), "TRA")
                consideredcountries = sheet["NUTS2"]

                # # change direction of considered countries
                # # energy timeseries
                # consideredcountries = []
                # for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):
                #     consideredcountries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country]]], \
                #         ).append(consideredcountries, ignore_index=True)

                result_energy_profiles = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\TRA_energy_demand_timeseries_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
                energy_profiles_df = energy_profiles_calc(consideredcountries, CTRL, energy_demand_per_modal_person_traffic_electrical_nuts2, 
                    energy_demand_per_modal_person_traffic_hydrogen_nuts2, energy_demand_per_modal_freight_traffic_electrical_nuts2, 
                    energy_demand_per_modal_freight_traffic_hydrogen_nuts2, tra_data.timeseries_loading)
                #print(energy_profiles_df)
                energy_profiles_df.to_excel(result_energy_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
                result_energy_profiles.save()

                # traffic kilometers timeseries
                consideredcountries = []
                for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):
                    consideredcountries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country]]], \
                         ).append(consideredcountries, ignore_index=True)

                result_kilometers_profiles = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\TRA_kilometers_demand_timeseries_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
                traffic_profiles_df = energy_kilometers_calc(consideredcountries, CTRL, self.tra_pt.energy_demand_person_traffic_total_country, 
                     self.tra_ft.energy_demand_freight_traffic_total_country, tra_data.timeseries_mobility)
                #print(energy_profiles_df)
                traffic_profiles_df.to_excel(result_kilometers_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
                result_kilometers_profiles.save()

            elif CTRL.NUTS2_ACTIVATED == False:

                logger.info(" - Timeseries traffic: Country")

                # change direction of considered countries
                # energy timeseries
                consideredcountries = []
                for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):
                    consideredcountries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country]]], \
                        ).append(consideredcountries, ignore_index=True)

                result_energy_profiles = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\TRA_energy_demand_timeseries_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
                energy_profiles_df = energy_profiles_calc(consideredcountries, CTRL, self.tra_pt.energy_demand_person_traffic_electrical_country, 
                    self.tra_pt.energy_demand_person_traffic_hydrogen_country, self.tra_ft.energy_demand_freight_traffic_electrical_country, 
                    self.tra_ft.energy_demand_freight_traffic_hydrogen_country, tra_data.timeseries_loading)
                #print(energy_profiles_df)
                energy_profiles_df.to_excel(result_energy_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
                result_energy_profiles.save()

                # traffic kilometers timeseries
                consideredcountries = []
                for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):
                    consideredcountries = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country]]], \
                        ).append(consideredcountries, ignore_index=True)

                result_kilometers_profiles = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\TRA_kilometers_demand_timeseries_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
                traffic_profiles_df = energy_kilometers_calc(consideredcountries, CTRL, self.tra_pt.energy_demand_person_traffic_total_country, 
                    self.tra_ft.energy_demand_freight_traffic_total_country, tra_data.timeseries_mobility)
                #print(energy_profiles_df)
                traffic_profiles_df.to_excel(result_kilometers_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
                result_kilometers_profiles.save()
        
        else:
            print("Calculation of load timeseries deactivated.")
            
def energy_kilometers_calc(consideredcountries, CTRL, kilometers_df_pt, kilometers_df_ft, load_profile):

    Traffic_sectors = ['pt_car_pkm', 'pt_bus_pkm', 'pt_rail_pkm', 'pt_flight_pkm','pt_ship_pkm','ft_road_tkm','ft_railway_tkm','ft_flight_tkm','ft_waterway_tkm']

    content = []
    idx_time = 0
    for time in load_profile["t"]:
        row = [time]

        for energy_type in Traffic_sectors:

            if energy_type == "pt_car_pkm":

               energy_type_name = "pt_car [Pkm]"

               idx_country = 0
               for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_pt[energy_type_name][idx_country] * load_profile["pt.car"][idx_time]*1000000000)
                        
                    idx_country += 1

            elif energy_type == "pt_bus_pkm":

                energy_type_name = "pt_bus [Pkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_pt[energy_type_name][idx_country] * load_profile["pt.bus"][idx_time]*1000000000)
                        
                    idx_country += 1

            elif energy_type == "pt_rail_pkm":

                energy_type_name = "pt_rail [Pkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_pt[energy_type_name][idx_country] * load_profile["pt.rail"][idx_time]*1000000000)
                        
                    idx_country += 1

            elif energy_type == "pt_flight_pkm":

                energy_type_name = "pt_flight [Pkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_pt[energy_type_name][idx_country] * load_profile["pt.flight"][idx_time]*1000000000)
                        
                    idx_country += 1
            
            elif energy_type == "pt_ship_pkm":

                energy_type_name = "pt_ship [Pkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_pt[energy_type_name][idx_country] * load_profile["pt.ship"][idx_time]*1000000000)
                        
                    idx_country += 1

            elif energy_type == "ft_road_tkm":

                energy_type_name = "ft_road [tkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_ft[energy_type_name][idx_country] * load_profile["ft.road"][idx_time]*1000000)
                        
                    idx_country += 1                    

            elif energy_type == "ft_railway_tkm":

                energy_type_name = "ft_railway [tkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_ft[energy_type_name][idx_country] * load_profile["ft.rail"][idx_time]*1000000)
                        
                    idx_country += 1

            elif energy_type == "ft_waterway_tkm":

                energy_type_name = "ft_waterway [tkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_ft[energy_type_name][idx_country] * load_profile["ft.ship"][idx_time]*1000000)
                        
                    idx_country += 1

            elif energy_type == "ft_flight_tkm":

                energy_type_name = "ft_flight [tkm]"

                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(kilometers_df_ft[energy_type_name][idx_country] * load_profile["ft.flight"][idx_time]*1000000)
                        
                    idx_country += 1            
                #print(energy_type , " finished")

        content.append(row)       
        idx_time += 1
    
    energy_profiles_col = ["t"]
    for energy_type in Traffic_sectors:
        for country in range(0, len(consideredcountries)):
            energy_profiles_col.append(consideredcountries[0][country]+ "." + energy_type)

    print("Calculated kilometers profiles. Df is making")
    energy_profiles_df = pd.DataFrame(content, columns = energy_profiles_col)
    return energy_profiles_df

def energy_profiles_calc(consideredcountries, CTRL, energy_df_pt_elec, energy_df_pt_hydrogen, energy_df_ft_elec, energy_df_ft_hydrogen, load_profile):
    content = []
    idx_time = 0
    for time in load_profile["t"]:
        row = [time]

        for energy_type in CTRL.ENERGYCARRIER:

            if energy_type == "Elec":

                # Elec
                energy_type_name_1 = "pt_car_elec [TWh]"
                energy_type_name_2 = "pt_rail_elec [TWh]"
                energy_type_name_3 = "pt_bus_elec [TWh]"
                energy_type_name_4 = "pt_flight_elec [TWh]"
                energy_type_name_5 = "pt_ship_elec [TWh]"

                energy_type_name_6 = "ft_railway_elec [TWh]"
                energy_type_name_7 = "ft_road_elec [TWh]"
                energy_type_name_8 = "ft_waterway_elec [TWh]"
                energy_type_name_9 = "ft_flight_elec [TWh]"
                
                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(energy_df_pt_elec[energy_type_name_1][idx_country] * load_profile["pt.road.electricity"][idx_time]+
                        energy_df_pt_elec[energy_type_name_2][idx_country] * load_profile["pt.rail.electricity"][idx_time]+
                        energy_df_pt_elec[energy_type_name_3][idx_country] * load_profile["pt.road.electricity"][idx_time]+
                        energy_df_pt_elec[energy_type_name_4][idx_country] * load_profile["flight.electricity"][idx_time]+
                        energy_df_pt_elec[energy_type_name_5][idx_country] * load_profile["waterway.electricity"][idx_time]
                        +
                        energy_df_ft_elec[energy_type_name_6][idx_country] * load_profile["ft.rail.electricity"][idx_time]+
                        energy_df_ft_elec[energy_type_name_7][idx_country] * load_profile["ft.road.electricity"][idx_time]+
                        energy_df_ft_elec[energy_type_name_8][idx_country] * load_profile["waterway.electricity"][idx_time]+
                        energy_df_ft_elec[energy_type_name_9][idx_country] * load_profile["flight.electricity"][idx_time])
                    
                    idx_country += 1
                #print(energy_type , " finished")

            elif energy_type == "H2":

                # Hydrogen
                energy_type_name_1 = "pt_car_hydrogen [TWh]"
                energy_type_name_2 = "pt_rail_hydrogen [TWh]"
                energy_type_name_3 = "pt_bus_hydrogen [TWh]"
                energy_type_name_4 = "pt_flight_hydrogen [TWh]"
                energy_type_name_5 = "pt_ship_hydrogen [TWh]"

                energy_type_name_6 = "ft_railway_hydrogen [TWh]"
                energy_type_name_7 = "ft_road_hydrogen [TWh]"
                energy_type_name_8 = "ft_waterway_hydrogen [TWh]"
                energy_type_name_9 = "ft_flight_hydrogen [TWh]"
                    
                idx_country = 0
                for country in range(0, len(consideredcountries)):

                    #print(str(energy_df[energy_type_name][idx_country]))
                    #print(str(load_profile[energy_type][idx_time]))

                    row.append(energy_df_pt_hydrogen[energy_type_name_1][idx_country] * load_profile["pt.road.hydrogen"][idx_time]+
                        energy_df_pt_hydrogen[energy_type_name_2][idx_country] * load_profile["pt.rail.hydrogen"][idx_time]+
                        energy_df_pt_hydrogen[energy_type_name_3][idx_country] * load_profile["pt.road.hydrogen"][idx_time]+
                        energy_df_pt_hydrogen[energy_type_name_4][idx_country] * load_profile["flight.hydrogen"][idx_time]+
                        energy_df_pt_hydrogen[energy_type_name_5][idx_country] * load_profile["waterway.hydrogen"][idx_time]
                        +
                        energy_df_ft_hydrogen[energy_type_name_6][idx_country] * load_profile["ft.rail.hydrogen"][idx_time]+
                        energy_df_ft_hydrogen[energy_type_name_7][idx_country] * load_profile["ft.road.hydrogen"][idx_time]+
                        energy_df_ft_hydrogen[energy_type_name_8][idx_country] * load_profile["waterway.hydrogen"][idx_time]+
                        energy_df_ft_hydrogen[energy_type_name_9][idx_country] * load_profile["flight.hydrogen"][idx_time])
                        
                    idx_country += 1
                #print(energy_type , " finished")

        content.append(row)       
        idx_time += 1
    
    energy_profiles_col = ["t"]
    for energy_type in CTRL.ENERGYCARRIER:
        for country in range(0, len(consideredcountries)):

            #print(consideredcountries[0][country])
            if energy_type ==  "Heat":
                print(country , ": ", energy_type , "make no sense for traffic sector.")
            elif CTRL.NUTS2_ACTIVATED == True:
                energy_profiles_col.append(consideredcountries[country]+ "." + energy_type)
            else:
                energy_profiles_col.append(consideredcountries[0][country]+ "." + energy_type)
    print("Calculated profiles. Df is making")
    energy_profiles_df = pd.DataFrame(content, columns = energy_profiles_col)
    return energy_profiles_df