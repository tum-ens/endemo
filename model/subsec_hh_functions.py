###############################################################################                                                                                   
# Chair:            Chair of Renewable and Sustainable Energy Systems (ENS)
# Assistant(s):     Andjelka Kerekes (andelka.bujandric@tum.de)
#                   Larissa Breuning (larissa.breuning@tum.de)

# Date:             
# Version:          v3.0
# Status:           in progress
# Python-Version:   3.7.3 (64-bit)
###############################################################################
"""This module defines functions for the household sector
"""
###############################################################################
from libraries import *
from op_methods import lin_regression_time

###############################################################################
# Additional functions
###############################################################################
def add_consum_per_source(sources_consum_country, efficiency_table):
    
    source_type = ["electricity", "derived heat", "gas", "solid fossil fuels","total oil & petroleum products", "total renew. & wastes"]
    source_type = [source.upper() for source in source_type]
   
    # Different countries have different data availability
    start_year = 2010
    stop_year = 2018
    while np.isnan(sources_consum_country[start_year]).all() and start_year<stop_year:
        start_year +=1  
    
    years = range(start_year, stop_year+1)
    sum_energies = []
    for year in years:
        sum_energy = 0
    
        for source in source_type:
            
            idx_source = list(sources_consum_country["Product"]).index(source)
            #  Source consumption in same units
            if sources_consum_country["Unit"][idx_source] == 'GWh':
                fact = 1/1000 # GWh -> TWh
            elif (sources_consum_country["Unit"][idx_source]).startswith("TJ"):
                fact = 1/3600 # TJ -> TWh
            elif sources_consum_country["Unit"][idx_source] == 'kt':
                if sources_consum_country["Product"][idx_source] == 'SOLID FOSSIL FUELS':
                    fact =  28157.5373355095 /1000/3600   # kt -> TWh: considering MJ/t = GJ/kt
                if sources_consum_country["Product"][idx_source] == 'TOTAL OIL & PETROLEUM PRODUCTS':
                    fact =  43208.3523702321 /1000/3600   # kt -> TWh: considering MJ/t = GJ/kt 
    
            # Convert nan value to zero
            if math.isnan(sources_consum_country[year][idx_source]):
                source_consum = 0
            else: 
                source_consum = sources_consum_country[year][idx_source] 
            
            idx_eff = list(efficiency_table["Energy carrier HH"]).index(source.lower())
            # Since energy is sumarized regardless of its type (heat or electricity demand)
            efficiency = efficiency_table["Heat production [-]"][idx_eff] + efficiency_table["Electricity production [-]"][idx_eff]
    
            # Calculate sum of the historical energy consumption
            sum_energy += source_consum * fact * efficiency # unit TWh
            
            # Excel sheet 1e_LightingAndAppliances has only electricity     
            if len(sources_consum_country) == 1:
                break
        
        sum_energies.append(sum_energy)

    return years, sum_energies, sum_energy # sum_energy = last historical energy value

#------------------------------------------------------------------------------   
def consum_per_parameter(years, sum_energies, parameters_table, country):
    
    try:
        idx_param_his = list(parameters_table["Country"]).index(country)
    except:
        idx_param_his = -1
    # Calculate historical energy consumption per capita or per m2
        ## if country has information for the given parameter
    if idx_param_his != -1:
        sum_energy_per_param = []
        for idx, year in enumerate(years):
            try:
                sum_energy_per_param.append(sum_energies[idx]/parameters_table[str(year)][idx_param_his])
            except:
                sum_energy_per_param.append(sum_energies[idx]/parameters_table[year][idx_param_his])
        sum_energy_per_param_df = pd.DataFrame(columns = ["Country"]+[year for year in years])
        sum_energy_per_param_df.loc[0] = [country]+sum_energy_per_param
        constant = False
    else:
        ## if country doesn't have information for the given parameter, signalaze that a default constant should be taken
        sum_energy_per_param_df = 0
        constant = True
    return sum_energy_per_param_df, constant

#------------------------------------------------------------------------------    
def lin_spec_consum_forecast(years, consum_per_parameter, param_forecast, FORECAST_YEAR, country):
        
    if len(years)>=5: 
        # Calculate parameters
        slope, intercept = lin_regression_time(consum_per_parameter, country, [])
        
        # Calculate forecasted energy consumption
        energy_forecast_per_param = (slope*FORECAST_YEAR+intercept)
    else:
        # read last historical value per parameter
        energy_forecast_per_param = consum_per_parameter[years[-1]][list(consum_per_parameter["Country"]).index(country)] 
    
    idx_param_forecast = list(param_forecast["Country"]).index(country)
    energy_forecast = energy_forecast_per_param * param_forecast[str(FORECAST_YEAR)][idx_param_forecast]
    
    # limiting energy demand to be non-negative
    energy_forecast = max(0,energy_forecast)

    return energy_forecast, energy_forecast_per_param

#------------------------------------------------------------------------------
def const_spec_consum_forecast(FORECAST_YEAR, REF_YEAR, energy_his, area_total_forecast, area_total_hist, country):
    
    idx_forecast = list(area_total_forecast["Country"]).index(country)
    idx_hist = list(area_total_hist["Country"]).index(country)
    area_total_forecast_c = area_total_forecast[str(FORECAST_YEAR)][idx_forecast]
    area_total_hist_c = area_total_hist[str(REF_YEAR)][idx_hist]
    
    energy_forecast = energy_his * area_total_forecast_c/area_total_hist_c
    energy_forecast_per_param = energy_his/area_total_hist_c

    return energy_forecast, energy_forecast_per_param
