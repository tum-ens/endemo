###############################################################################                                                                                   
# User set and control paramters
###############################################################################
"""The module initiates the user input of the control file.

"""
###############################################################################

###############################################################################
#Imports
###############################################################################

import pandas as pd

class CONTROL():

    # General settable parameters
    FORECAST_YEAR = 2050 #2050 # FORECAST_YEAR
    CONSIDERED_COUNTRIES = ["Belgium", "Bulgaria", "Czechia", "Denmark", "Germany", 
                "Ireland", "Greece", "Spain", "France", "Croatia", "Italy", #
                "Latvia", "Luxembourg", "Hungary", "Netherlands", "Austria", 
                "Poland", "Portugal", "Romania", "Slovenia", "Slovakia", 
                "Finland", "Sweden", "United Kingdom", "Norway", "Switzerland",#
                "Montenegro", "North Macedonia", "Albania", "Serbia", 
                "Bosnia and Herzegovina", "Iceland"]
    # for developers to include in the list ["Luxembourg", "Kosovo", "Estonia", "Lithuania"]
    #print("for Liechtenstein no GDP information jet")
    IGNORED_COUNTRIES = [] # for population
    GERMAN_STATES = ["BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV", "NS", "NW", "RP", "SL", "ST", "SN", "SH", "TH"] #for Population
    
    ## Activate and deactivate main sectors
    IND_ACTIVATED = False
    HH_ACTIVATED = False
    TRA_ACTIVATED = True
    CTS_ACTIVATED = False
    POP_ACTIVATED = True
    ACTIVATE_TIMESERIES = False
    NUTS2_ACTIVATED = False
    
    ACTIVATE_CHAINED_GDP = True 
    NUTS2_CLASSIFICATION = "2016" # 2021 for 2016
    GRAPHICAL_OUTPUT_ACTIVATED = True

  
    # Industry [IND]
    
    # Main settable parameters in industry
    IND_SUBECTORS = ["steel", "alu_prim", "alu_sec", "chlorin", "methanol", "ethylene","propylene","aromate", "paper", "cement", "ammonia", "glass", "steel_direct"] # material
    IND_FOOD = []#["Cereals", "Rice", "Pulses", "Roots", "Brassiacas", "Leafy","Tomatoes", "Cucumbers","Watermelons","Tuber", "Strawberries", "Pome", "Peaches", "Plums", "Tropics", "Nuts", "Citrus", "Grapes"]
    IND_SUBECTORS = IND_SUBECTORS + IND_FOOD
    IND_VOLUM_PROGNOS = "Trend" # "U-shape" or "Trend"
    IND_PRODUCTION_QUANTITY_PER_CAPITA = True
    IND_CALC_SPEC_EN_TREND = True
    IND_H2_SUBSTITUTION_OF_HEAT = 0 # if =1 then max. possibl substitution of heat with hydrogen
    IND_NUTS2_INST_CAP_ACTIVATED = False
    IND_SKIP_YEARS = [2009] 
    IND_SKIP_YEARS_IN_GRAPHIC = True

    
    IND_ACTIVATE_TIME_TREND_MODEL = False 
    IND_END_YEAR = 2019
    if IND_VOLUM_PROGNOS == "Trend":
        if IND_ACTIVATE_TIME_TREND_MODEL == True:
            print("Invalid user input. TIME_TREND_MODEL disactivated in trend prognosis!")
            # !! write warning
            IND_ACTIVATE_TIME_TREND_MODEL = False
    volume_percent_def = 100
    volume_percent_steel_direct = 60; volume_percent_steel = 100 - volume_percent_steel_direct
    volume_percent_chemicals = 100; 
    spec_vol_trend_def = 0
    spec_vol_trend_ammonia = -0.23; spec_vol_trend_glass = 0.33;
    spec_vol_trend_ethylene = -0.27; spec_vol_trend_methanol = 0;
    spec_vol_trend_propylene = 0; spec_vol_trend_aromate = 0;  spec_vol_trend_chlorin = 0;
    #spec_vol_trend_ammonia = 1; spec_vol_trend_glass = 0.33;
    #spec_vol_trend_ethylene = 1; spec_vol_trend_methanol = 1;
    #spec_vol_trend_propylene = 1; spec_vol_trend_aromate = 1;  spec_vol_trend_chlorin = 1;
    #spec_vol_trend_steel = -0.8; spec_vol_trend_cement = -0.1; spec_vol_trend_paper = 0.1; spec_vol_trend_alu = 2; # kupfer, kalk, chlorin, ethylen 
    IND_REST_PROGRESS = 0.7
    IND_ENDEMAND_SHEET=["Insgesamt", "Feste fossile Brennstoffe", "Synthetische Gase", "Erdgas", "Oel", "Erneuerbare Energien", "Abfaelle", "Elektrizitaet", "Waerme"]
    #IND_HEAT_Q2 = 0.13; IND_HEAT_Q3 = 0.15
    #IND_HEAT_Q4 = 1 - (IND_HEAT_Q2 + IND_HEAT_Q3)

    
    #Household
    HH_HEAT_Q1 = 0.45
    HH_HEAT_EFH = 0.83115 
    HH_METHOD_REST = "trend" #or "trend"

    # Traffic [TRA]
    TRA_REFERENCE_YEAR_PRODUCTION_HIS = 2018
    TRA_MODALSPLIT_MODELTYPE = "Trend" # choose Constant (reference year 2018) or Trend
    TRA_INDUSTRY_REST = False
    TRA_SCENARIO_SELECTION_MODALSPLIT = "Historical" # bei EU ref ist TRA_MODALSPLIT_MODELTYPE = Trend zu setzen; eine andere Möglichkeit ist "Historical" (für historical kann TRA_MODALSPLIT_MODELTYPE = Trend oder Constant genutzt werden)
    #TRA_UNIT_SELECTION = "TWh" #choose between PJ and TWh
    #TRA_UNIT_SELECTION = "TWh" #choose between PJ and TWh

    # Selection of scenarios for electrical and hydrogen

    #Tra_timeseries_single = False # time series for every treffic type_ True if only total False

    #traffic set and control: Szenarienentwicklung mit Änderung der Energieeffizienz und des Modalsplits

    # Commercial, trade and services [CTS]
    
    # Main settable parameters in CTS
    CTS_CONT_SPEC_EN = True
    CTS_NUTS2_PER_POP = False    
    CTS_SKIP_YEARS = [] 
    CTS_SKIP_YEARS_IN_GRAPHIC = True 
    
    CTS_END_YEAR = 2019 
    CTS_ENDEMAND_SHEET=["Insgesamt", "Feste fossile Brennstoffe", "Synthetische Gase", "Erdgas", "Oel", "Erneuerbare Energien", "Abfaelle", "Elektrizitaet", "Waerme"]
    CTS_HEAT_Q1 = 0.5
    CTS_HEAT_Q2 = 1 - CTS_HEAT_Q1
    
    
    # General: just for developers
    ## Select a scenario
    SCENARIO = "reference"  # also later hydrogen, efficience
    ENERGYCARRIER = ["Elec", "H2", "Heat"]
    
    if (IND_ACTIVATED == False) or (HH_ACTIVATED == False) or (TRA_ACTIVATED == False) or (CTS_ACTIVATED == False):
        GRAPHICAL_OUTPUT_ACTIVATED = False
    SECTORS_ACTIVATED = []
    if IND_ACTIVATED == True:
        SECTORS_ACTIVATED = pd.DataFrame([["IND"]], \
            ).append(SECTORS_ACTIVATED, ignore_index=True) 
    if HH_ACTIVATED == True:
        SECTORS_ACTIVATED = pd.DataFrame([["HH"]], \
            ).append(SECTORS_ACTIVATED, ignore_index=True)
    if CTS_ACTIVATED == True:
        SECTORS_ACTIVATED = pd.DataFrame([["CTS"]], \
            ).append(SECTORS_ACTIVATED, ignore_index=True)
    if TRA_ACTIVATED == True:
        SECTORS_ACTIVATED = pd.DataFrame([["TRA"]], \
            ).append(SECTORS_ACTIVATED, ignore_index=True)