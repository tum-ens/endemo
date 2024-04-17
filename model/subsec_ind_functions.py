###############################################################################                                                                                   
# Functions for industrial sector calculations
###############################################################################
"""This module defines functions for the industry sector
If subsectors have to be added:
    1) name of subsector in CTRL
    2) table of subsector production amounts in get_prepair_input_data
    3) sheets in specific and BAT consumption
"""
###############################################################################
# import libraries
from libraries import *
from op_methods import redistribution_NUTS2
        
###############################################################################
#functions
###############################################################################
def assign_his_prod_quantity(CTRL, ind_data, industry):
    
    if "_classic" in industry:
        industry = industry.replace("_classic","")
    elif industry == "steel_direct":
        # substituiton between steel_prim and DRI
        if "steel_prim" in CTRL.IND_SUBECTORS:
            industry = "steel_prim"
        else:
            industry = "steel"
        
    #if industry not in CTRL.IND_FOOD:
    industry_table = getattr(ind_data, industry + "_table")
    industry_table.columns = [str(a) for a in industry_table.columns] # to standardise all tables
    #else:
    #    industry_table_name = "food_table"
    #    industry_table = getattr(ind_data,industry_table_name)[industry]
        
    return industry_table

#------------------------------------------------------------------------------
# ckeck if the country belongs to considered countries. 
# If yes - include in the  list.
def incl_considered_countries(CONSIDERED_COUNTRIES, proposed_countries):
    country_list = []
    for country in CONSIDERED_COUNTRIES:
        if country in proposed_countries:
            country_list.append(country)
    return country_list#[country for country in proposed_countries if country in CONSIDERED_COUNTRIES]

def country_clustering(IND_VOLUM_PROGNOS, industry, CONSIDERED_COUNTRIES):
    if IND_VOLUM_PROGNOS == "Quadratic GDP function":
        if industry in ["steel", "steel_direct", "steel_prim", "steel_sec"]:
            country_group_4=incl_considered_countries(CONSIDERED_COUNTRIES,["Romania", "Bulgaria", "North Macedonia", "Montenegro", "Bosnia and Herzegovina"])#
            country_group_2=incl_considered_countries(CONSIDERED_COUNTRIES,["Norway","Netherlands","Switzerland"])
            country_group_zero=incl_considered_countries(CONSIDERED_COUNTRIES,["Ireland", "Denmark", "Albania","Latvia", "Lithuania", "Estonia", "Iceland"])# prognose = 0
            
            country_group_3=[]
            for country in CONSIDERED_COUNTRIES:
                if country not in country_group_2 + country_group_4 + country_group_zero:
                    country_group_3.append(country) 
                    
            country_group=[group for group in [country_group_2, country_group_3, country_group_4] if len(group)>0]
            country_group_separate=[]
            
        elif industry=="alu_prim":
            country_group_2=incl_considered_countries(CONSIDERED_COUNTRIES,["Montenegro", "Bosnia and Herzegovina"])#
            country_group_4=incl_considered_countries(CONSIDERED_COUNTRIES,["Netherlands", "United Kingdom"]) #
            country_group_zero=incl_considered_countries(CONSIDERED_COUNTRIES,["Austria", "Hungary", "Croatia","Poland","Belgium", "Bulgaria",
                                "Czechia", "Denmark", "Ireland", "Latvia", "Lithuania", "Estonia",
                                "Portugal", "Finland", "North Macedonia", "Albania", "Serbia"])
            country_group_separate=incl_considered_countries(CONSIDERED_COUNTRIES,["Norway","Iceland", "Italy"]) 
            
            country_group_3=[]
            for country in CONSIDERED_COUNTRIES:
                if country not in country_group_2+country_group_4+country_group_separate+country_group_zero:
                    country_group_3.append(country) 
                    
            country_group=[group for group in [country_group_2, country_group_3,country_group_4] if len(group)>0]
        
        elif industry in ["copper_prim", "copper_sec", "chlorine"]:
            # change!!
            country_group = []; country_group_zero = []
            country_group_separate=[country for country in CONSIDERED_COUNTRIES]
            
        elif industry=="cement":
            country_group_zero = incl_considered_countries(CONSIDERED_COUNTRIES,["Montenegro"])
            country_group_2 = incl_considered_countries(CONSIDERED_COUNTRIES,["Slovakia", "North Macedonia",  "Hungary", "Poland",
                              "Belgium", "Denmark", "Sweden", "Finland", "France"]) #parabel with delta
            # Cyprus would also belong to group 3
            country_group_3 = incl_considered_countries(CONSIDERED_COUNTRIES,["Spain", "Italy"]) # "Latvia", "Slovenia",
            country_group_4 = incl_considered_countries(CONSIDERED_COUNTRIES,["Ireland", "Greece"]) #with delta
            country_group_5 = incl_considered_countries(CONSIDERED_COUNTRIES,["Netherlands", "Austria","Switzerland", "Norway", "Czechia", "Germany"])
            country_group_6 = incl_considered_countries(CONSIDERED_COUNTRIES,["United Kingdom", "Lithuania"])
            country_group_7 = incl_considered_countries(CONSIDERED_COUNTRIES,["Croatia", "Serbia","Bulgaria","Portugal","Estonia"])
            country_group_8 = incl_considered_countries(CONSIDERED_COUNTRIES,["Romania", "Bosnia and Herzegovina"])
            #country_group_9 = incl_considered_countries(CONSIDERED_COUNTRIES,["Germany", "Netherlands", "France"])
           
            country_group = [group for group in [country_group_2, country_group_3,country_group_4, country_group_5,
                          country_group_6,country_group_7, country_group_8] if len(group)>0] #country_group_9
           
            country_group_separate=[]
            for country in CONSIDERED_COUNTRIES:
                if country not in country_group_2 + country_group_3 + country_group_4 +\
                    country_group_5 + country_group_6 + country_group_7 + country_group_8 + country_group_zero:
                        country_group_separate.append(country) 
                    
        elif industry == "paper":
            country_group_2=incl_considered_countries(CONSIDERED_COUNTRIES,["Sweden", "Spain", "Italy", "Portugal","Poland", "Hungary"])
            country_group_4=incl_considered_countries(CONSIDERED_COUNTRIES,["Germany",  "Austria", "Slovenia", "Switzerland","Belgium",  "Netherlands"])
            country_group_5=incl_considered_countries(CONSIDERED_COUNTRIES,["Ireland", "Iceland", "Denmark"])
            country_group_6=incl_considered_countries(CONSIDERED_COUNTRIES,["France", "United Kingdom", "Bulgaria", "Czechia", "Estonia", "Lithuania"])
            country_group_separate=incl_considered_countries(CONSIDERED_COUNTRIES,["Norway", "Finland"])
            country_group_zero=incl_considered_countries(CONSIDERED_COUNTRIES,["Malta", "Cyprus","Montenegro", "North Macedonia", "Serbia",
                                "Albania", "Bosnia and Herzegovina", "Liechtenstein"])
            
            country_group_3=[]
            for country in CONSIDERED_COUNTRIES:
                if country not in country_group_2 + country_group_4 +\
                    country_group_5 + country_group_6 + country_group_separate + country_group_zero:
                        country_group_3.append(country) 
                        
            country_group = [group for group in [country_group_2, country_group_3, country_group_4, country_group_5, country_group_6] if len(group)>0]
                        
        else:
            country_group = []; country_group_zero = [];  country_group_separate = []
            
    else:
        country_group = []; country_group_zero = []
        country_group_separate=[country for country in CONSIDERED_COUNTRIES]
        
    return country_group_separate, country_group_zero, country_group
#------------------------------------------------------------------------------
    
# industry production per person in tonnen
def ind_production_per_person(FILE, industry, industry_table_pd, pop_table, abb_table, IND_END_YEAR, CONSIDERED_COUNTRIES ):
    
    start_year=max(int(industry_table_pd.columns[1]), int(pop_table.columns[1]))
    
    col_content = []
    with open(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY, "Production of " + industry + " per Person.csv"), "w", newline='') as result:
        wtr= csv.writer( result, delimiter=';')

        col_names=["Country"]
        for i in range(start_year, IND_END_YEAR):
            col_names.append(int(i))
        wtr.writerow(col_names) 
        
        for country in CONSIDERED_COUNTRIES:
            #abb_idx=list(abb_table["Country"]).index(country)
            #country_de=abb_table["Country_de"][abb_idx]
    
            try:
                idx_industry=list(industry_table_pd["Country"]).index(country)
            except:
                idx_industry=-1
                # print(country + " has no production of "+ industry)
            idx_pop=list(pop_table["Country"]).index(country)
            
            # product_per_person is product in Tonnes per person
            y=[country]     
            for year in range(start_year, IND_END_YEAR):
                year = str(year)
                if idx_industry!=-1:
                    #if industry_table_pd[year][idx_industry]>0: 
                        # unit: tausend tonnes in tonnes
                    y.append(industry_table_pd[year][idx_industry]*1000
                             /pop_table[year][idx_pop])
                    #else:
                        #y.append(0)
                else:
                    y.append(0)
                             
            wtr.writerow(y)
            col_content.append(y)
            
    production_per_person_df = pd.DataFrame(col_content, columns = col_names)
    #production_per_person_df.to_excel(result, sheet_name="Data", index=False, startrow=0)
    return production_per_person_df
    
#------------------------------------------------------------------------------      
# corresponding GDP and industry
# Make orresponding industry table as if the data are for the whole land. 
#If the data should be per person, read the already written table with industry pp
            
def ind_corresponding_gdp_industry(CTRL, industry_table_pd,product_pp_table_c,
                                   gdp_table, abb_table, industry):
    
    start_year= max(int(industry_table_pd.columns[1]), int(gdp_table.columns[3]))
    
    col_names=["Country"]
    for i in range(start_year,CTRL.IND_END_YEAR):
        col_names.append(i)
    
    corresponding_gdp=[]
    corresponding_industry=[]
    
    for country in CTRL.CONSIDERED_COUNTRIES:
        abb_idx=list(abb_table["Country"]).index(country)
        country_de=abb_table["Country_de"][abb_idx]

        try:
            idx_industry=list(industry_table_pd["Country"]).index(country)
        except:
            idx_industry=-1  
        idx_gdp=list(gdp_table["Country"]).index(country)
        
        # product_per_person is product in Tonnes per person
        y=[country]
        # x is GDP of the country in the same years as y (corresponding_gdp)
        x=[country]
        
        if idx_industry!=-1:
            for year in range(start_year,CTRL.IND_END_YEAR):
                year = str(year)
                y.append(industry_table_pd[year][idx_industry]*1000)
                x.append(gdp_table[int(year)][idx_gdp])
        else:
            for year in range(start_year,CTRL.IND_END_YEAR):
                y.append(0)
                x.append(gdp_table[int(year)][idx_gdp])
                         
        corresponding_gdp.append(x)
        corresponding_industry.append(y)
      
    corresponding_gdp_table=pd.DataFrame(corresponding_gdp, columns=col_names)
    
    if CTRL.IND_PRODUCTION_QUANTITY_PER_CAPITA:
        # read column names as intigers
        int_names=[product_pp_table_c.columns[0]]
        for column in product_pp_table_c.columns[1:len(product_pp_table_c.columns)]:
            int_names.append(int(column))
        
        product_pp_table_c.columns=int_names
        corresponding_industry_table=product_pp_table_c

    else:
        corresponding_industry_table=pd.DataFrame(corresponding_industry, columns=col_names)
    
    return corresponding_gdp_table, corresponding_industry_table
    
#------------------------------------------------------------------------------    
def ind_plot_his_production_data_GDP(CTRL, industry, active_group,
                                 corresponding_industry_table,
                                 corresponding_gdp_table):
    
    start_year = max(corresponding_industry_table.columns[1], corresponding_gdp_table.columns[1])
    
    figure4=plt.figure(figsize=(6,4))
    
    
    for country in active_group:
    
        idx_industry=list(corresponding_industry_table["Country"]).index(country)
        idx_gdp=list(corresponding_gdp_table["Country"]).index(country)
    
        # product_per_person is product in Tonnes per person
        y=[country]
        # x is GDP of the country in the same years as y (corresponding_gdp)
        x=[country]
        
        start_counter=0
        while math.isnan(corresponding_gdp_table[start_year+start_counter][idx_gdp]):
            start_counter+=1 
            
        for year in corresponding_gdp_table.columns[(1+start_counter):]:
            y.append(corresponding_industry_table[year][idx_industry])
            x.append(corresponding_gdp_table[year][idx_gdp])                    

        # plot per group
        plt.plot(x[1:],y[1:], label = "historical data " + country)
        if "_prim" in industry:
            industry = industry.replace("_prim"," primary")
            if "alu" in industry:
                industry = industry.replace("alu"," aluminium")
        elif "_sec" in industry:
            industry = industry.replace("_sec"," secondary")
            if "alu" in industry:
                industry = industry.replace("alu"," aluminium")
        
    if CTRL.IND_PRODUCTION_QUANTITY_PER_CAPITA:
        plt.ylabel("Production quantity of "+ industry+" [t/per]")
    else:
        plt.ylabel("Production quantity of "+ industry+" in tonns")

            
    plt.xlabel("GDP per person [USD]")

    plt.grid(True)
    #plt.show()
    
#-------------------------------------------------------------------------------
def ind_plot_his_production_data_timeline(CTRL,industry, active_group, corresponding_industry_table, plot_data):
    
    figure4=plt.figure()
    
    x = [int(year) for year in corresponding_industry_table.columns[1:]]
    x.insert(0, "country")
    
    for country in active_group:#CTRL.CONSIDERED_COUNTRIES:
        idx_industry=list(corresponding_industry_table["Country"]).index(country)
    
        y=[country]

        for year in x[1:]:
            y.append(corresponding_industry_table[year][idx_industry])
              
        # plot per group
        plt.plot(x[1:],y[1:])

    # Layout anpassen:
    if "_prim" in industry:
        industry = industry.replace("_prim"," primary")
        if "alu" in industry:
            industry = industry.replace("alu"," aluminium")
    elif "_sec" in industry:
        industry = industry.replace("_sec"," secondary")
        if "alu" in industry:
            industry = industry.replace("alu"," aluminium")
                
    if plot_data=="production":
        if CTRL.IND_PRODUCTION_QUANTITY_PER_CAPITA:
            plt.ylabel("Production quantity of "+ industry+" in tonns per person")
        else:
            plt.ylabel("Production quantity of "+ industry+" in tonns")
    elif plot_data=="spec_energy_el":
        plt.axis([1950,2050,0,15])
        plt.ylabel("Specific electrical energy in [GJ/t]")
    elif plot_data=="spec_energy_heat":
        plt.axis([1950,2050,0,50])
        plt.ylabel("Specific heat energy in [GJ/t]")
            
    plt.xlabel("Years")
    plt.grid(True)
    #plt.show()
    
#------------------------------------------------------------------------------        
def plot_model_data_GDP(FILE, IND_ACTIVATE_TIME_TREND_MODEL, active_group, corresponding_gdp_table, koef, gdp_prognosis,
                    idx_group, delta_active, industry, group, file_path):   
    
    start_year = corresponding_gdp_table.columns[1]
    
    # temp: temporary index to choose for each country its delta koefficient 
    N=len(active_group)
    
    # set palette for plot
    palette = itertools.cycle(sns.color_palette())
    
    temp=0
    for country in active_group:
        start_counter=0
        while math.isnan(corresponding_gdp_table[start_year+start_counter][idx_group[temp]]):
            start_counter+=1
        #start_gdp=corresponding_gdp_table[start_year+start_counter][idx_group[temp]]//100*100
        gdp_list = corresponding_gdp_table.loc[idx_group[temp], :].values.flatten().tolist()[1:]
        gdp_list_withoutnan = [element for element in gdp_list if not math.isnan(element)]
        # [1:] to skip the country name
        start_gdp = min(gdp_list_withoutnan)//100*100
        idx_gdp_prog=list(gdp_prognosis["Country"]).index(country)
        #end_gdp=gdp_prognosis["GDP"][idx_gdp_prog]//100*100
        # [1:] to skip the country name
        end_gdp = max(max(gdp_list_withoutnan), gdp_prognosis["GDP"][idx_gdp_prog])//100*100
        if end_gdp > start_gdp:
            x1 = np.arange(start_gdp , end_gdp, 100)
            t = np.arange(1 , end_gdp-start_gdp+1, 1)
        else:
            x1 = np.arange(end_gdp, start_gdp, 100)
            t = np.arange(1, start_gdp-end_gdp+1, 1)
        
        if delta_active:
            if IND_ACTIVATE_TIME_TREND_MODEL==False:
                if temp<N-1:
                    y1 =  koef[0] + koef[1]*x1 + koef[2]*x1**2 + koef[3+temp]
                else:
                    y1 =  koef[0] + koef[1]*x1 + koef[2]*x1**2 
            else:
                if temp<N-1:
                    y1 =  koef[0] + koef[1]*x1 + koef[2]*x1**2 + koef[3]*t + koef[4+temp]
                else:
                    y1 =  koef[0] + koef[1]*x1 + koef[2]*x1**2 + koef[3]*t
        else:
            if IND_ACTIVATE_TIME_TREND_MODEL==False:
                    y1 =  koef[0] + koef[1]*x1 + koef[2]*x1**2 
            else:
                    y1 =  koef[0] + koef[1]*x1 + koef[2]*x1**2 + koef[3]*t
                    
        # Model will cut all production values smaller then zero to be equal to zero
        y1[y1 < 0] = 0
        # Funktion plotten:
        color_fig = next(palette)
        plt.plot(x1,y1,'--', color = color_fig, label = "model data "+country)
        plt.legend(loc="upper left")
        plt.text(x1[-2], y1[-2], country)
        temp+=1
        
    if N==1:
        plt.savefig(os.path.join(file_path, "Production_quanitity_vs_GDP_" + industry + country + ".png"),bbox_inches='tight')
    else:
        plt.savefig(os.path.join(file_path, "Production_quanitity_vs_GDP_" + industry + str(group) + ".png"),bbox_inches='tight')
    #plt.show()
#------------------------------------------------------------------------------
def plot_model_data_time(industry, country, corresponding_industry_table, koef, FORECAST_YEAR, file_path):
    
    # set palette for plot
    palette = itertools.cycle(sns.color_palette())
    
    x1=list(range(int(corresponding_industry_table.columns[1]),FORECAST_YEAR+1))
    if len(x1) == 1:
        x1.insert(0,FORECAST_YEAR-1)
    y1 = [koef[0] + koef[1] * i  for i in x1]
    #y1 =  koef[0] + koef[1]*x1 
    
    # Model will cut all production values smaller then zero to be equal to zero
    #y1[y1 < 0] = 0
    y1 = [max(element, 0) for element in y1]
    
    # Function plot:       
    color_fig = next(palette)
    plt.plot(x1,y1,'--', color = color_fig)  
    plt.text(x1[-1], y1[-1], country)
    
    plt.savefig(os.path.join(file_path, "Production_quanitity_vs_time_" + industry + country + ".png"),bbox_inches='tight')
    #plt.show()    
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------          
def save_koef(coeff_content,  active_group, koef, IND_ACTIVATE_TIME_TREND_MODEL, delta_active):   
         
    for idx_country, country in enumerate(active_group):  
        coeff_row=[country, koef[0], koef[1]]
        if len(koef)>2:
            coeff_row.append(koef[2])
        if IND_ACTIVATE_TIME_TREND_MODEL:
            coeff_row.append(koef[3])
            
        if delta_active:
            if idx_country < (len(active_group)-1):
                coeff_row.append( koef[3+int(IND_ACTIVATE_TIME_TREND_MODEL)+idx_country])
            else:
                coeff_row.append(0)
        else:
            coeff_row.append(0)
    
        coeff_content.append(coeff_row)

    return coeff_content     

#------------------------------------------------------------------------------    
def spec_en_source_timelines (CTRL, FILE, ind_data, industry, efficiency_table, corr_industry_table, pop_table, abb_table):
    
    # Opening energy consumption data per subsector with multiple sheets (with different energy carriers)
    if industry=="steel":
        en_demand=ind_data.en_demand_steel
    elif industry=="paper":
        en_demand=ind_data.en_demand_paper
    # elif industry=="alu_prim":
    #     en_demand=pd.read_excel(os.path.join(FILE_PATH_INPUT_DATA, "industry", "nrg_bal_s_nichtEisenMetalle.xls"),
    #                                    sheet_name=sheet,skiprows=0)
    # elif industry=="cement":
    #     en_demand=pd.read_excel(os.path.join(FILE_PATH_INPUT_DATA, "industry", "nrg_bal_s_nichtMetallische.xls"),
    #                                    sheet_name=sheet,skiprows=0)  
    
    start_y=max(int(en_demand["Elektrizitaet"].columns[1]), int(corr_industry_table.columns[1]))
    years=list(range(start_y, CTRL.IND_END_YEAR))
    years.insert(0,"Country")
    spec_energy_el=[]
    spec_energy_heat=[]
    
    result = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY, "spec_energy_" + industry + "timelines.xlsx"), engine='xlsxwriter')
    
    for country in CTRL.CONSIDERED_COUNTRIES:
        country_de=abb_table["Country_de"][list(abb_table["Country"]).index(country)]
        try: 
            idx_energy=list(en_demand["Elektrizitaet"]["GEO/TIME"]).index(country_de)
        except:
            idx_energy=-1
        idx_industry=list(corr_industry_table["Country"]).index(country)
        spec_energy_el_line=[country]
        spec_energy_heat_line=[country]
        
        # Set default value in the case that energy demand of the countries subsector is not known
        idx_spec_consum=list(ind_data.spec_consum_vordef[industry]["Country"]).index("all")
        def_val_el = ind_data.spec_consum_vordef[industry]["Spec electricity consumption [GJ/t]"][idx_spec_consum]
        def_val_heat = ind_data.spec_consum_vordef[industry]["Spec heat consumption [GJ/t]"][idx_spec_consum]
            
        if CTRL.IND_PRODUCTION_QUANTITY_PER_CAPITA:
            idx_pop=list(pop_table["Country"]).index(country)
        else:
            pop_val= 1
        
        # If consumed energy in subsector is known, specific energy consumption can be calculated
        if idx_energy!=-1:
            for year in years[1:]:
                electricity=0
                heat=0
                if CTRL.IND_PRODUCTION_QUANTITY_PER_CAPITA:
                    pop_val = pop_table[str(year)][idx_pop]
                for idx_carrier, carrier in enumerate(efficiency_table["Energy carrier"]):
                    # skip nan values
                    if carrier in en_demand:
                        electricity+=en_demand[carrier][str(year)][idx_energy]*efficiency_table["Electricity production [-]"][idx_carrier] # in TJ
                        heat+=en_demand[carrier][str(year)][idx_energy]*efficiency_table["Heat production [-]"][idx_carrier] # in TJ
                
                # If subsector's production is different then zero, specific energy consumption can be calculated
                if corr_industry_table[year][idx_industry]>0:
                    spec_energy_el_line.append(electricity*1000/(corr_industry_table[year][idx_industry]*pop_val)) # in GJ/t
                    spec_energy_heat_line.append(heat*1000/(corr_industry_table[year][idx_industry]*pop_val)) # in GJ/t
                # If there was no production for the given year, specific energy consumption for that year cannot be calculated
                else:
                    spec_energy_el_line.append(np.nan)
                    spec_energy_heat_line.append(np.nan)
        
        # If consumed energy in subsector is not known, default value for specific energy consumption is taken
        else:
            print(country, " had no data about energy consumption of ", industry, ". Default value taken.") 
            for year in years[1:]:
                spec_energy_el_line.append(def_val_el)
                spec_energy_heat_line.append(def_val_heat)
                
        spec_energy_el.append(spec_energy_el_line)
        spec_energy_heat.append(spec_energy_heat_line)   
      
    industry_spec_el=pd.DataFrame(spec_energy_el, columns=years)
    industry_spec_heat=pd.DataFrame(spec_energy_heat, columns=years)
    industry_spec_el.to_excel(result, sheet_name=str(industry)+"_el", index=False, startrow=0)
    industry_spec_heat.to_excel(result, sheet_name=str(industry)+"_heat", index=False, startrow=0)
    result.close()
    
    return industry_spec_el, industry_spec_heat
  
#------------------------------------------------------------------------------
def industry_en_demand(CTRL, ind_data, spec_consum_const, efficiency_table, efficiency_heat_levels, coeff_el_df, coeff_heat_df,
                           abb_table,  industry, volume_coeff, pop_prognosis, GDP_prognosis,
                           pop_table, const_industries,
                           industry_spec_el, industry_spec_heat):

    spec_consum = ind_data.spec_consum_vordef[industry]
    energy=[]
    volume=[]
    for country in CTRL.CONSIDERED_COUNTRIES: 
        idx_gdp=list(GDP_prognosis["Country"]).index(country)
        gdp=GDP_prognosis["GDP"][idx_gdp]
        
        # Forecasting production quantities (total or per person)
        if CTRL.IND_VOLUM_PROGNOS in ["Linear time trend", "Exponential"] or industry in const_industries:
            idx_coeff=list(volume_coeff["Country"]).index(country)
            volume_val = (getattr(CTRL, "prod_quant_share_" + industry) *
                          (volume_coeff["coeff_0"][idx_coeff]
                           + volume_coeff["coeff_1"][idx_coeff] * CTRL.FORECAST_YEAR
                           + volume_coeff["coeff_c"][idx_coeff]))
            
            if CTRL.IND_VOLUM_PROGNOS == "Exponential" or industry in const_industries:
                volume_val =  volume_val * (1+ getattr(CTRL,"prod_quant_change_" + industry)/100)**(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR + 1)
                
        else:
            if CTRL.IND_ACTIVATE_TIME_TREND_MODEL==False:
                idx_coeff=list(volume_coeff["Country"]).index(country)
                volume_val = (getattr(CTRL, "prod_quant_share_" + industry) *
                              (volume_coeff["coeff_0"][idx_coeff]
                               + volume_coeff["coeff_1"][idx_coeff]*gdp
                               + volume_coeff["coeff_2"][idx_coeff]*gdp**2
                               + volume_coeff["coeff_c"][idx_coeff]))
        if volume_val<0:
            volume_val=0
        
        # Reading population projection (for the case of production quantity per person)
        if CTRL.IND_PRODUCTION_QUANTITY_PER_CAPITA:
            abb_pop=abb_table["Abbreviation"][list(abb_table["Country"]).index(country)]
            try:
                idx_pop=list(pop_prognosis["Country"]).index(country)
                pop_val=pop_prognosis[str(CTRL.FORECAST_YEAR)][idx_pop]
            except:
                idx_pop=list(pop_table["Country"]).index(country) 
                end_pop_year=pop_table.columns[len(pop_table.columns)-1]
                pop_val= pop_table[end_pop_year][idx_pop]
                print(country+" is not in population prognosis table. Last value taken.")
        else:
            pop_val=1
        
        # Forecasting specific energy demand
        # spec. consumptions and BAT in input files are final demands regarding fuels. 
        # Therefore efficiency of mixed fuels has to be assumed.
        efficiency = efficiency_table["Heat production [-]"][list(efficiency_table["Energy carrier"]).index("Brennstoff allgemein")]
        
        if spec_consum_const == False:
            idx_spec_consum = list(coeff_el_df["Country"]).index(country)
            idx_spec_consum_h2=list(spec_consum["Country"]).index("all")
            
            # # hard-code that spec. energy cannot grow (usualy it falls) more than 1% per year
            # # c0 + c1*forecat_year < (1+ (forecast-year)/100)*last_available_spec.consum
            # if coeff_el_df["coeff_1"][idx_spec_consum] > 0:
            #     last_spec_consum = industry_spec_el[CTRL.IND_END_YEAR -1][list(industry_spec_el["Country"]).index(country)]
            #     c1_elec = min(coeff_el_df["coeff_1"][idx_spec_consum],
            #                   ((1+(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1)/100)*last_spec_consum - coeff_el_df["coeff_0"][idx_spec_consum])/CTRL.FORECAST_YEAR)
            # else:
            c1_elec = coeff_el_df["coeff_1"][idx_spec_consum]
            
            spec_consum_el = (coeff_el_df["coeff_0"][idx_spec_consum]
                              + c1_elec*CTRL.FORECAST_YEAR
                              + coeff_el_df["coeff_c"][idx_spec_consum])
            
            # # hard-code that spec. energy cannot grow (usualy it falls) more than 1% per year
            # # c0 + c1*forecat_year < (1+ (forecast-year)/100)*last_available_spec.consum
            # if coeff_heat_df["coeff_1"][idx_spec_consum] > 0:
            #     last_spec_consum = industry_spec_heat[CTRL.IND_END_YEAR -1][list(industry_spec_heat["Country"]).index(country)]
            #     c1_heat = min(coeff_heat_df["coeff_1"][idx_spec_consum],
            #                   ((1+(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1)/100)*last_spec_consum - coeff_heat_df["coeff_0"][idx_spec_consum])/CTRL.FORECAST_YEAR)
            # else:
            c1_heat = coeff_heat_df["coeff_1"][idx_spec_consum]                                    
            
            spec_consum_heat_total = (coeff_heat_df["coeff_0"][idx_spec_consum]
                                      + c1_heat*CTRL.FORECAST_YEAR
                                      + coeff_heat_df["coeff_c"][idx_spec_consum])
        else:
            try:
                idx_spec_consum=list(spec_consum["Country"]).index(country)
            except:
                idx_spec_consum=list(spec_consum["Country"]).index("all")
            idx_spec_consum_h2 = idx_spec_consum
            
            if CTRL.IND_CALC_METHOD == "exp":
                spec_consum_el = (spec_consum["Spec electricity consumption [GJ/t]"][idx_spec_consum] 
                                  * (1 - getattr(CTRL, "spec_demand_improvement_" + industry)/100)**(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1))
                
                spec_consum_heat_total = (spec_consum["Spec heat consumption [GJ/t]"][idx_spec_consum] 
                                    * (1 - getattr(CTRL, "spec_demand_improvement_" + industry)/100)**(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1)
                                    * efficiency)
            elif CTRL.IND_CALC_METHOD == "lin":
                spec_consum_el = (spec_consum["Spec electricity consumption [GJ/t]"][idx_spec_consum] 
                                  * (1 - getattr(CTRL, "spec_demand_improvement_" + industry)/100*(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1)))
                
                spec_consum_heat_total = (spec_consum["Spec heat consumption [GJ/t]"][idx_spec_consum] 
                                    * (1 - getattr(CTRL, "spec_demand_improvement_" + industry)/100*(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1))
                                    * efficiency)
        
        ## Limiting minimal specific energy demand on BAT value
        spec_consum_el = max(spec_consum_el, ind_data.spec_consum_BAT[industry]["Spec electricity consumption [GJ/t]"][0])
        spec_consum_heat = max(spec_consum_heat_total, ind_data.spec_consum_BAT[industry]["Spec heat consumption [GJ/t]"][0] * efficiency)
        spec_consum_h2 = spec_consum["Spec hydrogen consumption [GJ/t]"][idx_spec_consum_h2]
        
        # Forecasting energy demand
        ## unit t*GJ/t -> TWh
        energy_el=volume_val*pop_val*spec_consum_el /100 /1000/3600
        energy_heat=volume_val*pop_val*spec_consum_heat/100/1000/3600
        energy_h2=volume_val*pop_val*spec_consum_h2/100/1000/3600
        
        # if industry in CTRL.IND_FOOD: 
        #     industry_heat = "food"
        # else:
        industry_heat = industry
        idx_heat_level = list(ind_data.heat_levels["Industry"]).index(industry_heat)
        energy_heat_levels = []
        elec_from_heat = 0; h2_from_heat = 0; energy_heat_remaining = 0
        for level in ["Q1", "Q2", "Q3", "Q4"]:
            idx_level = list(efficiency_heat_levels["Energy carrier"]).index(level)
            
            energy_heat_level_total = energy_heat * ind_data.heat_levels[level][idx_heat_level]/100
            
            elec_from_heat += (energy_heat_level_total 
                               * getattr(CTRL, "IND_ELEC_SUBSTITUTION_OF_HEAT_" + level)
                               / efficiency_heat_levels["Electricity [-]"][idx_level])
            h2_from_heat += (energy_heat_level_total 
                             * getattr(CTRL, "IND_H2_SUBSTITUTION_OF_HEAT_" + level) 
                             / efficiency_heat_levels["Hydrogen [-]"][idx_level])
            energy_heat_level = (energy_heat_level_total 
                                 * (1 - getattr(CTRL, "IND_ELEC_SUBSTITUTION_OF_HEAT_" + level)
                                    - getattr(CTRL, "IND_H2_SUBSTITUTION_OF_HEAT_" + level))
                                 / efficiency_heat_levels["Fuel [-]"][idx_level]) # for "heat" no efficincy conversion, for "fuel" *1/efficincy
            
            energy_heat_remaining += energy_heat_level
            energy_heat_levels.append(energy_heat_level)
    
        energy.append([country, energy_el + elec_from_heat, energy_heat_remaining, energy_h2 + h2_from_heat]+energy_heat_levels)
        
        # amount in tausend tonnes
        volume.append([country, volume_val*pop_val/100/1000])
    
    return energy, volume
    
#------------------------------------------------------------------------------
def overall_ind_demand(CTRL, result_dem, result_dem_path, rest_table, heat_levels, efficiency_heat_levels):
    
    df = pd.read_excel(result_dem, CTRL.IND_SUBECTORS[0])
    for sheet in CTRL.IND_SUBECTORS[1:len(CTRL.IND_SUBECTORS)]:
        df = df.set_index("Country").add(pd.read_excel(result_dem, sheet).set_index("Country"), fill_value=0).reset_index()

    writer = pd.ExcelWriter(result_dem_path, engine = 'openpyxl', mode='a')
    df.to_excel(writer, sheet_name="forecasted", index = False)
    
    content = []
    column_names = ["Country",	"Electricity [TWh]", "Heat [TWh]", "Hydrogen [TWh]", "Heat Q1 [TWh]", "Heat Q2 [TWh]", "Heat Q3 [TWh]", "Heat Q4 [TWh]"]
    for country in df["Country"]:
        idx = list(rest_table["Country"]).index(country)
        
        if CTRL.IND_CALC_METHOD == "exp":
            rest_el = (rest_table["Rest el"][idx]/100 * rest_table["electricity TWh "+str(CTRL.REF_YEAR)][idx] 
                       * (1 + CTRL.IND_REST_PROGRESS/100)**(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1))
            rest_heat = (rest_table["Rest heat"][idx]/100 * rest_table["fuel TWh "+str(CTRL.REF_YEAR)][idx] 
                       * (1 + CTRL.IND_REST_PROGRESS/100)**(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1))
        elif CTRL.IND_CALC_METHOD == "lin":
            rest_el = (rest_table["Rest el"][idx]/100 * rest_table["electricity TWh "+str(CTRL.REF_YEAR)][idx] 
                       * (1 + CTRL.IND_REST_PROGRESS/100*(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1)))
            rest_heat = (rest_table["Rest heat"][idx]/100 * rest_table["fuel TWh "+str(CTRL.REF_YEAR)][idx] 
                       * (1 + CTRL.IND_REST_PROGRESS/100*(CTRL.FORECAST_YEAR - CTRL.IND_END_YEAR +1)))
            
        idx_heat_level = list(heat_levels["Industry"]).index("rest")
        energy_heat_levels = []
        elec_from_heat = 0; h2_from_heat = 0; energy_heat_remaining = 0
        for level in ["Q1", "Q2", "Q3", "Q4"]:
            
            energy_heat_level_total = rest_heat * heat_levels[level][idx_heat_level]/100
            
            idx_level = list(efficiency_heat_levels["Energy carrier"]).index(level)
            
            elec_from_heat += (energy_heat_level_total 
                               * getattr(CTRL, "IND_ELEC_SUBSTITUTION_OF_HEAT_" + level)
                               / efficiency_heat_levels["Electricity [-]"][idx_level])
            h2_from_heat += (energy_heat_level_total 
                             * getattr(CTRL, "IND_H2_SUBSTITUTION_OF_HEAT_" + level)
                             / efficiency_heat_levels["Hydrogen [-]"][idx_level])
            energy_heat_level = (energy_heat_level_total 
                                 * (1 - getattr(CTRL, "IND_ELEC_SUBSTITUTION_OF_HEAT_" + level)
                                    - getattr(CTRL, "IND_H2_SUBSTITUTION_OF_HEAT_" + level)) 
                                 / efficiency_heat_levels["Fuel [-]"][idx_level]) # for "heat" no efficincy conversion, for "fuel" *1/efficincy
            energy_heat_remaining += energy_heat_level
            energy_heat_levels.append(energy_heat_level)
    
        content.append([country, rest_el + elec_from_heat, energy_heat_remaining, 0 + h2_from_heat]+energy_heat_levels)
        

    df_rest = pd.DataFrame(content, columns=column_names)
    df_rest.to_excel(writer, sheet_name="rest", index=False, startrow=0)
    
    df_overall = df.set_index("Country").add(df_rest.set_index("Country"), fill_value=0).reset_index()
    df_overall.to_excel(writer, sheet_name="IND_demand", index=False, startrow=0)
    
    writer.close()
    
    return df_overall

#------------------------------------------------------------------------------
def redistribution_NUTS2_inst_cap(IND_SUBECTORS,FORECAST_YEAR, energy_demand, pop_prognosis, inst_cap_NUTS2, abb_table, result_dem_NUTS2):
    
    temp = 0
    for industry in IND_SUBECTORS:
        if industry == "steel_direct":
            industry_cap = "steel"
        elif "_classic" in industry:
            industry_cap = industry.replace("_classic","")
        else:
            industry_cap = industry
            
        col = ["NUTS2"]
        energy_demand_sheet = pd.read_excel(energy_demand, industry)
        for i in energy_demand_sheet.columns[1:len(energy_demand_sheet.columns)]:
            col.append(i)
        content = []
                
        for idx_country_demand, country in enumerate(energy_demand_sheet["Country"]):
            abb = abb_table["Abbreviation"][list(abb_table["Country"]).index(country)]
            nuts2_regions = [i for i in pop_prognosis["Population_NUTS2"]["NUTS2"] if i[0:2] == abb]
        #rather
        # for nuts2_region in pop_prognosis:
            # find country abb -> country -> demand of country
            # region proportion
            # region value
            
            
            for region in nuts2_regions:
                idx_nuts2region = list(inst_cap_NUTS2[industry_cap]["NUTS2"]).index(region)
                region_proportion = inst_cap_NUTS2[industry_cap][industry_cap+" %"][idx_nuts2region]
                content_row = [region]
                for i in col[1:len(col)]:
                    content_row.append(energy_demand_sheet[i][idx_country_demand]*region_proportion)
                content.append(content_row)
            
        energy_demand_NUTS2 = pd.DataFrame(content, columns = col)
        energy_demand_NUTS2.to_excel(result_dem_NUTS2,sheet_name=industry, index=False, startrow=0)
        if temp == 0:
            overall_energy_demand_NUTS2 = energy_demand_NUTS2
        else:
            overall_energy_demand_NUTS2 = overall_energy_demand_NUTS2.set_index("NUTS2").add(energy_demand_NUTS2.set_index("NUTS2"), fill_value=0).reset_index()
        temp += 1
    
    rest_df = pd.read_excel(energy_demand, "rest")
    energy_demand_NUTS2 = redistribution_NUTS2(FORECAST_YEAR, rest_df, pop_prognosis, abb_table)
    energy_demand_NUTS2.to_excel(result_dem_NUTS2,sheet_name="rest", index=False, startrow=0)
    overall_energy_demand_NUTS2 = overall_energy_demand_NUTS2.set_index("NUTS2").add(energy_demand_NUTS2.set_index("NUTS2"), fill_value=0).reset_index() 

        
    return overall_energy_demand_NUTS2

#------------------------------------------------------------------------------
def redistribution_NUTS2_pop(IND_SUBECTORS, FORECAST_YEAR, result_dem, pop_prognosis, abb_table, result_dem_NUTS2):
    
    temp = 0
    for industry in IND_SUBECTORS+["rest"]:
        ind_df = pd.read_excel(result_dem, industry)
        energy_demand_NUTS2 = redistribution_NUTS2(FORECAST_YEAR, ind_df, pop_prognosis, abb_table)
        energy_demand_NUTS2.to_excel(result_dem_NUTS2,sheet_name=industry, index=False, startrow=0)
        
        if temp == 0:
            overall_energy_demand_NUTS2 = energy_demand_NUTS2
        else:
            overall_energy_demand_NUTS2 = overall_energy_demand_NUTS2.set_index("NUTS2").add(energy_demand_NUTS2.set_index("NUTS2"), fill_value=0).reset_index()
        temp += 1
        
    return overall_energy_demand_NUTS2    

#------------------------------------------------------------------------------
# !!Annahme: alle Länder in der Enery/Year haben schon die  Reihenfolge von CTRL.CONSIDERED_COUNTRIES!!
def energy_timeseries_calcul(CTRL, energy_demand_overall_df, ind_data, result_dem, result_dem_NUTS2, abb_table, pop_prognosis):
    if CTRL.ACTIVATE_TIMESERIES:
        # calculation of electricity timeseries: start
        
        ## definition of column names
        if CTRL.NUTS2_ACTIVATED:
            year_dem_sheet = pd.read_excel(result_dem_NUTS2, "IND")
            regions = year_dem_sheet["NUTS2"]
        else:
            regions = CTRL.CONSIDERED_COUNTRIES
            year_dem_sheet = energy_demand_overall_df
            
        ## definition of column content
        content = []
        for idx_time, time in enumerate(ind_data.load_profile["t"]):
            row = [time]
            for idx_region, country in enumerate(regions):
                row.append(year_dem_sheet["Electricity [TWh]"][idx_region] * ind_data.load_profile["Electricity"][idx_time])
            content.append(row)       
        
        elec_timeseries_col = ["t"]; heat_h2_timeseries_col = ["t"]
        for region in regions:
            elec_timeseries_col.append(region+ ".Elec")
        print("Calculated electricity load timeseries. Df is beeing made.")
        elec_timeseries = pd.DataFrame(content, columns = elec_timeseries_col)
        # calculation of electricity timeseries: end
        
        
        # calculation of heat and hydrogen timeseries: start
        print("Calculation of heat and hydrogen load timeseries.")
        ## definition of column names
        heat_h2_col= [];
        considered_countries_code = [abb_table["Abbreviation"][list(abb_table["Country"]).index(region)] for region in  CTRL.CONSIDERED_COUNTRIES]
        if CTRL.NUTS2_ACTIVATED:
            region_type = "NUTS2"
            for region in pop_prognosis["NUTS2"]: ## NUR WENN NUTS2 aus countries die considered sind!
                if region[0:2] in considered_countries_code:
                    for short_type in ["Heat_Q1", "Heat_Q2", "Heat_Q3", "Heat_Q4", "H2"]:
                        heat_h2_col.append(region+"."+short_type)
        else:
            region_type = "Country"
            for region in CTRL.CONSIDERED_COUNTRIES:
                for short_type in ["Heat_Q1", "Heat_Q2", "Heat_Q3", "Heat_Q4", "H2"]:
                    heat_h2_col.append(region+"."+short_type)
       
        ## definition of column content: 
        ## There will be one matrix layer per each industry-subsector with demand time-series of all observed regions.
        ## Matrix layers per industry-subsector will be added.
        ## Thus a matrix layer with demand time-series of all observed regions with sumarized industrial demands will be obtained.
 
        for counter, industry in enumerate((CTRL.IND_SUBECTORS+["rest"])):
            matrix_ind = []
            industry_temp = industry.replace("_classic", "")
            if industry_temp in ["cement","glass"]:
                ind_group = "non_metalic_minerals"
            elif industry_temp == "paper":
                ind_group = industry
            elif industry_temp in ["chlorin", "methanol", "ethylene","propylene","aromatics", "ammonia"]:
                ind_group = "chemicals_and_petrochemicals"
            # elif industry_temp in CTRL.IND_FOOD:
            #     ind_group = "food_and_tobacco"
            else: # steel, alu, copper
                ind_group = "iron_and_steel"
            heat_load_profiles = getattr(ind_data, "heat_load_profile_"+ind_group)
            
            if CTRL.NUTS2_ACTIVATED:
                year_dem_sheet = pd.read_excel(result_dem_NUTS2, industry)
                
                for region in pop_prognosis["NUTS2"]: #in enumerate(year_dem_sheet[region_type]): #NUTS2 
                    country_code = region[0:2]
                    idx_dem = list(year_dem_sheet["NUTS2"]).index(region)
                    if country_code in ["CH", "IS","AL", "BA"]: # no time series for this countries
                        #print(f"No information for timeseries for {country_code}. Some approximations made")
                        if country_code in ["CH", "IS"] :
                            country_code_profile = "AT";
                        else:
                            country_code_profile = "MK";
                    else:
                        country_code_profile = country_code

                    try:
                        idx_profile = list(heat_load_profiles["NUTS0_code"]).index(country_code_profile)
                    except:
                        print("NO LOAD PROFILE for {}. Default is German profile.". format(country))
                        idx_profile = list(heat_load_profiles["NUTS0_code"]).index("DE")
                    heat_load_profile_country = heat_load_profiles["load"][idx_profile:(idx_profile+8760)]
                    
                    for dem_type, short_type in zip(["Heat Q1 [TWh]", "Heat Q2 [TWh]", "Heat Q3 [TWh]", "Heat Q4 [TWh]", "Hydrogen [TWh]"],
                                                    ["Heat_Q1", "Heat_Q2", "Heat_Q3", "Heat_Q4", "H2"]):
                        # same profile for all subcategories
                        if pd.isna(year_dem_sheet[dem_type][idx_dem]) == False:
                            col_body = pd.concat([pd.Series(0, [0]), heat_load_profile_country.iloc[:]])
                            col_body = col_body * year_dem_sheet[dem_type][idx_dem] /1000000
                        else:
                            col_body = pd.concat([pd.Series(0, [0]), heat_load_profile_country.iloc[:]]) * 0
                        matrix_ind.append(col_body)
                        #print(matrix_ind)
            else:
                year_dem_sheet = pd.read_excel(result_dem, industry)
                for region in CTRL.CONSIDERED_COUNTRIES: # Country
                    country_code = abb_table["Abbreviation"][list(abb_table["Country"]).index(region)]
                    idx_dem = list(year_dem_sheet["Country"]).index(region)
                    if country_code in ["CH", "IS","AL", "BA"]: # no time series for this countries
                        #print(f"No information for timeseries for {country_code}. Some approximations made")
                        if country_code in ["CH", "IS"] :
                            country_code_profile = "AT";
                        else:
                            country_code_profile = "MK";
                    else:
                        country_code_profile = country_code
                    idx_profile = list(heat_load_profiles["NUTS0_code"]).index(country_code_profile)
                    heat_load_profile_country = heat_load_profiles["load"][idx_profile:idx_profile+8760]
                    for dem_type, short_type in zip(["Heat Q1 [TWh]", "Heat Q2 [TWh]", "Heat Q3 [TWh]", "Heat Q4 [TWh]", "Hydrogen [TWh]"],
                                                    ["Heat_Q1", "Heat_Q2", "Heat_Q3", "Heat_Q4", "H2"]):
                        # same profile for all subcategories
                        if pd.isna(year_dem_sheet[dem_type][idx_dem]) == False:
                            col_body = pd.concat([pd.Series(0, [0]), heat_load_profile_country.iloc[:]])
                            col_body = col_body * year_dem_sheet[dem_type][idx_dem] /1000000
                        else:
                            col_body = pd.concat([pd.Series(0, [0]), heat_load_profile_country.iloc[:]]) * 0
                        matrix_ind.append(col_body)
            if counter == 0:
                matrix = np.array(matrix_ind.copy())#np.zeros((8760, 4))
            else:
                matrix += np.array(matrix_ind)
                    
    else:
        content = []; elec_timeseries_col = ["t"]
        matrix = []; heat_h2_col = []
        print("Calculation of load timeseries deactivated.")

    elec_timeseries = pd.DataFrame(content, columns = elec_timeseries_col)
    heat_h2_timeseries = pd.DataFrame(matrix).transpose()
    heat_h2_timeseries.columns = heat_h2_col
    #heat_h2_timeseries = heat_h2_timeseries.assign(t=pd.Series([i for i in range(0,8760)]))
    timeseries = pd.concat([elec_timeseries, heat_h2_timeseries], axis=1)
    return timeseries # elec_timeseries, heat_h2_timeseries 

#------------------------------------------------------------------------------ 
