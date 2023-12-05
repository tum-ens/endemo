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
from libraries import *  
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
        logger.info(" - Person traffic")
        self.tra_pt = subsec_tra_persontraffic.persontraffic(CTRL, FILE, tra_data, gen_data)   #person traffic = pt

        #------------------------------------------------------------------------------
        logger.info(" - Freight traffic")
        self.tra_ft = subsec_tra_freighttraffic.freighttraffic(CTRL, FILE, tra_data, gen_data, ind_data)   #freight traffic = ft

        #------------------------------------------------------------------------------
        # Absolute values of energy sources for both subsectors
        tra_ft_pt_energy_demand = []

        for country in CTRL.CONSIDERED_COUNTRIES:
            idx_pt = list(self.tra_pt.pt_energy_total["Country"]).index(country)
            idx_ft = list(self.tra_ft.ft_energy_total["Country"]).index(country)
                 
            tra_ft_pt_energy_demand.append([country, 
                self.tra_ft.ft_energy_total["ft_total_elec [TWh]"][idx_ft]+
                self.tra_pt.pt_energy_total["pt_total_elec [TWh]"][idx_pt], 
                0, 
                self.tra_ft.ft_energy_total["ft_total_h2 [TWh]"][idx_ft]+
                self.tra_pt.pt_energy_total["pt_total_h2 [TWh]"][idx_pt]])          
        self.tra_ft_pt_energy_demand = pd.DataFrame(tra_ft_pt_energy_demand, columns = ["Country", "Electricity [TWh]", 
            "Heat [TWh]", "Hydrogen [TWh]"])

        #------------------------------------------------------------------------------
        # NUTS2 for traffic

        pop_prognosis = gen_data.pop_forecast

        if CTRL.NUTS2_ACTIVATED:
        
            tra_energy_demand_NUTS2 = redistribution_NUTS2(CTRL.FORECAST_YEAR,self.tra_ft_pt_energy_demand, pop_prognosis, gen_data.abbreviations) #ind_sol.energy_demand
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"TRA"+FILE.FILENAME_OUTPUT_DEMAND_NUTS2)
            result_tra_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            tra_energy_demand_NUTS2.to_excel(result_tra_energy_demand_NUTS2,sheet_name="TRA", index=False, startrow=0)
            result_tra_energy_demand_NUTS2.close()

            # energy per modal and NUTS2
            energy_demand_pt_elec_nuts2 = redistribution_NUTS2(CTRL.FORECAST_YEAR,self.tra_pt.energy_demand_pt_elec, pop_prognosis, gen_data.abbreviations)
            energy_demand_pt_h2_nuts2 = redistribution_NUTS2(CTRL.FORECAST_YEAR,self.tra_pt.energy_demand_pt_h2, pop_prognosis, gen_data.abbreviations)
            energy_demand_ft_elec_nuts2 = redistribution_NUTS2(CTRL.FORECAST_YEAR,self.tra_ft.energy_demand_ft_elec, pop_prognosis, gen_data.abbreviations)
            energy_demand_ft_h2_nuts2 = redistribution_NUTS2(CTRL.FORECAST_YEAR,self.tra_ft.energy_demand_ft_h2, pop_prognosis, gen_data.abbreviations)

            # NUTS2 pkm or tkm
            # for tra_type, tra_km, unit in zip(["pt", "ft"],["pkm", "tkm"],["Mrd_", "Mil_"]):
            #     pkm_tkm_demand_NUTS2 = redistribution_NUTS2(CTRL.FORECAST_YEAR, getattr(self,"tra_"+tra_type, tra_type+unit+"_"+tra_km), pop_prognosis, gen_data.abbreviations)
            
            #     path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"TRA_"+tra_km+"_NUTS2_"+str(CTRL.FORECAST_YEAR)+".xlsx")
            #     result_pkm_tkm_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            #     pkm_tkm_demand_NUTS2.to_excel(result_pkm_tkm_demand_NUTS2,sheet_name=tra_km, index=False, startrow=0)
            #     result_pkm_tkm_demand_NUTS2.close()
            
            pkm_tkm_demand_NUTS2 = redistribution_NUTS2(CTRL.FORECAST_YEAR, self.tra_pt.pt_Mrd_pkm, pop_prognosis, gen_data.abbreviations)
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"TRA_pkm_NUTS2_"+str(CTRL.FORECAST_YEAR)+".xlsx")
            result_pkm_tkm_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            pkm_tkm_demand_NUTS2.to_excel(result_pkm_tkm_demand_NUTS2,sheet_name="pkm", index=False, startrow=0)
            result_pkm_tkm_demand_NUTS2.close()

            tra_energy_demand_NUTS2 = redistribution_NUTS2(CTRL.FORECAST_YEAR,self.tra_ft.ft_Mil_tkm, pop_prognosis, gen_data.abbreviations) 
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_tkm_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx')
            result_tra_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            tra_energy_demand_NUTS2.to_excel(result_tra_energy_demand_NUTS2,sheet_name="tkm", index=False, startrow=0)
            result_tra_energy_demand_NUTS2.close()

        #------------------------------------------------------------------------------
        # Timeseries for traffic

        if CTRL.ACTIVATE_TIMESERIES:
            
            if CTRL.NUTS2_ACTIVATED:
                text_NUTS2 = '_NUTS2_'
            else:
                text_NUTS2 = '_'
            
            result_energy_profiles = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "TRA" + FILE.FILENAME_OUTPUT_TIMESERIES), engine='xlsxwriter')
            result_pkm_tkm_profiles = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_TIMESERIES_TRA_PKM_TKM), engine='xlsxwriter')


            if CTRL.NUTS2_ACTIVATED:
                logger.info(" - Timeseries traffic: Nuts2")

                pt_pkm_total = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_pkm_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx'), sheet_name = ["pkm"])["pkm"]
                ft_tkm_total = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'TRA_tkm_NUTS2_'+str(CTRL.FORECAST_YEAR)+'.xlsx'), sheet_name = ["tkm"])["tkm"]
                
                consideredcountries = pt_pkm_total["NUTS2"]
                
                # energy demand timeseries
                energy_profiles_df = energy_profiles_calc(consideredcountries, CTRL, energy_demand_pt_elec_nuts2, 
                                                          energy_demand_pt_h2_nuts2, energy_demand_ft_elec_nuts2, 
                                                          energy_demand_ft_h2_nuts2, tra_data.timeseries_loading)
                # traffic kilometers timeseries
                pkm_tkm_profiles_df = km_profile_calc(consideredcountries, CTRL, pt_pkm_total, #self.tra_pt.energy_demand_pt_total
                                                             ft_tkm_total, tra_data.timeseries_mobility) #self.tra_ft.energy_demand_ft_total, tra_data.timeseries_mobility
            else:
                logger.info(" - Timeseries traffic: Country")
                
                # energy demand timeseries
                energy_profiles_df = energy_profiles_calc(CTRL.CONSIDERED_COUNTRIES, CTRL, self.tra_pt.energy_demand_pt_elec, 
                                                          self.tra_pt.energy_demand_pt_h2, self.tra_ft.energy_demand_ft_elec, 
                                                          self.tra_ft.energy_demand_ft_h2, tra_data.timeseries_loading)
                # traffic kilometers timeseries
                pkm_tkm_profiles_df = km_profile_calc(CTRL.CONSIDERED_COUNTRIES, CTRL, self.tra_pt.pt_Mrd_pkm, 
                                                             self.tra_ft.ft_Mil_tkm, tra_data.timeseries_mobility)
            
            energy_profiles_df.to_excel(result_energy_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
            result_energy_profiles.close()
            pkm_tkm_profiles_df.to_excel(result_pkm_tkm_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
            result_pkm_tkm_profiles.close()
        
        else:
            print("Calculation of load timeseries deactivated.")
            

def km_profile_calc(consideredcountries, CTRL, kilometers_df_pt, kilometers_df_ft, load_profile):

    traffic_sectors = ['pt_car [Mrd. pkm]', 'pt_bus [Mrd. pkm]', 'pt_rail [Mrd. pkm]', 'pt_flight [Mrd. pkm]','pt_ship [Mrd. pkm]','ft_road [Mil. tkm]','ft_rail [Mil. tkm]','ft_flight [Mil. tkm]','ft_ship [Mil. tkm]']

    # Define and calculate energy series
    km_timeseries_df = pd.DataFrame({"t":load_profile["t"]})
    print("Calculating km profiles.")
        
    for tra_type in traffic_sectors:
        if tra_type[0]=="p":
            kilometers_df = kilometers_df_pt
        else:
            kilometers_df = kilometers_df_ft
        
        for idx_country, country in enumerate(consideredcountries):
            # With assumption that kilometers_df_pt contains countries/NUTS2 regions in the same order as consideredcountries
            ## where [0:-11] removes " [Mrd. pkm]" or " [Mil. tkm]"
            country_timeseries = kilometers_df[tra_type][idx_country] * np.array(load_profile[tra_type[0:-11].replace("_", ".")]) 

            country_timeseries_df = pd.DataFrame({country+ "." + tra_type: country_timeseries})
            country_timeseries_df.index.name = "t"
            km_timeseries_df = km_timeseries_df.merge(country_timeseries_df, on = "t") 
    
    return km_timeseries_df


def energy_profiles_calc(consideredcountries, CTRL, energy_df_pt_elec, energy_df_pt_h2, energy_df_ft_elec, energy_df_ft_h2, load_profile):
    
    # Define names: due to operational time optimization - explicitely writing names
    energy_elec_name_1 = "pt_car_elec [TWh]"
    energy_elec_name_2 = "pt_rail_elec [TWh]"
    energy_elec_name_3 = "pt_bus_elec [TWh]"
    energy_elec_name_4 = "pt_flight_elec [TWh]"
    energy_elec_name_5 = "pt_ship_elec [TWh]"

    energy_elec_name_6 = "ft_rail_elec [TWh]"
    energy_elec_name_7 = "ft_road_elec [TWh]"
    energy_elec_name_8 = "ft_ship_elec [TWh]"
    energy_elec_name_9 = "ft_flight_elec [TWh]"
    
    energy_h2_name_1 = "pt_car_h2 [TWh]"
    energy_h2_name_2 = "pt_rail_h2 [TWh]"
    energy_h2_name_3 = "pt_bus_h2 [TWh]"
    energy_h2_name_4 = "pt_flight_h2 [TWh]"
    energy_h2_name_5 = "pt_ship_h2 [TWh]"

    energy_h2_name_6 = "ft_rail_h2 [TWh]"
    energy_h2_name_7 = "ft_road_h2 [TWh]"
    energy_h2_name_8 = "ft_ship_h2 [TWh]"
    energy_h2_name_9 = "ft_flight_h2 [TWh]"
    
    # Define and calculate energy series
    energy_timeseries_df = pd.DataFrame({"t":load_profile["t"]})
    print("Calculating energy profiles.")
    
    for idx_country, country in enumerate(consideredcountries):
        #energy_type = "elec"
        #pt_tra_types = ["car", "rail", "bus", "ship", "flight"]
        #fr_tra_types = ["road", "rail", "ship", "flight"]
        
        # Calculation for electricity
        country_timeseries_elec = list(
            + energy_df_pt_elec[energy_elec_name_1][idx_country] * np.array(load_profile["pt.road.elec"])
            + energy_df_pt_elec[energy_elec_name_2][idx_country] * np.array(load_profile["pt.rail.elec"])
            + energy_df_pt_elec[energy_elec_name_3][idx_country] * np.array(load_profile["pt.road.elec"])
            + energy_df_pt_elec[energy_elec_name_4][idx_country] * np.array(load_profile["flight.elec"])
            + energy_df_pt_elec[energy_elec_name_5][idx_country] * np.array(load_profile["ship.elec"])
            
            + energy_df_ft_elec[energy_elec_name_6][idx_country] * np.array(load_profile["ft.rail.elec"])
            + energy_df_ft_elec[energy_elec_name_7][idx_country] * np.array(load_profile["ft.road.elec"])
            + energy_df_ft_elec[energy_elec_name_8][idx_country] * np.array(load_profile["ship.elec"])
            + energy_df_ft_elec[energy_elec_name_9][idx_country] * np.array(load_profile["flight.elec"]))
        
        # Calculation for hydrogen    
        country_timeseries_h2 = list(
            + energy_df_pt_h2[energy_h2_name_1][idx_country] * np.array(load_profile["pt.road.hydrogen"])
            + energy_df_pt_h2[energy_h2_name_2][idx_country] * np.array(load_profile["pt.rail.hydrogen"])
            + energy_df_pt_h2[energy_h2_name_3][idx_country] * np.array(load_profile["pt.road.hydrogen"])
            + energy_df_pt_h2[energy_h2_name_4][idx_country] * np.array(load_profile["flight.hydrogen"])
            + energy_df_pt_h2[energy_h2_name_5][idx_country] * np.array(load_profile["ship.hydrogen"])
            
            + energy_df_ft_h2[energy_h2_name_6][idx_country] * np.array(load_profile["ft.rail.hydrogen"])
            + energy_df_ft_h2[energy_h2_name_7][idx_country] * np.array(load_profile["ft.road.hydrogen"])
            + energy_df_ft_h2[energy_h2_name_8][idx_country] * np.array(load_profile["ship.hydrogen"])
            + energy_df_ft_h2[energy_h2_name_9][idx_country] * np.array(load_profile["flight.hydrogen"]))
        
        country_timeseries_df = pd.DataFrame({country+ "." + CTRL.ENERGYCARRIER_PROFILE[0]: country_timeseries_elec,
                                              country+ "." + CTRL.ENERGYCARRIER_PROFILE[2]: country_timeseries_h2})
        country_timeseries_df.index.name = "t"
        energy_timeseries_df = energy_timeseries_df.merge(country_timeseries_df, on = "t")      
    
    return energy_timeseries_df
