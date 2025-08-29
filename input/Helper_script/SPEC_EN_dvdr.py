import pandas as pd
import os

# Automatically find the Excel file in the current directory
file_name = "spec_en_dvdr.xlsx"
file_path = os.path.join(os.getcwd(), file_name)

# Read settings and data sheets
settings_df = pd.read_excel(file_path, sheet_name='settings')
data_df = pd.read_excel(file_path, sheet_name='Data')

# Identify year columns (numerical)
year_columns = [col for col in data_df.columns if isinstance(col, int)]

# Store results here
results = []

# Process each row in settings
for _, row in settings_df.iterrows():
    dividend_var = row['Dividend']
    divisor_var = row['divisor']
    new_variable = row['Variable']
    sector = row['Sector']
    subsector = row['Subsector']

    # Get matching dividend and divisor rows
    dividend_rows = data_df[(data_df['Variable'] == dividend_var) &
                            (data_df['Sector'] == sector) &
                            (data_df['Subsector'] == subsector)]

    divisor_rows = data_df[(data_df['Variable'] == divisor_var) &
                           (data_df['Sector'] == sector) &
                           (data_df['Subsector'] == subsector)]

    # If either is empty, skip computation
    if dividend_rows.empty or divisor_rows.empty:
        if dividend_rows.empty:
            print(f"missing dividend {dividend_rows} ")
        if divisor_rows.empty:
            print(f"missing dividend {divisor_rows} ")
        continue
    # Since divisor might have multiple variations, loop through each
    for _, div_row in divisor_rows.iterrows():
        for _, dvnd_row in dividend_rows.iterrows():
            # Create a new result row
            result = {
                'Region': dvnd_row['Region'],
                'Sector': sector,
                'Subsector': subsector,
                'Variable': new_variable,
                'Technology': dvnd_row.get('Technology', ''),
                'UE_Type': dvnd_row.get('UE_Type', ''),
                'FE_Type': dvnd_row.get('FE_Type', ''),
                'Temp_level': dvnd_row.get('Temp_level', ''),
                'Subtech': dvnd_row.get('Subtech', ''),
                'Drive': dvnd_row.get('Drive', ''),
                'Unit': f"{dvnd_row['Unit']}/{div_row['Unit']}"
            }

            # Perform division for each year
            for year in year_columns:
                numerator = dvnd_row.get(year, None)
                denominator = div_row.get(year, None)
                try:
                    if pd.notna(numerator) and pd.notna(denominator) and denominator != 0:
                        result[year] = numerator / denominator
                    else:
                        result[year] = None
                except Exception:
                    result[year] = None

            results.append(result)

# Convert to DataFrame
result_df = pd.DataFrame(results)

# Save to Excel if needed
result_df.to_excel("spec_en_employy_output.xlsx", index=False)

print("Processing complete. Output saved as 'spec_en_employy_output.xlsx'.")
