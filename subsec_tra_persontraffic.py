###############################################################################                                                                                   
# Forecast of the subsector person traffic for traffic
###############################################################################
"""The module calculates the energy demand of the subsector person traffic for 
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
from subsec_ind_functions import *
#import op_methods

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def persontraffic(CTRL, FILE, tra_data, gen_data):

    energy_demand_person_traffic_total_country = []
    energy_demand_person_traffic_electrical_country = []
    energy_demand_person_traffic_hydrogen_country = []
    energy_demand_person_traffic_energycarriers_totalvalues = []
    modalsplit_percountry = []

    # Calculate energy demand person traffic (car, rail, bus, ship, ...)
    for country in range(0, len(CTRL.CONSIDERED_COUNTRIES)):

        # Calculate specific value Personkilometer per resident
        for i_country_perskm in range(0, len(tra_data.personkm_road_train)):    
            
            if CTRL.CONSIDERED_COUNTRIES[country] == tra_data.personkm_road_train["country_en"][i_country_perskm]:
            
                for i_country_population_his in range(0, len(gen_data.pop_table)):

                    if gen_data.pop_table["Country"][i_country_population_his] == CTRL.CONSIDERED_COUNTRIES[country]:
                        
                        #print(gen_data.pop_table[str(tra_data.personkm_road_train["year"][i_country_perskm]).split(".")[0]][i_country_population_his])
                        #print(tra_data.personkm_road_train["person_km"][i_country_perskm])
                        #print(tra_data.personkm_road_train["person_km"][i_country_perskm])

                        calc_personkm = (tra_data.personkm_road_train["person_km"][i_country_perskm]*
                            (10**9)/gen_data.pop_table[str(tra_data.personkm_road_train["year"][i_country_perskm]).split(".")[0]][i_country_population_his])
                            # Calculation factor unit 10^9/population of the value year to get a personspecific calulation factor

        # Calculate specific value pessangerkilometer per resident
        for i_country_pesskm in range(0, len(tra_data.passengerkm_flight)):    
            
            if CTRL.CONSIDERED_COUNTRIES[country] == tra_data.passengerkm_flight["country_en"][i_country_pesskm]:
            
                for i_country_population_his in range(0, len(gen_data.pop_table)):

                    if gen_data.pop_table["Country"][i_country_population_his] == CTRL.CONSIDERED_COUNTRIES[country]:

                        calc_pesskm = (tra_data.passengerkm_flight["pessenger_km"][i_country_pesskm]*
                            (10**6)/gen_data.pop_table[str(tra_data.passengerkm_flight["year"][i_country_pesskm]).split(".")[0]][i_country_population_his]) 
                            # Calculation factor unit 10^9/population of the value year to get a personspecific calulation factor
                        break
                break

        # Get forecast population
        for i_country_pop_forecast in range(0, len(gen_data.pop.pop_forecast)):

            for i_abbrev in range(0, len(gen_data.gen_abbreviations)):
            
                if (CTRL.CONSIDERED_COUNTRIES[country] == gen_data.gen_abbreviations["Country"][i_abbrev] and
                        gen_data.gen_abbreviations["Internationale Abkuerzung"][i_abbrev] == gen_data.pop.pop_forecast["Country"][i_country_pop_forecast]):
                    
                    #print(gen_data.gen_abbreviations["Country"][i_abbrev])
                    #print(gen_data.pop.pop_forecast["Country [-]"][i_country_pop_forecast])

                    forecast_population_country = gen_data.pop.pop_forecast["Population Prog Year [Pers.]"][i_country_pop_forecast]

                    #print(forecast_population_country)
                        # per country und dann noch country names davor aus Country_Names_Abbreviations
                        # per nuts 2 region: auf nuts_model mit abbreviations und beachte alte und neue schreibweise mit y 
                    break

        # Get modal split per country
        if CTRL.TRA_MODALSPLIT_MODELTYPE == "Constant":

            # Car
            for i_modal_split_car in range(0, len(tra_data.modalsplit_car)):
                if tra_data.modalsplit_car["country_en"][i_modal_split_car] == CTRL.CONSIDERED_COUNTRIES[country]:     
                    modal_split_car_country = tra_data.modalsplit_car[2018][i_modal_split_car]
                    break
        
            # Rail
            for i_modal_split_rail in range(0, len(tra_data.modalsplit_rail)):
                if tra_data.modalsplit_rail["country_en"][i_modal_split_rail] == CTRL.CONSIDERED_COUNTRIES[country]:
                    modal_split_rail_country = tra_data.modalsplit_rail[2018][i_modal_split_rail]
                    break
        
            # Bus
            for i_modal_split_bus in range(0, len(tra_data.modalsplit_bus)):
                if tra_data.modalsplit_bus["country_en"][i_modal_split_bus] == CTRL.CONSIDERED_COUNTRIES[country]:
                    modal_split_bus_country = tra_data.modalsplit_bus[2018][i_modal_split_bus]
                    break
            
            modalsplit_percountry = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], modal_split_car_country, modal_split_rail_country, modal_split_bus_country]], \
                ).append(modalsplit_percountry, ignore_index=True) 

        elif CTRL.TRA_MODALSPLIT_MODELTYPE == "Trend":

            #CTRL.IND_END_YEAR = 2018
            CTRL.IND_SKIP_YEARS = []
            coeff_content_car=[]
            coeff_content_rail=[]
            coeff_content_bus=[]
 
            # Car
            active_group=[CTRL.CONSIDERED_COUNTRIES[country]]
            idx_country=list(tra_data.modalsplit_car["country_en"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            idx_group=[idx_country]
            delta_active=False

            equation, eq_right, noData= linear_regression_single_country_time(CTRL, tra_data.modalsplit_car, 
                                                                idx_country)       
            if noData:
                koef=[np.nan, np.nan]
            else:
                koef=calc_koef(equation, eq_right)
            coeff_content_car=save_koef(coeff_content_car, active_group, koef, False, delta_active)
                    
            coeff_vol_df_car=pd.DataFrame(coeff_content_car, columns=["Country", "coeff_0", "coeff_1", 
                                                            "coeff_c"])

            idx_coeff=list(coeff_vol_df_car["Country"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            modal_split_car_country=(coeff_vol_df_car["coeff_0"][idx_coeff]
                    +coeff_vol_df_car["coeff_1"][idx_coeff]*CTRL.FORECAST_YEAR
                    +coeff_vol_df_car["coeff_c"][idx_coeff])

            # Rail
            equation, eq_right, noData= linear_regression_single_country_time(CTRL, tra_data.modalsplit_rail, 
                                                                 idx_country)       
            if noData:
                koef=[np.nan, np.nan]
            else:
                koef=calc_koef(equation, eq_right)
            coeff_content_rail=save_koef(coeff_content_rail, active_group, koef, False, delta_active)
                    
            coeff_vol_df_rail=pd.DataFrame(coeff_content_rail, columns=["Country", "coeff_0", "coeff_1", 
                                                            "coeff_c"])

            idx_coeff=list(coeff_vol_df_rail["Country"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            modal_split_rail_country=(coeff_vol_df_rail["coeff_0"][idx_coeff]
                    +coeff_vol_df_rail["coeff_1"][idx_coeff]*CTRL.FORECAST_YEAR
                    +coeff_vol_df_rail["coeff_c"][idx_coeff])

            # Bus
            equation, eq_right, noData= linear_regression_single_country_time(CTRL, tra_data.modalsplit_bus, 
                                                                idx_country)       
            if noData:
                koef=[np.nan, np.nan]
            else:
                koef=calc_koef(equation, eq_right)
            coeff_content_bus=save_koef(coeff_content_bus, active_group, koef, False, delta_active)
                    
            coeff_vol_df_bus=pd.DataFrame(coeff_content_bus, columns=["Country", "coeff_0", "coeff_1", 
                                                            "coeff_c"])

            idx_coeff=list(coeff_vol_df_bus["Country"]).index(CTRL.CONSIDERED_COUNTRIES[country])
            modal_split_bus_country=(coeff_vol_df_bus["coeff_0"][idx_coeff]
                    +coeff_vol_df_bus["coeff_1"][idx_coeff]*CTRL.FORECAST_YEAR
                    +coeff_vol_df_bus["coeff_c"][idx_coeff])

            if (modal_split_car_country > 95 or modal_split_car_country < 0 or modal_split_rail_country > 95 or modal_split_rail_country < 0 or
                modal_split_bus_country > 95 or modal_split_bus_country < 0): 
                modal_split_car_country = tra_data.modalsplit_car[2018][idx_country]
                modal_split_rail_country = tra_data.modalsplit_rail[2018][idx_country]
                modal_split_bus_country = tra_data.modalsplit_bus[2018][idx_country]

            if (modal_split_car_country+modal_split_rail_country+modal_split_bus_country >=102 or 
                modal_split_car_country+modal_split_rail_country+modal_split_bus_country <=98):
                print("Modal Split in pessenger transport "+ CTRL.CONSIDERED_COUNTRIES[country] + " is not correct.")
                sum_modalsplit=modal_split_car_country+modal_split_rail_country+modal_split_bus_country

            modalsplit_percountry = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], modal_split_car_country, modal_split_rail_country, modal_split_bus_country]], \
                ).append(modalsplit_percountry, ignore_index=True) 
                
        #coeff_vol_df.to_excel(result_vol_koef, sheet_name=industry, index=False, startrow=0)
        
        # Calculate final values
        #print(str(tra_data.energypermodal["car"][0]))
        #print(calc_personkm)
        #print(forecast_population_country)
        car = calc_personkm*forecast_population_country*(modal_split_car_country/100)  # Pkm        #  *tra_data.tra_pt_energypermodal["car"][0]*3.6*10**-9 # PJ
        rail = calc_personkm*forecast_population_country*(modal_split_rail_country/100) # Pkm
        bus = calc_personkm*forecast_population_country*(modal_split_bus_country/100)  # Pkm
        flight = calc_pesskm*forecast_population_country                                # Pkm       #   *tra_data.tra_pt_energypermodal["flight"][0] # PJ
        ship = 0 # PJ

        ## Electrical
        value_forecast_year_car_electrical = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_car_electrical)
        value_forecast_year_rail_electrical = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_rail_electrical)
        value_forecast_year_bus_electrical = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_bus_electrical)
        value_forecast_year_flight_electrical = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_flight_electrical)

        ## Hydrogen
        value_forecast_year_car_hydrogen = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_car_hydrogen)
        value_forecast_year_rail_hydrogen = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_rail_hydrogen)
        value_forecast_year_bus_hydrogen = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_bus_hydrogen)
        value_forecast_year_flight_hydrogen = calc_energycarrier_forecast(CTRL, country, tra_data.tra_pt_energysources_flight_hydrogen)           

        # Resulting energy consumption
        ## Total
        energy_demand_person_traffic_total_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], car*10**-9, rail*10**-9, bus*10**-9, flight*10**-9, ship*10**-9, 
            (car+rail+bus+flight+ship)*10**-9]], \
            ).append(energy_demand_person_traffic_total_country, ignore_index=True) 

        ## Electrical
        #for ENERGYCARRIER  if = ['Elec', 'Hydrogen', 'Heat']
        car_elec = car*(value_forecast_year_car_electrical/100)*tra_data.tra_pt_energypermodal["car"][0]*10**-9  #TWh       #*3.6*10**-9 # PJ
        rail_elec = rail*(value_forecast_year_rail_electrical/100)*tra_data.tra_pt_energypermodal["rail"][0]*10**-9  
        bus_elec = bus*(value_forecast_year_bus_electrical/100)*tra_data.tra_pt_energypermodal["bus"][0]*10**-9
        flight_elec = flight*(value_forecast_year_flight_electrical/100)*tra_data.tra_pt_energypermodal["flight"][0]*0.27777777777778  #TWh    # PJ
        ship_elec = ship*0

        energy_demand_person_traffic_electrical_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], car_elec, rail_elec, bus_elec, flight_elec, ship_elec, 
            car_elec+rail_elec+bus_elec+flight_elec+ship_elec]], \
            ).append(energy_demand_person_traffic_electrical_country, ignore_index=True)

        ## Hydrogen
        car_hydro = car*(value_forecast_year_car_hydrogen/100)*tra_data.tra_pt_energypermodal["car"][2]*10**-9 # PJ
        rail_hydro = rail*(value_forecast_year_rail_hydrogen/100)*tra_data.tra_pt_energypermodal["rail"][2]*10**-9  
        bus_hydro = bus*(value_forecast_year_bus_hydrogen/100)*tra_data.tra_pt_energypermodal["bus"][2]*10**-9
        flight_hydro = flight*(value_forecast_year_flight_hydrogen/100)*tra_data.tra_pt_energypermodal["flight"][2]*0.27777777777778 #TWh # PJ
        ship_hydro = ship*0

        energy_demand_person_traffic_hydrogen_country = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], car_hydro, rail_hydro, bus_hydro, flight_hydro, ship_hydro, 
            car_hydro+rail_hydro+bus_hydro+flight_hydro+ship_hydro]], \
            ).append(energy_demand_person_traffic_hydrogen_country, ignore_index=True)

        ## Total of all
        energy_demand_person_traffic_energycarriers_totalvalues = pd.DataFrame([[CTRL.CONSIDERED_COUNTRIES[country], car_elec+rail_elec+bus_elec+flight_elec+ship_elec, 
            car_hydro+rail_hydro+bus_hydro+flight_hydro+ship_hydro]], \
            ).append(energy_demand_person_traffic_energycarriers_totalvalues, ignore_index=True)

    tra_pt = PERSON_TRAFFIC(energy_demand_person_traffic_total_country, energy_demand_person_traffic_electrical_country, 
        energy_demand_person_traffic_hydrogen_country, energy_demand_person_traffic_energycarriers_totalvalues, modalsplit_percountry)

    return tra_pt

class PERSON_TRAFFIC():

    def __init__(self, energy_demand_person_traffic_total_country, energy_demand_person_traffic_electrical_country, energy_demand_person_traffic_hydrogen_country, 
        energy_demand_person_traffic_energycarriers_totalvalues, modalsplit_percountry):

        self.energy_demand_person_traffic_total_country = energy_demand_person_traffic_total_country.rename({0:"Country", 1:"pt_car [Pkm]", 2:"pt_rail [Pkm]", 
            3:"pt_bus [Pkm]", 4:"pt_flight [Pkm]", 5:"pt_ship [Pkm]", 6:"pt_total [Pkm]"}, axis='columns')
        self.energy_demand_person_traffic_electrical_country = energy_demand_person_traffic_electrical_country.rename({0:"Country", 1:"pt_car_elec [TWh]", 2:"pt_rail_elec [TWh]", 
            3:"pt_bus_elec [TWh]", 4:"pt_flight_elec [TWh]", 5:"pt_ship_elec [TWh]", 6:"pt_total_elec [TWh]"}, axis='columns')
        self.energy_demand_person_traffic_hydrogen_country = energy_demand_person_traffic_hydrogen_country.rename({0:"Country", 1:"pt_car_hydrogen [TWh]", 2:"pt_rail_hydrogen [TWh]", 
            3:"pt_bus_hydrogen [TWh]", 4:"pt_flight_hydrogen [TWh]", 5:"pt_ship_hydrogen [TWh]", 6:"pt_total_hydrogen [TWh]"}, axis='columns')
        self.energy_demand_person_traffic_energycarriers_totalvalues = energy_demand_person_traffic_energycarriers_totalvalues.rename({0:"Country", 1:"pt_total_elec [TWh]", 
            2:"pt_total_hydrogen [TWh]"}, axis='columns')
        self.modalsplit_percountry = modalsplit_percountry.rename({0:"Country", 1:"pt_car [%]", 2:"pt_rail [%]", 3:"pt_bus [%]"}, axis='columns')

def calc_energycarrier_forecast(CTRL, country, value_table):

    if CTRL.FORECAST_YEAR < 2018:
        print("The forcast year is not in the right range!")
    elif CTRL.FORECAST_YEAR <= 2020 and CTRL.FORECAST_YEAR >= 2018:

        for i_country in range(0, len(value_table)):

            if value_table["Country"][i_country]==CTRL.CONSIDERED_COUNTRIES[country]:

                trend = (((value_table[2020][i_country]/value_table[2018][i_country])**(1/(2020-2018)))-1)*100 # %
                value_forecast_year = value_table[2018][i_country]*(1+(trend/100))**(CTRL.FORECAST_YEAR-2018) # %
                
                if True == math.isnan(value_forecast_year):
                    value_forecast_year = 0
                break

    elif CTRL.FORECAST_YEAR <= 2030 and CTRL.FORECAST_YEAR > 2020: 

        for i_country in range(0, len(value_table)):

            if value_table["Country"][i_country]==CTRL.CONSIDERED_COUNTRIES[country]:

                trend = (((value_table[2030][i_country]/value_table[2020][i_country])**(1/(2030-2020)))-1)*100 # %
                value_forecast_year = value_table[2020][i_country]*(1+(trend/100))**(CTRL.FORECAST_YEAR-2020) # %
                
                if True == math.isnan(value_forecast_year):
                    value_forecast_year = 0
                break
        
    elif CTRL.FORECAST_YEAR <= 2050 and CTRL.FORECAST_YEAR > 2030:

        for i_country in range(0, len(value_table)):

            if value_table["Country"][i_country]==CTRL.CONSIDERED_COUNTRIES[country]:

                trend = (((value_table[2050][i_country]/value_table[2030][i_country])**(1/(2050-2030)))-1)*100 # %
                value_forecast_year = value_table[2030][i_country]*(1+(trend/100))**(CTRL.FORECAST_YEAR-2030) # %

                if True == math.isnan(value_forecast_year):
                    value_forecast_year = 0
                break
    
    return value_forecast_year
