
import pandas as pd
import os

def load_excel_sheet(filepath, filename, sheetname):
    path = os.path.join(filepath, filename)
    sheet = pd.read_excel(path, sheet_name=sheetname)
    return sheet 

year = "2018"

# production_per_land_his_alu = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', 'ProduktionsmengeGüterverkehr.xlsx','Aluminium')

# production_per_land_his_cem = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr.xlsx",'Cement')

# production_per_land_his_glas = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr.xlsx",'Glas')

# production_per_land_his_pa = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr.xlsx",'Paper')

# production_per_land_his_steel = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr.xlsx",'Steel')

production_per_land_his_alu = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', 'ProduktionsmengeGüterverkehr_2030.xlsx','Aluminium')

production_per_land_his_cem = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr_2030.xlsx",'Cement')

production_per_land_his_glas = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr_2030.xlsx",'Glas')

production_per_land_his_pa = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr_2030.xlsx",'Paper')

production_per_land_his_steel = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr_2030.xlsx",'Steel')

Countries = load_excel_sheet(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic', "ProduktionsmengeGüterverkehr.xlsx",'Country')

add = []
for country in range(0, len(Countries)):

    for i_alu in range(0, len(production_per_land_his_alu)):

        print(Countries['Country_engl'][country])
        #print(production_per_land_his_alu["Country"][i_alu])

        if Countries['Country_engl'][country] == production_per_land_his_alu["Country"][i_alu]: 
            alu = production_per_land_his_alu[2018][i_alu]
            break
        else:
            alu = 0

    for i_cem in range(0, len(production_per_land_his_cem)):

        if Countries['Country_engl'][country] == production_per_land_his_cem["Country"][i_cem]:
            cem = production_per_land_his_cem[2018][i_cem]
            break
        else: 
            cem = 0

    for i_glas in range(0, len(production_per_land_his_glas)):

        if Countries['Country_engl'][country] == production_per_land_his_glas["Country"][i_glas]:
            glas = production_per_land_his_glas[2018][i_glas]
            break
        else: 
            glas = 0

    for i_pa in range(0, len(production_per_land_his_pa)):

        if Countries['Country_engl'][country] == production_per_land_his_pa["Country"][i_pa]:
            pa = production_per_land_his_pa[2018][i_pa] 
            break
        else: 
            pa = 0 

    for i_steel in range(0, len(production_per_land_his_steel)):

        if Countries['Country_engl'][country] == production_per_land_his_steel["Country"][i_steel]:
            steel = production_per_land_his_steel[2018][i_steel]
            break
        else: 
            steel = 0


    calc_sum = (alu*1000 + cem*1000 + glas*1000 + pa*1000 + steel*1000) 
                                          
    add.append([Countries['Country_engl'][country], calc_sum])

production = pd.DataFrame(add)
#production.to_excel(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic\Productionvolume_historical.xlsx', index=False)
production.to_excel(r'N:\Projekte\IPP\08 Daten\Nachfrage\Nachfragemodell\endemo\input\traffic\Productionvolume_single_2050.xlsx', index=False)

print('finished.')

