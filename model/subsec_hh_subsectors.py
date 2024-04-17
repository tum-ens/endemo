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
from op_methods import foothold_lin_forecast
from op_methods import foothold_exp_forecast
import subsec_hh_functions

###############################################################################
# Data preprocessing
###############################################################################          
def datapreproces(CTRL, FILE, hh_data, gen_data):

    #Space heating: m^2/household / Pers/household  * Population * kWh/m^2 * %sources
    area_per_hh_forecast = []
    area_per_hh_hist = []
    person_per_hh_forecast = []
    area_total_forecast = []
    area_total_hist = []

    for country in CTRL.CONSIDERED_COUNTRIES:

        idx_area = list(hh_data.area_per_hh["Country"]).index(country)
        idx_person_per_hh = list(hh_data.person_per_hh["Country"]).index(country)
        idx_pop_forecast = list(gen_data.pop_forecast_country["Country"]).index(country)
        idx_pop_hist = list(gen_data.pop_table["Country"]).index(country)
                
        if CTRL.HH_CALC_METHOD_HH_AREA == "exp":
            area_per_hh_forecast_c = (hh_data.area_per_hh["Area per household [m2/HH] (2012)"][idx_area]
                                 * (1 + hh_data.area_per_hh["Trend Rate exp [%/a]"][idx_area]/100)**(CTRL.FORECAST_YEAR - 2012))
            area_per_hh_hist_c = (hh_data.area_per_hh["Area per household [m2/HH] (2012)"][idx_area]
                                 * (1 + hh_data.area_per_hh["Trend Rate exp [%/a]"][idx_area]/100)**(CTRL.REF_YEAR - 2012))
        elif CTRL.HH_CALC_METHOD_HH_AREA == "lin":
            area_per_hh_forecast_c = (hh_data.area_per_hh["Area per household [m2/HH] (2012)"][idx_area]
                                 * (1 + hh_data.area_per_hh["Trend Rate lin [%/a]"][idx_area]/100*(CTRL.FORECAST_YEAR - 2012)))
            area_per_hh_hist_c = (hh_data.area_per_hh["Area per household [m2/HH] (2012)"][idx_area]
                                 * (1 + hh_data.area_per_hh["Trend Rate lin [%/a]"][idx_area]/100*(CTRL.REF_YEAR - 2012)))
        area_per_hh_forecast.append([country, area_per_hh_forecast_c])
        area_per_hh_hist.append([country, area_per_hh_hist_c])
            
        if CTRL.HH_CALC_METHOD_PER_HH == "exp":
            person_per_hh_forecast_c = foothold_exp_forecast(CTRL.FORECAST_YEAR, CTRL.REF_YEAR, country, hh_data.person_per_hh, [2020, 2030, 2040, 2050])
        elif CTRL.HH_CALC_METHOD_PER_HH == "lin":
            person_per_hh_forecast_c = foothold_lin_forecast(CTRL.FORECAST_YEAR, CTRL.REF_YEAR, country, hh_data.person_per_hh, [2020, 2030, 2040, 2050])
        person_per_hh_forecast.append([country, person_per_hh_forecast_c])
            
        area_total_forecast_c = (area_per_hh_forecast_c/person_per_hh_forecast_c
                                 *gen_data.pop_forecast_country[str(CTRL.FORECAST_YEAR)][idx_pop_forecast]/10**6) # unit: m2 -> Mil. m2
        area_total_hist_c = (area_per_hh_hist_c/hh_data.person_per_hh[CTRL.REF_YEAR][idx_person_per_hh]
                             *gen_data.pop_table[str(CTRL.REF_YEAR)][idx_pop_hist]/10**6) # unit: m2 -> Mil. m2
        area_total_forecast.append([country, area_total_forecast_c])
        area_total_hist.append([country, area_total_hist_c])
        
    area_per_hh_forecast = pd.DataFrame(area_per_hh_forecast, columns = ["Country", CTRL.FORECAST_YEAR]) #"Area per Household [m2/HH]"
    area_per_hh_hist = pd.DataFrame(area_per_hh_hist, columns = ["Country", CTRL.REF_YEAR]) 
    person_per_hh_forecast = pd.DataFrame(person_per_hh_forecast, columns = ["Country", CTRL.FORECAST_YEAR]) #"Person per Household [Per./HH]"
    area_total_forecast = pd.DataFrame(area_total_forecast, columns = ["Country", str(CTRL.FORECAST_YEAR)]) #"Living area total [Mil. m2]"
    area_total_hist = pd.DataFrame(area_total_hist, columns = ["Country", str(CTRL.REF_YEAR)])
    
    hh_data_forecast = HH_DATA_FORECAST(area_per_hh_forecast,area_per_hh_hist, person_per_hh_forecast, area_total_forecast,area_total_hist)

    return hh_data_forecast

class HH_DATA_FORECAST():

    def __init__(self, area_per_hh_forecast,area_per_hh_hist, person_per_hh_forecast, area_total_forecast,area_total_hist):

        self.area_per_hh_forecast = area_per_hh_forecast
        self.area_per_hh_hist = area_per_hh_hist
        self.person_per_hh_forecast = person_per_hh_forecast
        self.area_total_forecast = area_total_forecast
        self.area_total_hist = area_total_hist


###############################################################################
# Subsector: Space heating
###############################################################################          
def spaceheating(CTRL, FILE, hh_data, gen_data, hh_data_forecast):

    spec_energy_spheat_forecast = []
    energy_demand_his = []

    # general without source sectors
    energy_space_heating = []
    forecast_year = CTRL.FORECAST_YEAR
    for country in CTRL.CONSIDERED_COUNTRIES:

        filename_sources = country + "_2018.xlsm"
        sources_per_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                            sheet_name=["1a_SpaceHeating"],skiprows=4)["1a_SpaceHeating"]

        years, sum_energies, energy_his = subsec_hh_functions.add_consum_per_source(sources_per_country, gen_data.efficiency_table)
        # temp, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)
        energy_demand_his.append([country, energy_his])

        idx_area = list(hh_data_forecast.area_per_hh_forecast["Country"]).index(country)
        idx_person_per_hh = list(hh_data_forecast.person_per_hh_forecast["Country"]).index(country)
        idx_spec_energy = list(hh_data.spec_energy_spheat["Country"]).index(country)
        idx_pop_forecast = list(gen_data.pop_forecast_country["Country"]).index(country)
        idx_calibration = list(hh_data.calibration_spheat["Country"]).index(country)
        
        area_per_hh_forecast_c = hh_data_forecast.area_per_hh_forecast[forecast_year][idx_area]
        person_per_hh_forecast_c = hh_data_forecast.person_per_hh_forecast[forecast_year][idx_person_per_hh]
        
        if CTRL.HH_CALC_METHOD_SP_HEAT == "exp":
            spec_energy_spheat_forecast_c = (hh_data.spec_energy_spheat[2019][idx_spec_energy]*
                                                ((1+(hh_data.spec_energy_spheat["Trend Rate exp [%/a]"][idx_spec_energy]/100))**(forecast_year-2019))) #unit kWh/m²
        elif CTRL.HH_CALC_METHOD_SP_HEAT == "lin":
            spec_energy_spheat_forecast_c = (hh_data.spec_energy_spheat[2019][idx_spec_energy]*
                                                (1+ hh_data.spec_energy_spheat["Trend Rate lin [%/a]"][idx_spec_energy]/100*(forecast_year-2019))) #unit kWh/m²
            
        spec_energy_spheat_forecast_c = max(spec_energy_spheat_forecast_c, 5) # kWh/m2
            
        spec_energy_spheat_forecast.append([country, spec_energy_spheat_forecast_c]) 

        energy_space_heating_country = (area_per_hh_forecast_c
                                        * gen_data.pop_forecast_country[str(forecast_year)][idx_pop_forecast]
                                        / person_per_hh_forecast_c
                                        * spec_energy_spheat_forecast_c
                                        * hh_data.calibration_spheat["Calibration parameter [-]"][idx_calibration]) #unit kWh/m²
               
        energy_space_heating.append([country, (energy_space_heating_country/10**9)]) #unit: TWh (kWh -> TWh)


    energy_space_heating = pd.DataFrame(energy_space_heating, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption "+str(CTRL.REF_YEAR)+" [TWh]"])
    spec_energy_spheat_forecast = pd.DataFrame(spec_energy_spheat_forecast, columns = ["Country", forecast_year]) #"Specific energy consumption [kWh/m2]"
    
    hh_sh = SPACE_HEATING(energy_demand_his, spec_energy_spheat_forecast, energy_space_heating)

    return hh_sh

class SPACE_HEATING():

    def __init__(self, energy_demand_his, spec_energy_spheat_forecast, energy_space_heating):

        self.energy_space_heating = energy_space_heating
        self.energy_demand_his = energy_demand_his
        self.spec_energy_spheat_forecast = spec_energy_spheat_forecast

        
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

        years, sum_energies, energy_his = subsec_hh_functions.add_consum_per_source(sources_per_country, gen_data.efficiency_table)
        # temp, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)

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
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption "+str(CTRL.REF_YEAR)+" [TWh]"])
    
    hh_hw = HOT_WATER(energy_hot_water, energy_demand_his)

    return hh_hw

class HOT_WATER():

    def __init__(self, energy_hot_water, energy_demand_his):

        self.energy_hot_water = energy_hot_water
        self.energy_demand_his = energy_demand_his
   
     
###############################################################################
# Subsector: Spacecooling
###############################################################################     
def spacecooling(CTRL, FILE, hh_data, gen_data, hh_data_forecast):

    energy_demand_his = []
    energy_cooling = []
    spec_energy_forecast = []
    for country in CTRL.CONSIDERED_COUNTRIES:

        filename_sources = country + "_2018.xlsm"
        sources_per_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                            sheet_name=["1b_SpaceCooling"],skiprows=4)["1b_SpaceCooling"]

        #get the consumption per main sector for private households
        years, sum_energies, energy_his = subsec_hh_functions.add_consum_per_source(sources_per_country, gen_data.efficiency_table)
        consum_per_m2_c, constant = subsec_hh_functions.consum_per_parameter(years, sum_energies, hh_data.floor_area, country) # unit: TWh/Mil. m2 = MWh/m2
        if constant == False:
            energy_forecast, energy_forecast_per_param = subsec_hh_functions.lin_spec_consum_forecast(years, consum_per_m2_c, hh_data_forecast.area_total_forecast, CTRL.FORECAST_YEAR, country)
        else:
            energy_forecast, energy_forecast_per_param = subsec_hh_functions.const_spec_consum_forecast(CTRL.FORECAST_YEAR, CTRL.REF_YEAR, energy_his, 
                                                                                                        hh_data_forecast.area_total_forecast, hh_data_forecast.area_total_hist, country)
        # energy_forecast, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)
        
        #unit TJ
        energy_cooling.append([country, energy_forecast])  
        energy_demand_his.append([country, energy_his])
        spec_energy_forecast.append([country, energy_forecast_per_param*10**3]) # MWh/m2 -> kWh/m2

    energy_cooling = pd.DataFrame(energy_cooling, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption "+str(CTRL.REF_YEAR)+" [TWh]"])
    spec_energy_forecast = pd.DataFrame(spec_energy_forecast, columns = ["Country", CTRL.FORECAST_YEAR])
        
    hh_sc = SPACE_COOLING(energy_cooling, energy_demand_his, spec_energy_forecast)

    return hh_sc

class SPACE_COOLING():

    def __init__(self, energy_cooling, energy_demand_his, spec_energy_forecast):

        self.energy_cooling = energy_cooling
        self.energy_demand_his = energy_demand_his
        self.spec_energy_forecast = spec_energy_forecast

       
###############################################################################
# Subsector: Lighting and electrical appliances
## Additional consideration of the rest (non-specified application) sector
###############################################################################
def lighting(CTRL, FILE, hh_data, gen_data):     #eletrical demand (e.g. light, appliances)

    energy_demand_his = []
    energy_electricity = []
    spec_energy_forecast = []
    spec_energy_hist = []
    for country in CTRL.CONSIDERED_COUNTRIES:

        filename_sources = country + "_2018.xlsm"
        sources_per_country_file = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                                    sheet_name=["1e_LightingAndAppliances", "1f_OtherEndUses"],skiprows=4)
        sources_per_country = sources_per_country_file["1e_LightingAndAppliances"]
        sources_per_country_rest = sources_per_country_file["1f_OtherEndUses"]
        
        #get the consumption per main sector for private households
        ## electrical appliances and lightening
        years, sum_energies, energy_his = subsec_hh_functions.add_consum_per_source(sources_per_country, gen_data.efficiency_table)
        consum_per_capita_c, constant = subsec_hh_functions.consum_per_parameter(years, sum_energies, gen_data.pop_table, country)
        energy_forecast, energy_forecast_per_param = subsec_hh_functions.lin_spec_consum_forecast(years, consum_per_capita_c, gen_data.pop_forecast_country, CTRL.FORECAST_YEAR, country)
       
        ## other electricity applications
        years, sum_energies, energy_his_rest = subsec_hh_functions.add_consum_per_source(sources_per_country_rest, gen_data.efficiency_table)
        consum_per_capita_rest_c, constant = subsec_hh_functions.consum_per_parameter(years, sum_energies, gen_data.pop_table, country)
        energy_forecast_rest, energy_forecast_per_param_rest = subsec_hh_functions.lin_spec_consum_forecast(years, consum_per_capita_rest_c, gen_data.pop_forecast_country, CTRL.FORECAST_YEAR, country)

        
        energy_electricity.append([country, energy_forecast+energy_forecast_rest]) 
        energy_demand_his.append([country, (energy_his+energy_his_rest)])
        spec_energy_forecast.append([country, (energy_forecast_per_param+energy_forecast_per_param_rest)*10**9]) # TWh/per -> kWh/per
        spec_energy_hist.append([country, (consum_per_capita_c[CTRL.REF_YEAR][0]+consum_per_capita_rest_c[CTRL.REF_YEAR][0])*10**9]) # TWh/per -> kWh/per

    energy_electricity = pd.DataFrame(energy_electricity, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption "+str(CTRL.REF_YEAR)+" [TWh]"])
    spec_energy_forecast = pd.DataFrame(spec_energy_forecast, columns = ["Country", CTRL.FORECAST_YEAR])
    spec_energy_hist = pd.DataFrame(spec_energy_hist, columns = ["Country", CTRL.REF_YEAR])
    
    hh_liandap = LIGHTING(energy_electricity, energy_demand_his, spec_energy_forecast, spec_energy_hist)

    return hh_liandap

class LIGHTING():

    def __init__(self, energy_electricity, energy_demand_his, spec_energy_forecast, spec_energy_hist):

        self.energy_electricity = energy_electricity
        self.energy_demand_his = energy_demand_his
        self.spec_energy_forecast = spec_energy_forecast
        self.spec_energy_hist = spec_energy_hist


###############################################################################
# Subsector: Cooking
###############################################################################
def cooking(CTRL, FILE, hh_data, gen_data):

    energy_demand_his = []
    energy_cooking = []
    spec_energy_forecast = []
    spec_energy_hist = []
    for country in CTRL.CONSIDERED_COUNTRIES:
        
        filename_sources = country + "_2018.xlsm"
        sources_per_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS_SOURCES, filename_sources),
                                            sheet_name=["1d_Cooking"],skiprows=4)["1d_Cooking"]

        #get the consumption per main sector for private households
        years, sum_energies, energy_his = subsec_hh_functions.add_consum_per_source(sources_per_country, gen_data.efficiency_table)
        consum_per_capita_c, constant = subsec_hh_functions.consum_per_parameter(years, sum_energies, gen_data.pop_table, country)
        energy_forecast, energy_forecast_per_param = subsec_hh_functions.lin_spec_consum_forecast(years, consum_per_capita_c, gen_data.pop_forecast_country, CTRL.FORECAST_YEAR, country)
        #energy_forecast, energy_his = subsec_hh_functions.add_consum_per_source(CTRL, gen_data.pop_table, gen_data.pop_forecast_country, gen_data.abbreviations, country, CTRL.FORECAST_YEAR, sources_per_country, gen_data.efficiency_table)
  
        #unit TJ
        energy_cooking.append([country, (energy_forecast)]) 
        energy_demand_his.append([country, energy_his])
        spec_energy_forecast.append([country, energy_forecast_per_param*10**9]) # TWh/per -> kWh/per
        spec_energy_hist.append([country, consum_per_capita_c[CTRL.REF_YEAR][0]*10**9]) # TWh/per -> kWh/per

    energy_cooking = pd.DataFrame(energy_cooking, columns = ["Country", "Consumption Prog [TWh]"])
    energy_demand_his = pd.DataFrame(energy_demand_his, columns = ["Country", "Consumption "+str(CTRL.REF_YEAR)+" [TWh]"])
    spec_energy_forecast = pd.DataFrame(spec_energy_forecast, columns = ["Country", CTRL.FORECAST_YEAR])
    spec_energy_hist = pd.DataFrame(spec_energy_hist, columns = ["Country", CTRL.REF_YEAR])
        
    hh_co = COOKING(energy_cooking, energy_demand_his, spec_energy_forecast, spec_energy_hist)

    return hh_co

class COOKING():

    def __init__(self, energy_cooking, energy_demand_his, spec_energy_forecast, spec_energy_hist):

        self.energy_cooking = energy_cooking
        self.energy_demand_his = energy_demand_his
        self.spec_energy_forecast = spec_energy_forecast
        self.spec_energy_hist = spec_energy_hist
        