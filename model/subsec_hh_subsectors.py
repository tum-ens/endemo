###############################################################################                                                                                   
# Forecast of the subsector lighting and electrical appliances for households
###############################################################################
"""The module calculates the energy demand of the subsector lighting and 
electrical appliances for households.
"""
###############################################################################
# Imports
###############################################################################
from libraries import *
from op_methods import foothold_year_forecast
import subsec_hh_functions

###############################################################################
# Subsector: Lighting and electrical appliances
## Additional consideration of the rest (non-specified application) sector
###############################################################################
def lighting(CTRL, FILE, hh_data, gen_data):     #eletrical demand (e.g. light, appliances)

    energy_demand_his = []
    energy_electricity = []
    for country in CTRL.CONSIDERED_COUNTRIES:

        filename_sources = country + "_2018.xlsm"
        sources_per_country_file = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                                    sheet_name=["1e_LightingAndAppliances", "1f_OtherEndUses"],skiprows=4)
        sources_per_country = sources_per_country_file["1e_LightingAndAppliances"]
        sources_per_country_rest = sources_per_country_file["1f_OtherEndUses"]
        
        #get the consumption per main sector for private households
        energy_forecast, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)
        energy_forecast_rest, energy_his_rest = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country_rest, gen_data.efficiency_table)

        
        energy_electricity.append([country, energy_forecast+energy_forecast_rest]) 
        energy_demand_his.append([country, (energy_his+energy_his_rest)]) 

    energy_electricity = pd.DataFrame(energy_electricity, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption 2018 [TWh]"])
    
    hh_liandap = LIGHTING(energy_electricity, energy_demand_his)

    return hh_liandap

class LIGHTING():

    def __init__(self, energy_electricity, energy_demand_his):

        self.energy_electricity = energy_electricity
        self.energy_demand_his = energy_demand_his

        
###############################################################################
# Subsector: Spacecooling
###############################################################################     
def spacecooling(CTRL, FILE, hh_data, gen_data):

    energy_demand_his = []
    energy_cooling = []
    for country in CTRL.CONSIDERED_COUNTRIES:

        filename_sources = country + "_2018.xlsm"
        sources_per_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                            sheet_name=["1b_SpaceCooling"],skiprows=4)["1b_SpaceCooling"]

        #get the consumption per main sector for private households
        energy_forecast, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)
        
        #unit TJ
        energy_cooling.append([country, energy_forecast])
        
        energy_demand_his.append([country, energy_his])

    energy_cooling = pd.DataFrame(energy_cooling, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption 2018 [TWh]"])
        
    hh_sc = SPACE_COOLING(energy_cooling, energy_demand_his)

    return hh_sc

class SPACE_COOLING():

    def __init__(self, energy_cooling, energy_demand_his):

        self.energy_cooling = energy_cooling
        self.energy_demand_his = energy_demand_his
        

###############################################################################
# Subsector: Spacecooling
###############################################################################
def cooking(CTRL, FILE, hh_data, gen_data):

    energy_demand_his = []
    energy_cooking = []
    for country in CTRL.CONSIDERED_COUNTRIES:
        
        filename_sources = country + "_2018.xlsm"
        sources_per_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                            sheet_name=["1d_Cooking"],skiprows=4)["1d_Cooking"]

        #get the consumption per main sector for private households
        energy_forecast, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)
  
        #unit TJ
        energy_cooking.append([country, (energy_forecast)]) 

        energy_demand_his.append([country, energy_his])

    energy_cooking = pd.DataFrame(energy_cooking, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption 2018 [TWh]"])
    
    hh_co = COOKING(energy_cooking, energy_demand_his)

    return hh_co

class COOKING():

    def __init__(self, energy_cooking, energy_demand_his):

        self.energy_cooking = energy_cooking
        self.energy_demand_his = energy_demand_his
        

###############################################################################
# Subsector: Hotwater
###############################################################################        
def hotwater(CTRL, FILE, hh_data, gen_data):

    energy_demand_his = []
    energy_hot_water = []
    
    for country in CTRL.CONSIDERED_COUNTRIES:

        filename_sources = country + "_2018.xlsm"
        sources_per_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                            sheet_name=["1c_WaterHeating"],skiprows=4)["1c_WaterHeating"]

        temp, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)

        idx_demand = list(hh_data.demand_per_person["Country"]).index(country)
        idx_abb = list(gen_data.abbreviations["Country"]).index(country)
        idx_pop_forecast = list(gen_data.pop_forecast_country["Country"]).index(country)
        idx_spec_capa = list(hh_data.techn_data["Parameter"]).index("Specific capacity")
        idx_calibration = list(hh_data.calibration_hw["Country"]).index(country)
        try:
            idx_return_temp = list(hh_data.techn_data["Parameter"]).index("Inlet temperature "+country)
        except:
            idx_return_temp = list(hh_data.techn_data["Parameter"]).index("Inlet temperature all")
        idx_flow_temp = list(hh_data.techn_data["Parameter"]).index("Outlet temperature")
        
        if type(hh_data.demand_per_person["Hot water in total water [%]"][idx_demand]) in [float, int]:
            hot_water = (hh_data.demand_per_person["Total water [liter/d/per]"][idx_demand]*(10**-3)*365 # m³/a/per
                          * hh_data.demand_per_person["Hot water in total water [%]"][idx_demand]/100)
        else:
            hot_water = hh_data.demand_per_person["Hot water [liter/d/per]"][idx_demand]*(10**-3)*365 # m³/a/per

        energy_hot_water_country = (hot_water # m³/a/per
                                     * gen_data.pop_forecast_country[str(CTRL.FORECAST_YEAR)][idx_pop_forecast]
                                     * hh_data.techn_data["Value"][idx_spec_capa]
                                     * (hh_data.techn_data["Value"][idx_flow_temp] - hh_data.techn_data["Value"][idx_return_temp]) # unit: kWh
                                     * hh_data.calibration_hw["Calibration parameter [-]"][idx_calibration])
                        
        energy_hot_water.append([country, energy_hot_water_country/10**9])    #unit TWh
                                
        energy_demand_his.append([country, energy_his])

    energy_hot_water = pd.DataFrame(energy_hot_water, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption 2018 [TWh]"])
    
    hh_hw = HOT_WATER(energy_hot_water, energy_demand_his)

    return hh_hw

class HOT_WATER():

    def __init__(self, energy_hot_water, energy_demand_his):

        self.energy_hot_water = energy_hot_water
        self.energy_demand_his = energy_demand_his
        

###############################################################################
# Subsector: Space heating
###############################################################################          
def spaceheating(CTRL, FILE, hh_data, gen_data):

    #Space heating: m^2/household / Pers/household  * Population * kWh/m^2 * %sources
    table_area_prog_country = []
    table_spec_energy_use_prog = []
    person_per_HH_prog = []
    table_total_area_country = []
    energy_demand_his = []

    # general without source sectors
    energy_space_heating = []
    for country in CTRL.CONSIDERED_COUNTRIES:

        filename_sources = country + "_2018.xlsm"
        sources_per_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                            sheet_name=["1a_SpaceHeating"],skiprows=4)["1a_SpaceHeating"]

        temp, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)

        idx_area = list(hh_data.area_per_household["Country"]).index(country)
        idx_person_per_hh = list(hh_data.person_per_household["Country"]).index(country)
        idx_spec_energy = list(hh_data.specific_energy_use["Country"]).index(country)
        idx_pop_forecast = list(gen_data.pop_forecast_country["Country"]).index(country)
        idx_calibration = list(hh_data.calibration_spheat["Country"]).index(country)
        
        area_prog_country = (hh_data.area_per_household["Area per household [m2/HH] (2012)"][idx_area]
                             * (1 + hh_data.area_per_household["Trend Rate [%]"][idx_area]/100)**(CTRL.FORECAST_YEAR - 2012))
        table_area_prog_country.append([country, area_prog_country]) 
            
        person_per_HH_prog_country = foothold_year_forecast(CTRL.FORECAST_YEAR, country, hh_data.person_per_household, [2020, 2030, 2040, 2050])
        person_per_HH_prog.append([country, person_per_HH_prog_country])
        
        specific_energy_use_prog_country = (hh_data.specific_energy_use[2019][idx_spec_energy]*
                                            ((1+(hh_data.specific_energy_use["Trend Rate [%] calc"][idx_spec_energy]/100))**(CTRL.FORECAST_YEAR-2019))) #unit kWh/m²
        table_spec_energy_use_prog.append([country, specific_energy_use_prog_country]) 

        energy_space_heating_country = (area_prog_country
                                        * gen_data.pop_forecast_country[str(CTRL.FORECAST_YEAR)][idx_pop_forecast]
                                        / person_per_HH_prog_country
                                        * specific_energy_use_prog_country
                                        * hh_data.calibration_spheat["Calibration parameter [-]"][idx_calibration]) #unit kWh/m²
        table_total_area_country.append([country, (area_prog_country/person_per_HH_prog_country)*gen_data.pop_forecast_country[str(CTRL.FORECAST_YEAR)][idx_pop_forecast]])
        
        #unit TJ 
        energy_space_heating.append([country, (energy_space_heating_country/10**9)]) #unit TWh

        energy_demand_his.append([country, energy_his])

    energy_space_heating = pd.DataFrame(energy_space_heating, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption 2018 [TWh]"])
    table_area_prog_country = pd.DataFrame(table_area_prog_country, columns = ["Country", "Area per Household [m^2/Household]"])
    person_per_HH_prog = pd.DataFrame(person_per_HH_prog, columns = ["Country", "Person per Household [Pers./Household]"])
    table_spec_energy_use_prog = pd.DataFrame(table_spec_energy_use_prog, columns = ["Country", "Specific energy consumption [kWh/m^2]"])
    table_total_area_country = pd.DataFrame(table_total_area_country, columns = ["Country", "Living area total [m^2]"])
    
    hh_sh = SPACE_HEATING(energy_space_heating, table_area_prog_country, 
                          table_spec_energy_use_prog, person_per_HH_prog, table_total_area_country, energy_demand_his)

    return hh_sh

class SPACE_HEATING():

    def __init__(self, energy_space_heating, table_area_prog_country, table_spec_energy_use_prog, person_per_HH_prog,
        table_total_area_country, energy_demand_his):

        self.energy_space_heating = energy_space_heating
        self.energy_demand_his = energy_demand_his
        self.table_area_prog_country = table_area_prog_country
        self.person_per_HH_prog = person_per_HH_prog
        self.table_spec_energy_use_prog = table_spec_energy_use_prog
        self.table_total_area_country = table_total_area_country