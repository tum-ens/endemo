###############################################################################                                                                                   
# Mathematical operations
###############################################################################
"""The module contains mathematical operators for solving the inter-sectoral 
   problems.

"""
###############################################################################
#Imports
###############################################################################
from libraries import *

def get_last_nonnan_value(data_table, country):
    
    idx_country = list(data_table["Country"]).index(country)
    counter = 0
    while math.isnan(data_table[data_table.columns[-1-counter]][idx_country]):
        counter += 1
    
    return data_table[data_table.columns[-1-counter]][idx_country]

#------------------------------------------------------------------------------
def linear_regression_gdp_lin(corr_industry_table, corr_gdp_table, country, skip_years):
    
    varx_total = corr_gdp_table.iloc[list(corr_gdp_table["Country"]).index(country)].values.tolist()
    varx = []; var_y = []
    idx_dismiss = [0]
    for idx, element in enumerate(varx_total[1:]):
        if element not in skip_years:
            varx.append(element)
        else:
            idx_dismiss.append(idx+1) # since first index was skipped because it was a "Country" and not a number
    vary_total = corr_industry_table.iloc[list(corr_industry_table["Country"]).index(country)].values.tolist()
    vary = [element for idx, element in enumerate(vary_total) if idx not in idx_dismiss]
    mask = (~np.isnan(varx) & ~np.isnan(vary)).tolist()
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress([elem_x for idx, elem_x in enumerate(varx) if mask[idx]], 
                                                                         [elem_y for idx, elem_y in enumerate(vary) if mask[idx]])

    return slope, intercept

#------------------------------------------------------------------------------

def linear_regression_single_country_time(CTRL, corr_industry_table, idx_country, sector): 

    N=1
    #t=end_year-start_year-len(CTRL.IND_SKIP_YEARS)
    skip_years = [year for year in getattr(CTRL, sector + "_SKIP_YEARS") if (year > corr_industry_table.columns[1] and year < getattr(CTRL, sector + "_END_YEAR"))]
    t= getattr(CTRL, sector + "_END_YEAR")-int(corr_industry_table.columns[1])-len(skip_years) #!!!!!
    
    time_table_col=[]
    time_table_col1=list(range(int(corr_industry_table.columns[1]),getattr(CTRL, sector + "_END_YEAR")))
    time_table_col.append(time_table_col1)
    time_table_colname=time_table_col1
    time_table=pd.DataFrame(time_table_col, columns=time_table_colname)
    
    e_1=0
    a_1=N*t # !!!!!!
    b_1=0
    ##c_1=0
    #d_1=N*(2019-start_year)*(2019-start_year+1)/2
    
    e_2=0
    b_2=0
    ##c_2=0
    #d_2=0
    
    e_3=0
    ##c_3=0
    #d_3=0
    
    t1=0
    for column in corr_industry_table:
        # skip columns with country names and comments as well as user-defined skip years 
        if type(column) == int and column not in skip_years and column < getattr(CTRL, sector + "_END_YEAR"):
            if math.isnan(corr_industry_table[column][idx_country]) == False:
                t1+=1
                e_1+= corr_industry_table[column][idx_country]
                b_1+= float(time_table[column][0])
                ##c_1+= float(corresponding_gdp_table[column][i])**2
                b_2+= (float(time_table[column][0])**2)
                e_2+= corr_industry_table[column][idx_country] * time_table[column][0]
                ##c_2+= float(corresponding_gdp_table[column][i])**3
                #d_2+= corresponding_gdp_table[column][i]*temp
        
    a_1= N*t1 # !!!!   
    a_2=b_1

    equation=[[a_1,b_1], [a_2,b_2]]
    eq_right=[e_1, e_2]
        
    if t1>0:
        noData=False
    else:
        noData=True
    
    return equation, eq_right, noData

#------------------------------------------------------------------------------
# calculate modell parameter with delta for each land in y-axis, without time part
# not alle countries have the same number of information in time!
# changes are marked with #!
def calc_model_parameter_skipNaN_gdp(corresponding_gdp_table, IND_SKIP_YEARS, active_group, 
                                 corresponding_industry_table, IND_ACTIVATE_TIME_TREND_MODEL, delta_active):
    
    #t=end_year-start_year-len(IND_SKIP_YEARS)
    
    N=len(active_group)
    
    e_1=0
    a_1=0 #! N*t
    b_1=0
    c_1=0
    #d_1=0 #! N*(2019-start_year)*(2019-start_year+1)/2
    
    e_2=0
    c_2=0
    #d_2=0
    
    e_3=0
    c_3=0
    #d_3=0
    
    #e_4=0
    #! #a_4=d_1 
    #d_4=0
    
    if IND_ACTIVATE_TIME_TREND_MODEL:
        d_1=0
        d_2=0
        d_3=0
        e_4=0
        d_4=0       
    
    idx_group=[]
    for country in active_group:
        idx_group.append(list(corresponding_gdp_table["Country"]).index(country))
    
    temp=1
    for column in corresponding_gdp_table:
        # skip columns with country names and comments as well as user-defined skip years 
        if type(column) == int and column not in IND_SKIP_YEARS:
            for i in idx_group:
                if math.isnan(corresponding_gdp_table[column][i])== False and math.isnan(corresponding_industry_table[column][i])== False:
                    e_1+= corresponding_industry_table[(column)][i]
                    a_1+=1 #
                    b_1+= float(corresponding_gdp_table[column][i])
                    c_1+= float(corresponding_gdp_table[column][i])**2
                    #d_1+= temp
                    e_2+= corresponding_industry_table[(column)][i] * corresponding_gdp_table[column][i]
                    c_2+= float(corresponding_gdp_table[column][i])**3
                    #d_2+= corresponding_gdp_table[column][i]*temp
                    e_3+= corresponding_industry_table[(column)][i] * (corresponding_gdp_table[column][i])**2
                    c_3+= float(corresponding_gdp_table[column][i])**4
                    #d_3+= (corresponding_gdp_table[column][i])**2 *temp
                    #e_4+= product_pp_table_c[str(column)][i] * temp
                    #d_4+= temp**2
                    if IND_ACTIVATE_TIME_TREND_MODEL:
                        d_1+= temp
                        d_2+= corresponding_gdp_table[column][i]*temp
                        d_3+= (corresponding_gdp_table[column][i])**2 *temp
                        e_4+= product_pp_table_c[str(column)][i] * temp
                        d_4+= temp**2
        temp+=1
     
    a_2=b_1
    b_2=c_1
    
    a_3=c_1
    b_3=c_2
    
    if IND_ACTIVATE_TIME_TREND_MODEL:
        a_4=d_1 #!
        b_4=d_2
        c_4=d_3
 
        equation=[[a_1,b_1, c_1, d_1], [a_2,b_2, c_2, d_2], [a_3,b_3, c_3, d_3],[a_4,b_4, c_4, d_4]]
        eq_right=[e_1, e_2, e_3, e_4]
    else:
        equation=[[a_1,b_1, c_1], [a_2,b_2, c_2], [a_3,b_3, c_3]]
        eq_right=[e_1, e_2, e_3]
    
    
    if delta_active:
        counter=0
        for country_idx in idx_group:
            par_eq2=0
            par_eq3=0
            e_c=0
            
            counter_year=0
    
            if counter!=N-1:
                for column in corresponding_gdp_table:
                    # skip columns with country names and comments as well as user-defined skip years
                    if type(column) == int and column not in IND_SKIP_YEARS:
                        if (math.isnan(corresponding_gdp_table[column][country_idx])==False 
                            and math.isnan(corresponding_industry_table[column][country_idx])==False): 
                            counter_year+=1
                            par_eq2+=corresponding_gdp_table[column][country_idx]
                            par_eq3+=corresponding_gdp_table[column][country_idx]**2
                            e_c +=corresponding_industry_table[(column)][country_idx]
                    
                equation[0].append(counter_year)
                equation[1].append(par_eq2)
                equation[2].append(par_eq3)
                if IND_ACTIVATE_TIME_TREND_MODEL:
                    equation[3].append(t*(t+1)/2)
                eq_right.append(e_c)
                eq_sub_country=[counter_year, par_eq2, par_eq3]
    
    
                counter2=0
                for c in idx_group:
                    if counter2<N-1:
                        if c==country_idx:
                            eq_sub_country.append(counter_year)
                        else:
                            eq_sub_country.append(0)
                    counter2+=1
                    
                equation.append(eq_sub_country)
            counter+=1
        
    return equation, eq_right

#------------------------------------------------------------------------------
  
def calc_koef(equation, eq_right):
    koef = np.linalg.solve(equation, eq_right)   
    return koef
#------------------------------------------------------------------------------
def save_koef_lin(country, koef):   
    coeff_row = koef.insert(0, country)
    return coeff_row 

#------------------------------------------------------------------------------
def foothold_year_forecast(FORECAST_YEAR, country, value_table, foothold_years):
    
    idx_country = list(value_table["Country"]).index(country)
    
    foothold_years = [2018] + foothold_years

    if FORECAST_YEAR < 2018 or FORECAST_YEAR > foothold_years[-1]:
        print("The forcasted year has to be in range from 2018 to 2050!")
    
    elif FORECAST_YEAR in foothold_years:
        value_forecast_year = value_table[FORECAST_YEAR][idx_country]
    
    else:
        # find the two foothold years between which is the forecasted year 
        for idx_year, fh_year in enumerate(foothold_years[:-1]):
            next_fh_year = foothold_years[idx_year + 1]
            if FORECAST_YEAR < next_fh_year:
                # calculate the change between the two foothold years
                # to avoid dividaton with zero taking max of 0 and last foothold value from the table
                trend = (((value_table[next_fh_year][idx_country]/max(0.01, value_table[fh_year][idx_country]))**(1/(next_fh_year-fh_year)))-1)*100 # %
                value_forecast_year = value_table[fh_year][idx_country]*(1+(trend/100))**(FORECAST_YEAR-fh_year) # % 
                if math.isnan(value_forecast_year):
                    value_forecast_year = 0
                break
       
    
    return value_forecast_year
#------------------------------------------------------------------------------
def interpolate(data_table, FORECAST_YEAR, idx_table):
    for idx_col, column_name in enumerate(data_table.columns):
        try:
            int(column_name)
        except:
            continue
        if int(column_name) >= FORECAST_YEAR:
            x = [int(data_table.columns[idx_col-1]), int(column_name)]
            break
    try:
        y = [data_table[x_elem][idx_table] for x_elem in x]
    except:
        y = [data_table[str(x_elem)][idx_table] for x_elem in x]    
    x_new = FORECAST_YEAR
    y_new = np.interp(x_new, x, y)
    
    return y_new
    
##############################################################################  

def redistribution_NUTS2(FORECAST_YEAR, energy_demand, pop_prognosis, abb_table):
    col = ["NUTS2"]
    for i in energy_demand.columns[1:len(energy_demand.columns)]:
        col.append(i)
    content = []
    
    idx_demand = 0
    for country in energy_demand["Country"]:
        abb = abb_table["Abbreviation"][list(abb_table["Country"]).index(country)]
        #import pdb; pdb.set_trace()
        pop_country = pop_prognosis["Population_Countries"][str(FORECAST_YEAR)][list(pop_prognosis["Population_Countries"]["Country"]).index(country)]
        idx_nuts2_regions = [i for i, x in enumerate(pop_prognosis["Population_NUTS2"]["NUTS2"]) if x[0:2] == abb]
        for idx_nuts2region in idx_nuts2_regions:
            proportion = pop_prognosis["Population_NUTS2"][str(FORECAST_YEAR)][idx_nuts2region]/pop_country
            nuts2region = pop_prognosis["Population_NUTS2"]["NUTS2"][idx_nuts2region]
            content_row = [nuts2region]
            for i in col[1:len(col)]:
                content_row.append(energy_demand[i][idx_demand]*proportion)
            content.append(content_row)
        idx_demand+= 1
        
    energy_demand_NUTS2 = pd.DataFrame(content, columns = col)
        
    return energy_demand_NUTS2

#------------------------------------------------------------------------------

def add_timeseries(FILE, path_timeseries, CTS_ACTIVATED):

    # if CTS_ACTIVATED == True:
    
    overall_timeseries_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND'+path_timeseries),
                                sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"]  
    for sheet in ["HH", "TRA", "CTS"]:
        df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,sheet+path_timeseries),
                                sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"] 
        overall_timeseries_df = overall_timeseries_df.set_index("t").add(df_sector.set_index("t"), fill_value=0).reset_index() 
    
    result_total_timeseries = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Total'+path_timeseries), engine='xlsxwriter')
    overall_timeseries_df.to_excel(result_total_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
    result_total_timeseries.close()
    
    # else:

    #     overall_timeseries_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND'+path_timeseries),
    #                                 sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"]  
    #     for sheet in ["HH", "TRA"]:
    #         df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,sheet+path_timeseries),
    #                                 sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"] 
    #         overall_timeseries_df = overall_timeseries_df.set_index("t").add(df_sector.set_index("t"), fill_value=0).reset_index() 
        
    #     result_total_timeseries = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Total'+path_timeseries), engine='xlsxwriter')
    #     overall_timeseries_df.to_excel(result_total_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
    #     result_total_timeseries.close()
        


    
