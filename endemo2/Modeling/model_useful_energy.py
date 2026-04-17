import pandas as pd
import itertools
import numpy as np
from endemo2.Modeling.model_final_energy import get_matches
from endemo2.Input.loaders.common import select_rows_with_default

# Switch for normalization

# Important: You must manually change this setting here to see if you want it or not. The variable name must also match!
NORMALIZE_TECH_SHARE = True
TECH_SHARE_VARIABLE_NAME = "TECH_SHARE"
TECH_SHARE_NORM_TOLERANCE = 1e-6


def normalize_share(df, year_cols, group_keys):
    """
    Normalize share-like rows so that for each group and year, the sum equals 1.
    If the sum is 0/NaN, keep original values for that year.
    """
    # Errorhandling für leere übergabe
    if df.empty:
        return df
    year_cols = [c for c in year_cols if c in df.columns]
    if not year_cols:
        return df

    #work = runtime helper variable
    # Umwandlung von year in numeric und erstellen des lösungsarrays
    work = df.copy()
    work[year_cols] = work[year_cols].apply(pd.to_numeric, errors="coerce")
    sums = work.groupby(group_keys, dropna=False)[year_cols].sum(min_count=1).reset_index()
    sums = sums.rename(columns={c: f"__sum_{c}" for c in year_cols})
    work = work.merge(sums, on=group_keys, how="left")

    # Normierung: 
    for c in year_cols:
        denom = pd.to_numeric(work[f"__sum_{c}"], errors="coerce")
        numer = pd.to_numeric(work[c], errors="coerce")
        work[c] = np.where(denom > 0, numer / denom, numer)

    drop_cols = [f"__sum_{c}" for c in year_cols if f"__sum_{c}" in work.columns]
    if drop_cols:
        work = work.drop(columns=drop_cols)
    return work


def normalize_tech_shares(data, forecast_year_range):
    """
    Normalize TECH_SHARE across technologies within each subsector.
    """
    # nur wenn Variable = true,  funktioniert es
    if not NORMALIZE_TECH_SHARE:
        return
    year_cols = [str(y) for y in forecast_year_range]

# Hirachie durchlaufen und Variablen auslesen
    for region in data.regions:
        for sector in region.sectors:
            for subsector in sector.subsectors:
                tech_share_vars = []
                for tech in subsector.technologies:
                    for var in getattr(tech, "ddets", []):
                        if str(getattr(var, "name", "")).upper() != TECH_SHARE_VARIABLE_NAME:
                            continue
                        if getattr(var, "forecast", None) is None or var.forecast.empty:
                            continue
                        tech_share_vars.append(var)

                # Nur normieren, wenn es mehr ale eine Technologie gibt
                if len(tech_share_vars) < 2:
                    continue

                # alle Tech-shares werden in ein Array gepackt, zum übergeben an hilfsfunktion
                combined = pd.concat([v.forecast.copy() for v in tech_share_vars], ignore_index=True)
                combined.columns = combined.columns.astype(str)

                # Es wird eine Gruppe erstellt, für die Normiert wird (also alle Technologien innerhalb eines Subsektors)
                group_keys = [k for k in ["Region", "Sector", "Subsector"] if k in combined.columns]
                if not group_keys or "Technology" not in combined.columns:
                    continue

                #Übergabe an hilfsfunktion
                combined_num = combined.copy()
                combined_num[year_cols] = combined_num[year_cols].apply(pd.to_numeric, errors="coerce")
                sums = combined_num.groupby(group_keys, dropna=False)[year_cols].sum(min_count=1).reset_index()
                needs_norm = False
                for _, sum_row in sums.iterrows():
                    not_norm_years = []
                    for y in year_cols:
                        val = sum_row.get(y)
                        if pd.isna(val) or val <= 0:
                            continue
                        if abs(val - 1.0) > TECH_SHARE_NORM_TOLERANCE:
                            not_norm_years.append(y)
                    if not_norm_years:
                        needs_norm = True
                        group_desc = ", ".join(f"{k}={sum_row.get(k)}" for k in group_keys)
                        print(
                            f"[TECH_SHARE] Not normalized for group ({group_desc}). "
                            f"Years: {', '.join(not_norm_years)}. Normalizing."
                        )

                if not needs_norm:
                    continue

                normalized = normalize_share(
                    combined,
                    year_cols=year_cols,
                    group_keys=group_keys,
                )

                # Hier werden die Normierten Werte zurück in die entsprechende Variable geschrieben
                match_keys = group_keys + ["Technology"]
                normalized_idx = normalized.set_index(match_keys)
                for v in tech_share_vars:
                    vf = v.forecast.copy()
                    vf.columns = vf.columns.astype(str)
                    if not all(k in vf.columns for k in match_keys):
                        continue
                    vf_idx = vf.set_index(match_keys)
                    update_cols = [c for c in year_cols if c in vf_idx.columns and c in normalized_idx.columns]
                    if update_cols:
                        vf_idx.update(normalized_idx[update_cols])
                        v.forecast = vf_idx.reset_index()

def calculate_useful_energy(data):
    """
    Calculate useful energy as ECU * sum(DDet[Technology][Type]) for each subsector,
    for each combination of DDet, Technology, and Type.
    """
    general_settings = data.input_manager.general_settings
    effiency_fe = data.efficiency_data[0].forecast # List of Variable objects for FE [var_ef, var_share] always given by user
    forecast_year_range = general_settings.forecast_year_range
    forecast_year_range = [str(year) for year in forecast_year_range]
    # Optional: normalize technology shares before UE is computed.
    normalize_tech_shares(data, forecast_year_range)
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
                    if ue_per_technology is not None and not ue_per_technology.empty:
                        ue_per_subsectors.append(ue_per_technology)
                if not ue_per_subsectors:
                    continue
                ue_per_subsector = pd.concat(ue_per_subsectors, ignore_index=True)
                subsector.energy_ue = ue_per_subsector
                ue_per_sector.append(ue_per_subsector)
            if not ue_per_sector:
                continue
            ue_sector = pd.concat(ue_per_sector, ignore_index=True)
            sector.energy_ue = ue_sector
            ue_region.append(ue_sector)
        if ue_region:
            ue_per_region = pd.concat(ue_region, ignore_index=True)
            region.energy_ue = ue_per_region


def _build_ue_trace(region_name, sector_name, subsector_name, technology_name, ecu_name, ddet_names, ue_type, subtech, drive, temp_level="TOTAL"):
    """Build compact per-row trace text for useful-energy rows."""
    ddet_txt = ",".join(sorted({str(n) for n in ddet_names})) if ddet_names else "none"
    return (
        f"Region={region_name} | Sector={sector_name} | Subsector={subsector_name} | "
        f"Technology={technology_name} | UE_Type={ue_type} | Temp_level={temp_level} | "
        f"ECU={ecu_name} | DDets={ddet_txt} | Subtech={subtech if subtech is not None else 'default'} | "
        f"Drive={drive if drive is not None else 'default'}"
    )


def calculate_ue(ecu, ddets, forecast_year_range,
                 subsector_name, technology_name, sector_name, region_name, effiency_fe):
    """
    Calculate useful energy for each Technology dynamically.

    Heat handling:
    - Compute each explicit heat level first (Q1/Q2/... dynamic levels).
    - Build HEAT/TOTAL as the sum over computed heat levels.
    - If no heat levels exist for a group, fall back to direct total-heat computation.
    """
    if getattr(ecu, "forecast", None) is None or ecu.forecast.empty:
        raise ValueError(
            f"[UE] Missing ECU forecast for {region_name}/{sector_name}/{subsector_name}/{technology_name}. "
            f"Check ECU input rows (Historical/User) and mapping."
        )

    ecu_df = ecu.forecast.copy()
    ecu_df.columns = ecu_df.columns.astype(str)
    for y in forecast_year_range:
        if y not in ecu_df.columns:
            ecu_df[y] = np.nan
    ecu_vals_df = ecu_df[forecast_year_range].apply(pd.to_numeric, errors="coerce")
    # Deterministic behavior for multiple ECU rows: last non-NaN per year wins.
    ecu_values = ecu_vals_df.ffill(axis=0).iloc[-1].reindex(forecast_year_range)

    # Prepare DDet DataFrames
    ddets_dfs = []
    missing_ddet_forecasts = []
    for ddet in ddets:
        if getattr(ddet, "forecast", None) is None or ddet.forecast.empty:
            missing_ddet_forecasts.append(ddet.name)
            continue
        df = ddet.forecast.copy()
        df.columns = df.columns.astype(str)
        if 'FE_Type' in df.columns and df['FE_Type'].notna().any():
            # Sum over FE types for defined UE type where needed.
            df = calc_eu_for_defined_fe(df, effiency_fe, forecast_year_range)
        ddets_dfs.append(df)

    if missing_ddet_forecasts:
        missing_txt = ", ".join(sorted(set(str(v) for v in missing_ddet_forecasts)))
        raise ValueError(
            f"[UE] Missing DDet forecast(s) for {region_name}/{sector_name}/{subsector_name}/{technology_name}: "
            f"{missing_txt}. Check input completeness (e.g. 'Forecast data=Historical' without historical values)."
        )
    if not ddets_dfs:
        return pd.DataFrame()

    ddet_combined_raw = pd.concat(ddets_dfs, ignore_index=True)
    ddet_combined_raw.columns = ddet_combined_raw.columns.astype(str)

    # Regular calculation context (non-heat + optional direct heat total rows).
    heat_level_frames, ddet_for_regular = process_temp_levels(ddet_combined_raw)

    # Group identification should see all rows (including heat level rows).
    valid_groups = identify_valid_groups(ddet_combined_raw)
    ue_entries = []

    def _select_applicable_rows(source_df: pd.DataFrame, criteria: dict, ordered_columns: list) -> pd.DataFrame:
        if source_df is None or source_df.empty:
            return pd.DataFrame()
        if "Variable" in source_df.columns:
            selected_parts = []
            for _, ddet_group in source_df.groupby("Variable", dropna=False):
                resolved = select_rows_with_default(
                    ddet_group,
                    criteria=criteria,
                    ordered_columns=ordered_columns,
                )
                if resolved is not None and not resolved.empty:
                    selected_parts.append(resolved)
            return pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame()
        resolved = select_rows_with_default(
            source_df,
            criteria=criteria,
            ordered_columns=ordered_columns,
        )
        return resolved if resolved is not None else pd.DataFrame()

    def _calc_ue_values(applicable_ddet: pd.DataFrame):
        if applicable_ddet is None or applicable_ddet.empty:
            return None
        product = applicable_ddet[forecast_year_range].apply(pd.to_numeric, errors="coerce").prod()
        product.index = product.index.map(str)
        product = product.reindex(forecast_year_range)
        ecu_vals_aligned = pd.to_numeric(ecu_values, errors="coerce").reindex(forecast_year_range)
        return ecu_vals_aligned * product

    # Heat-level source must contain only explicit level rows (Q1/Q2/...),
    # so general HEAT rows such as TOTAL/default/CALIB are not applied a second time
    # during the level distribution step.
    if heat_level_frames:
        heat_source = pd.concat(heat_level_frames, ignore_index=True)
        heat_source.columns = heat_source.columns.astype(str)
    else:
        heat_source = pd.DataFrame()

    # Dynamic set of explicit heat levels (exclude total/default/empty).
    heat_levels = []
    if not heat_source.empty and 'Temp_level' in heat_source.columns:
        raw_levels = heat_source['Temp_level'].fillna("").astype(str).str.strip().tolist()
        level_set = {
            lvl for lvl in raw_levels
            if lvl and lvl.lower() not in {"default", "total", "none", "nan"}
        }
        heat_levels = sorted(level_set)

    for group in valid_groups:
        ue_type = group['UE_Type']
        # Safety guard: never compute standalone groups for undefined UE types.
        if pd.isna(ue_type) or str(ue_type).strip().lower() in {'', 'default', 'none', 'nan'}:
            continue
        subtech = group['Subtech']
        drive = group['Drive']
        ue_type_norm = str(ue_type).strip().upper()

        if ue_type_norm != 'HEAT':
            criteria = {
                "UE_Type": ue_type,
                "Subtech": subtech,
                "Drive": drive,
            }
            matching_columns = [
                col for col in ["UE_Type", "Subtech", "Drive"]
                if col in (ddet_for_regular.columns if ddet_for_regular is not None else [])
            ]
            applicable_ddet = _select_applicable_rows(ddet_for_regular, criteria, matching_columns)
            ue_values = _calc_ue_values(applicable_ddet)
            if ue_values is None:
                continue

            entry = {
                "Region": region_name,
                "Sector": sector_name,
                "Subsector": subsector_name,
                "Technology": technology_name,
                "UE_Type": ue_type,
                "Temp_level": "TOTAL",
                "Subtech": subtech if subtech is not None else "default",
                "Drive": drive if drive is not None else "default",
                "Trace": _build_ue_trace(
                    region_name=region_name,
                    sector_name=sector_name,
                    subsector_name=subsector_name,
                    technology_name=technology_name,
                    ecu_name=getattr(ecu, "name", "ECU"),
                    ddet_names=[getattr(d, "name", None) for d in ddets],
                    ue_type=ue_type,
                    subtech=subtech,
                    drive=drive,
                    temp_level="TOTAL",
                ),
            }
            entry.update(ue_values.to_dict())
            ue_entries.append(entry)
            continue

        # HEAT share logic: calculate HEAT/TOTAL once, then distribute to Q-levels by shares.
        criteria_total = {
            "UE_Type": "HEAT",
            "Subtech": subtech,
            "Drive": drive,
        }
        matching_columns_total = [
            col for col in ["UE_Type", "Subtech", "Drive"]
            if col in (ddet_for_regular.columns if ddet_for_regular is not None else [])
        ]
        applicable_total = _select_applicable_rows(ddet_for_regular, criteria_total, matching_columns_total)
        heat_total_values = _calc_ue_values(applicable_total)
        if heat_total_values is None:
            continue

        # Apply per-level shares to the already computed heat total.
        share_sum = pd.Series(0.0, index=forecast_year_range, dtype=float)
        for temp_level in heat_levels:
            criteria_share = {
                "UE_Type": "HEAT",
                "Subtech": subtech,
                "Drive": drive,
                "Temp_level": temp_level,
            }
            matching_columns_share = [
                col for col in ["UE_Type", "Subtech", "Drive", "Temp_level"]
                if col in heat_source.columns
            ]
            applicable_shares = _select_applicable_rows(heat_source, criteria_share, matching_columns_share)
            if applicable_shares is None or applicable_shares.empty:
                continue

            share_values = applicable_shares[forecast_year_range].apply(pd.to_numeric, errors="coerce").prod()
            share_values.index = share_values.index.map(str)
            share_values = share_values.reindex(forecast_year_range)

            heat_values_level = pd.to_numeric(heat_total_values, errors="coerce").reindex(forecast_year_range) * share_values
            share_sum = share_sum.add(pd.to_numeric(share_values, errors="coerce").fillna(0.0), fill_value=0.0)

            temp_entry = {
                "Region": region_name,
                "Sector": sector_name,
                "Subsector": subsector_name,
                "Technology": technology_name,
                "UE_Type": "HEAT",
                "Temp_level": temp_level,
                "Subtech": subtech if subtech is not None else "default",
                "Drive": drive if drive is not None else "default",
                "Trace": _build_ue_trace(
                    region_name=region_name,
                    sector_name=sector_name,
                    subsector_name=subsector_name,
                    technology_name=technology_name,
                    ecu_name=getattr(ecu, "name", "ECU"),
                    ddet_names=[getattr(d, "name", None) for d in ddets],
                    ue_type="HEAT",
                    subtech=subtech,
                    drive=drive,
                    temp_level=temp_level,
                ) + " | DerivedFrom=HeatTotal*Share",
            }
            temp_entry.update(heat_values_level.to_dict())
            ue_entries.append(temp_entry)

        # Share diagnostics (non-blocking): helps detect malformed heat-level inputs.
        if heat_levels and not share_sum.empty:
            max_dev = (share_sum - 1.0).abs().max(skipna=True)
            if pd.notna(max_dev) and max_dev > 0.05:
                print(
                    f"[UE heat share] Shares do not sum to 1 for {region_name}/{sector_name}/{subsector_name}/"
                    f"{technology_name} (Subtech={subtech}, Drive={drive}). Max deviation={max_dev:.4f}"
                )

        total_trace = _build_ue_trace(
            region_name=region_name,
            sector_name=sector_name,
            subsector_name=subsector_name,
            technology_name=technology_name,
            ecu_name=getattr(ecu, "name", "ECU"),
            ddet_names=[getattr(d, "name", None) for d in ddets],
            ue_type="HEAT",
            subtech=subtech,
            drive=drive,
            temp_level="TOTAL",
        ) + " | DerivedFrom=DirectHeatTotal"

        total_entry = {
            "Region": region_name,
            "Sector": sector_name,
            "Subsector": subsector_name,
            "Technology": technology_name,
            "UE_Type": "HEAT",
            "Temp_level": "TOTAL",
            "Subtech": subtech if subtech is not None else "default",
            "Drive": drive if drive is not None else "default",
            "Trace": total_trace,
        }
        total_entry.update(heat_total_values.to_dict())
        ue_entries.append(total_entry)

    return pd.DataFrame(ue_entries)

def process_temp_levels(dfs_with_type):
    """Split DDet DataFrames into total heat and temperature-specific entries."""
    dfs_heat_q = []
    dfs_with_total_type = []
    if dfs_with_type is None or dfs_with_type.empty:
        return dfs_heat_q, pd.DataFrame()

    temp = dfs_with_type["Temp_level"].fillna("").astype(str).str.strip()
    ue = dfs_with_type["UE_Type"].fillna("").astype(str).str.strip().str.upper()
    temp_upper = temp.str.upper()

    is_total_heat = (ue == "HEAT") & (
        (temp_upper == "TOTAL") | (temp == "") | (temp.str.lower() == "default")
    )
    is_non_heat = ue != "HEAT"
    total_mask = is_total_heat | is_non_heat
    total_df = dfs_with_type[total_mask]
    level_df = dfs_with_type[(ue == "HEAT") & (~is_total_heat)]
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
    def _is_non_default(series: pd.Series) -> bool:
        norm = series.fillna("").astype(str).str.strip().str.lower()
        return (norm != "") & (norm != "default")

    non_default_ue = _is_non_default(ddet_combined['UE_Type']).any()
    non_default_subtech = _is_non_default(ddet_combined['Subtech']).any()
    non_default_drive = _is_non_default(ddet_combined['Drive']).any()
    #  Identify valid groups based on case detection
    if non_default_ue and non_default_subtech and non_default_drive:
        # Case 1: All three columns have non-default values
        # Group by UE_Type-Drive pairs and expand with Subtechs
        ue_drive_pairs = (
            ddet_combined[
                (_is_non_default(ddet_combined['UE_Type'])) &
                (_is_non_default(ddet_combined['Drive']))
                ][['UE_Type', 'Drive']]
            .drop_duplicates()
        )
        # Extract non-default Subtech values
        subtechs = ddet_combined.loc[_is_non_default(ddet_combined['Subtech']), 'Subtech'].unique().tolist()
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
        # Keep only concrete UE types (exclude empty/default/NaN).
        ue_types = ddet_combined.loc[_is_non_default(ddet_combined['UE_Type']), 'UE_Type'].unique().tolist()
        valid_groups = [
            {'UE_Type': ut, 'Subtech': 'default', 'Drive': 'default'}
            for ut in ue_types
        ]

    elif non_default_ue and non_default_drive and not non_default_subtech:
        # Case 3: UE_Type and Drive are non-default, Subtech is default
        ue_drive_pairs = (
            ddet_combined[
                (_is_non_default(ddet_combined['UE_Type'])) &
                (_is_non_default(ddet_combined['Drive']))
                ][['UE_Type', 'Drive']]
            .drop_duplicates()
        )
        valid_groups = [
            {'UE_Type': pair['UE_Type'], 'Subtech': 'default', 'Drive': pair['Drive']}
            for _, pair in ue_drive_pairs.iterrows()
        ]
    else:
        # Fallback: Handle mixed cases or edge scenarios, generating all combinations of UE_Type, Subtech, and Drive.
        ue_types = ddet_combined.loc[_is_non_default(ddet_combined['UE_Type']), 'UE_Type'].unique().tolist()
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

