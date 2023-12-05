###############################################################################                                                                                   
# Chair:            Chair of Renewable and Sustainable Energy Systems (ENS)
# Assistant(s):     Andjelka Kerekes (andelka.kerekes@tum.de)/ 
#                   Larissa Breuning (larissa.breuning@tum.de)

# Date:             
# Version:          v3.0
# Status:           done
# Python-Version:   3.7.3 (64-bit)
###############################################################################
"""This module makes a prognosis about the product demand in Europe, per NUTS0
 level. Calculates energy demand for each product in industry as a 
multiplication of product demand with specific energy demand for its production.

Comments:
    Luxembourg
"""
###############################################################################
from libraries import *
from subsec_ind_functions import *
#from subsec_ind_food import *
from op_methods import *
###############################################################################
def start_calc(CTRL, FILE, ind_data, gen_data):
    # Output data definition
    result_vol_koef = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY,FILE.FILENAME_OUTPUT_IND_VOLUME_KOEF), engine='xlsxwriter')
    result_vol = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,FILE.FILENAME_OUTPUT_IND_VOLUME_FORECAST), engine='xlsxwriter')
    result_dem_path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA,FILE.FILENAME_OUTPUT_DEMAND_IND)
    result_dem = pd.ExcelWriter(result_dem_path, engine='xlsxwriter')
    ## This file will be saved only if NUTS2 calculation is activated
    result_dem_NUTS2 = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,FILE.FILENAME_OUTPUT_DEMAND_IND_NUTS2), engine='xlsxwriter')

    # Reading abbreviation data
    abb_table= gen_data.abbreviations
    
    # specifying countries which are to be plotted
    plot_countries = []# ["Spain", "Italy"] # CTRL.CONSIDERED_COUNTRIES#
                #["Brunei Darussalam", "Indonesia", "Cambodia", "Lao PDR", "Malaysia", "Myanmar", "Philippines", "Singapore", "Thailand", "Vietnam"]
                #["Belgium", "Bulgaria", "Czechia", "Denmark", "Germany", 
                #"Ireland", "Greece", "Spain", "France", "Croatia", "Italy", 
                #"Latvia", "Luxembourg", "Hungary", "Netherlands", "Austria", 
                #"Poland", "Portugal", "Romania", "Slovenia", "Slovakia", 
                #"Finland", "Sweden", "United Kingdom", "Norway", "Switzerland",
                #"Montenegro", "North Macedonia", "Albania", "Serbia", 
                #"Bosnia and Herzegovina", "Iceland"]
    plot_industries = ["cement"] # ["alu_prim","cement", "steel_prim", "steel_sec", "copper_prim", "copper_sec", "paper"] #CTRL.IND_SUBECTORS
        
    # Calculating energy demand per industrial subsector
    for industry in CTRL.IND_SUBECTORS:
        #  Initialization: setting industry and grouping countries
        print("Calculation for ", industry)
        industry_table = assign_his_prod_quantity(CTRL, ind_data, industry)
        # optimise function ind_production_per_person
        product_pp_table = ind_production_per_person(FILE, industry, industry_table, gen_data.pop_table, abb_table,
                                                     CTRL.IND_END_YEAR, CTRL.CONSIDERED_COUNTRIES)
        corr_gdp_table, corr_industry_table = ind_corresponding_gdp_industry(CTRL, industry_table,product_pp_table, 
                                                                         gen_data.gdp_table, abb_table, industry)
        group=1; coeff_content=[]
        country_group_separate, country_group_zero, country_group = country_clustering(CTRL.IND_VOLUM_PROGNOS, industry, CTRL.CONSIDERED_COUNTRIES)   
        const_industries = ["ammonia","ethylene", "methanol", "propylene", "aromatics", 
                    "ammonia_classic","ethylene_classic", "methanol_classic", "propylene_classic", "aromatics_classic",
                    "alu_sec", "glass"]
        #######################################################################
        # Industrial production quantities
        #######################################################################    
        # Defining development of the product quantity:
        # choosing the form of the development as either a), b) or c):
        # a) quadratic function depending on GDP per person (qrouped countries or for each country separately)
        # b) linear time trend
        # c) exponential function (for const_industries)
        #######################################################################
        # Production quantity coeficients are to be determined
        col_names_coef = ["Country", "coeff_0", "coeff_1", "coeff_2", "coeff_c"]
        
        if industry not in const_industries:
            if CTRL.IND_VOLUM_PROGNOS == "Quadratic GDP function":
                # Calculate production quantity coefficients per country group
                for active_group in country_group: 
                    delta_active=True 
                    equation, eq_right= calc_model_parameter_skipNaN_gdp(corr_gdp_table,CTRL.IND_SKIP_YEARS,
                                                                     active_group, corr_industry_table,
                                                                     CTRL.IND_ACTIVATE_TIME_TREND_MODEL, delta_active)
                    koef=calc_koef(equation, eq_right)
                    coeff_content=save_koef(coeff_content, active_group, koef, CTRL.IND_ACTIVATE_TIME_TREND_MODEL, 
                                            delta_active)
                    idx_group=[list(corr_industry_table["Country"]).index(i) for i in active_group]
                    #ploting historical and modeled (forecasted) data    
                    if industry in plot_industries: #active_group == "test" and
                        ind_plot_his_production_data_GDP(CTRL, industry, active_group, corr_industry_table,
                                                         corr_gdp_table)
                        plot_model_data_GDP(FILE, CTRL.IND_ACTIVATE_TIME_TREND_MODEL, active_group, corr_gdp_table, koef, gen_data.GDP_prognosis, idx_group,
                                      delta_active, industry, group, FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL)
                    group+=1
            
                # Calculate production quantity coefficients per country
                for country in country_group_separate:
                    active_group=[country]; delta_active=False
                    equation, eq_right= calc_model_parameter_skipNaN_gdp(corr_gdp_table,CTRL.IND_SKIP_YEARS, 
                                                                     active_group, corr_industry_table,
                                                                     CTRL.IND_ACTIVATE_TIME_TREND_MODEL, delta_active)
                    koef=calc_koef(equation, eq_right)
                    coeff_content=save_koef(coeff_content, active_group, koef, CTRL.IND_ACTIVATE_TIME_TREND_MODEL, 
                                            delta_active)
                    idx_country=list(corr_industry_table["Country"]).index(country)
                    idx_group=[idx_country]
                    if country in plot_countries and industry in plot_industries:
                        ind_plot_his_production_data_GDP(CTRL, industry, active_group, corr_industry_table, 
                                                         corr_gdp_table)
                        plot_model_data_GDP(FILE, CTRL.IND_ACTIVATE_TIME_TREND_MODEL, active_group, corr_gdp_table, koef, gen_data.GDP_prognosis, idx_group,
                                            delta_active, industry, group, FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL)
                    group+=1
            
                # Setting production quantity coefficients to zero for countries
                # with clear trend to exit the industrial subsector production market
                for country in country_group_zero:
                    if CTRL.IND_ACTIVATE_TIME_TREND_MODEL:
                        coeff_content.append([country, 0,0,0,0,0])
                    else:
                        coeff_content.append([country, 0,0,0,0])
                        
                if CTRL.IND_ACTIVATE_TIME_TREND_MODEL:
                    col_names_coef.insert(-1, "coeff_time")
      
            
            elif CTRL.IND_VOLUM_PROGNOS == "Linear time trend": 
                # Calculate quantity parameters per land
                for country in country_group_separate:
                    idx_country=list(corr_industry_table["Country"]).index(country)
                    idx_group=[idx_country]
    
                    equation, eq_right, noData= linear_regression_single_country_time(CTRL, corr_industry_table, idx_country, "IND")       
                    if noData:
                        koef=[np.nan, np.nan]
                    else:
                        koef=calc_koef(equation, eq_right)
                    coeff_content.append([country]+koef.tolist()+[0,0])
                    if country in plot_countries and industry in plot_industries: # 
                        ind_plot_his_production_data_timeline(CTRL,industry, [country], corr_industry_table, "production")
                        plot_model_data_time(industry, country, corr_industry_table, koef, CTRL.FORECAST_YEAR, FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL)
                              
                
            elif CTRL.IND_VOLUM_PROGNOS == "Linear GDP function": 
                # Calculate quantity parameters per land
                for country in country_group_separate:
                    idx_group = [list(corr_industry_table["Country"]).index(country)]
                    slope, intercept = linear_regression_gdp_lin(corr_industry_table, corr_gdp_table, country, CTRL.IND_SKIP_YEARS)       
                    coeff_content.append([country, intercept, slope, 0, 0]) 
                    if country in plot_countries and industry in plot_industries: # 
                        ind_plot_his_production_data_GDP(CTRL, industry, [country], corr_industry_table,
                                                         corr_gdp_table)
                        plot_model_data_GDP(FILE, False, [country], corr_gdp_table, [intercept, slope, 0, 0], gen_data.GDP_prognosis, idx_group,
                                            False, industry, "", FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL)
                                    
        
        if industry in const_industries or CTRL.IND_VOLUM_PROGNOS == "Exponential":
            for country in CTRL.CONSIDERED_COUNTRIES:
                coeff_content.append([country, get_last_nonnan_value(corr_industry_table, country),0,0,0])
            
        coeff_vol_df = pd.DataFrame(coeff_content, columns = col_names_coef)         
        coeff_vol_df.to_excel(result_vol_koef, sheet_name=industry, index=False, startrow=0)
        
        #######################################################################
        # Specific energy consumption trend  
        #######################################################################
        if CTRL.IND_CALC_SPEC_EN_TREND and (industry in ["steel","paper"]):
            print("Entering spec energy part")
            # Output data definition
            result_spec_energy_koef = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY, "spec_energy_koef_" + industry + ".xlsx"), engine='xlsxwriter')

            coeff_content_el=[]; coeff_content_heat=[]
            industry_spec_el, industry_spec_heat= spec_en_source_timelines(CTRL, FILE, ind_data, industry, gen_data.efficiency_table, corr_industry_table, gen_data.pop_table, abb_table)
            
            # Calculate timeseries and their koeficients per land
            for country in CTRL.CONSIDERED_COUNTRIES:
                active_group=[country]; delta_active=False
                idx_country=list(corr_industry_table["Country"]).index(country)
                
                # Linear regression for electricity data
                equation, eq_right, noData = linear_regression_single_country_time(CTRL, industry_spec_el, idx_country, "IND")
                if noData == False:
                    koef=calc_koef(equation, eq_right)
                else:
                    print(country,"spec_energy_el", "noData = ", noData)
                    koef=[np.nan, np.nan]
                coeff_content_el=save_koef(coeff_content_el,  active_group, koef, CTRL.IND_ACTIVATE_TIME_TREND_MODEL, delta_active)
               
                ## Plot electricity data - historical and predicted values
                if country in plot_countries and industry in plot_industries:
                    ind_plot_his_production_data_timeline(CTRL,industry, active_group, industry_spec_el, "spec_energy_el")
                    plot_model_data_time(industry, country, industry_spec_el, koef, CTRL.FORECAST_YEAR, FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL)
                
                # Linear regression for heat data
                equation, eq_right, noData = linear_regression_single_country_time(CTRL, industry_spec_heat, idx_country, "IND")
                if noData == False:
                    koef=calc_koef(equation, eq_right)
                else:
                    print(country,"spec_energy_heat", "noData = ", noData)
                    koef=[np.nan, np.nan]
                coeff_content_heat=save_koef(coeff_content_heat,  active_group, koef, CTRL.IND_ACTIVATE_TIME_TREND_MODEL, delta_active)
                
                ## Plot heat data - historical and predicted values
                if country in plot_countries and industry in plot_industries: 
                    ind_plot_his_production_data_timeline(CTRL,industry, active_group, industry_spec_heat, "spec_energy_heat")
                    plot_model_data_time(industry, country, industry_spec_heat, koef, CTRL.FORECAST_YEAR, FILE.FILE_PATH_OUTPUT_DATA_INDUSTRY_GRAPHYCAL)

            
            coeff_el_df=pd.DataFrame(coeff_content_el, columns=["Country", "coeff_0", "coeff_1", "coeff_c"]) 
            coeff_heat_df=pd.DataFrame(coeff_content_heat, columns=["Country", "coeff_0", "coeff_1", "coeff_c"])    
            coeff_el_df.to_excel(result_spec_energy_koef, sheet_name='Electricity', index=False, startrow=0)
            coeff_heat_df.to_excel(result_spec_energy_koef, sheet_name='Heat', index=False, startrow=0)
            result_spec_energy_koef.close()
            spec_consum_const = False
        else:
            coeff_el_df = []; coeff_heat_df = []
            spec_consum_const = True
            industry_spec_el = industry_spec_heat = []
        
        #######################################################################
        # Energy consumption
        #######################################################################
        energy_col=["Country", "Electricity [TWh]", "Heat [TWh]", "Hydrogen [TWh]", "Heat Q1 [TWh]", "Heat Q2 [TWh]", "Heat Q3 [TWh]", "Heat Q4 [TWh]"]
        vol_col=["Country", "Amount [kt]"]           
        col_content_energy, col_content_volume = industry_en_demand(CTRL, ind_data, spec_consum_const, gen_data.efficiency_table, gen_data.efficiency_heat_levels,
                                                                    coeff_el_df, coeff_heat_df, abb_table,
                                                                    industry, coeff_vol_df, gen_data.pop_forecast["Population_Countries"], gen_data.GDP_prognosis, 
                                                                    gen_data.pop_table, const_industries,
                                                                    industry_spec_el, industry_spec_heat)
        energy_dem_df=pd.DataFrame(col_content_energy, columns=energy_col)
        energy_dem_df.to_excel(result_dem, sheet_name=industry, index=False, startrow=0)
        volume_dem_df=pd.DataFrame(col_content_volume, columns=vol_col)
        volume_dem_df.to_excel(result_vol, sheet_name=industry, index=False, startrow=0)
        
    ###########################################################################
    # Total industrial energy consumption
    ###########################################################################
    # Saving the data for separate subsectors 
    result_vol_koef.close()
    result_vol.close()
    result_dem.close()
    
    energy_demand_overall_df = overall_ind_demand(CTRL, result_dem, result_dem_path, ind_data.rest_table, ind_data.heat_levels, gen_data.efficiency_heat_levels)
    ###########################################################################
    if CTRL.NUTS2_ACTIVATED:
        if CTRL.IND_NUTS2_INST_CAP_ACTIVATED:
            overall_energy_demand_NUTS2 = redistribution_NUTS2_inst_cap(CTRL.IND_SUBECTORS, CTRL.FORECAST_YEAR, result_dem, gen_data.pop_forecast, ind_data.installed_capacity_NUTS2, abb_table, result_dem_NUTS2)
        else:
            overall_energy_demand_NUTS2 = redistribution_NUTS2_pop(CTRL.IND_SUBECTORS, CTRL.FORECAST_YEAR, result_dem, gen_data.pop_forecast, abb_table, result_dem_NUTS2)
        overall_energy_demand_NUTS2.to_excel(result_dem_NUTS2,sheet_name="IND", index=False, startrow=0)
        result_dem_NUTS2.close()
    ###########################################################################                        
    #if CTRL.IND_NUTS2_INST_CAP_ACTIVATED:
    timeseries = energy_timeseries_calcul(CTRL, energy_demand_overall_df, ind_data, result_dem, result_dem_NUTS2, abb_table, gen_data.pop_forecast["Population_NUTS2"])
    # elec_timeseries, heat_h2_timeseries =   
    # timeseries = []
    # else:
        #timeseries = energy_timeseries_calcul_old(CTRL, energy_demand_overall_df,result_dem_NUTS2, ind_data.load_profile)
        #elec_timeseries = []; heat_h2_timeseries = []
    
    sol = IND_SOL(energy_demand_overall_df, timeseries)
    return sol

class IND_SOL(): #(volume_koef, volume, energy_demand_overall, energy_timeseries):
    def __init__(self, energy_demand_overall_df, timeseries):
        self.energy_demand = energy_demand_overall_df
        self.timeseries = timeseries
        #self.elec_timeseries = elec_timeseries
        #self.heat_h2_timeseries = heat_h2_timeseries
