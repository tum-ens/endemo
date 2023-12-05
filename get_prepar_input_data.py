###############################################################################                                                                                   
# Input and preparation of input data
###############################################################################
"""The module initiates the input data for the demand model.

The script not only reads in the data, but also prepares it for further use.
"""
###############################################################################
#Imports
###############################################################################

import get_population
from xlrd import open_workbook
import pandas as pd
import load_excel
import os

def in_data(CTRL, FILE):

    #------------------------------------------------------------------------------
    # General (gen_).

    # Population, GDP forecast and abbreviations of countries.

    #get_population.load_population(CTRL, FILE)
    gen = GENERAL(CTRL, FILE)

    #------------------------------------------------------------------------------
    # Industry (ind_).

    if CTRL.IND_ACTIVATED == True:
        ind = INDUSTRY(CTRL, FILE)
    elif CTRL.IND_ACTIVATED == False:
        ind = 1
    
    #------------------------------------------------------------------------------
    # Commercial trade and services (cts_).

    if CTRL.CTS_ACTIVATED == True:
        cts = CTS(CTRL, FILE)
    elif CTRL.CTS_ACTIVATED == False:
        cts = 1
    
    #------------------------------------------------------------------------------
    # Household (hh_).

    if CTRL.HH_ACTIVATED == True:
        hh = HOUSEHOLD(CTRL, FILE)
    elif CTRL.HH_ACTIVATED == False:
        hh = 1

    #------------------------------------------------------------------------------
    # Traffic (tra_).    
    
    if CTRL.TRA_ACTIVATED == True:
        tra = TRAFFIC(CTRL, FILE)
    if CTRL.TRA_ACTIVATED == False:
        tra = 1

    return gen, ind, cts, hh, tra

class GENERAL():

    def __init__(self, CTRL, FILE):

        if CTRL.POP_ACTIVATED == True:
            self.pop = get_population.POPULATION(CTRL, FILE)
        self.pop_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, FILE.FILENAME_INPUT_POPULATION_HISTORICAL),
            sheet_name=["Data"],skiprows=0)["Data"]
        self.pop_nuts2_table = pd.read_csv(FILE.FILE_PATH_INPUT_DATA_GENERAL+"\\"+ "Population_current_nuts2_v3.csv", engine='python')
        
        self.gen_abbreviations = pd.read_csv(FILE.FILE_PATH_INPUT_DATA_GENERAL+"\\"+
            FILE.FILENAME_INPUT_ABBREVIATIONS, engine='python')

        # Inputs of GDP data depends on the user input in set and control parameters. 
        if CTRL.ACTIVATE_CHAINED_GDP:
            gdp_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, FILE.FILENAME_INPUT_GDP_wKKS), #"GDP_wKKS.xls"
                                      sheet_name=["Data"],skiprows=0)["Data"]
        else:
            gdp_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, FILE.FILENAME_INPUT_GDP_KKS), #"GDP_KKS.xls"
                                      sheet_name=["Data"],skiprows=0)["Data"]
        self.gdp_table = gdp_table
        
        self.gdp_forecast_percentage= pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "GDP_Forecast.xlsx"))
        self.efficiency_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_GENERAL, "Efficiency_Combustion_normal.xlsx"),skiprows=0) #Efficiency_Combustion_normal for real combustion values, Efficiency_Combustion for eff = 100%


class INDUSTRY():

    def __init__(self, CTRL, FILE):
        
        self.steel_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Steel_Production.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.alu_prim_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Aluminium_Production.xlsx"),sheet_name=["Prim_Data"],skiprows=0)["Prim_Data"]
        self.alu_sec_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Aluminium_Production.xlsx"),sheet_name=["Sec_Data_const"],skiprows=0)["Sec_Data_const"]
        self.cement_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Cement_Production.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.paper_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Paper_Production.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.ethylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Ethylene_Production.xls"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
        self.methanol_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Methanol_Production.xls"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
        self.ammonia_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Ammonia_Production.xls"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
        self.glass_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Glass_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
        self.chlorin_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Chlorin_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
        self.propylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Propylene_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
        self.aromate_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Aromate_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
        self.spec_consum_vordef=pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Specific_Consumption.xlsx"),
                                             sheet_name=CTRL.IND_SUBECTORS,skiprows=0)
        self.spec_consum_BAT=pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "BAT_Consumption.xlsx"),
                                             sheet_name=None,skiprows=0)
        self.installed_capacity_NUTS2=pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Installed_capacity_NUTS2.xlsx"),
                                             sheet_name=None,skiprows=0) #[a for a in CTRL.IND_SUBECTORS if a not in ["steel_direct"]]
        self.endemand_book_steel = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "nrg_bal_s_stahl.xls"),
                                       sheet_name=CTRL.IND_ENDEMAND_SHEET,skiprows=0)
        self.endemand_book_paper = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "nrg_bal_s_papier.xls"),
                                       sheet_name=CTRL.IND_ENDEMAND_SHEET,skiprows=0)
        self.rest_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Ind_energy_demand_2018_Trend_Restcalcul_v2.xlsx"),sheet_name=["overall"],skiprows=0)["overall"]
        self.heat_levels = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Heat_levels.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        self.load_profile = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "IND_Loadprofile.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]

        for ind_type in ["chemicals_and_petrochemicals", "food_and_tobacco", "iron_and_steel", "non_metalic_minerals", "paper"]:
            setattr(self, "heat_load_profile_"+ind_type, 
                    pd.read_csv(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY,
                                             "hotmaps_task_2.7_load_profile_industry_"+ind_type+"_yearlong_2018.csv"), engine='python'))
            #self.heat_load_profiles = {ind_type: pd.read_csv(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY,
        #                                                              "hotmaps_task_2.7_load_profile_industry_"+ind_type+"_yearlong_2018.csv"), engine='python')
        #                           for ind_type in ["chemicals_and_petrochemicals", "food_and_tobacco", "iron_and_steel", "non_metalic_minerals", "paper"]}
            #self.heat_profile = = pd.read_csv(r'H:\Projekte\endemo\input\industry\not_directly_used\hotmaps_task_2.7_load_profile_industry_paper_yearlong_2018.csv', engine='python')
        
        
        #food
        #food_production = pd.ExcelFile(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Food_Production.xlsx"))
        #for food_product_name in CTRL.IND_FOOD: #food_production.sheet_names[0:len(food_production.sheet_names)-1]:
        #    setattr(self, food_product_name+"_table", food_production.parse(food_product_name))

        food_production = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Food_Production.xlsx"), sheet_name=CTRL.IND_FOOD,skiprows=0)
        for food_product_name in CTRL.IND_FOOD: #food_production.sheet_names[0:len(food_production.sheet_names)-1]:
            setattr(self, food_product_name+"_table", food_production[food_product_name])

class CTS():

    def __init__(self, CTRL, FILE):
        
        #self.employee_per_sector = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Employee_Nuts2.xlsx"),sheet_name="Data_Employee_Nuts2", header=0)
        self.employee_NUTS0 = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Employee_Nuts0.xlsx"),sheet_name=["Rohdaten Eurostat", "Employee_per_sector"],skiprows=0)
        self.employee_NUTS2 = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Employee_Nuts2.xlsx"),sheet_name=["Employee_per_sector"],skiprows=0)["Employee_per_sector"]
        self.endemand = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "nrg_bal_s_GHD.xls"),sheet_name=CTRL.CTS_ENDEMAND_SHEET,skiprows=0)
        self.load_profile = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "CTS_Loadprofile.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
        #self.endemand_el = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Energy_balance_spec_Nuts0.xlsx"),sheet_name="spec_Electricity_consumption",skiprows=0)
        #self.endemand_heat = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_COMMERCIAL_TRADE_AND_SERVICES, "Energy_balance_spec_Nuts0.xlsx"),sheet_name="spec_Heat_consumption",skiprows=0)
        

class HOUSEHOLD():

    def __init__(self, CTRL, FILE):

        # Space heating
        self.area_per_household = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_SPACE_HEATING, 'AreaPerHousehold')
        self.person_per_household = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_SPACE_HEATING, 'PersPerHousehold')
        self.specific_energy_use = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_SPACE_HEATING, 'SpecificEnergyUse')
        self.sources_space_heating_temp = ['x', 'x', 'x', 'x','renewable & wastes', 'x', 'x', 'x','oil/petroleum products','solid fossil fuels', 'gas','derived heat', 'electricity']
        self.sources_space_heating = ['electricity', 'derived heat', 'gas', 'solid fossil fuels', 'oil/petroleum products', 'renewable & wastes']

        # Warm water
        self.demand_per_person = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_WARM_WATER, 'DemandPerPers')
        self.techn_data = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_WARM_WATER, 'TechnData')

        #Sources
        self.sources_split = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_HOUSEHOLD_SOURCES, 'Sources_Setting_high')

        self.building_stock = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_SPACE_HEATING, 'buildingstock')
        self.heating_stock = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_SPACE_HEATING, 'heatingstock')

        self.timeseries = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_HOUSEHOLDS, FILE.FILENAME_INPUT_HOUSEHOLD_TIMESERIES, 'timeseries')

class TRAFFIC():

    def __init__(self, CTRL, FILE):

        # Person traffic 
        self.personkm_road_train = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'Personkm_road_train')
        self.passengerkm_flight = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'Passengerkm_flight')

        if CTRL.TRA_SCENARIO_SELECTION_MODALSPLIT == "Historical":          
            self.modalsplit_car = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_car')
            self.modalsplit_rail = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_rail') 
            self.modalsplit_bus = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_bus')

        elif CTRL.TRA_SCENARIO_SELECTION_MODALSPLIT == "EU Reference Scenario 2020":
            self.modalsplit_car = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_car_EURef')
            self.modalsplit_rail = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_rail_EURef') 
            self.modalsplit_bus = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_bus_EURef')

        elif CTRL.TRA_SCENARIO_SELECTION_MODALSPLIT == "User defined":
            self.modalsplit_car = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_car_Userdefined')
            self.modalsplit_rail = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_rail_Userdefined') 
            self.modalsplit_bus = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'ModalSplit_bus_Userdefined')

        self.tra_pt_energypermodal = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC, 'EnergyperSource')

        # Freight traffic 
        self.tonnekm_road_train = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'Tonnekm_road_train')
        self.tonnekm_flight = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'Tonnekm_flight')

        if CTRL.TRA_SCENARIO_SELECTION_MODALSPLIT == "Historical": 
            self.modalsplit_railway = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit_railways')
            self.modalsplit_road = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit_roads') 
            self.modalsplit_ship = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit_ship')

        elif CTRL.TRA_SCENARIO_SELECTION_MODALSPLIT == "EU Reference Scenario 2020":
            self.modalsplit_railway = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit_railways_EURef')
            self.modalsplit_road = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit_roads_EURef') 
            self.modalsplit_ship = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit_ship_EURef')

        elif CTRL.TRA_SCENARIO_SELECTION_MODALSPLIT == "User defined":
            self.modalsplit_railway = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit__Userdefined')
            self.modalsplit_road = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit__Userdefined') 
            self.modalsplit_ship = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'ModalSplit__Userdefined')


        self.tra_ft_energypermodal = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC, 'EnergyperSource')
        self.tra_ft_production_volume_flight_his = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PRODUCTION_VOLUME_HIS, 'Flight')

        self.industry_rest = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_REST, 'Data') 

        ## Electrical and hydrogen depending on input setting of user
        if CTRL.SCENARIO == "reference":
            self.tra_pt_energysources_car_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_ELECTRICAL, 'elec_car_ref')
            self.tra_pt_energysources_bus_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_ELECTRICAL, 'elec_bus_ref')
            self.tra_pt_energysources_rail_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_ELECTRICAL, 'elec_rail_ref')
            self.tra_pt_energysources_flight_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_ELECTRICAL, 'elec_flight_ref')  
            self.tra_pt_energysources_car_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_HYDROGEN, 'hydrogen_car_ref')
            self.tra_pt_energysources_bus_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_HYDROGEN, 'hydrogen_bus_ref')
            self.tra_pt_energysources_rail_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_HYDROGEN, 'hydrogen_rail_ref')
            self.tra_pt_energysources_flight_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_PERSON_TRAFFIC_HYDROGEN, 'hydrogen_flight_ref')

            self.tra_ft_energysources_railway_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_ELECTRICAL, 'elec_railway_ref')
            self.tra_ft_energysources_road_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_ELECTRICAL, 'elec_road_ref')
            self.tra_ft_energysources_ship_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_ELECTRICAL, 'elec_ship_ref')
            self.tra_ft_energysources_flight_electrical = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_ELECTRICAL, 'elec_flight_ref')
            self.tra_ft_energysources_railway_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_HYDROGEN, 'hydrogen_railway_ref')
            self.tra_ft_energysources_road_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_HYDROGEN, 'hydrogen_road_ref')
            self.tra_ft_energysources_ship_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_HYDROGEN, 'hydrogen_ship_ref')
            self.tra_ft_energysources_flight_hydrogen = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_FREIGHT_TRAFFIC_HYDROGEN, 'hydrogen_flight_ref')

        # Timeseries
        self.timeseries_loading = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_TRAFFIC_TIMESERIES, 'timeseries_LoadingProfile') #'timeseries' -> 'timeseries_Beladungsprofil' oder 'timeseries_Mobilitätsprofil' 
        self.timeseries_mobility = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_TRAFFIC_TIMESERIES, 'timeseries_MobilityProfile')
        #self.tra_timeseries_railway = load_excel.load_excel_sheet(FILE.FILE_PATH_INPUT_DATA_TRAFFIC, FILE.FILENAME_INPUT_TRAFFIC_TIMESERIES, 'rail_holeweek')

        if CTRL.IND_ACTIVATED == False:

            self.steel_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Steel_Production.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
            self.alu_prim_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Aluminium_Production.xlsx"),sheet_name=["Prim_Data"],skiprows=0)["Prim_Data"]
            self.alu_sec_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Aluminium_Production.xlsx"),sheet_name=["Sec_Data_const"],skiprows=0)["Sec_Data_const"]
            self.cement_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Cement_Production.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
            self.paper_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Paper_Production.xlsx"),sheet_name=["Data"],skiprows=0)["Data"]
            self.ammonia_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Ammonia_Production.xls"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
            self.glass_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Glass_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
            self.chlorin_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Chlorin_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
            
            self.aromate_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Aromate_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
            self.ethylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Ethylene_Production.xls"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
            self.methanol_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Methanol_Production.xls"),sheet_name=["Data_const"],skiprows=0)["Data_const"]
            self.propylene_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Propylene_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]

            self.mais_table = pd.read_excel(os.path.join(FILE.FILE_PATH_INPUT_DATA_INDUSTRY, "Mais_Production.xlsx"),sheet_name=["Data_const"],skiprows=0)["Data_const"]

