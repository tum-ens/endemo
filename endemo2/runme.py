import endemo
import warnings
import numpy as np

warnings.simplefilter('ignore', np.RankWarning)
warnings.simplefilter('ignore', UserWarning)

model_instance = endemo.Endemo()
model_instance.execute_with_preprocessing()