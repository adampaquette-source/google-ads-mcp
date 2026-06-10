"""Product velocity tiering: classify products as New Winners, Turning Losers, or Consistent Losers."""

from __future__ import annotations

import statistics
from datetime import date, timedelta

from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.performance import get_product_performance, ProductRow
from ads_mcp.reporting.queries import TROAS_AUDIT
from ads_mcp.reporting.utils import date_range_clause, micros_to_currency

# ---------------------------------------------------------------------------
# Thresholds -- adjust here to tune classification sensitivity
# ---------------------------------------------------------------------------

_MIN_SPEND_MEANINGFUL = 25.0        # minimum current-period spend to be classified
_MAX_PRIOR_SPEND_NEW_WINNER = 10.0  # max prior spend to qualify as a new product
_MIN_PRIOR_SPEND_ESTABLISHED = 15.0 # prior spend needed to establish a history
_MIN_CURRENT_SPEND_TURNING = 10.0   # min current spend for Turning Loser (still receiving traffic)
_LOSER_ROAS_MAX = 1.0               # ROAS below this = spending more than it earns
_TURNING_LOSER_DECAY = 0.70         # current/prior ROAS ratio below this = 30%+ decay
_FALLBACK_TARGET_ROAS = 2.0         # used when no campaign tROAS target is found
_MIN_PRICE_COVERAGE = 0.50          # current spend must be >= this fraction of estimated item price


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class ProductVelocityRow(TypedDict):
    product_id: str
    title: str
    product_type: str
    tier: str                      # NEW_WINNER | TURNING_LOSER | CONSISTENT_LOSER | ON_TRACK
    action: str
    current_cost: float
    current_roas: float
    current_conversions: float
    current_conversions_value: float
    prior_cost: float
    prior_roas: float
    roas_delta: float              # current_roas - prior_roas (positive = improving)
    cost_delta: float              # current_cost - prior_cost (positive = spending more)
    estimated_price: float | None  # avg order value from conversion data; None if no conversions in either window


class VelocitySummary(TypedDict):
    new_winners: int
    turning_losers: int
    consistent_losers: int
    on_track: int


class ProductVelocityResult(TypedDict):
    customer_id: str
    current_date_range: str
    prior_date_range: str
    account_target_roas: float
    summary: VelocitySummary
    new_winners: list[ProductVelocityRow]
    turning_losers: list[ProductVelocityRow]
    consistent_losers: list[ProductVelocityRow]
    on_track: list[ProductVelocityRow]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_prior_window(date_range: str | dict) -> dict:
    """Return a {start_date, end_date} dict for the period immediately before date_range."""
    today = date.today()

    if isinstance(date_range, dict):
        start = date.fromisoformat(date_range["start_date"])
        end = date.fromisoformat(date_range["end_date"])
        duration_days = (end - start).days  # inclusive duration - 1
        prior_end = start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=duration_days)
        return {"start_date": prior_start.isoformat(), "end_date": prior_end.isoformat()}

    preset_days = {
        "LAST_7_DAYS": 7,
        "LAST_14_DAYS": 14,
        "LAST_30_DAYS": 30,
    }
    n = preset_days.get(date_range.upper(), 30)
    # LAST_N_DAYS covers today-N through today-1 (n days inclusive).
    # Prior window: same length, ending the day before current window starts.
    prior_end = today - timedelta(days=n + 1)
    prior_start = today - timedelta(days=2 * n)
    return {"start_date": prior_start.isoformat(), "end_date": prior_end.isoformat()}


def _aggregate_product_rows(rows: list[ProductRow]) -> dict[str, dict]:
    """Sum metrics per product_id across all campaigns."""
    agg: dict[str, dict] = {}
    for row in rows:
        pid = row["product_id"]
        if not pid:
            continue
        if pid not in agg:
            agg[pid] = {
                "product_id": pid,
                "title": row["title"],
                "product_type": row["product_type"],
                "cost": 0.0,
                "conversions": 0.0,
                "conversions_value": 0.0,
            }
        agg[pid]["cost"] = round(agg[pid]["cost"] + row["cost"], 2)
        agg[pid]["conversions"] = round(agg[pid]["conversions"] + row["conversions"], 2)
        agg[pid]["conversions_value"] = round(agg[pid]["conversions_value"] + row["conversions_value"], 2)
    return agg


def _get_account_target_roas(client: GoogleAdsClient, customer_id: str) -> float:
    """Return the median tROAS across ENABLED TARGET_ROAS/PMax campaigns, or fallback."""
    dc = date_range_clause("LAST_7_DAYS")
    query = TROAS_AUDIT.format(date_clause=dc)

    ga_service = client.get_service("GoogleAdsService")
    request = client.get_type("SearchGoogleAdsStreamRequest")
    request.customer_id = customer_id
    request.query = query

    troas_values: list[float] = []
    for batch in ga_service.search_stream(request=request):
        for row in batch.results:
            camp = row.campaign
            pmax = camp.maximize_conversion_value.target_roas
            standard = camp.target_roas.target_roas
            val = pmax if pmax > 0 else standard
            if val > 0:
                troas_values.append(val)

    if not troas_values:
        return _FALLBACK_TARGET_ROAS
    return round(statistics.median(troas_values), 4)


def _roas(conversions_value: float, cost: float) -> float:
    return round(conversions_value / cost, 4) if cost > 0 else 0.0


# ---------------------------------------------------------------------------
# Main classification function
# ---------------------------------------------------------------------------

def classify_product_velocity(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
) -> ProductVelocityResult:
    """Classify products into performance tiers by comparing current vs prior period.

    Fetches shopping_performance_view for two equal-length windows and classifies
    each product_id (aggregated across campaigns) into one of four tiers.
    Products with insufficient spend in both windows are excluded.
    """
    prior_window = _compute_prior_window(date_range)
    prior_label = f"{prior_window['start_date']} to {prior_window['end_date']}"

    current_rows = get_product_performance(client, customer_id, date_range)
    prior_rows = get_product_performance(client, customer_id, prior_window)
    account_target_roas = _get_account_target_roas(client, customer_id)

    current_agg = _aggregate_product_rows(current_rows)
    prior_agg = _aggregate_product_rows(prior_rows)

    all_ids = set(current_agg) | set(prior_agg)

    new_winners: list[ProductVelocityRow] = []
    turning_losers: list[ProductVelocityRow] = []
    consistent_losers: list[ProductVelocityRow] = []
    on_track: list[ProductVelocityRow] = []

    _empty: dict = {"cost": 0.0, "conversions": 0.0, "conversions_value": 0.0}

    for pid in all_ids:
        curr = current_agg.get(pid, _empty)
        prior = prior_agg.get(pid, _empty)

        curr_cost = curr["cost"]
        curr_roas = _roas(curr["conversions_value"], curr_cost)
        prior_cost = prior["cost"]
        prior_roas = _roas(prior["conversions_value"], prior_cost)

        meta = current_agg.get(pid) or prior_agg.get(pid)
        title = meta["title"]          # type: ignore[index]
        product_type = meta["product_type"]  # type: ignore[index]

        roas_delta = round(curr_roas - prior_roas, 4)
        cost_delta = round(curr_cost - prior_cost, 2)

        # Estimate item price from avg order value -- use whichever window has conversions.
        # Products with zero conversions in both windows have no price estimate;
        # these are excluded from Consistent Losers (high-ticket items waiting for a sale).
        estimated_price: float | None = None
        prior_conversions = prior["conversions"]
        curr_conversions = curr["conversions"]
        if prior_conversions > 0:
            estimated_price = round(prior["conversions_value"] / prior_conversions, 2)
        elif curr_conversions > 0:
            estimated_price = round(curr["conversions_value"] / curr_conversions, 2)

        # Tier classification -- first match wins.
        tier: str
        action: str

        if (
            curr_cost >= _MIN_SPEND_MEANINGFUL
            and curr_roas >= account_target_roas
            and prior_cost < _MAX_PRIOR_SPEND_NEW_WINNER
        ):
            tier = "NEW_WINNER"
            action = "Consider dedicated campaign or higher listing group priority to scale."

        elif (
            prior_cost >= _MIN_PRIOR_SPEND_ESTABLISHED
            and prior_roas >= account_target_roas
            and curr_cost >= _MIN_CURRENT_SPEND_TURNING
            and prior_roas > 0
            and curr_roas < prior_roas * _TURNING_LOSER_DECAY
        ):
            tier = "TURNING_LOSER"
            action = "Investigate pricing, inventory, or competition. Exclude if decline continues."

        elif (
            curr_cost >= _MIN_SPEND_MEANINGFUL
            and curr_roas < _LOSER_ROAS_MAX
            and prior_cost >= _MIN_PRIOR_SPEND_ESTABLISHED
            and estimated_price is not None
            and curr_cost >= estimated_price * _MIN_PRICE_COVERAGE
        ):
            tier = "CONSISTENT_LOSER"
            action = "Candidate for feed exclusion or listing group demotion."

        elif curr_cost >= _MIN_SPEND_MEANINGFUL:
            tier = "ON_TRACK"
            action = "No action required."

        else:
            continue  # insufficient spend in both windows to classify

        row = ProductVelocityRow(
            product_id=pid,
            title=title,
            product_type=product_type,
            tier=tier,
            action=action,
            current_cost=round(curr_cost, 2),
            current_roas=curr_roas,
            current_conversions=round(curr_conversions, 2),
            current_conversions_value=round(curr["conversions_value"], 2),
            prior_cost=round(prior_cost, 2),
            prior_roas=prior_roas,
            roas_delta=roas_delta,
            cost_delta=cost_delta,
            estimated_price=estimated_price,
        )

        if tier == "NEW_WINNER":
            new_winners.append(row)
        elif tier == "TURNING_LOSER":
            turning_losers.append(row)
        elif tier == "CONSISTENT_LOSER":
            consistent_losers.append(row)
        else:
            on_track.append(row)

    # Sort each tier by highest-impact first.
    new_winners.sort(key=lambda r: r["current_conversions_value"], reverse=True)
    turning_losers.sort(key=lambda r: r["prior_cost"], reverse=True)
    consistent_losers.sort(key=lambda r: r["current_cost"], reverse=True)
    on_track.sort(key=lambda r: r["current_cost"], reverse=True)

    current_label = (
        date_range if isinstance(date_range, str)
        else f"{date_range['start_date']} to {date_range['end_date']}"
    )

    return ProductVelocityResult(
        customer_id=customer_id,
        current_date_range=current_label,
        prior_date_range=prior_label,
        account_target_roas=account_target_roas,
        summary=VelocitySummary(
            new_winners=len(new_winners),
            turning_losers=len(turning_losers),
            consistent_losers=len(consistent_losers),
            on_track=len(on_track),
        ),
        new_winners=new_winners,
        turning_losers=turning_losers,
        consistent_losers=consistent_losers,
        on_track=on_track,
    )
