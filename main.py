"""
This module is used to start the Useful Energy Demand Model ENDEMO.
"""
from endemo2.endemo import Endemo
import warnings
import numpy as np


warnings.simplefilter('ignore', np.RankWarning)
warnings.simplefilter('ignore', UserWarning)

model_instance = Endemo()
model_instance.execute_with_preprocessing()

# execute this after changes to settings to restart the model but not execute preprocessing again
# model_instance.execute_without_preprocessing()

