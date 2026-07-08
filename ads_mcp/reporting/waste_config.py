"""Per-account config loader for the wasted-keyword audit.

Reads waste_audit_config.json (keyed by customer_id) and merges the `_defaults`
block with any per-account overrides. Scalar keys fall back to the default;
list keys are REPLACED by the account block when present (so an account can
define its own competitor list without inheriting the generic retailer list).

The config drives ads_mcp/reporting/waste_audit.py. It holds no secrets and is
committed to the repo, mirroring stores_mapping.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from typing_extensions import TypedDict


class WasteAccountConfig(TypedDict):
    breakeven_roas_pct: float
    min_spend: float
    min_clicks: int
    target_cpa: float          # 0 = unset; when > 0 the zero-conv bar scales to it
    zero_conv_cpa_mult: float  # k in the "cost >= k x target_CPA, 0 conv" rule
    flag_foreign_language: bool
    flag_below_breakeven: bool
    block_non_branded: bool
    flag_ngram: bool           # aggregate diffuse sub-threshold waste by word
    ngram_min_spend: float     # 0 = derive from the zero-conv bar (2x)
    ngram_min_terms: int       # a gram must span at least this many distinct terms
    protect_terms: list[str]
    protect_regexes: list[str]
    competitor_terms: list[str]
    off_product_terms: list[str]


# Keys whose default is used only when the account block does not set them.
_SCALAR_KEYS = (
    "breakeven_roas_pct",
    "min_spend",
    "min_clicks",
    "target_cpa",
    "zero_conv_cpa_mult",
    "flag_foreign_language",
    "flag_below_breakeven",
    "block_non_branded",
    "flag_ngram",
    "ngram_min_spend",
    "ngram_min_terms",
)
_LIST_KEYS = (
    "protect_terms",
    "protect_regexes",
    "competitor_terms",
    "off_product_terms",
)


def _default_config_path() -> Path:
    """Resolve the config path.

    Order: ADS_WASTE_CONFIG_PATH env var, else waste_audit_config.json two
    directories up from this file (the project root). The env override lets the
    deployed control center point at its rsynced copy.
    """
    env = os.environ.get("ADS_WASTE_CONFIG_PATH", "").strip()
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parents[2] / "waste_audit_config.json"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and return the raw config dict (including `_defaults`).

    Returns an empty-defaults skeleton if the file is missing, so the audit can
    still run (with no protect/competitor lists) rather than crash.
    """
    p = Path(path).expanduser() if path else _default_config_path()
    if not p.exists():
        return {"_defaults": _empty_defaults()}
    with open(p, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "_defaults" not in data:
        data["_defaults"] = _empty_defaults()
    return data


def _empty_defaults() -> dict[str, Any]:
    return {
        "breakeven_roas_pct": 300.0,
        "min_spend": 5.0,
        "min_clicks": 3,
        "target_cpa": 0.0,
        "zero_conv_cpa_mult": 1.0,
        "flag_foreign_language": False,
        "flag_below_breakeven": True,
        "block_non_branded": False,
        "flag_ngram": True,
        "ngram_min_spend": 0.0,
        "ngram_min_terms": 3,
        "protect_terms": [],
        "protect_regexes": [],
        "competitor_terms": [],
        "off_product_terms": [],
    }


def config_for(customer_id: str, config: dict[str, Any] | None = None) -> WasteAccountConfig:
    """Return the merged config for one account.

    Scalars fall back to `_defaults`; lists are taken from the account block
    when present, otherwise from `_defaults`.
    """
    raw = config if config is not None else load_config()
    defaults = {**_empty_defaults(), **raw.get("_defaults", {})}
    account = raw.get(str(customer_id), {})

    merged: dict[str, Any] = {}
    for key in _SCALAR_KEYS:
        merged[key] = account.get(key, defaults.get(key))
    for key in _LIST_KEYS:
        # Account list replaces the default list when the account defines it.
        merged[key] = list(account.get(key, defaults.get(key, [])) or [])

    return WasteAccountConfig(**merged)  # type: ignore[typeddict-item]
