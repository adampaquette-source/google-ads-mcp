"""Shared helpers for reporting functions."""

from __future__ import annotations


_VALID_PRESETS = {
    "TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_14_DAYS", "LAST_30_DAYS",
    "LAST_BUSINESS_WEEK", "THIS_WEEK_SUN_TODAY", "LAST_WEEK_SUN_SAT",
    "THIS_MONTH", "LAST_MONTH", "LAST_QUARTER", "LAST_YEAR",
}


def date_range_clause(date_range: str | dict) -> str:
    """Convert a date_range argument into a GAQL WHERE snippet.

    Accepts:
      - preset string: "LAST_30_DAYS", "LAST_7_DAYS", "THIS_MONTH", etc.
      - dict with "start_date" and "end_date" keys: {"start_date": "2024-01-01", "end_date": "2024-01-31"}

    Returns a GAQL fragment ready to embed in a WHERE clause, e.g.:
      "segments.date DURING LAST_30_DAYS"
      "segments.date BETWEEN '2024-01-01' AND '2024-01-31'"
    """
    if isinstance(date_range, str):
        upper = date_range.strip().upper()
        if upper not in _VALID_PRESETS:
            raise ValueError(
                f"Unknown date range preset {date_range!r}. "
                f"Valid presets: {sorted(_VALID_PRESETS)}"
            )
        return f"segments.date DURING {upper}"

    if isinstance(date_range, dict):
        start = date_range.get("start_date")
        end = date_range.get("end_date")
        if not start or not end:
            raise ValueError(
                "date_range dict must have 'start_date' and 'end_date' keys, "
                f"got: {date_range!r}"
            )
        return f"segments.date BETWEEN '{start}' AND '{end}'"

    raise TypeError(f"date_range must be a str or dict, got {type(date_range).__name__!r}")


def micros_to_currency(micros: int) -> float:
    return micros / 1_000_000
