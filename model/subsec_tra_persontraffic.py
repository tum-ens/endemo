###############################################################################                                                                                   
# Forecast of the subsector person traffic for traffic
###############################################################################
"""The module calculates the energy demand of the subsector person traffic for 
traffic.
"""
###############################################################################
#Imports
###############################################################################
from libraries import *
from op_methods import *

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def persontraffic(CTRL, FILE, tra_data, gen_data):
    # pf = person traffic

    modalsplit_body = []
    modalsplit_body_scaled = []
    pt_Mrd_pkm = []
    energy_demand_pt_elec = []
    energy_demand_pt_h2 = []
    pt_energy_total = []

    # Calculate energy demand person traffic (car, rail, bus, ship, flight)
    for country in CTRL.CONSIDERED_COUNTRIES:
       
        #######################################################################
        #Get modal split per country (distribution between car, rail and bus)
        #######################################################################   
        idx_modal_split_car = list(tra_data.modalsplit_pt_car["Country"]).index(country)
        idx_modal_split_rail = list(tra_data.modalsplit_pt_rail["Country"]).index(country)
        idx_modal_split_bus = list(tra_data.modalsplit_pt_bus["Country"]).index(country)
        
        dict_modal_split = {}
        modalsplit_percountry = [country]
        modalsplit_percountry_scaled = [country]
        
        if CTRL.TRA_MODALSPLIT_SCENARIO == "Historical":
            if CTRL.TRA_MODALSPLIT_METHOD == "Constant":
                for tra_type, idx_modal_split in zip(["car", "rail", "bus"],[idx_modal_split_car,idx_modal_split_rail,idx_modal_split_bus]):
                    dict_modal_split[tra_type] = getattr(tra_data,"modalsplit_pt_"+tra_type)[CTRL.REF_YEAR][idx_modal_split]
                    modalsplit_percountry.append(dict_modal_split[tra_type])
                modalsplit_percountry_scaled = modalsplit_percountry
    
            elif CTRL.TRA_MODALSPLIT_METHOD == "Trend":
                sum_modalsplit = 0
                for tra_type, idx_modal_split in zip(["car", "rail", "bus"],[idx_modal_split_car,idx_modal_split_rail,idx_modal_split_bus]):
                    equation, eq_right, noData= linear_regression_single_country_time(CTRL, getattr(tra_data,"modalsplit_pt_"+tra_type), 
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
                for tra_type, idx_modal_split in zip(["car", "rail", "bus"],[idx_modal_split_car,idx_modal_split_rail,idx_modal_split_bus]):
                    dict_modal_split[tra_type] = dict_modal_split[tra_type]*100/sum_modalsplit
                    modalsplit_percountry_scaled.append(dict_modal_split[tra_type])
        
        elif CTRL.TRA_MODALSPLIT_SCENARIO == "User-defined":
            for tra_type, idx_modal_split in zip(["car", "rail", "bus"],[idx_modal_split_car,idx_modal_split_rail,idx_modal_split_bus]):
                dict_modal_split[tra_type] = interpolate(getattr(tra_data,"modalsplit_pt_"+tra_type), CTRL.FORECAST_YEAR, idx_modal_split)
                modalsplit_percountry.append(dict_modal_split[tra_type])
            modalsplit_percountry_scaled = modalsplit_percountry
        
        modalsplit_body.append(modalsplit_percountry)
        modalsplit_body_scaled.append(modalsplit_percountry_scaled)
        
        #######################################################################
        # Get pkm
        #######################################################################
        # Get km
        # Get historical km per transport type group (road and rail OR flight)
        ## Calculate pkm per resident which are made by road and rail passenger transport
        idx_pkm_road_rail = list(tra_data.personkm_road_rail["Country"]).index(country)
        idx_pop_his = list(gen_data.pop_table["Country"]).index(country)

        calc_km_road_rail = (tra_data.personkm_road_rail["Mrd. pkm"][idx_pkm_road_rail]*(10**9) # from Mrd. pkm -> pkm
                             /gen_data.pop_table[str(int(tra_data.personkm_road_rail["year"][idx_pkm_road_rail]))][idx_pop_his])

        ## Calculate pkm per resident which are made by flight passenger transport
        idx_pkm_flight = list(tra_data.personkm_flight["Country"]).index(country)
        
        calc_km_flight = (tra_data.personkm_flight["Mil. pkm"][idx_pkm_flight]*(10**6) # from Mil. pkm -> pkm
                       /gen_data.pop_table[str(int(tra_data.personkm_flight["year"][idx_pkm_flight]))][idx_pop_his]) 

        # Get p (persons)
        # Get forecast of population (persons = passengers)
        #abb = gen_data.abbreviations["Abbreviation"][list(gen_data.abbreviations["Country"]).index(country)]
        idx_pop_forecast = list(gen_data.pop_forecast_country["Country"]).index(country)
        pop_forecast = gen_data.pop_forecast_country[str(CTRL.FORECAST_YEAR)][idx_pop_forecast]

        
        # Get pkm 
        
        car_pkm = calc_km_road_rail*pop_forecast*dict_modal_split["car"]/100  # Pkm
        rail_pkm = calc_km_road_rail*pop_forecast*dict_modal_split["rail"]/100 # Pkm
        bus_pkm = calc_km_road_rail*pop_forecast*dict_modal_split["bus"]/100  # Pkm
        ship_pkm = 0
        flight_pkm = calc_km_flight*pop_forecast                                # Pkm       
        
        # Resulting pkm
        total_pkm = car_pkm + rail_pkm + bus_pkm + ship_pkm + flight_pkm
        pt_Mrd_pkm.append([country, car_pkm*(10**-9), rail_pkm*(10**-9), bus_pkm*(10**-9), ship_pkm*(10**-9), flight_pkm*(10**-9), total_pkm*(10**-9)])
        dict_pkm = {"car":car_pkm, "rail":rail_pkm, "bus":bus_pkm, "ship":ship_pkm, "flight":flight_pkm}    

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
            for tra_type in ["car", "rail", "bus", "ship", "flight"]:
                data_table = getattr(tra_data, "tra_pt_energysources_"+tra_type+"_"+energy_type)
                dict_forecast_energycarrier_distrib[energy_type][tra_type] = foothold_lin_forecast(CTRL.FORECAST_YEAR, CTRL.REF_YEAR, country, data_table, [2020, 2030, 2040, 2050])
        
        #######################################################################
        #Get energy demand
        #######################################################################      
        # conversion factor from MJ/pkm in TWh/pkm
        fact_MJ = 10**-6/3600
        
        # Electrical
        energy_type = "elec"
        dict_energy_elec = {}
        energy_elec_total = 0
        energy_demand_country = [country]
        idx_energy_carrier = list(tra_data.tra_pt_energypersourcepermodal["Energy consumption MJ/pkm"]).index("Electricity")
        for tra_type in ["car", "rail", "bus", "ship"]:
            # car_elec = car*(value_forecast_year_car_elec/100)*tra_data.tra_pt_energypersourcepermodal["car"][0]*10**-9
            dict_energy_elec[tra_type] = (dict_pkm[tra_type] * dict_forecast_energycarrier_distrib[energy_type][tra_type]/100 
                                          * tra_data.tra_pt_energypersourcepermodal[tra_type][idx_energy_carrier]
                                          * fact_MJ) # TWh
            energy_demand_country.append(dict_energy_elec[tra_type])
            energy_elec_total += dict_energy_elec[tra_type]
            
        tra_type = "flight"
        dict_energy_elec[tra_type] = (dict_pkm[tra_type] * dict_forecast_energycarrier_distrib[energy_type][tra_type]/100 
                                      * tra_data.tra_pt_energypersourcepermodal[tra_type][idx_energy_carrier]
                                      * fact_MJ) # TWh
        energy_demand_country.append(dict_energy_elec[tra_type])
        energy_elec_total += dict_energy_elec[tra_type]

        energy_demand_country.append(energy_elec_total)
        energy_demand_pt_elec.append(energy_demand_country)

        # Hydrogen
        energy_type = "h2"
        dict_energy_h2 = {}
        energy_h2_total = 0
        energy_demand_country = [country]
        idx_energy_carrier = list(tra_data.tra_pt_energypersourcepermodal["Energy consumption MJ/pkm"]).index("Hydrogen")
        for tra_type in ["car", "rail", "bus", "ship"]:
            # car_hydro = car*(value_forecast_year_car_h2/100)*tra_data.tra_pt_energypermodal["car"][2]*10**-9 # PJ
            dict_energy_h2[tra_type] = (dict_pkm[tra_type] * dict_forecast_energycarrier_distrib[energy_type][tra_type]/100 
                                        * tra_data.tra_pt_energypersourcepermodal[tra_type][idx_energy_carrier]
                                        * fact_MJ)
            energy_demand_country.append(dict_energy_h2[tra_type])
            energy_h2_total += dict_energy_h2[tra_type]
            
        tra_type = "flight"
        dict_energy_h2[tra_type] = (dict_pkm[tra_type] * dict_forecast_energycarrier_distrib[energy_type][tra_type]/100 
                                    * tra_data.tra_pt_energypersourcepermodal[tra_type][idx_energy_carrier]
                                    * fact_MJ)
        energy_demand_country.append(dict_energy_h2[tra_type])
        energy_h2_total += dict_energy_h2[tra_type]

        energy_demand_country.append(energy_h2_total)
        energy_demand_pt_h2.append(energy_demand_country)

        # Total of all
        pt_energy_total.append([country, energy_elec_total, energy_h2_total])
    
    #######################################################################
    # Postprocessing: make Data Frames
    #######################################################################
        
    modalsplit_percountry = pd.DataFrame(modalsplit_body, columns = ["Country","pt_car [%]", "pt_rail [%]", "pt_bus [%]"])
    modalsplit_percountry_scaled = pd.DataFrame(modalsplit_body_scaled, columns = ["Country","pt_car [%]", "pt_rail [%]", "pt_bus [%]"])
    pt_Mrd_pkm = pd.DataFrame(pt_Mrd_pkm, columns = ["Country", "pt_car [Mrd. pkm]", "pt_rail [Mrd. pkm]", 
            "pt_bus [Mrd. pkm]", "pt_ship [Mrd. pkm]","pt_flight [Mrd. pkm]", "pt_total [Mrd. pkm]"])
    energy_demand_pt_elec = pd.DataFrame(energy_demand_pt_elec, columns = ["Country","pt_car_elec [TWh]", "pt_rail_elec [TWh]", 
            "pt_bus_elec [TWh]", "pt_ship_elec [TWh]","pt_flight_elec [TWh]", "pt_total_elec [TWh]"])
    energy_demand_pt_h2 = pd.DataFrame(energy_demand_pt_h2, columns = ["Country", "pt_car_h2 [TWh]","pt_rail_h2 [TWh]", 
            "pt_bus_h2 [TWh]", "pt_ship_h2 [TWh]", "pt_flight_h2 [TWh]", "pt_total_h2 [TWh]"])
    pt_energy_total = pd.DataFrame(pt_energy_total, columns = ["Country","pt_total_elec [TWh]", 
            "pt_total_h2 [TWh]"])
        
    tra_pt = PERSON_TRAFFIC(pt_Mrd_pkm, energy_demand_pt_elec, 
        energy_demand_pt_h2, pt_energy_total, modalsplit_percountry, modalsplit_percountry_scaled)

    return tra_pt

class PERSON_TRAFFIC():

    def __init__(self, pt_Mrd_pkm, energy_demand_pt_elec, energy_demand_pt_h2, 
        pt_energy_total, modalsplit_percountry, modalsplit_percountry_scaled):
        
        self.modalsplit_percountry = modalsplit_percountry
        self.modalsplit_percountry_scaled = modalsplit_percountry_scaled
        self.pt_Mrd_pkm = pt_Mrd_pkm
        self.energy_demand_pt_elec = energy_demand_pt_elec
        self.energy_demand_pt_h2 = energy_demand_pt_h2
        self.pt_energy_total = pt_energy_total

