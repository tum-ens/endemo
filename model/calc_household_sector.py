###############################################################################                                                                                   
# Forecast of the household sector
###############################################################################
"""The module calculates the energy demand of the household sector.

The script calculates an energy demand development for the household sector 
based on user-specific inputs. A forecast should be made for the energy sources 
heat and electricity.
"""
###############################################################################
#Imports
###############################################################################
from libraries import *
import subsec_hh_subsectors
from op_methods import *

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

def start_calc(CTRL, FILE, hh_data, gen_data):

    sol = SUBSEC(CTRL, FILE, hh_data, gen_data)

    return sol

class SUBSEC():

    def __init__(self, CTRL, FILE, hh_data, gen_data):
        
        #------------------------------------------------------------------------------
        logger.info(" - Preprocessing (characterizing) households")
        self.hh_data_forecast = subsec_hh_subsectors.datapreproces(CTRL, FILE, hh_data, gen_data)
        #------------------------------------------------------------------------------
        logger.info(" - Space heating")
        self.hh_sh = subsec_hh_subsectors.spaceheating(CTRL, FILE, hh_data, gen_data, self.hh_data_forecast)

        #------------------------------------------------------------------------------
        logger.info(" - Hot water")
        self.hh_hw = subsec_hh_subsectors.hotwater(CTRL, FILE, hh_data, gen_data)

        #------------------------------------------------------------------------------
        logger.info(" - Cooking")
        self.hh_co = subsec_hh_subsectors.cooking(CTRL, FILE, hh_data, gen_data)

        #------------------------------------------------------------------------------
        logger.info(" - Lighting and electrical appliances")
        self.hh_liandap = subsec_hh_subsectors.lighting(CTRL, FILE, hh_data, gen_data)

        #------------------------------------------------------------------------------
        logger.info(" - Space cooling")
        self.hh_sc = subsec_hh_subsectors.spacecooling(CTRL, FILE, hh_data, gen_data, self.hh_data_forecast)

        #------------------------------------------------------------------------------
        
        energy_demand_subsector = []
        energy_demand_usefulenergy = []
        energy_demand_finalenergy = []

        for country in CTRL.CONSIDERED_COUNTRIES:

            idx_country = list(self.hh_sh.energy_space_heating["Country"]).index(country)
            energy_demand_subsector.append([country, 
                # per subsector
                self.hh_sh.energy_space_heating["Consumption Prog [TWh]"][idx_country],
                self.hh_hw.energy_hot_water["Consumption Prog [TWh]"][idx_country],
                self.hh_co.energy_cooking["Consumption Prog [TWh]"][idx_country],
                self.hh_sc.energy_cooling["Consumption Prog [TWh]"][idx_country],
                self.hh_liandap.energy_electricity["Consumption Prog [TWh]"][idx_country],
                # total
                self.hh_sh.energy_space_heating["Consumption Prog [TWh]"][idx_country]
                +self.hh_hw.energy_hot_water["Consumption Prog [TWh]"][idx_country]
                +self.hh_co.energy_cooking["Consumption Prog [TWh]"][idx_country]
                +self.hh_sc.energy_cooling["Consumption Prog [TWh]"][idx_country]
                +self.hh_liandap.energy_electricity["Consumption Prog [TWh]"][idx_country]])
            
            heating_demand = (self.hh_sh.energy_space_heating["Consumption Prog [TWh]"][idx_country]
                              +self.hh_hw.energy_hot_water["Consumption Prog [TWh]"][idx_country])
            elec_demand = (self.hh_sc.energy_cooling["Consumption Prog [TWh]"][idx_country]
                           +self.hh_co.energy_cooking["Consumption Prog [TWh]"][idx_country]
                           +self.hh_liandap.energy_electricity["Consumption Prog [TWh]"][idx_country])
            # Useful energy
            energy_demand_usefulenergy.append([country, elec_demand, heating_demand, heating_demand + elec_demand])
            
            # Final energy, with hydrogen and electricity substitution of heat
            # Heat at different temperature levels
            idx_level = list(gen_data.efficiency_heat_levels["Energy carrier"]).index("Q1")
            elec_from_heat = ((self.hh_sh.energy_space_heating["Consumption Prog [TWh]"][idx_country]
                              * CTRL.HH_ELEC_IN_SPACEHEAT
                              + self.hh_hw.energy_hot_water["Consumption Prog [TWh]"][idx_country]
                              * CTRL.HH_ELEC_IN_HOTWATER)
                              / gen_data.efficiency_heat_levels["Electricity [-]"][idx_level])
            h2_from_heat = (self.hh_sh.energy_space_heating["Consumption Prog [TWh]"][idx_country]
                            * CTRL.HH_H2_IN_SPACEHEAT
                             / gen_data.efficiency_heat_levels["Hydrogen [-]"][idx_level])
            heat_remaining = ((self.hh_sh.energy_space_heating["Consumption Prog [TWh]"][idx_country]
                             * (1 - CTRL.HH_ELEC_IN_SPACEHEAT - CTRL.HH_H2_IN_SPACEHEAT)
                             + self.hh_hw.energy_hot_water["Consumption Prog [TWh]"][idx_country]
                              * (1- CTRL.HH_ELEC_IN_HOTWATER))
                              / gen_data.efficiency_heat_levels["Fuel [-]"][idx_level]) # for "heat" no efficincy conversion, for "fuel" *1/efficincy
                        
            energy_demand_finalenergy.append([country, elec_demand + elec_from_heat, heat_remaining, h2_from_heat, 
                                                      heat_remaining*CTRL.HH_HEAT_Q1, heat_remaining*(1-CTRL.HH_HEAT_Q1)])
        
        self.energy_demand_subsector = pd.DataFrame(energy_demand_subsector, columns = ["Country", "space heating [TWh]", 
            "hot water [TWh]", "cooking [TWh]", "space cooling [TWh]", "lighting and appliances [TWh]", "total [TWh]"])
        self.energy_demand_usefulenergy = pd.DataFrame(energy_demand_usefulenergy, columns = ["Country",  
            "Electricity [TWh]", "Heat [TWh]", "Total [TWh]"])
        self.energy_demand_finalenergy = pd.DataFrame(energy_demand_finalenergy, columns = ["Country", "Electricity [TWh]", 
            "Heat [TWh]", "Hydrogen [TWh]", "Heat Q1 [TWh]", "Heat Q2 [TWh]"])

        #------------------------------------------------------------------------------
        # NUTS2 distribution          
        if CTRL.NUTS2_ACTIVATED:
            pop_prognosis=pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, FILE.FILENAME_OUTPUT_POPULATION),
                                        sheet_name=["Population_NUTS2", "Population_Countries"],skiprows=0)
    
            hh_energy_demand_NUTS2 = redistribution_NUTS2(CTRL.FORECAST_YEAR, self.energy_demand_finalenergy, pop_prognosis, gen_data.abbreviations)
            result_hh_energy_demand_NUTS2 = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"HH"+FILE.FILENAME_OUTPUT_DEMAND_NUTS2), engine='xlsxwriter')
            hh_energy_demand_NUTS2.to_excel(result_hh_energy_demand_NUTS2,sheet_name="HH", index=False, startrow=0)
            result_hh_energy_demand_NUTS2.close()

            hh_energy_demand_NUTS2_subsector = redistribution_NUTS2(CTRL.FORECAST_YEAR,self.energy_demand_subsector, pop_prognosis, gen_data.abbreviations)
            result_hh_energy_demand_NUTS2 = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA_HOUSEHOLD, FILE.FILENAME_OUTPUT_HH_DEMAND_SUBSECTORS_NUTS2), engine='xlsxwriter')
            hh_energy_demand_NUTS2_subsector.to_excel(result_hh_energy_demand_NUTS2,sheet_name="HH", index=False, startrow=0)
            result_hh_energy_demand_NUTS2.close()

        #------------------------------------------------------------------------------
        # Timeseries for household

        if CTRL.ACTIVATE_TIMESERIES:
            result_energy_profiles = pd.ExcelWriter(os.path.join(FILE.FILE_PATH_OUTPUT_DATA, "HH"+FILE.FILENAME_OUTPUT_TIMESERIES), engine='xlsxwriter')

            if CTRL.NUTS2_ACTIVATED:
                logger.info(" - Timeseries household: NUTS2")

                sheet = pd.read_excel(os.path.join(FILE.FILE_PATH_OUTPUT_DATA,"HH"+FILE.FILENAME_OUTPUT_DEMAND_NUTS2), sheet_name = ["HH"])["HH"]
                consideredcountries = sheet["NUTS2"]
                energy_profiles_df = calc_energy_timeseries(consideredcountries, CTRL, hh_energy_demand_NUTS2, hh_data.timeseries)               

            else:    
                logger.info(" - Timeseries household: Country")
            
                consideredcountries = [country for country in CTRL.CONSIDERED_COUNTRIES]
                energy_profiles_df = calc_energy_timeseries(consideredcountries, CTRL, self.energy_demand_finalenergy, hh_data.timeseries)
                
            energy_profiles_df.to_excel(result_energy_profiles, sheet_name="Load_timeseries", index=False, startrow=0)
            result_energy_profiles.save()
            print("HH finished")
            
        #---------------------------------------------------------------------   

def calc_energy_timeseries(consideredcountries, CTRL, energy_df, load_profile):
    
    # Define and calculate energy series
    energy_timeseries_df = pd.DataFrame({"t":load_profile["t"]})
    print("Calculating energy profiles.")
    for energy_type in load_profile.columns[1:]:

        if energy_type == "Elec":
            energy_type_name = "Electricity [TWh]"
            distribution = 1
            buildingstock = 1

        elif energy_type == "EFH_Heat_Q1":
            energy_type_name = "Heat [TWh]"
            distribution = CTRL.HH_HEAT_Q1
            buildingstock = CTRL.HH_HEAT_EFH

            energy_type2 = "MFH_Heat_Q1"
            distribution2 = CTRL.HH_HEAT_Q1
            buildingstock2 = 1 - CTRL.HH_HEAT_EFH                

        elif energy_type == "EFH_Heat_Q2":
            energy_type_name = "Heat [TWh]"
            distribution = 1 - CTRL.HH_HEAT_Q1
            buildingstock = CTRL.HH_HEAT_EFH

            energy_type2 = "MFH_Heat_Q2"
            distribution2 = 1 - CTRL.HH_HEAT_Q1
            buildingstock2 = 1 - CTRL.HH_HEAT_EFH                

        elif energy_type == "EFH_H2":
            energy_type_name = "Hydrogen [TWh]"
            buildingstock = 1
            distribution = 1

            energy_type2 = "MFH_H2"
            buildingstock2 = 1     
            distribution2 = 1
        
        if energy_type not in ["MFH_Heat_Q1","MFH_Heat_Q2","MFH_H2"]:
            for idx_country, country in enumerate(consideredcountries): 
                if energy_type == "Elec":
                    country_timeseries = list(energy_df[energy_type_name][idx_country] * distribution * buildingstock * np.array(load_profile[energy_type]))
                    country_timeseries_df = pd.DataFrame({country+ "."+energy_type: country_timeseries})
                else:
                    country_timeseries = list(energy_df[energy_type_name][idx_country] * distribution * buildingstock * np.array(load_profile[energy_type])
                                          + energy_df[energy_type_name][idx_country] * distribution2 * buildingstock2 * np.array(load_profile[energy_type2]))
                    country_timeseries_df = pd.DataFrame({country+ "." +energy_type.split("H_")[1]: country_timeseries})                      

                country_timeseries_df.index.name = "t"
                energy_timeseries_df = energy_timeseries_df.merge(country_timeseries_df, on = "t")     

    return energy_timeseries_df
