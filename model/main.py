###############################################################################                                                                                   
# Chair:            Chair of Renewable and Sustainable Energy Systems (ENS)
# Programm title:   Energy demand model (endemo)
# Assistant(s):     Larissa Breuning (larissa.breuning@tum.de)/
#                   Andjelka Kerekes (andelka.bujandric@tum.de) 
#                   

# Date:             
# Version:          v3.0
# Status:           done
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
from libraries import *
from pathlib import Path

# Import functions that are implemented project-specifically.
import calc_industry_sector
import calc_commercial_trade_and_services as calc_cts_sector
import calc_household_sector
import calc_traffic_sector
import get_set_and_control_parameters
import get_prepare_output_locations
import get_prepare_input_data
import postprocess_output_data

# Creation of the logger to show information on the display.
logger = logging.getLogger(__name__)
level = logging.DEBUG
logging.basicConfig(level=level)
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

###############################################################################
# Main path
# Set and control parameters and data locations
###############################################################################

FILE_PATH = Path(os.path.dirname(__file__)).parent

# Terminal display.
SPACE = "-"*79
logger.info(SPACE)
logger.info("Initialize: Set and control parameters & data locations")

CTRL = get_set_and_control_parameters.CONTROL(FILE_PATH)
FILE = get_prepare_output_locations.LOCATIONS(FILE_PATH, CTRL.FORECAST_YEAR, CTRL.REF_YEAR, CTRL.IND_VOLUM_PROGNOS, logger)

###############################################################################
# Initiate and prepare input data
###############################################################################

logger.info(SPACE)
logger.info("Initialize: Data (IND, CTS, HH, TRA, GEN)")
gen_data, ind_data, cts_data, hh_data, tra_data = get_prepare_input_data.in_data(CTRL, FILE)

###############################################################################
# Main
###############################################################################
# The individual sector models are set up in the main program. Each sector 
# model can also be implemented as a stand-alone model.


# Industry.
logger.info(SPACE)
logger.info("Processing: Industry")

if CTRL.IND_ACTIVATED:
    ind_sol = calc_industry_sector.start_calc(CTRL, FILE, ind_data, gen_data)
else:
    ind_sol = 1

#------------------------------------------------------------------------------
# Commercial trade and services.
logger.info(SPACE)
logger.info("Processing: Commercial trade and services")

if CTRL.CTS_ACTIVATED:  
    cts_sol = calc_cts_sector.start_calc(CTRL, FILE, cts_data, gen_data)
else:
    cts_sol = 1

#------------------------------------------------------------------------------
# Households.
logger.info(SPACE)
logger.info("Processing: Households")

if CTRL.HH_ACTIVATED:
    hh_sol = calc_household_sector.start_calc(CTRL, FILE, hh_data, gen_data)
else:
    hh_sol = 1

#------------------------------------------------------------------------------
# Traffic.
logger.info(SPACE)
logger.info("Processing: Traffic")

if CTRL.TRA_ACTIVATED:
    tra_sol = calc_traffic_sector.start_calc(CTRL, FILE, tra_data, gen_data, ind_data)
else:
    tra_sol = 1

#------------------------------------------------------------------------------
# Output at postprocessing of output data.

logger.info(SPACE)
logger.info("Output: Data (IND, HH, CTS, TRA, GEN)")
postprocess_output_data.out_data(CTRL, FILE, ind_sol, hh_sol, cts_sol, tra_sol)

#------------------------------------------------------------------------------
# Final information

logger.info(SPACE)
logger.info("Main: demand model run finished.")
logger.info(SPACE)