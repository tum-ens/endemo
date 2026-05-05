import pandas as pd


class SectorEnergyOutputMixin:


    def _append_sum_rows_per_energy_type(
        self,
        agg_df: pd.DataFrame,
        year_cols: list,
        type_col: str,
        sum_label_col: str = 'Temp_level',
        sum_label: str = 'SUM',
    ) -> pd.DataFrame:
        """Append one SUM row per energy-type block for aggregated tables."""
        if agg_df is None or agg_df.empty or type_col not in agg_df.columns:
            return agg_df
        if not year_cols:
            return agg_df

        cols = list(agg_df.columns)
        out_parts = []

        for energy_type, grp in agg_df.groupby(type_col, dropna=False, sort=False):
            grp_out = grp.copy()
            out_parts.append(grp_out)

            # SUM row should not double count HEAT/TOTAL.
            sum_source = grp_out
            if 'UE_Type' in grp_out.columns and 'Temp_level' in grp_out.columns:
                ue_col = grp_out['UE_Type'].fillna('').astype(str).str.strip().str.upper()
                tl_col = grp_out['Temp_level'].fillna('').astype(str).str.strip().str.upper()
                is_heat_total = (ue_col == 'HEAT') & ((tl_col == 'TOTAL') | (tl_col == 'DEFAULT') | (tl_col == ''))
                sum_source = grp_out[~is_heat_total]

            sum_values = sum_source[year_cols].apply(pd.to_numeric, errors='coerce').sum(axis=0, min_count=1).fillna(0.0)

            sum_row = {c: "" for c in cols}
            sum_row[type_col] = energy_type
            if sum_label_col in cols:
                sum_row[sum_label_col] = sum_label
            for y in year_cols:
                sum_row[y] = float(sum_values.get(y, 0.0))

            out_parts.append(pd.DataFrame([sum_row], columns=cols))

        return pd.concat(out_parts, ignore_index=True) if out_parts else agg_df


    def _append_region_sum_rows_per_energy_type(
        self,
        agg_df: pd.DataFrame,
        year_cols: list,
        type_col: str,
        region_col: str,
        label_col: str,
    ) -> pd.DataFrame:
        """Append one SUM_<Region> row per region inside each energy-type block."""
        if agg_df is None or agg_df.empty:
            return agg_df
        if type_col not in agg_df.columns or region_col not in agg_df.columns or label_col not in agg_df.columns:
            return agg_df
        if not year_cols:
            return agg_df

        cols = list(agg_df.columns)
        out_parts = []

        for energy_type, grp in agg_df.groupby(type_col, dropna=False, sort=False):
            grp_out = grp.copy()
            out_parts.append(grp_out)

            sum_source = grp_out
            if 'UE_Type' in grp_out.columns and 'Temp_level' in grp_out.columns:
                ue_col = grp_out['UE_Type'].fillna('').astype(str).str.strip().str.upper()
                tl_col = grp_out['Temp_level'].fillna('').astype(str).str.strip().str.upper()
                is_heat_total = (ue_col == 'HEAT') & ((tl_col == 'TOTAL') | (tl_col == 'DEFAULT') | (tl_col == ''))
                sum_source = grp_out[~is_heat_total]

            for region_value, region_grp in sum_source.groupby(region_col, dropna=False, sort=False):
                region_label = str(region_value).strip() if pd.notna(region_value) else ''
                if not region_label:
                    continue

                sum_values = (
                    region_grp[year_cols]
                    .apply(pd.to_numeric, errors='coerce')
                    .sum(axis=0, min_count=1)
                    .fillna(0.0)
                )

                sum_row = {c: "" for c in cols}
                sum_row[type_col] = energy_type
                sum_row[label_col] = f"SUM_{region_label}"
                for y in year_cols:
                    sum_row[y] = float(sum_values.get(y, 0.0))

                out_parts.append(pd.DataFrame([sum_row], columns=cols))

        return pd.concat(out_parts, ignore_index=True) if out_parts else agg_df


    def _aggregate_with_sum_rows(
        self,
        combined: pd.DataFrame,
        group_cols: list,
        year_cols: list,
        type_col: str,
        sum_mode: str = 'global',
        region_col: str = 'Region',
        label_col: str = 'UE_Type',
        sum_label_col: str = 'Temp_level',
        sum_label: str = 'SUM',
    ) -> pd.DataFrame:
        """Aggregate and append summary rows, then return as MultiIndex for legacy Excel look."""
        agg = combined.groupby(group_cols, as_index=False)[year_cols].sum()
        if sum_mode == 'per_region':
            agg = self._append_region_sum_rows_per_energy_type(
                agg,
                year_cols=year_cols,
                type_col=type_col,
                region_col=region_col,
                label_col=label_col,
            )
        else:
            agg = self._append_sum_rows_per_energy_type(
                agg,
                year_cols=year_cols,
                type_col=type_col,
                sum_label_col=sum_label_col,
                sum_label=sum_label,
            )
        return agg.set_index(group_cols)


    def _write_aggregate_sheet(
        self,
        writer,
        combined: pd.DataFrame,
        sheet_name: str,
        group_cols: list,
        year_cols: list,
        type_col: str,
        sum_mode: str = 'global',
        region_col: str = 'Region',
        label_col: str = 'UE_Type',
        sum_label_col: str = 'Temp_level',
        sum_label: str = 'SUM',
    ):
        """Write one aggregate sheet in legacy style (index + merged blocks)."""
        agg_idx = self._aggregate_with_sum_rows(
            combined,
            group_cols,
            year_cols,
            type_col,
            sum_mode=sum_mode,
            region_col=region_col,
            label_col=label_col,
            sum_label_col=sum_label_col,
            sum_label=sum_label,
        )
        agg_idx.to_excel(writer, sheet_name=sheet_name, merge_cells=True)


    def _energy_series_header(self, row: pd.Series, channel: str) -> str:
        def tok(v):
            if v is None:
                return "default"
            try:
                if pd.isna(v):
                    return "default"
            except Exception:
                pass
            s = str(v).strip()
            return s if s else "default"

        region = tok(row.get("Region"))
        sector = tok(row.get("Sector"))
        subsector = tok(row.get("Subsector"))
        technology = tok(row.get("Technology"))
        subtech = tok(row.get("Subtech"))
        drive = tok(row.get("Drive"))
        ue_type = tok(row.get("UE_Type"))
        temp_level = tok(row.get("Temp_level"))

        if channel == "FE":
            fe_type = tok(row.get("FE_Type"))
            parts = [region, sector, subsector, technology, subtech, drive, fe_type, ue_type, temp_level]
        else:
            parts = [region, sector, subsector, technology, subtech, drive, ue_type, temp_level]
        return "|".join(parts)

    def _write_energy_columnar_yearly(self, combined: pd.DataFrame, output_path, channel: str):
        if combined is None or combined.empty:
            return

        year_cols = [c for c in combined.columns if str(c).isdigit()]
        if not year_cols:
            return
        year_cols = sorted([str(c) for c in year_cols], key=lambda x: int(x))

        with self._get_excel_writer(output_path) as writer:
            # metadata sheet
            metadata_cols = [
                c for c in [
                    "Region", "Sector", "Subsector", "Technology", "Subtech", "Drive",
                    "UE_Type", "FE_Type", "Temp_level", "Variable", "Unit", "Trace"
                ] if c in combined.columns
            ]
            metadata = combined[metadata_cols].copy()
            metadata["Header"] = combined.apply(lambda r: self._energy_series_header(r, channel), axis=1)
            metadata = metadata.drop_duplicates(subset=["Header"], keep="first")
            metadata.to_excel(writer, sheet_name="Metadata", index=False)

            # one sheet per forecast year
            for year in year_cols:
                cols = {}
                for _, row in combined.iterrows():
                    header = self._energy_series_header(row, channel)
                    value = pd.to_numeric(row.get(year), errors="coerce")
                    if pd.isna(value):
                        value = 0.0
                    if header in cols:
                        cols[header] += float(value)
                    else:
                        cols[header] = float(value)

                if not cols:
                    continue

                # one-row sheet: each column is one series in that year
                df_year = pd.DataFrame([cols])
                df_year.insert(0, "year", year)
                df_year.to_excel(writer, sheet_name=str(year)[:31], index=False)

    def _write_energy_columnar_by_sector(self, combined: pd.DataFrame, output_path, channel: str):
        if combined is None or combined.empty or "Sector" not in combined.columns:
            return

        year_cols = [c for c in combined.columns if str(c).isdigit()]
        if not year_cols:
            return
        year_cols = sorted([str(c) for c in year_cols], key=lambda x: int(x))

        with self._get_excel_writer(output_path) as writer:
            metadata_cols = [
                c for c in [
                    "Region", "Sector", "Subsector", "Technology", "Subtech", "Drive",
                    "UE_Type", "FE_Type", "Temp_level", "Variable", "Unit", "Trace"
                ] if c in combined.columns
            ]
            metadata = combined[metadata_cols].copy()
            metadata["Header"] = combined.apply(lambda r: self._energy_series_header(r, channel), axis=1)
            metadata = metadata.drop_duplicates(subset=["Header"], keep="first")
            metadata.to_excel(writer, sheet_name="Metadata", index=False)

            used_sheet_names = set(["Metadata"])
            for sector_name, sector_df in combined.groupby("Sector", dropna=False):
                sector_label = str(sector_name) if pd.notna(sector_name) else "default"
                for year in year_cols:
                    cols = {}
                    for _, row in sector_df.iterrows():
                        header = self._energy_series_header(row, channel)
                        value = pd.to_numeric(row.get(year), errors="coerce")
                        if pd.isna(value):
                            value = 0.0
                        if header in cols:
                            cols[header] += float(value)
                        else:
                            cols[header] = float(value)

                    if not cols:
                        continue

                    df_year = pd.DataFrame([cols])
                    df_year.insert(0, "year", year)

                    base_name = f"{year}_{sector_label}"
                    sheet_name = base_name[:31]
                    counter = 1
                    while sheet_name in used_sheet_names:
                        suffix = f"_{counter}"
                        sheet_name = (base_name[: max(0, 31 - len(suffix))] + suffix)
                        counter += 1
                    used_sheet_names.add(sheet_name)
                    df_year.to_excel(writer, sheet_name=sheet_name, index=False)

    def collect_ue_data(self, regions):
        """Collect useful energy data from model_useful_energy structure"""
        for region in regions:
            if not region.energy_ue.empty:
                self._process_region_ue(region)

    def collect_fe_data(self, regions):
        """Collect final energy data from model_useful_energy structure"""
        for region in regions:
            if region.energy_fe is not None and not region.energy_fe.empty:
                self._process_region_fe(region)

    def _process_region_ue(self, region):
        """Process region-level UE data"""
        df = region.energy_ue
        for sector_name, sector_df in df.groupby('Sector'):
            self.ue_sector_data[sector_name].append(sector_df)

    def _process_region_fe(self, region):
        """Process region-level FE data"""
        df = region.energy_fe
        for sector_name, sector_df in df.groupby('Sector'):
            self.fe_sector_data[sector_name].append(sector_df)

    def collect_sector_forecasts(self, data):
        """Collect forecast data from model_forecast structure"""
        if data.efficiency_data:
            v1, v2 = data.efficiency_data
            forecast_eff = v1.forecast
            forecast_share = v2.forecast
            self.efficiency[v1.name].append(forecast_eff)
            self.efficiency[v2.name].append(forecast_share)

        for region in data.regions:
            for sector in region.sectors:
                for subsector in sector.subsectors:
                    self._process_subsector_data(region, sector, subsector)

    def _process_subsector_data(self, region, sector, subsector):
        """Process subsector-level data"""
        if subsector.ecu.forecast is not None:
            self._add_forecast_entry(region, sector, subsector, subsector.ecu, None)

        for tech in subsector.technologies:
            for var in tech.ddets:
                if var.forecast is not None:
                    self._add_forecast_entry(region, sector, subsector, var, tech.name)

    def _add_forecast_entry(self, region, sector, subsector, variable, technology):
        """Store one forecast dataframe entry; final column order is standardized on write."""
        df = variable.forecast.copy()
        df.columns = df.columns.astype(str)
        self.sector_forecasts[sector.name].append(df)

    def _write_sector_forecasts(self):
        """Write per-sector prediction files in standardized metadata layout."""
        sector_dir = self.output_path / "sector_forecasts"
        sector_dir.mkdir(exist_ok=True)

        for sector_name, dfs in self.sector_forecasts.items():
            if not dfs:
                continue
            combined = pd.concat(dfs, ignore_index=True)
            combined = self._filter_years_for_output(combined)
            combined = self._standardize_output_layout(combined)
            file_path = sector_dir / f"predictions_{sector_name}.xlsx"
            with self._get_excel_writer(file_path) as writer:
                self._prepare_non_timeseries_output(combined).to_excel(writer, sheet_name="Sheet1", index=False)

        for name, df_list in self.efficiency.items():
            if all(x is None for x in df_list):
                continue
            combined = pd.concat(df_list, ignore_index=True)
            combined = self._filter_years_for_output(combined)
            combined = self._standardize_output_layout(combined)
            file_path = sector_dir / f"predictions_{name}.xlsx"
            with self._get_excel_writer(file_path) as writer:
                self._prepare_non_timeseries_output(combined).to_excel(writer, sheet_name="Sheet1", index=False)




    def _write_ue_sector_data(self):
        """Write UE outputs per sector in legacy multi-sheet format."""
        for sector_name, dfs in self.ue_sector_data.items():
            valid = [df for df in dfs if df is not None and not df.empty]
            if not valid:
                continue

            combined = pd.concat(valid, ignore_index=True)
            combined = self._filter_years_for_output(combined)
            combined = self._standardize_output_layout(combined)

            year_cols = [c for c in combined.columns if str(c).isdigit()]
            year_cols = sorted(year_cols, key=lambda x: int(str(x)))

            file_path = self.output_path / f"UE_{sector_name}.xlsx"
            with self._get_excel_writer(file_path) as writer:
                self._prepare_non_timeseries_output(combined).to_excel(writer, sheet_name="UE_all", index=False)

                if year_cols:
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Sector_per_Region",
                        ['UE_Type', 'Temp_level', 'Region'], year_cols, type_col='UE_Type'
                    )
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Technology",
                        ['UE_Type', 'Temp_level', 'Subsector', 'Technology'], year_cols, type_col='UE_Type'
                    )
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Subsector",
                        ['UE_Type', 'Temp_level', 'Subsector'], year_cols, type_col='UE_Type'
                    )
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Sector",
                        ['UE_Type', 'Temp_level', 'Sector'], year_cols, type_col='UE_Type'
                    )


    def _write_fe_sector_data(self):
        """Write FE outputs per sector in legacy multi-sheet format."""
        for sector_name, dfs in self.fe_sector_data.items():
            valid = [df for df in dfs if df is not None and not df.empty]
            if not valid:
                continue

            combined = pd.concat(valid, ignore_index=True)
            combined = self._filter_years_for_output(combined)
            combined = self._standardize_output_layout(combined)

            year_cols = [c for c in combined.columns if str(c).isdigit()]
            year_cols = sorted(year_cols, key=lambda x: int(str(x)))

            file_path = self.output_path / f"FE_{sector_name}.xlsx"
            with self._get_excel_writer(file_path) as writer:
                self._prepare_non_timeseries_output(combined).to_excel(writer, sheet_name="FE_all", index=False)

                if year_cols:
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Sector_per_Region",
                        ['FE_Type', 'UE_Type', 'Temp_level', 'Region'], year_cols, type_col='FE_Type',
                        sum_mode='per_region', region_col='Region', label_col='UE_Type'
                    )
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Technology",
                        ['FE_Type', 'UE_Type', 'Temp_level', 'Subsector', 'Technology'], year_cols, type_col='FE_Type',
                        sum_label_col='UE_Type'
                    )
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Subsector",
                        ['FE_Type', 'UE_Type', 'Temp_level', 'Subsector'], year_cols, type_col='FE_Type',
                        sum_label_col='UE_Type'
                    )
                    self._write_aggregate_sheet(
                        writer, combined, "Aggregated_by_Sector",
                        ['FE_Type', 'UE_Type', 'Temp_level', 'Sector'], year_cols, type_col='FE_Type',
                        sum_label_col='UE_Type'
                    )


    def _write_combined_aggregate_workbook(self):
        """Write one additional workbook with UE/FE aggregate tables combined across all sectors."""
        ue_frames = [pd.concat([df for df in dfs if df is not None and not df.empty], ignore_index=True)
                     for _, dfs in self.ue_sector_data.items() if any(df is not None and not df.empty for df in dfs)]
        fe_frames = [pd.concat([df for df in dfs if df is not None and not df.empty], ignore_index=True)
                     for _, dfs in self.fe_sector_data.items() if any(df is not None and not df.empty for df in dfs)]

        ue_all = pd.concat(ue_frames, ignore_index=True) if ue_frames else pd.DataFrame()
        fe_all = pd.concat(fe_frames, ignore_index=True) if fe_frames else pd.DataFrame()

        if ue_all.empty and fe_all.empty:
            return

        if not ue_all.empty:
            ue_all = self._filter_years_for_output(ue_all)
            ue_all = self._standardize_output_layout(ue_all)
        if not fe_all.empty:
            fe_all = self._filter_years_for_output(fe_all)
            fe_all = self._standardize_output_layout(fe_all)

        year_cols_ue = [c for c in ue_all.columns if str(c).isdigit()] if not ue_all.empty else []
        year_cols_fe = [c for c in fe_all.columns if str(c).isdigit()] if not fe_all.empty else []
        year_cols_ue = sorted(year_cols_ue, key=lambda x: int(str(x)))
        year_cols_fe = sorted(year_cols_fe, key=lambda x: int(str(x)))

        out_path = self.output_path / "Aggregated_Comparison.xlsx"
        with self._get_excel_writer(out_path) as writer:
            if not ue_all.empty and year_cols_ue:
                self._write_aggregate_sheet(
                    writer, ue_all, 'UE_Agg_Sector_per_Region',
                    ['UE_Type', 'Temp_level', 'Region'], year_cols_ue, type_col='UE_Type'
                )
                self._write_aggregate_sheet(
                    writer, ue_all, 'UE_Agg_by_Sector',
                    ['UE_Type', 'Temp_level', 'Sector'], year_cols_ue, type_col='UE_Type'
                )

            if not fe_all.empty and year_cols_fe:
                self._write_aggregate_sheet(
                    writer, fe_all, 'FE_Agg_Sector_per_Region',
                    ['FE_Type', 'UE_Type', 'Temp_level', 'Region'], year_cols_fe, type_col='FE_Type',
                    sum_mode='per_region', region_col='Region', label_col='UE_Type'
                )
                self._write_aggregate_sheet(
                    writer, fe_all, 'FE_Agg_by_Sector',
                    ['FE_Type', 'UE_Type', 'Temp_level', 'Sector'], year_cols_fe, type_col='FE_Type',
                    sum_label_col='UE_Type'
                )

