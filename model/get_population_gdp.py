###############################################################################                                                                                   
# Forecast of population on NUTS2 level and GDP forecast
###############################################################################
"""The function predicts the population development for a desired year.
"""
###############################################################################
from libraries import *

logger = logging.getLogger(__name__)
level = logging.DEBUG
#level = logging.Warning
logging.basicConfig(level=level)


def load_population(CTRL, FILE, gen_data, result_name):
    
    space = "-"*79
    logger.info(space)
    logger.info("Run: " + __file__)
    
    result_population = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, result_name), engine='xlsxwriter')

    abbreviations = gen_data.abbreviations
    nuts_codes = gen_data.nuts_codes
    population_current = gen_data.pop_nuts2_table
    population_changeprojection = gen_data.population_changeprojection
    
    abb_list = []
    for country in CTRL.CONSIDERED_COUNTRIES:
        idx_abb = list(abbreviations["Country"]).index(country)
        abb_list.append(abbreviations["Abbreviation"][idx_abb])
    
    code_class = "Code " + CTRL.NUTS2_CLASSIFICATION
    country_code_list = [code for idx, code in enumerate(nuts_codes[code_class]) 
                         if ((code[0:2] in abb_list) and len(code) == 4 and (nuts_codes["Skip region"][idx] not in ["x"]))]
    
    
    # NUTS2 prognosis
    # taking last available population data as a starting point for the prognosis
    last_year = "2019"
    years_number = CTRL.FORECAST_YEAR - int(last_year)
    
    pop_nuts2_body = []
    for country_code in country_code_list:
        idx_pop_current_nuts2 = list(population_current["Code"]).index(country_code)
        population_last_year = population_current[last_year][idx_pop_current_nuts2]
        
        idx_pop_projection_nuts2 = list(population_changeprojection["Code"]).index(country_code)
        pop_yearly_change = float(population_changeprojection["per year"][idx_pop_projection_nuts2])
        
        #population in calculated year
        population_forecast = population_last_year * ((1 + pop_yearly_change/100)**years_number)
        pop_nuts2_body.append([country_code, population_forecast])
    population_forecast_nuts2 = pd.DataFrame(pop_nuts2_body, columns = ["NUTS2", str(CTRL.FORECAST_YEAR) + " before scaling"])
             
    
    # Country prognosis
    # population per country = sum of the forecasted Nuts2 population data 
    # and then scaled to correspond to UN population projection per country
    pop_country_body = []
    for abb in abb_list:
        pop_country = population_forecast_nuts2[population_forecast_nuts2["NUTS2"].str.startswith(abb)].sum()
        
        idx_country = list(abbreviations["Abbreviation"]).index(abb)
        country = abbreviations["Country"][idx_country]
        
        idx_pop_projection_country = list(gen_data.pop_forecast_country["Country"]).index(country)
        scaling_factor = (gen_data.pop_forecast_country[str(CTRL.FORECAST_YEAR)][idx_pop_projection_country]
                          / pop_country[str(CTRL.FORECAST_YEAR) + " before scaling"])
        
        pop_country_body.append([country, abb, pop_country[str(CTRL.FORECAST_YEAR) + " before scaling"], scaling_factor,
                                 gen_data.pop_forecast_country[str(CTRL.FORECAST_YEAR)][idx_pop_projection_country]])
    
    population_forecast_country = pd.DataFrame(pop_country_body, columns = ["Country", "Code", str(CTRL.FORECAST_YEAR)+ " before scaling", "Scaling factor", str(CTRL.FORECAST_YEAR)])
    
    # NUTS2 prognosis: scaling
    pop_nuts2_body = []
    for idx_nuts2, pop_forecast_nuts2 in enumerate(population_forecast_nuts2[str(CTRL.FORECAST_YEAR) + " before scaling"]):
        country_code = population_forecast_nuts2["NUTS2"][idx_nuts2]
        idx_scaling = list(population_forecast_country["Code"]).index(country_code[0:2])
        scaling_factor = population_forecast_country["Scaling factor"][idx_scaling]
        population_forecast_scaled = pop_forecast_nuts2 * scaling_factor
        pop_nuts2_body.append([country_code, population_forecast_scaled])
    population_forecast_nuts2_scaled = pd.DataFrame(pop_nuts2_body, columns = ["NUTS2", str(CTRL.FORECAST_YEAR)])
    
    population_forecast_nuts2 = population_forecast_nuts2.merge(population_forecast_nuts2_scaled)
     
    
    population_forecast_nuts2.to_excel(result_population, sheet_name="Population_NUTS2", index=False, startrow=0)
    population_forecast_country.to_excel(result_population, sheet_name="Population_Countries", index=False, startrow=0)
    result_population.close()
    print("Population data saved")
    
#------------------------------------------------------------------------------
# Calculating GDP forecast for the forecasted year 
def gdp_prognosis(CTRL, FILE, gen_data, result_name):
    
    result = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, result_name), engine='xlsxwriter')
    end_gdp_year = 2020 #end_gdp_year=gen_data.gdp_table.columns[len(gen_data.gdp_table.columns)-3]
      
    if CTRL.FORECAST_YEAR>2050:
        print("please enter CTRL.FORECAST_YEAR:  "+str(CTRL.REF_YEAR)+" <= CTRL.FORECAST_YEAR <= 2050")
    elif CTRL.FORECAST_YEAR==2050:
        h1=0; h2=10; h3=10; h4=10
    elif CTRL.FORECAST_YEAR>=2040:
        h1=0; h2=10; h3=10
        h4=CTRL.FORECAST_YEAR % 10
    elif CTRL.FORECAST_YEAR>=2030:
        h1=0; h2=10;
        h3=CTRL.FORECAST_YEAR % 10
        h4=0
    elif CTRL.FORECAST_YEAR>=2020:
        h1=0; h2=CTRL.FORECAST_YEAR % 10
        h3=0; h4=0
    elif CTRL.FORECAST_YEAR>=CTRL.REF_YEAR:
        h1 = CTRL.FORECAST_YEAR - CTRL.REF_YEAR; 
        h2=0; h3=0; h4=0
        end_gdp_year = CTRL.REF_YEAR
    else:
        print("please enter CTRL.FORECAST_YEAR: "+str("+str(CTRL.REF_YEAR)+")+ "<= CTRL.FORECAST_YEAR <= 2050")
        
    col_content = []
    for country in CTRL.CONSIDERED_COUNTRIES:
        # Find country's last available GDP data
        # If in the last 50 years there are no GDP data, skip this country
        idx_last_gdp=list(gen_data.gdp_table["Country"]).index(country)
        counter = 0;
        while (math.isnan(gen_data.gdp_table[end_gdp_year-counter][idx_last_gdp]) and counter<=50):
            counter += 1; 
        if counter<50:
            GDP_current = gen_data.gdp_table[end_gdp_year-counter][idx_last_gdp]
        else:
            GDP_current = np.nan; print("For {} there was no GDP data.". format(country))
        
        # Find the country's GDP forecast
        # If it is not explizitely given, take the default value marked under "all"
        try:
            idx_progn_gdp= list(gen_data.gdp_changeprojection["Country"]).index(country)
        except:
            idx_progn_gdp= list(gen_data.gdp_changeprojection["Country"]).index("all")
        
        # Calculation of the GDP in future
        ## In the case that there is a last GDP value older then end_gdp_year, it is assumed, that GDP change from 2021-2030 applies.
        GDP_forecast = (GDP_current
               *(1+gen_data.gdp_changeprojection["2020-2030"][idx_progn_gdp]/100)**(h1+h2+counter)
               *(1+gen_data.gdp_changeprojection["2030-2040"][idx_progn_gdp]/100)**h3
               *(1+gen_data.gdp_changeprojection["2040-2050"][idx_progn_gdp]/100)**h4
               )
            
        col_content.append([country, GDP_forecast])
    print("GDP prognosis per person for ",CTRL.FORECAST_YEAR, " has been calculated." )
    
    GDP_prognosis_df = pd.DataFrame(col_content, columns=["Country", "GDP"])
    GDP_prognosis_df.to_excel(result, sheet_name="Data", index=False, startrow=0)
    result.close()
    
    return GDP_prognosis_df
   
