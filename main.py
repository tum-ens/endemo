"""
This module is used to start the Useful Energy Demand Model ENDEMO.
"""
from endemo2.endemo import Endemo
import warnings
import numpy as np


warnings.simplefilter('ignore', np.RankWarning)
warnings.simplefilter('ignore', UserWarning)

model = Endemo()
model.execute_with_preprocessing()


