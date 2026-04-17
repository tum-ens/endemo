from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from pathlib import Path
import os
import re
import pandas as pd
import numpy as np
from endemo2.Input.loaders.common import select_rows_with_default


class SubregionalOutputMixin:

    def _timeseries_channel_attr(self, channel: str) -> str:
        return "timeseries_results" if channel == "UE" else "timeseries_results_fe"

    def _log_subregional_error(self, channel: str, region: str, sector: str, subsector: str, message: str):
        key = (channel, region, str(sector), str(subsector), message)
        if key in self._subregion_distribution_errors:
            return
        self._subregion_distribution_errors.add(key)
        # Mapping diagnostics are tracked in-memory via _subregion_distribution_errors
        # but intentionally not printed to console.

    def _build_subregional_variable_map(self) -> dict:
        mapping = {}
        for region in self.data.regions:
            for sector in region.sectors:
                settings = getattr(sector, "settings", None)
                if settings is None or settings.empty:
                    continue
                if "Subregional_division" not in settings.columns:
                    continue
                for subsector_name, row in settings.iterrows():
                    val = row.get("Subregional_division")
                    if pd.isna(val) or str(val).strip() == "":
                        continue
                    key = (region.region_name, str(sector.name).strip(), str(subsector_name).strip())
                    mapping[key] = str(val).strip()
        return mapping

    def _match_distribution_rows(self, dist_df: pd.DataFrame, source_row: pd.Series, dist_var: str, region_name: str) -> pd.DataFrame:
        df = dist_df[dist_df["Region"].astype(str).str.strip() == str(region_name).strip()]
        target_var = self._norm_var(dist_var)
        df = df[df["Variable"].apply(self._norm_var) == target_var]
        if df.empty:
            return df

        # Primary resolver: same hierarchical default-mapping as DDr.
        # This enforces ordered priority instead of global "best score".
        def _resolve_with_default(criteria_keys: list[str]) -> pd.DataFrame:
            ordered = [k for k in criteria_keys if k in df.columns]
            if not ordered:
                return df
            criteria = {k: source_row.get(k) for k in ordered}
            return select_rows_with_default(df=df, criteria=criteria, ordered_columns=ordered)

        def _dedupe_best_per_subregion(input_df: pd.DataFrame, ordered_keys: list[str]) -> pd.DataFrame:
            """
            Keep only the most specific row per subregion.

            This is the final resolver step that avoids returning both exact and
            default matches for the same target subregion.
            """
            if input_df is None or input_df.empty:
                return input_df
            if "Subregion" not in input_df.columns:
                return input_df

            keys = [k for k in ordered_keys if k in input_df.columns]
            if not keys:
                return input_df

            ranked = input_df.copy()
            # Build a lexicographic specificity tuple in hierarchy order.
            # non-default (1) outranks default (0), earlier keys are more important.
            ranked["_spec_tuple"] = ranked[keys].apply(
                lambda r: tuple(0 if self._is_default(v) else 1 for v in r),
                axis=1,
            )
            ranked["_rowid"] = np.arange(len(ranked))
            ranked = ranked.sort_values(["Subregion", "_spec_tuple", "_rowid"], ascending=[True, False, True])
            ranked = ranked.drop_duplicates(subset=["Subregion"], keep="first")
            ranked = ranked.sort_values("_rowid")
            return ranked.drop(columns=["_spec_tuple", "_rowid"], errors="ignore")

        def _cell_matches_target(cell_value, target_value) -> bool:
            """Allow exact match or list-like match (comma/semicolon) in scenario cells."""
            if self._is_default(cell_value):
                return True
            if pd.isna(target_value):
                return False
            target = str(target_value).strip()
            if target == "":
                return False
            raw = str(cell_value).strip()
            if raw == target:
                return True
            # Support cells like "A, B, C" or "A;B;C"
            tokens = [t.strip() for t in re.split(r"[;,]", raw) if t.strip()]
            if not tokens:
                return False
            target_norm = target.casefold()
            return any(t.casefold() == target_norm for t in tokens)

        def _match_with_keys(input_df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
            out_df = input_df
            for col in keys:
                if col not in out_df.columns:
                    continue
                val = source_row.get(col)
                out_df = out_df[out_df[col].apply(lambda c: _cell_matches_target(c, val))]
                if out_df.empty:
                    return out_df
            if out_df.empty:
                return out_df
            spec_scores = []
            for _, row in out_df.iterrows():
                score = 0
                for col in keys:
                    if col not in out_df.columns:
                        continue
                    if not self._is_default(row.get(col)):
                        score += 1
                spec_scores.append(score)
            scored = out_df.copy()
            scored["_spec"] = spec_scores
            scored = scored[scored["_spec"] == scored["_spec"].max()]
            return scored.drop(columns=["_spec"], errors="ignore")

        # 1) Primary match: full metadata (keeps UE/Temp-specific distributions when defined)
        full_keys = ["Sector", "Subsector", "Technology", "UE_Type", "FE_Type", "Temp_level", "Subtech", "Drive"]
        matched = _resolve_with_default(full_keys)
        if not matched.empty:
            return _dedupe_best_per_subregion(matched, full_keys)

        # Compatibility fallback: legacy list-like cell matching ("A, B; C").
        matched = _match_with_keys(df, full_keys)
        if not matched.empty:
            return _dedupe_best_per_subregion(matched, full_keys)

        # 2) Fallback: subsector-level distribution (independent of energy type)
        base_keys = ["Sector", "Subsector", "Technology"]
        matched = _resolve_with_default(base_keys)
        if not matched.empty:
            return _dedupe_best_per_subregion(matched, base_keys)
        return _dedupe_best_per_subregion(_match_with_keys(df, base_keys), base_keys)

    def _prepare_distribution_weights(self, match_df: pd.DataFrame, year_cols: list) -> tuple[pd.DataFrame, bool]:
        weights = match_df[year_cols].apply(pd.to_numeric, errors="coerce")
        sums = weights.sum(axis=0, skipna=True)
        normalized = bool(((sums > 0) & ~(np.isclose(sums, 1.0, atol=1e-6) | np.isclose(sums, 100.0, atol=1e-4))).any())
        norm = weights.div(sums.where(sums > 0), axis=1).fillna(0.0)
        return norm, normalized

    def _collect_source_rows(self, channel: str) -> list:
        rows = []
        if channel == "FE":
            for region in self.data.regions:
                if region.energy_fe is None or region.energy_fe.empty:
                    continue
                for _, row in region.energy_fe.iterrows():
                    rows.append((region.region_name, row))
            return rows

        if channel == "UE":
            for region in self.data.regions:
                if region.energy_ue is None or region.energy_ue.empty:
                    continue
                for _, row in region.energy_ue.iterrows():
                    rows.append((region.region_name, row))
            return rows

        if channel == "ECU":
            for region in self.data.regions:
                for sector in region.sectors:
                    for subsector in sector.subsectors:
                        ecu = getattr(subsector, "ecu", None)
                        ecu_forecast = getattr(ecu, "forecast", None)
                        if ecu_forecast is None or ecu_forecast.empty:
                            self._log_subregional_error("ECU", region.region_name, sector.name, subsector.name, "Missing ECU forecast.")
                            continue
                        for _, ecu_row in ecu_forecast.iterrows():
                            row = ecu_row.copy()
                            row["Region"] = region.region_name
                            row["Sector"] = sector.name
                            row["Subsector"] = subsector.name
                            row["Technology"] = "default"
                            rows.append((region.region_name, row))
            return rows

        return rows

    def _compute_subregions(self, channel: str) -> pd.DataFrame:
        dist_df = getattr(self.data, "subregion_division_forecast", None)
        if dist_df is None or dist_df.empty:
            return pd.DataFrame()
        dist_map = self._build_subregional_variable_map()
        if not dist_map:
            return pd.DataFrame()

        year_cols = [str(c) for c in dist_df.columns if str(c).isdigit()]
        forecast_years = [str(y) for y in self.data.input_manager.general_settings.forecast_year_range]
        forecast_years = [y for y in forecast_years if y in year_cols]
        output_rows = []

        for region_name, source_row in self._collect_source_rows(channel):
            sector = str(source_row.get("Sector", "")).strip()
            subsector = str(source_row.get("Subsector", "")).strip()
            map_key = (region_name, sector, subsector)
            dist_var = dist_map.get(map_key)
            if not dist_var:
                self._log_subregional_error(channel, region_name, sector, subsector, "Missing 'Subregional_division' setting.")
                continue

            match_df = self._match_distribution_rows(dist_df, source_row, dist_var, region_name)
            if match_df.empty:
                self._log_subregional_error(
                    channel,
                    region_name,
                    sector,
                    subsector,
                    f"No subregional forecast rows found for distribution variable '{dist_var}'.",
                )
                continue

            expected_subs = set((self.data.subregions.get(region_name) or {}).keys())
            found_subs = set(match_df["Subregion"].astype(str).str.strip().tolist())
            if expected_subs and found_subs != expected_subs:
                missing = sorted(expected_subs - found_subs)
                extra = sorted(found_subs - expected_subs)
                self._log_subregional_error(
                    channel,
                    region_name,
                    sector,
                    subsector,
                    f"Subregion mismatch (missing={missing}, extra={extra}) for variable '{dist_var}'.",
                )
                continue

            norm_weights, normalized_flag = self._prepare_distribution_weights(match_df, year_cols)

            # Jahrspalten robust lesen: source_row kann Jahres-Keys als int oder str enthalten.
            source_series = source_row.copy()
            source_series.index = source_series.index.map(str)
            src_vals = pd.to_numeric(source_series.reindex(forecast_years), errors="coerce").astype(float)

            sub_values = norm_weights[forecast_years].mul(src_vals.values, axis=1)

            base_variable = source_row.get("Variable")
            if pd.isna(base_variable) or str(base_variable).strip() == "":
                if channel == "FE":
                    base_variable = source_row.get("FE_Type")
                elif channel == "UE":
                    base_variable = source_row.get("UE_Type")
                else:
                    base_variable = "ECU"

            source_trace = source_row.get("Trace")
            if pd.isna(source_trace):
                source_trace = ""
            base_trace = str(source_trace).strip()
            dist_trace = f"SubregionalDivision={dist_var}; Normalized={normalized_flag}"
            trace_value = f"{base_trace} | {dist_trace}" if base_trace else dist_trace

            meta = pd.DataFrame({
                "Region": region_name,
                "Subregion": match_df["Subregion"].values,
                "Sector": source_row.get("Sector"),
                "Subsector": source_row.get("Subsector"),
                "Variable": base_variable,
                "Technology": source_row.get("Technology"),
                "UE_Type": source_row.get("UE_Type"),
                "FE_Type": source_row.get("FE_Type"),
                "Temp_level": source_row.get("Temp_level"),
                "Subtech": source_row.get("Subtech"),
                "Drive": source_row.get("Drive"),
                "Trace": trace_value,
                "Distribution_variable": dist_var,
                "Normalized": normalized_flag,
            })
            out_df = pd.concat([meta, sub_values.reset_index(drop=True)], axis=1)
            output_rows.append(out_df)

        if not output_rows:
            return pd.DataFrame()
        return pd.concat(output_rows, ignore_index=True)

    def _prepare_subregional_energy_detail(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        out = df.copy()
        if "Variable" in out.columns:
            out = out.drop(columns=["Variable"])
        return out

    def _aggregate_subregional_energy(self, df: pd.DataFrame, channel: str, sector_name: str | None = None) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        work = df.copy()
        if sector_name is not None:
            work = work[work["Sector"].astype(str).str.strip() == str(sector_name).strip()]
        if work.empty:
            return pd.DataFrame()

        year_cols = [str(c) for c in work.columns if str(c).isdigit()]
        if not year_cols:
            return pd.DataFrame()

        energy_col = "UE_Type" if channel == "UE" else "FE_Type"
        group_cols = ["Region", "Subregion", energy_col, "Temp_level"]
        agg = work.groupby(group_cols, dropna=False)[year_cols].sum(min_count=1).reset_index()
        agg.insert(2, "Sector", sector_name if sector_name is not None else "ALL_SECTORS")
        return agg

    def _aggregate_fe_subregional_all_temp(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        work = df.copy()
        year_cols = [str(c) for c in work.columns if str(c).isdigit()]
        if not year_cols:
            return pd.DataFrame()

        ue_col = work.get("UE_Type", pd.Series(index=work.index, dtype=object)).fillna("").astype(str).str.strip().str.upper()
        temp_col = work.get("Temp_level", pd.Series(index=work.index, dtype=object)).fillna("").astype(str).str.strip()

        is_heat = ue_col == "HEAT"
        is_total_like = is_heat & ((temp_col.str.upper() == "TOTAL") | (temp_col == "") | (temp_col.str.lower() == "default"))
        is_heat_level = is_heat & (~is_total_like)

        group_cols = ["Region", "Subregion", "FE_Type"]
        parts = []

        non_heat = work[~is_heat]
        if not non_heat.empty:
            parts.append(non_heat.groupby(group_cols, dropna=False)[year_cols].sum(min_count=1).reset_index())

        heat_total = work[is_total_like]
        if not heat_total.empty:
            parts.append(heat_total.groupby(group_cols, dropna=False)[year_cols].sum(min_count=1).reset_index())

        heat_levels = work[is_heat_level]
        if not heat_levels.empty:
            level_agg = heat_levels.groupby(group_cols, dropna=False)[year_cols].sum(min_count=1).reset_index()
            if not heat_total.empty:
                total_keys = set(tuple(x) for x in heat_total[group_cols].drop_duplicates().itertuples(index=False, name=None))
                level_agg = level_agg[
                    ~level_agg[group_cols].apply(lambda r: tuple(r), axis=1).isin(total_keys)
                ]
            if not level_agg.empty:
                parts.append(level_agg)

        if not parts:
            return pd.DataFrame()

        agg = pd.concat(parts, ignore_index=True)
        agg = agg.groupby(group_cols, dropna=False)[year_cols].sum(min_count=1).reset_index()
        agg.insert(2, "Sector", "ALL_SECTORS")
        agg["Temp_level"] = "TOTAL"
        return agg

    def _write_subregional_energy_aggregates(self, writer, df: pd.DataFrame, channel: str):
        if df is None or df.empty or "Sector" not in df.columns:
            return

        active_sectors = list(getattr(self.data.input_manager.general_settings, "active_sectors", []) or [])
        present_sectors = [
            str(sec).strip() for sec in df["Sector"].dropna().astype(str).tolist()
            if str(sec).strip()
        ]

        sector_order = []
        seen = set()
        for sector_name in active_sectors + present_sectors:
            sector_str = str(sector_name).strip()
            if not sector_str or sector_str in seen:
                continue
            seen.add(sector_str)
            sector_order.append(sector_str)

        for sector_name in sector_order:
            sector_df = self._aggregate_subregional_energy(df, channel, sector_name=sector_name)
            if sector_df.empty:
                continue
            sector_df = self._standardize_output_layout(sector_df)
            self._prepare_non_timeseries_output(sector_df).to_excel(
                writer,
                sheet_name=str(sector_name)[:31],
                index=False,
            )

        total_df = self._aggregate_subregional_energy(df, channel, sector_name=None)
        if not total_df.empty:
            total_df = self._standardize_output_layout(total_df)
            self._prepare_non_timeseries_output(total_df).to_excel(
                writer,
                sheet_name="ALL_SECTORS",
                index=False,
            )

        if channel == "FE":
            total_sum_temp_df = self._aggregate_fe_subregional_all_temp(df)
            if not total_sum_temp_df.empty:
                total_sum_temp_df = self._standardize_output_layout(total_sum_temp_df)
                self._prepare_non_timeseries_output(total_sum_temp_df).to_excel(
                    writer,
                    sheet_name="TOTAL",
                    index=False,
                )

    def _write_ue_subregions(self):
        df = self._compute_subregions("UE")
        if df is None or df.empty:
            return
        df = self._prepare_subregional_energy_detail(df)
        df = self._filter_years_for_output(df)
        agg_source = df.copy()
        df = self._standardize_output_layout(df)
        subregional_dir = self.output_path / "subregional division"
        subregional_dir.mkdir(exist_ok=True)
        file_path = subregional_dir / "UE_Subregions.xlsx"
        with self._get_excel_writer(file_path) as writer:
            self._prepare_non_timeseries_output(df).to_excel(writer, sheet_name="UE_Subregions", index=False)
            self._write_subregional_energy_aggregates(writer, agg_source, channel="UE")

    def _write_fe_subregions(self):
        df = self._compute_subregions("FE")
        if df is None or df.empty:
            return
        df = self._prepare_subregional_energy_detail(df)
        df = self._filter_years_for_output(df)
        agg_source = df.copy()
        df = self._standardize_output_layout(df)
        subregional_dir = self.output_path / "subregional division"
        subregional_dir.mkdir(exist_ok=True)
        file_path = subregional_dir / "FE_Subregions.xlsx"
        with self._get_excel_writer(file_path) as writer:
            self._prepare_non_timeseries_output(df).to_excel(writer, sheet_name="FE_Subregions", index=False)
            self._write_subregional_energy_aggregates(writer, agg_source, channel="FE")

    def _write_ecu_subregions(self):
        df = self._compute_subregions("ECU")
        if df is None or df.empty:
            return
        df = self._filter_years_for_output(df)
        df = self._standardize_output_layout(df)
        subregional_dir = self.output_path / "subregional division"
        subregional_dir.mkdir(exist_ok=True)
        file_path = subregional_dir / "ECU_Subregions.xlsx"
        with self._get_excel_writer(file_path) as writer:
            self._prepare_non_timeseries_output(df).to_excel(writer, sheet_name="ECU_Subregions", index=False)

    def _write_subregional_timeseries_rows(self, channel: str = "UE"):
        dist_df = getattr(self.data, "subregion_division_forecast", None)
        if dist_df is None or dist_df.empty:
            return
        dist_map = self._build_subregional_variable_map()
        if not dist_map:
            return

        forecast_years = {str(y) for y in self.data.input_manager.general_settings.forecast_year_range}
        dist_year_cols = [str(c) for c in dist_df.columns if str(c).isdigit()]
        valid_years = [y for y in dist_year_cols if y in forecast_years]
        if not valid_years:
            return

        per_sector_enabled = self._is_enabled(self.data.input_manager.general_settings.timeseries_per_region)
        total_yearly = defaultdict(dict)
        sector_yearly = defaultdict(lambda: defaultdict(dict))

        def _merge_yearly_columns(dst: dict, src: dict):
            for year_str, cols in src.items():
                dst_bucket = dst.setdefault(year_str, {})
                for header, arr in cols.items():
                    if header in dst_bucket:
                        dst_bucket[header] += arr
                    else:
                        dst_bucket[header] = np.asarray(arr, dtype=np.float32).copy()

        def _merge_sector_yearly(dst: dict, src: dict):
            for sector_name, yearly in src.items():
                if sector_name not in dst:
                    dst[sector_name] = defaultdict(dict)
                _merge_yearly_columns(dst[sector_name], yearly)

        max_workers = min(max(1, (os.cpu_count() or 1)), max(1, len(self.data.regions)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self._process_subregional_timeseries_region,
                    region=region,
                    dist_df=dist_df,
                    dist_map=dist_map,
                    dist_year_cols=dist_year_cols,
                    valid_years=valid_years,
                    per_sector_enabled=per_sector_enabled,
                    channel=channel,
                )
                for region in self.data.regions
            ]
            for future in futures:
                region_total, region_sector, errors = future.result()
                _merge_yearly_columns(total_yearly, region_total)
                if per_sector_enabled:
                    _merge_sector_yearly(sector_yearly, region_sector)
                for err in errors:
                    self._log_subregional_error(*err)

        output_dir = self.output_path / "houerly timeserries" / "timeseries_subregions"
        output_dir.mkdir(exist_ok=True)
        self._write_subregional_columns_workbook(
            output_path=output_dir / f"timeseries_subregions_total_{channel}.xlsx",
            yearly_data=total_yearly,
        )

        if not per_sector_enabled:
            return
        by_sector_dir = output_dir / "by_sector"
        by_sector_dir.mkdir(exist_ok=True)
        for sector_name, yearly in sector_yearly.items():
            safe_name = str(sector_name).replace("/", "_").replace("\\", "_")
            self._write_subregional_columns_workbook(
                output_path=by_sector_dir / f"{safe_name}_{channel}.xlsx",
                yearly_data=yearly,
            )

    def _process_subregional_timeseries_region(
        self,
        region,
        dist_df: pd.DataFrame,
        dist_map: dict,
        dist_year_cols: list[str],
        valid_years: list[str],
        per_sector_enabled: bool,
        channel: str,
    ):
        region_total = defaultdict(dict)
        region_sector = defaultdict(lambda: defaultdict(dict))
        errors = []
        distribution_cache = {}
        region_name = region.region_name

        def _add(bucket: dict, year_key: str, header: str, values: np.ndarray):
            year_bucket = bucket.setdefault(year_key, {})
            if header in year_bucket:
                year_bucket[header] += values
            else:
                year_bucket[header] = values.copy()

        for sector in region.sectors:
            sector_name = str(sector.name)
            for subsector in sector.subsectors:
                subsector_name = str(subsector.name)
                dist_var = dist_map.get((region_name, sector_name, subsector_name))
                if not dist_var:
                    errors.append(("TIMESERIES", region_name, sector_name, subsector_name, "Missing 'Subregional_division' setting."))
                    continue

                for tech in subsector.technologies:
                    tech_profiles = getattr(tech, self._timeseries_channel_attr(channel), {}) or {}
                    for _, pdata in tech_profiles.items():
                        components = pdata.get("components", {})
                        ue_raw = str(components.get("UE_Type", "default"))
                        temp_raw = str(components.get("Temp_level", "default"))
                        if channel == "FE":
                            fe_raw = str(components.get("FE_Type", "default"))
                            commodity = fe_raw.capitalize()
                        else:
                            ue_disp = ue_raw.capitalize()
                            commodity = f"{ue_disp}_{temp_raw}" if ue_disp == "Heat" else ue_disp

                        cache_key = (
                            channel,
                            region_name,
                            sector_name,
                            subsector_name,
                            str(tech.name),
                            str(components.get("FE_Type", "default")),
                            ue_raw,
                            temp_raw,
                            dist_var,
                        )
                        if cache_key not in distribution_cache:
                            source_row = pd.Series({
                                "Region": region_name,
                                "Sector": sector_name,
                                "Subsector": subsector_name,
                                "Technology": tech.name,
                                "UE_Type": ue_raw,
                                "FE_Type": components.get("FE_Type"),
                                "Temp_level": temp_raw,
                                "Subtech": "default",
                                "Drive": "default",
                            })
                            match_df = self._match_distribution_rows(dist_df, source_row, dist_var, region_name)
                            if match_df.empty:
                                errors.append((
                                    "TIMESERIES",
                                    region_name,
                                    sector_name,
                                    subsector_name,
                                    f"No subregional forecast rows found for distribution variable '{dist_var}'.",
                                ))
                                distribution_cache[cache_key] = None
                            else:
                                expected_subs = set((self.data.subregions.get(region_name) or {}).keys())
                                found_subs = set(match_df["Subregion"].astype(str).str.strip().tolist())
                                if expected_subs and found_subs != expected_subs:
                                    missing = sorted(expected_subs - found_subs)
                                    extra = sorted(found_subs - expected_subs)
                                    errors.append((
                                        "TIMESERIES",
                                        region_name,
                                        sector_name,
                                        subsector_name,
                                        f"Subregion mismatch (missing={missing}, extra={extra}) for variable '{dist_var}'.",
                                    ))
                                    distribution_cache[cache_key] = None
                                else:
                                    norm_weights, _ = self._prepare_distribution_weights(match_df, dist_year_cols)
                                    subregions = match_df["Subregion"].astype(str).str.strip().tolist()
                                    weights_by_year = {}
                                    for year_str in valid_years:
                                        if year_str in norm_weights.columns:
                                            weights_by_year[year_str] = pd.to_numeric(
                                                norm_weights[year_str],
                                                errors="coerce",
                                            ).fillna(0.0).to_numpy(dtype=np.float32)
                                    distribution_cache[cache_key] = (subregions, weights_by_year)

                        distribution = distribution_cache.get(cache_key)
                        if distribution is None:
                            continue
                        subregions, weights_by_year = distribution

                        for year, ydata in (pdata.get("years", {}) or {}).items():
                            year_str = str(year)
                            if year_str not in valid_years:
                                continue
                            weights = weights_by_year.get(year_str)
                            if weights is None:
                                continue
                            hourly_region = np.asarray(ydata.get("hourly_values"), dtype=np.float32)
                            if hourly_region.size == 0:
                                continue
                            for idx_sub, subregion in enumerate(subregions):
                                share = float(weights[idx_sub]) if idx_sub < len(weights) else 0.0
                                if share == 0.0:
                                    continue
                                hourly_sub = hourly_region * share
                                header = f"{subregion}.{commodity}"
                                _add(region_total, year_str, header, hourly_sub)
                                if per_sector_enabled:
                                    _add(region_sector[sector_name], year_str, header, hourly_sub)

        return region_total, region_sector, errors

    def _write_subregional_columns_workbook(self, output_path: Path, yearly_data: dict):
        if not yearly_data:
            return
        with self._get_excel_writer(output_path) as writer:
            for year, columns in sorted(yearly_data.items(), key=lambda kv: str(kv[0])):
                if not columns:
                    continue
                max_len = max(len(arr) for arr in columns.values())
                prepared = {}
                for header, arr in columns.items():
                    vec = np.asarray(arr, dtype=np.float64)
                    if vec.size > max_len:
                        vec = vec[:max_len]
                    elif vec.size < max_len:
                        vec = np.pad(vec, (0, max_len - vec.size), constant_values=0.0)
                    total = float(np.nansum(vec))
                    prepared[header] = np.concatenate(([total], vec))

                df = pd.DataFrame(prepared)
                df.insert(0, "Hour", ["total"] + [str(i) for i in range(1, max_len + 1)])
                df.to_excel(writer, sheet_name=str(year)[:31], index=False)

