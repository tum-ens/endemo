from concurrent.futures import ThreadPoolExecutor
import os
import time
import numpy as np
import pandas as pd


class TimeseriesOutputMixin:

    def _timeseries_channel_attr(self, channel: str) -> str:
        return "timeseries_results" if channel == "UE" else "timeseries_results_fe"

    def _get_profiles_by_channel(self, node, channel: str):
        results = getattr(node, self._timeseries_channel_attr(channel), None)
        if results is None:
            return {}
        return results.get("profiles", {}) if isinstance(results, dict) else {}

    def _has_channel_timeseries(self, channel: str) -> bool:
        for region in self.data.regions:
            if self._get_profiles_by_channel(region, channel):
                return True
        return False


    def _write_timeseries_data(self):
        if self.data.input_manager.general_settings.timeseries_forecast == 0:
            return
        print("Starting timeseries export...")
        start_time = time.time()
        hourly_dir = self.output_path / "houerly timeserries"
        hourly_dir.mkdir(exist_ok=True)

        # total workbook (region + UE/FE aggregation)
        self._write_timeseries_results(channel="UE", output_dir=hourly_dir)
        if self._is_enabled(self.data.input_manager.general_settings.FE_marker):
            self._write_timeseries_results(channel="FE", output_dir=hourly_dir)

        per_sector_enabled = self._is_enabled(self.data.input_manager.general_settings.timeseries_per_region)

        # by-sector output only when enabled:
        # - one workbook per region (Region_UE/Region_FE naming)
        if per_sector_enabled:
            directory = hourly_dir / "timeseries"
            directory.mkdir(exist_ok=True)
            self._write_per_region_timeseries(directory, channel="UE")
            if self._is_enabled(self.data.input_manager.general_settings.FE_marker):
                self._write_per_region_timeseries(directory, channel="FE")

        # Optional subregional output stays in row format.
        subregional_on = self._is_enabled(self.data.input_manager.general_settings.subregional_resolution)
        if subregional_on:
            self._write_subregional_timeseries_rows(channel="UE")
            if self._is_enabled(self.data.input_manager.general_settings.FE_marker):
                self._write_subregional_timeseries_rows(channel="FE")

        print(f"Timeseries export completed in {time.time() - start_time:.2f}s")
    def _write_dependent_ddrs(self):
        """Export dependent DDr metadata in standardized non-timeseries layout."""
        if not hasattr(self.data, "build_dependent_ddr_export"):
            return
        df = self.data.build_dependent_ddr_export()
        if df is None or df.empty:
            return
        df = self._filter_years_for_output(df)
        df = self._standardize_output_layout(df)
        forecast_dir = self.output_path / "DDr and Subregional forecasst"
        forecast_dir.mkdir(exist_ok=True)
        file_path = forecast_dir / "DemandDrivers_calculated.xlsx"
        with self._get_excel_writer(file_path) as writer:
            self._prepare_non_timeseries_output(df).to_excel(writer, sheet_name="Demand_drivers", index=False)

    def _write_subregion_division_forecast(self):
        df = getattr(self.data, "subregion_division_forecast", None)
        if df is None or df.empty:
            return
        df = self._filter_years_for_output(df)
        df = self._standardize_output_layout(df)
        forecast_dir = self.output_path / "DDr and Subregional forecasst"
        forecast_dir.mkdir(exist_ok=True)
        file_path = forecast_dir / "Subregional_Division_Forecast.xlsx"
        with self._get_excel_writer(file_path) as writer:
            self._prepare_non_timeseries_output(df).to_excel(writer, sheet_name="Subregional_division", index=False)

    def _ts_token(self, value, default="default") -> str:
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except Exception:
            pass
        text = str(value).strip()
        return text if text else default

    def _normalize_hourly_column_data(self, ydata) -> np.ndarray:
        """Return fixed-length array: [annual_total, h1..h8760]."""
        hourly_values = list(ydata.get("hourly_values", [])) if isinstance(ydata, dict) else []
        if len(hourly_values) > 8760:
            hourly_values = hourly_values[:8760]
        elif len(hourly_values) < 8760:
            hourly_values = hourly_values + [0.0] * (8760 - len(hourly_values))

        # Keep total row strictly consistent with the written hourly values.
        annual = float(np.nansum(hourly_values))
        return np.asarray([annual] + hourly_values, dtype=np.float64)



    def _build_timeseries_header(self, region_code: str, comp: dict, channel: str, mode: str = "detailed") -> str:
        region = self._ts_token(region_code).upper()
        sector = self._ts_token(comp.get("Sector")).upper()
        ue_type = self._ts_token(comp.get("UE_Type")).upper()
        temp_level = self._ts_token(comp.get("Temp_level")).upper()
        fe_type = self._ts_token(comp.get("FE_Type")).upper()

        # total workbook: region + commodity (keep heat split by level)
        if mode == "total":
            if channel == "FE":
                return f"{region}.{fe_type}"
            if ue_type == "HEAT":
                return f"{region}.HEAT.{temp_level}"
            return f"{region}.{ue_type}"

        # sector workbook: region + sector + commodity (heat split by level)
        if mode == "sector":
            if channel == "FE":
                return f"{region}.{sector}.{fe_type}"
            if ue_type == "HEAT":
                return f"{region}.{sector}.HEAT.{temp_level}"
            return f"{region}.{sector}.{ue_type}"

        # detailed fallback (debug/legacy use only)
        subsector = self._ts_token(comp.get("Subsector"))
        technology = self._ts_token(comp.get("Technology"))
        subtech = self._ts_token(comp.get("Subtech"))
        drive = self._ts_token(comp.get("Drive"))

        if channel == "FE":
            parts = [region, sector, subsector, technology, subtech, drive, fe_type, ue_type, temp_level]
        else:
            parts = [region, sector, subsector, technology, subtech, drive, ue_type, temp_level]
        return "|".join(parts)

    def _collect_timeseries_columns(self, channel: str, header_mode: str = "detailed", split_by_sector: bool = False):
        metadata = []
        yearly_data = {}  # year -> headers OR year -> sector -> headers

        for region in self.data.regions:
            profiles = self._get_profiles_by_channel(region, channel)
            if not profiles:
                continue

            for pid, pdata in profiles.items():
                comp = pdata.get("components", {})
                sector_name = self._ts_token(comp.get("Sector"))
                header = self._build_timeseries_header(region.code, comp, channel, mode=header_mode)

                metadata.append({
                    "Channel": channel,
                    "Region": region.code,
                    "Profile ID": pid,
                    "Header": header,
                    **comp,
                    "Sectors": ", ".join(pdata.get("contributors", {}).get("sectors", [])),
                    "Subsectors": ", ".join(pdata.get("contributors", {}).get("subsectors", [])),
                    "Techs": ", ".join(pdata.get("contributors", {}).get("technologies", [])),
                    "Subtechs": ", ".join(pdata.get("contributors", {}).get("subtechs", [])),
                    "Drives": ", ".join(pdata.get("contributors", {}).get("drives", [])),
                })

                for yr, ydata in (pdata.get("years", {}) or {}).items():
                    year_key = str(yr)
                    column_values = self._normalize_hourly_column_data(ydata)

                    if split_by_sector:
                        sector_bucket = yearly_data.setdefault(year_key, {}).setdefault(sector_name, {})
                        if header in sector_bucket:
                            sector_bucket[header] += column_values
                        else:
                            sector_bucket[header] = column_values.copy()
                    else:
                        year_bucket = yearly_data.setdefault(year_key, {})
                        if header in year_bucket:
                            year_bucket[header] += column_values
                        else:
                            year_bucket[header] = column_values.copy()

        return metadata, yearly_data

    def _write_columnar_sheet(self, writer, sheet_name: str, columns: dict):
        if not columns:
            return

        fixed_hours = 8760
        data = {}
        for header, arr in columns.items():
            vec = np.asarray(arr, dtype=np.float64)
            hourly = vec[1:] if vec.size > 0 else np.array([], dtype=np.float64)
            if hourly.size > fixed_hours:
                hourly = hourly[:fixed_hours]
            elif hourly.size < fixed_hours:
                hourly = np.pad(hourly, (0, fixed_hours - hourly.size), constant_values=0.0)

            total = float(np.nansum(hourly))
            data[header] = np.concatenate(([total], hourly))

        df = pd.DataFrame(data)
        df.insert(0, "Country_code.Commodity", ["total"] + [str(i) for i in range(1, fixed_hours + 1)])
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)


    def _write_timeseries_results(self, channel: str = "UE", output_dir=None):
        if not self._has_channel_timeseries(channel):
            return

        base_dir = output_dir or self.output_path
        output_path = base_dir / f"timeseries_total_{channel}.xlsx"
        metadata, yearly_data = self._collect_timeseries_columns(
            channel=channel,
            header_mode="total",
            split_by_sector=False,
        )

        with self._get_excel_writer(output_path) as writer:
            if metadata:
                pd.DataFrame(metadata).to_excel(writer, sheet_name="Metadata", index=False)
            for year in sorted(yearly_data.keys(), key=lambda y: int(y) if str(y).isdigit() else str(y)):
                self._write_columnar_sheet(writer, sheet_name=str(year), columns=yearly_data.get(year, {}))



    def _write_timeseries_results_by_sector(self, channel: str = "UE", output_dir=None):
        if not self._has_channel_timeseries(channel):
            return

        base_dir = output_dir or self.output_path
        output_path = base_dir / f"timeseries_by_sector_{channel}.xlsx"
        metadata, yearly_data = self._collect_timeseries_columns(
            channel=channel,
            header_mode="sector",
            split_by_sector=False,
        )

        with self._get_excel_writer(output_path) as writer:
            if metadata:
                pd.DataFrame(metadata).to_excel(writer, sheet_name="Metadata", index=False)

            # One sheet per year; sector split is encoded in header (e.g. DE.IND.HEAT.Q1)
            for year in sorted(yearly_data.keys(), key=lambda y: int(y) if str(y).isdigit() else str(y)):
                self._write_columnar_sheet(writer, sheet_name=str(year), columns=yearly_data.get(year, {}))


    def _write_per_region_timeseries(self, directory, channel: str = "UE"):
        """Per-region timeseries in columnar yearly format (aggregated by sector level)."""
        if not self._has_channel_timeseries(channel):
            return

        def process_region(region):
            profiles = self._get_profiles_by_channel(region, channel)
            if not profiles:
                return
            output_path = directory / f"{region.region_name}_{channel}.xlsx"

            metadata = []
            yearly_data = {}
            for pid, pdata in profiles.items():
                comp = pdata.get("components", {})
                header = self._build_timeseries_header(region.code, comp, channel, mode="sector")
                metadata.append({
                    "Channel": channel,
                    "Region": region.code,
                    "Profile ID": pid,
                    "Header": header,
                    **comp,
                    "Sectors": ", ".join(pdata.get("contributors", {}).get("sectors", [])),
                    "Subsectors": ", ".join(pdata.get("contributors", {}).get("subsectors", [])),
                    "Techs": ", ".join(pdata.get("contributors", {}).get("technologies", [])),
                    "Subtechs": ", ".join(pdata.get("contributors", {}).get("subtechs", [])),
                    "Drives": ", ".join(pdata.get("contributors", {}).get("drives", [])),
                })

                for yr, ydata in (pdata.get("years", {}) or {}).items():
                    year_key = str(yr)
                    year_bucket = yearly_data.setdefault(year_key, {})
                    col_data = self._normalize_hourly_column_data(ydata)
                    if header in year_bucket:
                        year_bucket[header] += col_data
                    else:
                        year_bucket[header] = col_data.copy()

            with self._get_excel_writer(output_path) as writer:
                if metadata:
                    pd.DataFrame(metadata).to_excel(writer, sheet_name="Metadata", index=False)
                for year in sorted(yearly_data.keys(), key=lambda y: int(y) if str(y).isdigit() else str(y)):
                    self._write_columnar_sheet(writer, sheet_name=str(year), columns=yearly_data.get(year, {}))

        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count())) as executor:
            list(executor.map(process_region, self.data.regions))

