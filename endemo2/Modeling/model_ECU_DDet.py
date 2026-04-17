import logging
import numpy as np
import pandas as pd

from endemo2.Modeling.Methods import prediction_methods as pm
from endemo2.Modeling.Methods.method_map import forecast_methods_map
from endemo2.Modeling.Methods.prediction_methods import (
    ForecastMethod,
    build_interpolation_points,
    map_forecast_method_to_string,
)
from endemo2.Input.loaders.common import is_default_value, select_rows_with_default

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HIERARCHY_FALLBACK_ORDER = ("Sector", "Subsector", "Region")
CONTEXT_DETAIL_COLUMNS = [
    "Region",
    "Sector",
    "Subsector",
    "Technology",
    "UE_Type",
    "FE_Type",
    "Temp_level",
    "Subtech",
    "Drive",
]

# Caches for DDr row resolution and year-series extraction.
# They only accelerate repeated lookups; forecast logic remains unchanged.
_DDR_RESOLVE_CACHE = {}
_DDR_YEAR_SERIES_CACHE = {}


def reset_driver_mapping_caches():
    """
    Clear all DDr mapping caches.
    """
    _DDR_RESOLVE_CACHE.clear()
    _DDR_YEAR_SERIES_CACHE.clear()


def _get_last_non_nan_year_value(row_df: pd.DataFrame, year_keys):
    ordered_years = sorted((str(year) for year in year_keys), key=int)
    for year in reversed(ordered_years):
        value = pd.to_numeric(row_df[year].iloc[0], errors="coerce")
        if not pd.isna(value):
            return int(year), float(value)
    return None, None


def _fallback_to_const_last_user(method: pm.Method, row_df: pd.DataFrame, year_keys, variable, region_name) -> bool:
    fallback_year, fallback_value = _get_last_non_nan_year_value(row_df, year_keys)
    if fallback_value is None:
        context = _build_context_string(row_df, region_name)
        print(
            f"[Forecast] Not enough interpolation points for '{variable.name}' ({context}). "
            f"No numeric fallback value available. Skipping."
        )
        return False

    method.name = ForecastMethod.CONST_LAST
    method.coefficients = [fallback_value]
    method.equation = "y = const = y(t_hist)"
    context = _build_context_string(row_df, region_name)
    print(
        f"[Forecast] Not enough interpolation points for '{variable.name}' ({context}). "
        f"Falling back to CONST_LAST with value from {fallback_year}: {fallback_value}."
    )
    return True


def calc_ECU_DDet(data):
    """
    Forecast all ECU/DDet variables, plus FE helper inputs if enabled.
    """
    reset_driver_mapping_caches()
    for region in data.regions:
        for sector in region.sectors:
            for subsector in sector.subsectors:
                forecast_data(subsector.ecu, data)
                for technology in subsector.technologies:
                    for variable in technology.ddets:
                        forecast_data(variable, data)

    if data.input_manager.general_settings.FE_marker == 1:
        for variable in data.efficiency_data:
            forecast_data(variable, data)  # TODO entry building should be changed
    else:
        forecast_data(data.efficiency_data[0], data)


def forecast_data(variable, data):
    """
    Generate forecasts for one variable from historical and/or user inputs.
    """
    forecast_year_range = data.input_manager.general_settings.forecast_year_range
    forecast_frames = []
    calculated_methods = []
    interpolation_methods = []

    if variable.historical is not None and not variable.historical.empty:
        coefficients = calc_coeff_hist(variable, data)
        calculated_methods.extend(coefficients)

    if variable.user is not None and not variable.user.empty:
        coefficients, interpolation_list = process_user(variable, data)
        calculated_methods.extend(coefficients)
        interpolation_methods.extend(interpolation_list)

    if calculated_methods:
        predictions_df = do_predictions(calculated_methods, variable, data, forecast_year_range)
        forecast_frames.append(predictions_df)

    if interpolation_methods:
        interpolation_df = do_interpolation(interpolation_methods, variable, data, forecast_year_range)
        forecast_frames.append(interpolation_df)

    if forecast_frames:
        variable.forecast = pd.concat(forecast_frames, ignore_index=False)


def process_user(variable, data):
    """
    Parse user rows into either coefficient-based methods or interpolation methods.
    """
    user_data = variable.user
    coefficients_list = []
    interpolation_list = []

    for _, row in user_data.iterrows():
        method = pm.Method()
        row_df = row.to_frame().T
        row_df.columns = row_df.columns.map(str)
        row_df = clean_dataframe(row_df)

        region_name = variable.region_name
        if variable.region_name is None:
            # Happens for FE helper variables built directly from the input sheet.
            method.efficiency_variable = 1
            method.region = get_df_value(row_df, "Region")
            method.sector = get_df_value(row_df, "Sector")
            method.subsector = get_df_value(row_df, "Subsector")
            method.tech = get_df_value(row_df, "Technology")
            method.fe_type = get_df_value(row_df, "FE_Type")

        method.ue_type = get_df_value(row_df, "UE_Type")
        if "FE_Type" in row_df.columns:
            method.fe_type = row_df["FE_Type"].iloc[0]
        else:
            method.fe_type = None

        method.temp_level = get_df_value(row_df, "Temp_level")
        method.subtech = get_df_value(row_df, "Subtech")
        method.drive = get_df_value(row_df, "Drive")
        method.equation = get_df_value(row_df, "Equation")
        method.extract_forecast_settings(row_df)

        coef_keys = [col for col in row_df.columns if isinstance(col, str) and col.startswith("k")]
        year_keys = [str(col) for col in row_df.columns if isinstance(col, str) and col.isdigit()]

        if coef_keys:
            method.coefficients = extract_user_given_coefficients(row_df, coef_keys)
            coefficients_list.append(method)
            continue

        if not year_keys:
            continue

        if len(year_keys) == 1:
            if _fallback_to_const_last_user(method, row_df, year_keys, variable, region_name):
                coefficients_list.append(method)
            continue

        row_future_data = row_df[year_keys]
        interp_points = build_interpolation_points(row_future_data.iloc[0])

        if len(interp_points) < 2:
            _fallback_to_const_last_user(method, row_future_data, year_keys, variable, region_name)
            if method.name == ForecastMethod.CONST_LAST:
                coefficients_list.append(method)
            continue

        row_future_data = pd.DataFrame({str(y): [v] for y, v in interp_points})
        driver_context = _build_driver_context(variable=variable, method=method, region_name=region_name)
        method.interp_points = process_future_projections(
            row_future_data,
            region_name,
            method.demand_drivers_names,
            data,
            context=driver_context,
        )
        interpolation_list.append(method)

    return coefficients_list, interpolation_list


def calc_coeff_hist(variable, data):
    """
    Calculate coefficients from historical data and matched demand-driver values.
    """
    key_columns = ["UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive"]
    historical_data = variable.historical
    settings = variable.settings
    valid_keys = [col for col in key_columns if col in historical_data.columns and col in settings.columns]

    coefficients_list = []
    for _, row in historical_data.iterrows():
        method = pm.Method()
        row = row.to_frame().T
        row.columns = row.columns.map(str)

        row_set = settings
        if valid_keys:
            merged_df = settings.merge(row, on=valid_keys, how="inner")
            merged_df = merged_df.rename(columns=lambda x: x.rstrip("_x"))
            merged_df = merged_df.rename(columns=lambda x: x.rstrip("_y"))
            merged_df = merged_df.loc[:, ~merged_df.columns.duplicated()]
            row_set = clean_dataframe(merged_df)

        method.ue_type = get_df_value(row_set, "UE_Type")
        if "FE_Type" in row_set.columns:
            method.fe_type = row_set["FE_Type"].iloc[0]
        else:
            method.fe_type = None

        method.temp_level = get_df_value(row, "Temp_level")
        method.subtech = get_df_value(row_set, "Subtech")
        method.drive = get_df_value(row_set, "Drive")
        method.equation = get_df_value(row_set, "Equation")
        method.extract_forecast_settings(row_set)

        row = clean_dataframe(row)
        year_columns = [col for col in row.columns if str(col).isdigit()]
        if not year_columns:
            raise ValueError(f"No valid year columns found in historical data for {variable.region_name}.")

        year_columns_list = list(map(int, year_columns))
        row = row[year_columns]

        driver_context = _build_driver_context(variable=variable, method=method, region_name=variable.region_name)
        demand_driver_data = map_filtered_demand_driver_data(
            method.demand_drivers_names,
            year_columns_list,
            variable.region_name,
            data,
            context=driver_context,
        )

        filtered_years = demand_driver_data.index.tolist()
        common_years = sorted(set(filtered_years).intersection(year_columns_list))
        if not common_years:
            print(
                f"No common years between demand drivers and historical data for {variable.region_name} with the set {row_set}/"
                f"forecast method changed to the const_last"
            )
            method.name = ForecastMethod.CONST_LAST
            last_year = str(year_columns_list[-1])
            historical_values = [row[last_year].iloc[0]]
            demand_driver_array = np.array([])
        else:
            common_years = list(map(str, common_years))
            historical_values = row[common_years].iloc[0].values.tolist()
            common_years = list(map(int, common_years))
            selected_ddr = demand_driver_data.loc[common_years]
            demand_driver_array = selected_ddr.values

        method = calculate_coef_for_filtered_data(
            values=historical_values,
            demand_driver_data=demand_driver_array,
            method=method,
            row=row,
            variable=variable,
        )
        coefficients_list.append(method)

    return coefficients_list


def calculate_coef_for_filtered_data(values, demand_driver_data, method, row, variable) -> pm.Method:
    """
    Calculate coefficients for one method configuration.
    """
    forecast_method = method.name
    if forecast_method not in forecast_methods_map:
        print(f"Warning: Forecast method '{forecast_method}' is not recognized. Using 'CONST_LAST' as fallback.")
        forecast_method = ForecastMethod.CONST_LAST

    method.name = forecast_method
    method_details = forecast_methods_map[forecast_method]
    min_points = method_details["min_points"]
    n_features = 0
    if hasattr(demand_driver_data, "shape"):
        if len(demand_driver_data.shape) == 1:
            n_features = 0 if demand_driver_data.size == 0 else 1
        elif len(demand_driver_data.shape) >= 2:
            n_features = demand_driver_data.shape[1]
    if callable(min_points):
        min_points = min_points(n_features)

    if len(values) < min_points:
        print(
            f"Warning: Insufficient data points for '{variable.region_name}'. Minimum required: {min_points}.\n"
            f"the variable '{variable.name}'.\n"
            f"Forecast method changed to const_last, given points: {len(values)}"
        )
        forecast_method = ForecastMethod.CONST_LAST
        method.name = forecast_method
        method_details = forecast_methods_map[forecast_method]

    generate_coef = method_details["generate_coef"]

    try:
        if len(demand_driver_data.shape) == 1:
            demand_driver_data = demand_driver_data.reshape(-1, 1)
        method.coefficients, method.equation = generate_coef(X=demand_driver_data, y=values)
        return method
    except Exception as e:
        print(
            f"Error generating coefficients for method '{forecast_method}': {e}.\n"
            f"the row '{row}'"
        )
        if forecast_method in {
            ForecastMethod.LOG_SUM,
            ForecastMethod.EXP_SUM,
            ForecastMethod.POWER_SUM,
            ForecastMethod.BASE_EXP_SUM,
        }:
            fallback_method = ForecastMethod.CONST_LAST
            method.name = fallback_method
            fallback_details = forecast_methods_map[fallback_method]
            method.coefficients, method.equation = fallback_details["generate_coef"](X=demand_driver_data, y=values)
        return method


def map_filtered_demand_driver_data(demand_drivers_names, years, region_name, data, context=None):
    """
    Build a matrix of required DDr values for existing ECUs/DDets.
    """
    aligned_ddr_df = pd.DataFrame(index=years)
    if "TIME" in demand_drivers_names:
        aligned_ddr_df["TIME"] = years

    region = data.get_region(region_name) if region_name else None
    missing_region = region is None

    for driver_name in demand_drivers_names:
        if driver_name == "TIME":
            continue

        if driver_name not in aligned_ddr_df.columns:
            aligned_ddr_df[driver_name] = np.nan

        if missing_region:
            continue

        driver_variable = region.get_demand_driver(driver_name)
        if driver_variable is None or driver_variable.demand_driver_data is None:
            aligned_ddr_df[driver_name] = np.nan
            continue

        filtered_values = _filter_values_by_year(
            driver_variable.demand_driver_data,
            years,
            context=context,
            driver_name=driver_name,
        )
        aligned_ddr_df[driver_name] = filtered_values

    return aligned_ddr_df if missing_region else aligned_ddr_df.dropna()


def process_future_projections(row_future_data, region_name, demand_driver_names, data, context=None):
    """
    Prepare interpolation support points from future input values and DDr mapping.
    """
    years = list(map(int, row_future_data.columns))
    demand_driver_data = map_filtered_demand_driver_data(
        demand_driver_names,
        years,
        region_name,
        data,
        context=context,
    )

    filtered_years = demand_driver_data.index.astype(int)
    common_years = sorted(set(filtered_years).intersection(years))
    if not common_years:
        raise ValueError(f"No common years between demand drivers and historical data for {region_name}")

    common_years = list(map(str, common_years))
    future_values = row_future_data[common_years].iloc[0].values.tolist()

    common_years = list(map(int, common_years))
    demand_driver_array = demand_driver_data.loc[common_years].values

    known_points = [
        tuple(coord) + (value,)
        for coord, value in zip(demand_driver_array, future_values)
    ]
    return known_points


def extract_user_given_coefficients(row: pd.DataFrame, coef_keys: list):
    """
    Extract user-provided coefficients in key order (k0, k1, ...).
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


def do_predictions(predictions_method: list, variable, data, forecast_year_range) -> pd.DataFrame:
    """
    Run forecast methods (regression/const) over the global forecast year range.
    """
    region_name = variable.region_name
    hierarchy = variable.get_hierarchy()
    region_predictions_df_list = []

    for method in predictions_method:
        method_details = forecast_methods_map[method.name]
        demand_drivers = method.demand_drivers_names
        driver_context = _build_driver_context(variable=variable, method=method, region_name=region_name)
        predict_function = method_details.get("predict_function")

        if not predict_function:
            raise ValueError(f"Prediction function not defined for forecast method: {method.name}")

        predictions = {}
        for year in forecast_year_range:
            try:
                x_values = map_x_values(demand_drivers, region_name, year, data, context=driver_context)
                predicted_value = predict_function(method, x_values)
                lower_limit = getattr(method, "lower_limit", -np.inf)
                upper_limit = getattr(method, "upper_limit", np.inf)
                if pd.notna(predicted_value) and pd.notna(lower_limit) and predicted_value < lower_limit:
                    predicted_value = lower_limit
                if pd.notna(predicted_value) and pd.notna(upper_limit) and predicted_value > upper_limit:
                    predicted_value = upper_limit
                predictions[year] = predicted_value
            except Exception as e:
                logging.error(f"Error predicting for {region_name}, year {year}: {e}")
                predictions[year] = pd.NaT

        scaled_predictions = {}
        for year, value in predictions.items():
            scaled_value = value * method.factor
            scaled_predictions[year] = scaled_value
        region_data = _build_region_output_row(
            hierarchy=hierarchy,
            variable_name=variable.name,
            method=method,
            region_name=region_name,
            year_values=scaled_predictions,
            coeff_or_points=method.coefficients,
        )
        region_predictions_df_list.append(pd.DataFrame(region_data))

    return pd.concat(region_predictions_df_list, ignore_index=False)


def do_interpolation(interpolations, variable, data, forecast_year_range) -> pd.DataFrame:
    """
    Run interpolation methods over the global forecast year range.
    """
    region_name = variable.region_name
    hierarchy = variable.get_hierarchy()
    region_interpolations_df_list = []

    for method in interpolations:
        method_details = forecast_methods_map[method.name]
        driver_context = _build_driver_context(variable=variable, method=method, region_name=region_name)
        predict_function = method_details.get("predict_function")

        if not predict_function:
            raise ValueError(f"Prediction function not defined for forecast method: {method.name}")

        predictions = {}
        interp_points = method.interp_points
        for year in forecast_year_range:
            try:
                x_values = map_x_values(
                    method.demand_drivers_names,
                    region_name,
                    year,
                    data,
                    context=driver_context,
                )
                predicted_value = predict_function(interp_points, x_values)
                lower_limit = getattr(method, "lower_limit", -np.inf)
                upper_limit = getattr(method, "upper_limit", np.inf)
                if pd.notna(predicted_value) and pd.notna(lower_limit) and predicted_value < lower_limit:
                    predicted_value = lower_limit
                if pd.notna(predicted_value) and pd.notna(upper_limit) and predicted_value > upper_limit:
                    predicted_value = upper_limit
                predictions[year] = predicted_value
            except Exception as e:
                logging.error(f"Error interpolating for {region_name}, {variable.settings} , year {year}: {e}")
                predictions[year] = np.nan

        scaled_predictions = {}
        for year, value in predictions.items():
            scaled_value = value * method.factor
            scaled_predictions[year] = scaled_value
        region_data = _build_region_output_row(
            hierarchy=hierarchy,
            variable_name=variable.name,
            method=method,
            region_name=region_name,
            year_values=scaled_predictions,
            coeff_or_points=method.interp_points,
        )
        region_interpolations_df_list.append(pd.DataFrame(region_data))

    return pd.concat(region_interpolations_df_list, ignore_index=False)


def map_x_values(demand_drivers, region_name, year, data, context=None):
    """
    Map demand drivers to their values for one region-year point.
    """
    x_values = []
    region = data.get_region(region_name) if region_name else None

    for driver in demand_drivers:
        if driver == "TIME":
            x_values.append(float(year))
            continue

        if region is None:
            x_values.append(np.nan)
            continue

        driver_variable = region.get_demand_driver(driver)
        driver_data = driver_variable.demand_driver_data if driver_variable else None
        if driver_data is None or driver_data.empty:
            x_values.append(np.nan)
            continue

        value = _get_driver_value_for_year(driver_data, year, context=context, driver_name=driver)
        x_values.append(value)

    return x_values


def _filter_values_by_year(region_data: pd.DataFrame, years: list, context=None, driver_name=None) -> pd.Series:
    """
    Read one value per requested year from a mapped DDr table.
    """
    if region_data is None or region_data.empty:
        return pd.Series([np.nan] * len(years), index=years, dtype=float)

    series = _get_driver_year_series(region_data, context=context)
    values = [series.get(int(year), np.nan) for year in years]

    return pd.Series(values, index=years, dtype=float)


def _get_driver_value_for_year(region_data: pd.DataFrame, year: int, context=None, driver_name=None) -> float:
    """
    Return the best-matching numeric DDr value for one year.
    """
    try:
        series = _get_driver_year_series(region_data, context=context)
        value = series.get(int(year), np.nan)
        return float(value) if not pd.isna(value) else np.nan
    except Exception:
        return np.nan


def _build_driver_context(variable=None, method=None, region_name=None) -> dict:
    """
    Build DDr mapping context for hierarchical lookup.
    """
    context = {}
    if region_name is not None:
        context["Region"] = region_name

    if variable is not None and hasattr(variable, "get_hierarchy"):
        hierarchy = variable.get_hierarchy() or {}
        if hierarchy.get("Sector") is not None:
            context["Sector"] = hierarchy.get("Sector")
        if hierarchy.get("Subsector") is not None:
            context["Subsector"] = hierarchy.get("Subsector")

    if method is not None:
        if getattr(method, "subtech", None) is not None:
            context["Subtech"] = method.subtech
        if getattr(method, "drive", None) is not None:
            context["Drive"] = method.drive
        if getattr(method, "ue_type", None) is not None:
            context["UE_Type"] = method.ue_type
        if getattr(method, "temp_level", None) is not None:
            context["Temp_level"] = method.temp_level

    return context


def _resolve_driver_rows_with_context(region_data: pd.DataFrame, context=None) -> pd.DataFrame:
    """
    Resolve candidate DDr rows using hierarchical default fallback.
    """
    if region_data is None or region_data.empty or not context:
        return region_data

    ordered_columns = [c for c in HIERARCHY_FALLBACK_ORDER if c in region_data.columns and c in context]
    if not ordered_columns:
        return region_data

    cache_key = (
        id(region_data),
        tuple(ordered_columns),
        tuple((c, _cacheable_context_value(context.get(c))) for c in ordered_columns),
    )
    cached = _DDR_RESOLVE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    criteria = {c: context.get(c) for c in ordered_columns}
    resolved = select_rows_with_default(region_data, criteria=criteria, ordered_columns=ordered_columns)
    if resolved is None or resolved.empty:
        resolved = pd.DataFrame()

    _DDR_RESOLVE_CACHE[cache_key] = resolved
    return resolved


def _rank_driver_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    """
    Rank rows by specificity so exact rows win over default rows.
    """
    if candidates is None or candidates.empty:
        return candidates

    key_cols = [c for c in HIERARCHY_FALLBACK_ORDER if c in candidates.columns]
    if not key_cols:
        return candidates

    ranked = candidates.copy()
    ranked["__spec"] = ranked[key_cols].apply(
        lambda r: sum(0 if is_default_value(v) else 1 for v in r), axis=1
    )
    ranked = ranked.sort_values("__spec", ascending=False)
    return ranked.drop(columns=["__spec"], errors="ignore")


def _cacheable_context_value(value):
    """
    Normalize context values for stable cache keys.
    """
    if value is None:
        return "default"
    try:
        if pd.isna(value):
            return "default"
    except Exception:
        pass
    text = str(value).strip()
    return text if text != "" else "default"


def _get_driver_year_series(region_data: pd.DataFrame, context=None) -> pd.Series:
    """
    Build one numeric series (year -> chosen value) for the given DDr table/context.
    Selection rule is identical to _get_driver_value_for_year: choose first non-NaN
    value from ranked candidates per year.
    """
    if region_data is None or region_data.empty:
        return pd.Series(dtype=float)

    ordered_columns = [c for c in HIERARCHY_FALLBACK_ORDER if context and c in context and c in region_data.columns]
    cache_key = (
        id(region_data),
        tuple(ordered_columns),
        tuple((c, _cacheable_context_value(context.get(c))) for c in ordered_columns),
    )
    cached = _DDR_YEAR_SERIES_CACHE.get(cache_key)
    if cached is not None:
        return cached

    candidates = _resolve_driver_rows_with_context(region_data, context=context)
    if candidates is None or candidates.empty:
        candidates = region_data
    ranked = _rank_driver_candidates(candidates)

    year_cols = [col for col in ranked.columns if str(col).isdigit()]
    if not year_cols:
        series = pd.Series(dtype=float)
        _DDR_YEAR_SERIES_CACHE[cache_key] = series
        return series

    values = {}
    for col in year_cols:
        col_values = pd.to_numeric(ranked[col], errors="coerce")
        non_nan = col_values[col_values.notna()]
        year_int = int(str(col))
        values[year_int] = float(non_nan.iloc[0]) if not non_nan.empty else np.nan

    series = pd.Series(values, dtype=float)
    _DDR_YEAR_SERIES_CACHE[cache_key] = series
    return series


def _build_context_string(row_df: pd.DataFrame, region_name: str) -> str:
    """
    Build a compact context string for user-input interpolation warnings.
    """
    context_parts = []
    for col in CONTEXT_DETAIL_COLUMNS:
        if col in row_df.columns:
            val = row_df[col].iloc[0]
            if pd.isna(val):
                val = "default"
            context_parts.append(f"{col}={val}")

    if not context_parts and region_name:
        context_parts.append(f"Region={region_name}")

    return ", ".join(context_parts) if context_parts else "context=unknown"


def _get_non_nan_years(row_future_data: pd.DataFrame, year_keys: list) -> list:
    """
    Return year labels whose values are numeric and not NaN.
    """
    non_nan_years = []
    for year in year_keys:
        value = pd.to_numeric(row_future_data[year].iloc[0], errors="coerce")
        if not pd.isna(value):
            non_nan_years.append(year)
    return non_nan_years


def _trace_text(value, max_len=180):
    """Return compact single-line text for trace output."""
    try:
        txt = str(value)
    except Exception:
        txt = repr(value)
    txt = txt.replace("\n", " ").replace("\r", " ").strip()
    if len(txt) > max_len:
        return txt[: max_len - 3] + "..."
    return txt


def _method_to_output_string(method_name):
    if method_name is None:
        return None
    if method_name in map_forecast_method_to_string:
        return map_forecast_method_to_string[method_name]
    if hasattr(method_name, "name"):
        return str(method_name.name).strip().lower()
    return str(method_name).strip()


def _equation_to_output_string(method):
    method_name = getattr(method, "name", None)
    raw_equation = getattr(method, "equation", None)

    if method_name == ForecastMethod.USER_FUNCTION:
        return raw_equation

    method_details = forecast_methods_map.get(method_name, {})
    template = method_details.get("get_eqaution_user")

    if isinstance(template, str) and template.strip():
        equation = template.strip()
    else:
        equation = raw_equation

    if equation is None:
        return None

    equation = str(equation).strip()
    if equation and method_name not in {ForecastMethod.INTERP_LIN, ForecastMethod.USER_FUNCTION}:
        if not equation.lower().startswith("y ="):
            equation = f"y = {equation}"
    return equation


def _build_method_trace(hierarchy, variable_name, method, region_name, coeff_or_points):
    """Build a compact per-row provenance string for forecast outputs."""
    drivers = getattr(method, "demand_drivers_names", None) or []
    drivers_txt = ",".join(str(d) for d in drivers) if drivers else "none"
    coeff_txt = _trace_text(coeff_or_points)
    method_txt = _method_to_output_string(getattr(method, "name", None))
    equation_txt = _equation_to_output_string(method)

    parts = [
        f"Region={region_name}",
        f"Sector={hierarchy.get('Sector')}",
        f"Subsector={hierarchy.get('Subsector')}",
        f"Technology={hierarchy.get('Technology')}",
        f"Variable={variable_name}",
        f"ForecastMethod={method_txt}",
        f"Drivers={drivers_txt}",
        f"UE_Type={getattr(method, 'ue_type', None)}",
        f"FE_Type={getattr(method, 'fe_type', None)}",
        f"Temp_level={getattr(method, 'temp_level', None)}",
        f"Subtech={getattr(method, 'subtech', None)}",
        f"Drive={getattr(method, 'drive', None)}",
        f"Factor={getattr(method, 'factor', None)}",
        f"LowerLimit={getattr(method, 'lower_limit', None)}",
        f"UpperLimit={getattr(method, 'upper_limit', None)}",
        f"Equation={_trace_text(equation_txt, 120)}",
        f"CoeffOrPoints={coeff_txt}",
    ]
    return " | ".join(parts)


def _build_region_output_row(hierarchy, variable_name, method, region_name, year_values, coeff_or_points):
    """
    Build one output row payload for prediction/interpolation exports.
    """
    trace = _build_method_trace(hierarchy, variable_name, method, region_name, coeff_or_points)
    function_name = _method_to_output_string(getattr(method, "name", None))
    equation_text = _equation_to_output_string(method)

    region_data = {
        "Sector": [hierarchy["Sector"]],
        "Region": region_name,
        "Subsector": [hierarchy["Subsector"]],
        "Variable": [variable_name],
        "Technology": [hierarchy["Technology"]],
        "Function": [function_name],
        "Coefficients/intp_points": [coeff_or_points],
        "Equation": [equation_text],
        "UE_Type": [method.ue_type],
        "FE_Type": [method.fe_type],
        "Factor": [method.factor],
        "Temp_level": [method.temp_level],
        "Subtech": [method.subtech],
        "Drive": [method.drive],
        "Trace": [trace],
        **year_values,
    }

    if method.efficiency_variable == 1:
        region_data.update(
            {
                "Region": [method.region],
                "Sector": [method.sector],
                "Subsector": [method.subsector],
                "Technology": [method.tech],
                "FE_Type": [method.fe_type],
                "Trace": [_trace_text(trace + " | EfficiencyVariable=1")],
            }
        )

    return region_data


def clean_dataframe(df):
    """
    Remove fully empty rows/columns from a dataframe.
    """
    if df is None:
        return df
    return df.dropna(axis=0, how="all").dropna(axis=1, how="all")


def get_df_value(row, column_name):
    """
    Extract a value from a single-row dataframe, handling missing and NaN values.
    """
    if column_name in row.columns:
        value = row[column_name].iloc[0]
        if pd.isna(value):
            return None
        return value
    return None
