from endemo2.endemo import Endemo
import warnings
import numpy as np


warnings.simplefilter('ignore', np.RankWarning)
warnings.simplefilter('ignore', UserWarning)

model_instance = Endemo()
model_instance.execute_with_preprocessing()

