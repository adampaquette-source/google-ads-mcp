"""Smart Bidding seasonality adjustments: propose and commit.

A seasonality adjustment tells Smart Bidding to expect a short-term change in
conversion rate over a defined window (a sale, a holiday, a known slow weekend),
so it adjusts bids in advance instead of learning after the fact.

Scope matters:
  CAMPAIGN  -- applies only to the campaign IDs you list.
  CHANNEL   -- applies to every campaign of the given channel types.

Only campaigns using Smart Bidding (Target ROAS, Target CPA, Maximize
Conversions, Maximize Conversion Value) are affected. Manual CPC and Maximize
Clicks campaigns ignore seasonality adjustments entirely.

Google's guidance: use these sparingly, for known short events (1 to 7 days,
14 max). Smart Bidding already handles routine, recurring seasonality on its own.

Creation follows the propose/commit pattern: propose_seasonality_adjustment()
validates and stores a JSON proposal; commit_seasonality_adjustment() reads it
and fires the single mutate call. Nothing is written to Google Ads until commit.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from google.ads.googleads.client import GoogleAdsClient
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_SCOPES = {"CAMPAIGN", "CHANNEL"}
# AdvertisingChannelType values that carry Smart Bidding traffic for our stores.
_VALID_CHANNELS = {"SEARCH", "SHOPPING", "DISPLAY", "PERFORMANCE_MAX", "VIDEO", "DEMAND_GEN"}
_VALID_DEVICES = {"MOBILE", "TABLET", "DESKTOP", "CONNECTED_TV", "OTHER"}
_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
# API accepts a conversion_rate_modifier between 0.1 (-90%) and 10.0 (+900%).
_MIN_MODIFIER = 0.1
_MAX_MODIFIER = 10.0
_MAX_WINDOW_DAYS = 14


def _short_error(exc: Exception) -> str:
    """Return a concise, single-line error string from any exception."""
    try:
        from google.ads.googleads.errors import GoogleAdsException
        if isinstance(exc, GoogleAdsException):
            parts = []
            for e in exc.failure.errors:
                code = e.error_code.WhichOneof("error_code") or "unknown"
                parts.append(f"{code}: {e.message}")
            return "; ".join(parts) if parts else str(exc)[:200]
    except Exception:
        pass
    return str(exc).replace("\n", " ")[:200]


# ---------------------------------------------------------------------------
# Proposal storage directory (project root / creation_proposals/)
# ---------------------------------------------------------------------------

def _proposals_dir() -> Path:
    here = Path(__file__).resolve()
    root = here
    for _ in range(6):
        root = root.parent
        if (root / "pyproject.toml").exists():
            break
    d = root / "creation_proposals"
    d.mkdir(exist_ok=True)
    return d


def _proposal_path(proposal_id: str) -> Path:
    return _proposals_dir() / f"seasonality_{proposal_id}.json"


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class SeasonalityAdjustmentConfig(TypedDict, total=False):
    name: str                              # descriptive label, required
    scope: str                             # "CAMPAIGN" | "CHANNEL", required
    conversion_rate_pct_change: float      # e.g. -20.0 for a 20% drop, required
    start_date_time: str                   # "yyyy-MM-dd HH:mm:ss", required
    end_date_time: str                     # "yyyy-MM-dd HH:mm:ss", required
    description: str                       # optional free text
    campaign_ids: list[str]                # required when scope == "CAMPAIGN"
    advertising_channel_types: list[str]   # required when scope == "CHANNEL"
    devices: list[str]                     # optional; default = all devices


class SeasonalityProposal(TypedDict):
    proposal_id: str
    customer_id: str
    config: SeasonalityAdjustmentConfig
    conversion_rate_modifier: float        # resolved from conversion_rate_pct_change
    created_at: str
    status: str                            # "pending" | "committed" | "cancelled"


class SeasonalityCommitResult(TypedDict):
    proposal_id: str
    customer_id: str
    resource_name: str
    conversion_rate_modifier: float
    scope: str
    status: str                            # "created"


class SeasonalityRemoveResult(TypedDict):
    customer_id: str
    resource_name: str
    status: str                            # "removed" | "error"
    error: str                             # empty string on success


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _modifier_from_pct(pct_change: float) -> float:
    """Convert a percent change (e.g. -20.0) to an API modifier (0.8). Rounded to 4dp."""
    return round(1.0 + (pct_change / 100.0), 4)


def _validate_config(config: SeasonalityAdjustmentConfig) -> list[str]:
    errors: list[str] = []

    name = config.get("name", "")
    if not name or not str(name).strip():
        errors.append("name is required")

    scope = config.get("scope", "")
    if scope not in _VALID_SCOPES:
        errors.append(f"scope must be one of {sorted(_VALID_SCOPES)}, got {scope!r}")

    if "conversion_rate_pct_change" not in config:
        errors.append("conversion_rate_pct_change is required (e.g. -20.0 for a 20% drop)")
    else:
        modifier = _modifier_from_pct(float(config["conversion_rate_pct_change"]))
        if not (_MIN_MODIFIER <= modifier <= _MAX_MODIFIER):
            errors.append(
                f"conversion_rate_pct_change {config['conversion_rate_pct_change']} "
                f"resolves to modifier {modifier}, outside the allowed range "
                f"[{_MIN_MODIFIER}, {_MAX_MODIFIER}] (i.e. -90% to +900%)"
            )

    start_raw = config.get("start_date_time", "")
    end_raw = config.get("end_date_time", "")
    start_dt = end_dt = None
    for label, raw in (("start_date_time", start_raw), ("end_date_time", end_raw)):
        if not raw:
            errors.append(f"{label} is required (format 'yyyy-MM-dd HH:mm:ss')")
            continue
        try:
            parsed = datetime.strptime(raw, _DATETIME_FMT)
            if label == "start_date_time":
                start_dt = parsed
            else:
                end_dt = parsed
        except ValueError:
            errors.append(f"{label} {raw!r} is not in format 'yyyy-MM-dd HH:mm:ss'")

    if start_dt and end_dt:
        if end_dt <= start_dt:
            errors.append("end_date_time must be after start_date_time")
        elif (end_dt - start_dt).total_seconds() > _MAX_WINDOW_DAYS * 86400:
            errors.append(
                f"window exceeds the {_MAX_WINDOW_DAYS}-day maximum for a "
                "seasonality adjustment"
            )

    if scope == "CAMPAIGN":
        ids = config.get("campaign_ids") or []
        if not ids:
            errors.append("campaign_ids is required and non-empty when scope == 'CAMPAIGN'")
    elif scope == "CHANNEL":
        channels = config.get("advertising_channel_types") or []
        if not channels:
            errors.append(
                "advertising_channel_types is required and non-empty when scope == 'CHANNEL'"
            )
        for ch in channels:
            if ch not in _VALID_CHANNELS:
                errors.append(
                    f"advertising_channel_type {ch!r} invalid; "
                    f"must be one of {sorted(_VALID_CHANNELS)}"
                )

    for dev in config.get("devices") or []:
        if dev not in _VALID_DEVICES:
            errors.append(f"device {dev!r} invalid; must be one of {sorted(_VALID_DEVICES)}")

    return errors


# ---------------------------------------------------------------------------
# Propose / get / commit
# ---------------------------------------------------------------------------

def propose_seasonality_adjustment(
    customer_id: str,
    config: SeasonalityAdjustmentConfig,
) -> SeasonalityProposal:
    """Validate a seasonality adjustment config and store it as a pending proposal.

    Does NOT touch Google Ads. Returns the proposal (with proposal_id and the
    resolved conversion_rate_modifier) for review before commit.

    Raises ValueError with a formatted error list if validation fails.
    """
    errors = _validate_config(config)
    if errors:
        raise ValueError(
            "Seasonality adjustment config failed validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    modifier = _modifier_from_pct(float(config["conversion_rate_pct_change"]))
    proposal_id = str(uuid.uuid4())[:8]
    proposal: SeasonalityProposal = {
        "proposal_id": proposal_id,
        "customer_id": customer_id,
        "config": config,
        "conversion_rate_modifier": modifier,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    _proposal_path(proposal_id).write_text(
        json.dumps(proposal, indent=2), encoding="utf-8"
    )
    return proposal


def get_seasonality_proposal(proposal_id: str) -> SeasonalityProposal:
    """Read and return a pending seasonality proposal by ID.

    Raises FileNotFoundError if no proposal with that ID exists.
    """
    path = _proposal_path(proposal_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No seasonality proposal found with ID {proposal_id!r}. "
            "Run propose_seasonality_adjustment() first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def commit_seasonality_adjustment(
    client: GoogleAdsClient,
    proposal_id: str,
) -> SeasonalityCommitResult:
    """Execute a pending seasonality adjustment via the Google Ads API.

    Reads the stored proposal and fires a single
    mutate_bidding_seasonality_adjustments call. Writes an audit record on
    success and marks the proposal committed.

    Raises FileNotFoundError if the proposal does not exist.
    Raises ValueError if the proposal is not pending.
    Raises GoogleAdsException if the API call fails.
    """
    proposal = get_seasonality_proposal(proposal_id)
    if proposal["status"] != "pending":
        raise ValueError(
            f"Proposal {proposal_id!r} has status {proposal['status']!r}. "
            "Only pending proposals can be committed."
        )

    customer_id = proposal["customer_id"]
    config = proposal["config"]
    modifier = proposal["conversion_rate_modifier"]

    service = client.get_service("BiddingSeasonalityAdjustmentService")
    campaign_service = client.get_service("CampaignService")
    operation = client.get_type("BiddingSeasonalityAdjustmentOperation")
    adj = operation.create

    adj.name = config["name"]
    # Client runs use_proto_plus=False (raw protobuf): enums are not
    # subscriptable, so resolve names via getattr.
    adj.scope = getattr(client.enums.SeasonalityEventScopeEnum, config["scope"])
    adj.start_date_time = config["start_date_time"]
    adj.end_date_time = config["end_date_time"]
    adj.conversion_rate_modifier = modifier
    if config.get("description"):
        adj.description = config["description"]

    if config["scope"] == "CAMPAIGN":
        for cid in config["campaign_ids"]:
            adj.campaigns.append(campaign_service.campaign_path(customer_id, cid))
    else:  # CHANNEL
        for ch in config["advertising_channel_types"]:
            adj.advertising_channel_types.append(
                getattr(client.enums.AdvertisingChannelTypeEnum, ch)
            )

    for dev in config.get("devices") or []:
        adj.devices.append(getattr(client.enums.DeviceEnum, dev))

    # Audit BEFORE the write so a partial/failed call is still visible.
    _write_audit(proposal_id, customer_id, config, modifier, resource_name="", status="attempted")

    try:
        response = service.mutate_bidding_seasonality_adjustments(
            customer_id=customer_id,
            operations=[operation],
        )
    except Exception as exc:
        _write_audit(
            proposal_id, customer_id, config, modifier,
            resource_name="", status=f"error: {_short_error(exc)}",
        )
        raise

    resource_name = response.results[0].resource_name

    _write_audit(proposal_id, customer_id, config, modifier, resource_name, status="created")

    proposal["status"] = "committed"
    _proposal_path(proposal_id).write_text(
        json.dumps(proposal, indent=2), encoding="utf-8"
    )

    return SeasonalityCommitResult(
        proposal_id=proposal_id,
        customer_id=customer_id,
        resource_name=resource_name,
        conversion_rate_modifier=modifier,
        scope=config["scope"],
        status="created",
    )


# ---------------------------------------------------------------------------
# Remove (rollback)
# ---------------------------------------------------------------------------

def remove_seasonality_adjustment(
    client: GoogleAdsClient,
    customer_id: str,
    adjustment: str,
) -> SeasonalityRemoveResult:
    """Remove a live seasonality adjustment. Immediate, no propose step.

    This is a reversal/cleanup operation: use it to pull a scheduled or active
    adjustment before it applies (or to undo a mistake). Logs to audit.db with
    status 'removed'.

    adjustment: either the full resource name
    ("customers/{cid}/biddingSeasonalityAdjustments/{id}") or just the numeric
    seasonality_adjustment_id.

    Returns a SeasonalityRemoveResult; status is "removed" on success or "error"
    with the message on failure (the call does not raise).
    """
    service = client.get_service("BiddingSeasonalityAdjustmentService")
    resource_name = (
        adjustment
        if "/" in str(adjustment)
        else service.bidding_seasonality_adjustment_path(customer_id, str(adjustment))
    )

    try:
        operation = client.get_type("BiddingSeasonalityAdjustmentOperation")
        operation.remove = resource_name
        service.mutate_bidding_seasonality_adjustments(
            customer_id=customer_id,
            operations=[operation],
        )
        _write_audit(
            proposal_id="", customer_id=customer_id, config={"name": "", "scope": ""},
            modifier=0.0, resource_name=resource_name, status="removed",
        )
        return SeasonalityRemoveResult(
            customer_id=customer_id,
            resource_name=resource_name,
            status="removed",
            error="",
        )
    except Exception as exc:
        err = _short_error(exc)
        _write_audit(
            proposal_id="", customer_id=customer_id, config={"name": "", "scope": ""},
            modifier=0.0, resource_name=resource_name, status=f"remove_error: {err}",
        )
        return SeasonalityRemoveResult(
            customer_id=customer_id,
            resource_name=resource_name,
            status="error",
            error=err,
        )


# ---------------------------------------------------------------------------
# Internal: audit log
# ---------------------------------------------------------------------------

def _write_audit(
    proposal_id: str,
    customer_id: str,
    config: SeasonalityAdjustmentConfig,
    modifier: float,
    resource_name: str,
    status: str,
) -> None:
    """Append a seasonality adjustment record to the SQLite audit log."""
    import sqlite3

    db_path = os.getenv("ADS_MCP_AUDIT_LOG_PATH", "./audit.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seasonality_adjustment_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                proposal_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                name TEXT NOT NULL,
                scope TEXT NOT NULL,
                conversion_rate_modifier REAL NOT NULL,
                start_date_time TEXT NOT NULL,
                end_date_time TEXT NOT NULL,
                targets TEXT NOT NULL,
                resource_name TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        targets = (
            config.get("campaign_ids")
            if config.get("scope") == "CAMPAIGN"
            else config.get("advertising_channel_types")
        )
        conn.execute(
            """
            INSERT INTO seasonality_adjustment_log
              (created_at, proposal_id, customer_id, name, scope,
               conversion_rate_modifier, start_date_time, end_date_time,
               targets, resource_name, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                proposal_id,
                customer_id,
                config.get("name", ""),
                config.get("scope", ""),
                modifier,
                config.get("start_date_time", ""),
                config.get("end_date_time", ""),
                json.dumps(targets or []),
                resource_name,
                status,
            ),
        )
        conn.commit()
    finally:
        conn.close()
