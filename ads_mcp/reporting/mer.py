"""MER (Marketing Efficiency Ratio) data module.

MER = Shopify Net Sales / Google Ads Spend

This module handles the Google Ads side of the calculation. Claude orchestrates
the full report by:
  1. Calling get_mer_ads_data() to pull spend per store (via this module).
  2. Calling shopify_query_sales() per store (via the shopify-toolup MCP) to get net sales.
  3. Joining on shopify_key to compute per-store and portfolio-blended MER.
  4. Calling write_mer_report() (via the update_mer_report_tab MCP tool) to persist to Sheets.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.performance import get_account_summary


_MAPPING_PATH = Path(__file__).parent.parent.parent / "stores_mapping.json"


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class MerAdsRow(TypedDict):
    """Single store's Google Ads spend, ready to join with Shopify net sales.

    prior_cost is spend for the equivalent prior period (e.g. days 8-14 for a
    LAST_7_DAYS run). Zero if the prior period could not be fetched.
    """
    shopify_key: str
    store_name: str
    ads_customer_id: str
    cost: float
    prior_cost: float  # Ads spend for the prior equivalent period; 0 if unavailable


class MerAdsData(TypedDict):
    """Return type for get_mer_ads_data. Contains Google Ads spend per store only."""
    date_range: str
    generated_at: str
    stores: list[MerAdsRow]
    total_cost: float
    total_prior_cost: float


class MerReportRow(TypedDict):
    """Fully joined row with both Google Ads spend and Shopify net sales.

    mer is Ad Spend % = (cost / net_sales) * 100. Lower is better.
    Example: mer=4.3 means ads cost 4.3% of net sales.

    mer_delta = current mer - prior mer. Positive means worsening (higher ad spend %),
    negative means improving (lower ad spend %). Displayed with sign in the Sheets report.

    trend: "Improving" (delta < -0.5pp), "Worsening" (delta > +0.5pp),
           "Stable" (within 0.5pp), "No Prior Data" (prior period unavailable).
    """
    shopify_key: str
    store_name: str
    ads_customer_id: str
    cost: float
    net_sales: float
    mer: float          # Ad Spend % = (cost / net_sales) * 100; lower is better
    mer_status: str     # "Strong" | "Good" | "Watch" | "Poor" | "No Spend" | "No Sales"
    prior_net_sales: float   # Net sales in the prior equivalent period; 0 if unavailable
    prior_mer: float         # Ad Spend % for prior period; 0 if no prior data
    mer_delta: float         # current_mer - prior_mer (positive = worsening)
    trend: str               # "Improving" | "Worsening" | "Stable" | "No Prior Data"


class MerReportData(TypedDict):
    """Fully assembled MER report, ready to write to Sheets or post to Chat.

    portfolio_mer is Ad Spend % = (total_cost / total_net_sales) * 100.
    portfolio_mer_delta = current portfolio_mer - prior portfolio_mer.
    Positive = worsening (ad spend growing faster than sales), negative = improving.
    """
    date_range: str
    generated_at: str
    stores: list[MerReportRow]
    total_cost: float
    total_net_sales: float
    portfolio_mer: float          # Ad Spend % = (total_cost / total_net_sales) * 100
    portfolio_mer_status: str
    total_prior_net_sales: float  # Prior period net sales across all stores
    portfolio_prior_mer: float    # Ad Spend % for the prior equivalent period
    portfolio_mer_delta: float    # current portfolio_mer - portfolio_prior_mer
    portfolio_trend: str          # "Improving" | "Worsening" | "Stable" | "No Prior Data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_enabled_stores() -> list[dict]:
    """Load ENABLED stores from stores_mapping.json."""
    with open(_MAPPING_PATH) as f:
        data = json.load(f)
    return [s for s in data["stores"] if s["ads_status"] == "ENABLED"]


def _mer_status(mer_pct: float, cost: float, net_sales: float) -> str:
    """Classify an Ad Spend % value into an action-oriented status label.

    mer_pct is (cost / net_sales) * 100. Lower is better.
    Thresholds: Strong < 5%, Good 5-10%, Watch 10-20%, Poor > 20%.
    """
    if cost == 0:
        return "No Spend"
    if net_sales == 0:
        return "No Sales"
    if mer_pct <= 5.0:
        return "Strong"
    if mer_pct <= 10.0:
        return "Good"
    if mer_pct <= 20.0:
        return "Watch"
    return "Poor"


def _trend_label(mer_delta: float, has_prior: bool) -> str:
    """Classify the direction of MER change.

    mer_delta = current_mer - prior_mer. Positive = worsening (ad spend % rising),
    negative = improving (ad spend % falling).
    Threshold: 0.5 percentage points -- moves smaller than this are Stable.
    """
    if not has_prior:
        return "No Prior Data"
    if mer_delta < -0.5:
        return "Improving"
    if mer_delta > 0.5:
        return "Worsening"
    return "Stable"


def _prior_period_range(date_range: str) -> dict | None:
    """Return an explicit date range dict for the prior equivalent period.

    Supports LAST_7_DAYS and LAST_30_DAYS presets only. Returns None for all other
    inputs (explicit date strings, THIS_MONTH, etc.) -- callers treat None as
    "no prior period available."

    Google Ads LAST_7_DAYS = (today-7) to (today-1).
    Prior 7 days              = (today-14) to (today-8).

    Google Ads LAST_30_DAYS = (today-30) to (today-1).
    Prior 30 days              = (today-60) to (today-31).

    Returns a dict compatible with date_range_clause() in utils.py.
    """
    today = datetime.now(timezone.utc).date()
    if date_range == "LAST_7_DAYS":
        end = today - timedelta(days=8)
        start = today - timedelta(days=14)
        return {"start_date": str(start), "end_date": str(end)}
    if date_range == "LAST_30_DAYS":
        end = today - timedelta(days=31)
        start = today - timedelta(days=60)
        return {"start_date": str(start), "end_date": str(end)}
    return None


# ---------------------------------------------------------------------------
# Main data pull (Google Ads side only)
# ---------------------------------------------------------------------------

def get_mer_ads_data(
    client: GoogleAdsClient,
    date_range: str = "LAST_7_DAYS",
) -> MerAdsData:
    """Pull Google Ads spend for all ENABLED stores from stores_mapping.json.

    Returns cost (current period) and prior_cost (equivalent prior period) per store,
    keyed by shopify_key. Accounts that error on query are included with cost=0.

    Prior period is automatically computed for LAST_7_DAYS and LAST_30_DAYS presets.
    All other date_range values get prior_cost=0 (no prior data available).

    Sorted by cost descending. Pair with shopify_query_sales() results to
    compute MER and trend per store.

    date_range: preset like LAST_7_DAYS, THIS_MONTH, LAST_30_DAYS, or
                explicit as 'start_date=YYYY-MM-DD,end_date=YYYY-MM-DD'.
    """
    stores = _load_enabled_stores()
    prior_range = _prior_period_range(date_range)
    rows: list[MerAdsRow] = []
    total_cost = 0.0
    total_prior_cost = 0.0

    for store in stores:
        cid = store["ads_customer_id"]
        try:
            summary = get_account_summary(client, cid, date_range)
            cost = round(summary["cost"], 2)
        except Exception:
            cost = 0.0

        prior_cost = 0.0
        if prior_range:
            try:
                prior_summary = get_account_summary(client, cid, prior_range)
                prior_cost = round(prior_summary["cost"], 2)
            except Exception:
                prior_cost = 0.0

        total_cost += cost
        total_prior_cost += prior_cost
        rows.append(MerAdsRow(
            shopify_key=store["shopify_key"],
            store_name=store["ads_name"],
            ads_customer_id=cid,
            cost=cost,
            prior_cost=prior_cost,
        ))

    rows.sort(key=lambda r: r["cost"], reverse=True)

    return MerAdsData(
        date_range=date_range,
        generated_at=datetime.now(timezone.utc).isoformat(),
        stores=rows,
        total_cost=round(total_cost, 2),
        total_prior_cost=round(total_prior_cost, 2),
    )


# ---------------------------------------------------------------------------
# Assembly helper (called by Claude after collecting Shopify data)
# ---------------------------------------------------------------------------

def assemble_mer_report(
    ads_data: MerAdsData,
    net_sales_by_shopify_key: dict[str, float],
    prior_net_sales_by_shopify_key: dict[str, float] | None = None,
) -> MerReportData:
    """Join Google Ads spend with Shopify net sales and compute MER plus trend.

    ads_data: result from get_mer_ads_data(). Includes cost and prior_cost per store.
    net_sales_by_shopify_key: dict mapping shopify_key -> current period net_sales float.
                               Keys not present default to 0.0.
    prior_net_sales_by_shopify_key: dict mapping shopify_key -> prior period net_sales float.
                                     Pass None (or omit) to skip trend computation.
                                     Keys not present default to 0.0.

    Returns fully assembled MerReportData ready for write_mer_report().
    """
    rows: list[MerReportRow] = []
    total_net_sales = 0.0
    total_prior_net_sales = 0.0

    for store in ads_data["stores"]:
        key = store["shopify_key"]
        net_sales = round(net_sales_by_shopify_key.get(key, 0.0), 2)
        cost = store["cost"]
        prior_cost = store["prior_cost"]

        # Current period Ad Spend % = (cost / net_sales) * 100. Lower is better.
        mer = round((cost / net_sales) * 100, 2) if net_sales > 0 else 0.0
        total_net_sales += net_sales

        # Prior period
        if prior_net_sales_by_shopify_key is not None:
            prior_net_sales = round(prior_net_sales_by_shopify_key.get(key, 0.0), 2)
        else:
            prior_net_sales = 0.0
        total_prior_net_sales += prior_net_sales

        has_prior = prior_net_sales_by_shopify_key is not None and (prior_cost > 0 or prior_net_sales > 0)
        prior_mer = round((prior_cost / prior_net_sales) * 100, 2) if prior_net_sales > 0 else 0.0
        mer_delta = round(mer - prior_mer, 2) if has_prior else 0.0

        rows.append(MerReportRow(
            shopify_key=key,
            store_name=store["store_name"],
            ads_customer_id=store["ads_customer_id"],
            cost=cost,
            net_sales=net_sales,
            mer=mer,
            mer_status=_mer_status(mer, cost, net_sales),
            prior_net_sales=prior_net_sales,
            prior_mer=prior_mer,
            mer_delta=mer_delta,
            trend=_trend_label(mer_delta, has_prior),
        ))

    total_cost = ads_data["total_cost"]
    total_prior_cost = ads_data["total_prior_cost"]

    # Portfolio Ad Spend % = total ads cost as % of total net sales
    portfolio_mer = round((total_cost / total_net_sales) * 100, 2) if total_net_sales > 0 else 0.0

    has_portfolio_prior = prior_net_sales_by_shopify_key is not None and (
        total_prior_cost > 0 or total_prior_net_sales > 0
    )
    portfolio_prior_mer = (
        round((total_prior_cost / total_prior_net_sales) * 100, 2)
        if total_prior_net_sales > 0
        else 0.0
    )
    portfolio_mer_delta = round(portfolio_mer - portfolio_prior_mer, 2) if has_portfolio_prior else 0.0

    return MerReportData(
        date_range=ads_data["date_range"],
        generated_at=ads_data["generated_at"],
        stores=rows,
        total_cost=total_cost,
        total_net_sales=round(total_net_sales, 2),
        portfolio_mer=portfolio_mer,
        portfolio_mer_status=_mer_status(portfolio_mer, total_cost, total_net_sales),
        total_prior_net_sales=round(total_prior_net_sales, 2),
        portfolio_prior_mer=portfolio_prior_mer,
        portfolio_mer_delta=portfolio_mer_delta,
        portfolio_trend=_trend_label(portfolio_mer_delta, has_portfolio_prior),
    )
