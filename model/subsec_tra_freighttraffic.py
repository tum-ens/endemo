###############################################################################                                                                                   
# Forecast of the subsector road traffic for traffic
###############################################################################
"""The module calculates the energy demand of the subsector freight traffic for 
traffic.
"""
###############################################################################
#Imports
###############################################################################
from libraries import *
import subsec_tra_persontraffic
from op_methods import *

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def freighttraffic(CTRL, FILE, tra_data, gen_data, ind_data):

    ft_volume_sum_forecast, ft_volume_sum_historical, production_sum_historical_singlesectors = sum_production_volume(CTRL, FILE, ind_data, tra_data)

    ft_Mil_tkm = []
    energy_demand_ft_elec =[]
    energy_demand_ft_h2 = []
    ft_energy_total = []
    modalsplit_body = []
    modalsplit_body_scaled = []

    # Calculate energy demand freight traffic (rail, road, ship, ...)
    for country in CTRL.CONSIDERED_COUNTRIES:
        
        #######################################################################
        #Get modal split per country (distribution between road, rail and ship)
        #######################################################################    
        idx_modal_split_road = list(tra_data.modalsplit_ft_road["Country"]).index(country)
        idx_modal_split_rail = list(tra_data.modalsplit_ft_rail["Country"]).index(country)
        idx_modal_split_ship = list(tra_data.modalsplit_ft_ship["Country"]).index(country)
        
        dict_modal_split = {}
        modalsplit_percountry = [country]
        modalsplit_percountry_scaled = [country]
        
        if CTRL.TRA_MODALSPLIT_SCENARIO == "Historical":
            if CTRL.TRA_MODALSPLIT_METHOD == "Constant":
                for tra_type, idx_modal_split in zip(["road", "rail", "ship"],[idx_modal_split_road,idx_modal_split_rail,idx_modal_split_ship]):
                    dict_modal_split[tra_type] = getattr(tra_data,"modalsplit_ft_"+tra_type)[2018][idx_modal_split]
                    modalsplit_percountry.append(dict_modal_split[tra_type])
                modalsplit_percountry_scaled = modalsplit_percountry
    
            elif CTRL.TRA_MODALSPLIT_METHOD == "Trend":
                sum_modalsplit = 0
                for tra_type, idx_modal_split in zip(["road", "rail", "ship"],[idx_modal_split_road,idx_modal_split_rail,idx_modal_split_ship]):
                    equation, eq_right, noData= linear_regression_single_country_time(CTRL, getattr(tra_data,"modalsplit_ft_"+tra_type), 
                                                                        idx_modal_split, "TRA")       
                    if noData:
                        koef=[np.nan, np.nan]
                    else:
                        koef=calc_koef(equation, eq_right)
                    
                    modal_split=koef[0]+koef[1]*CTRL.FORECAST_YEAR
                    
                    if modal_split < 0:
                        dict_modal_split[tra_type] = 0
                    else:
                        dict_modal_split[tra_type] = modal_split
                        
                    sum_modalsplit += dict_modal_split[tra_type]
                    modalsplit_percountry.append(dict_modal_split[tra_type])
               
                # scale to 100%
                for tra_type, idx_modal_split in zip(["road", "rail", "ship"],[idx_modal_split_road,idx_modal_split_rail,idx_modal_split_ship]):
                    dict_modal_split[tra_type] = dict_modal_split[tra_type]*100/sum_modalsplit
                    modalsplit_percountry_scaled.append(dict_modal_split[tra_type])
                
        elif CTRL.TRA_MODALSPLIT_SCENARIO == "User-defined":
            for tra_type, idx_modal_split in zip(["road", "rail", "ship"],[idx_modal_split_road,idx_modal_split_rail,idx_modal_split_ship]):
                dict_modal_split[tra_type] = interpolate(getattr(tra_data,"modalsplit_ft_"+tra_type), CTRL.FORECAST_YEAR, idx_modal_split)
                modalsplit_percountry.append(dict_modal_split[tra_type])
            modalsplit_percountry_scaled = modalsplit_percountry
        
        modalsplit_body.append(modalsplit_percountry)
        modalsplit_body_scaled.append(modalsplit_percountry_scaled)

        #######################################################################
        # Get tkm
        #######################################################################
        # Get km
        # Get historical km per transport type group (road, rail and ship OR flight)
        ## Calculate km which are made by road, rail and ship freight transport
        idx_tonnekm_road_rail_ship = list(tra_data.tonnekm_road_rail_ship["Country"]).index(country)
        idx_ft_volume_his_total = list(ft_volume_sum_historical["Country"]).index(country)
        idx_ft_volume_his_flight = list(tra_data.tra_ft_volume_flight_his["Country"]).index(country)

        if CTRL.TRA_INDUSTRY_REST == True:
            idx_ind_rest = list(tra_data.rest_table['Country']).index(country)
            ind_rest_proportion = (tra_data.rest_table['Rest el'][idx_ind_rest]+tra_data.rest_table['Rest heat'][idx_ind_rest])/2/100
            ft_volume_his_total = (ft_volume_sum_historical["Amount [t]"][idx_ft_volume_his_total] 
                                  * (1 + ind_rest_proportion))
            ft_volume_his_flight = (tra_data.tra_ft_volume_flight_his["Flight_tonne [t]"][idx_ft_volume_his_flight] 
                                  * (1 + ind_rest_proportion))

        else:
            ft_volume_his_total = ft_volume_sum_historical["Amount [t]"][idx_ft_volume_his_total] 
            ft_volume_his_flight = tra_data.tra_ft_volume_flight_his["Flight_tonne [t]"][idx_ft_volume_his_flight] 
            
        if ft_volume_his_total != 0:
            calc_km_road_rail_ship = (tra_data.tonnekm_road_rail_ship["Mil. tkm"][idx_tonnekm_road_rail_ship]*(10**6)/ # from Mil. tkm -> tkm
                                  (ft_volume_his_total - ft_volume_his_flight)) 
        else:
            calc_km_road_rail_ship = 0 # assumption: if there is a value in tkm, 100km transport per tonn is given
        ## Calculate km which are made by flight freight transport
        idx_tonnekm_flight = list(tra_data.tonnekm_flight["Country"]).index(country)
        
        if ft_volume_his_flight != 0:
            calc_km_flight = (tra_data.tonnekm_flight["tonne_km"][idx_tonnekm_flight]
                              /ft_volume_his_flight)
        else:
            calc_km_flight = 0
            print("No freight air transport in ", country)
        
        # Get t
        # Get forecast freight volume and distributopn per transport type group
        ## Calculate forecast freight volume per country
        idx_ft_volume_forecast = list(ft_volume_sum_forecast["Country"]).index(country)
        if CTRL.TRA_INDUSTRY_REST == True:
            ft_volume_forecast = (ft_volume_sum_forecast["Amount [t]"][idx_ft_volume_forecast] 
                                  + ind_rest_proportion * ft_volume_sum_historical["Amount [t]"][idx_ft_volume_his_total]
                                  *(1 + CTRL.IND_REST_PROGRESS/100)**(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1))
        else:
            ft_volume_forecast = ft_volume_sum_forecast["Amount [t]"][idx_ft_volume_forecast]

        ## Calculate propotion of freight volume transported by flight
        if ft_volume_his_total != 0:
            prop_volume_flight = (tra_data.tra_ft_volume_flight_his["Flight_tonne [t]"][idx_ft_volume_his_flight]/
                                  ft_volume_his_total)
        else:
            prop_volume_flight = 1
            
        # Get tkm 
        road_tkm = (calc_km_road_rail_ship*ft_volume_forecast*(1-prop_volume_flight)
                *(dict_modal_split["road"]/100))  # tkm
        rail_tkm = (calc_km_road_rail_ship*ft_volume_forecast*(1-prop_volume_flight)
                *(dict_modal_split["rail"]/100)) # tkm
        ship_tkm = (calc_km_road_rail_ship*ft_volume_forecast*(1-prop_volume_flight)
                *(dict_modal_split["ship"]/100)) # tkm
        flight_tkm = calc_km_flight*(ft_volume_forecast*prop_volume_flight) # tkm
        
        # Resulting tkm
        total_tkm = road_tkm+rail_tkm+ship_tkm+flight_tkm
        ft_Mil_tkm.append([country, road_tkm*(10**-6), rail_tkm*(10**-6), ship_tkm*(10**-6), flight_tkm*(10**-6), total_tkm*(10**-6)])
        dict_tkm = {"road":road_tkm, "rail":rail_tkm, "ship":ship_tkm, "flight":flight_tkm}    

        #######################################################################
        # Get distribution of energy carriers
        #######################################################################
        # Get percentual distribution of energy carriers for different transport types.
        # Electrical and hydrogen percents are calculated based on 
        # ... assumed state in foothold years (from external studies), assuming a percentual yearly change between them.
        # The rest is driven by fossil fuels.
        dict_forecast_energycarrier_distrib = {}
        
        for energy_type in ["elec", "h2"]:
            dict_forecast_energycarrier_distrib[energy_type] = {}
            for tra_type in ["road", "rail", "ship", "flight"]:
                data_table = getattr(tra_data, "tra_ft_energysources_"+tra_type+"_"+energy_type)
                dict_forecast_energycarrier_distrib[energy_type][tra_type] = foothold_year_forecast(CTRL.FORECAST_YEAR, country, data_table, [2020, 2030, 2040, 2050])
        
        #######################################################################
        #Get energy demand
        ####################################################################### 
        # conversion factor from MJ/tkm in TWh/tkm
        fact = 0.277778*10**-9

        # Electrical
        energy_type = "elec"
        dict_energy_elec = {}
        energy_elec_total = 0
        energy_demand_country = [country]
        idx_energy_carrier = list(tra_data.tra_ft_energypersourcepermodal["Energy consumption MJ/tkm"]).index("Electricity")
        for tra_type in ["road", "rail", "ship", "flight"]:
            #road_elec = (value_forecast_year_road_elec/100)*road_tkm*tra_data.tra_ft_energypersourcepermodal["road"][0]*0.277778*10**-9
            dict_energy_elec[tra_type] = (dict_tkm[tra_type] * dict_forecast_energycarrier_distrib[energy_type][tra_type]/100 
                                          * tra_data.tra_ft_energypersourcepermodal[tra_type][idx_energy_carrier]
                                          * fact) # TWh
            energy_demand_country.append(dict_energy_elec[tra_type])
            energy_elec_total += dict_energy_elec[tra_type]

        energy_demand_country.append(energy_elec_total)
        energy_demand_ft_elec.append(energy_demand_country)

        # Hydrogen
        energy_type = "h2"
        dict_energy_h2 = {}
        energy_h2_total = 0
        energy_demand_country = [country]
        idx_energy_carrier = list(tra_data.tra_ft_energypersourcepermodal["Energy consumption MJ/tkm"]).index("Hydrogen")
        for tra_type in ["road", "rail", "ship", "flight"]:
            # road_hydro = (value_forecast_year_road_h2/100)*road_tkm*tra_data.tra_ft_energypersourcepermodal["road"][2]*0.277778*10**-9
            dict_energy_h2[tra_type] = (dict_tkm[tra_type] * dict_forecast_energycarrier_distrib[energy_type][tra_type]/100 
                                        * tra_data.tra_ft_energypersourcepermodal[tra_type][idx_energy_carrier]
                                        * fact)
            energy_demand_country.append(dict_energy_h2[tra_type])
            energy_h2_total += dict_energy_h2[tra_type]

        energy_demand_country.append(energy_h2_total)
        energy_demand_ft_h2.append(energy_demand_country)

        # Total of all
        ft_energy_total.append([country, energy_elec_total, energy_h2_total])
    
    #######################################################################
    # Postprocessing: make Data Frames
    ####################################################################### 
    ft_Mil_tkm = pd.DataFrame(ft_Mil_tkm, columns = ["Country", "ft_road [Mil. tkm]","ft_rail [Mil. tkm]", 
            "ft_ship [Mil. tkm]", "ft_flight [Mil. tkm]", "ft_total [Mil. tkm]"])
    energy_demand_ft_elec = pd.DataFrame(energy_demand_ft_elec, columns = ["Country", "ft_road_elec [TWh]","ft_rail_elec [TWh]", 
            "ft_ship_elec [TWh]", "ft_flight_elec [TWh]", "ft_total_elec [TWh]"])
    energy_demand_ft_h2= pd.DataFrame(energy_demand_ft_h2, columns = ["Country","ft_road_h2 [TWh]", "ft_rail_h2 [TWh]", 
            "ft_ship_h2 [TWh]", "ft_flight_h2 [TWh]", "ft_total_h2 [TWh]"])
    ft_energy_total = pd.DataFrame(ft_energy_total, columns = ["Country", "ft_total_elec [TWh]", "ft_total_h2 [TWh]"])
    modalsplit_percountry = pd.DataFrame(modalsplit_body, columns = ["Country", "ft_road [%]", "ft_rail [%]", "ft_ship [%]"])
    modalsplit_percountry_scaled = pd.DataFrame(modalsplit_body_scaled, columns = ["Country", "ft_road [%]", "ft_rail [%]", "ft_ship [%]"])
    
    
    tra_ft = FREIGHT_TRAFFIC(ft_volume_sum_forecast, ft_volume_sum_historical, ft_Mil_tkm, 
        energy_demand_ft_elec, energy_demand_ft_h2, ft_energy_total, modalsplit_percountry, modalsplit_percountry_scaled,
        production_sum_historical_singlesectors)

    return tra_ft

class FREIGHT_TRAFFIC():

    def __init__(self, ft_volume_sum_forecast, ft_volume_sum_historical, ft_Mil_tkm, 
        energy_demand_ft_elec, energy_demand_ft_h2, ft_energy_total, 
        modalsplit_percountry,modalsplit_percountry_scaled, production_sum_historical_singlesectors):

        self.ft_volume_sum_forecast = ft_volume_sum_forecast
        self.ft_volume_sum_historical = ft_volume_sum_historical
        self.ft_Mil_tkm = ft_Mil_tkm
        self.energy_demand_ft_elec = energy_demand_ft_elec
        self.energy_demand_ft_h2 = energy_demand_ft_h2     
        self.ft_energy_total = ft_energy_total
        self.modalsplit_percountry = modalsplit_percountry
        self.modalsplit_percountry_scaled = modalsplit_percountry_scaled
        self.production_sum_historical_singlesectors = production_sum_historical_singlesectors
        
        
def sum_production_volume(CTRL, FILE, ind_data, tra_data):

    for col_name, info_type in zip(["Amount [kt]", CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS],["Forecasted", "Hystorical"]) :

        if info_type == "Forecasted":
            # Import result of industry sector of production volume
            production_per_land = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_IND_VOLUME_FORECAST),sheet_name=None,skiprows=0)
            
            dict_production_per_land = {}
            all_ind_sectors = CTRL.IND_SUBECTORS
            for industry in all_ind_sectors:
                dict_production_per_land[industry] = production_per_land[industry]
        
        elif info_type == "Hystorical":
            # Industry sector of production volume
            
            all_ind_sectors = ["steel", "alu_prim", "alu_sec", "copper_prim",  "copper_sec", "paper","cement","glass","chlorine","ammonia","aromatics","ethylene","propylene","methanol"]
            dict_production_per_land = {}
            for industry in all_ind_sectors:
                dict_production_per_land[industry] = getattr(tra_data, industry+"_table")

        add = []
        production_sum_singlesectors_body = []
        production_sum_singlesectors_col_name = [industry+" [t]" for industry in all_ind_sectors]
        production_sum_singlesectors_col_name.insert(0, "Country")
        for country in CTRL.CONSIDERED_COUNTRIES:
            calc_sum = 0
            production_sum_singlesectors_body_row = [country]
            for industry in all_ind_sectors:
                try:
                    idx_ind_production = list(dict_production_per_land[industry]["Country"]).index(country)
                except:
                    idx_ind_production = -1
                if idx_ind_production != -1:
                    ind_production = dict_production_per_land[industry][col_name][idx_ind_production]
                else:
                    ind_production = 0
                production_sum_singlesectors_body_row.append(ind_production*1000) # from tausend tonnes in tonnes
                
                calc_sum += ind_production*1000 # from tausend tonnes in tonnes
            
            production_sum_singlesectors_body.append(production_sum_singlesectors_body_row)

            add.append([country, calc_sum])

        # Get resulting sum of production volume for historical data or forecast year
        if info_type == "Forecasted":
            production_sum_forecast = pd.DataFrame(add, columns=["Country", "Amount [t]"])
            production_sum_forecast_singlesectors = pd.DataFrame(production_sum_singlesectors_body, columns = production_sum_singlesectors_col_name)
        elif info_type == "Hystorical":
            production_sum_historical = pd.DataFrame(add, columns=["Country", "Amount [t]"])
            production_sum_historical_singlesectors = pd.DataFrame(production_sum_singlesectors_body, columns = production_sum_singlesectors_col_name)

    return production_sum_forecast, production_sum_historical, production_sum_historical_singlesectors