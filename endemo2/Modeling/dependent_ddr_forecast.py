import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
import ast


def _normalize_equation_for_scan(expr: Any) -> str:
    s = "" if expr is None else str(expr).strip()
    if not s:
        return ""
    if "=" in s:
        left, right = s.split("=", 1)
        if left.strip().lower() == "y":
            s = right.strip()
    return s.replace("^", "**")


def dependencies_used_in_equation(equation: Any, dependencies: List[str]) -> List[str]:
    """
    Return only those dependencies that are actually referenced by the equation.

    Supports references via:
      - direct dependency names (e.g. GDP, POP)
      - DDr1..DDrN (mapped to dependencies[0..N-1])

    If parsing fails, fall back to the full dependencies list (conservative).
    """
    expr = _normalize_equation_for_scan(equation)
    if not expr or not dependencies:
        return list(dependencies)
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return list(dependencies)

    dep_names = [str(d) for d in dependencies]
    dep_set = set(dep_names)

    used = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Name):
            continue
        name = str(node.id)
        if name in dep_set:
            used.add(name)
            continue
        nlow = name.lower()
        if nlow.startswith("ddr") and nlow[3:].isdigit():
            idx = int(nlow[3:])
            if 1 <= idx <= len(dep_names):
                used.add(dep_names[idx - 1])

    return [d for d in dep_names if d in used]


# Zweck:
#   Forecast / Berechnung für "abhängige" Demand Driver (DDrs), d.h. DDrs, die in
#   der Excel-Tabelle "Demand_Drivers" mindestens eine Abhängigkeit DDr1..DDrN
#   definiert haben.
#
#   Wichtig: Dieses Skript ist NUR für den DDr-Forecast gedacht (nicht ECU/DDet).
#   Es wird früh im Modellablauf aufgerufen, damit berechnete DDrs anschließend
#   als Input für ECU/DDet verwendet werden können.
#
# Unterstützte Cases (pro dependent DDr, pro Region):
#   A) Forecast data = "Historical"
#      - Koeffizienten werden aus der historischen Zeitreihe des dependent DDr
#        bestimmt (analog ECU/DDet), basierend auf den Dependency-DDrs.
#      - Danach werden die Werte für alle (sinnvollen) Jahre prognostiziert.
#
#   B) Forecast data = "User"
#      B1) User-Koeffizienten (k0..k4) sind gesetzt
#          - Es wird die vorhandene Forecast-Funktion verwendet (lin/exp/...), aber
#            die k-Werte kommen direkt aus Excel (keine Koeffizientenberechnung).
#      B2) Interpolation_points sind gesetzt (Function typischerweise "interp_lin")
#          - Es wird über die Punkte interpoliert; für INTERP_LIN ist nur 1 Dependency
#            erlaubt (1D-Interpolation entlang der DDr1-"x-Achse").
#
#   Hinweis:
#     Function == "user_function" wird als ganz normale Forecast-Funktion behandelt
#     (Auswertung zentral in endemo2.model.calc_functions)
#
# Regeln:
#   - Forecast startet erst nach dem letzten vorhandenen historischen Jahr des
#     dependent DDr (damit Hist-Daten nicht überschrieben werden).
#   - Es werden nur Jahre prognostiziert, in denen alle benötigten Dependency-DDrs
#     numerisch vorhanden sind (kein NaN) -> stabilere Vorhersagen.
#   - lower_limit und factor werden angewendet (wie bei ECU/DDet).

#   Wichtig: Ziel dieses Skripts ist es, den vorhandenen forecast algorithmus zu verwenden und diesen möglichst
#   unverändert zu lassen. Daher sind einige Mappings einmal für die DDr logik und einmal für die DDet logik vorhanden
#   Die forecast-logik der DDet/ECUs soll möglichst unveränder bleiben, daher ist dieses skript lang
# -----------------------------------------------------------------------------

from endemo2.Modeling.model_ECU_DDet import (
    map_filtered_demand_driver_data,
    calculate_coef_for_filtered_data,
    do_predictions,
    do_interpolation,
    reset_driver_mapping_caches,
)
from endemo2.Modeling.Methods import prediction_methods as pm
from endemo2.Modeling.Methods.prediction_methods import ForecastMethod
from endemo2.Input.model_config import META_COLUMNS
from endemo2.Input.loaders.common import is_default_value

# --- Hard-coded forecast defaults ---
DEFAULT_FORECAST_METHOD = ForecastMethod.CONST_LAST


# -----------------------------------------------------------------------------
# Hilfsfunktionen: Mapping / Koeffizientenlängen
# -----------------------------------------------------------------------------

#   Übersetzt den Excel-String (Function-Spalte) auf den internen ForecastMethod.
def map_function_name(func_name: str):
    """Map text from Excel to ForecastMethod; default to DEFAULT_FORECAST_METHOD."""
    if func_name is None:
        return DEFAULT_FORECAST_METHOD
    name = str(func_name).strip().upper()
    mapping = {
        "LIN": ForecastMethod.LIN,
        "EXP": ForecastMethod.EXP,
        "LOG": ForecastMethod.LOG,
        "LOG_SUM": ForecastMethod.LOG_SUM,
        "EXP_SUM": ForecastMethod.EXP_SUM,
        "POWER_SUM": ForecastMethod.POWER_SUM,
        "BASE_EXP_SUM": ForecastMethod.BASE_EXP_SUM,
        "CONST": ForecastMethod.CONST,
        "CONST_LAST": ForecastMethod.CONST_LAST,
        "CONST_MEAN": ForecastMethod.CONST_MEAN,
        "QUADR": ForecastMethod.QUADR,
        "POLY": ForecastMethod.POLY,
        "CONST_MULT_DIV": ForecastMethod.CONST_MULT_DIV,
        "LIN_MULT_DIV": ForecastMethod.LIN_MULT_DIV,
        "LIN_SHARE": ForecastMethod.LIN_SHARE,
        "EXP_MULT_DIV": ForecastMethod.EXP_MULT_DIV,
        "INTERP_LIN": ForecastMethod.INTERP_LIN,
        "MULT": ForecastMethod.MULT,
        "MULT_K0_ZERO": ForecastMethod.MULT_K0_ZERO,
        "USER_FUNCTION": ForecastMethod.USER_FUNCTION,
    }
    if name.startswith("USER_"):
        return ForecastMethod.USER_FUNCTION
    return mapping.get(name, DEFAULT_FORECAST_METHOD)


# Kurzbeschreibung:
#   Manche Funktionen erwarten eine feste Anzahl an Koeffizienten (z.B. EXP),
#   andere sind abhängig von der Anzahl Dependencies (z.B. LIN: k0 + k1*DDr1 + k2*DDr2 ...).
#   Im Code ist es also hart gecodet. Änderungen müssen ebenfalls hier übernommen werden
def expected_coeff_len(method_name: ForecastMethod, dependencies: list) -> int:
    """Return the expected number of coefficients for a given method."""
    # for lin, mult_k0_zero, mult the koefficians are lin(deps)+1
    if method_name == ForecastMethod.EXP:
        return 4  # k0, k1, k2, k3
    if method_name == ForecastMethod.LOG_SUM:
        return len(dependencies) + 1
    if method_name in {ForecastMethod.EXP_SUM, ForecastMethod.POWER_SUM, ForecastMethod.BASE_EXP_SUM}:
        return 1 + 2 * len(dependencies)
    if method_name == ForecastMethod.CONST:
        return 1
    if method_name in {ForecastMethod.CONST_LAST, ForecastMethod.CONST_MEAN}:
        return 1
    if method_name == ForecastMethod.CONST_MULT_DIV:
        return 1
    if method_name == ForecastMethod.LIN_MULT_DIV:
        return 3  # k0, k1, k2
    if method_name == ForecastMethod.EXP_MULT_DIV:
        return 4  # k0, k1, k2, k3
    if method_name == ForecastMethod.INTERP_LIN:
        return 0
    if method_name == ForecastMethod.USER_FUNCTION:
        return 0
    # Default: intercept + one coefficient per dependency
    return len(dependencies) + 1


# -----------------------------------------------------------------------------
# Hilfsfunktionen: sichere Auswertung für Function = "user_function"
# also für die selbst eingegebene Funktion, was ist erlaubt
#   will man anderer mathematische funktionen, müssen diese hier eingegeben werden
# -----------------------------------------------------------------------------

# Erlaubte Operatoren (bewusst eingeschränkt, damit keine beliebigen Python-Ausdrücke laufen)
_USER_FUNCTION_NOTE = (
    "Hinweis: Function == 'user_function' wird zentral in endemo2.model.calc_functions "
    "ausgewertet (calc_user_function)."
)

# Whitelist für Funktionen, die in der Equation genutzt werden dürfen



# Kurzbeschreibung:
#   Normalisiert den Equation-String:
#   - erlaubt "y = ..." und entfernt den "y =" Prefix
#   - ersetzt Excel-Potenzoperator "^" durch Python "**"

# Kurzbeschreibung:
#   Sichere Auswertung eines mathematischen Ausdrucks per AST.
#   Es sind nur numerische Konstanten, definierte Variablen (Context),
#   + - * / ** % und Whitelist-Funktionen erlaubt.
#   Die eingegebene Formel wird in eine Baumstruktur zerlegt. 
#   Wenn hier komplexere Formeln gebraucht werden, dann umbauen auf "sympy"! damit wären dann auch Ableitungen, Integrale usw besser möglich
#   AST variante guter mittelweg aus aufwand und nutzen

# -----------------------------------------------------------------------------
# Hilfsfunktionen: Zeitbereich / Validierung von Dependency-Daten
# -----------------------------------------------------------------------------

# Kurzbeschreibung:
#   Bestimmt das letzte Jahr, in dem die Time Series (erste Zeile) einen Wert (nicht NaN) hat.
#   Das nutzen wir, um den Forecast erst NACH dem letzten Hist-Jahr zu starten.
def max_non_nan_year(df: pd.DataFrame) -> Optional[int]:
    if df is None or df.empty:
        return None
    year_cols = [c for c in df.columns if str(c).isdigit()]
    if not year_cols:
        return None
    max_year = None
    for col in year_cols:
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        if vals.empty:
            continue
        y = int(str(col))
        if max_year is None or y > max_year:
            max_year = y
    return max_year


# Kurzbeschreibung:
#   Filtert eine Jahre-Liste auf die Jahre, für die ALLE Dependencies Werte haben.
#   Intern nutzen wir map_filtered_demand_driver_data (gleiches Mapping wie im Forecast).
def valid_years_for_dependencies(dependencies: list, years: list, region_name: str, data) -> List[int]:
    """
    Return years where all dependency drivers have numeric values (no NaN).
    Uses the existing mapping logic (and its year lookup rules).
    """
    if not years:
        return []
    ddr_df = map_filtered_demand_driver_data(dependencies, years, region_name, data)
    if ddr_df is None or ddr_df.empty:
        return []
    return [int(y) for y in ddr_df.index.tolist()]


# -----------------------------------------------------------------------------
# Gemeinsame Forecast-Logik (DDr + Subregional Division)
# -----------------------------------------------------------------------------

class _ForecastVariableStub:
    def __init__(self, name: str, region_name: str, hierarchy: Optional[Dict[str, Any]] = None):
        self.name = name
        self.region_name = region_name
        self.settings = {}
        self._hierarchy = hierarchy or {}

    def get_hierarchy(self):
        base = {
            "Variable": self.name,
            "Technology": None,
            "Subsector": None,
            "Sector": None,
            "Region": self.region_name,
        }
        for key in ["Sector", "Subsector", "Technology"]:
            if self._hierarchy.get(key) is not None:
                base[key] = self._hierarchy.get(key)
        return base


def _build_base_row(base_row: Optional[Dict[str, Any]], region_name: str, variable_name: str) -> Dict[str, Any]:
    row = dict(base_row or {})
    if "Region" not in row:
        row["Region"] = region_name
    if "Variable" not in row:
        row["Variable"] = variable_name
    return row


def _build_spec_trace(spec: Dict[str, Any], context_label: str, region_name: str, variable_name: str) -> str:
    """Build compact per-row trace text for dependent DDr/Subregional rows."""
    deps = spec.get("Dependencies") or []
    dep_txt = ",".join(str(d) for d in deps) if deps else "none"
    coeffs = spec.get("Coefficients") or {}
    coeff_txt = str(coeffs)
    if len(coeff_txt) > 160:
        coeff_txt = coeff_txt[:157] + "..."
    return (
        f"Context={context_label} | Region={region_name} | Variable={variable_name} | "
        f"ForecastData={spec.get('Forecast data')} | Function={spec.get('Function')} | "
        f"Drivers={dep_txt} | Equation={spec.get('Equation')} | Factor={spec.get('Factor')} | "
        f"LowerLimit={spec.get(META_COLUMNS['LOWER_LIMIT'])} | Coefficients={coeff_txt}"
    )


def _merge_hist_and_forecast(
    base_row: Dict[str, Any],
    hist_df: Optional[pd.DataFrame],
    preds_df: Optional[pd.DataFrame],
    years: List[int],
    prefer_forecast: bool = False,
) -> pd.DataFrame:
    def _rank_hist_rows(df: Optional[pd.DataFrame]) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        keys = [c for c in ["Sector", "Subsector", "Region"] if c in df.columns]
        if not keys:
            return df.copy()
        ranked = df.copy()
        ranked["__spec"] = ranked[keys].apply(
            lambda r: sum(0 if is_default_value(v) else 1 for v in r), axis=1
        )
        ranked = ranked.sort_values("__spec", ascending=False)
        return ranked.drop(columns=["__spec"], errors="ignore")

    def _last_non_nan(df: Optional[pd.DataFrame], year_key: str) -> float:
        if df is None or df.empty or year_key not in df.columns:
            return np.nan
        vals = pd.to_numeric(df[year_key], errors="coerce").dropna()
        if vals.empty:
            return np.nan
        return float(vals.iloc[-1])

    hist_vals: Dict[str, Any] = {}
    if hist_df is not None and not hist_df.empty:
        ranked_hist = _rank_hist_rows(hist_df)
        for col in ranked_hist.columns:
            if not str(col).isdigit():
                continue
            for _, hist_row in ranked_hist.iterrows():
                val = pd.to_numeric(hist_row[col], errors="coerce")
                if not pd.isna(val):
                    hist_vals[str(col)] = float(val)
                    break
    all_years = sorted(set(years) | {int(y) for y in hist_vals.keys()})
    row = dict(base_row)
    preds_cols = set()
    if preds_df is not None and not preds_df.empty:
        preds_cols = set(preds_df.columns)
    for y in all_years:
        y_str = str(y)
        pred_val = _last_non_nan(preds_df, y_str) if y_str in preds_cols else np.nan
        hist_val = hist_vals.get(y_str, np.nan)

        if prefer_forecast:
            if not pd.isna(pred_val):
                row[y_str] = pred_val
            elif not pd.isna(hist_val):
                row[y_str] = hist_val
            else:
                row[y_str] = np.nan
        else:
            if not pd.isna(hist_val):
                row[y_str] = hist_val
            elif not pd.isna(pred_val):
                row[y_str] = pred_val
            else:
                row[y_str] = np.nan
    ordered_years = [str(y) for y in sorted(all_years)]
    base_cols = [c for c in base_row.keys()]
    return pd.DataFrame([row], columns=base_cols + ordered_years)


def _apply_method_metadata(method: pm.Method, spec: Dict[str, Any]):
    method.factor = spec.get("Factor") if pd.notna(spec.get("Factor")) else 1
    method.equation = spec.get("Equation")
    ll_raw = spec.get(META_COLUMNS["LOWER_LIMIT"])
    try:
        method.lower_limit = float(ll_raw)
    except Exception:
        method.lower_limit = -np.inf
    method.ue_type = spec.get("UE_Type") if pd.notna(spec.get("UE_Type")) else None
    method.fe_type = spec.get("FE_Type") if pd.notna(spec.get("FE_Type")) else None
    method.temp_level = spec.get("Temp_level") if pd.notna(spec.get("Temp_level")) else None
    method.subtech = spec.get("Subtech") if pd.notna(spec.get("Subtech")) else None
    method.drive = spec.get("Drive") if pd.notna(spec.get("Drive")) else None


def _extract_last_numeric_year_value(df: Optional[pd.DataFrame]) -> Optional[float]:
    if df is None or df.empty:
        return None
    year_cols = sorted(
        [c for c in df.columns if str(c).isdigit()],
        key=lambda c: int(str(c)),
    )
    if not year_cols:
        return None

    keys = [c for c in ["Sector", "Subsector", "Region"] if c in df.columns]
    ranked = df.copy()
    if keys:
        ranked["__spec"] = ranked[keys].apply(
            lambda r: sum(0 if is_default_value(v) else 1 for v in r), axis=1
        )
        ranked = ranked.sort_values("__spec", ascending=False).drop(columns=["__spec"], errors="ignore")

    for col in reversed(year_cols):
        for _, hist_row in ranked.iterrows():
            val = pd.to_numeric(hist_row[col], errors="coerce")
            if not pd.isna(val):
                return float(val)
    return None


def _extract_last_user_year_value(spec: Dict[str, Any]) -> Optional[float]:
    interpolation_points = spec.get("Interpolation_points") or []
    valid_points = [
        (int(y), pd.to_numeric(v, errors="coerce"))
        for y, v in interpolation_points
        if not pd.isna(pd.to_numeric(v, errors="coerce"))
    ]
    if not valid_points:
        return None
    valid_points.sort(key=lambda item: item[0])
    return float(valid_points[-1][1])


def _build_const_last_method(spec: Dict[str, Any], dependencies: List[str]) -> pm.Method:
    method = pm.Method()
    method.demand_drivers_names = list(dependencies)
    method.name = ForecastMethod.CONST_LAST
    _apply_method_metadata(method, spec)
    return method


def _fallback_const_last_series(
    *,
    prefix: str,
    reason: str,
    spec: Dict[str, Any],
    dependencies: List[str],
    data,
    variable,
    base_row: Dict[str, Any],
    hist_df: Optional[pd.DataFrame],
    region_name: str,
    variable_name: str,
    settings_forecast_years: List[int],
) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    fallback_value = _extract_last_numeric_year_value(hist_df)
    if fallback_value is None:
        fallback_value = _extract_last_user_year_value(spec)

    if fallback_value is None:
        print(f"{prefix} {reason} No fallback value available for CONST_LAST in '{variable_name}' region '{region_name}'. Skipping.")
        return None, None

    forecast_years = list(settings_forecast_years)
    if not forecast_years:
        forecast_years = sorted(
            int(y) for y in (data.input_manager.general_settings.full_year_range or []) if pd.notna(y)
        )
    if not forecast_years:
        print(f"{prefix} {reason} No forecast years available for CONST_LAST in '{variable_name}' region '{region_name}'. Skipping.")
        return None, None

    method = _build_const_last_method(spec, dependencies)
    method.coefficients = [float(fallback_value)]
    method.equation = "y = const = y(t_hist)"

    print(
        f"{prefix} {reason} Falling back to CONST_LAST for '{variable_name}' in region '{region_name}' "
        f"with value {fallback_value}."
    )

    preds_df = do_predictions([method], variable, data, forecast_years)
    preds_df = preds_df.copy()
    preds_df.columns = preds_df.columns.map(str)

    series_df = _merge_hist_and_forecast(
        base_row,
        hist_df,
        preds_df,
        forecast_years,
        prefer_forecast=True,
    )
    return series_df, preds_df


def compute_dependent_series(
    spec: Dict[str, Any],
    data,
    region_name: str,
    variable_name: str,
    hist_df: Optional[pd.DataFrame],
    variable_obj: Optional[Any] = None,
    base_row: Optional[Dict[str, Any]] = None,
    context_label: str = "DDr",
):
    """
    Shared forecast logic for dependent series (DDrs and Subregional Division).
    Returns (series_df, forecast_df). If skipped, returns (None, None).
    """
    prefix = f"[{context_label} calc]"
    # Always keep a normalized copy of the configured forecast horizon
    # (used for User coefficient/user_function mode without historical merge).
    settings_forecast_years = sorted(
        {
            int(y)
            for y in (data.input_manager.general_settings.forecast_year_range or [])
            if pd.notna(y)
        }
    )
    forecast_flag = str(spec.get("Forecast data")).strip().lower() if spec.get("Forecast data") is not None else ""
    dependencies = spec.get("Dependencies") or []
    method_name = map_function_name(spec.get("Function"))

    allow_no_deps = method_name in {ForecastMethod.CONST, ForecastMethod.CONST_LAST, ForecastMethod.CONST_MEAN, ForecastMethod.USER_FUNCTION}
    if not dependencies and not allow_no_deps:
        return _fallback_const_last_series(
            prefix=prefix,
            reason="No dependencies for configured function.",
            spec=spec,
            dependencies=[],
            data=data,
            variable=variable_obj or _ForecastVariableStub(variable_name, region_name),
            base_row=_build_base_row(base_row, region_name, variable_name),
            hist_df=hist_df,
            region_name=region_name,
            variable_name=variable_name,
            settings_forecast_years=settings_forecast_years,
        )

    hierarchy = None
    if base_row:
        hierarchy = {
            "Sector": base_row.get("Sector"),
            "Subsector": base_row.get("Subsector"),
            "Technology": base_row.get("Technology"),
        }
    variable = variable_obj or _ForecastVariableStub(variable_name, region_name, hierarchy=hierarchy)
    base_row = _build_base_row(base_row, region_name, variable_name)
    if "Trace" not in base_row or pd.isna(base_row.get("Trace")):
        base_row["Trace"] = _build_spec_trace(spec, context_label, region_name, variable_name)

    # -------------------------------------------------------------------------
    # Case A) Forecast data == "Historical"
    # -------------------------------------------------------------------------
    if forecast_flag in {"historical", "hist"}:
        allowed_hist = {
            ForecastMethod.LIN,
            ForecastMethod.CONST_LAST,
            ForecastMethod.CONST_MEAN,
            ForecastMethod.LIN_SHARE,
            ForecastMethod.MULT_K0_ZERO,
            ForecastMethod.LOG_SUM,
            ForecastMethod.EXP_SUM,
            ForecastMethod.POWER_SUM,
            ForecastMethod.BASE_EXP_SUM,
        }
        if method_name not in allowed_hist:
            return _fallback_const_last_series(
                prefix=prefix,
                reason=f"Function '{spec.get('Function')}' not allowed for Historical.",
                spec=spec,
                dependencies=dependencies,
                data=data,
                variable=variable,
                base_row=base_row,
                hist_df=hist_df,
                region_name=region_name,
                variable_name=variable_name,
                settings_forecast_years=settings_forecast_years,
            )

        df_values = hist_df if hist_df is not None else pd.DataFrame()
        if df_values is None or df_values.empty:
            return _fallback_const_last_series(
                prefix=prefix,
                reason="No historical data.",
                spec=spec,
                dependencies=dependencies,
                data=data,
                variable=variable,
                base_row=base_row,
                hist_df=hist_df,
                region_name=region_name,
                variable_name=variable_name,
                settings_forecast_years=settings_forecast_years,
            )

        year_cols = [c for c in df_values.columns if str(c).isdigit()]
        hist_map: Dict[int, float] = {}
        keys = [c for c in ["Sector", "Subsector", "Region"] if c in df_values.columns]
        ranked_values = df_values.copy()
        if keys:
            ranked_values["__spec"] = ranked_values[keys].apply(
                lambda r: sum(0 if is_default_value(v) else 1 for v in r), axis=1
            )
            ranked_values = ranked_values.sort_values("__spec", ascending=False).drop(columns=["__spec"], errors="ignore")
        for col in year_cols:
            for _, hist_row in ranked_values.iterrows():
                val = pd.to_numeric(hist_row[col], errors="coerce")
                if not pd.isna(val):
                    hist_map[int(col)] = float(val)
                    break
        years = sorted(hist_map.keys())
        values = [hist_map[y] for y in years]
        if not years:
            return _fallback_const_last_series(
                prefix=prefix,
                reason="No historical values.",
                spec=spec,
                dependencies=dependencies,
                data=data,
                variable=variable,
                base_row=base_row,
                hist_df=hist_df,
                region_name=region_name,
                variable_name=variable_name,
                settings_forecast_years=settings_forecast_years,
            )
#        print(f"{prefix} Hist series for '{variable_name}' in region '{region_name}': {dict(zip(years, values))}")

        if dependencies:
            ddr_df = map_filtered_demand_driver_data(dependencies, years, region_name, data)
            if ddr_df is None or ddr_df.empty:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason="No dependency data for Historical forecast.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )
            y_series = pd.Series(values, index=years, dtype=float)
            common_years = []
            for y in y_series.index:
                if y in ddr_df.index:
                    row = ddr_df.loc[y]
                    if (not pd.isna(y_series.loc[y])) and row.notna().all():
                        common_years.append(y)
            if len(common_years) == 0:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason="No common years with valid dependency data.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )
            y_values = y_series.loc[common_years].tolist()
            X_values = ddr_df.loc[common_years].values
        else:
            common_years = years
            y_values = values
            X_values = np.array([])

        method = pm.Method()
        method.demand_drivers_names = dependencies
        method.name = method_name
        _apply_method_metadata(method, spec)
        method = calculate_coef_for_filtered_data(
            values=y_values,
            demand_driver_data=X_values,
            method=method,
            row=pd.DataFrame(),
            variable=variable,
        )
#        print(f"{prefix} Coefficients for '{variable_name}' in '{region_name}': {method.coefficients} equation: {method.equation}")

        dep_years = set()
        if dependencies:
            region_obj = data.get_region(region_name)
            for dep in dependencies:
                dep_var = region_obj.get_demand_driver(dep) if region_obj else None
                if dep_var and dep_var.demand_driver_data is not None:
                    dep_years.update({int(c) for c in dep_var.demand_driver_data.columns if str(c).isdigit()})
        if not dep_years:
            dep_years = set(data.input_manager.general_settings.full_year_range)
        forecast_years = sorted(dep_years | set(years))

        preds_df = do_predictions([method], variable, data, forecast_years)
        preds_df = preds_df.copy()
        preds_df.columns = preds_df.columns.map(str)

        all_years = sorted({int(y) for y in years} | set(forecast_years))
        series_df = _merge_hist_and_forecast(
            base_row,
            df_values,
            preds_df,
            all_years,
            prefer_forecast=True,
        )
        return series_df, preds_df

    # -------------------------------------------------------------------------
    # Case B) Forecast data == "User"
    # -------------------------------------------------------------------------
    if forecast_flag == "user":
        allowed_user = {
            ForecastMethod.LIN,
            ForecastMethod.EXP,
            ForecastMethod.CONST,
            ForecastMethod.CONST_MULT_DIV,
            ForecastMethod.LIN_MULT_DIV,
            ForecastMethod.EXP_MULT_DIV,
            ForecastMethod.MULT,
            ForecastMethod.MULT_K0_ZERO,
            ForecastMethod.INTERP_LIN,
            ForecastMethod.USER_FUNCTION,
            ForecastMethod.CONST_LAST,
            ForecastMethod.CONST_MEAN,
            ForecastMethod.LOG_SUM,
            ForecastMethod.EXP_SUM,
            ForecastMethod.POWER_SUM,
            ForecastMethod.BASE_EXP_SUM,
        }

        raw_coef_dict = spec.get("Coefficients") or {}
        k_vals: Dict[str, Any] = {}
        k_indices = set()
        for k, v in raw_coef_dict.items():
            k_str = str(k).strip().lower()
            if len(k_str) >= 2 and k_str[0] == "k" and k_str[1:].isdigit():
                idx = int(k_str[1:])
                k_vals[f"k{idx}"] = v
                k_indices.add(idx)
        has_k = any(pd.notna(v) for v in k_vals.values())
        max_k = max(k_indices) if k_indices else -1
        k_list = [0.0] * (max_k + 1) if max_k >= 0 else []
        for idx in sorted(k_indices):
            v = k_vals.get(f"k{idx}")
            if pd.notna(v):
                k_list[idx] = float(v)

        interpolation_points = spec.get("Interpolation_points") or []

        is_user_function = method_name == ForecastMethod.USER_FUNCTION
        deps_for_year_filter = (
            dependencies_used_in_equation(spec.get("Equation"), dependencies)
            if is_user_function
            else dependencies
        )
        dep_years = set()
        if deps_for_year_filter:
            region_obj = data.get_region(region_name)
            for dep in deps_for_year_filter:
                dep_var = region_obj.get_demand_driver(dep) if region_obj else None
                if dep_var and dep_var.demand_driver_data is not None:
                    dep_years.update({int(c) for c in dep_var.demand_driver_data.columns if str(c).isdigit()})
        if not dep_years:
            dep_years = set(data.input_manager.general_settings.full_year_range)

        # User coefficient/user_function mode:
        # forecast strictly on configured forecast years (no historical-year merge).
        candidate_years = list(settings_forecast_years)
        if not candidate_years:
            candidate_years = sorted(dep_years)
        forecast_years = (
            valid_years_for_dependencies(deps_for_year_filter, candidate_years, region_name, data)
            if deps_for_year_filter
            else candidate_years
        )
        if not forecast_years:
            forecast_years = candidate_years

        if has_k or is_user_function:
            method = pm.Method()
            # TIME is not injected implicitly. If TIME is needed, it must be
            # configured explicitly in DDr1..DDrN.
            method.demand_drivers_names = list(dependencies)
            method.name = method_name
            if method.name not in allowed_user:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason=f"Function '{spec.get('Function')}' not allowed for User.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )
            _apply_method_metadata(method, spec)

            if is_user_function and (method.equation is None or str(method.equation).strip() == ""):
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason="user_function selected but Equation is empty.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )

            if is_user_function:
                coeffs = list(k_list)
                if len(coeffs) < 5:
                    coeffs.extend([0.0] * (5 - len(coeffs)))
                method.coefficients = coeffs
            else:
                expected_len = expected_coeff_len(method.name, dependencies)
                coeffs = list(k_list)
                if len(coeffs) < expected_len:
                    coeffs.extend([0.0] * (expected_len - len(coeffs)))
                method.coefficients = coeffs[:expected_len]

            preds_df = do_predictions([method], variable, data, forecast_years)
            preds_df = preds_df.copy()
            preds_df.columns = preds_df.columns.map(str)

            # No merge with historical values for this path by design:
            # keep only forecast-year results from User coefficient/user_function input.
            series_df = _merge_hist_and_forecast(
                base_row,
                None,
                preds_df,
                forecast_years,
                prefer_forecast=True,
            )
            return series_df, preds_df

        if interpolation_points:
            if len(dependencies) != 1:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason=f"INTERP_LIN requires exactly 1 dependency (got {len(dependencies)}).",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )
            interpolation_points = [(y, pd.to_numeric(v, errors="coerce")) for y, v in interpolation_points if not pd.isna(v)]
            interpolation_points = sorted(interpolation_points, key=lambda t: t[0])
            if len(interpolation_points) < 2:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason="Not enough interpolation points.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )
            interp_years_list = [int(y) for y, _ in interpolation_points]
            if interp_years_list:
                # Ensure full interpolation span is forecasted (not only knot years),
                # so scenario points override historical values between them.
                span_start, span_end = min(interp_years_list), max(interp_years_list)
                interp_span_years = list(range(span_start, span_end + 1))
                valid_interp_span = (
                    valid_years_for_dependencies(dependencies, interp_span_years, region_name, data)
                    if dependencies
                    else interp_span_years
                )
                if valid_interp_span:
                    forecast_years = sorted(set(forecast_years) | set(valid_interp_span))
                else:
                    forecast_years = sorted(set(forecast_years) | set(interp_span_years))

            if not forecast_years:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason="No valid forecast years after filtering dependency data.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )

            ddr_df = map_filtered_demand_driver_data(dependencies, interp_years_list, region_name, data)
            if ddr_df is None or ddr_df.empty:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason="No dependency data for interpolation forecast.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )
            valid_rows = []
            y_vals = []
            for (year, y_val) in interpolation_points:
                if year in ddr_df.index:
                    row = ddr_df.loc[year]
                    if row.notna().all() and not pd.isna(y_val):
                        valid_rows.append(row.values)
                        y_vals.append(y_val)
            if len(valid_rows) < 2:
                return _fallback_const_last_series(
                    prefix=prefix,
                    reason="Not enough valid interpolation rows.",
                    spec=spec,
                    dependencies=dependencies,
                    data=data,
                    variable=variable,
                    base_row=base_row,
                    hist_df=hist_df,
                    region_name=region_name,
                    variable_name=variable_name,
                    settings_forecast_years=settings_forecast_years,
                )

            interp_points = [tuple(x) + (y_val,) for x, y_val in zip(valid_rows, y_vals)]
            interp_points = sorted(interp_points, key=lambda t: t[0])

            method = pm.Method()
            method.demand_drivers_names = dependencies
            method.name = ForecastMethod.INTERP_LIN
            method.interp_points = interp_points
            _apply_method_metadata(method, spec)

            preds_df = do_interpolation([method], variable, data, forecast_years)
            preds_df = preds_df.copy()
            preds_df.columns = preds_df.columns.map(str)

            series_df = _merge_hist_and_forecast(
                base_row,
                hist_df,
                preds_df,
                forecast_years,
                prefer_forecast=True,
            )
            return series_df, preds_df

        return _fallback_const_last_series(
            prefix=prefix,
            reason=f"Forecast data '{forecast_flag}' has neither coefficients nor interpolation points.",
            spec=spec,
            dependencies=dependencies,
            data=data,
            variable=variable,
            base_row=base_row,
            hist_df=hist_df,
            region_name=region_name,
            variable_name=variable_name,
            settings_forecast_years=settings_forecast_years,
        )

    return _fallback_const_last_series(
        prefix=prefix,
        reason=f"Forecast data '{forecast_flag}' not handled.",
        spec=spec,
        dependencies=dependencies,
        data=data,
        variable=variable,
        base_row=base_row,
        hist_df=hist_df,
        region_name=region_name,
        variable_name=variable_name,
        settings_forecast_years=settings_forecast_years,
    )

# -----------------------------------------------------------------------------
# Hauptfunktion: dependent DDr Forecast
# -----------------------------------------------------------------------------

# Kurzbeschreibung:
#   Läuft über alle dependent DDr Specs (aus dem Scenario-Sheet),
#   berechnet je nach Case die Forecast-Werte und schreibt sie in:
#     - variable.demand_driver_data  (wichtig, damit region.get_demand_driver(...) künftig Werte liefert)
#     - variable.forecast            (optional/Debug, ähnlich ECU/DDet)
#   Zusätzlich wird der DemandDriverData-Cache aktualisiert (für Export).
def forecast_dependent_ddrs(data):
    """
    Calculate coefficients and predictions for dependent DDrs (those with DDr* dependencies).
    Results are written into the variable.demand_driver_data and variable.forecast.
    """
    specs = getattr(data, "dependent_demand_driver_specs", {})
    if not specs:
        return
    reset_driver_mapping_caches()

    for (driver_name, region_name), spec in specs.items():
        region = data.get_region(region_name)
        if region is None:
#            print(f"[DDr calc] Region '{region_name}' not found for driver '{driver_name}'. Skipping.")
            continue
        variable = region.get_demand_driver(driver_name)
        if variable is None:
            print(f"[DDr calc] Variable '{driver_name}' not attached to region '{region_name}'. Skipping.")
            continue
        series_df, preds_df = compute_dependent_series(
            spec=spec,
            data=data,
            region_name=region_name,
            variable_name=driver_name,
            hist_df=variable.demand_driver_data,
            variable_obj=variable,
            base_row={"Variable": driver_name, "Region": region_name},
            context_label="DDr",
        )
        if series_df is None:
            continue
        variable.demand_driver_data = series_df
        if preds_df is not None:
            variable.forecast = preds_df
        driver_obj = data.demand_drivers.get(driver_name)
        if driver_obj:
            driver_obj._region_cache[region_name] = series_df


