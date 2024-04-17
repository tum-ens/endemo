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
import os
import math

class CONTROL():
    
    def __init__(self, FILE_PATH):
    
        # read set and control data from user input
        settings = pd.read_excel(os.path.join(FILE_PATH, "input", "Set_and_Control_Parameters.xlsx"), sheet_name = None, skiprows=0)
        settings_general = settings["GeneralSettings"]
        settings_IND_general = settings["IND_general"]
        settings_IND_subsector = settings["IND_subsectors"]
    
        # General settable parameters
        self.FORECAST_YEAR = settings_general["Value"][list(settings_general["Parameter"]).index("Forecast year")] # FORECAST_YEAR
        self.REF_YEAR = 2018
        self.CONSIDERED_COUNTRIES = settings["Countries"]["Country"][settings["Countries"]["Active"]==True].tolist()
        
        ## Activate and deactivate main sectors
        self.IND_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Sector: industry")])
        self.HH_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Sector: households")])
        self.TRA_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Sector: transport")])
        self.CTS_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Sector: commertial, trade, services")])
        self.POP_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Population forecast")])
        self.ACTIVATE_TIMESERIES = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Timeseries forecast")])
        self.NUTS2_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("NUTS2 geographical resolution")])
        self.NUTS2_CLASSIFICATION = str(settings_general["Value"][list(settings_general["Parameter"]).index("NUTS2 classification")]) # 2021 or 2016
        self.GRAPHICAL_OUTPUT_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Graphical output")])
        self.FINAL_DEMAND_ACTIVATED = bool(settings_general["Value"][list(settings_general["Parameter"]).index("Calculate final energy demand")])

        # Industry [IND]
        
        # Main settable parameters in industry
        self.IND_SUBECTORS = settings_IND_subsector["Subsectors"][settings_IND_subsector["Active subsectors"]==True].tolist()    
        self.IND_VOLUM_PROGNOS = settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Forecast method")] # "U-shape" or "Trend" or "Exponential"
        self.IND_ACTIVATE_TIME_TREND_MODEL = False #bool(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Time trend model activation for U-shape method")])
        self.IND_PRODUCTION_QUANTITY_PER_CAPITA = bool(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Production quantity calculated per capita")])
        self.IND_CALC_SPEC_EN_TREND = bool(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Trend calculation for specific energy requirements")])
        self.IND_CALC_METHOD = settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Calculation of IND parametres change")]
        self.IND_H2_SUBSTITUTION_OF_HEAT_Q1 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of hydrogen usage for heat supply at Q1 level")])
        self.IND_ELEC_SUBSTITUTION_OF_HEAT_Q1 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of electricity usage for heat supply at Q1 level")])
        self.IND_H2_SUBSTITUTION_OF_HEAT_Q2 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of hydrogen usage for heat supply at Q2 level")])
        self.IND_ELEC_SUBSTITUTION_OF_HEAT_Q2 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of electricity usage for heat supply at Q2 level")])
        self.IND_H2_SUBSTITUTION_OF_HEAT_Q3 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of hydrogen usage for heat supply at Q3 level")])
        self.IND_ELEC_SUBSTITUTION_OF_HEAT_Q3 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of electricity usage for heat supply at Q3 level")])
        self.IND_H2_SUBSTITUTION_OF_HEAT_Q4 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of hydrogen usage for heat supply at Q4 level")])
        self.IND_ELEC_SUBSTITUTION_OF_HEAT_Q4 = float(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Proportion of electricity usage for heat supply at Q4 level")])
        self.IND_NUTS2_INST_CAP_ACTIVATED = bool(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("NUTS2 distribution based on installed industrial capacity")])
        try:
            self.IND_SKIP_YEARS = [int(i) for i in settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Skip years")].split(",")]
        except:
            if math.isnan(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Skip years")]):
                self.IND_SKIP_YEARS = []
            else:
                self.IND_SKIP_YEARS = [settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Skip years")]]
        self.IND_END_YEAR = int(settings_IND_general["Value"][list(settings_IND_general["Parameter"]).index("Last available year")])
        
        if self.IND_VOLUM_PROGNOS == "Trend":
            if self.IND_ACTIVATE_TIME_TREND_MODEL == True:
                logger.warning("Invalid user input. TIME_TREND_MODEL disactivated in trend prognosis!")
                self.IND_ACTIVATE_TIME_TREND_MODEL = False
            
        for industry in self.IND_SUBECTORS:
            setattr(self, "prod_quant_change_" + industry, settings_IND_subsector["Parameter: production quantity change in %/year"][list(settings_IND_subsector["Subsectors"]).index(industry)])
            setattr(self, "spec_demand_improvement_" + industry, settings_IND_subsector["Parameter: efficiency improvement in %/year"][list(settings_IND_subsector["Subsectors"]).index(industry)])
            
            if industry in ["steel_direct", "steel_prim", "steel"]:
                setattr(self, "prod_quant_share_steel_direct", settings_IND_subsector["Parameter: technology substitution in %"][list(settings_IND_subsector["Subsectors"]).index("steel_direct")])
                if "steel_prim" in self.IND_SUBECTORS:
                    # substituiton between steel_prim and DRI
                    # steel_sec development does not depend on DRI
                    setattr(self, "prod_quant_share_steel_prim", 100-getattr(self, "prod_quant_share_steel_direct"))   
                else:
                    # substituiton between total steel production quantity and DRI
                    setattr(self, "prod_quant_share_steel", 100-getattr(self, "prod_quant_share_steel_direct"))
            elif type(settings_IND_subsector["Parameter: technology substitution in %"][list(settings_IND_subsector["Subsectors"]).index(industry)]) in [int, float]:
                setattr(self, "prod_quant_share_" + industry, settings_IND_subsector["Parameter: technology substitution in %"][list(settings_IND_subsector["Subsectors"]).index(industry)])
            else:
                setattr(self, "prod_quant_share_" + industry, 100)
        self.IND_REST_PROGRESS = settings_IND_subsector["Parameter: production quantity change in %/year"][list(settings_IND_subsector["Subsectors"]).index("unspecified industry")]
        
        #Household
        self.HH_HEAT_Q1 = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Predefined ratio of Q1 heat level (below 60°C)")]
        self.HH_HEAT_EFH = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Predefined ratio of single households")]
        self.HH_CALC_METHOD_HH_AREA = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Calculation of parametre change: household surface")]
        self.HH_CALC_METHOD_PER_HH = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Calculation of parametre change: occupants per household")]
        self.HH_CALC_METHOD_SP_HEAT = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Calculation of parametre change: spec. space heating")]
        self.HH_H2_IN_SPACEHEAT = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Proportion of hydrogen usage for space heating")]
        self.HH_ELEC_IN_SPACEHEAT = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Proportion of electricity usage for space heating")]
        self.HH_ELEC_IN_HOTWATER = settings["HH"]["Value"][list(settings["HH"]["Parameter"]).index("Proportion of electricity usage for hot water")]
    
        # Traffic [TRA]
        self.TRA_MODALSPLIT_SCENARIO = settings["TRA"]["Value"][list(settings["TRA"]["Parameter"]).index("Scenario selection for modal split")]
        #If scenario selection = user-defined, the method is not relevant (it will be interpolated between values). If scenario selection = historical => method can be both linear Trend or Constant
        self.TRA_MODALSPLIT_METHOD = settings["TRA"]["Value"][list(settings["TRA"]["Parameter"]).index("Method for modal split")] # Constant (reference year 2018) or Trend
        # Energy distribution on commodities electricity and hydrogen depending on user input settings
        self.TRA_SCENARIO_FINALSOURCES = settings["TRA"]["Value"][list(settings["TRA"]["Parameter"]).index("Scenario selection for final energy demand")]
        self.TRA_INDUSTRY_REST = settings["TRA"]["Value"][list(settings["TRA"]["Parameter"]).index("Calculation for rest subsector")]
        self.TRA_REFERENCE_YEAR_PRODUCTION_HIS = settings["TRA"]["Value"][list(settings["TRA"]["Parameter"]).index("Reference year for industrial production")]
        self.TRA_SKIP_YEARS = []
        self.TRA_END_YEAR = 2020
    
    
        # Commercial, trade and services [CTS]
        self.CTS_CALC_SPEC_EN_TREND = bool(settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Trend calculation for specific energy requirements")])
        self.CTS_NUTS2_PER_POP = bool(settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("NUTS2 distribution based on population")])
        try:
            self.CTS_SKIP_YEARS = settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Skip years")].split(",")
        except:
            if math.isnan(settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Skip years")]):
                self.CTS_SKIP_YEARS = []
            else:
                self.CTS_SKIP_YEARS = [settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Skip years")]]
        
        self.CTS_END_YEAR = int(settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Last available year")])
        self.CTS_HEAT_Q1 = settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Predefined ratio of Q1 heat level (below 60°C)")]
        self.CTS_HEAT_Q2 = 1 - self.CTS_HEAT_Q1
        self.CTS_H2_SUBSTITUTION_OF_HEAT = float(settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Proportion of hydrogen usage for heat supply")])
        self.CTS_ELEC_SUBSTITUTION_OF_HEAT = float(settings["CTS"]["Value"][list(settings["CTS"]["Parameter"]).index("Proportion of electricity usage for heat supply")])

        
        
        # just for developers
        self.ENERGYCARRIER = ["Electricity", "Heat", "Hydrogen"]
        self.ENERGYCARRIER_PROFILE = ["Elec", "Heat", "H2"]
                 
        ## sector specific
        self.IND_EN_DEMAND_SHEET=["Insgesamt", "Feste fossile Brennstoffe", "Synthetische Gase", "Erdgas", "Oel", "Erneuerbare Energien", "Abfaelle", "Elektrizitaet", "Waerme"]
        self.CTS_EN_DEMAND_SHEET=["Insgesamt", "Feste fossile Brennstoffe", "Synthetische Gase", "Torf", "Erdgas", "Oel", "Erneuerbare Energien", "Abfaelle", "Elektrizitaet", "Waerme"]