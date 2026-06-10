"""Cross-account digest aggregation for Phase 2 reporting."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.accounts import list_accounts
from ads_mcp.reporting.performance import get_account_summary
from ads_mcp.reporting.health import (
    TroasPacingResult,
    BudgetPacingResult,
    check_troas_pacing,
    check_budget_pacing,
    find_disapprovals,
)


class AccountDigestRow(TypedDict):
    customer_id: str
    name: str
    cost: float
    conversions: float
    conversions_value: float
    roas: float
    clicks: int
    impressions: int
    troas_alerts: list[TroasPacingResult]
    budget_alerts: list[BudgetPacingResult]
    disapproval_count: int


class DigestData(TypedDict):
    date_range: str
    generated_at: str
    total_cost: float
    total_conversions: float
    total_conversions_value: float
    total_roas: float
    total_clicks: int
    total_impressions: int
    accounts: list[AccountDigestRow]
    accounts_with_troas_alerts: int
    accounts_with_budget_alerts: int
    total_disapprovals: int


def get_cross_account_digest(
    client: GoogleAdsClient,
    date_range: str = "LAST_7_DAYS",
) -> DigestData:
    """Aggregate performance and health data across all enabled sub-accounts.

    Calls 4 API endpoints per account (summary, tROAS pacing, budget pacing,
    disapprovals). Skips suspended/cancelled accounts. Returns totals plus
    per-account rows sorted by cost descending.
    """
    accounts = list_accounts(client)
    enabled = [a for a in accounts if a["status"] == "ENABLED" and not a["is_manager"]]

    rows: list[AccountDigestRow] = []
    total_cost = 0.0
    total_conversions = 0.0
    total_conversions_value = 0.0
    total_clicks = 0
    total_impressions = 0
    accounts_with_troas_alerts = 0
    accounts_with_budget_alerts = 0
    total_disapprovals = 0

    for account in enabled:
        cid = account["id"]

        try:
            summary = get_account_summary(client, cid, date_range)
        except Exception:
            continue

        try:
            troas_all = check_troas_pacing(client, cid)
            troas_alerts = [r for r in troas_all if r["status"] != "ON_TRACK"]
        except Exception:
            troas_alerts = []

        try:
            budget_all = check_budget_pacing(client, cid)
            budget_alerts = [r for r in budget_all if r["status"] != "ON_TRACK"]
        except Exception:
            budget_alerts = []

        try:
            disapprovals = find_disapprovals(client, cid)
            disapproval_count = disapprovals["total_count"]
        except Exception:
            disapproval_count = 0

        cost = summary["cost"]
        total_cost += cost
        total_conversions += summary["conversions"]
        total_conversions_value += summary["conversions_value"]
        total_clicks += summary["clicks"]
        total_impressions += summary["impressions"]

        if troas_alerts:
            accounts_with_troas_alerts += 1
        if budget_alerts:
            accounts_with_budget_alerts += 1
        total_disapprovals += disapproval_count

        roas = round(summary["conversions_value"] / cost, 4) if cost > 0 else 0.0

        rows.append(AccountDigestRow(
            customer_id=cid,
            name=account["name"],
            cost=cost,
            conversions=summary["conversions"],
            conversions_value=summary["conversions_value"],
            roas=roas,
            clicks=summary["clicks"],
            impressions=summary["impressions"],
            troas_alerts=troas_alerts,
            budget_alerts=budget_alerts,
            disapproval_count=disapproval_count,
        ))

    rows.sort(key=lambda r: r["cost"], reverse=True)

    total_roas = round(total_conversions_value / total_cost, 4) if total_cost > 0 else 0.0

    return DigestData(
        date_range=date_range,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_cost=round(total_cost, 2),
        total_conversions=round(total_conversions, 2),
        total_conversions_value=round(total_conversions_value, 2),
        total_roas=total_roas,
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        accounts=rows,
        accounts_with_troas_alerts=accounts_with_troas_alerts,
        accounts_with_budget_alerts=accounts_with_budget_alerts,
        total_disapprovals=total_disapprovals,
    )
