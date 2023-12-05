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

###############################################################################
# Additional functions
###############################################################################
def add_consum_per_source(CTRL, pop_table, pop_forecast, abb_table, country, PROGNOS_YEAR, sources_consum_country, efficiency_table):
    
    source_type = ["electricity", "derived heat", "gas", "solid fossil fuels","total oil & petroleum products", "total renew. & wastes"]
    source_type = [source.upper() for source in source_type]
   
    # Different countries have different data availability
    start_year = 2010
    stop_year = 2018
    while np.isnan(sources_consum_country[start_year]).all() and start_year<stop_year:
        start_year +=1  
    
    idx_pop_his = list(pop_table["Country"]).index(country)
    idx_pop_prog = list(pop_forecast["Country"]).index(country)
    
    sum_start_year = 0
    sum_stop_year = 0
    
    # sources_start_body = []
    # sources_stop_body = []
    
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
        if math.isnan(sources_consum_country[start_year][idx_source]):
            source_consum_start = 0
        else: 
            source_consum_start = sources_consum_country[start_year][idx_source] 
        if math.isnan(sources_consum_country[stop_year][idx_source]):
            source_consum_stop = 0
        else: 
            source_consum_stop = sources_consum_country[stop_year][idx_source]
        
        idx_eff = list(efficiency_table["Energy carrier HH"]).index(source.lower())
        # Since energy is sumarized regardless of its type (heat or electricity demand)
        efficiency = efficiency_table["Heat production [-]"][idx_eff] + efficiency_table["Electricity production [-]"][idx_eff]
        # sources_start_body.append([country, source_consum_start * fact * efficiency]) # unit TWh
        # sources_stop_body.append([country, source_consum_stop * fact * efficiency]) # unit TWh

        # Calculate sum of the historical energy consumption
        sum_start_year += source_consum_start * fact * efficiency
        sum_stop_year += source_consum_stop * fact * efficiency
        
        # Excel sheet 1e_LightingAndAppliances has only electricity     
        if len(sources_consum_country) == 1:
            break
        
    # Calculate sum of the historical energy consumption per capita
    sum_start_year_per_cap = sum_start_year/pop_table[str(start_year)][idx_pop_his]
    sum_stop_year_per_cap = sum_stop_year/pop_table[str(stop_year)][idx_pop_his]

    # Calculate change rate
    if start_year == 2010 and sum_start_year > 0:
        prog_rate_temp = ((sum_stop_year_per_cap/sum_start_year_per_cap)**(1/(stop_year-start_year))-1)*100 # unit %/a
        # better methodology needed!!!
        # limitation of the yearly change to 5%
        prog_rate_temp = min(prog_rate_temp, 5)
    else: 
        prog_rate_temp = 0
    # Calculate forecasted energy consumption
    energy_forecast = (sum_stop_year_per_cap * pop_forecast[str(PROGNOS_YEAR)][idx_pop_prog] 
                       * ((1+(prog_rate_temp/100))**(PROGNOS_YEAR-stop_year)))  #unit TWh

    return energy_forecast, sum_stop_year