###############################################################################                                                                                   
# Mathematical operations
###############################################################################
"""The module contains mathematical operators for solving the sector-specific 
   problems.

"""
###############################################################################
#Imports
###############################################################################

from libraries import *

#class REGRESSION()

def redistribution_NUTS2(energy_demand, pop_prognosis, abb_table):
    col = ["NUTS2"]
    for i in energy_demand.columns[1:len(energy_demand.columns)]:
        col.append(i)
    content = []
    
    idx_demand = 0
    for country in energy_demand["Country"]:
        abb = abb_table["Internationale Abkuerzung"][list(abb_table["Country"]).index(country)]
        #import pdb; pdb.set_trace()
        pop_country = pop_prognosis["Population_Countries"]["Population Prog Year [Pers.]"][list(pop_prognosis["Population_Countries"]["Country"]).index(abb)]
        idx_nuts2_regions = [i for i, x in enumerate(pop_prognosis["Population_NUTS2"]["Nuts_2"]) if x[0:2] == abb]
        for idx_nuts2region in idx_nuts2_regions:
            proportion = pop_prognosis["Population_NUTS2"]["Population Prog Year [Pers.]"][idx_nuts2region]/pop_country
            nuts2region = pop_prognosis["Population_NUTS2"]["Nuts_2"][idx_nuts2region]
            content_row = [nuts2region]
            for i in col[1:len(col)]:
                content_row.append(energy_demand[i][idx_demand]*proportion)
            content.append(content_row)
        idx_demand+= 1
        
    energy_demand_NUTS2 = pd.DataFrame(content, columns = col)
        
    return energy_demand_NUTS2

#------------------------------------------------------------------------------

#------------------------------------------------------------------------------

def add_timeseries(FILE, path_timeseries, CTRL):

    if CTRL.CTS_ACTIVATED == True:
    
        overall_timeseries_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND'+path_timeseries),
                                    sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"]  
        for sheet in ["HH", "TRA", "CTS"]:
            df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,sheet+path_timeseries),
                                    sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"] 
            overall_timeseries_df = overall_timeseries_df.set_index("t").add(df_sector.set_index("t"), fill_value=0).reset_index() 
        
        result_total_timeseries = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Total'+path_timeseries), engine='xlsxwriter')
        overall_timeseries_df.to_excel(result_total_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
        result_total_timeseries.save()
    
    else:

        overall_timeseries_df = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'IND'+path_timeseries),
                                    sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"]  
        for sheet in ["HH", "TRA"]:
            df_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,sheet+path_timeseries),
                                    sheet_name=["Load_timeseries"],skiprows=0)["Load_timeseries"] 
            overall_timeseries_df = overall_timeseries_df.set_index("t").add(df_sector.set_index("t"), fill_value=0).reset_index() 
        
        result_total_timeseries = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,'Total'+path_timeseries), engine='xlsxwriter')
        overall_timeseries_df.to_excel(result_total_timeseries, sheet_name="Load_timeseries", index=False, startrow=0)
        result_total_timeseries.save()
        


    