###############################################################################                                                                                   
# Output and postprocess of data
###############################################################################
"""The module outputs the result values of the model.

"""
###############################################################################
#Imports
###############################################################################

import pandas as pd
import matplotlib.pyplot as plt
import csv
import matplotlib.pyplot as plt
import numpy as np
from xlrd import open_workbook
import matplotlib as mpl
import os 
import logging
import math
import logging
from op_methods import *
import load_excel

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def out_data(CTRL, FILE, ind_sol, hh_sol, cts_sol, tra_sol, abb_table):
    
    pop_prognosis=pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"Population_Nuts2_Country.xlsx"),
                            sheet_name=["Population_NUTS2", "Population_Countries"],skiprows=0)
    #------------------------------------------------------------------------------
    # Generall paths.
    path_timeseries = '_energy_demand_timeseries_'+str(CTRL.FORECAST_YEAR)+'.xlsx'
    
    #------------------------------------------------------------------------------
    # Industry.

    if CTRL.IND_ACTIVATED == True:
         # defining all outputs
        result_energy_timeseries = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND_energy_demand_timeseries_'+str(CTRL.FORECAST_YEAR)+'.xlsx'), engine='xlsxwriter')
        #if CTRL.IND_NUTS2_INST_CAP_ACTIVATED:
        #ind_sol.elec_timeseries.to_excel(result_energy_timeseries, sheet_name="Elec_timeseries", index=False, startrow=0)
        #ind_sol.heat_h2_timeseries.to_excel(result_energy_timeseries, sheet_name="Heat_H2_timeseries", index=False, startrow=0)
        #else:
        ind_sol.timeseries.to_excel(result_energy_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
        result_energy_timeseries.save()
 
    #------------------------------------------------------------------------------
    # Household.

    if CTRL.HH_ACTIVATED == True:

        # total demand sources trend
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_DEMAND_HOUSEHOLDS)
        data = {'SpaceHeating_PerCountry': hh_sol.hh_sh.energy_space_heating_countries, 'SpaceHeating_PerSource': hh_sol.hh_sh.sources_per_country_table_space_heating,
            'WaterHeating_PerCountry': hh_sol.hh_ww.energy_warm_water_countries,'WaterHeating_PerSource': hh_sol.hh_ww.sources_per_country_table_water_heating, 
            'Cooking_PerCountry': hh_sol.hh_co.energy_chocking_countries,'Cooking_PerSource': hh_sol.hh_co.sources_per_country_table_chocking,
            'Elec_PerCountry': hh_sol.hh_liandap.energy_electricity_countries, 
            'Cooling_PerCountry': hh_sol.hh_sc.energy_cooling_countries, 'Cooling_PerSource': hh_sol.hh_sc.sources_per_country_table_cooling}
        
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        # total demand per subsec
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_DEMAND_HOUSEHOLD_SUBSECTORS)
        data = {'Total_PerCountry': hh_sol.energy_demand_household_total_country, 'UsefulEnergy_PerCountry': hh_sol.energy_demand_household_usefulenergy_country}
        
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)  

        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_HOUSEHOLD)
        data = {'HH_demand': hh_sol.energy_demand_household_finalenergy_country}
        
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
        
        # Pers Per household
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_CHARACTERISTICS_HOUSEHOLDS)
        data = {'Pers per Household': hh_sol.hh_sh.table_person_prog_country, 
                'Area per Household': hh_sol.hh_sh.table_area_prog_country,
                'Specific energy consumption': hh_sol.hh_sh.table_specific_energy_use_prog_country,
                'Living area total': hh_sol.hh_sh.table_total_area_country}
        
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
    
        # historical data
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_ENERGYDEMAND_HIS_HOUSEHOLDS)
        data = {'cooking': hh_sol.hh_co.energy_demand_hisvalue,
            'space cooling': hh_sol.hh_sc.energy_demand_hisvalue,
            'lighting and appliances': hh_sol.hh_liandap.energy_demand_hisvalue,
            'space heating': hh_sol.hh_sh.energy_demand_hisvalue, 
            'warm water': hh_sol.hh_ww.energy_demand_hisvalue}
        
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        # hh_energy_demand_NUTS2 = redistribution_NUTS2(hh_sol.energy_demand_household_finalenergy_country, pop_prognosis, abb_table) #ind_sol.energy_demand
        
        # path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'HH_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
        # result_hh_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
        # hh_energy_demand_NUTS2.to_excel(result_hh_energy_demand_NUTS2,sheet_name="housholds", index=False, startrow=0)
        # result_hh_energy_demand_NUTS2.save()

        # hh_energy_demand_NUTS2 = redistribution_NUTS2(hh_sol.energy_demand_household_total_country, pop_prognosis, abb_table) #ind_sol.energy_demand
        
        # path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD,'HH_energy_NUTS2_subsector_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
        # result_hh_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
        # hh_energy_demand_NUTS2.to_excel(result_hh_energy_demand_NUTS2,sheet_name="HH", index=False, startrow=0)
        # result_hh_energy_demand_NUTS2.save()

    #------------------------------------------------------------------------------
    # Commertial, trade and services.

    if CTRL.CTS_ACTIVATED == True:
        # defining all outputs
        result_employee_number = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA_CTS+'\employee_number.xlsx', engine='xlsxwriter')
        result_energy = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\CTS_energy_demand_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
        result_energy_timeseries = pd.ExcelWriter(FILE.FILE_PATH_OUTPUT_DATA+'\CTS_energy_demand_timeseries_'+str(CTRL.FORECAST_YEAR) + '.xlsx', engine='xlsxwriter')
        
        cts_sol.employee.to_excel(result_employee_number, sheet_name="Empleyee total", index=False, startrow=0)
        cts_sol.energy_demand.to_excel(result_energy, sheet_name="CTS_demand", index=False, startrow=0)
        cts_sol.energy_timeseries.to_excel(result_energy_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
                  
        result_employee_number.save()
        result_energy.save()
        result_energy_timeseries.save()

        
        if CTRL.NUTS2_ACTIVATED:
            if CTRL.CTS_NUTS2_PER_POP: 
                cts_energy_demand_NUTS2 = redistribution_NUTS2(cts_sol.energy_demand, pop_prognosis, abb_table)
            else:
                cts_energy_demand_NUTS2 = cts_sol.cts_energy_demand_NUTS2
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'CTS_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            result_cts_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            cts_energy_demand_NUTS2.to_excel(result_cts_energy_demand_NUTS2,sheet_name="CTS", index=False, startrow=0)
            result_cts_energy_demand_NUTS2.save()
            
    #------------------------------------------------------------------------------
    # Traffic.

    if CTRL.TRA_ACTIVATED == True:

        # Person traffic results
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_DEMAND_PERSONTRAFFIC)
        data = {'Elec_PerCountry': tra_sol.tra_pt.energy_demand_person_traffic_electrical_country, 
            'Hydrogen_PerCountry': tra_sol.tra_pt.energy_demand_person_traffic_hydrogen_country,
            'Total_EnergyCarrier_PerCountry': tra_sol.tra_pt.energy_demand_person_traffic_energycarriers_totalvalues}
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_KILOMETERS_TRAFFIC)
        data = {'Person_kilometers': tra_sol.tra_pt.energy_demand_person_traffic_total_country, 
            'Tonne_kilometers': tra_sol.tra_ft.energy_demand_freight_traffic_total_country}
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
        
        #path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_PRODUCTION_VOLUME_TOTAL)
        #tra_sol.tra_pt.freight_transport_production_sum = to_excel(path, index=False)

        # Production volume
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_PRODUCTION_VOLUME_TOTAL)
        data = {"total_" + str(CTRL.FORECAST_YEAR): tra_sol.tra_ft.freight_transport_production_sum_forecast, 
            "total_" + str(CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS): tra_sol.tra_ft.freight_transport_production_sum_historical,
            "single_" + str(CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS): tra_sol.tra_ft.production_sum_historical_singlesectors}
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        # Freight traffic results
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_DEMAND_FREIGHTTRAFFIC)
        data = {'Elec_PerCountry': tra_sol.tra_ft.energy_demand_freight_traffic_electrical_country, 
            'Hydrogen_PerCountry': tra_sol.tra_ft.energy_demand_freight_traffic_hydrogen_country,
            'Total_EnergyCarrier_PerCountry': tra_sol.tra_ft.energy_demand_freight_traffic_energycarriers_totalvalues}
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        # Conclusion
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_TRAFFIC)
        data = {'TRA_demand': tra_sol.tra_ft_pt_energy_demand}
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_MODALSPLIT_TRAFFIC)
        data = {'Pt Modal Split': tra_sol.tra_pt.modalsplit_percountry,
            'Ft Modal Split': tra_sol.tra_ft.modalsplit_percountry}
        with pd.ExcelWriter(path) as ew: 

            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

    #------------------------------------------------------------------------------
    # Summary.

    if (CTRL.IND_ACTIVATED == True) and (CTRL.HH_ACTIVATED == True) and (CTRL.TRA_ACTIVATED == True) and (CTRL.CTS_ACTIVATED == True):
        
        # Total energy demand per energy carrier    
        overall_demand_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND_energy_demand_'+str(CTRL.FORECAST_YEAR)+'_'+ CTRL.IND_VOLUM_PROGNOS +'.xlsx'),
                                sheet_name=["IND_demand"],skiprows=0)["IND_demand"]
        for sheet in ["HH", "TRA", "CTS"]:
            sheet_name_demand = sheet+"_demand"
            df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+"_energy_demand_"+str(CTRL.FORECAST_YEAR)+".xlsx"),
                                    sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
            overall_demand_df = overall_demand_df.set_index("Country").add(df_sector.set_index("Country"), fill_value=0).reset_index()
            
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Energy_demand_'+str(CTRL.FORECAST_YEAR)+'.csv')
        overall_demand_df.to_csv(path, index=False, sep=";")
        
        # Total energy demand per sector
        df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND_energy_demand_'+str(CTRL.FORECAST_YEAR)+'_'+ 'Trend'+'.xlsx'),
            sheet_name=["IND_demand"],skiprows=0)["IND_demand"]
        for sheet in ["HH", "TRA", "CTS"]:
             sheet_name_demand = sheet+"_demand"
             df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+"_energy_demand_"+str(CTRL.FORECAST_YEAR)+".xlsx"),
                                     sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
             df = df.set_index("Country").add(df_sector.set_index("Country"), fill_value=0).reset_index()
            
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Energy_demand_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
        result_energy_demand = pd.ExcelWriter(path, engine='xlsxwriter')
        df.to_excel(result_energy_demand,sheet_name="overall_demand", index=False, startrow=0)
        result_energy_demand.save()
        
        # Total energy demand per energy carrier per NUTS2
        if CTRL.NUTS2_ACTIVATED:
            overall_demand_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx'),
                                    sheet_name=["IND"],skiprows=0)["IND"]
            for sheet in ["HH", "TRA", "CTS"]:
                df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+"_energy_NUTS2_"+str(CTRL.FORECAST_YEAR)+".xlsx"),
                                        sheet_name=[sheet],skiprows=0)[sheet]
                overall_demand_df = overall_demand_df.set_index("NUTS2").add(df_sector.set_index("NUTS2"), fill_value=0).reset_index()
                
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.csv')
            overall_demand_df.to_csv(path, index=False, sep=";")
        
        if CTRL.ACTIVATE_TIMESERIES:    
            add_timeseries(FILE, path_timeseries)

    if (CTRL.IND_ACTIVATED == True) and (CTRL.HH_ACTIVATED == True) and (CTRL.TRA_ACTIVATED == True) and (CTRL.CTS_ACTIVATED == False): # mit CTRL.SECTORS_ACTIVATED ohne doppelung
        
        # Total energy demand per energy carrier    
        overall_demand_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND_energy_demand_'+str(CTRL.FORECAST_YEAR)+'_'+ CTRL.IND_VOLUM_PROGNOS +'.xlsx'),
                                sheet_name=["IND_demand"],skiprows=0)["IND_demand"]
        for sheet in ["HH", "TRA"]:
            sheet_name_demand = sheet+"_demand"
            df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+"_energy_demand_"+str(CTRL.FORECAST_YEAR)+".xlsx"),
                                    sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
            overall_demand_df = overall_demand_df.set_index("Country").add(df_sector.set_index("Country"), fill_value=0).reset_index()
            
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Energy_demand_'+str(CTRL.FORECAST_YEAR)+'.csv')
        overall_demand_df.to_csv(path, index=False, sep=";")
        
        # Total energy demand per sector
        df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND_energy_demand_'+str(CTRL.FORECAST_YEAR)+'_'+ 'Trend'+'.xlsx'),
            sheet_name=["IND_demand"],skiprows=0)["IND_demand"]
        for sheet in ["HH", "TRA"]:
             sheet_name_demand = sheet+"_demand"
             df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+"_energy_demand_"+str(CTRL.FORECAST_YEAR)+".xlsx"),
                                     sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
             df = df.set_index("Country").add(df_sector.set_index("Country"), fill_value=0).reset_index()
            
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Energy_demand_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
        result_energy_demand = pd.ExcelWriter(path, engine='xlsxwriter')
        df.to_excel(result_energy_demand,sheet_name="overall_demand", index=False, startrow=0)
        result_energy_demand.save()
        
        # Total energy demand per energy carrier per NUTS2
        if CTRL.NUTS2_ACTIVATED:
            overall_demand_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND_energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx'),
                                    sheet_name=["IND"],skiprows=0)["IND"]
            for sheet in ["HH", "TRA"]:
                df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+"_energy_NUTS2_"+str(CTRL.FORECAST_YEAR)+".xlsx"),
                                        sheet_name=[sheet],skiprows=0)[sheet]
                overall_demand_df = overall_demand_df.set_index("NUTS2").add(df_sector.set_index("NUTS2"), fill_value=0).reset_index()
                
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Energy_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.csv')
            overall_demand_df.to_csv(path, index=False, sep=";")
        
        if CTRL.ACTIVATE_TIMESERIES:    
            add_timeseries(FILE, path_timeseries, CTRL)
    
    #------------------------------------------------------------------------------
    # Graphical Output (Plot and create figures).

    if (CTRL.GRAPHICAL_OUTPUT_ACTIVATED == True):

        # Total energy demand per energy carrier and country
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, 'Energy_demand_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
        sheet = pd.read_excel(path, sheet_name="overall_demand")

        #del sheet["Total [TWh]"]
        sheet.set_index(['Country']).plot(kind='bar')
        plt.title("Total energy demand per energy carrier in Europe " + str(CTRL.FORECAST_YEAR))
        plt.xlabel("Country")
        plt.ylabel("Useful energy demand in [TWh]")
        #plt.show()
        #plt.savefig(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "Plot_UsefulEnergyDemand_perenergycarrier" + str(CTRL.FORECAST_YEAR)+".pdf"))
        plt.savefig(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "Plot_UsefulEnergyDemand_perenergycarrier_" + str(CTRL.FORECAST_YEAR)+".png"))

        # muss noch bessere Ansicht gewählt werden, s. Ausgabe urbs  (Farben, Formatierung etc.!!!!!!!!!!!
        # 3 D Darstellung mit Ländern und Zeit bei intertemporaler Ausgabe von Jahren x=county, y=demand, z=Jahr?

        # Total energy demand per sector and country

        for comm in CTRL.ENERGYCARRIER:

            i=0

            for sector in range(0,len(CTRL.SECTORS_ACTIVATED)):

                df = []

                #print(CTRL.SECTORS_ACTIVATED[sector])

                sheet_name_demand = CTRL.SECTORS_ACTIVATED[0][sector]+"_demand"

                if CTRL.SECTORS_ACTIVATED[0][sector] == "IND":

                    df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, CTRL.SECTORS_ACTIVATED[0][sector]+"_energy_demand_"+str(CTRL.FORECAST_YEAR)+'_'+ 'Trend'+'.xlsx'),
                        sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
                else:
                        
                    df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, CTRL.SECTORS_ACTIVATED[0][sector]+"_energy_demand_"+str(CTRL.FORECAST_YEAR)+".xlsx"),
                        sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
                    
                df_sector_help = df_sector.set_index("Country")

                for country in CTRL.CONSIDERED_COUNTRIES:

                    if i == 0: 
                        df = pd.DataFrame([[country, df_sector_help[comm+" [TWh]"][country]]], columns=["Country", CTRL.SECTORS_ACTIVATED[0][sector]] \
                            ).append(df, ignore_index=True)
                    else:
                        df = pd.DataFrame([[df_sector_help[comm+" [TWh]"][country]]], columns=[CTRL.SECTORS_ACTIVATED[0][sector]] \
                            ).append(df, ignore_index=True)
                
                if i==1:
                    df_help = pd.concat([df_help, df], axis = 1)
                else:
                    df_help = df
                i=1

            #Plot
            #path = os.path.join(r'H:\04_Projekte\Nachfragemodell\03_Modell\endemo\results_2050\Energy_demand_2050.xlsx')
            #sheet = pd.read_excel(path, sheet_name="overall_demand")

            df_help.set_index(['Country']).plot(kind='bar', stacked=True)
            plt.title(comm + " energy demand per sector in Europe " + str(CTRL.FORECAST_YEAR))
            plt.xlabel("Country")
            plt.ylabel("Useful energy demand in [TWh]")

            #plt.show()

            plt.savefig(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "Plot_" + comm + "_UsefulEnergyDemand_persector_"+str(CTRL.FORECAST_YEAR)+".png"))    
