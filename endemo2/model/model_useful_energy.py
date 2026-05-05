import pandas as pd
import itertools
from endemo2.model.model_final_energy import get_matches

def calculate_useful_energy(data):
    """
    Calculate useful energy as ECU * sum(DDet[Technology][Type]) for each subsector,
    for each combination of DDet, Technology, and Type.
    """
    general_settings = data.input_manager.general_settings
    effiency_fe = data.efficiency_data[0].forecast # List of Variable objects for FE [var_ef, var_share] always given by user
    forecast_year_range = general_settings.forecast_year_range
    forecast_year_range = [str(year) for year in forecast_year_range]
    for region in data.regions:
        region_name = region.region_name
        ue_region = []
        for sector in region.sectors:
            sector_name = sector.name
            ue_per_sector = []
            for subsector in sector.subsectors:
                # Gather region-level results for this subsector
                ecu = subsector.ecu
                technologies = subsector.technologies
                subsector_name = subsector.name
                ue_per_subsectors = []
                for technology in technologies:
                    technology_name = technology.name
                    ddets = technology.ddets  # list of dddet variables per technology
                    ue_per_technology = calculate_ue(ecu, ddets, forecast_year_range, subsector_name,
                                                          technology_name, sector_name, region_name,effiency_fe)
                    technology.energy_ue = ue_per_technology
                    ue_per_subsectors.append(ue_per_technology)
                ue_per_subsector = pd.concat(ue_per_subsectors, ignore_index=True)
                subsector.energy_ue = ue_per_subsector
                ue_per_sector.append(ue_per_subsector)
            ue_sector = pd.concat(ue_per_sector, ignore_index=True)
            sector.energy_ue = ue_sector
            ue_region.append(ue_sector)
        ue_per_region = pd.concat(ue_region, ignore_index=True)
        region.energy_ue = ue_per_region


def calculate_ue(ecu, ddets, forecast_year_range,
                 subsector_name, technology_name, sector_name, region_name, effiency_fe):
    """
    Calculate useful energy for each Technology dynamically.
    """
    ecu.forecast.columns = ecu.forecast.columns.astype(str)
    ecu_values = ecu.forecast[forecast_year_range].iloc[0] if not ecu.forecast.empty else pd.Series(1,index=forecast_year_range)
    # Prepare DDet DataFrames and ECU values
    ddets_dfs = []
    for ddet in ddets:
        df = ddet.forecast.copy()
        df.columns = df.columns.astype(str)
        if 'FE_Type' in df.columns and df['FE_Type'].notna().any():
            df = calc_eu_for_defined_fe(df, effiency_fe,forecast_year_range) # sum over the fe_type for the defined ue_type
        ddets_dfs.append(df)
    ddet_combined = pd.concat(ddets_dfs, ignore_index=True)
    # Process temperature levels for HEAT type
    dfs_heat_q, dfs_with_total_type = process_temp_levels(ddet_combined)
    ddet_combined = dfs_with_total_type
    #Check if Subtech/Drive have non-default values
    valid_groups = identify_valid_groups(ddet_combined)
    #  Compute ue for each valid group
    ue_entries = []
    for group in valid_groups:
        ue_type = group['UE_Type']
        subtech = group['Subtech']
        drive = group['Drive']
        # Filter applicable rows (include defaults)
        mask = (
                ((ddet_combined['UE_Type'] == ue_type) | (ddet_combined['UE_Type'] == 'default')) &
                ((ddet_combined['Subtech'] == subtech) | (ddet_combined['Subtech'] == 'default')) &
                ((ddet_combined['Drive'] == drive) | (ddet_combined['Drive'] == 'default'))
        )
        applicable_ddet = ddet_combined[mask]
        if applicable_ddet.empty:
            continue
        # Compute product of applicable rows
        product = applicable_ddet[forecast_year_range].prod()
        ue_values = ecu_values * product
        # Create entry
        entry = {
            "Region": region_name,
            "Sector": sector_name,
            "Subsector": subsector_name,
            "Technology": technology_name,
            "UE_Type": ue_type,
            "Temp_level": "TOTAL",
            "Subtech": subtech if subtech is not None else "default",
            "Drive": drive if drive is not None else "default",
        }
        entry.update(ue_values.to_dict())
        ue_entries.append(entry)
        if ue_type == "HEAT" and not all(df.empty for df in dfs_heat_q):
            combined_heat = pd.concat(dfs_heat_q, ignore_index=True)
            for _, heat_row in combined_heat.iterrows():
                temp_level = heat_row["Temp_level"]
                heat_values = heat_row[forecast_year_range] * ue_values
                temp_entry = {
                    "Region": region_name,
                    "Sector": sector_name,
                    "Subsector": subsector_name,
                    "Technology": technology_name,
                    "UE_Type": "HEAT",
                    "Temp_level": temp_level,
                    "Subtech": subtech if subtech is not None else "default",
                    "Drive": drive if drive is not None else "default",
                }
                temp_entry.update(heat_values.to_dict())
                ue_entries.append(temp_entry)
    return pd.DataFrame(ue_entries)


def process_temp_levels(dfs_with_type):
    """Split DDet DataFrames into total heat and temperature-specific entries."""
    dfs_heat_q = []
    dfs_with_total_type = []
    total_mask = dfs_with_type["Temp_level"].fillna("").astype(str) == "TOTAL"
    total_df = dfs_with_type[total_mask]
    level_df = dfs_with_type[~total_mask]
    if not total_df.empty:
        dfs_with_total_type.append(total_df)
        dfs_with_total_type = pd.concat(dfs_with_total_type, ignore_index=True)
    if not level_df.empty:
        dfs_heat_q.append(level_df)

    return dfs_heat_q, dfs_with_total_type


def identify_valid_groups(ddet_combined):
    """
    - Case 1: Explicitly defined Subtech/Drive (non-default). person earth
    - Case 2: Subtech/Drive are defaults (apply to all combinations). all others
    - Case 3: UE_Type and Drive are non-default (primary grouping keys).eg Fright air
    :param ddet_combined:
    :return:
    """
    non_default_ue = (ddet_combined['UE_Type'] != 'default').any()
    non_default_subtech = (ddet_combined['Subtech'] != 'default').any()
    non_default_drive = (ddet_combined['Drive'] != 'default').any()
    #  Identify valid groups based on case detection
    if non_default_ue and non_default_subtech and non_default_drive:
        # Case 1: All three columns have non-default values
        # Group by UE_Type-Drive pairs and expand with Subtechs
        ue_drive_pairs = (
            ddet_combined[
                (ddet_combined['UE_Type'] != 'default') &
                (ddet_combined['Drive'] != 'default')
                ][['UE_Type', 'Drive']]
            .drop_duplicates()
        )
        # Extract non-default Subtech values
        subtechs = ddet_combined.loc[ddet_combined['Subtech'] != 'default', 'Subtech'].unique().tolist()
        # Generate valid groups as a list of dictionaries
        valid_groups = []
        for _, pair in ue_drive_pairs.iterrows():
            for subtech in subtechs:
                valid_groups.append({
                    'UE_Type': pair['UE_Type'],
                    'Subtech': subtech,
                    'Drive': pair['Drive']
                })
    elif non_default_ue and not non_default_subtech and not non_default_drive:
        # Case 2: Only UE_Type is non-default
        ue_types = ddet_combined['UE_Type'].unique().tolist()
        valid_groups = [
            {'UE_Type': ut, 'Subtech': 'default', 'Drive': 'default'}
            for ut in ue_types if ut != 'default'
        ]

    elif non_default_ue and non_default_drive and not non_default_subtech:
        # Case 3: UE_Type and Drive are non-default, Subtech is default
        ue_drive_pairs = (
            ddet_combined[
                (ddet_combined['UE_Type'] != 'default') &
                (ddet_combined['Drive'] != 'default')
                ][['UE_Type', 'Drive']]
            .drop_duplicates()
        )
        valid_groups = [
            {'UE_Type': pair['UE_Type'], 'Subtech': 'default', 'Drive': pair['Drive']}
            for _, pair in ue_drive_pairs.iterrows()
        ]
    else:
        # Fallback: Handle mixed cases or edge scenarios, generating all combinations of UE_Type, Subtech, and Drive.
        ue_types = ddet_combined.loc[ddet_combined['UE_Type'] != 'default', 'UE_Type'].unique().tolist()
        subtechs = ddet_combined['Subtech'].unique().tolist()
        drives = ddet_combined['Drive'].unique().tolist()
        valid_groups = [
            {'UE_Type': ut, 'Subtech': st, 'Drive': dr}
            for ut, st, dr in itertools.product(ue_types, subtechs, drives)
        ]
    return valid_groups


def calc_eu_for_defined_fe(df, efficiency_fe, forecast_year_range):
    """
    Calculate EU for defined FE types by grouping by UE_type and applying efficiency factors
    Args:
        df (pd.DataFrame): Input DataFrame with energy data
        efficiency_fe (pd.DataFrame): DataFrame with efficiency factors
        forecast_year_range (list): List of year columns to calculate
    Returns:
        pd.DataFrame: Aggregated results with summed values by UE_type combined with heat quantities
    """
    dfs_heat_q, dfs_with_total_type = process_temp_levels(df)
    # Define the matching keys
    matching_keys = ['Region', 'Sector', 'Subsector', 'Technology', 'UE_Type',
                     'FE_Type', 'Temp_level', 'Subtech', 'Drive']
    group_keys = ['Region', 'Sector', 'Subsector', 'Variable', 'Technology', 'UE_Type',
                  'Temp_level', 'Subtech', 'Drive']
    results = []
    # Group by UE_type and process each group
    for ue_type, group in dfs_with_total_type.groupby('UE_Type', observed=True):
        group_results = []
        for _, row in group.iterrows():
            eff_row = get_matches(efficiency_fe, row.to_dict(), matching_keys)
            eff_row.columns = eff_row.columns.astype(str)
            if not eff_row.empty:
                if len(eff_row) > 1:
                    eff_row = eff_row.iloc[0]
                    print(" FE_efficiencies are given twice for one type of share")
                calculated = row[forecast_year_range] * eff_row[forecast_year_range]
                new_row = row.copy().to_frame().T
                new_row[forecast_year_range] = calculated.values
                new_row['FE_Type'] = None  # Or np.nan if preferred
                group_results.append(new_row)
        if group_results:
            group_df = pd.concat(group_results, ignore_index=True)
            # Sum while preserving all non-year columns
            if len(group_df) <= 1:
                summed = group_df  # Return the row directly
            else:
                summed = group_df.groupby(group_keys, as_index=False)[forecast_year_range].sum()
            results.append(summed)
    # Combine results with dfs_heat_q if results exist
    if results:
        if not all(df.empty for df in dfs_heat_q):
            selected_cols = group_keys + forecast_year_range
            selected_dfs = [df[selected_cols] for df in dfs_heat_q if not df.empty]
            results.extend(selected_dfs)
        final_result = pd.concat(results, ignore_index=True)
        return final_result







