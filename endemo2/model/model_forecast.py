import pandas as pd
import logging
import numpy as np
from endemo2.model import prediction_methods as pm
from endemo2.model.method_map import  forecast_methods_map
from endemo2.data_structures.enumerations import ForecastMethod

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def do_forecast(data):
    """
    Process ECU and DDet variables to prepare coefficients and generate predictions.
    """
    for region in data.regions:
        for sector in region.sectors:
            for subsector in sector.subsectors:
                # Process ECU Variable
                forecast_data(subsector.ecu, data) #subsector.ecu = variable instance
                # Process DDet Variables under Technologies
                for technology in subsector.technologies:
                    for variable in technology.ddets:
                        forecast_data(variable, data)
    if data.input_manager.general_settings.FE_marker == 1:
        for variable in data.efficiency_data:
            forecast_data(variable,data) #TODO entry building should be changed
    else:
        forecast_data(data.efficiency_data[0], data)

def forecast_data(variable,data):
    """
    Generate predictions based on historical or user data.
    """
    forecast_year_range = data.input_manager.general_settings.forecast_year_range
    forecast = []
    calc_coef = []  #objects with coef for the region
    interpolations = [] #objects with intp points for the region
    if variable.historical is not None and not variable.historical.empty:
        coefficients = calc_coeff_hist(variable,data) # coefficients: list of coef objetcs
        calc_coef.extend(coefficients)
    if variable.user is not None and not variable.user.empty:
        coefficients, interpolation_list = process_user(variable,data)
        calc_coef.extend(coefficients)
        interpolations.extend(interpolation_list)
    # Generate predictions
    if calc_coef:
        predictions_df = do_predictions(calc_coef,variable,data,forecast_year_range)
        forecast.append(predictions_df)
    if interpolations:
        interpolation_df = do_interpolation(interpolations, variable,data,forecast_year_range)
        forecast.append(interpolation_df)
    if forecast:
        forecast = pd.concat(forecast, ignore_index=False)
        variable.forecast = forecast

def process_user(variable,data):
    """
    Process user data for a region, identifying coefficients and future projections.
    :return: list of coef objects containing the calculated coefficients or known interpolation points.
    """
    user_data = variable.user
    coefficients_list = []  # To store coefficients for all rows
    interpolation_list = []
    # Process each row of user_data
    for index, row in user_data.iterrows():
        method = pm.Method()
        row = row.to_frame().T
        row.columns = row.columns.map(str)
        row = clean_dataframe(row)
        region_name = variable.region_name
        if variable.region_name is None: # it is done since we directly create the variable object, not as the hierarchical part.
            method.efficiency_variable = 1
            method.region = get_df_value(row, 'Region')
            method.sector = get_df_value(row, 'Sector')
            method.subsector = get_df_value(row, 'Subsector')
            method.tech = get_df_value(row, 'Technology')
            method.fe_type = get_df_value(row, 'FE_Type')
        ue_type = get_df_value(row, 'UE_Type')
        if ue_type is None :
            ue_type = "default"
        method.ue_type = ue_type
        if "FE_Type" in row.columns:
            method.fe_type = row["FE_Type"].iloc[0]  # Get first value if column exists
        else:
            method.fe_type = None
        method.temp_level  = get_df_value(row, 'Temp_level')
        if method.temp_level  ==  "default" :
            method.temp_level = "TOTAL"
        method.subtech = get_df_value(row, 'Subtech')
        method.drive = get_df_value(row, 'Drive')
        method.equation = get_df_value(row, 'Equation')
        method.extract_forecast_settings(row)
        # Extract relevant keys for coefficients and years
        coef_keys = [col for col in row.columns if isinstance(col, str) and col.startswith('k')]
        year_keys = [str(col) for col in row.columns if isinstance(col, str) and col.isdigit()]
        # Extract coefficients for the row #TODO we can do priorty here which one is first coef or years projections
        if coef_keys:
            method.coefficients = extract_user_given_coefficients(row, coef_keys)
            coefficients_list.append(method)
        # Extract future projections for the row
        elif year_keys:
            if len(year_keys) > 1:
                row_future_data = row[year_keys]
                method.interp_points = process_future_projections(row_future_data, region_name, method.demand_drivers_names, data)
                interpolation_list.append(method)
            else:
                method.coefficients = [row[year_keys].iloc[0].values]
                method.name = ForecastMethod.CONST
                coefficients_list.append(method)
    return coefficients_list, interpolation_list

def calc_coeff_hist(variable, data):
    """
    Calculate coefficients from historical data and demand drivers.
    :param data:
    :param variable: obj.
    :return: Coefficient object.
    """
    key_columns = ["UE_Type","FE_Type", "Temp_level","Subtech","Drive"]
    historical_data = variable.historical
    settings = variable.settings
    valid_keys = [col for col in key_columns if col in historical_data.columns and col in settings.columns]
    coefficients_list = []  # To store coef objects for all rows that we cna do the predictions
    for index, row in historical_data.iterrows():
        method = pm.Method()
        row = row.to_frame().T
        row.columns = row.columns.map(str)
        row_set = settings # in case when we have only 1 settings row
        if valid_keys:
            #extarcting needed settings for processing row:
            merged_df = settings.merge(row, on=valid_keys, how='inner')
            # Identify columns with _x and _y suffix
            merged_df = merged_df.rename(columns=lambda x: x.rstrip('_x'))  # Remove `_x`
            merged_df = merged_df.rename(columns=lambda x: x.rstrip('_y'))  # Remove `_y`
            # Drop duplicate columns (since `_x` and `_y` were merged into a single name)
            merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
            row_set = clean_dataframe(merged_df)
        ue_type = get_df_value(row_set, 'UE_Type')
        if ue_type is None:
            ue_type = "default"
        method.ue_type = ue_type
        if "FE_Type" in row_set.columns:
            method.fe_type = row_set["FE_Type"].iloc[0]  # Get first value if column exists
        else:
            method.fe_type = None
        method.temp_level = get_df_value(row, 'Temp_level')
        if method.temp_level == "default":
            method.temp_level = "TOTAL"
        method.subtech = get_df_value(row_set, 'Subtech')
        method.drive = get_df_value(row_set, 'Drive')
        method.equation = get_df_value(row_set, 'Equation')
        method.extract_forecast_settings(row_set)
        row = clean_dataframe(row)
        # Separate year columns from non-year columns
        year_columns = [col for col in row.columns if str(col).isdigit()]  # Identify valid year columns
        if not year_columns:
            raise ValueError(f"No valid year columns found in historical data for {variable.region_name}.")
        # Ensure year columns are integers
        year_columns_list = list(map(int, year_columns))
        # Set the non-year columns as index temporarily for mapping the DDr data
        row = row[year_columns] # only timeseries data for the row
        # Get filtered demand driver data
        demand_driver_data = map_filtered_demand_driver_data(method.demand_drivers_names, year_columns_list, variable.region_name,data)
        # Align historical data with demand driver years
        filtered_years = demand_driver_data.index.tolist()
        common_years = sorted(set(filtered_years).intersection(year_columns_list))  # Find common years
        if not common_years:
            print(f"No common years between demand drivers and historical data for {variable.region_name} with the set {row_set}/"
                f"forecast method changed to the const_last")
            method.forecast_method = ForecastMethod.CONST_LAST
            last_year = str(year_columns_list[-1])
            historical_values = [row[last_year].iloc[0]]
            demand_driver_array = np.array([])# empty array for Ddrs as we use const_last no matetr
        else:
            common_years = list(map(str, common_years))
            # Filter historical data and demand driver data to only include common years
            historical_values = row[common_years].iloc[0].values.tolist()  # Select region and years
            common_years = list(map(int, common_years))
            demand_driver_array = demand_driver_data.loc[common_years].values  # Align demand driver data numpy arrray
        # Pass the filtered data and aligned demand driver data for coefficient calculation
        method = calculate_coef_for_filtered_data(
            values=historical_values,
            demand_driver_data=demand_driver_array,
            method= method,
            row = row,
            variable =variable
        )
        coefficients_list.append(method)
    return coefficients_list

def calculate_coef_for_filtered_data(values, demand_driver_data, method, row, variable) -> pm.Method:
    """
    Calculate coefficients for the given values and demand driver data using the specified forecast method.

    :param values: List of y-values (dependent variable).
    :param demand_driver_data: 2D array of x-values (independent variables).
    :param method: The Forecast method object specifying which method to use for coefficient generation.
    :return: A Coef object containing the calculated coefficients.

    """
    forecast_method = method.name
    # Check if the forecast method exists in the map
    if forecast_method not in forecast_methods_map:
        print(f"Warning: Forecast method '{forecast_method}' is not recognized. Using 'CONST_LAST' as fallback.")
        forecast_method = ForecastMethod.CONST_LAST
    method.name = forecast_method
    # Retrieve the method details from the map
    method_details = forecast_methods_map[forecast_method]
    generate_coef = method_details["generate_coef"]
    min_points = method_details["min_points"]
    # Validate the number of data points
    if len(values) < min_points:
        print(
                f"Warning: Insufficient data points for '{variable.region_name}'. Minimum required: {min_points}.\n"
                f"the variable '{variable.name}'.\n"
                f"Forecast method changed to const_last, given points: {len(values)}"
        )
        method.name = ForecastMethod.CONST_LAST
    try:
        # Ensure demand_driver_data is a 2D array #case when we will have a single DDr
        if len(demand_driver_data.shape) == 1:
            demand_driver_data = demand_driver_data.reshape(-1, 1)
        # Generate coefficients using the mapped function anad save
        method.coefficients ,method.equation = generate_coef(X=demand_driver_data, y=values)
        return method
    except Exception as e:
        print(f"Error generating coefficients for method '{forecast_method}': {e}.\n"
              f"the row '{row}'"
              )
        return method

def map_filtered_demand_driver_data(demand_drivers_names, years, region_name,data):
    aligned_DDr_df = pd.DataFrame(index=years)
    for driver_name in demand_drivers_names:
        if driver_name == "TIME":
            aligned_DDr_df["TIME"] = years
            continue
        driver_data_object = data.get_demand_driver(driver_name)
        if not driver_data_object:
            print(f"Demand driver '{driver_name}' object  not found.")
            aligned_DDr_df[driver_name] = np.nan
            continue
        region_data = driver_data_object.get_data_for_region(region_name)
        if region_data is not None and not region_data.empty:
            filtered_values = _filter_values_by_year(region_data, years)
            aligned_DDr_df[driver_name] = filtered_values
        else:
            print(f"No data for demand driver '{driver_name}' in region '{region_name}'.")
            aligned_DDr_df[driver_name] = np.nan
    return aligned_DDr_df.dropna()

def process_future_projections(row_future_data, region_name, demand_driver_names,
                               data):
    """
    Prepare future data for interpolation
    :param demand_driver_names: name of Ddrs
    :param region_name: name of processed region
    :param row_future_data: df year,value.
    :param data: obj containing the ddr data.
    :return: Coef object with interpolation points.

    """
    # Extract years and values from future_data
    years = list(map(int, row_future_data.columns))
    demand_driver_data = map_filtered_demand_driver_data(demand_driver_names, years, region_name,data)
    filtered_years = demand_driver_data.index.astype(int)
    common_years = sorted(set(filtered_years).intersection(years))  # Find common years
    if not common_years:
        raise ValueError(
            f"No common years between demand drivers and historical data for {region_name}")
    common_years = list(map(str, common_years))
    # Filter historical data and demand driver data to only include common years
    future_values = row_future_data[common_years].iloc[0].values.tolist()  #  value of the function [f1,f2,...]
    common_years = list(map(int, common_years))
    demand_driver_array = demand_driver_data.loc[common_years].values  # Coordinates of the function [[x1,x2,...],...] 2d array
    known_points = [
        tuple(coord) + (value,)
        for coord, value in zip(demand_driver_array, future_values)
    ]  # list of tuples of known points [(x1,x2,..., f1), ...]
    interp_points = known_points
    return interp_points

def extract_user_given_coefficients(row: pd.DataFrame, coef_keys: list):
    """
    Extract user-provided coefficients from the data and return them as a list.
    :param row: DataFrame containing user data with coef and set.
    :param coef_keys: List of columns representing coefficients (e.g., 'k0', 'k1').
    :return: List of coefficients in the order of coef_keys.
    """
    coefficients = []
    for coef_key in coef_keys:
        try:
            if coef_key in row.columns:
                value = row.iloc[0][coef_key]
                coefficients.append(float(value))
            else:
                logging.warning(f"Coefficient key {coef_key} not found in user data columns.")
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid or missing value for coefficient {coef_key} in user data: {e}")
    return coefficients

def do_predictions(predictions_method: list, variable,data,forecast_year_range) -> pd.DataFrame:
    """
    Make predictions for a range of years using the specified forecast method.

    :param predictions_method: list of Coef object containing the regression coefficients.
    :param variable: obj.
    :return: A DataFrame with predictions.
    Args:
        data:
        forecast_year_range:
    """
    region_name = variable.region_name
    hierarchy = variable.get_hierarchy()
    region_predictions_df_list = []
    for method in predictions_method:
        # Retrieve the prediction function from the forecast map
        method_details = forecast_methods_map[method.name]
        demand_drivers = method.demand_drivers_names
        predict_function = method_details.get("predict_function")
        if not predict_function:
            raise ValueError(f"Prediction function not defined for forecast method: {method.name}")
        # Generate X_values for all years
        predictions = {}
        for year in forecast_year_range:
            try:
                x_values = map_x_values(demand_drivers, region_name, year, data)
                predicted_value = predict_function(method, x_values)
                if predicted_value < method.lower_limit:
                    predictions[year] = method.lower_limit
                else:
                    predictions[year] = predicted_value
            except Exception as e:
                logging.error(f"Error predicting for {region_name}, year {year}: {e}")
                predictions[year] = pd.NaT  # Default to NaN for errors
        # Structure the DataFrame
        scaled_predictions = {year: value * method.factor for year, value in predictions.items()} #scale by factor to get standard values
        region_data = {
            "Sector": [hierarchy["Sector"]],
            "Region": region_name,
            "Subsector": [hierarchy["Subsector"]],
            "Variable": [variable.name],
            "Technology": [hierarchy["Technology"]],
            "Coefficients/intp_points": [method.coefficients],
            "Equation": [method.equation],
            "UE_Type": [method.ue_type],
            "FE_Type": [method.fe_type],
            "Factor": [method.factor],
            "Temp_level": [method.temp_level],
            "Subtech": [method.subtech],
            "Drive": [method.drive],
            **scaled_predictions
        }
        if method.efficiency_variable == 1 :
            entry = {
                "Region": [method.region],
                "Sector": [method.sector],
                "Subsector": [method.subsector],
                "Technology": [method.tech],
                "FE_Type": [method.fe_type],
            }
            region_data.update(entry)
        region_predictions_df_list.append(pd.DataFrame(region_data))
    return pd.concat(region_predictions_df_list, ignore_index=False)

def do_interpolation(interpolations, variable, data, forecast_year_range) -> pd.DataFrame:
    """
    do interpolations for a range of years using the specified forecast method.
    :param interpolations: list of method object containing the known interpolation obj.
    :param variable: obj.
    :return: A DataFrame with predictions.
    """
    region_name = variable.region_name
    hierarchy  = variable.get_hierarchy()
    region_interpolations_df_list = []
    for method in interpolations:
        # Retrieve the prediction function from the forecast map
        method_details = forecast_methods_map[method.name]
        predict_function = method_details.get("predict_function")
        if not predict_function:
            raise ValueError(f"Prediction function not defined for forecast method: {method.name}")
        # Generate X_values for all years
        predictions = {}
        interp_points = method.interp_points
        for year in forecast_year_range:
            try:
                x_values = map_x_values(method.demand_drivers_names, region_name, year, data) #points where the interp are needed
                predicted_value = predict_function(interp_points, x_values)
                if predicted_value <= method.lower_limit:
                    predictions[year] = method.lower_limit
                else:
                    predictions[year] = predicted_value
            except Exception as e:
                logging.error(f"Error interpolating for {region_name}, {variable.settings} , year {year}: {e}")
                predictions[year] = pd.NaT # Default to NaN for errors suche when the dot is out of interp boundarries
        # Structure the DataFrame
        scaled_predictions = {year: value * method.factor for year, value in predictions.items()}
        region_data = {
            "Sector": [hierarchy["Sector"]],
            "Region": region_name,
            "Subsector": [hierarchy["Subsector"]],
            "Variable": [variable.name],
            "Technology": [hierarchy["Technology"]],
            "Coefficients/intp_points": [method.interp_points],
            "Equation": [method.equation],
            "UE_Type": [method.ue_type],
            "FE_Type": [method.fe_type],
            "Factor": [method.factor],
            "Temp_level": [method.temp_level],
            "Subtech": [method.subtech],
            "Drive": [method.drive],
            **scaled_predictions
        }
        if method.efficiency_variable == 1 :
            entry = {
                "Region": [method.region],
                "Sector": [method.sector],
                "Subsector": [method.subsector],
                "Technology": [method.tech],
                "FE_Type": [method.fe_type],
            }
            region_data.update(entry)
        region_interpolations_df_list.append(pd.DataFrame(region_data))
    return pd.concat(region_interpolations_df_list, ignore_index=False)

def map_x_values(demand_drivers, region_name, year, data):
    """
    Maps demand drivers to their respective values for a specified region and year in the future.

    :param data:obj containing future values of the defined DDr
    :param demand_drivers: List of demand driver names.
    :param region_name: Name of the region.
    :param year: Year for which the values are to be fetched.
    :return: List of values corresponding to the demand drivers for the specified region and year.
    """
    x_values = []
    for driver in demand_drivers:
        if driver == "TIME":
            x_values.append(float(year))
        else:
            DDr = data.get_demand_driver(driver)
            if DDr:
                region_data = DDr.get_data_for_region(region_name)
                if region_data is not None and not region_data.empty:
                    # Extract the value for the specified year
                    region_data.columns = region_data.columns.map(str).str.strip() # Normalize columns
                    if str(year) in region_data.columns:
                        value = region_data[str(year)].iloc[0]
                        x_values.append(float(value) if not pd.isna(value) else np.nan)  # Handle NaN as is
                    else:
                        logging.warning(
                            f"Year {year} not found in data for driver '{driver}' in region '{region_name}'.")
                        x_values.append(np.nan)  # Use NaN for missing years
                else:
                    logging.warning(f"No data found for region '{region_name}' in driver '{driver}'.")
                    x_values.append(np.nan)  # Use NaN for missing regions
            else:
                logging.warning(f"No data found for demand driver '{driver}' in region '{region_name}'.")
                x_values.append(np.nan)  # Use NaN for missing drivers
    return x_values

def _filter_values_by_year(region_data: pd.DataFrame, years: list) -> list:
    """
    Filter region data to extract values corresponding to specified years.

    :param region_data: DataFrame containing region-specific demand driver data.
    :param years: List of years to filter the data by.
    :return: List of values corresponding to the specified years.
    """
    # Ensure column names are strings to handle year columns
    region_data.columns = region_data.columns.map(str)

    # Find matching year columns
    matching_columns = [str(year) for year in years if str(year) in region_data.columns]

    if not matching_columns:
        print(f"Warning: None of the specified years '{years}' found in the data columns.")
        return []
    # Extract values for the matching years
    filtered_values = region_data.iloc[0][matching_columns].astype(float).tolist()
    return filtered_values

def clean_dataframe(df):
    if df is None:
        return df
    # Drop rows/columns with all NaN values
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return df

def get_df_value(row, column_name):
    """extract a value from a row, handling missing columns or NaN values."""
    if column_name in row.columns:
        value = row[column_name].iloc[0]
        return value if not pd.isna(value) else "default"
    return "default"

