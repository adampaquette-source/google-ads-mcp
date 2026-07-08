"""Wasted-keyword audit producer for the control center.

Runs the shared classification engine (ads_mcp/reporting/waste_audit.py) across
accounts, then persists the proposals to the negative_proposals table so the
Negatives tab can render them grouped by tranche. Propose-only: no Google Ads
writes happen here. Committing approved negatives is a separate, human-clicked
step (see app.py /negatives/commit and ads_mcp/proposals/negatives.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.waste_audit import TRANCHE_ORDER, build_waste_proposals

from control_center import store
from control_center.detectors import compute_tiers


def run_waste_audit(
    conn,
    client: GoogleAdsClient,
    date_range: str | dict = "LAST_30_DAYS",
    customer_ids: Optional[list[str]] = None,
) -> dict:
    """Run the waste audit and refresh the Negatives tab.

    Returns {"inserted": N, "accounts_checked": N, "protected_count": M,
             "tranche_counts": {...}, "audit_run_id": "..."}.
    """
    tiers = compute_tiers(conn)
    result = build_waste_proposals(
        client, date_range=date_range, customer_ids=customer_ids, tiers=tiers
    )
    proposals = result["proposals"]

    audit_run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    inserted = store.refresh_negative_proposals(conn, proposals, audit_run_id)

    return {
        "inserted": inserted,
        "accounts_checked": result["accounts_checked"],
        "protected_count": result["protected_count"],
        "tranche_counts": {t: result["tranche_counts"].get(t, 0) for t in TRANCHE_ORDER},
        "audit_run_id": audit_run_id,
    }
