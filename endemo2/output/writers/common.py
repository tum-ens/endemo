from pathlib import Path
import pandas as pd


class OutputCommonMixin:

    OUTPUT_LAYOUT_COLUMNS = [
        "Top_Region",
        "Region",
        "Subregion",
        "Subregion_name",
        "Sector",
        "Subsector",
        "Variable",
        "Technology",
        "UE_Type",
        "FE_Type",
        "Temp_level",
        "Subtech",
        "Drive",
        "Forecast data",
        "Function",
        "Equation",
        "DDr1",
        "DDr2",
        "DDr3",
        "Unit",
        "Factor",
        "Lower limit",
        "Comment",
        "Trace",
    ]

    OUTPUT_LAYOUT_ALIASES = {
        "Top-Region": "Top_Region",
        "Top Region": "Top_Region",
        "Subregion name": "Subregion_name",
        "Subregion Name": "Subregion_name",
        "Subregion_name": "Subregion_name",
        "Forecast_data": "Forecast data",
        "Forecast Data": "Forecast data",
        "Lower_limit": "Lower limit",
        "Lower Limit": "Lower limit",
    }

    def _is_enabled(self, value) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "x", "wahr", "ja"}
        return False

    def _norm_var(self, value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip().upper().replace(" ", "").replace("_", "")

    def _is_default(self, value) -> bool:
        if pd.isna(value):
            return True
        s = str(value).strip().lower()
        return s in {"", "default", "none", "nan"}

    def _trace_enabled(self) -> bool:
        settings = getattr(getattr(self.data, 'input_manager', None), 'general_settings', None)
        if settings is None:
            return True
        return self._is_enabled(getattr(settings, 'trace_output', None))

    def _filter_years_for_output(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        years = self.data.input_manager.general_settings.forecast_year_range
        year_cols = [c for c in df.columns if str(c).isdigit()]
        keep_years = [str(y) for y in years if str(y) in {str(c) for c in year_cols}]
        non_year = [c for c in df.columns if c not in year_cols]
        if not year_cols:
            return df
        rename_map = {c: str(c) for c in year_cols}
        df = df.rename(columns=rename_map)
        cols = non_year + [y for y in keep_years if y in df.columns]
        return df.loc[:, cols]

    def _normalize_output_column_aliases(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df
        if not self.OUTPUT_LAYOUT_ALIASES:
            return df
        rename_map = {}
        for col in df.columns:
            mapped = self.OUTPUT_LAYOUT_ALIASES.get(str(col), str(col))
            rename_map[col] = mapped
        return df.rename(columns=rename_map)

    def _extract_sorted_year_columns(self, df: pd.DataFrame) -> list[str]:
        if df is None or df.empty:
            return []
        year_cols = [c for c in df.columns if str(c).isdigit()]
        if not year_cols:
            return []
        rename_map = {c: str(c) for c in year_cols}
        df.rename(columns=rename_map, inplace=True)
        return sorted([str(c) for c in df.columns if str(c).isdigit()], key=lambda x: int(x))

    def _standardize_output_layout(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Unify non-timeseries output layout to match input-style metadata ordering.

        - Ensures all standard metadata columns exist (filled with empty values when missing).
        - Keeps year columns sorted numerically after metadata.
        - Preserves any additional columns at the end.
        """
        if df is None or df.empty:
            return df

        out = self._normalize_output_column_aliases(df.copy())
        year_cols = self._extract_sorted_year_columns(out)

        trace_enabled = self._trace_enabled()
        layout_cols = self.OUTPUT_LAYOUT_COLUMNS if trace_enabled else [c for c in self.OUTPUT_LAYOUT_COLUMNS if c != "Trace"]

        for col in layout_cols:
            if col not in out.columns:
                out[col] = pd.NA

        if not trace_enabled and "Trace" in out.columns:
            out = out.drop(columns=["Trace"])

        fixed_cols = [c for c in layout_cols if c != "Trace"]
        fixed_set = set(fixed_cols)
        year_set = set(year_cols)
        extra_cols = [c for c in out.columns if c not in fixed_set and c not in year_set and c != "Trace"]

        ordered_cols = fixed_cols + year_cols + extra_cols
        if trace_enabled:
            if "Trace" not in out.columns:
                out["Trace"] = pd.NA
            ordered_cols = ordered_cols + ["Trace"]

        return out.loc[:, ordered_cols]

    def _drop_empty_output_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove columns that are completely empty in non-timeseries Excel outputs."""
        if df is None or df.empty:
            return df
        cleaned = df.replace(r"^\s*$", pd.NA, regex=True)
        return cleaned.dropna(axis=1, how="all")

    def _prepare_non_timeseries_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply common non-timeseries export cleanup without touching hourly timeseries."""
        if df is None or df.empty:
            return df
        out = df.copy()
        if not self._trace_enabled() and "Trace" in out.columns:
            out = out.drop(columns=["Trace"])
        return self._drop_empty_output_columns(out)

    def _write_large_excel(self, df, writer, base_sheet_name):
        """Modified writer that handles unsorted data"""
        max_rows = 1_000_000
        chunks = (len(df) // max_rows) + 1
        for i in range(chunks):
            chunk = df.iloc[i * max_rows: (i + 1) * max_rows]
            chunk = self._prepare_non_timeseries_output(chunk)
            sheet_name = f"{base_sheet_name}_part{i + 1}" if chunks > 1 else base_sheet_name
            chunk.to_excel(
                writer,
                sheet_name=sheet_name[:31],
                index=False,
                header=True,
                startrow=0
            )

    def _get_excel_writer(self, output_path: Path):
        """
        Return an ExcelWriter with fallback.

        Use xlsxwriter when available. If unavailable, fall back to openpyxl.
        """
        try:
            return pd.ExcelWriter(output_path, engine="xlsxwriter")
        except Exception:
            return pd.ExcelWriter(output_path, engine="openpyxl")

