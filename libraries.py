###############################################################################                                                                                   
# Chair:            Chair of Renewable and Sustainable Energy Systems (ENS)
# Programm title:   Energy demand model (endemo)
# Assistant(s):     Larissa Breuning (larissa.breuning@tum.de)/
#                   Andjelka Kerekes (andelka.bujandric@tum.de) 
#                   

# Date:             in progress
# Version:          v3.0
# Status:           done
# Python-Version:   3.7.3 (64-bit)
###############################################################################
import pandas as pd
import csv
import os
#%matplotlib notebook
import matplotlib.pyplot as plt
import numpy as np
from xlrd import open_workbook
from xlsxwriter.workbook import Workbook
import matplotlib as mpl
import math
from openpyxl import load_workbook


###############################################################################
