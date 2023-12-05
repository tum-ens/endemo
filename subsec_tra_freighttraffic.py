###############################################################################                                                                                   
# Forecast of the subsector road traffic for traffic
###############################################################################
"""The module calculates the energy demand of the subsector freight traffic for 
traffic.
"""
###############################################################################
#Imports
###############################################################################

import load_excel
import logging
import pandas as pd
import math
import logging
import subsec_tra_persontraffic
from subsec_ind_functions import *

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def freighttraffic(CTRL, FILE, tra_data, gen_data, ind_data):

    freight_transport_production_sum_forecast, freight_transport_production_sum_historical, production_sum_historical_singlesectors = sum_production_volume(CTRL, FILE, ind_data, tra_data)

    energy_demand_freight_traffic_total_country = []
    energy_demand_freight_traffic_electrical_country =[]
    energy_demand_freight_traffic_hydrogen_country = []
    energy_demand_freight_traffic_energycarriers_totalvalues = []
    modalsplit_percountry = []

    # Calculate energy demand freight traffic (railway, road, ship, ...)
    for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

        # Calculate specific value tonne kilometer per production volume tkm
        for i_country_tonnekm in range(0, len(tra_data.tonnekm_road_train)):    
            
            if CTRL.CONSIDERED_COUNTRIES[country] == tra_data.tonnekm_road_train["country_en"][i_country_tonnekm]:
            
                for i_country_production_his in range(0, len(freight_transport_production_sum_historical)):

                    if freight_transport_production_sum_historical[0][i_country_production_his] == CTRL.CONSIDERED_COUNTRIES[country]:

                        for i_production_volume_fligth_his in range(0, len(tra_data.tra_ft_production_volume_flight_his)):

                            if tra_data.tra_ft_production_volume_flight_his["country_en"][i_production_volume_fligth_his] == CTRL.CONSIDERED_COUNTRIES[country]:
                        
                                #print(gen_data.pop_table[str(tra_data.personkm_road_train["year"][i_country_perskm]).split(".")[0]][i_country_population_his])
                                #print(tra_data.personkm_road_train["person_km"][i_country_perskm])
                                #print(tra_data.personkm_road_train["person_km"][i_country_perskm])

                                freight_transport_production_country_historical = freight_transport_production_sum_historical[1][i_country_production_his]

                                calc_tonnekm = (tra_data.tonnekm_road_train["tonne_km"][i_country_tonnekm]*
                                    (10**6)/(freight_transport_production_sum_historical[1][i_country_production_his]-tra_data.tra_ft_production_volume_flight_his["Flight_tonne [t]"][i_production_volume_fligth_his]))
                                    # Calculation factor unit 10^6/production volume of the value year to get a freightspecific calulation factor
                                break
                        break
                break

        # Calculate propotion of flight production volume
        for i_country_prop_flight in range(0, len(tra_data.tra_ft_production_volume_flight_his)):    
            
            if CTRL.CONSIDERED_COUNTRIES[country] == tra_data.tra_ft_production_volume_flight_his["country_en"][i_country_prop_flight]:

                for i_country_production_his in range(0, len(freight_transport_production_sum_historical)):

                    if freight_transport_production_sum_historical[0][i_country_production_his] == CTRL.CONSIDERED_COUNTRIES[country]:

                        prop_production_volume_flight = (tra_data.tra_ft_production_volume_flight_his["Flight_tonne [t]"][i_country_prop_flight]/
                            freight_transport_production_sum_historical[1][i_country_production_his])
                        break
                break

        # Calculate specific value tonne kilometer per production volume for flight
        for i_country_tonnekm_flight in range(0, len(tra_data.tonnekm_flight)):    
            
            if CTRL.CONSIDERED_COUNTRIES[country] == tra_data.tonnekm_flight["country_en"][i_country_tonnekm_flight]:
            
                calc_tonnekm_flight = tra_data.tonnekm_flight["tonne_km"][i_country_tonnekm_flight]/freight_transport_production_country_historical*prop_production_volume_flight
                break

        # Get forecast production volume per country
        for i_country_forecast in range(0, len(freight_transport_production_sum_forecast)):

            if CTRL.CONSIDERED_COUNTRIES[country] == freight_transport_production_sum_forecast[0][i_country_forecast]:
                
                if CTRL.TRA_INDUSTRY_REST == True:

                    freight_transport_production_country_forecast = freight_transport_production_sum_forecast[1][i_country_forecast]

                    for i_country_rest in range(0, len(tra_data.industry_rest)):

                        if freight_transport_production_sum_forecast[0][i_country_forecast] == tra_data.industry_rest['country'][i_country_rest]:

                            freight_transport_production_country_forecast = (freight_transport_production_country_forecast + 
                                freight_transport_production_country_forecast * tra_data.industry_rest['t_percentage'][i_country_rest])
                else:
                    freight_transport_production_country_forecast = freight_transport_production_sum_forecast[1][i_country_forecast]
                #break

        # Get modal split per country
        if CTRL.TRA_MODALSPLIT_MODELTYPE == "Constant":
            # Railways
            for i_modal_split_railway in range(0, len(tra_data.modalsplit_railway)):
                if tra_data.modalsplit_road["country_en"][i_modal_split_railway] == CTRL.CONSIDERED_COUNTRIES[country]:     
                    modal_split_railway_country = tra_data.modalsplit_railway[2018][i_modal_split_railway]
                    break
            
            # Roads
            for i_modal_split_road in range(0, len(tra_data.modalsplit_road)):
                if tra_data.modalsplit_road["country_en"][i_modal_split_road] == CTRL.CONSIDERED_COUNTRIES[country]:
                    modal_split_road_country = tra_data.modalsplit_road[2018][i_modal_split_road]
                    break
            
            # Ship
            for i_modal_split_ship in range(0, len(tra_data.modalsplit_ship)):
                if tra_data.modalsplit_ship["country_en"][i_modal_split_ship] == CTRL.CONSIDERED_COUNTRIES[country]:
                    modal_split_ship_country = tra_data.modalsplit_ship[2018][i_modal_split_ship] 
                    break  

        elif CTRL.TRA_MODALSPLIT_MODELTYPE == "Trend":

            CTRL.IND_END_YEAR = 2020
            CTRL.IND_SKIP_YEARS = []
            coeff_content_roads=[]
            coeff_content_railway=[]
            coeff_content_ship=[]
 
            # Roads
            active_group=[CTRL.CONSIDERED_COUNTRIES[country]]
            idx_country=list(tra_data.modalsplit_road["country_en"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            idx_group=[idx_country]
            delta_active=False

            equation, eq_right, noData= linear_regression_single_country_time(CTRL, tra_data.modalsplit_road, 
                                                                idx_country)       
            if noData:
                koef=[np.nan, np.nan]
            else:
                koef=calc_koef(equation, eq_right)
            coeff_content_roads=save_koef(coeff_content_roads, active_group, koef, False, delta_active)
                    
            coeff_vol_df_roads=pd.DataFrame(coeff_content_roads, columns=["Country", "coeff_0", "coeff_1", 
                                                            "coeff_c"])

            idx_coeff=list(coeff_vol_df_roads["Country"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            modal_split_road_country=(coeff_vol_df_roads["coeff_0"][idx_coeff]
                    +coeff_vol_df_roads["coeff_1"][idx_coeff]*CTRL.FORECAST_YEAR
                    +coeff_vol_df_roads["coeff_c"][idx_coeff])

            # Railways
            active_group=[CTRL.CONSIDERED_COUNTRIES[country]]
            idx_country=list(tra_data.modalsplit_railway["country_en"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            idx_group=[idx_country]
            delta_active=False

            equation, eq_right, noData= linear_regression_single_country_time(CTRL, tra_data.modalsplit_railway, 
                                                                idx_country)       
            if noData:
                koef=[np.nan, np.nan]
            else:
                koef=calc_koef(equation, eq_right)
            coeff_content_railway=save_koef(coeff_content_railway, active_group, koef, False, delta_active)
                    
            coeff_vol_df_railway=pd.DataFrame(coeff_content_railway, columns=["Country", "coeff_0", "coeff_1", 
                                                            "coeff_c"])

            idx_coeff=list(coeff_vol_df_railway["Country"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            modal_split_railway_country=(coeff_vol_df_railway["coeff_0"][idx_coeff]
                    +coeff_vol_df_railway["coeff_1"][idx_coeff]*CTRL.FORECAST_YEAR
                    +coeff_vol_df_railway["coeff_c"][idx_coeff])

            # Ship
            active_group=[CTRL.CONSIDERED_COUNTRIES[country]]
            idx_country=list(tra_data.modalsplit_ship["country_en"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            idx_group=[idx_country]
            delta_active=False

            equation, eq_right, noData= linear_regression_single_country_time(CTRL, tra_data.modalsplit_ship, 
                                                                idx_country)       
            if noData:
                koef=[np.nan, np.nan]
            else:
                koef=calc_koef(equation, eq_right)
            coeff_content_ship=save_koef(coeff_content_ship, active_group, koef, False, delta_active)
                    
            coeff_vol_df_ship=pd.DataFrame(coeff_content_ship, columns=["Country", "coeff_0", "coeff_1", 
                                                            "coeff_c"])

            idx_coeff=list(coeff_vol_df_ship["Country"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            modal_split_ship_country=(coeff_vol_df_ship["coeff_0"][idx_coeff]
                    +coeff_vol_df_ship["coeff_1"][idx_coeff]*CTRL.FORECAST_YEAR
                    +coeff_vol_df_ship["coeff_c"][idx_coeff])

            if (modal_split_road_country > 95 or modal_split_road_country < 0 or modal_split_railway_country > 95 or modal_split_railway_country < 0 or
                modal_split_ship_country > 95 or modal_split_ship_country < 0): 
                modal_split_road_country = tra_data.modalsplit_road[2018][idx_country]
                modal_split_railway_country = tra_data.modalsplit_railway[2018][idx_country]
                modal_split_ship_country = tra_data.modalsplit_ship[2018][idx_country]

            if (modal_split_road_country+modal_split_railway_country+modal_split_ship_country >=102 or 
                modal_split_road_country+modal_split_ship_country+modal_split_railway_country <=98):
                print("Modal Split in freight transport "+ CTRL.CONSIDERED_COUNTRIES[country] + " is not correct.")
                sum_modalsplit=modal_split_road_country+modal_split_railway_country+modal_split_ship_country

            modalsplit_percountry = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], modal_split_road_country, modal_split_railway_country, modal_split_ship_country]], \
                ).append(modalsplit_percountry, ignore_index=True) 

        # Calculate final values
        railway = (calc_tonnekm*(freight_transport_production_country_forecast-freight_transport_production_country_forecast*prop_production_volume_flight)*
            (modal_split_railway_country/100)) # tkm
        road = (calc_tonnekm*(freight_transport_production_country_forecast-freight_transport_production_country_forecast*
            prop_production_volume_flight)*(modal_split_road_country/100))  # tkm
        ship = (calc_tonnekm*(freight_transport_production_country_forecast-freight_transport_production_country_forecast*
            prop_production_volume_flight)*(modal_split_ship_country/100)) # tkm
        flight = calc_tonnekm_flight*(freight_transport_production_country_forecast*prop_production_volume_flight) # tkm

        ## Electrical
        value_forecast_year_road_electrical = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_road_electrical)
        value_forecast_year_railway_electrical = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_railway_electrical)
        value_forecast_year_ship_electrical = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_ship_electrical)
        value_forecast_year_flight_electrical = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_flight_electrical)

        ## Hydrogen
        value_forecast_year_road_hydrogen = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_road_hydrogen)
        value_forecast_year_railway_hydrogen = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_railway_hydrogen)
        value_forecast_year_ship_hydrogen = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_ship_hydrogen)
        value_forecast_year_flight_hydrogen = subsec_tra_persontraffic.calc_energycarrier_forecast(CTRL, country, tra_data.tra_ft_energysources_flight_hydrogen)
        
        # Resulting energy consumption
        energy_demand_freight_traffic_total_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], railway*10**-6, road*10**-6, ship*10**-6, flight*10**-6, (railway+road+ship+flight)*10**-6]], \
            ).append(energy_demand_freight_traffic_total_country, ignore_index=True) 
        
        ## Electrical
        railway_elec = (value_forecast_year_railway_electrical/100)*railway*tra_data.tra_ft_energypermodal["railways"][0]*0.277778*10**-9 #TWh
        road_elec = (value_forecast_year_road_electrical/100)*road*tra_data.tra_ft_energypermodal["roads"][0]*0.277778*10**-9
        ship_elec = (value_forecast_year_ship_electrical/100)*ship*tra_data.tra_ft_energypermodal["waterways"][0]*0.277778*10**-9
        flight_elec = (value_forecast_year_flight_electrical/100)*flight*tra_data.tra_ft_energypermodal["flight"][0]*0.277778*10**-9

        energy_demand_freight_traffic_electrical_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], railway_elec, road_elec, ship_elec, flight_elec, 
            railway_elec+road_elec+ship_elec+flight_elec]], \
            ).append(energy_demand_freight_traffic_electrical_country, ignore_index=True)

        ## Hydrogen
        railway_hydro = (value_forecast_year_railway_hydrogen/100)*railway*tra_data.tra_ft_energypermodal["railways"][2]*0.277778*10**-9 #TWh
        road_hydro = (value_forecast_year_road_hydrogen/100)*road*tra_data.tra_ft_energypermodal["roads"][2]*0.277778*10**-9
        ship_hydro = (value_forecast_year_ship_hydrogen/100)*ship*tra_data.tra_ft_energypermodal["waterways"][2]*0.277778*10**-9
        flight_hydro = (value_forecast_year_flight_hydrogen/100)*flight*tra_data.tra_ft_energypermodal["flight"][2]*0.277778*10**-9

        energy_demand_freight_traffic_hydrogen_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], railway_hydro, road_hydro, ship_hydro, flight_hydro, 
            railway_hydro+road_hydro+ship_hydro+flight_hydro]], \
            ).append(energy_demand_freight_traffic_hydrogen_country, ignore_index=True)

        ## Total of all
        energy_demand_freight_traffic_energycarriers_totalvalues = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], railway_elec+road_elec+ship_elec+flight_elec, 
            railway_hydro+road_hydro+ship_hydro+flight_hydro, railway+road+ship+flight]], \
            ).append(energy_demand_freight_traffic_energycarriers_totalvalues, ignore_index=True)        
    
    tra_ft = FREIGHT_TRAFFIC(freight_transport_production_sum_forecast, freight_transport_production_sum_historical, energy_demand_freight_traffic_total_country, 
        energy_demand_freight_traffic_electrical_country, energy_demand_freight_traffic_hydrogen_country, energy_demand_freight_traffic_energycarriers_totalvalues, modalsplit_percountry,
        production_sum_historical_singlesectors)

    return tra_ft

class FREIGHT_TRAFFIC():

    def __init__(self, freight_transport_production_sum_forecast, freight_transport_production_sum_historical, energy_demand_freight_traffic_total_country, 
        energy_demand_freight_traffic_electrical_country, energy_demand_freight_traffic_hydrogen_country, energy_demand_freight_traffic_energycarriers_totalvalues, 
        modalsplit_percountry, production_sum_historical_singlesectors):

        self.freight_transport_production_sum_forecast = freight_transport_production_sum_forecast.rename({0:"Country", 1:"Ammount [t]"}, axis='columns')
        self.freight_transport_production_sum_historical = freight_transport_production_sum_historical.rename({0:"Country", 1:"Ammount [t]"}, axis='columns')
        self.energy_demand_freight_traffic_total_country = energy_demand_freight_traffic_total_country.rename({0:"Country", 1:"ft_railway [tkm]", 2:"ft_road [tkm]", 
            3:"ft_waterway [tkm]", 4:"ft_flight [tkm]", 5:"ft_total [tkm]"}, axis='columns')
        self.energy_demand_freight_traffic_electrical_country = energy_demand_freight_traffic_electrical_country.rename({0:"Country", 1:"ft_railway_elec [TWh]", 2:"ft_road_elec [TWh]", 
            3:"ft_waterway_elec [TWh]", 4:"ft_flight_elec [TWh]", 5:"ft_total_elec [TWh]"}, axis='columns')
        self.energy_demand_freight_traffic_hydrogen_country = energy_demand_freight_traffic_hydrogen_country.rename({0:"Country", 1:"ft_railway_hydrogen [TWh]", 2:"ft_road_hydrogen [TWh]", 
            3:"ft_waterway_hydrogen [TWh]", 4:"ft_flight_hydrogen [TWh]", 5:"ft_total_hydrogen [TWh]"}, axis='columns')     
        self.energy_demand_freight_traffic_energycarriers_totalvalues = energy_demand_freight_traffic_energycarriers_totalvalues.rename({0:"Country", 1:"ft_total_elec [TWh]", 
            2:"ft_total_hydrogen [TWh]", 3:"ft_total [TWh]"}, axis='columns') 
        self.modalsplit_percountry = modalsplit_percountry.rename({0:"Country", 1:"ft_road [%]", 2:"pt_railway [%]", 3:"pt_ship [%]"}, axis='columns')
        self.production_sum_historical_singlesectors = production_sum_historical_singlesectors.rename({0:"Country", 1:"alu_prim [t]", 2:"alu_sec [t]", 3:"cem [t]", 4:"glas [t]", 5: "pa [t]", 6: "steel [t]",
            7: "steel_direct [t]", 8:"ammon [t]", 9: "chlorin [t]", 10: "aromate [t]", 11:"ethylene [t]", 12:"methanol [t]", 13: "propylene [t]"}, axis='columns')#, 13:  "mais [t]"

def sum_production_volume(CTRL, FILE, ind_data, tra_data):

    num_sum_production_volume = ["Country", CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS]
    col_name = ["Ammount [kt]", CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS]

    for i_num_sum in range(0, len(num_sum_production_volume)):

        if num_sum_production_volume[i_num_sum] == "Country":

            # Import result of industry sector of production volume
            production_per_land_steel = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'steel')
            production_per_land_alu_prim = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'alu_prim')
            production_per_land_alu_sec = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'alu_sec')
            production_per_land_paper = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'paper')
            production_per_land_cement = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'cement')
            production_per_land_ammonia = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'ammonia')    
            production_per_land_glass = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'glass')

            production_per_land_steel_direct = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'steel_direct')
            production_per_land_chlorin = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'chlorin')
            production_per_land_aromate = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'aromate')
            production_per_land_ethylene = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'ethylene')
            production_per_land_methanol = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'methanol')
            production_per_land_propylene = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'propylene')

            #production_per_land_mais = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'mais')

            land_steel_direct = 1

            #production_per_land_steel_direct = load_excel.load_excel_sheet(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_FORECAST_INDUSTRY_VOLUME, 'direct')

        elif num_sum_production_volume[i_num_sum] == CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS:

            if CTRL.IND_ACTIVATED == False:
                # Input of industry sector of production volume
                production_per_land_steel = tra_data.steel_table
                production_per_land_alu_prim = tra_data.alu_prim_table
                production_per_land_alu_sec = tra_data.alu_sec_table
                production_per_land_cement = tra_data.cement_table
                production_per_land_paper = tra_data.paper_table
                production_per_land_ammonia = tra_data.ammonia_table
                production_per_land_glass = tra_data.glass_table 

                production_per_land_chlorin = tra_data.chlorin_table
                production_per_land_aromate = tra_data.aromate_table 
                production_per_land_ethylene = tra_data.ethylene_table 
                production_per_land_methanol = tra_data.methanol_table 
                production_per_land_propylene = tra_data.propylene_table
            else:
                # Input of industry sector of production volume
                production_per_land_steel = ind_data.steel_table
                production_per_land_alu_prim = ind_data.alu_prim_table
                production_per_land_alu_sec = ind_data.alu_sec_table
                production_per_land_cement = ind_data.cement_table
                production_per_land_paper = ind_data.paper_table
                production_per_land_ammonia = ind_data.ammonia_table
                production_per_land_glass = ind_data.glass_table 

                production_per_land_chlorin = ind_data.chlorin_table
                production_per_land_aromate = ind_data.aromate_table 
                production_per_land_ethylene = ind_data.ethylene_table 
                production_per_land_methanol = ind_data.methanol_table 
                production_per_land_propylene = ind_data.propylene_table

            #production_per_land_mais = tra_data.mais_table

            land_steel_direct = 0

        add = []
        production_sum_historical_singlesectors = []
        for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

            for i_alu in range(0, len(production_per_land_alu_prim)):

                #print(Countries['Country_engl'][country])
                #print(production_per_land_his_alu["Country"][i_alu])

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_alu_prim["Country"][i_alu]: 
                    alu = production_per_land_alu_prim[col_name[i_num_sum]][i_alu]
                    break
                else:
                    alu = 0

            for i_alu_sec in range(0, len(production_per_land_alu_sec)):

                #print(Countries['Country_engl'][country])
                #print(production_per_land_his_alu["Country"][i_alu])

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_alu_sec["Country"][i_alu_sec]: 
                    alu_sec = production_per_land_alu_sec[col_name[i_num_sum]][i_alu_sec]
                    break
                else:
                    alu_sec = 0

            #if CTRL.CONSIDERED_COUNTRIES[country] == "Belgium":
            #    import pdb; pdb.set_trace()
                
            for i_cem in range(0, len(production_per_land_cement)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_cement["Country"][i_cem]:
                    cem = production_per_land_cement[col_name[i_num_sum]][i_cem]
                    break
                else: 
                    cem = 0

            for i_glas in range(0, len(production_per_land_glass)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_glass["Country"][i_glas]:
                    glas = production_per_land_glass[col_name[i_num_sum]][i_glas]
                    break
                else: 
                    glas = 0

            for i_pa in range(0, len(production_per_land_paper)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_paper["Country"][i_pa]:
                    pa = production_per_land_paper[col_name[i_num_sum]][i_pa] 
                    break
                else: 
                    pa = 0 

            for i_steel in range(0, len(production_per_land_steel)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_steel["Country"][i_steel]:
                    steel = production_per_land_steel[col_name[i_num_sum]][i_steel]
                    break
                else: 
                    steel = 0

            for i_chlorin in range(0, len(production_per_land_chlorin)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_chlorin["Country"][i_chlorin]:
                    chlorin = production_per_land_chlorin[col_name[i_num_sum]][i_chlorin]
                    break
                else: 
                    chlorin = 0
            
            if land_steel_direct == 0:
                steel_direct = 0
            else:
                for i_steel in range(0, len(production_per_land_steel_direct)):

                    if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_steel_direct["Country"][i_steel]:
                        steel_direct = production_per_land_steel_direct[col_name[i_num_sum]][i_steel]
                        break
                    else: 
                        steel_direct = 0
                #steel_direct = 0
            
            for i_ammon in range(0, len(production_per_land_ammonia)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_ammonia["Country"][i_ammon]:
                    ammon = production_per_land_ammonia[col_name[i_num_sum]][i_ammon]
                    break
                else: 
                    ammon = 0
            
            for i_aromate in range(0, len(production_per_land_aromate)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_aromate["Country"][i_aromate]:
                    aromate = production_per_land_aromate[col_name[i_num_sum]][i_aromate]
                    break
                else: 
                    aromate = 0
            
            for i_ethylene in range(0, len(production_per_land_ethylene)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_ethylene["Country"][i_ethylene]:
                    ethylene = production_per_land_ethylene[col_name[i_num_sum]][i_ethylene]
                    break
                else: 
                    ethylene = 0

            for i_methanol in range(0, len(production_per_land_methanol)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_methanol["Country"][i_methanol]:
                    methanol = production_per_land_methanol[col_name[i_num_sum]][i_methanol]
                    break
                else: 
                    methanol = 0

            for i_propylene in range(0, len(production_per_land_propylene)):

                if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_propylene["Country"][i_propylene]:
                    propylene = production_per_land_propylene[col_name[i_num_sum]][i_propylene]
                    break
                else: 
                    propylene = 0   

            # for i_mais in range(0, len(production_per_land_mais)):

            #     if CTRL.CONSIDERED_COUNTRIES[country] == production_per_land_mais["Country"][i_mais]:
            #         mais = production_per_land_mais[col_name[i_num_sum]][i_mais]
            #         break
            #     else: 
            #         mais = 0  

            calc_sum = (alu*1000 + alu_sec*1000 + cem*1000 + glas*1000 + pa*1000 + steel*1000 + steel_direct*1000 + ammon*1000 + chlorin*1000 + 
                aromate*1000 + ethylene*1000 + methanol*1000 + propylene*1000 )# + mais*1000) 
                                                
            add.append([CTRL.CONSIDERED_COUNTRIES[country], calc_sum])

            if num_sum_production_volume[i_num_sum] == CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS:

                production_sum_historical_singlesectors = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], alu*1000, alu_sec*1000, cem*1000, glas*1000, pa*1000, steel*1000, 
                    steel_direct*1000, ammon*1000, chlorin*1000, aromate*1000, ethylene*1000, methanol*1000, propylene*1000]], \
                    ).append(production_sum_historical_singlesectors, ignore_index=True) #, mais*1000]], \

        # Get resulting sum of production volume for historical data or foecast year
        if num_sum_production_volume[i_num_sum] == "Country":
            production_sum_forecast = pd.DataFrame(add)
        elif num_sum_production_volume[i_num_sum] == CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS:
            production_sum_historical = pd.DataFrame(add)

    return production_sum_forecast, production_sum_historical, production_sum_historical_singlesectors

