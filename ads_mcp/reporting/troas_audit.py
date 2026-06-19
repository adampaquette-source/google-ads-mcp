"""tROAS audit module.

Generates tROAS adjustment proposals for the M/W/F review cycle.

Rules:
  TIGHTEN: actual ROAS is more than _DRIFT_TRIGGER_PCT below target
  LOOSEN:  actual ROAS is more than _DRIFT_TRIGGER_PCT above target
           AND spend grew >= _SPEND_SCALING_MIN_PCT week-over-week

Step size mapping (drift magnitude to pp adjustment):
  7-13%  -> 25pp
  13-22% -> 50pp
  22-30% -> 75pp
  30%+   -> 100pp

Eligibility:
  - campaign.status = ENABLED
  - campaign.bidding_strategy_type = TARGET_ROAS
  - L7 spend >= _MIN_SPEND_WEEK
  - (customer_id, campaign_id) not in recently_adjusted set (3-day cooldown)

Rollback monitoring:
  - Campaigns adjusted in the last 72h with L7 spend >= _ROLLBACK_MIN_SPEND_L7
  - Flag if conversions drop >= _ROLLBACK_DROP_PCT vs prior 72h window
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.accounts import list_accounts
from ads_mcp.reporting.queries import TROAS_AUDIT, TROAS_AUDIT_ADGROUP, TROAS_CONVERSION_WINDOW
from ads_mcp.reporting.utils import date_range_clause, micros_to_currency


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

_MIN_SPEND_WEEK: float = 100.0        # $100/week minimum to propose any change
_DRIFT_TRIGGER_PCT: float = 7.0       # minimum relative drift % to trigger a proposal
_SPEND_SCALING_MIN_PCT: float = 15.0  # WoW spend increase required for LOOSEN
_ROLLBACK_MIN_SPEND_L7: float = 1000.0  # L7 spend threshold for rollback monitoring
_ROLLBACK_DROP_PCT: float = 50.0       # conversion drop % that triggers a rollback flag


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class TroasProposal(TypedDict):
    """One tROAS adjustment proposal for a single campaign or ad group.

    ad_group_id / ad_group_name are empty strings for campaign-level proposals.
    When non-empty the change targets the ad group rather than the parent campaign.
    """
    account_name: str
    customer_id: str
    campaign_id: str
    campaign_name: str
    ad_group_id: str         # empty for campaign-level proposals
    ad_group_name: str       # empty for campaign-level proposals
    bidding_type: str        # TARGET_ROAS | MAXIMIZE_CONVERSION_VALUE
    direction: str          # TIGHTEN | LOOSEN
    current_target_roas: float   # display percentage, e.g. 1000.0
    proposed_target_roas: float  # display percentage, e.g. 1025.0
    change_pp: int           # absolute pp step (always positive; direction gives sign)
    l7_actual_roas: float    # display percentage
    l7_target_roas: float    # same as current_target_roas, for display clarity
    drift_pct: float         # relative drift: (actual - target) / target * 100
    l7_spend: float
    l7_conversions_value: float  # revenue (conversions_value), not conversion count
    prior_l7_spend: float
    spend_change_pct: float  # (l7 - prior) / prior * 100; 0 if no prior data
    decision: str            # "-" initially; "Approve" | "Skip" after review


class TroasAuditResult(TypedDict):
    """Return type from build_troas_proposals."""
    run_at: str
    accounts_checked: int
    total_proposals: int
    proposals: list[TroasProposal]


class RollbackFlag(TypedDict):
    """A campaign flagged for potential rollback after a tROAS change."""
    account_name: str
    customer_id: str
    campaign_id: str
    campaign_name: str
    direction: str           # TIGHTEN | LOOSEN (what was applied)
    old_target_roas: float
    new_target_roas: float
    applied_date: str
    current_72h_conversions: float
    prior_72h_conversions: float
    conversion_drop_pct: float


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


def _drift_to_step_pp(drift_pct_abs: float) -> int:
    """Map absolute relative drift percentage to a pp step size.

    Bands (drift magnitude -> step):
      7-13%  -> 25pp
      13-22% -> 50pp
      22-30% -> 75pp
      30%+   -> 100pp
    """
    if drift_pct_abs >= 30.0:
        return 100
    if drift_pct_abs >= 22.0:
        return 75
    if drift_pct_abs >= 13.0:
        return 50
    return 25


def _prior_7d_range() -> dict:
    """Return an explicit date range for days 8-14 (the week before LAST_7_DAYS)."""
    today = datetime.now(timezone.utc).date()
    end = today - timedelta(days=8)
    start = today - timedelta(days=14)
    return {"start_date": str(start), "end_date": str(end)}


# ---------------------------------------------------------------------------
# Main audit function
# ---------------------------------------------------------------------------

def build_troas_proposals(
    client: GoogleAdsClient,
    recently_adjusted: set[tuple[str, str]],
) -> TroasAuditResult:
    """Generate tROAS adjustment proposals across all ENABLED accounts.

    recently_adjusted: set of (customer_id, campaign_id) tuples adjusted in
    the last cooldown window (3 days). These campaigns are skipped entirely.

    Returns a TroasAuditResult with the proposal list sorted by urgency:
    TIGHTEN proposals first, then by absolute drift descending.
    """
    accounts = list_accounts(client)
    enabled = [a for a in accounts if a["status"] == "ENABLED"]

    prior_range = _prior_7d_range()
    proposals: list[TroasProposal] = []

    for account in enabled:
        cid = account["id"]

        # -- Ad group level query (run first to know which campaigns delegate to ad groups) --
        # For any TARGET_ROAS campaign that has ad groups with their own tROAS set,
        # we propose changes at the ad group level instead of the campaign level.
        # PMax campaigns (MAXIMIZE_CONVERSION_VALUE) never appear here -- they have
        # no traditional ad_groups -- so they always fall through to campaign level.
        adgroup_rows: dict[str, dict] = {}  # key: "{campaign_id}:{ad_group_id}"
        campaigns_delegated_to_adgroup: set[str] = set()  # campaign_ids to skip at campaign level

        try:
            dc = date_range_clause("LAST_7_DAYS")
            query = TROAS_AUDIT_ADGROUP.format(date_clause=dc)
            for row in _stream(client, cid, query):
                camp = row.campaign
                ag = row.ad_group
                m = row.metrics
                # ad_group.target_roas (plain double in v24) is not
                # GAQL-filterable; skip ad groups without their own tROAS here.
                if not ag.target_roas:
                    continue
                cost = micros_to_currency(m.cost_micros)
                camp_id_str = str(camp.id)
                key = f"{camp_id_str}:{ag.id}"
                adgroup_rows[key] = {
                    "campaign_id": camp_id_str,
                    "campaign_name": camp.name,
                    "ad_group_id": str(ag.id),
                    "ad_group_name": ag.name,
                    "target_roas_dec": ag.target_roas,
                    "cost": cost,
                    "conversions_value": m.conversions_value,
                }
                campaigns_delegated_to_adgroup.add(camp_id_str)
        except Exception:
            pass

        adgroup_prior_cost: dict[str, float] = {}
        if adgroup_rows:
            try:
                dc = date_range_clause(prior_range)
                query = TROAS_AUDIT_ADGROUP.format(date_clause=dc)
                for row in _stream(client, cid, query):
                    key = f"{row.campaign.id}:{row.ad_group.id}"
                    adgroup_prior_cost[key] = micros_to_currency(row.metrics.cost_micros)
            except Exception:
                pass

        # -- Current period (L7) campaign level --
        current_rows: dict[str, dict] = {}
        try:
            dc = date_range_clause("LAST_7_DAYS")
            query = TROAS_AUDIT.format(date_clause=dc)
            for row in _stream(client, cid, query):
                camp = row.campaign
                m = row.metrics
                cost = micros_to_currency(m.cost_micros)
                # For PMax: tROAS lives in maximize_conversion_value.target_roas
                # For others (TARGET_ROAS): tROAS lives in target_roas.target_roas
                pmax_troas = camp.maximize_conversion_value.target_roas
                standard_troas = camp.target_roas.target_roas
                target_roas_dec = pmax_troas if pmax_troas > 0 else standard_troas
                bidding_type = (
                    "MAXIMIZE_CONVERSION_VALUE" if pmax_troas > 0 else "TARGET_ROAS"
                )
                current_rows[str(camp.id)] = {
                    "name": camp.name,
                    "target_roas_dec": target_roas_dec,
                    "bidding_type": bidding_type,
                    "cost": cost,
                    "conversions_value": m.conversions_value,
                    "conversions": m.conversions,
                }
        except Exception:
            continue

        # -- Prior period (L8-14) for spend scaling check --
        prior_cost_by_id: dict[str, float] = {}
        try:
            dc = date_range_clause(prior_range)
            query = TROAS_AUDIT.format(date_clause=dc)
            for row in _stream(client, cid, query):
                prior_cost_by_id[str(row.campaign.id)] = micros_to_currency(
                    row.metrics.cost_micros
                )
        except Exception:
            pass  # no prior data -- spend_change_pct will be 0

        def _make_proposal(
            account_name: str,
            customer_id: str,
            campaign_id: str,
            campaign_name: str,
            ad_group_id: str,
            ad_group_name: str,
            bidding_type: str,
            target_dec: float,
            cost: float,
            conversions_value: float,
            prior_cost: float,
        ) -> "TroasProposal | None":
            actual_dec = conversions_value / cost if cost > 0 else 0.0
            drift_pct = (actual_dec - target_dec) / target_dec * 100 if target_dec else 0.0

            if abs(drift_pct) < _DRIFT_TRIGGER_PCT:
                return None

            spend_change_pct = (
                (cost - prior_cost) / prior_cost * 100 if prior_cost > 0 else 0.0
            )

            if drift_pct < 0:
                direction = "TIGHTEN"
            else:
                if spend_change_pct < _SPEND_SCALING_MIN_PCT:
                    return None
                direction = "LOOSEN"

            step_pp = _drift_to_step_pp(abs(drift_pct))
            current_pct = target_dec * 100.0
            proposed_pct = (
                current_pct + step_pp if direction == "TIGHTEN"
                else max(current_pct - step_pp, 1.0)
            )

            return TroasProposal(
                account_name=account_name,
                customer_id=customer_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                ad_group_id=ad_group_id,
                ad_group_name=ad_group_name,
                bidding_type=bidding_type,
                direction=direction,
                current_target_roas=round(current_pct, 2),
                proposed_target_roas=round(proposed_pct, 2),
                change_pp=step_pp,
                l7_actual_roas=round(actual_dec * 100.0, 2),
                l7_target_roas=round(current_pct, 2),
                drift_pct=round(drift_pct, 2),
                l7_spend=round(cost, 2),
                l7_conversions_value=round(conversions_value, 2),
                prior_l7_spend=round(prior_cost, 2),
                spend_change_pct=round(spend_change_pct, 2),
                decision="-",
            )

        # -- Evaluate campaign-level proposals --
        # Skip campaigns that have ad groups with their own tROAS (handled below).
        for campaign_id, cdata in current_rows.items():

            if (cid, campaign_id) in recently_adjusted:
                continue

            if campaign_id in campaigns_delegated_to_adgroup:
                continue  # ad groups will be evaluated instead

            target_dec = cdata["target_roas_dec"]
            if not target_dec:
                continue

            cost = cdata["cost"]
            if cost < _MIN_SPEND_WEEK:
                continue

            prior_cost = prior_cost_by_id.get(campaign_id, 0.0)
            proposal = _make_proposal(
                account_name=account["name"],
                customer_id=cid,
                campaign_id=campaign_id,
                campaign_name=cdata["name"],
                ad_group_id="",
                ad_group_name="",
                bidding_type=cdata["bidding_type"],
                target_dec=target_dec,
                cost=cost,
                conversions_value=cdata["conversions_value"],
                prior_cost=prior_cost,
            )
            if proposal:
                proposals.append(proposal)

        # -- Evaluate ad group level proposals --
        for key, agdata in adgroup_rows.items():
            ag_campaign_id = agdata["campaign_id"]

            if (cid, ag_campaign_id) in recently_adjusted:
                continue

            target_dec = agdata["target_roas_dec"]
            if not target_dec:
                continue

            cost = agdata["cost"]
            if cost < _MIN_SPEND_WEEK:
                continue

            prior_cost = adgroup_prior_cost.get(key, 0.0)
            proposal = _make_proposal(
                account_name=account["name"],
                customer_id=cid,
                campaign_id=ag_campaign_id,
                campaign_name=agdata["campaign_name"],
                ad_group_id=agdata["ad_group_id"],
                ad_group_name=agdata["ad_group_name"],
                bidding_type="TARGET_ROAS",
                target_dec=target_dec,
                cost=cost,
                conversions_value=agdata["conversions_value"],
                prior_cost=prior_cost,
            )
            if proposal:
                proposals.append(proposal)

    # Sort: TIGHTEN first (more urgent), then by absolute drift descending
    proposals.sort(key=lambda p: (0 if p["direction"] == "TIGHTEN" else 1, -abs(p["drift_pct"])))

    return TroasAuditResult(
        run_at=datetime.now(timezone.utc).isoformat(),
        accounts_checked=len(enabled),
        total_proposals=len(proposals),
        proposals=proposals,
    )


# ---------------------------------------------------------------------------
# Rollback monitor
# ---------------------------------------------------------------------------

def check_rollback_flags(
    client: GoogleAdsClient,
    recently_adjusted: list[dict],
) -> list[RollbackFlag]:
    """Check campaigns adjusted in the last 72h for conversion dropoffs.

    recently_adjusted: list of tROAS Log rows (dicts with keys: customer_id,
    campaign_id, campaign_name, account_name, direction, old_target_roas,
    new_target_roas, l7_spend).

    Returns a list of RollbackFlag for any campaign showing a conversion drop
    >= _ROLLBACK_DROP_PCT and L7 spend >= _ROLLBACK_MIN_SPEND_L7 at time of
    adjustment.
    """
    today = datetime.now(timezone.utc).date()

    # Current 72h window: yesterday-2 to yesterday (3 full days)
    current_end = today - timedelta(days=1)
    current_start = today - timedelta(days=3)
    current_range = {"start_date": str(current_start), "end_date": str(current_end)}

    # Prior 72h window: today-4 to today-6
    prior_end = today - timedelta(days=4)
    prior_start = today - timedelta(days=6)
    prior_range = {"start_date": str(prior_start), "end_date": str(prior_end)}

    # Group adjusted campaigns by customer_id
    by_customer: dict[str, list[dict]] = {}
    for row in recently_adjusted:
        cid = row["customer_id"]
        by_customer.setdefault(cid, []).append(row)

    flags: list[RollbackFlag] = []

    for cid, adjusted_list in by_customer.items():
        # Only monitor campaigns above the spend threshold
        to_monitor = {
            c["campaign_id"]: c for c in adjusted_list
            if float(c.get("l7_spend", 0)) >= _ROLLBACK_MIN_SPEND_L7
        }
        if not to_monitor:
            continue

        def query_conversions(date_range: dict) -> dict[str, float]:
            convs: dict[str, float] = {}
            try:
                dc = date_range_clause(date_range)
                query = TROAS_CONVERSION_WINDOW.format(date_clause=dc)
                for row in _stream(client, cid, query):
                    cid_str = str(row.campaign.id)
                    if cid_str in to_monitor:
                        convs[cid_str] = float(row.metrics.conversions)
            except Exception:
                pass
            return convs

        current_convs = query_conversions(current_range)
        prior_convs = query_conversions(prior_range)

        for campaign_id, log_row in to_monitor.items():
            current = current_convs.get(campaign_id, 0.0)
            prior = prior_convs.get(campaign_id, 0.0)

            if prior <= 0:
                continue  # no prior baseline, skip

            drop_pct = (prior - current) / prior * 100
            if drop_pct >= _ROLLBACK_DROP_PCT:
                flags.append(RollbackFlag(
                    account_name=log_row.get("account_name", ""),
                    customer_id=cid,
                    campaign_id=campaign_id,
                    campaign_name=log_row.get("campaign_name", ""),
                    direction=log_row.get("direction", ""),
                    old_target_roas=float(log_row.get("old_target_roas", 0)),
                    new_target_roas=float(log_row.get("new_target_roas", 0)),
                    applied_date=log_row.get("applied_date", ""),
                    current_72h_conversions=round(current, 1),
                    prior_72h_conversions=round(prior, 1),
                    conversion_drop_pct=round(drop_pct, 1),
                ))

    return flags
