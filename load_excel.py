import pandas as pd
import os 

def load_excel_sheet(filepath, filename, sheetname):
    path = os.path.join(filepath, filename)
    sheet = pd.read_excel(path, sheet_name=sheetname)
    return sheet 


