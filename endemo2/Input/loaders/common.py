"""
Common helpers for input loader modules.

This module centralizes small utilities that are shared across
the loader layer (DDr, subregions, sector profiles, efficiencies). Keeping them
here avoids circular imports and keeps loader code focused on data reading and
validation.
"""

from __future__ import annotations

import re
from typing import Iterable, Any, Optional
import pandas as pd


def split_tokens(value) -> list[str]:
    """
    Split a cell value into tokens.

    Supports both comma and semicolon as separators to remain compatible
    with legacy sheets that used commas for list-like cells.
    """
    if value is None:
        return []
    if isinstance(value, float) and value != value:  # NaN
        return []
    if isinstance(value, str):
        parts = re.split(r"[;,]", value)
        return [p.strip() for p in parts if p.strip()]
    return [str(value).strip()]


def match_any(cell, target_list: Iterable[str]) -> bool:
    """
    Return True if any token in cell matches any item in target_list.
    """
    tokens = split_tokens(cell)
    if not tokens:
        return False
    targets = [t.strip() for t in target_list]
    return any(token in targets for token in tokens)


def keep_only_matching(cell, target_list: Iterable[str]) -> str:
    """
    Filter a list-like cell to only keep items that exist in target_list.

    The output is normalized to comma-separated values for consistency
    with the legacy loader behavior.
    """
    tokens = split_tokens(cell)
    targets = [t.strip() for t in target_list]
    matches = [token for token in tokens if token in targets]
    return ", ".join(matches)


def parse_cell_content(cell_value) -> list[str]:
    """
    Normalize a list-like cell into a list of tokens.

    Accepts comma- or semicolon-separated values and trims whitespace.
    """
    return split_tokens(cell_value)


def is_default_value(value: Any) -> bool:
    """
    Return True if value should be treated as a generic fallback.

    Fallback markers are:
    - empty / None / NaN
    - the literal string "default" (case-insensitive)
    """
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    text = str(value).strip()
    if text == "":
        return True
    return text.lower() == "default"


def _normalize_match_value(value: Any) -> Optional[str]:
    """
    Normalize a value for deterministic matching.

    Non-default values are compared case-insensitively with trimmed whitespace.
    Default-like values return None.
    """
    if is_default_value(value):
        return None
    return str(value).strip().casefold()


def select_rows_with_default(df, criteria: dict[str, Any], ordered_columns: list[str]):
    """
    Hierarchisches Matching mit Default-Fallback.

    Idee:
    - Wir gehen Spalte fuer Spalte in `ordered_columns` durch.
    - Pro Spalte gilt: exakt vor default.
    - Wenn exakt + default gleichzeitig existieren, behalten wir default nur
      fuer Kombinationen, die von exakt noch nicht abgedeckt sind.

    Wichtiger Hinweis:
    - Doppelte, fachlich widerspruechliche Input-Zeilen werden hier nicht
      "geloest". Welche Zeile spaeter wirkt, entscheidet der weitere Ablauf.
    """
    if df is None or getattr(df, "empty", True):
        return df

    # Nur Spalten betrachten, die im DataFrame wirklich existieren.
    scoped_columns = [c for c in ordered_columns if c in df.columns]
    current = df.copy()

    # Diese Spalten definieren zusammen eine "Signatur" einer Zeile.
    # Damit erkennen wir, ob ein default-Eintrag fuer eine konkrete Kombination
    # noch gebraucht wird oder schon durch einen exakten Treffer ersetzt wurde.
    signature_candidates = [
        "Region",
        "Subregion",
        "Sector",
        "Subsector",
        "Variable",
        "Technology",
        "UE_Type",
        "FE_Type",
        "Temp_level",
        "Subtech",
        "Drive",
    ]

    def _normalize_signature_value(value: Any) -> str:
        """Normalisiert Signaturwerte fuer stabile Vergleiche."""
        if value is None:
            return "__none__"
        if isinstance(value, float) and value != value:  # NaN
            return "__nan__"
        text = str(value).strip()
        if text == "":
            return "__blank__"
        return text.casefold()

    # Hierarchischer Filterlauf (z. B. Sector -> Subsector -> Region).
    for column in scoped_columns:
        target = criteria.get(column)

        # Wenn das Kriterium selbst "default" ist, akzeptieren wir nur
        # default-Zeilen in dieser Spalte.
        if is_default_value(target):
            default_only = current[current[column].apply(is_default_value)]
            if default_only.empty:
                return current.iloc[0:0]
            current = default_only
            continue

        # Exakten Treffer (normalisiert, case-insensitiv) bestimmen.
        target_norm = _normalize_match_value(target)
        col_norm = current[column].apply(_normalize_match_value)
        exact_df = current[col_norm == target_norm]

        # Default-Kandidaten parallel bestimmen.
        default_df = current[current[column].apply(is_default_value)]

        # Nichts gefunden -> leer zurueck.
        if exact_df.empty and default_df.empty:
            return current.iloc[0:0]

        # Nur default vorhanden -> default nehmen.
        if exact_df.empty:
            current = default_df
            continue

        # Nur exakt vorhanden -> exakt nehmen.
        if default_df.empty:
            current = exact_df
            continue

        # Exakt + default vorhanden:
        # default nur fuer noch nicht abgedeckte Kombinationen behalten.
        sig_cols = [c for c in signature_candidates if c in current.columns and c != column]
        if not sig_cols:
            current = exact_df
            continue

        exact_sigs = set(
            exact_df[sig_cols].apply(
                lambda row: tuple(_normalize_signature_value(row[c]) for c in sig_cols),
                axis=1,
            ).tolist()
        )
        default_sigs = default_df[sig_cols].apply(
            lambda row: tuple(_normalize_signature_value(row[c]) for c in sig_cols),
            axis=1,
        )

        # Default-Zeilen mit schon vorhandener exakter Signatur verwerfen.
        default_keep = default_df.loc[~default_sigs.isin(exact_sigs)]

        if default_keep.empty:
            current = exact_df.reset_index(drop=True)
        else:
            current = pd.concat([exact_df, default_keep], ignore_index=True)

    return current


def parse_year_label(col: Any) -> Optional[str]:
    """
    Parse a column label into its base year string.

    Accepts plain year labels and pandas-renamed duplicates
    (e.g. '2100.1' -> '2100'). Returns None for non-year columns.
    """
    base = str(col).strip().split(".", 1)[0].strip()
    return base if base.isdigit() else None


def contiguous_year_blocks(columns: list[Any]) -> list[list[Any]]:
    """
    Return contiguous blocks of year-like columns by header position.

    A block is defined by adjacent column positions where each column can be
    parsed as a year via parse_year_label().
    """
    year_positions = []
    for idx, col in enumerate(columns):
        if parse_year_label(col) is not None:
            year_positions.append((idx, col))

    if not year_positions:
        return []

    blocks: list[list[Any]] = []
    current: list[Any] = [year_positions[0][1]]
    prev_idx = year_positions[0][0]

    for idx, col in year_positions[1:]:
        if idx == prev_idx + 1:
            current.append(col)
        else:
            blocks.append(current)
            current = [col]
        prev_idx = idx

    blocks.append(current)
    return blocks


def select_longest_year_block(columns: list[Any]) -> list[Any]:
    """
    Select the best long time-series block from a column list.

    Priority:
    1) largest contiguous block length
    2) largest max year in that block
    3) rightmost block position (implicit via first occurrence order)
    """
    blocks = contiguous_year_blocks(columns)
    if not blocks:
        return []

    indexed_blocks = [(i, block) for i, block in enumerate(blocks)]

    def block_key(item: tuple[int, list[Any]]) -> tuple[int, int, int]:
        block_idx, block_cols = item
        years = [int(parse_year_label(c)) for c in block_cols if parse_year_label(c) is not None]
        max_year = max(years) if years else -1
        return (len(block_cols), max_year, block_idx)

    _, best_block = max(indexed_blocks, key=block_key)
    return best_block


def extract_long_series_columns(columns: list[Any]) -> tuple[list[Any], list[Any]]:
    """
    Split columns into metadata + selected long year-series columns.
    """
    long_year_cols = select_longest_year_block(columns)
    metadata_cols = [c for c in columns if parse_year_label(c) is None]
    return metadata_cols, long_year_cols


def extract_years_from_selected_long_block(columns: list[Any]) -> set[int]:
    """
    Return years contained in the selected long year block.
    """
    long_cols = select_longest_year_block(columns)
    years = set()
    for col in long_cols:
        year = parse_year_label(col)
        if year is not None:
            years.add(int(year))
    return years
