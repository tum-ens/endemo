import pandas as pd
from endemo2.input_and_settings.input_region_sect_sub import Region, Sector, Subsector, Variable, Technology, \
 DataManager

def initialize_hierarchy_input_from_settings_data(input_manager):
    """
       Initialize hierarchy input using settings data for active sectors.

       Parameters:
           input_manager : obj that contain all setting parameters for model execution.
       Returns:
           None
       """
    data = DataManager(input_manager) # class that holds all necessary data DDr, input, Efficiencies
    active_sectors = input_manager.general_settings.active_sectors
    active_regions = input_manager.general_settings.active_regions
    region_code_map = input_manager.general_settings.region_code_map
    sectors_settings = input_manager.general_settings.sectors_settings # dictionary that holds sector settings of the Set_and_contol file as dfs
    input_data_paths = input_manager.sector_paths
    timeseries_forecast = input_manager.general_settings.timeseries_forecast
    ue_type_list = get_useful_energy_types(input_manager)
    heat_levels_list = get_temp_levels(input_manager)
    hist_data, user_set_data = load_sector_data(input_data_paths)
    hist_data, user_set_data = filter_sector_data(hist_data, user_set_data, ue_type_list, heat_levels_list)
    # extract the DDr that are used in the current model running
    unique_ddr_names = extract_unique_ddr_values(user_set_data) #TODO DDr changes starts here
    data.read_all_demand_drivers(unique_ddr_names) #TODO DDr changes starts here
    # Pre-filter data for sectors
    sector_hist_data = {
        sector: hist_data[hist_data["Sector"] == sector]
        for sector in active_sectors
    }
    sector_user_data = {
        sector: user_set_data[user_set_data["Sector"] == sector]
        for sector in active_sectors
    }
    if timeseries_forecast == 1:
        timeseries = pd.read_excel(input_manager.timeseries_file, sheet_name="Data",header=None).set_index(0)
        data.read_and_filter_load_profiles(timeseries)
    #intilaization of the region objects
    for region_name in active_regions:
        # create the region object
        code = region_code_map[region_name]
        region = Region(region_name=region_name, country_code=code) #TODO add DDrs as region attribute
        #region.DDR_data = get_DDr_data_for_region(hist, user_data)
        for sector_name in active_sectors:
            sector = Sector(name=sector_name)
            sector.settings = sectors_settings[sector_name]
            # Get pre-filtered data
            hist_data_by_sector = sector_hist_data[sector_name]
            user_set_data_by_sector = sector_user_data[sector_name]
            for subsector_name, row in sector.settings.iterrows():
                # Initialize Subsector
                subsector = Subsector(name=subsector_name)
                # Get technologies, ensuring "default" exists if no technologies are provided
                technology_names = parse_technologies(row)
                # Process ECU of the subsector
                ecu_name = row.get("ECU")
                # Process DDet Variables
                ddet_columns = {col: row[col] for col in row.index if col.startswith("DDet") and pd.notna(row[col])}
                ddet_names = list(ddet_columns.values())
                subsector_variables = [ecu_name] + ddet_names  # the first element always ecu
                for index, variable_name in enumerate(subsector_variables):
                    if index == 0:  # ECU Variable
                        # Populate ECU regions
                        variable = map_region_data(region_name = region_name,
                                                   variable_name = variable_name,
                                                   hist_data=hist_data_by_sector,
                                                   user_set_data=user_set_data_by_sector,
                                                   subsector_name=subsector_name)
                        subsector.add_ecu(variable)
                    else:  # DDet Variables
                        for tech_name in technology_names:
                            # Check if there is any data for the current variable and technology # for exampl Subdrive DDet in TRA
                            variable_user_df = user_set_data_by_sector[
                                (user_set_data_by_sector["Variable"] == variable_name) &
                                (user_set_data_by_sector["Subsector"] == subsector_name) &
                                (user_set_data_by_sector["Technology"].isin([tech_name, "default"]))
                                ]
                            if variable_user_df.empty:  # Skip if there is no data for this technology
                                continue
                            # Get or create Technology
                            technology = next(
                                (tech for tech in subsector.technologies if tech.name == tech_name),
                                None)
                            if not technology:
                                technology = Technology(name=tech_name)
                                subsector.add_technology(technology)
                            # Populate variable for the specific technology
                            variable = map_region_data(region_name = region_name,
                                                       variable_name = variable_name,
                                                       hist_data=hist_data_by_sector,
                                                       user_set_data=user_set_data_by_sector,
                                                       tech_name=tech_name,
                                                       subsector_name=subsector_name)
                            if timeseries_forecast == 1:
                                technology.load_profile = data.get_load_profiles(region_name,sector_name,subsector_name,tech_name) #get the list of loadprofile objects related to the tech
                            technology.add_variable(variable)
                    # Add Subsector to Sector
                sector.add_subsector(subsector)
            region.add_sector(sector)
        data.add_region(region)

    fe_type_list = get_final_energy_types(input_manager)
    user_set_data_filtered = user_set_data[user_set_data['FE_Type'].isin(fe_type_list)]
    fe_dfs = {
        "EFFICIENCY": user_set_data_filtered[user_set_data_filtered["Variable"] == "EFFICIENCY"],
        "FE_SHARE_FOR_UE": user_set_data_filtered[user_set_data_filtered["Variable"] == "FE_SHARE_FOR_UE"]
    }
    data.load_efficiency_data(fe_dfs)
    return data

def map_region_data(region_name, variable_name, hist_data, user_set_data, subsector_name, tech_name=None):
    """
    Populate region-specific data for a given variable based on active regions and technology.

    Args:
        region_name (str) : The region name to populate variable.
        subsector_name (str) : The subsector name to populate variable.
        variable_name (str) : The variable name to populate.
        hist_data (pd.DataFrame): Historical data for the sector.
        user_set_data (pd.DataFrame): User-set data for the sector.
        tech_name (str, optional): Filter by technology name. Defaults to None.
    """
    # Filter by technology if it is given
    variable = Variable(variable_name)
    variable.region_name = region_name
    if tech_name:
        user_set_data = user_set_data[user_set_data["Technology"].isin([tech_name, "default"])]
        hist_data = hist_data[hist_data["Technology"].isin([tech_name, "default"])]
    # Filter user-set data by variable name, active regions, and (optionally) technology
    variable_user_df = user_set_data[(user_set_data["Variable"] == variable_name) & (user_set_data["Subsector"] == subsector_name)]
    # Filter historical data by variable name, active regions, and (optionally) technology
    variable_hist_df = hist_data[(hist_data["Variable"] == variable_name) & (hist_data["Subsector"] == subsector_name)]
    settings_columns = [
                           col for col in
                           ["Region", "UE_Type","FE_Type", "Temp_level","Subtech","Drive", "Unit", "Factor", "Function", "Equation", "Forecast data", "Lower limit"]
                           if col in variable_user_df.columns
                       ] + [col for col in variable_user_df.columns if str(col).startswith("DDr")]

    filter_columns = ["UE_Type","FE_Type","Temp_level","Subtech","Drive"]
    # Filter default rows
    default_set_rows = variable_user_df[variable_user_df["Region"] == "default"]
    default_hist_rows = variable_hist_df[variable_hist_df["Region"] == "default"]
    variable_set_df = variable_user_df[settings_columns]

    # Get region-specific settings
    region_set_df = get_region_data(variable_set_df,region_name,default_set_rows, filter_columns)
    variable.settings = region_set_df
    filtered_list = [col for col in filter_columns if col in region_set_df.columns]

    if any(col in region_set_df.columns for col in filtered_list):
        # Separate historical and user-set data for all types
        historical_rows = region_set_df[region_set_df["Forecast data"] == "Historical"]
        user_rows = region_set_df[region_set_df["Forecast data"] != "Historical"]
        if not historical_rows.empty:
            filter_keys = [col for col in filtered_list if
                          col in historical_rows.columns and col in variable_hist_df.columns]
            # Extract existing region data based on filter keys
            region_types_levels = historical_rows[filter_keys]
            # Filter user data for the specific region
            hist_data_region = variable_hist_df[
                (variable_hist_df["Region"] == region_name) &
                variable_hist_df[filter_keys].apply(tuple, axis=1).isin(region_types_levels.apply(tuple, axis=1))
                    ]
            # Identify missing row combinations (not just Type, but all keys)
            missing_combinations = region_types_levels.apply(tuple, axis=1)[
                    ~region_types_levels.apply(tuple, axis=1).isin(hist_data_region[filter_keys].apply(tuple, axis=1))
                ]

            # Get missing data from the "default" region (based on missing row combinations)
            if not missing_combinations.empty:
                default_data = variable_hist_df[
                    (variable_hist_df["Region"] == "default") &
                    variable_hist_df[filter_keys].apply(tuple, axis=1).isin(missing_combinations)
                    ]
                hist_data_region = pd.concat([hist_data_region, default_data], ignore_index=True)

            variable.historical = hist_data_region if not hist_data_region.empty else None
        if not user_rows.empty:
            filter_keys = [col for col in filtered_list if
                               col in user_rows.columns and col in variable_user_df.columns]
            # Extract existing region data based on filter keys
            region_types_levels = user_rows[filter_keys]

            # Filter user data for the specific region
            user_data_region = variable_user_df[
                    (variable_user_df["Region"] == region_name) &
                    variable_user_df[filter_keys].apply(tuple, axis=1).isin(region_types_levels.apply(tuple, axis=1))
                ]

            # Identify missing row combinations (not just Type, but all keys)
            missing_combinations = region_types_levels.apply(tuple, axis=1)[
                    ~region_types_levels.apply(tuple, axis=1).isin(user_data_region[filter_keys].apply(tuple, axis=1))
            ]
            # Get missing data from the "default" region (based on missing row combinations)
            if not missing_combinations.empty:
                default_data = variable_user_df[
                    (variable_user_df["Region"] == "default") &
                    variable_user_df[filter_keys].apply(tuple, axis=1).isin(missing_combinations)
                    ]
                user_data_region = pd.concat([user_data_region, default_data], ignore_index=True)

            variable.user = user_data_region if not user_data_region.empty else None
    else:
        # Handle cases without iteration columns
        forecast_data = variable.settings["Forecast data"].iloc[0]
        if forecast_data == "Historical":
            hist_data = get_region_data(variable_hist_df, region_name, default_hist_rows, filtered_list)
            variable.historical = hist_data
        else:
            user_data = get_region_data(variable_user_df, region_name, default_set_rows,filtered_list)
            variable.user = user_data
    return variable


def get_region_data(df, region_name, default_data, filter_columns):
    # Filter for the region
    region_data = df[df['Region'] == region_name].copy()

    # Return default if region not found
    if region_data.empty:
        if default_data.empty:
            return pd.DataFrame([{
                "Region": region_name,
                "Coefficients/intp_points": "None",
                "Equation": "None",
                "UE_Type": "None",
                "Factor": "None",
                "2000": 0,
            }])
        return clean_dataframe(default_data)

    # Only proceed with columns that exist in region_data
    filtered_cols = [col for col in filter_columns if col in region_data.columns]
    if not filtered_cols:
        return clean_dataframe(region_data)

    # Reset indices for clean merging
    default_data = default_data.reset_index(drop=True)
    region_data = region_data.reset_index(drop=True)

    # Handle FE_Type priority logic
    if 'FE_Type' in filtered_cols:
        # Split default data into FE_Type=None and FE_Type≠None
        default_with_fe = default_data[default_data['FE_Type'].notna()]
        default_without_fe = default_data[default_data['FE_Type'].isna()]

        # Step 1: Merge non-None FE_Type rows from default
        merged_fe = default_with_fe.merge(
            region_data, on=filtered_cols, how='left', indicator=True
        )
        missing_fe = merged_fe[merged_fe['_merge'] == 'left_only'].drop(columns='_merge')

        # Step 2: For FE_Type=None rows, exclude those where (UE_Type, Temp_level)
        # already exists in region_data with a non-None FE_Type
        non_null_fe_pairs = region_data[region_data['FE_Type'].notna()] \
            [['UE_Type', 'Temp_level']].drop_duplicates()

        default_without_fe_filtered = default_without_fe.merge(
            non_null_fe_pairs, on=['UE_Type', 'Temp_level'],
            how='left', indicator=True
        ).query('_merge == "left_only"').drop(columns='_merge')

        # Merge remaining FE_Type=None rows
        merged_no_fe = default_without_fe_filtered.merge(
            region_data, on=filtered_cols, how='left', indicator=True
        )
        missing_no_fe = merged_no_fe[merged_no_fe['_merge'] == 'left_only'].drop(columns='_merge')

        # Combine missing rows
        missing_rows = pd.concat([missing_fe, missing_no_fe], ignore_index=True)
    else:
        # Original logic if FE_Type not in filter_columns
        merged = default_data.merge(
            region_data, on=filtered_cols, how='left', indicator=True
        )
        missing_rows = merged[merged['_merge'] == 'left_only'].drop(columns='_merge')

    # Clean and merge missing rows
    if not missing_rows.empty:
        missing_rows.columns = missing_rows.columns.str.replace('_x$', '', regex=True)
        missing_rows = missing_rows[[col for col in missing_rows if not col.endswith('_y')]]

        # Align columns with region_data
        for col in region_data.columns:
            if col not in missing_rows:
                missing_rows[col] = None

        region_data = pd.concat([region_data, missing_rows], ignore_index=True)

    return clean_dataframe(region_data)

def clean_dataframe(df):
    if df is None:
        return df
    # Drop rows/columns with all NaN values
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    return df

def load_sector_data(data_paths):
    # load data file only once for processed sector and save it in the cash to not open it several times after we clear cash
    hist_path = data_paths["hist_path"]
    user_set_path = data_paths["user_set_path"]
    # Use ExcelFileCache to load files
    hist_data =  pd.read_excel(hist_path, sheet_name="Data")
    user_set_data = pd.read_excel(user_set_path, sheet_name="Data")
    # Convert column names to strings
    hist_data.columns = hist_data.columns.astype(str)
    user_set_data.columns = user_set_data.columns.astype(str)
    return hist_data, user_set_data


def get_final_energy_types(input_manager):
    """Extract the list of useful energy types from the input manager settings."""
    fe_type_list = input_manager.general_settings.dropdown_settings['Final Energy Types'][input_manager.general_settings.dropdown_settings['Final Energy Types'].notna()]
    return fe_type_list.tolist() + ["default"]

def get_useful_energy_types(input_manager):
    """Extract the list of useful energy types from the input manager settings."""
    ue_type_list = input_manager.general_settings.dropdown_settings['Useful Energy Types'][input_manager.general_settings.dropdown_settings['Useful Energy Types'].notna()]
    return ue_type_list.tolist()

def get_temp_levels(input_manager):
    """Extract the list of useful energy types from the input manager settings."""
    heat_levels_list = input_manager.general_settings.dropdown_settings['Heat levels'][input_manager.general_settings.dropdown_settings['Heat levels'].notna()]
    return heat_levels_list.tolist()

def filter_sector_data(hist_data, user_set_data, ue_type_list, heat_levels_list):
    """Filter historical and user-set data based on useful energy types and temperature levels."""
    hist_data_filtered = hist_data[
        ((hist_data['UE_Type'].isna()) | (hist_data['UE_Type'].isin(ue_type_list))) &
        ((hist_data['Temp_level'].isna()) | (hist_data['Temp_level'].isin(heat_levels_list)))
    ]
    user_set_data_filtered = user_set_data[
        ((user_set_data['UE_Type'].isna()) | (user_set_data['UE_Type'].isin(ue_type_list))) &
        ((user_set_data['Temp_level'].isna()) | (user_set_data['Temp_level'].isin(heat_levels_list)))
    ]
    return hist_data_filtered, user_set_data_filtered


def extract_unique_ddr_values(user_set_data):
    """
        Extract unique DDr values from user_set_data and add them to demand_driver.global_ddr_values
        if they are not already present.
        Args:
            user_set_data (pd.DataFrame): The DataFrame containing user-set data with DDr columns.
     """
    # Extract columns starting with "DDr"
    columns = [col for col in user_set_data.columns if str(col).startswith("DDr")]
    # Extract unique values from these columns
    unique_ddr_names = pd.unique(user_set_data[columns].values.ravel())
    # Filter out NaN values
    unique_ddr_names = [ddr for ddr in unique_ddr_names if pd.notna(ddr)]
    return unique_ddr_names

def parse_technologies(row):
    """Replicates your exact technology parsing logic with default handling"""
    if "Technology" in row and pd.notna(row["Technology"]) and row["Technology"].strip():
        return [
            tech.strip() if tech.strip() else "default"
            for tech in row["Technology"].split(",")
        ]
    return ["default"]
