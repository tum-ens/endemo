###############################################################################                                                                                   
# Forecast of the commercial trade and services sector
###############################################################################
"""The module calculates the energy demand of the commercial trade and services
 sector.

The script calculates an energy demand development for the commercial trade 
and services sector based on user-specific inputs. A forecast should be made 
for the energy sources 
heat and electricity.
"""
###############################################################################
# Import libraries
###############################################################################
from libraries import *
from subsec_cts_functions import *
from op_methods import *
###############################################################################
def start_calc(CTRL, FILE, cts_data, gen_data):
    # Output data definition
    result_empl_coef = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_CTS,FILE.FILENAME_OUTPUT_CTS_EMPL_COEF), engine='xlsxwriter')
    result_spec_energy = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_CTS, "spec_energy.xlsx"), engine='xlsxwriter')
    ###########################################################################
    # Calculting trend of employees in cts
    ###########################################################################
    number_employee = []; country_employee = 0
    country_abb_to_plot = ["Germany"] #["DE","BG", "BE", "AL", "RS", "BA", "IS", "FI", "SW", "SK", "SE", "SL"]
    coeff_empl_content = []
    
    pop_prognosis=gen_data.pop_forecast["Population_Countries"]
    for country in CTRL.CONSIDERED_COUNTRIES:
        row = [country]
        coef_row = [country]
        country_abb = gen_data.abbreviations["Abbreviation"][list(gen_data.abbreviations["Country"]).index(country)]
        idx_country = list(cts_data.employee_NUTS0["Country"]).index(country)

        # for all subsectors (except agriculture)
        for idx_subsector, subsector in tuple(enumerate(cts_data.employee_NUTS0["Subsector"]))[1:8]:
            
            # Calculate employee in percent of overall population
            employee_per_pop_per_land = corr_data_per_land(CTRL, country, idx_country+idx_subsector, cts_data.employee_NUTS0, gen_data.pop_table)
            # Calculate the linear trend of employees as percent of overall population
            equation, eq_right, noData = linear_regression_single_country_time(CTRL, employee_per_pop_per_land, 0, "CTS")       
            if noData:
                koef=[np.nan, np.nan]
            else:
                koef=calc_koef(equation, eq_right)
            coef_row.append(koef[0]); coef_row.append(koef[1])
           
            if country_abb in country_abb_to_plot:
                cts_plot_his_employee_data_timeline(CTRL, country, employee_per_pop_per_land) #idx_country+idx_subsector, cts_data.employee_NUTS0
                plot_model_data_time(country, employee_per_pop_per_land, koef, CTRL.FORECAST_YEAR)
            
            row.append(calc_employee_forecast(koef, CTRL.FORECAST_YEAR, country, pop_prognosis, employee_per_pop_per_land))
        
        coeff_empl_content.append(coef_row)
        # total of all subsectoral employees
        row.append(sum(row[1:8])) # skip country name
        number_employee.append(row)
        
    column_names = [subsector for subsector in cts_data.employee_NUTS0["Subsector"][1:8]]
    column_names.insert(0,"Country"); column_names.append("Employee total")
    employee_df=pd.DataFrame(number_employee, columns = column_names)   
    
    # save coefficients of employees trends
    coef_col_names = ["Country"]
    for subsector in cts_data.employee_NUTS0["Subsector"][1:8]:
        coef_col_names.append("c0_"+subsector); coef_col_names.append("c1_"+subsector)
    coef_empl_df = pd.DataFrame(coeff_empl_content, columns = coef_col_names)
    coef_empl_df.to_excel(result_empl_coef, sheet_name="empl_coef", index=False, startrow=0)
    result_empl_coef.close()
    
    ###########################################################################
    # Calculting specific energy demand
    ###########################################################################
    cts_el, cts_heat = spec_en_source_timelines (CTRL, FILE, cts_data.endemand, cts_data.employee_NUTS0, gen_data.efficiency_table, gen_data.abbreviations)
    cts_el.to_excel(result_spec_energy, sheet_name="cts_el_timelines", index=False, startrow=0)
    cts_heat.to_excel(result_spec_energy, sheet_name="cts_heat_timelines", index=False, startrow=0)
    if CTRL.CTS_CALC_SPEC_EN_TREND == False:
        spec_energy_mean_el = mean_timeline_val(cts_el)
        spec_energy_mean_heat = mean_timeline_val(cts_heat)
        spec_energy_mean_el.to_excel(result_spec_energy, sheet_name="cts_el_mean", index=False, startrow=0)
        spec_energy_mean_heat.to_excel(result_spec_energy, sheet_name="cts_heat_mean", index=False, startrow=0)
    else:
        for demand_data in [cts_el, cts_heat]:
                
            coeff_content = []     
            for idx_country, country in enumerate(demand_data["Country"]):
                equation, eq_right, noData= linear_regression_single_country_time(CTRL, demand_data, idx_country, "CTS") 
                if noData:
                    koef=[np.nan, np.nan]
                else:
                    koef=calc_koef(equation, eq_right)
                coeff_content.append([country, koef[0],koef[1]])
            koef_df = pd.DataFrame(coeff_content, columns = ["Country", "koef_0", "koef_1"])
            koef_df.to_excel(result_spec_energy, sheet_name=i+"_koef", index=False, startrow=0)
    result_spec_energy.close()
    
    ###########################################################################
    # Calculting energy demand in CTS
    ###########################################################################
    if CTRL.CTS_CALC_SPEC_EN_TREND == False:
        energy_df = energy_calcul(CTRL, employee_df, spec_energy_mean_el, spec_energy_mean_heat, gen_data.pop_forecast["Population_Countries"],
                                  gen_data.abbreviations, CTRL.FORECAST_YEAR, gen_data.efficiency_heat_levels)
    else:
        spec_energy = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_CTS, "spec_energy.xlsx"),sheet_name=["el_koef", "heat_koef"],skiprows=0)
        energy_df = energy_calcul(CTRL, employee_df,spec_energy["el_koef"], spec_energy["heat_koef"], gen_data.pop_forecast["Population_Countries"], 
                                  gen_data.abbreviations, CTRL.FORECAST_YEAR, gen_data.efficiency_heat_levels)
   
    ###########################################################################
    # Distribution on NUTS2 and hourly profiles
    ###########################################################################
    if CTRL.NUTS2_ACTIVATED:
        if CTRL.CTS_NUTS2_PER_POP == False:
            employee_NUTS2_df = redistribution_NUTS2_empl(CTRL.CONSIDERED_COUNTRIES, employee_df, cts_data.employee_NUTS2_distrib, gen_data.abbreviations, gen_data.pop_forecast["Population_NUTS2"])
            energy_NUTS2 = redistribution_NUTS2_energy(CTRL.CONSIDERED_COUNTRIES, energy_df, employee_NUTS2_df, gen_data.abbreviations, gen_data.pop_forecast["Population_NUTS2"])
        else:
            employee_NUTS2_df = redistribution_NUTS2(CTRL.FORECAST_YEAR, employee_df, gen_data.pop_forecast, gen_data.abbreviations)
            energy_NUTS2 = redistribution_NUTS2(CTRL.FORECAST_YEAR, energy_df, gen_data.pop_forecast, gen_data.abbreviations)
    else:
        employee_NUTS2_df = pd.DataFrame(); energy_NUTS2 = pd.DataFrame()

    energy_timeseries_df = energy_timeseries_calcul(CTRL, energy_df,energy_NUTS2, cts_data.load_profile)

    sol = CTS_SOL(employee_df, employee_NUTS2_df, energy_df, energy_NUTS2, energy_timeseries_df)
    return sol


class CTS_SOL(): 
    def __init__(self, employee_df, employee_NUTS2_df, energy_df, energy_NUTS2, energy_timeseries_df):
        self.employee = employee_df
        self.employee_NUTS2 = employee_NUTS2_df
        self.energy_demand = energy_df
        self.cts_energy_demand_NUTS2 = energy_NUTS2
        self.energy_timeseries = energy_timeseries_df
