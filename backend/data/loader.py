"""Excel ingestion layer.

This module is the ONLY place where the data source is read.
To replace Excel with live Snowflake execution data, swap the implementation
of `fetch_raw_data()` without touching any other module.
"""

import io
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional

import pandas as pd


# ------------------------------------------------------------
# Path configuration — default Excel
# ------------------------------------------------------------
DATA_PATH = Path(__file__).parent.parent / "query_to_be_optimised.xlsx"

# Runtime-uploaded file (bytes). When set, takes priority over DATA_PATH.
_uploaded_bytes: Optional[bytes] = None
_uploaded_filename: Optional[str] = None


# ------------------------------------------------------------
# Column name variants (case-insensitive). First match wins.
# ------------------------------------------------------------
COL_ALIASES = {
    "query_id": ["query_id", "queryid", "query_id", "id"],
    "query_text": ["query_text", "query", "sql", "sql_text"],
    "credits": ["credits", "credit", "snowflake_credits", "cost"],
}


# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------

def _fetch_raw_data() -> pd.DataFrame:
    """Load the Excel file — from uploaded bytes if available, else from disk.

    EXTENSIBILITY NOTE: Replace this function body with a Snowflake connector call,
    e.g.: conn = snowflake.connector.connect(...)
          df = pd.read_sql("SELECT query_id, query_text, credits FROM ...", conn)
    The rest of the module stays identical.
    """
    if _uploaded_bytes is not None:
        if _uploaded_filename and _uploaded_filename.lower().endswith(".csv"):
            return pd.read_csv(io.BytesIO(_uploaded_bytes), dtype=str)
        return pd.read_excel(io.BytesIO(_uploaded_bytes), dtype=str)

    if not DATA_PATH.exists():
        return pd.DataFrame()

    return pd.read_excel(DATA_PATH, dtype=str)


def _resolve_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Return a mapping of logical name -> actual column name in df.
    Matching is case-insensitive and alias-aware.

    Raises ValueError listing the actual columns if any required field cannot be matched.
    """
    actual = {c.strip(): c for c in df.columns}
    actual_lower = {k.lower().replace(" ", "_"): v for k, v in actual.items()}

    resolved: Dict[str, str] = {}
    missing: List[str] = []

    for logical, aliases in COL_ALIASES.items():
        matched = None
        for alias in aliases:
            if alias.lower() in actual_lower:
                matched = actual_lower[alias.lower()]
                break
        if matched:
            resolved[logical] = matched
        else:
            missing.append(logical)

    if missing:
        raise ValueError(
            f"Could not find columns for: {missing}.\n"
            f"Actual columns in Excel: {list(df.columns)}\n"
            f"Expected one of: { {k: v for k, v in COL_ALIASES.items() if k in missing} }"
        )

    return resolved


def _build_query_map(df: pd.DataFrame) -> Dict[str, dict]:
    """Group rows by Query Id, concatenate multi-row Query Text, keep Credits.
    Returns empty dict when df has no rows (no file uploaded yet).
    Forward-fills Query Id so multi-row queries are captured correctly.
    """
    if df.empty:
        return {}

    col = _resolve_columns(df)

    import numpy as np

    df[col["query_id"]] = df[col["query_id"]].replace("nan", np.nan).ffill()

    result: Dict[str, dict] = {}

    for query_id, group in df.groupby(col["query_id"], sort=False):
        qid = str(query_id).strip()
        if not qid or qid.lower() == "nan":
            continue

        text_parts = []
        for t in group[col["query_text"]]:
            s = str(t).strip().replace("\x00B", " ").replace("\r", " ").strip()
            if s and s.lower() != "nan":
                text_parts.append(s)

        query_text = " ".join(text_parts)

        credits = 0.0
        for c in group[col["credits"]]:
            s = str(c).strip()
            if s and s.lower() != "nan":
                try:
                    credits = float(s)
                    break
                except ValueError:
                    pass

        result[qid] = {
            "query_id": qid,
            "query_text": query_text,
            "credits": credits,
        }

    return result


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

@lru_cache(maxsize=1)
def _cached_queries() -> Dict[str, dict]:
    """Load and cache the query map for the lifetime of the process."""
    df = _fetch_raw_data()
    return _build_query_map(df)


def get_all_queries() -> Dict[str, dict]:
    return _cached_queries()


def get_query_ids() -> List[str]:
    return list(get_all_queries().keys())


def get_query(query_id: str) -> dict:
    queries = get_all_queries()
    if query_id not in queries:
        raise ValueError(
            f"Query ID '{query_id}' not found. Available: {list(queries.keys())}"
        )
    return queries[query_id]


def reload_cache() -> None:
    """Force-reload from source (e.g. after the Excel file is updated)."""
    _cached_queries.cache_clear()


def load_from_upload(content: bytes, filename: str) -> dict:
    """Store uploaded Excel bytes as the active data source, replacing the default file
    for the lifetime of this process.

    Returns a summary dict with query count and query IDs.
    """
    global _uploaded_bytes, _uploaded_filename
    _uploaded_bytes = content
    _uploaded_filename = filename
    _cached_queries.cache_clear()  # force re-parse from new bytes
    ids = get_query_ids()
    return {
        "filename": filename,
        "query_count": len(ids),
        "query_ids": ids,
    }


def get_active_source() -> str:
    """Return a label for whichever data source is currently active."""
    if _uploaded_filename:
        return _uploaded_filename
    return DATA_PATH.name


def get_debug_info() -> dict:
    """Return raw Excel metadata for diagnosing column issues."""
    if not DATA_PATH.exists():
        return {"error": f"File not found: {DATA_PATH}"}
    try:
        df = pd.read_excel(DATA_PATH, dtype=str, nrows=3)
        return {
            "file_path": str(DATA_PATH),
            "columns": list(df.columns),
            "row_count": len(df),
            "sample_rows": df.head(3).to_dict(orient="records"),
        }
    except Exception as exc:
        return {"error": str(exc)}
