import pandas as pd
import numpy as np
from typing import Any, Dict, List

from endemo2.Modeling.Methods.prediction_methods import build_interpolation_points, base_year
from endemo2.Modeling.dependent_ddr_forecast import compute_dependent_series
from endemo2.Input.loaders.common import select_rows_with_default, is_default_value
from endemo2.Input.model_config import (
    META_COLUMNS,
)


def _norm_subregion(val: Any):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s.lower() in {"default", "none", "nan"}:
        return None
    return s


def _norm_region(val: Any):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s.lower() in {"default", "none", "nan"}:
        return None
    return s


def _expand_default_scenario_rows(
    scen_raw: pd.DataFrame,
    scen_long: pd.DataFrame,
    active_regions: List[str],
    subregions_by_region: Dict[str, Dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Expand rows with Region/Subregion == default to active region/subregion targets.

    Specificity rules:
    - exact region + exact subregion overrides all default-derived rows
    - exact region + default subregion overrides region-default + default subregion
    """
    expanded_raw = []
    expanded_long = []
    scores = []
    slot_keys = []

    key_cols = [
        "Region", "Subregion", "Sector", "Subsector", "Variable",
        "Technology", "UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive",
    ]

    for idx, row in scen_raw.iterrows():
        row_long = scen_long.iloc[idx] if idx < len(scen_long) else row

        src_region = _norm_region(row.get("Region"))
        src_subregion = _norm_subregion(row.get("Subregion"))

        if src_region is None:
            target_regions = list(active_regions)
            region_is_exact = False
        else:
            target_regions = [src_region] if src_region in active_regions else []
            region_is_exact = True

        for region in target_regions:
            expected_subregions = list((subregions_by_region.get(region) or {}).keys())
            if not expected_subregions:
                continue

            if src_subregion is None:
                target_subregions = expected_subregions
                subregion_is_exact = False
            else:
                target_subregions = [src_subregion]
                subregion_is_exact = True

            for sub in target_subregions:
                # Let validation below report unknown/extra codes.
                out_row = row.copy()
                out_row["Region"] = region
                out_row["Subregion"] = sub
                out_long = row_long.copy()
                out_long["Region"] = region
                out_long["Subregion"] = sub

                expanded_raw.append(out_row)
                expanded_long.append(out_long)
                score = int(region_is_exact) + int(subregion_is_exact)
                scores.append(score)
                slot_keys.append(tuple(out_row.get(c) for c in key_cols))

    if not expanded_raw:
        return pd.DataFrame(), pd.DataFrame()

    raw_df = pd.DataFrame(expanded_raw).reset_index(drop=True)
    long_df = pd.DataFrame(expanded_long).reset_index(drop=True)

    # Keep the most specific row per target slot.
    helper = pd.DataFrame({"slot": slot_keys, "__score": scores, "__idx": range(len(slot_keys))})
    best_idx = (
        helper.sort_values(["slot", "__score", "__idx"], ascending=[True, False, True])
        .drop_duplicates(subset=["slot"], keep="first")["__idx"]
        .tolist()
    )
    best_idx = sorted(best_idx)
    return raw_df.iloc[best_idx].reset_index(drop=True), long_df.iloc[best_idx].reset_index(drop=True)


def _get_dependency_columns(df: pd.DataFrame) -> List[str]:
    if df is None or df.empty:
        return []
    dep_cols = []
    for col in df.columns:
        col_str = str(col)
        if col_str.lower().startswith("ddr"):
            dep_cols.append(col_str)
    def sort_key(c):
        suf = c[3:]
        try:
            return (0, int(suf))
        except Exception:
            return (1, suf)
    return sorted(dep_cols, key=sort_key)


def _collect_coef_columns(df: pd.DataFrame) -> Dict[int, str]:
    coef_cols_by_idx = {}
    for col in df.columns:
        col_str = str(col).strip().lower().replace(" ", "").replace("_", "").replace("/", "")
        if len(col_str) >= 2 and col_str[0] == "k" and col_str[1:].isdigit():
            try:
                coef_cols_by_idx[int(col_str[1:])] = col
            except Exception:
                continue
    return coef_cols_by_idx


def _filter_hist_rows(
    hist_df: pd.DataFrame,
    row: pd.Series,
    match_cols: List[str],
    variable_name: str,
    wildcard_defaults: bool = True,
) -> pd.DataFrame:
    if hist_df is None or hist_df.empty:
        return pd.DataFrame()
    df = hist_df
    var_norm = str(variable_name).strip().upper()
    if var_norm == "POP":
        must_cols = ["Region", "Subregion", "Variable"]
        if any(c not in df.columns for c in must_cols):
            return pd.DataFrame()
        if _norm_subregion(row.get("Subregion")) is None:
            return pd.DataFrame()
        return select_rows_with_default(
            df=df,
            criteria={c: row.get(c) for c in must_cols},
            ordered_columns=must_cols,
        )

    ordered_cols_all = [c for c in match_cols if c in df.columns]
    if "Subregion" in ordered_cols_all and _norm_subregion(row.get("Subregion")) is None:
        return pd.DataFrame()

    # In subregion forecast, default values can be treated in two modes:
    # - wildcard_defaults=True: default acts as wildcard to collect expansion context
    # - wildcard_defaults=False: default is enforced as default row selector
    # Region/Subregion/Variable stay mandatory in both modes.
    mandatory_cols = {"Region", "Subregion", "Variable"}
    criteria = {}
    ordered_cols = []
    for col in ordered_cols_all:
        val = row.get(col)
        if col in mandatory_cols:
            criteria[col] = val
            ordered_cols.append(col)
            continue
        if is_default_value(val):
            if not wildcard_defaults:
                criteria[col] = val
                ordered_cols.append(col)
            continue
        criteria[col] = val
        ordered_cols.append(col)

    if not ordered_cols:
        return df
    return select_rows_with_default(df=df, criteria=criteria, ordered_columns=ordered_cols)


def _coalesce_hist_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse multiple historical matches into one row by taking first non-NaN
    value per year column. Metadata is taken from the first row.
    """
    if rows is None or rows.empty:
        return pd.DataFrame()
    if len(rows) == 1:
        return rows.reset_index(drop=True)

    out = rows.iloc[[0]].copy().reset_index(drop=True)
    year_cols = [c for c in rows.columns if str(c).isdigit()]
    for col in year_cols:
        vals = pd.to_numeric(rows[col], errors="coerce")
        non_nan = vals.dropna()
        out.at[0, col] = non_nan.iloc[0] if not non_nan.empty else np.nan
    return out


def _expand_row_with_hist_context(
    row: pd.Series,
    row_long: pd.Series,
    hist_df: pd.DataFrame,
    match_cols: List[str],
    variable_name: str,
) -> List[tuple[pd.Series, pd.Series, pd.DataFrame]]:
 
    hist_row = _filter_hist_rows(hist_df, row, match_cols, variable_name, wildcard_defaults=True)
    if hist_row is None or hist_row.empty or len(hist_row) <= 1:
        return [(row, row_long, hist_row)]

    expandable_cols = [
        c for c in ["Sector", "Subsector", "Technology", "UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive"]
        if c in hist_row.columns and is_default_value(row.get(c))
    ]
    if not expandable_cols:
        return [(row, row_long, hist_row)]

    variants: List[tuple[pd.Series, pd.Series, pd.DataFrame]] = []
    for _, combo in hist_row[expandable_cols].drop_duplicates().iterrows():
        concrete_row = row.copy()
        concrete_row_long = row_long.copy()
        for col in expandable_cols:
            concrete_row[col] = combo[col]
            concrete_row_long[col] = combo[col]
        concrete_hist = _filter_hist_rows(
            hist_df,
            concrete_row,
            match_cols,
            variable_name,
            wildcard_defaults=False,
        )
        if concrete_hist is None or concrete_hist.empty:
            continue
        variants.append((concrete_row, concrete_row_long, concrete_hist))

    if not variants:
        return [(row, row_long, hist_row)]
    return variants


def _build_subregional_variable_map(data) -> dict:
    """
    Build mapping (Region, Sector, Subsector) -> distribution variable
    from sector settings (same source as subregional output writer).
    """
    mapping = {}
    for region in getattr(data, "regions", []) or []:
        for sector in getattr(region, "sectors", []) or []:
            settings = getattr(sector, "settings", None)
            if settings is None or settings.empty or "Subregional_division" not in settings.columns:
                continue
            for subsector_name, row in settings.iterrows():
                val = row.get("Subregional_division")
                if pd.isna(val) or str(val).strip() == "":
                    continue
                mapping[(region.region_name, str(sector.name).strip(), str(subsector_name).strip())] = str(val).strip()
    return mapping


def _prune_redundant_default_rows(df: pd.DataFrame, data) -> pd.DataFrame:
    """
    Remove default/default rows that are redundant for configured sector/subsector usage.

    A row is removed only if:
    - it has Sector=default and Subsector=default
    - and for the same (Region, Subregion, Variable), all configured
      (Sector, Subsector) pairs for that variable already have exact rows.
    """
    if df is None or df.empty:
        return df
    needed_cols = {"Region", "Subregion", "Variable", "Sector", "Subsector"}
    if not needed_cols.issubset(df.columns):
        return df

    dist_map = _build_subregional_variable_map(data)
    required_pairs_by_var = {}
    for (region, sector, subsector), var in dist_map.items():
        key = (str(region).strip(), str(var).strip())
        required_pairs_by_var.setdefault(key, set()).add((str(sector).strip(), str(subsector).strip()))

    if not required_pairs_by_var:
        return df

    keep_mask = pd.Series(True, index=df.index)
    grouped = df.groupby(["Region", "Subregion", "Variable"], dropna=False)
    for (region, subregion, variable), group in grouped:
        region_s = str(region).strip()
        var_s = str(variable).strip()
        required_pairs = required_pairs_by_var.get((region_s, var_s), set())
        if not required_pairs:
            continue

        exact_group = group[
            (~group["Sector"].apply(is_default_value)) & (~group["Subsector"].apply(is_default_value))
        ]
        exact_pairs = set(
            zip(
                exact_group["Sector"].astype(str).str.strip(),
                exact_group["Subsector"].astype(str).str.strip(),
            )
        )
        if not required_pairs.issubset(exact_pairs):
            continue

        redundant_defaults = group[
            group["Sector"].apply(is_default_value) & group["Subsector"].apply(is_default_value)
        ]
        if not redundant_defaults.empty:
            keep_mask.loc[redundant_defaults.index] = False

    return df.loc[keep_mask].reset_index(drop=True)


def forecast_subregion_division(data):
    """
    Forecast subregional division time series using the same forecast channel as dependent DDrs.
    Stores result in data.subregion_division_forecast.
    """
    scen_raw = data.subregion_scenario_raw
    scen_long = data.subregion_scenario_long
    hist_df = data.subregion_hist_data
    if scen_raw is None or scen_raw.empty:
        return

    active_regions = list(data.input_manager.general_settings.active_regions or [])
    scen_raw, scen_long = _expand_default_scenario_rows(
        scen_raw=scen_raw.reset_index(drop=True),
        scen_long=scen_long.reset_index(drop=True),
        active_regions=active_regions,
        subregions_by_region=getattr(data, "subregions", {}) or {},
    )
    if scen_raw.empty:
        return

    if "Subregion" not in scen_raw.columns:
        raise ValueError("[Subregion forecast] Scenario sheet must contain column 'Subregion'.")

    # Validate subregion list against settings per active region
    for region in active_regions:
        expected = set((data.subregions.get(region) or {}).keys())
        scen_subs = set(
            _norm_subregion(v)
            for v in scen_raw.loc[scen_raw["Region"] == region, "Subregion"].tolist()
        )
        scen_subs.discard(None)
        missing = expected - scen_subs
        extra = scen_subs - expected
        if missing or extra:
            raise ValueError(
                f"[Subregion forecast] Subregion mismatch for region '{region}'. "
                f"Missing in scenario: {sorted(missing)}; Extra in scenario: {sorted(extra)}"
            )

    dep_cols = _get_dependency_columns(scen_raw)
    coef_cols_by_idx = _collect_coef_columns(scen_raw)
    coef_indices = sorted(coef_cols_by_idx.keys())
    year_cols = [c for c in scen_raw.columns if str(c).isdigit()]
    meta_cols = [c for c in scen_raw.columns if c not in year_cols]

    match_cols = [
        "Region", "Subregion", "Sector", "Subsector", "Variable",
        "Technology", "UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive",
    ]

    results = []
    full_years = [str(y) for y in data.input_manager.general_settings.full_year_range]
    for idx, row in scen_raw.iterrows():
        row_long = scen_long.iloc[idx] if idx < len(scen_long) else row
        var_name = str(row.get("Variable")).strip()
        variants = _expand_row_with_hist_context(
            row=row,
            row_long=row_long,
            hist_df=hist_df,
            match_cols=match_cols,
            variable_name=var_name,
        )

        for proc_row, proc_row_long, hist_row in variants:
            subregion = _norm_subregion(proc_row.get("Subregion"))
            if subregion is None:
                raise ValueError("[Subregion forecast] Subregion cannot be empty/default in scenario sheet.")

            if pd.isna(proc_row.get("Forecast data")) or str(proc_row.get("Forecast data")).strip() == "":
                raise ValueError(f"[Subregion forecast] Missing Forecast data for {proc_row.get('Region')}/{subregion}.")
            if pd.isna(proc_row.get("Function")) or str(proc_row.get("Function")).strip() == "":
                raise ValueError(f"[Subregion forecast] Missing Function for {proc_row.get('Region')}/{subregion}.")

            dependencies = [str(proc_row[c]).strip() for c in dep_cols if pd.notna(proc_row.get(c)) and str(proc_row.get(c)).strip()]
            func_name = str(proc_row.get("Function")).strip().lower() if pd.notna(proc_row.get("Function")) else ""
            if not dependencies and var_name.upper() == "POP" and func_name == "lin":
                dependencies = ["TIME"]

            interpolation_points = build_interpolation_points(proc_row_long)

            spec = {
                "Region": proc_row.get("Region"),
                "Subregion": subregion,
                "Sector": proc_row.get("Sector"),
                "Subsector": proc_row.get("Subsector"),
                "Variable": proc_row.get("Variable"),
                "Technology": proc_row.get("Technology"),
                "UE_Type": proc_row.get("UE_Type"),
                "FE_Type": proc_row.get("FE_Type"),
                "Temp_level": proc_row.get("Temp_level"),
                "Subtech": proc_row.get("Subtech"),
                "Drive": proc_row.get("Drive"),
                "Forecast data": proc_row.get("Forecast data"),
                "Function": proc_row.get("Function"),
                "Unit": proc_row.get("Unit"),
                "Factor": proc_row.get("Factor"),
                "Equation": proc_row.get("Equation"),
                META_COLUMNS["LOWER_LIMIT"]: proc_row.get(META_COLUMNS["LOWER_LIMIT"]),
                "Dependencies": dependencies,
                "Interpolation_points": interpolation_points,
                "Coefficients": {f"k{i}": proc_row.get(coef_cols_by_idx[i]) for i in coef_indices},
            }

            if str(spec.get("Forecast data")).strip().lower() == "historical" and (hist_row is None or hist_row.empty):
                raise ValueError(
                    f"[Subregion forecast] Missing historical data for "
                    f"{proc_row.get('Region')}/{subregion}/{proc_row.get('Variable')}."
                )
            if hist_row is not None and len(hist_row) > 1:
                hist_row = _coalesce_hist_rows(hist_row)

            base_row = {col: proc_row.get(col) for col in meta_cols}
            series_df, _ = compute_dependent_series(
                spec=spec,
                data=data,
                region_name=str(proc_row.get("Region")),
                variable_name=str(proc_row.get("Variable")),
                hist_df=hist_row,
                variable_obj=None,
                base_row=base_row,
                context_label="Subregion",
            )
            if series_df is None:
                raise ValueError(
                    f"[Subregion forecast] Forecast failed for "
                    f"{proc_row.get('Region')}/{subregion}/{proc_row.get('Variable')}."
                )
            # Normalize year columns and enforce the global full-year range/order
            rename_map = {}
            for col in series_df.columns:
                y = base_year(col)
                if y is not None:
                    rename_map[col] = str(y)
            if rename_map:
                series_df = series_df.rename(columns=rename_map)
                series_df = series_df.loc[:, ~series_df.columns.duplicated()]
            # Keep scenario metadata order, but retain computed trace diagnostics
            # even if the scenario sheet has no explicit "Trace" column.
            meta_order = [c for c in meta_cols if c in series_df.columns]
            if "Trace" in series_df.columns and "Trace" not in meta_order:
                meta_order.append("Trace")
            # Add missing year columns in one step to avoid DataFrame fragmentation warnings
            series_df = series_df.reindex(columns=meta_order + full_years)
            results.append(series_df)

    out_df = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    data.subregion_division_forecast = _prune_redundant_default_rows(out_df, data)




