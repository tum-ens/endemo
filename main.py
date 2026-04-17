"""
This module is used to start the Useful Energy Demand Model ENDEMO.
"""
import sys

# Disable Python bytecode cache files (__pycache__) for this run.
sys.dont_write_bytecode = True

from endemo2.endemo import Endemo
import warnings
import numpy as np
from numpy.polynomial.polyutils import RankWarning


# numpy>=2.x no longer exposes RankWarning at the top level, so we import it from polyutils.
warnings.simplefilter('ignore', RankWarning)
warnings.simplefilter('ignore', UserWarning)

model = Endemo()
model.execute_with_preprocessing()
