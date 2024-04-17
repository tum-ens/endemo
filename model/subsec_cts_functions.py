###############################################################################                                                                                   
# Functions for CTS sector calculations
###############################################################################
# import libraries
from libraries import *
###############################################################################
#functions
###############################################################################
def corr_data_per_land(CTRL, country, idx_subsector, employee_per_sector, pop_table):

    x=list(range(int(employee_per_sector.columns[4]),CTRL.CTS_END_YEAR))

    x.insert(0, "Country")
    idx_pop = list(pop_table["Country"]).index(country)

    y=[country + "_"+ employee_per_sector["Subsector"][idx_subsector]]
    for year in x[1:]:
        # employee in percent of overall population
        # employee in tsd person whereas pop in 1 person
        y.append(employee_per_sector[str(year)][idx_subsector]*1000/pop_table[str(year)][idx_pop]*100) # in %
              
    return pd.DataFrame([y], columns=x)  

#------------------------------------------------------------------------------
def cts_plot_his_employee_data_timeline(CTRL, country, employee_per_pop_per_land):
    
    figure4=plt.figure()
    
    # x=list(range(int(employee_per_sector.columns[4]),CTRL.CTS_END_YEAR))

    # if CTRL.NUTS2_ACTIVATED == True
    #     x.insert(0, "NUTS2")
    #     #idx_pop = list(pop_table["Code"]).index(country)
    #     idx_pop = list(pop_table["Code"]).index(country)
    # else:
    #     x.insert(0, "Country")
    #     idx_pop = list(pop_table["Country"]).index(country)
        
    # # product_per_person is product in Tonnes per person
    # y=[country]
    # for year in x[1:]:
    #     # employee in percent of overall population
    #     # employee in tsd person whereas pop in 1 person
    #     y.append(employee_per_sector[year][idx_subsector]*1000/pop_table[str(year)][idx_pop]*100) # in %
    x = employee_per_pop_per_land.columns[4:]
    y = employee_per_pop_per_land.iloc[0][4:].values.tolist()
    plt.plot(x[1:], y[1:]) 
    
    # Layout anpassen:
    ## Extract the sector name from the employee_per_pop_per_land["Country"] containing both country and the sector name
    plt.ylabel("Employees in sector "+ employee_per_pop_per_land["Country"][0].split("_")[1] + " in % of overall population")
    #plt.axis([1990,2050,0,200])
    try:
        plt.text(x[6], y[6], country)
    except:
        plt.text(x[len(x)-1], y[len(x)-1], country)   
    plt.xlabel("Years")
    plt.grid(True)
    #plt.show()
           
#------------------------------------------------------------------------------  
def plot_model_data_time(country, employee_per_pop_per_land, koef, FORECAST_YEAR):   
    
    x1 = list(range(employee_per_pop_per_land.columns[1],FORECAST_YEAR)) # list(range(int(corresponding_industry_table.columns[4]),FORECAST_YEAR))
    y1 = [koef[0] + koef[1] * i  for i in x1]
    #y1 =  koef[0] + koef[1]*x1 

    # Funktion plotten:
    #plt.plot(x1,y1,'--' )
    plt.plot(x1, y1,'--')
    try:
        plt.text(x1[6], y1[6], country)
    except:
        plt.text(x1[len(x1)-1], y1[len(x1)-1], country)
    plt.show()

#------------------------------------------------------------------------------  
def calc_employee_forecast(koef, FORECAST_YEAR, country, pop_prognosis, corr_table_per_land):  

    if any(koef) == np.nan:
        country_employee = np.nan
    else:
        idx_pop_prognosis = list(pop_prognosis["Country"]).index(country)
        
        # not less than 0% of population can work in CTS
        country_employee = max(0, koef[0]+koef[1]* FORECAST_YEAR)
        ## hard-coded: share of subsector employees cannot grow more than 15% comparing to 2018 
        #country_employee = min(country_employee, corr_table_per_land[int(2018)][0]*1.15 )
        # not more than 100% of population can work in CTS
        country_employee = min(country_employee,100)
        # prognosis of employee per population * prognosis of population
        country_employee = country_employee/100 * pop_prognosis[str(FORECAST_YEAR)][idx_pop_prognosis]
        
    return country_employee

#------------------------------------------------------------------------------
def spec_en_source_timelines (CTRL, FILE, endemand_book, employees_historical, efficiency_table, abb_table):
    
    cts_el=endemand_book["Elektrizitaet"] 
    start_y=max(int(cts_el.columns[1]), int(employees_historical.columns[2]))
    years=list(range(start_y, CTRL.CTS_END_YEAR))
    years.insert(0,"Country")
    spec_energy_el=[]
    spec_energy_heat=[]

    for country in CTRL.CONSIDERED_COUNTRIES:
        country_de = abb_table["Country_de"][list(abb_table["Country"]).index(country)]
        country_abb = abb_table["Abbreviation"][list(abb_table["Country"]).index(country)]
        try: 
            idx_energy=list(cts_el["GEO/TIME"]).index(country_de)
        except:
            idx_energy=-1
        spec_energy_el_line=[country]
        spec_energy_heat_line=[country]
        
        def_val=0
        try:
            idx_employee=list(employees_historical["Country"]).index(country)
        except:
            idx_employee = -1
            
        if idx_energy!=-1:
            if idx_employee != -1:
                for year in years[1:]:
                    electricity=0
                    heat=0
                    # to obtain total number of employees in CTS
                    employee_val = 0
                    for subsector in range(1,8): # skip agriculture and add all other subsectors
                        employee_val += employees_historical[str(year)][idx_employee+subsector]
                    for idx_carrier, carrier in enumerate(efficiency_table["Energy carrier"]):
                        # skip nan values
                        if carrier in endemand_book:
                            electricity+=endemand_book[carrier][str(year)][idx_energy]*efficiency_table["Electricity production [-]"][idx_carrier] # in GWh
                            heat+=endemand_book[carrier][str(year)][idx_energy]*efficiency_table["Heat production [-]"][idx_carrier] # in GWh
                    if employee_val>0: 
                        spec_energy_el_line.append(electricity/employee_val) # in GWh/ tsd. employee
                        spec_energy_heat_line.append(heat/employee_val) # in GWh/tsd.employee
                    else:
                        spec_energy_el_line.append(np.nan)
                        spec_energy_heat_line.append(np.nan)
            else:
                print(country, " has no number known of emloyees in commertial, trade an services. No specific energy can be determined")
                for year in years[1:]:
                    spec_energy_el_line.append(np.nan)
                    spec_energy_heat_line.append(np.nan)
        else:
            print(country, " had no data about energy consumption of commertioal, trande and services. Default value", def_val ," taken.")
            for year in years[1:]:
                spec_energy_el_line.append(def_val)
                spec_energy_heat_line.append(def_val)
                
        spec_energy_el.append(spec_energy_el_line)
        spec_energy_heat.append(spec_energy_heat_line)   
      
    cts_el=pd.DataFrame(spec_energy_el, columns=years)
    cts_fuel=pd.DataFrame(spec_energy_heat, columns=years)
    
    return cts_el, cts_fuel

#------------------------------------------------------------------------------
def mean_timeline_val(cts_el):
    content = []
    for country in cts_el["Country"]:
        idx_country =  list(cts_el["Country"]).index(country)
        country_values = []
        for year in cts_el.columns[1:]:
            country_values.append(cts_el[year][idx_country])
        content.append([country, np.nanmean(country_values)])
        
    mean_timeline_val_df = pd.DataFrame(content, columns = ["Country", "Mean specific demand [GWh/tsd. employees]"])
    return mean_timeline_val_df        

#------------------------------------------------------------------------------
def energy_calcul(CTRL, employee_table, spec_energy_el, spec_energy_heat, pop_prognosis, abbreviations, FORECAST_YEAR, efficiency_heat_levels):
    energy_col=["Country", "Electricity [TWh]", "Heat [TWh]", "Hydrogen [TWh]", "Heat Q1 [TWh]", "Heat Q2 [TWh]"]
    energy_body = []

    for country in CTRL.CONSIDERED_COUNTRIES:
        idx_spec_energy = list(spec_energy_el["Country"]).index(country)
        abb = abbreviations["Abbreviation"][list(abbreviations["Country"]).index(country)]
        idx_employee = list(employee_table["Country"]).index(country)

        if CTRL.CTS_CALC_SPEC_EN_TREND == False:
            if math.isnan(spec_energy_el["Mean specific demand [GWh/tsd. employees]"][idx_spec_energy]):
                energy_el = np.nan
                energy_heat = np.nan
            else:
                energy_el = (employee_table["Employee total"][idx_employee]/1000
                                 * spec_energy_el["Mean specific demand [GWh/tsd. employees]"][idx_spec_energy]/1000) # employees/1000 * GWh/tsd. employees *  -> TWh
                energy_heat = (employee_table["Employee total"][idx_employee]/1000 
                                   * spec_energy_heat["Mean specific demand [GWh/tsd. employees]"][idx_spec_energy]/1000) # employees/1000 * GWh/tsd. employees *  -> TWh
        else:
            if math.isnan(spec_energy_el["koef_0"][idx_spec_energy]):
                energy_el = np.nan
                energy_heat = np.nan
            else:
                energy_el = (employee_table["Employee total"][idx_employee]/1000 
                                 * max(0,(spec_energy_el["koef_0"][idx_spec_energy]+spec_energy_el["koef_1"][idx_spec_energy]*CTRL.FORECAST_YEAR))/1000) # employees/1000 * GWh/tsd. employees *  -> TWh
                energy_heat = (employee_table["Employee total"][idx_employee] 
                                   * max(0,(spec_energy_heat["koef_0"][idx_spec_energy]+spec_energy_heat["koef_1"][idx_spec_energy]*CTRL.FORECAST_YEAR))/1000) # employees/1000 * GWh/tsd. employees *  -> TWh
                
        idx_level = list(efficiency_heat_levels["Energy carrier"]).index("Q1")
        elec_from_heat = (energy_heat * CTRL.CTS_ELEC_SUBSTITUTION_OF_HEAT
                          / efficiency_heat_levels["Electricity [-]"][idx_level])
        h2_from_heat = (energy_heat * CTRL.CTS_H2_SUBSTITUTION_OF_HEAT
                        / efficiency_heat_levels["Hydrogen [-]"][idx_level])
        energy_heat_remaining = (energy_heat * (1- CTRL.CTS_ELEC_SUBSTITUTION_OF_HEAT - CTRL.CTS_H2_SUBSTITUTION_OF_HEAT)
                                    / efficiency_heat_levels["Fuel [-]"][idx_level]) # for "heat" no efficincy conversion, for "fuel" *1/efficincy
                
        energy_body.append([country,energy_el+elec_from_heat,energy_heat_remaining,
                            h2_from_heat, energy_heat_remaining * CTRL.CTS_HEAT_Q1, energy_heat_remaining * CTRL.CTS_HEAT_Q2])
    energy_df = pd.DataFrame(energy_body, columns = energy_col)
    return energy_df

#------------------------------------------------------------------------------
def redistribution_NUTS2_empl(CONSIDERED_COUNTRIES, employee_df, empl_NUTS2_distrib_xlsx, abbreviations, pop_prognosis):
    
    subsectors = ["Wholesale and retail trade","Hotels and restaurants",
                  "Private offices",
                  "Public offices","Education","Health and social", 
                  "Other"] # "Agriculture and fishing",
    assigned_sheets = ["Wholesale-Hotels","Wholesale-Hotels",
                    "Private_offices",
                    "Public_offices-Education-Health","Public_offices-Education-Health","Public_offices-Education-Health",
                    "Other"] #"Agriculture",
    
    # Write as a first columns all NUTS2 region names
    all_regions = []
    for country in CONSIDERED_COUNTRIES:
        abb = abbreviations["Abbreviation"][list(abbreviations["Country"]).index(country)]
        for region in pop_prognosis["NUTS2"]:
            if region[0:2] == abb:
               all_regions.append(region) 
            
    df_NUTS2 = pd.DataFrame(all_regions, columns = ["NUTS2"])
    
    # Make a distribution for each subsector on NUTS2 level
    for subsector, sheet in zip(subsectors, assigned_sheets):
        empl_NUTS2_distrib_table = empl_NUTS2_distrib_xlsx[sheet]
        subsector_values = []
        
        for country in CONSIDERED_COUNTRIES:
            idx_empl = list(employee_df["Country"]).index(country)
            abb = abbreviations["Abbreviation"][list(abbreviations["Country"]).index(country)]
            regions = [i for i in pop_prognosis["NUTS2"] if i[0:2] == abb]
                
            for region in regions:
               
                idx_nuts2region = list(empl_NUTS2_distrib_table["NUTS2"]).index(region)
                region_proportion = empl_NUTS2_distrib_table["%"][idx_nuts2region]/100

                subsector_values.append(employee_df[subsector][idx_empl]*region_proportion)
                
        df_NUTS2[subsector]=subsector_values
    
    # Add all subsectors to a total value
    df_NUTS2["Employee total"] = df_NUTS2.iloc[:,1:].sum(axis=1) # sum whole columns except the first one (with NUTS2 names)
        
    return df_NUTS2

#------------------------------------------------------------------------------
def redistribution_NUTS2_energy(CONSIDERED_COUNTRIES, energy_df, employee_NUTS2_df, abb_table, pop_prognosis):
    
    col = energy_df.columns[1:] # skip the column with country names
    col = col.insert(0, "NUTS2")
    content = []
    
    for country in CONSIDERED_COUNTRIES:
        abb = abb_table["Abbreviation"][list(abb_table["Country"]).index(country)]
        regions = [i for i in pop_prognosis["NUTS2"] if i[0:2] == abb]
        idx_country_energy = list(energy_df["Country"]).index(country)
        
        # Find total number of employees
        total_empl = 0
        for region in regions:
            
            idx_region_empl = list(employee_NUTS2_df["NUTS2"]).index(region)
            total_empl += employee_NUTS2_df["Employee total"][idx_region_empl]
        
        # Calculate proportion of employees of each of the region
        # Distribute energy per region: 
        # multiply this proportion of a region with the energy demand of the country
        for region in regions:
            idx_region_empl = list(employee_NUTS2_df["NUTS2"]).index(region)   
            proportion = employee_NUTS2_df["Employee total"][idx_region_empl]/total_empl
            
            content_row = [region]
            
            for column in col[1:]:
                content_row.append(energy_df[column][idx_country_energy]*proportion)
            
            content.append(content_row)
        
    energy_NUTS2_df = pd.DataFrame(content, columns = col)
        
    return energy_NUTS2_df
        
#------------------------------------------------------------------------------
# !!Assumption: all countries in Energy/Year have the same order as in CTRL.CONSIDERED_COUNTRIES!!
def energy_timeseries_calcul(CTRL, energy_df,energy_NUTS2, load_profile):
    if CTRL.ACTIVATE_TIMESERIES:
        
        if CTRL.NUTS2_ACTIVATED:
            year_dem_sheet = energy_NUTS2
            regions = year_dem_sheet["NUTS2"]
        else:
            regions = CTRL.CONSIDERED_COUNTRIES
            year_dem_sheet = energy_df

        content = []
        for idx_time, time in enumerate(load_profile["t"]):
            row = [time]
            for energy_type, energy_type_name, distribution in zip(["Elec", "Heat_Q1", "Heat_Q2", "H2"],
                                                                   ["Electricity [TWh]","Heat [TWh]", "Heat [TWh]", "Hydrogen [TWh]"],
                                                                   [1, CTRL.CTS_HEAT_Q1, CTRL.CTS_HEAT_Q2, 1]): #
                for idx_region, region in enumerate(regions):
                    row.append(year_dem_sheet[energy_type_name][idx_region] * distribution * load_profile[energy_type][idx_time])
            content.append(row)       
        
        energy_timeseries_col = ["t"]
        for energy_type in load_profile.columns[1:len(load_profile.columns)]:
            for region in regions:
                energy_timeseries_col.append(region+ "." + energy_type)
        print("Calculated timeseries. Df is making")
        
    else:
        content = []
        energy_timeseries_col = []
        print("Load timeseries are not made")
        
    energy_timeseries_df = pd.DataFrame(content, columns = energy_timeseries_col)
    return energy_timeseries_df