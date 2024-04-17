###############################################################################                                                                                   
# Input and preparation of input data
###############################################################################
"""The module initiates the input data for the demand model.

The script not only reads in the data, but also prepares it for further use.
"""
###############################################################################
#Imports
###############################################################################
from libraries import *
import get_population_gdp
import op_methods

def in_data(CTRL, FILE):
    
    #------------------------------------------------------------------------------
    # General (gen_).
    # Population, GDP forecast and abbreviations of countries.

    gen = GENERAL(CTRL, FILE)

    #------------------------------------------------------------------------------
    # Industry (ind_).

    if CTRL.IND_ACTIVATED == True:
        ind = INDUSTRY(CTRL, FILE)
    else:
        ind = 1
    
    #------------------------------------------------------------------------------
    # Commercial trade and services (cts_).

    if CTRL.CTS_ACTIVATED == True:
        cts = CTS(CTRL, FILE)
    else:
        cts = 1
    
    #------------------------------------------------------------------------------
    # Household (hh_).

    if CTRL.HH_ACTIVATED == True:
        hh = HOUSEHOLD(CTRL, FILE)
    else:
        hh = 1

    #------------------------------------------------------------------------------
    # Traffic (tra_).    
    
    if CTRL.TRA_ACTIVATED == True:
        tra = TRAFFIC(CTRL, FILE)
    else:
        tra = 1

    return gen, ind, cts, hh, tra


class GENERAL():
    

    def __init__(self, CTRL, FILE):
        self.abbreviations = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL,"Abbreviations.xlsx"),
                                               sheet_name=["Data"],skiprows=0)["Data"]
        self.nuts_codes = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "NUTS2_classification.xlsx"),
                                        sheet_name=["Data"],skiprows=0)["Data"]
        
        # Population data
        self.pop_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Population_historical_world.xls"),
                                       sheet_name=["Data"],skiprows=0)["Data"]
        self.pop_nuts2_table = pd.read_csv(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Population_historical_NUTS2.csv"),
                                           engine='python', encoding = 'latin1')
        self.population_changeprojection = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Population_changeprojection_NUTS2.xlsx"),
                                                    sheet_name=["Populationprojection_NUTS2_"+str(CTRL.NUTS2_CLASSIFICATION)],
                                                    skiprows=0)["Populationprojection_NUTS2_"+str(CTRL.NUTS2_CLASSIFICATION)]
        self.pop_forecast_country = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Population_projection_world.xlsx"),
                                                      sheet_name=["Population_Countries"],skiprows=0)["Population_Countries"]
        if CTRL.NUTS2_ACTIVATED:
            if CTRL.POP_ACTIVATED:
                get_population_gdp.load_population(CTRL, FILE, self, FILE.FILENAME_OUTPUT_POPULATION)

            self.pop_forecast_nuts2 = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_POPULATION),
                                                sheet_name=["Population_NUTS2"],skiprows=0)["Population_NUTS2"]
            self.pop_forecast = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_POPULATION),
                                                      sheet_name=["Population_NUTS2","Population_Countries"],skiprows=0)
        else:
            self.pop_forecast = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Population_projection_world.xlsx"),
                                              sheet_name=["Population_NUTS2","Population_Countries"],skiprows=0)
            
        self.gdp_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "GDP_per_capita_historical.xlsx"), # GDP_KKS = GDP_PPS_current_prices_per_person.xls
                                      sheet_name=None,skiprows=0)["constant 2015 USD"] # or constant LCU or PPP constant 2017 internat
        self.gdp_changeprojection= pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "GDP_per_capita_change_rate_projection.xlsx"))
        self.GDP_prognosis = get_population_gdp.gdp_prognosis(CTRL, FILE, self, FILE.FILENAME_OUTPUT_GDP)
        
        # For transformation from fuels to heat
        if CTRL.FINAL_DEMAND_ACTIVATED: 
            efficiency = "Data_final"
        else:
            efficiency = "Data"
        self.efficiency_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Efficiency_Combustion.xlsx"),
                                              sheet_name=[efficiency],skiprows=0)[efficiency]
        self.efficiency_heat_levels = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Efficiency_Combustion.xlsx"),
                                              sheet_name=["Data_final_heat_levels"],skiprows=0)["Data_final_heat_levels"]

        
class INDUSTRY():

    
    def __init__(self, CTRL, FILE):
        
        logger = logging.getLogger(__name__)
        logger.info("-"*79)
        logger.info("Initialize data IND, CTS, HH, TRA")
        print("start ind data preparation")
        self.steel_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Steel.xlsx"),sheet_name=["Data_total"],skiprows=0)["Data_total"]
        self.steel_prim_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Steel.xlsx"),sheet_name=["Steel_prim"],skiprows=0)["Steel_prim"]
        self.steel_sec_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Steel.xlsx"),sheet_name=["Steel_sec"],skiprows=0)["Steel_sec"]
        self.alu_prim_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Aluminium.xlsx"),sheet_name=["Prim_Data"],skiprows=0)["Prim_Data"]
        self.alu_sec_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Aluminium.xlsx"),sheet_name=["Sec_Data"],skiprows=0)["Sec_Data"]
        self.cement_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Cement.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.paper_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Paper.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.copper_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Copper.xlsx"),sheet_name=["Data"],skiprows=2)["Data"]
        self.copper_prim_table = self.copper_table[self.copper_table["Type"]=="Primary"].reset_index()
        self.copper_prim_table = self.copper_prim_table.drop(["index", "Type"],axis= 1)
        self.copper_sec_table = self.copper_table[self.copper_table["Type"]=="Secondary"].reset_index()
        self.copper_sec_table = self.copper_sec_table.drop(["index", "Type"],axis= 1)
        self.ethylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Ethylene.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.methanol_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Methanol.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.ammonia_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Ammonia.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.glass_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Glass.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.chlorine_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Chlorine.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.propylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Propylene.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.aromatics_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Aromatics.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.spec_consum_vordef=pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Specific_Consumption.xlsx"),
                                             sheet_name=None,skiprows=0)
        self.spec_consum_BAT=pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Specific_Consumption_BAT.xlsx"),
                                             sheet_name=None,skiprows=0)
        self.installed_capacity_NUTS2=pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Installed_capacity_NUTS2.xlsx"),
                                             sheet_name=None,skiprows=0) #[a for a in CTRL.IND_SUBECTORS if a not in ["steel_direct"]]
        self.en_demand_steel = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "nrg_bal_s_steel.xls"),
                                       sheet_name=CTRL.IND_EN_DEMAND_SHEET,skiprows=0)
        self.en_demand_paper = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "nrg_bal_s_paper.xls"),
                                       sheet_name=CTRL.IND_EN_DEMAND_SHEET,skiprows=0)
        self.rest_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Ind_energy_demand_"+str(CTRL.REF_YEAR)+"_Trend_Restcalcul.xlsx"),
                                        sheet_name=["Data"],skiprows=0)["Data"]
        self.heat_levels = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Heat_levels.xlsx"),
                                         sheet_name=["Data"],skiprows=0)["Data"]
        self.load_profile = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "IND_Hourly_load_profile.xlsx"),
                                          sheet_name=["Data"],skiprows=0)["Data"]

        if CTRL.ACTIVATE_TIMESERIES:
            for ind_type in ["chemicals_and_petrochemicals", "food_and_tobacco", "iron_and_steel", "non_metalic_minerals", "paper"]:
                setattr(self, "heat_load_profile_"+ind_type, 
                        pd.read_csv(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY,"hotmaps_task_2.7_load_profile_industry_"+ind_type+"_yearlong_2018.csv"), engine='python'))
        
        #    self.heat_load_profiles = {ind_type: pd.read_csv(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY,
        #                                                              "hotmaps_task_2.7_load_profile_industry_"+ind_type+"_yearlong_2018.csv"), engine='python')
        #                           for ind_type in ["chemicals_and_petrochemicals", "food_and_tobacco", "iron_and_steel", "non_metalic_minerals", "paper"]}
        #    self.heat_profile = = pd.read_csv(r'H:\Projekte\endemo\input\industry\not_directly_used\hotmaps_task_2.7_load_profile_industry_paper_yearlong_2018.csv', engine='python')

        #food_production = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "FoodProduction_.xlsx"), sheet_name=None,skiprows=0)
        #for food_product_name in CTRL.IND_FOOD: #food_production.sheet_names[0:len(food_production.sheet_names)-1]:
        #    setattr(self, food_product_name+"_table", food_production[food_product_name])


class CTS():

    
    def __init__(self, CTRL, FILE):
        
        print("start cts data preparation")
        self.employee_NUTS0 = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Employee_Nuts0.xlsx"),
                                            sheet_name=["Data"],skiprows=0)["Data"]
        # self.employee_NUTS2 = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Employee_Nuts2.xlsx"),
        #                                     sheet_name=["Employee_per_sector"],skiprows=0)["Employee_per_sector"]
        self.employee_NUTS2_distrib = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Employee_distribution_perNUTS2.xlsx"),
                                            sheet_name=None,skiprows=0)
        self.endemand = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "nrg_bal_s_GHD.xlsx"),
                                      sheet_name=CTRL.CTS_EN_DEMAND_SHEET,skiprows=0)
        self.load_profile = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "CTS_Hourly_load_profile.xlsx"),
                                          sheet_name=["Data"],skiprows=0)["Data"]

        
class HOUSEHOLD():

    
    def __init__(self, CTRL, FILE):
        
        print("start HH data preparation")
        # Space heating
        xlsx_space_heating = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, "Space_Heating.xlsx"),
                                           sheet_name=['AreaPerHousehold','TotalFloorArea','PersPerHousehold','SpecificEnergyUse', 'Calibration'],
                                           skiprows=0)
        self.area_per_hh = xlsx_space_heating['AreaPerHousehold']
        self.floor_area = xlsx_space_heating['TotalFloorArea']
        self.person_per_hh = xlsx_space_heating['PersPerHousehold']
        self.spec_energy_spheat = xlsx_space_heating['SpecificEnergyUse']
        self.calibration_spheat = xlsx_space_heating['Calibration']
        
        # hot water
        xlsx_hot_water = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, "Hot_Water.xlsx"), sheet_name=None)
        self.demand_per_person = xlsx_hot_water['WaterPerPers']
        self.techn_data = xlsx_hot_water['TechnData']
        self.calibration_hw = xlsx_hot_water['Calibration']

        if CTRL.ACTIVATE_TIMESERIES:
            self.timeseries = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, "HH_Hourly_load_profile.xlsx"), sheet_name=['timeseries'])['timeseries']
        
class TRAFFIC():

    def __init__(self, CTRL, FILE):

        print("start tra data preparation")
        # Person traffic kilometres
        xlsx_person_traffic = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, "Persontraffic.xlsx"),
                                           sheet_name=None, skiprows=0)
        self.personkm_road_rail = xlsx_person_traffic['Personkm_road_rail']
        self.personkm_flight = xlsx_person_traffic['Passengerkm_flight']

        # Freight traffic kilometres
        xlsx_freight_traffic = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, "Freighttraffic.xlsx"),
                                           sheet_name=None, skiprows=0)
        self.tonnekm_road_rail_ship = xlsx_freight_traffic['Tonnekm_road_rail_ship']
        self.tonnekm_flight = xlsx_freight_traffic['Tonnekm_flight']
        self.tra_ft_volume_flight_his = xlsx_freight_traffic['Tonne_flight']

        # Modal split depending on user input settings
        pt_modals = ["car","rail","bus"]
        ft_modals = ["rail","road","ship"]
        if CTRL.TRA_MODALSPLIT_SCENARIO == "Historical": 
            selection = "_his"
        elif CTRL.TRA_MODALSPLIT_SCENARIO == "User-defined":
            selection = "_user"
        for modal in pt_modals:
            # exampel: self.modalsplit_pt_car = xlsx_person_traffic['ModalSplit_car'] or ['ModalSplit_car_user']
            setattr(self,"modalsplit_pt_" + modal, xlsx_person_traffic['ModalSplit_' + modal + selection])
        for modal in ft_modals:
            setattr(self,"modalsplit_ft_" + modal, xlsx_freight_traffic['ModalSplit_' + modal + selection])

        
        # Energy demand and distribution on commodities electricity and hydrogen depending on user input settings
        xlsx_pt_energy = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, "Pt_FinalEnergySources.xlsx"),
                                       sheet_name=None, skiprows=0)
        self.tra_pt_energypersourcepermodal = xlsx_pt_energy['EnergyperSource']
        xlsx_ft_energy = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, "Ft_FinalEnergySources.xlsx"),
                                       sheet_name=None, skiprows=0)
        self.tra_ft_energypersourcepermodal = xlsx_ft_energy['EnergyperSource']
        
        if CTRL.TRA_SCENARIO_FINALSOURCES == "Reference":
            scenario = "_ref"
        elif CTRL.TRA_SCENARIO_FINALSOURCES == "User-defined":
            scenario = "_user"
            
        for tra_type, xlsx_energy in zip(["pt", "ft"],[xlsx_pt_energy, xlsx_ft_energy]):
            if tra_type == "pt":
                vehicle_types = ["car", "bus", "rail", "ship", "flight"]
            else:
                vehicle_types = ["rail", "road", "ship", "flight"]
            
            for com_type in ["elec", "h2"]:
                for vehicle_type in vehicle_types:
                    # exampel: self.tra_pt_energysources_car_elec
                    setattr(self, "tra_"+tra_type+"_energysources_"+vehicle_type+"_"+com_type, 
                            xlsx_energy[com_type+"_"+vehicle_type + scenario])
           
        # Timeseries
        if CTRL.ACTIVATE_TIMESERIES:
            timeseries = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, "TRA_Hourly_load_profile.xlsx"),sheet_name=["timeseries_LoadingProfile","timeseries_MobilityProfile"],skiprows=0)
            self.timeseries_loading = timeseries["timeseries_LoadingProfile"] 
            self.timeseries_mobility = timeseries["timeseries_MobilityProfile"]

        # Industry ammounts to be transported
        self.rest_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Ind_energy_demand_"+str(CTRL.REF_YEAR)+"_Trend_Restcalcul.xlsx"),
                                        sheet_name=["Data"],skiprows=0)["Data"]     
        self.steel_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Steel.xlsx"),sheet_name=["Data_total"],skiprows=0)["Data_total"]
        self.alu_prim_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Aluminium.xlsx"),sheet_name=["Prim_Data"],skiprows=0)["Prim_Data"]
        self.alu_sec_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Aluminium.xlsx"),sheet_name=["Sec_Data"],skiprows=0)["Sec_Data"]
        self.cement_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Cement.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.paper_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Paper.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.copper_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Copper.xlsx"),sheet_name=["Data"],skiprows=2)["Data"]
        self.copper_prim_table = self.copper_table[self.copper_table["Type"]=="Primary"].reset_index()
        self.copper_prim_table = self.copper_prim_table.drop(["index", "Type"],axis= 1)
        self.copper_sec_table = self.copper_table[self.copper_table["Type"]=="Secondary"].reset_index()
        self.copper_sec_table = self.copper_sec_table.drop(["index", "Type"],axis= 1)
        self.ethylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Ethylene.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.methanol_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Methanol.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.ammonia_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Ammonia.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.glass_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Glass.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.chlorine_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Chlorine.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.propylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Propylene.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.aromatics_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Production_Aromatics.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]