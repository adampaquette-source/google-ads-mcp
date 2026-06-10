"""Budget audit module.

Identifies two types of budget anomaly across ENABLED campaigns:

  constrained -- hit >= 80% of daily budget on >= 2 of the last 7 days.
                 Candidate for a budget increase.

  excess      -- L7 average daily spend < 40% of current budget and
                 total L7 spend >= $1 (not dormant).
                 Candidate for a budget decrease or reallocation.

Results are written to the Budget Proposals tab. Constrained rows are white,
excess rows are light teal. User enters a new dollar value in column F
(New Budget) for any row, then calls commit_budget_changes to apply via the API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.accounts import list_accounts
from ads_mcp.reporting.queries import BUDGET_PROPOSALS
from ads_mcp.reporting.utils import micros_to_currency


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

_THRESHOLD_PCT: float = 80.0        # daily_spend / daily_budget * 100 threshold
_MIN_DAYS_AT_THRESHOLD: int = 2     # minimum qualifying days in the L7 window
_EXCESS_THRESHOLD_PCT: float = 40.0 # avg_daily_spend / budget below this = excess
_MIN_L7_SPEND_FOR_EXCESS: float = 1.0  # ignore campaigns with negligible spend


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class BudgetProposal(TypedDict):
    """One budget proposal row for the Budget Proposals tab."""
    account_name: str
    customer_id: str
    campaign_id: str
    campaign_name: str
    channel_type: str
    budget_id: str
    current_budget: float      # daily budget in USD
    days_at_threshold: int     # days >= 80% of budget; 0 for excess rows
    avg_daily_spend: float     # threshold-days avg for constrained; L7 avg for excess
    max_daily_spend: float     # highest single-day spend in L7
    l7_spend: float            # total L7 spend
    l7_roas: float             # L7 conversions_value / L7 spend (0 if no spend)
    new_budget: float          # placeholder; user fills this in the sheet
    proposal_type: str         # "constrained" | "excess"


class BudgetAuditResult(TypedDict):
    """Return type from build_budget_proposals."""
    run_at: str
    accounts_checked: int
    total_proposals: int
    constrained_proposals: int
    excess_proposals: int
    proposals: list[BudgetProposal]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stream(client: GoogleAdsClient, customer_id: str, query: str):
    ga_service = client.get_service("GoogleAdsService")
    request = client.get_type("SearchGoogleAdsStreamRequest")
    request.customer_id = customer_id
    request.query = query
    for batch in ga_service.search_stream(request=request):
        yield from batch.results


def _channel_type_label(channel_type_value: int) -> str:
    """Convert advertising_channel_type enum integer to a readable label."""
    mapping = {
        0: "UNSPECIFIED",
        1: "UNKNOWN",
        2: "SEARCH",
        3: "DISPLAY",
        4: "SHOPPING",
        5: "HOTEL",
        6: "VIDEO",
        7: "MULTI_CHANNEL",
        8: "LOCAL",
        9: "SMART",
        10: "PERFORMANCE_MAX",
        11: "LOCAL_SERVICES",
        12: "DISCOVERY",
        13: "TRAVEL",
    }
    return mapping.get(int(channel_type_value), str(channel_type_value))


# ---------------------------------------------------------------------------
# Main audit function
# ---------------------------------------------------------------------------

def build_budget_proposals(client: GoogleAdsClient) -> BudgetAuditResult:
    """Generate budget proposals across all ENABLED accounts.

    Two-pass evaluation on the same L7 daily query per account:

    Pass 1 -- constrained:
      Counts days where daily_spend / daily_budget >= 80%.
      Includes campaign if count >= 2.
      avg_daily_spend is the average of those qualifying days only.

    Pass 2 -- excess:
      For campaigns NOT already flagged as constrained:
      Includes if avg_daily_spend (full L7 / 7) < 40% of current budget
      and total L7 spend >= $1 (filters out genuinely dormant campaigns).

    Returns constrained rows sorted by days_at_threshold descending,
    followed by excess rows sorted by utilization ascending.
    """
    accounts = list_accounts(client)
    enabled = [a for a in accounts if a["status"] == "ENABLED"]

    constrained: list[BudgetProposal] = []
    excess: list[BudgetProposal] = []

    for account in enabled:
        cid = account["id"]

        # Keyed by campaign_id; accumulates per-day rows.
        # Structure: {camp_id: {"name", "channel_type", "budget_id",
        #                       "current_budget", "days": [{"spend", "budget", "conv_value"}]}}
        campaign_data: dict[str, dict] = {}

        try:
            for row in _stream(client, cid, BUDGET_PROPOSALS):
                camp = row.campaign
                budget = row.campaign_budget
                m = row.metrics

                camp_id = str(camp.id)
                daily_budget = micros_to_currency(budget.amount_micros)
                daily_spend = micros_to_currency(m.cost_micros)

                if camp_id not in campaign_data:
                    campaign_data[camp_id] = {
                        "name": camp.name,
                        "channel_type": _channel_type_label(camp.advertising_channel_type),
                        "budget_id": str(budget.id),
                        "current_budget": daily_budget,
                        "days": [],
                    }
                else:
                    # Budget amount could vary across days (if user changed it); use latest
                    if daily_budget > 0:
                        campaign_data[camp_id]["current_budget"] = daily_budget

                if daily_budget > 0:
                    campaign_data[camp_id]["days"].append({
                        "spend": daily_spend,
                        "budget": daily_budget,
                        "conv_value": m.conversions_value,
                    })

        except Exception:
            continue

        constrained_ids: set[str] = set()

        # Pass 1: constrained campaigns
        for camp_id, cdata in campaign_data.items():
            days = cdata["days"]
            if not days:
                continue

            threshold_days = [
                d for d in days
                if d["budget"] > 0 and (d["spend"] / d["budget"] * 100) >= _THRESHOLD_PCT
            ]
            if len(threshold_days) < _MIN_DAYS_AT_THRESHOLD:
                continue

            constrained_ids.add(camp_id)
            avg_daily_spend = sum(d["spend"] for d in threshold_days) / len(threshold_days)
            max_daily_spend = max(d["spend"] for d in days)
            l7_spend = sum(d["spend"] for d in days)
            l7_conv_value = sum(d["conv_value"] for d in days)
            l7_roas = round(l7_conv_value / l7_spend, 4) if l7_spend > 0 else 0.0

            constrained.append(BudgetProposal(
                account_name=account["name"],
                customer_id=cid,
                campaign_id=camp_id,
                campaign_name=cdata["name"],
                channel_type=cdata["channel_type"],
                budget_id=cdata["budget_id"],
                current_budget=round(cdata["current_budget"], 2),
                days_at_threshold=len(threshold_days),
                avg_daily_spend=round(avg_daily_spend, 2),
                max_daily_spend=round(max_daily_spend, 2),
                l7_spend=round(l7_spend, 2),
                l7_roas=round(l7_roas, 4),
                new_budget=0.0,
                proposal_type="constrained",
            ))

        # Pass 2: excess budget campaigns (skip anything already flagged as constrained)
        for camp_id, cdata in campaign_data.items():
            if camp_id in constrained_ids:
                continue

            days = cdata["days"]
            if not days:
                continue

            l7_spend = sum(d["spend"] for d in days)
            if l7_spend < _MIN_L7_SPEND_FOR_EXCESS:
                continue

            current_budget = cdata["current_budget"]
            if current_budget <= 0:
                continue

            avg_daily_spend = l7_spend / 7.0
            utilization_pct = avg_daily_spend / current_budget * 100

            if utilization_pct >= _EXCESS_THRESHOLD_PCT:
                continue

            max_daily_spend = max(d["spend"] for d in days)
            l7_conv_value = sum(d["conv_value"] for d in days)
            l7_roas = round(l7_conv_value / l7_spend, 4) if l7_spend > 0 else 0.0

            excess.append(BudgetProposal(
                account_name=account["name"],
                customer_id=cid,
                campaign_id=camp_id,
                campaign_name=cdata["name"],
                channel_type=cdata["channel_type"],
                budget_id=cdata["budget_id"],
                current_budget=round(current_budget, 2),
                days_at_threshold=0,
                avg_daily_spend=round(avg_daily_spend, 2),
                max_daily_spend=round(max_daily_spend, 2),
                l7_spend=round(l7_spend, 2),
                l7_roas=round(l7_roas, 4),
                new_budget=0.0,
                proposal_type="excess",
            ))

    # Constrained: most constrained first; excess: lowest utilization first
    constrained.sort(key=lambda p: -p["days_at_threshold"])
    excess.sort(key=lambda p: p["avg_daily_spend"] / p["current_budget"] if p["current_budget"] > 0 else 0)

    proposals = constrained + excess

    return BudgetAuditResult(
        run_at=datetime.now(timezone.utc).isoformat(),
        accounts_checked=len(enabled),
        total_proposals=len(proposals),
        constrained_proposals=len(constrained),
        excess_proposals=len(excess),
        proposals=proposals,
    )
