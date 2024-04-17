###############################################################################                                                                                   
# Output and postprocess of data
###############################################################################
"""The module outputs the result values of the model.

"""
###############################################################################
#Imports
###############################################################################
from libraries import *
from op_methods import *


# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def out_data(CTRL, FILE, ind_sol, hh_sol, cts_sol, tra_sol):
       
    #------------------------------------------------------------------------------
    # Industry.

    if CTRL.IND_ACTIVATED == True:
         # defining all outputs
        result_energy_timeseries = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND'+FILE.FILENAME_OUTPUT_TIMESERIES), engine='xlsxwriter')
        #if CTRL.IND_NUTS2_INST_CAP_ACTIVATED:
        #ind_sol.elec_timeseries.to_excel(result_energy_timeseries, sheet_name="Elec_timeseries", index=False, startrow=0)
        #ind_sol.heat_h2_timeseries.to_excel(result_energy_timeseries, sheet_name="Heat_H2_timeseries", index=False, startrow=0)
        #else:
        ind_sol.timeseries.to_excel(result_energy_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
        result_energy_timeseries.close()
 
    #------------------------------------------------------------------------------
    # Household.

    if CTRL.HH_ACTIVATED == True:

        # final HH output
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "HH"+FILE.FILENAME_OUTPUT_DEMAND)
        data = {'HH_demand': hh_sol.energy_demand_finalenergy}
        
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
        
        # additional HH outputs
        ## total demand and demand per subsector
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_HH_DEMAND_SUBSECTORS)
        data = {'Energy_PerSubsector': hh_sol.energy_demand_subsector, 
                'Energy_Useful_Total': hh_sol.energy_demand_usefulenergy}
  
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
        
        ## Characteristics of the households
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_HH_CHARACTERISTICS)
        data = {'Person per household': hh_sol.hh_data_forecast.person_per_hh_forecast, 
                'Area per household (m2)': hh_sol.hh_data_forecast.area_per_hh_forecast,
                'Living area total (Mil. m2)': hh_sol.hh_data_forecast.area_total_forecast,
                'Spec. sp. heating (kWh per m2)': hh_sol.hh_sh.spec_energy_spheat_forecast,
                'Spec. sp. cooling (kWh per m2)': hh_sol.hh_sc.spec_energy_forecast,
                'Spec. light&appl (kWh per per.)': hh_sol.hh_liandap.spec_energy_forecast,
                'Spec. cooking (kWh per person)': hh_sol.hh_co.spec_energy_forecast
                }
        
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
    
        ## historical energy data
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_HH_DEMAND_SUBSECTORS_HIS)
        data = {'lighting and appliances': hh_sol.hh_liandap.energy_demand_his,
                'space cooling': hh_sol.hh_sc.energy_demand_his,
                'cooking': hh_sol.hh_co.energy_demand_his,
                'space heating': hh_sol.hh_sh.energy_demand_his, 
                'hot water': hh_sol.hh_hw.energy_demand_his}
        
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
                
        ## Characteristics of the households
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_HH_CHARACTERISTICS_HIS)
        data = {'Area per household (m2)': hh_sol.hh_data_forecast.area_per_hh_hist,
                'Living area total (Mil. m2)': hh_sol.hh_data_forecast.area_total_hist,
                'Spec. light&appl (kWh per per.)': hh_sol.hh_liandap.spec_energy_hist,
                'Spec. cooking (kWh per person)': hh_sol.hh_co.spec_energy_hist}
        
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

    #------------------------------------------------------------------------------
    # Commertial, trade and services.

    if CTRL.CTS_ACTIVATED == True:
        # defining all outputs
        result_employee_number = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_CTS, FILE.FILENAME_OUTPUT_CTS_EMPLOYEE), engine='xlsxwriter')
        result_energy = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"CTS"+FILE.FILENAME_OUTPUT_DEMAND), engine='xlsxwriter')
        result_energy_timeseries = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"CTS"+FILE.FILENAME_OUTPUT_TIMESERIES), engine='xlsxwriter')
        
        cts_sol.employee.to_excel(result_employee_number, sheet_name="Empleyee total", index=False, startrow=0)
        cts_sol.employee_NUTS2.to_excel(result_employee_number, sheet_name="Empleyee NUTS2 total", index=False, startrow=0)
        cts_sol.energy_demand.to_excel(result_energy, sheet_name="CTS_demand", index=False, startrow=0)
        cts_sol.energy_timeseries.to_excel(result_energy_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
                  
        result_employee_number.close()
        result_energy.close()
        result_energy_timeseries.close()

        if CTRL.NUTS2_ACTIVATED:
            cts_energy_demand_NUTS2 = cts_sol.cts_energy_demand_NUTS2
            
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "CTS"+FILE.FILENAME_OUTPUT_DEMAND_NUTS2)
            result_cts_energy_demand_NUTS2 = pd.ExcelWriter(path, engine='xlsxwriter')
            cts_energy_demand_NUTS2.to_excel(result_cts_energy_demand_NUTS2,sheet_name="CTS", index=False, startrow=0)
            result_cts_energy_demand_NUTS2.close()      
   
    #------------------------------------------------------------------------------
    # Traffic.

    if CTRL.TRA_ACTIVATED == True:
        
        # Final TRA output
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "TRA"+FILE.FILENAME_OUTPUT_DEMAND)
        data = {'TRA_demand': tra_sol.tra_ft_pt_energy_demand}
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        # Additional TRA outputs
        ## Person traffic results
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_PT_DEMAND)
        data = {'Elec_PerCountry': tra_sol.tra_pt.energy_demand_pt_elec, 
            'Hydrogen_PerCountry': tra_sol.tra_pt.energy_demand_pt_h2,
            'Total_EnergyCarrier_PerCountry': tra_sol.tra_pt.pt_energy_total}
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

        ## Freight traffic results
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_FT_DEMAND)
        data = {'Elec_PerCountry': tra_sol.tra_ft.energy_demand_ft_elec, 
            'Hydrogen_PerCountry': tra_sol.tra_ft.energy_demand_ft_h2,
            'Total_EnergyCarrier_PerCountry': tra_sol.tra_ft.ft_energy_total}
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
                
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_TRA_PRODUCTION_VOLUME)
        data = {"total_" + str(CTRL.FORECAST_YEAR): tra_sol.tra_ft.ft_volume_sum_forecast, 
            "total_" + str(CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS): tra_sol.tra_ft.ft_volume_sum_historical,
            "single_" + str(CTRL.TRA_REFERENCE_YEAR_PRODUCTION_HIS): tra_sol.tra_ft.production_sum_historical_singlesectors}
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
                
        ## Person and freight traffic 
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_TRA_KILOMETERS)
        data = {'Person_kilometers': tra_sol.tra_pt.pt_Mrd_pkm, 
            'Tonne_kilometers': tra_sol.tra_ft.ft_Mil_tkm}
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)
                
        ## Modal split
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA_TRAFFIC, FILE.FILENAME_OUTPUT_TRA_MODALSPLIT)
        data = {'Pt Modal Split': tra_sol.tra_pt.modalsplit_percountry_scaled,
            'Ft Modal Split': tra_sol.tra_ft.modalsplit_percountry_scaled,
            'Pt Modal Split_unscaled': tra_sol.tra_pt.modalsplit_percountry,
            'Ft Modal Split_unscaled': tra_sol.tra_ft.modalsplit_percountry}
        with pd.ExcelWriter(path) as ew: 
            for sheet_name in data.keys():
                data[sheet_name].to_excel(ew, sheet_name=sheet_name, index=False)

    #------------------------------------------------------------------------------
    # Summary.

    if (CTRL.IND_ACTIVATED == True) and (CTRL.HH_ACTIVATED == True) and (CTRL.TRA_ACTIVATED == True) and (CTRL.CTS_ACTIVATED == True):
        
        # Total energy demand per energy carrier    
        overall_demand_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_IND),
                                sheet_name=["IND_demand"],skiprows=0)["IND_demand"]
        for sheet in ["HH", "TRA", "CTS"]:
            sheet_name_demand = sheet+"_demand"
            df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+FILE.FILENAME_OUTPUT_DEMAND),
                                    sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
            overall_demand_df = overall_demand_df.set_index("Country").add(df_sector.set_index("Country"), fill_value=0).reset_index()
            
        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_TOTAL+'.csv')
        overall_demand_df.to_csv(path, index=False, sep=";")

        path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_TOTAL+'.xlsx')
        result_energy_demand = pd.ExcelWriter(path, engine='xlsxwriter')
        overall_demand_df.to_excel(result_energy_demand,sheet_name="overall_demand", index=False, startrow=0)
        result_energy_demand.close()
        
        # Total energy demand per energy carrier per NUTS2
        if CTRL.NUTS2_ACTIVATED:
            overall_demand_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_IND_NUTS2),
                                    sheet_name=["IND"],skiprows=0)["IND"]
            for sheet in ["HH", "TRA", "CTS"]:
                df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sheet+FILE.FILENAME_OUTPUT_DEMAND_NUTS2),
                                        sheet_name=[sheet],skiprows=0)[sheet]
                overall_demand_df = overall_demand_df.set_index("NUTS2").add(df_sector.set_index("NUTS2"), fill_value=0).reset_index()
                
            path = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_TOTAL_NUTS2)
            overall_demand_df.to_csv(path, index=False, sep=";")
        
        if CTRL.ACTIVATE_TIMESERIES:    
            add_timeseries(FILE, FILE.FILENAME_OUTPUT_TIMESERIES, CTRL.CTS_ACTIVATED)
    
    #------------------------------------------------------------------------------
    # Graphical Output (Plot and create figures).
    # Energy demand per sector and country
    if (CTRL.GRAPHICAL_OUTPUT_ACTIVATED == True):
        for comm in CTRL.ENERGYCARRIER:
            # Concatenate all sectors in one DataFrame per energy carrier
            i=0
            for sector, sector_activated in zip(["IND", "HH", "TRA", "CTS"],
                                                [CTRL.IND_ACTIVATED, CTRL.HH_ACTIVATED, CTRL.TRA_ACTIVATED, CTRL.CTS_ACTIVATED]):
                columns = []
                if sector_activated:
                    sheet_name_demand = sector+"_demand"
                    if sector == "IND":
                        file_name = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_DEMAND_IND)
                    else:
                        file_name = os.path.join(FILE.FILE_PATH_OUTPUT_DATA, sector+FILE.FILENAME_OUTPUT_DEMAND)
                    df_sector_help = pd.read_excel(file_name, sheet_name=[sheet_name_demand],skiprows=0)[sheet_name_demand]
                    df_sector_help = df_sector_help.set_index("Country")
                    
                    # Even after a prognosis calculation, a graphical output can be ...
                    # chosen to be a subset of the calculated countries.
                    # No new calculation needed, just new run for the graphical output.
                    # df_country_list = []
                    # for country_df in df_sector_help["Country"]:
                    #     if country_df in CTRL.CONSIDERED_COUNTRIES:
                    #         df_country_list = df_country_list.append(1)
                    #     else:
                    #         df_country_list = df_country_list.append(0)

                    # df_sector_help = df_sector_help[df_country_list]
                    
                    # Make first sector a basis and concatenate other sectors to it
                    if i == 0:
                        df = df_sector_help[ [comm+" [TWh]"]]
                        df = df.rename(columns={comm+" [TWh]": sector})
                    else:
                        df = pd.concat([df, df_sector_help[comm+" [TWh]"]], axis = 1)
                        df = df.rename(columns={comm+" [TWh]": sector})
                    i += 1
                    columns = columns.append(sector)
            #df = df.reset_index()

            #Plot
            #df.set_index(['Country']).plot(kind='bar', stacked=True)
            df.plot(kind='bar', stacked=True)
            plt.title(comm + " demand per sector in " + str(CTRL.FORECAST_YEAR))
            plt.xlabel("Country")
            plt.ylabel("Energy demand in [TWh]")
            plt.tight_layout()
            plt.ylim(bottom=0)
            #plt.show()
            plt.savefig(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "Plot_" + comm + "_EnergyDemand_perEnergyCarrier_"+str(CTRL.FORECAST_YEAR)+".png"), bbox_inches='tight')    

