import pandas as pd

def calc_fe_types(energy_ue, eff_forecast, share_forecast, forecast_year_range):

    """
    Calculate final energy by:
    1. First finding matching share records
    2. Then finding efficiency records with matching UE_Type+FE_Type
    :param forecast_year_range:
    :param energy_ue: region obj containing useful energy per region
    :param eff_forecast: DataFrame containing FE efficiency conversion variables
    :param share_forecast: DataFrame containing FE share variables
    :return: DataFrame containing final energy calculations for the technology
    """
    # Define the key columns to match
    keys = ['Region', 'Sector', 'Subsector', 'Technology', 'UE_Type',
            'Temp_level', 'Subtech', 'Drive']
    results = []
    # Iterate through each row in region_ue DataFrame
    for _, ue_row in energy_ue.iterrows():
        # Get matches from both variables using the same filtering
        share_matches = get_matches(share_forecast, ue_row, keys)
        if len(share_matches) == 0:
            continue
        # For each share match, find corresponding efficiencies
        for _, share_row in share_matches.iterrows():
            # Create search row with FE_Type from share record
            search_row = ue_row.copy()
            search_row['FE_Type'] = share_row['FE_Type']
            # Find matching efficiency (must match UE_Type and FE_Type)
            ef_match = get_matches(eff_forecast, search_row, keys + ['FE_Type'])
            if len(ef_match) > 1:
                print(f"{ef_match}\n error double efficiency found: {ue_row}")
                ef_match = ef_match.iloc[0]  # Take the first match just to check if problem is here
            elif len(ef_match) == 0: # means that there is no share for that effinency
                print(f"share_row: {share_row}\n no efficiency for that FE_Type for ue row: {ue_row}")
                continue
            fe_values = (
                ue_row[forecast_year_range]
                .mul(share_row[forecast_year_range])
                .div(ef_match[forecast_year_range])
            )
            result = {
                **ue_row[keys].to_dict(),
                'FE_Type': share_row['FE_Type'],
                **fe_values.squeeze().to_dict()  # TODO as the last multiplication as df we got index as 2d
            }
            results.append(result)
    return pd.DataFrame(results)

def get_matches(source_df, row, keys):
    """
    Returns rows from source_df that match all keys in `row`,
    prioritizing exact matches and falling back to 'default' only if no exact match exists.
    Args:
        source_df (pd.DataFrame): DataFrame to filter
        row (dict): Dictionary containing key-value pairs to match
        keys (list): List of columns to match against
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    # First try to find exact matches for all keys
    exact_mask = pd.Series(True, index=source_df.index)
    for key in keys:
        row_value = row.get(key)
        exact_mask &= (source_df[key] == row_value)
    exact_matches = source_df[exact_mask]
    # If exact matches exist, return them
    if not exact_matches.empty:
        return exact_matches
    # Otherwise, fall back to 'default' for missing values
    fallback_mask = pd.Series(True, index=source_df.index)
    for key in keys:
        row_value = row.get(key)
        fallback_mask &= (
                (source_df[key] == row_value) |
                (source_df[key] == 'default')
        )
    return source_df[fallback_mask]









