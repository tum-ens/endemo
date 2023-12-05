###############################################################################                                                                                   
# Chair:            Chair of Renewable and Sustainable Energy Systems (ENS)
# Programm title:   Energy demand model (endemo)
# Assistant(s):     Larissa Breuning (larissa.breuning@tum.de)/
#                   Andjelka Kerekes (andelka.bujandric@tum.de) 
#                   

# Date:             in progress
# Version:          v3.0
# Status:           in progress
# Python-Version:   3.7.3 (64-bit)
###############################################################################
"""The module calculates the forecast energy demand for a defined geographical 
    area. The spatial resolution is limited to the Nuts2 level. The result 
    output includes the energy-related sectors (households; industry; traffic; 
    commerce, trade and services).
"""
###############################################################################
# Import libraries
###############################################################################

# Import functions that are already available in Python libraries.
import pandas as pd
import csv
import matplotlib.pyplot as plt
import numpy as np
from xlrd import open_workbook
import matplotlib as mpl
import os 
import logging
import math
from pathlib import Path

# Import functions that are implemented project-specifically.
import calc_industry_sector
import calc_commercial_trade_and_services as calc_cts_sector
import calc_household_sector
import calc_traffic_sector
import load_excel
import get_set_and_control_parameters
import get_data_locations
import get_prepar_input_data
import postprocess_output_data

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)

###############################################################################
# Paths and filenames
###############################################################################

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# User Input: Enter the storage location of the model here (without "endemo" folder)

FILE_PATH_USER_SPECIFIC = Path(os.path.dirname(__file__)).parent
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

###############################################################################
# Set and control parameters and data locations
###############################################################################

# Terminal display.
SPACE = "-"*79
logger.info(SPACE)
logger.info("Initialize: Set and control parameters & data locations")

CTRL = get_set_and_control_parameters.CONTROL()
FILE = get_data_locations.LOCATIONS(FILE_PATH_USER_SPECIFIC, CTRL.FORECAST_YEAR, 
    logger)

###############################################################################
# Main
###############################################################################

# The individual sector models are set up in the main program. Each sector 
# model can also be implemented as a stand-alone model.

#------------------------------------------------------------------------------
# Initiate and prepare input data.

logger.info(SPACE)
logger.info("Initialize: Data (IND, CTS, HH, CTS, TRA, GEN)")
gen_data, ind_data, cts_data, hh_data, tra_data = get_prepar_input_data.in_data(CTRL, FILE)

#------------------------------------------------------------------------------
# Industry.

logger.info(SPACE)
logger.info("Processing: Industry")

if CTRL.IND_ACTIVATED == True:
    ind_sol = calc_industry_sector.start_calc(CTRL, FILE, ind_data, gen_data)
elif CTRL.IND_ACTIVATED == False:
    ind_sol = 1

#------------------------------------------------------------------------------
# Commercial trade and services.

logger.info(SPACE)
logger.info("Processing: Commercial trade and services")

if CTRL.CTS_ACTIVATED == True:  
    cts_sol = calc_cts_sector.start_calc(CTRL, FILE, cts_data, gen_data)
elif CTRL.CTS_ACTIVATED == False:
    cts_sol = 1

#------------------------------------------------------------------------------
# Households.

logger.info(SPACE)
logger.info("Processing: Households")

if CTRL.HH_ACTIVATED == True:
    hh_sol = calc_household_sector.start_calc(CTRL, FILE, hh_data, gen_data)
elif CTRL.HH_ACTIVATED == False:
    hh_sol = 1

#------------------------------------------------------------------------------
# Traffic.

logger.info(SPACE)
logger.info("Processing: Traffic")

if CTRL.TRA_ACTIVATED == True:
    tra_sol = calc_traffic_sector.start_calc(CTRL, FILE, tra_data, gen_data, ind_data)
elif CTRL.TRA_ACTIVATED == False:
    tra_sol = 1

#------------------------------------------------------------------------------
# Output at postprocessing of output data.

logger.info(SPACE)
logger.info("Output: Data (IND, HH, CTS, TRA, GEN)")
postprocess_output_data.out_data(CTRL, FILE, ind_sol, hh_sol, cts_sol, tra_sol, gen_data.gen_abbreviations)

#------------------------------------------------------------------------------
# Final information

logger.info(SPACE)
logger.info("Main: demand model run finished.")
logger.info(SPACE)