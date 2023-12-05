
import load_excel
import logging
import pandas as pd
import math

def load_sources_values_private_household(EU_COUNTRIES, country, PROGNOS_YEAR, sources_percent_per_country):

    sources_space_heating_temp = ['x', 'x', 'x', 'x','renewable & wastes', 'x', 'x', 'x','oil/petroleum products','solid fossil fuels', 'gas','derived heat', 'electricity']
    sources_space_heating = ['electricity', 'derived heat', 'gas', 'solid fossil fuels', 'oil/petroleum products', 'renewable & wastes']

    for sourc in range(4,17):

        # calculated source relstion in percent
        if sources_percent_per_country['Unnamed: 2'][sourc] == 'GWh':
            calculation_factor = 3.6 
        elif sources_percent_per_country['Unnamed: 2'][sourc] == 'kt':
            calculation_factor =  4184.00000000001*0.001   #kt 4184,00000000001 GJ/kt  * 0,001 TJ/GJ
        else: 
            calculation_factor = 1    

        if (EU_COUNTRIES[country] == 'Belgium' or EU_COUNTRIES[country] == 'Cyprus' or EU_COUNTRIES[country] == 'Czechia'
                or EU_COUNTRIES[country] == 'Denmark' or EU_COUNTRIES[country] == 'Finland' or EU_COUNTRIES[country] == 'Georgia'
                or EU_COUNTRIES[country] == 'Greece'or EU_COUNTRIES[country] == 'Hungary'or EU_COUNTRIES[country] == 'Ireland'
                or EU_COUNTRIES[country] == 'Italy' or EU_COUNTRIES[country] == 'Lithuania' or EU_COUNTRIES[country] == 'Malta'
                or EU_COUNTRIES[country] == 'Poland' or EU_COUNTRIES[country] == 'Romania' or EU_COUNTRIES[country] == 'Malta'
                or EU_COUNTRIES[country] == 'Sweden' or EU_COUNTRIES[country] == 'Slovakia'):
            row_start = 'Unnamed: 9'
            year_start = 2016 #higher than 2010
            row_stop = 'Unnamed: 11'
            year_stop = 2018
        else: 
            row_start = 'Unnamed: 3'
            year_start = 2010
            row_stop = 'Unnamed: 11'
            year_stop = 2018

        if math.isnan(sources_percent_per_country[row_start][sourc]) == True:
                sources_percent_start = 0
        else: 
            sources_percent_start = sources_percent_per_country[row_start][sourc]
            
        if math.isnan(sources_percent_per_country[row_stop][sourc]) == True:
            sources_percent_stop = 0
        else: 
            sources_percent_stop = sources_percent_per_country[row_stop][sourc]

        if sourc == 4:
            sources_start_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_start*calculation_factor)]]) # unit TJ
            sources_stop_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_stop*calculation_factor)]]) # unit TJ
        else: #unit TJ
            sources_start_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_start*calculation_factor)]], \
                ).append(sources_start_year, ignore_index=True) 
            sources_stop_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_stop*calculation_factor)]], \
                ).append(sources_stop_year, ignore_index=True) 

    # sum of the energy consumption per source for space heating
    sum_start_year = 0
    for sum_start in range(0, len(sources_start_year)):
        if (sources_start_year[1][sum_start] != 'nan' and sum_start != 0
                and sum_start != 1 and sum_start != 2 and sum_start != 3 and sum_start != 5
                and sum_start != 6 and sum_start != 7):
            sum_start_year += float(sources_start_year[1][sum_start])

    sum_stop_year = 0
    for sum_stop in range(0, len(sources_stop_year)):
        if (sources_stop_year[1][sum_stop] != 'nan' and sum_stop != 0
                and sum_stop != 1 and sum_stop != 2 and sum_stop != 3 and sum_stop != 5
                and sum_stop != 6 and sum_stop != 7):
            sum_stop_year += float(sources_stop_year[1][sum_stop])
        
    #Ratio of energy sources for a country in current years 
    for relativ in range(0, len(sources_start_year)):

        if (relativ != 0 and relativ != 1 and relativ != 2 and relativ != 3 and relativ != 5
                and relativ != 6 and relativ != 7):

            if relativ == 4:
                sources_rel_start_year = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating_temp[relativ], ((sources_start_year[1][relativ]/sum_start_year)*100)]]) # unit % start with electricity
                sources_rel_stop_year = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating_temp[relativ], ((sources_stop_year[1][relativ]/sum_stop_year)*100)]]) # unit %
            else: 
                sources_rel_start_year = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating_temp[relativ], ((sources_start_year[1][relativ]/sum_start_year)*100)]], \
                    ).append(sources_rel_start_year, ignore_index=True) 
                sources_rel_stop_year = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating_temp[relativ], ((sources_stop_year[1][relativ]/sum_stop_year)*100)]], \
                    ).append(sources_rel_stop_year, ignore_index=True) 

    # prognose rate per subsector
    for prog in range(0, len(sources_rel_stop_year)):
        
        if year_start == 2010:
            prog_rate_temp = ((((sources_rel_stop_year[2][prog]/sources_rel_start_year[2][prog])**(1/(year_stop-year_start))))-1)*100  # unit %/a
            source_prog_value_temp = sources_rel_stop_year[2][prog]*((1+(prog_rate_temp/100))**(PROGNOS_YEAR-year_stop)) #unit %

            if prog == 0:
                sources_prog_rate = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (prog_rate_temp)]]) # unit %/a
                sources_prog_value = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (source_prog_value_temp)]])
            else: 
                sources_prog_rate = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (prog_rate_temp)]], \
                    ).append(sources_prog_rate, ignore_index=True) 
                sources_prog_value = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (source_prog_value_temp)]], \
                    ).append(sources_prog_value, ignore_index=True) 

        else: 
            prog_rate_temp = 0
            source_prog_value_temp = sources_rel_stop_year[2][prog] #unit %

            if prog == 0:
                sources_prog_rate = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (prog_rate_temp)]]) # unit %/a
                sources_prog_value = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (source_prog_value_temp)]])
            else: 
                sources_prog_rate = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (prog_rate_temp)]], \
                    ).append(sources_prog_rate, ignore_index=True) 
                sources_prog_value = pd.DataFrame([[EU_COUNTRIES[country], sources_space_heating[prog], (source_prog_value_temp)]], \
                    ).append(sources_prog_value, ignore_index=True)

    # control 100% by prognose, else correction
    sum_control = 0
    for control in range(0, len(sources_prog_value)):
        sum_control += sources_prog_value[2][control]

    if sum_control > 100: 
        correction_factor = (sum_control-100)/6 #six sources

        for control in range(0, len(sources_prog_value)):
            sources_prog_value[2][control] = sources_prog_value[2][control]-correction_factor
                
        sum_control = 0
        for control in range(0, len(sources_prog_value)):
            sum_control += sources_prog_value[2][control]
                
    if sum_control < 100: 
        correction_factor = (100-sum_control)/6 #six sources

        for control in range(0, len(sources_prog_value)):
            sources_prog_value[2][control] = sources_prog_value[2][control]+correction_factor
                
        sum_control = 0
        for control in range(0, len(sources_prog_value)):
            sum_control += sources_prog_value[2][control]          

    #negative control
    negative_values = 0
    for negative in range(0, len(sources_prog_value)):
        if sources_prog_value[2][negative] < 0:
            sources_prog_value[2][negative] = 0  
            negative_values += 1

    if sum_control > 100: 
        correction_factor = (sum_control-100)/(6-negative_values) #six sources

        for control in range(0, len(sources_prog_value)):
            if sources_prog_value[2][control] != 0:
                sources_prog_value[2][control] = sources_prog_value[2][control]-correction_factor
                
        sum_control = 0
        for control in range(0, len(sources_prog_value)):
            sum_control += sources_prog_value[2][control]     

    return sources_rel_stop_year, sources_prog_value   

def load_sector_data_countries(CTRL, EU_COUNTRIES, country, PROGNOS_YEAR, sources_percent_per_country):

    for sourc in range(4,17):

        # calculated source relstion in percent
        if sources_percent_per_country['Unnamed: 2'][sourc] == 'GWh':
            calculation_factor = 3.6 
        elif sources_percent_per_country['Unnamed: 2'][sourc] == 'kt':
            calculation_factor =  4184.00000000001*0.001   #kt 4184,00000000001 GJ/kt  * 0,001 TJ/GJ
        else: 
            calculation_factor = 1    

        if (EU_COUNTRIES[country] == 'Belgium' or EU_COUNTRIES[country] == 'Cyprus' or EU_COUNTRIES[country] == 'Czechia'
                or EU_COUNTRIES[country] == 'Denmark' or EU_COUNTRIES[country] == 'Finland' or EU_COUNTRIES[country] == 'Georgia'
                or EU_COUNTRIES[country] == 'Greece'or EU_COUNTRIES[country] == 'Hungary'or EU_COUNTRIES[country] == 'Ireland'
                or EU_COUNTRIES[country] == 'Italy' or EU_COUNTRIES[country] == 'Lithuania' or EU_COUNTRIES[country] == 'Malta'
                or EU_COUNTRIES[country] == 'Poland' or EU_COUNTRIES[country] == 'Romania' or EU_COUNTRIES[country] == 'Malta'
                or EU_COUNTRIES[country] == 'Sweden' or EU_COUNTRIES[country] == 'Slovakia'):
            row_start = 'Unnamed: 9'
            year_start = 2016 #higher than 2010
            row_stop = 'Unnamed: 11'
            year_stop = 2018
        else: 
            row_start = 'Unnamed: 3'
            year_start = 2010
            row_stop = 'Unnamed: 11'
            year_stop = 2018

        if math.isnan(sources_percent_per_country[row_start][sourc]) == True:
                sources_percent_start = 0
        else: 
            sources_percent_start = sources_percent_per_country[row_start][sourc]
            
        if math.isnan(sources_percent_per_country[row_stop][sourc]) == True:
            sources_percent_stop = 0
        else: 
            sources_percent_stop = sources_percent_per_country[row_stop][sourc]

        if sourc == 4:
            sources_start_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_start*calculation_factor)]]) # unit TJ
            sources_stop_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_stop*calculation_factor)]]) # unit TJ
        else: #unit TJ
            sources_start_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_start*calculation_factor)]], \
                ).append(sources_start_year, ignore_index=True) 
            sources_stop_year = pd.DataFrame([[EU_COUNTRIES[country], (sources_percent_stop*calculation_factor)]], \
                ).append(sources_stop_year, ignore_index=True) 

    # sum of the energy consumption 
    sum_start_year = 0
    for sum_start in range(0, len(sources_start_year)):
        if (sources_start_year[1][sum_start] != 'nan' and sum_start != 0
                and sum_start != 1 and sum_start != 2 and sum_start != 3 and sum_start != 5
                and sum_start != 6 and sum_start != 7):
        
            if sum_start == 12:
                sum_start_year += float(sources_start_year[1][sum_start]*1)  # elec efficiency 100%
            
            elif sum_start == 11:
                sum_start_year += float(sources_start_year[1][sum_start]*1)  # heat efficiency 100%                

            elif sum_start == 10:
                sum_start_year += float(sources_start_year[1][sum_start]*0.96)  # gas efficiency 96%

            elif sum_start == 9:
                sum_start_year += float(sources_start_year[1][sum_start]*0.92)  # wodd etc efficiency 0.92%

            elif sum_start == 8:
                sum_start_year += float(sources_start_year[1][sum_start]*0.9)  # oil efficiency 0.9%

            elif sum_start == 4:
                sum_start_year += float(sources_start_year[1][sum_start]*0.8)  # waste efficiency 80%

            else:
                sum_start_year += float(sources_start_year[1][sum_start])

    sum_stop_year = 0
    for sum_stop in range(0, len(sources_stop_year)):
        if (sources_stop_year[1][sum_stop] != 'nan' and sum_stop != 0
                and sum_stop != 1 and sum_stop != 2 and sum_stop != 3 and sum_stop != 5
                and sum_stop != 6 and sum_stop != 7):
        
            if sum_stop == 12:
                sum_stop_year += float(sources_stop_year[1][sum_stop]*1)  # elec efficiency 100%
            
            elif sum_stop == 11:
                sum_stop_year += float(sources_stop_year[1][sum_stop]*1)  # heat efficiency 100%                

            elif sum_stop == 10:
                sum_stop_year += float(sources_stop_year[1][sum_stop]*0.96)  # gas efficiency 96%

            elif sum_stop == 9:
                sum_stop_year += float(sources_stop_year[1][sum_stop]*0.92)  # wodd etc efficiency 0.92%

            elif sum_stop == 8:
                sum_stop_year += float(sources_stop_year[1][sum_stop]*0.9)  # oil efficiency 0.9%

            elif sum_stop == 4:
                sum_stop_year += float(sources_stop_year[1][sum_stop]*0.8)  # waste efficiency 80%

            else:
                sum_stop_year += float(sources_stop_year[1][sum_stop])
            
            #sum_stop_year += float(sources_stop_year[1][sum_stop]) #sum_stop_year last status of energy demand

    # prognose rate

    if PROGNOS_YEAR > year_stop:
        if year_start == 2010 and CTRL.HH_METHOD_REST == "trend":
            if sum_start_year == 0:
                sum_start_year = 0.01*(10**-15)

            prog_rate_temp = ((((sum_stop_year/sum_start_year)**(1/(year_stop-year_start))))-1)*100  # unit %/a
            source_prog_value_temp = sum_stop_year*((1+(prog_rate_temp/100))**(PROGNOS_YEAR-year_stop)) #unit TJ
        else: 
            prog_rate_temp = 0
            source_prog_value_temp = sum_stop_year #unit TJ
    else:

        if year_start == 2010 and CTRL.HH_METHOD_REST == "trend":
            if sum_start_year == 0:
                sum_start_year = 0.01*(10**-15)

            prog_rate_temp = ((((sum_stop_year/sum_start_year)**(1/(year_stop-year_start))))-1)*100  # unit %/a
            source_prog_value_temp = sum_start_year*((1+(prog_rate_temp/100))**(PROGNOS_YEAR-year_start)) #unit TJ
        else: 
            prog_rate_temp = 0
            source_prog_value_temp = sum_start_year #unit TJ

    return source_prog_value_temp,sum_stop_year