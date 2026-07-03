"""FastMCP server -- exposes Google Ads tools over stdio."""

from typing import Optional
from fastmcp import FastMCP

from ads_mcp.client import get_client
from ads_mcp.reporting.accounts import AccountInfo, list_accounts
from ads_mcp.reporting.performance import (
    AccountSummary,
    AdGroupRow,
    BrandRow,
    CampaignRow,
    ImageAssetInfo,
    KeywordRow,
    ProductRow,
    SearchTermRow,
    get_account_summary,
    get_ad_group_performance,
    get_brand_performance,
    get_campaign_performance,
    get_keyword_performance,
    get_product_performance,
    get_search_terms,
    list_image_assets,
)
from ads_mcp.creation.assets import upload_image_asset
from ads_mcp.creation.pmax import (
    PMaxCampaignConfig,
    PMaxCreationResult,
    PMaxProposal,
    commit_pmax_campaign,
    get_pmax_proposal,
    propose_pmax_campaign,
)
from ads_mcp.creation.search import (
    SearchCampaignConfig,
    SearchCreationResult,
    SearchProposal,
    commit_search_campaign,
    get_search_proposal,
    propose_search_campaign,
)
from ads_mcp.creation.shopping import (
    ShoppingCreationResult,
    ShoppingProposal,
    StandardShoppingConfig,
    commit_standard_shopping_campaign,
    get_shopping_proposal,
    propose_standard_shopping_campaign,
)
from ads_mcp.reporting.health import (
    AnomalyResult,
    BudgetPacingResult,
    DisapprovalsResult,
    TroasPacingResult,
    check_budget_pacing,
    check_troas_pacing,
    find_anomalies,
    find_disapprovals,
)
from ads_mcp.reporting.digest import DigestData, get_cross_account_digest
from ads_mcp.reporting.mer import MerAdsData, MerReportData, get_mer_ads_data
from ads_mcp.reporting.product_velocity import ProductVelocityResult, classify_product_velocity
from ads_mcp.reporting.troas_audit import TroasAuditResult, build_troas_proposals, check_rollback_flags
from ads_mcp.reporting.budget_audit import build_budget_proposals
from ads_mcp.proposals.troas import apply_troas_change, apply_troas_adgroup_change
from ads_mcp.proposals.budget import apply_budget_change
from ads_mcp.notify import (
    BudgetAuditCardData,
    BudgetCommitCardData,
    BudgetCommitItem,
    BudgetErrorItem,
    DigestCardData,
    PostResult,
    TroasAuditCardData,
    TroasCommitCardData,
    TroasCommitItem,
    TroasErrorItem,
    TroasProposalItem,
    TroasRollbackCardData,
    TroasRollbackItem,
    post_budget_audit_card,
    post_budget_commit_card,
    post_digest_card_to_google_chat,
    post_to_google_chat,
    post_to_troas_chat,
    post_troas_audit_card,
    post_troas_commit_card,
    post_troas_rollback_card,
)
from ads_mcp.sheets import (
    write_digest,
    write_mer_report,
    write_troas_proposals,
    read_troas_decisions,
    append_troas_log,
    read_troas_log_recent,
    has_pending_troas_decisions,
    write_budget_proposals,
    read_budget_decisions,
    append_budget_log,
    write_dfw_lookup_table,
    read_dfw_lookup_table,
)

mcp: FastMCP = FastMCP("google-ads")


def _parse_date_range(date_range: str) -> str | dict:
    """Accept either a preset string or 'start_date=YYYY-MM-DD,end_date=YYYY-MM-DD'."""
    if "start_date=" in date_range:
        parts = dict(p.split("=") for p in date_range.split(","))
        return {"start_date": parts["start_date"], "end_date": parts["end_date"]}
    return date_range


# ---------------------------------------------------------------------------
# Account tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_google_ads_accounts() -> list[AccountInfo]:
    """List all Google Ads accounts visible under the MCC.

    Returns one entry per sub-account with id, name, currency, timezone, and status.
    Use the returned 'id' values as customer_id in all other tools.
    """
    return list_accounts(get_client())


@mcp.tool()
def get_google_ads_account_summary(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
) -> AccountSummary:
    """Return aggregate performance metrics for a single Google Ads account.

    customer_id: 10-digit account ID from list_google_ads_accounts (no dashes).
    date_range: preset like LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH,
                or explicit range as 'start_date=YYYY-MM-DD,end_date=YYYY-MM-DD'.

    Returns: impressions, clicks, cost (USD), conversions, conversions_value,
             ctr, avg_cpc, roas (conversions_value / cost).
    """
    return get_account_summary(get_client(), customer_id, _parse_date_range(date_range))


# ---------------------------------------------------------------------------
# Performance tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_google_ads_campaign_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    status_filter: Optional[str] = None,
) -> list[CampaignRow]:
    """Return per-campaign performance for a Google Ads account, sorted by cost descending.

    customer_id: 10-digit account ID.
    date_range: preset or explicit range (see get_google_ads_account_summary).
    status_filter: optional -- pass "ENABLED", "PAUSED", or "REMOVED" to filter by status.

    Returns for each campaign: id, name, status, channel type, bidding strategy,
    target_roas, target_cpa, daily budget, impressions, clicks, cost, conversions,
    conversions_value, roas, ctr, avg_cpc, search_impression_share.
    """
    filters = None
    if status_filter:
        filters = {"campaign.status": status_filter}
    return get_campaign_performance(get_client(), customer_id, _parse_date_range(date_range), filters)


@mcp.tool()
def get_google_ads_ad_group_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    campaign_id: Optional[str] = None,
) -> list[AdGroupRow]:
    """Return per-ad-group performance for a Google Ads account, sorted by cost descending.

    customer_id: 10-digit account ID.
    date_range: preset or explicit range.
    campaign_id: optional -- restrict to ad groups within a specific campaign.
    """
    return get_ad_group_performance(get_client(), customer_id, _parse_date_range(date_range), campaign_id)


@mcp.tool()
def get_google_ads_search_terms(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    campaign_id: Optional[str] = None,
) -> list[SearchTermRow]:
    """Return search terms that triggered ads, sorted by cost descending.

    customer_id: 10-digit account ID.
    date_range: preset or explicit range.
    campaign_id: optional -- restrict to one campaign.

    status field: ADDED (already a keyword), EXCLUDED (negative keyword), NONE (neither).
    """
    return get_search_terms(get_client(), customer_id, _parse_date_range(date_range), campaign_id)


@mcp.tool()
def get_google_ads_keyword_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
) -> list[KeywordRow]:
    """Return keyword-level performance for a Google Ads account, sorted by cost descending.

    customer_id: 10-digit account ID.
    date_range: preset or explicit range.

    Returns: keyword text, match type, status, quality score (1-10 or null),
             ad group, campaign, impressions, clicks, cost, conversions, avg_cpc.
    """
    return get_keyword_performance(get_client(), customer_id, _parse_date_range(date_range))


@mcp.tool()
def get_google_ads_product_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
) -> list[ProductRow]:
    """Return product-level performance from Shopping and Performance Max campaigns.

    customer_id: 10-digit account ID.
    date_range: preset or explicit range.

    Sorted by conversions_value descending. Returns product_id, title, product_type,
    campaign info, impressions, clicks, cost, conversions, conversions_value, roas.
    """
    return get_product_performance(get_client(), customer_id, _parse_date_range(date_range))


@mcp.tool()
def classify_google_ads_product_velocity(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
) -> ProductVelocityResult:
    """Classify products into performance tiers by comparing current vs prior period.

    Runs shopping_performance_view for two equal-length windows (current + prior),
    aggregates metrics per product_id across all campaigns, then classifies each
    product into one of four tiers:

      NEW_WINNER:       Strong current ROAS (>= account target), minimal prior spend.
                        Recently started converting well.
                        Action: consider dedicated campaign or higher listing group priority.

      TURNING_LOSER:    Was performing at or above target, now showing 30%+ ROAS decay.
                        Still receiving spend, so decline is a real signal.
                        Action: investigate pricing, inventory, or competition.

      CONSISTENT_LOSER: High current spend with ROAS below 1.0 (costs more than it earns),
                        with an established spend history (not a brand-new product).
                        Action: candidate for feed exclusion or listing group demotion.

      ON_TRACK:         Meaningful spend with acceptable ROAS. No action required.

    Products with insufficient spend in both windows are excluded to reduce noise.
    The prior window is computed automatically -- the same-duration period immediately
    before the current window (e.g. LAST_30_DAYS prior = the 30 days before that).

    customer_id: 10-digit account ID from list_google_ads_accounts (no dashes).
    date_range: preset like LAST_7_DAYS, LAST_30_DAYS (default), LAST_14_DAYS, or
                explicit range as 'start_date=YYYY-MM-DD,end_date=YYYY-MM-DD'.

    Returns: account_target_roas used for classification, summary counts per tier,
             and per-tier product lists with current/prior cost, ROAS, ROAS delta,
             and a recommended action for each product.
    """
    return classify_product_velocity(get_client(), customer_id, _parse_date_range(date_range))


# ---------------------------------------------------------------------------
# Health check tools
# ---------------------------------------------------------------------------

@mcp.tool()
def check_google_ads_troas_pacing(
    customer_id: str,
    drift_pct: float = 10.0,
) -> list[TroasPacingResult]:
    """Check actual vs target ROAS for all TARGET_ROAS campaigns in an account.

    customer_id: 10-digit account ID.
    drift_pct: flag campaigns where actual ROAS deviates from target by this percentage or more.

    Uses last 7 days of data for stability. Returns: campaign name, target_roas,
    actual_roas, drift_pct (positive = over target, negative = under target),
    status (ON_TRACK / OVER / UNDER). Sorted by absolute drift descending.
    """
    return check_troas_pacing(get_client(), customer_id, drift_pct)


@mcp.tool()
def check_google_ads_budget_pacing(
    customer_id: str,
) -> list[BudgetPacingResult]:
    """Check today's spend vs expected pace for each campaign.

    customer_id: 10-digit account ID.

    Expected spend = daily_budget * (current hour of day / 24).
    Status: OVERPACING (ratio > 1.2), UNDERPACING (ratio < 0.5), ON_TRACK otherwise.
    Sorted by deviation from 1.0 (worst pacing first).
    """
    return check_budget_pacing(get_client(), customer_id)


@mcp.tool()
def find_google_ads_anomalies(
    customer_id: str,
    metric: str = "cost",
    sensitivity: float = 2.0,
) -> AnomalyResult:
    """Detect statistical anomalies in a daily metric over the last 30 days.

    customer_id: 10-digit account ID.
    metric: one of "impressions", "clicks", "cost", "conversions", "conversions_value".
    sensitivity: standard deviations required to flag a day as anomalous (default 2.0).

    Returns: mean, std_dev, list of anomaly days with their sigma values,
             and the most recent day's value and deviation for quick assessment.
    """
    return find_anomalies(get_client(), customer_id, metric, sensitivity)


@mcp.tool()
def find_google_ads_disapprovals(
    customer_id: str,
) -> DisapprovalsResult:
    """Return all disapproved ads and keywords with their policy violation topics.

    customer_id: 10-digit account ID.

    Returns: ads (list of disapproved ad entries), keywords (list of disapproved
    keyword entries), total_count. Each entry includes campaign, ad group, and
    the policy topic(s) causing the disapproval.
    """
    return find_disapprovals(get_client(), customer_id)


# ---------------------------------------------------------------------------
# Digest tools (Phase 2)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_google_ads_cross_account_digest(
    date_range: str = "LAST_7_DAYS",
) -> DigestData:
    """Aggregate performance and health data across ALL Google Ads accounts in the MCC.

    Call this first when generating a digest. It returns structured data covering every
    enabled sub-account: total spend, conversions, ROAS, clicks, impressions, plus per-account
    tROAS alerts, budget pacing alerts, and disapproval counts.

    date_range: preset like LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, LAST_MONTH.

    After receiving the data, write a concise narrative digest and call
    post_digest_to_google_chat with the result.
    """
    return get_cross_account_digest(get_client(), date_range)


@mcp.tool()
def update_google_ads_sheets_dashboard(
    digest_data: dict,
) -> dict:
    """Write digest data to the Google Ads Performance Dashboard spreadsheet.

    Call this after get_google_ads_cross_account_digest, passing the full digest_data
    dict as returned by that tool. On first run, creates tabs, formatting, and three
    bar charts (Cost, ROAS, Conversions by account). On subsequent runs, refreshes
    all data and the charts update automatically.

    Requires GOOGLE_ADS_SHEETS_DASHBOARD_ID in .env. Returns the Dashboard tab URL.
    """
    import os
    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError(
            "GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set. Add it to your .env file:\n"
            "GOOGLE_ADS_SHEETS_DASHBOARD_ID=11CcymBpqMtgR2vjeuqtuplUI5dgc2KnIhUHNjUZWMG0"
        )
    url = write_digest(digest_data, spreadsheet_id)  # type: ignore[arg-type]
    return {"status": "ok", "dashboard_url": url}


@mcp.tool()
def get_google_ads_mer_data(
    date_range: str = "LAST_7_DAYS",
) -> MerAdsData:
    """Pull Google Ads spend (current + prior period) for all 18 stores, keyed by shopify_key.

    Returns cost and prior_cost per store. prior_cost is automatically computed for
    LAST_7_DAYS (prior 7 days) and LAST_30_DAYS (prior 30 days) presets. All other
    date ranges return prior_cost=0.

    Workflow for the full MER report with trend:
      1. Call this tool to get current and prior ads spend per store.
      2. For each store, call shopify_query_sales(store_key=shopify_key,
         metrics=["net_sales"], dimensions=["day"], days=14) via the shopify-toolup MCP.
         Read the full CSV. Split rows by date: last 7 days = current net_sales,
         days 8-14 = prior_net_sales.
      3. Assemble mer_data including prior_mer and mer_delta per store.
      4. Call update_mer_report_tab with the assembled data to write results to Sheets.
      5. Include portfolio MER and trend in the Chat digest message.

    date_range: preset like LAST_7_DAYS, THIS_MONTH, LAST_30_DAYS, or
                explicit as 'start_date=YYYY-MM-DD,end_date=YYYY-MM-DD'.

    Returns: date_range, generated_at, total_cost, total_prior_cost,
    stores (list sorted by cost desc). Each store entry: shopify_key, store_name,
    ads_customer_id, cost, prior_cost.
    """
    return get_mer_ads_data(get_client(), _parse_date_range(date_range))  # type: ignore[arg-type]


@mcp.tool()
def update_mer_report_tab(mer_data: dict) -> dict:
    """Write a fully assembled MER report to the MER tab in the Google Ads Performance Dashboard.

    Call this after computing MER for all stores (Google Ads spend joined with Shopify net sales).

    mer_data must be a dict matching this structure:
      {
        "date_range": "LAST_7_DAYS",
        "generated_at": "<ISO timestamp>",
        "total_cost": 12345.67,
        "total_net_sales": 56789.01,
        "portfolio_mer": 4.6,
        "portfolio_mer_status": "Strong",
        "total_prior_net_sales": 54000.00,
        "portfolio_prior_mer": 5.1,
        "portfolio_mer_delta": -0.5,
        "portfolio_trend": "Improving",
        "stores": [
          {
            "shopify_key": "toolupstore",
            "store_name": "ToolUp",
            "ads_customer_id": "1864748540",
            "cost": 3456.78,
            "net_sales": 18000.00,
            "mer": 5.21,
            "mer_status": "Strong",
            "prior_net_sales": 16500.00,
            "prior_mer": 6.10,
            "mer_delta": -0.89,
            "trend": "Improving"
          },
          ...
        ]
      }

    mer_status values: "Strong" (<=5%), "Good" (5-10%), "Watch" (10-20%), "Poor" (>20%),
    "No Sales" (net_sales=0 with spend), "No Spend" (cost=0).
    trend values: "Improving" (delta < -0.5pp), "Worsening" (delta > +0.5pp),
    "Stable", "No Prior Data".

    Writes MER tab (overwrite, 9 columns A-I) and appends to MER History tab.
    Returns the MER tab URL. Requires GOOGLE_ADS_SHEETS_DASHBOARD_ID in .env.
    """
    import os
    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError(
            "GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set. Add it to your .env file:\n"
            "GOOGLE_ADS_SHEETS_DASHBOARD_ID=11CcymBpqMtgR2vjeuqtuplUI5dgc2KnIhUHNjUZWMG0"
        )
    url = write_mer_report(mer_data, spreadsheet_id)  # type: ignore[arg-type]
    return {"status": "ok", "mer_tab_url": url}


@mcp.tool()
def post_digest_to_google_chat(message: str) -> PostResult:
    """Post a digest narrative to the Google Chat space via the configured webhook.

    Call this after writing the narrative from get_google_ads_cross_account_digest data.
    message is plain text; keep under 4000 characters for Google Chat compatibility.
    Returns status confirmation and message length.

    Requires GOOGLE_CHAT_WEBHOOK_URL in .env. Raises a clear error if not set.
    """
    return post_to_google_chat(message)


@mcp.tool()
def post_digest_card_to_google_chat(card_data: dict) -> PostResult:
    """Post the daily or weekly digest as a structured Google Chat card.

    Preferred over post_digest_to_google_chat. Renders a cardsV2 message with:
    - Card header: "Google Ads + MER Digest" + date range subtitle
    - Portfolio Overview section: decoratedText widget for Ad Spend %, net sales, ads spend, ROAS, conversions, clicks
    - Ad Spend % by Store section: HTML-formatted best/watch stores
    - Alerts section: tROAS, zero conversions, budget pacing, disapprovals
    - Priority Actions section: numbered action list
    - Strategic Summary section (weekly only)
    - Clickable buttons for Ads Dashboard and MER Report links

    card_data must be a dict matching the DigestCardData TypedDict in ads_mcp/notify.py.
    All text fields are plain strings -- no raw HTML needed except strategic_summary_html.
    The card builder applies color tokens and HTML formatting automatically.

    Required keys:
      date_str             -- "May 21, 2026"
      date_range_label     -- "Last 7 Days" or "Last 30 Days"
      portfolio_mer        -- float, e.g. 4.3
      portfolio_mer_status -- "Strong" | "Good" | "Watch" | "Poor" | "No Sales"
      portfolio_trend      -- "Improving" | "Worsening" | "Stable" | "No Prior Data"
      portfolio_mer_delta  -- pp change vs prior (negative = improving; 0 if no prior)
      total_net_sales      -- float
      total_cost           -- float
      portfolio_roas       -- float
      total_conversions    -- float
      total_clicks         -- int
      mer_stores           -- list of {name, mer, status, spend, net_sales} dicts,
                              all non-zero-spend stores sorted by MER ascending
      troas_alerts         -- list of {account, campaign, actual_roas, target_roas,
                              drift_pct, status} dicts; empty list if none
      zero_conv_accounts   -- list of {account, spend} dicts; empty list if none
      budget_pacing_note   -- plain text note, e.g. "4 accounts underpacing -- early-day";
                              empty string if no underpacing
      budget_overpacing    -- list of {account, campaign} dicts; empty list if none
      disapproval_count    -- int
      disapproval_accounts -- list of account name strings; empty list if clean
      priority_actions     -- list of plain text action strings (builder numbers them)
      strategic_summary_html -- HTML string for weekly strategic narrative; empty for daily
      dashboard_url        -- URL string or empty string if unavailable
      mer_tab_url          -- URL string or empty string if unavailable

    Requires GOOGLE_CHAT_WEBHOOK_URL in .env.
    """
    typed: DigestCardData = card_data  # type: ignore[assignment]
    return post_digest_card_to_google_chat(typed)


# ---------------------------------------------------------------------------
# tROAS audit + commit tools (Phase 3)
# ---------------------------------------------------------------------------

@mcp.tool()
def run_troas_audit() -> dict:
    """Run the M/W/F tROAS adjustment audit across all Google Ads accounts.

    Workflow:
      1. Reads the tROAS Log to identify campaigns adjusted in the last 3 days
         (cooldown -- these are skipped).
      2. Queries every ENABLED TARGET_ROAS campaign across all accounts.
      3. Proposes tROAS changes for campaigns outside the 7% drift threshold:
           TIGHTEN if actual ROAS is more than 7% below target.
           LOOSEN  if actual ROAS is more than 7% above target AND L7 spend
                   grew >= 15% vs the prior 7 days.
      4. Step size based on drift magnitude:
           7-13%  ->  25pp  |  13-22% ->  50pp
           22-30% ->  75pp  |  30%+   -> 100pp
      5. Writes proposals to the tROAS Proposals tab (overwrite).
      6. Posts a summary to the tROAS Google Chat space with the Sheets link.

    Eligibility: ENABLED campaigns, TARGET_ROAS bidding, L7 spend >= $100.

    Returns: run summary with proposal count and the Proposals tab URL.
    """
    import os
    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError("GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set.")

    client = get_client()

    # Build cooldown set from tROAS Log (7-day window: skips Wed + Fri + following Mon)
    recent_log = read_troas_log_recent(spreadsheet_id, days=7)
    recently_adjusted: set[tuple[str, str]] = {
        (r["customer_id"], r["campaign_id"]) for r in recent_log
    }

    # Run audit
    result = build_troas_proposals(client, recently_adjusted)
    proposals = result["proposals"]

    # Write to Sheets
    proposals_url = write_troas_proposals(proposals, spreadsheet_id)

    # Post to tROAS Chat space
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if proposals:
        tighten_count = sum(1 for p in proposals if p["direction"] == "TIGHTEN")
        loosen_count  = sum(1 for p in proposals if p["direction"] == "LOOSEN")
        accounts_count = len({p["customer_id"] for p in proposals})
        top_proposals = [
            TroasProposalItem(
                account=p["account_name"],
                campaign=p["campaign_name"],
                direction=p["direction"],
                current_pct=p["current_target_roas"],
                proposed_pct=p["proposed_target_roas"],
                drift_pct=p["drift_pct"],
            )
            for p in proposals[:10]
        ]
        card_data = TroasAuditCardData(
            date_str=date_str,
            total_proposals=len(proposals),
            tighten_count=tighten_count,
            loosen_count=loosen_count,
            accounts_count=accounts_count,
            top_proposals=top_proposals,
            proposals_url=proposals_url,
        )
        try:
            post_troas_audit_card(card_data)
        except Exception as exc:
            return {
                "status": "ok",
                "total_proposals": len(proposals),
                "accounts_checked": result["accounts_checked"],
                "proposals_url": proposals_url,
                "chat_warning": str(exc),
            }
    else:
        msg = (
            f"tROAS Audit | {date_str}\n"
            f"No proposals this cycle. All {result['accounts_checked']} accounts "
            f"are within drift thresholds or on cooldown."
        )
        try:
            post_to_troas_chat(msg)
        except Exception as exc:
            return {
                "status": "ok",
                "total_proposals": 0,
                "accounts_checked": result["accounts_checked"],
                "proposals_url": "",
                "chat_warning": str(exc),
            }

    return {
        "status": "ok",
        "total_proposals": len(proposals),
        "accounts_checked": result["accounts_checked"],
        "proposals_url": proposals_url,
    }


@mcp.tool()
def commit_troas_changes() -> dict:
    """Apply all Approved rows from the tROAS Proposals tab to Google Ads.

    Reads the tROAS Proposals tab and applies every row where Decision = 'Approve'.
    For each approved row:
      - Calls the Google Ads API to update campaign.target_roas.target_roas.
      - Appends a record to the tROAS Log tab (used for cooldown and rollback).
    Skipped rows (Decision = 'Skip' or '-') are left unchanged.

    Posts a commit summary to the tROAS Google Chat space.
    Returns: counts of applied, skipped, and errored campaigns.
    """
    import os
    from datetime import datetime, timezone

    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError("GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set.")

    client = get_client()
    approved_rows = read_troas_decisions(spreadsheet_id)

    if not approved_rows:
        return {"status": "ok", "applied": 0, "skipped": 0, "errors": 0, "detail": []}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    applied_log: list[dict] = []
    results_detail: list[dict] = []
    applied = 0
    errors = 0

    for row in approved_rows:
        ad_group_id = row.get("Ad Group ID", "").strip()
        customer_id = row.get("Customer ID", "").strip()
        campaign_id = row.get("Campaign ID", "").strip()
        campaign_name = row.get("Campaign Name", "").strip()
        current_pct = float(row.get("Current tROAS (%)", 0) or 0)
        proposed_pct = float(row.get("Proposed tROAS (%)", 0) or 0)
        change_pp = int(float(row.get("Change (pp)", 0) or 0))

        if not customer_id:
            errors += 1
            results_detail.append({
                "status": "error",
                "campaign_name": campaign_name or "(unknown)",
                "old_target_roas_pct": current_pct,
                "new_target_roas_pct": proposed_pct,
                "change_pp": change_pp,
                "error": "Customer ID missing -- re-run audit to refresh proposals",
            })
            continue

        bidding_type = row.get("Bidding Type", "TARGET_ROAS").strip() or "TARGET_ROAS"

        if ad_group_id:
            # Ad group level tROAS (Standard Shopping)
            result = apply_troas_adgroup_change(
                client=client,
                customer_id=customer_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                ad_group_id=ad_group_id,
                current_target_roas_pct=current_pct,
                proposed_target_roas_pct=proposed_pct,
                change_pp=change_pp,
            )
        else:
            # Campaign level tROAS (Standard or PMax)
            result = apply_troas_change(
                client=client,
                customer_id=customer_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                current_target_roas_pct=current_pct,
                proposed_target_roas_pct=proposed_pct,
                change_pp=change_pp,
                bidding_type=bidding_type,
            )

        r_with_meta = dict(result)
        r_with_meta["account_name"] = row.get("Account Name", "")
        results_detail.append(r_with_meta)

        if result["status"] == "applied":
            applied += 1
            applied_log.append({
                "applied_date": today,
                "customer_id": result["customer_id"],
                "campaign_id": result["campaign_id"],
                "campaign_name": result["campaign_name"],
                "ad_group_id": ad_group_id,
                "ad_group_name": row.get("Ad Group Name", ""),
                "account_name": row.get("Account Name", ""),
                "direction": row.get("Direction", ""),
                "old_target_roas": result["old_target_roas_pct"],
                "new_target_roas": result["new_target_roas_pct"],
                "change_pp": result["change_pp"],
                "l7_spend": row.get("L7 Spend ($)", "0"),
            })
        else:
            errors += 1

    # Append to tROAS Log (cooldown tracking + rollback monitoring)
    if applied_log:
        append_troas_log(applied_log, spreadsheet_id)

    skipped = len(approved_rows) - applied - errors

    # Post commit card to tROAS Chat
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    applied_items: list[TroasCommitItem] = []
    error_items: list[TroasErrorItem] = []
    for r in results_detail:
        if r["status"] == "applied":
            direction = "UP" if r["new_target_roas_pct"] > r["old_target_roas_pct"] else "DOWN"
            applied_items.append(TroasCommitItem(
                campaign_name=r["campaign_name"],
                account_name=r.get("account_name", ""),
                old_pct=r["old_target_roas_pct"],
                new_pct=r["new_target_roas_pct"],
                change_pp=r["change_pp"],
                direction=direction,
            ))
        elif r["status"] == "error":
            error_items.append(TroasErrorItem(
                campaign_name=r["campaign_name"],
                error=r["error"],
            ))

    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    commit_card = TroasCommitCardData(
        date_str=date_str,
        applied=applied,
        errors=errors,
        skipped=skipped,
        applied_items=applied_items,
        error_items=error_items,
        proposals_url=sheet_url,
    )
    try:
        post_troas_commit_card(commit_card)
    except Exception:
        pass

    return {
        "status": "ok",
        "applied": applied,
        "errors": errors,
        "skipped": skipped,
        "detail": results_detail,
    }


@mcp.tool()
def check_troas_rollback() -> dict:
    """Check campaigns adjusted in the last 72h for conversion dropoffs.

    Reads the tROAS Log for campaigns applied in the last 3 days that had
    L7 spend >= $1000 at time of adjustment. For each, compares conversions
    in the last 72h against the prior 72h window.

    If any campaign shows a >= 50% drop, posts a flag to the tROAS Chat space
    with options to rollback, hold, or proceed as normal.

    Returns: list of flagged campaigns (empty if all clear).
    """
    import os
    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError("GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set.")

    client = get_client()
    recent_log = read_troas_log_recent(spreadsheet_id, days=3)

    if not recent_log:
        return {"status": "ok", "flags": [], "message": "No campaigns adjusted in the last 3 days."}

    flags = check_rollback_flags(client, recent_log)

    if flags:
        from datetime import datetime, timezone
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        rollback_card = TroasRollbackCardData(
            date_str=date_str,
            flags=[
                TroasRollbackItem(
                    account_name=f["account_name"],
                    campaign_name=f["campaign_name"],
                    direction=f["direction"],
                    old_roas_pct=float(f["old_target_roas"]),
                    new_roas_pct=float(f["new_target_roas"]),
                    current_72h_convs=f["current_72h_conversions"],
                    prior_72h_convs=f["prior_72h_conversions"],
                    drop_pct=f["conversion_drop_pct"],
                )
                for f in flags
            ],
            proposals_url=sheet_url,
        )
        try:
            post_troas_rollback_card(rollback_card)
        except Exception:
            pass

    return {"status": "ok", "flags": flags}


@mcp.tool()
def check_troas_reminder() -> dict:
    """Check if the tROAS Proposals tab has undecided rows and post a reminder if so.

    Run on T/TH/S at 10am and 3pm. Posts a cheery nudge to the tROAS Chat space
    if any proposals still have Decision = '-' (not yet reviewed). Stays silent
    if the sheet is empty or all rows are decided.

    Returns: whether a reminder was posted.
    """
    import os
    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError("GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set.")

    if not has_pending_troas_decisions(spreadsheet_id):
        return {"status": "ok", "reminder_posted": False, "reason": "No pending decisions."}

    messages = [
        "Good morning! Your tROAS proposals are sitting in the sheet, full of potential, just waiting for your wisdom. Don't leave them hanging! Review now -> approve or skip each row -> call commit_troas_changes.",
        "Hey hey! tROAS proposals need attention! They've been waiting patiently (unlike me). Pop into the sheet, make your calls, and let's get those bids optimized!",
        "Friendly reminder that your tROAS proposals are STILL there! Lonely. Sad. Unapproved. You've got this -- two minutes and they'll be sorted. Sheet link in the last audit message!",
        "Just checking in! Those tROAS proposals aren't going to approve themselves (I wish). Quick peek, Approve or Skip, call commit_troas_changes -- done! Go team!",
        "Another nudge from your friendly neighborhood AI! tROAS proposals await. They believe in you. Do you believe in them? Review + commit whenever you're ready!",
    ]

    import random
    msg = random.choice(messages)

    try:
        post_to_troas_chat(msg)
        posted = True
    except Exception:
        posted = False

    return {"status": "ok", "reminder_posted": posted}


# ---------------------------------------------------------------------------
# Budget audit + commit tools (Phase 3)
# ---------------------------------------------------------------------------

@mcp.tool()
def run_budget_audit() -> dict:
    """Run the budget audit across all Google Ads accounts.

    Two proposal types are identified and written to the Budget Proposals tab:

      constrained (white rows) -- campaigns that hit >= 80% of daily budget on
        >= 2 of the last 7 days. Candidate for a budget increase.

      excess (light teal rows) -- campaigns where L7 average daily spend is
        < 40% of current budget and total L7 spend >= $1. Candidate for a
        budget decrease or reallocation.

    Constrained rows appear first, sorted by days at cap descending.
    Excess rows follow, sorted by utilization ascending (lowest first).
    Column F (New Budget) is left blank for user input on any row type.

    User reviews the sheet, enters new dollar values in column F, then calls
    commit_budget_changes to apply the changes via the API.

    Returns: constrained and excess proposal counts plus Budget Proposals tab URL.
    """
    import os
    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError("GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set.")

    client = get_client()
    result = build_budget_proposals(client)
    proposals = result["proposals"]
    constrained_count = result["constrained_proposals"]
    excess_count = result["excess_proposals"]

    # Write to Sheets
    tab_url = write_budget_proposals(proposals, spreadsheet_id)

    # Post summary card to tROAS Chat space
    from datetime import date
    date_str = date.today().strftime("%B %-d, %Y")
    accounts_count = len({p["customer_id"] for p in proposals})

    audit_card_data = BudgetAuditCardData(
        date_str=date_str,
        constrained_count=constrained_count,
        excess_count=excess_count,
        total_proposals=len(proposals),
        accounts_count=accounts_count,
        proposals_url=tab_url,
    )
    try:
        post_budget_audit_card(audit_card_data)
    except Exception as exc:
        return {
            "status": "ok",
            "constrained_proposals": constrained_count,
            "excess_proposals": excess_count,
            "total_proposals": len(proposals),
            "accounts_checked": result["accounts_checked"],
            "tab_url": tab_url,
            "chat_warning": str(exc),
        }

    return {
        "status": "ok",
        "constrained_proposals": constrained_count,
        "excess_proposals": excess_count,
        "total_proposals": len(proposals),
        "accounts_checked": result["accounts_checked"],
        "tab_url": tab_url,
    }


@mcp.tool()
def commit_budget_changes() -> dict:
    """Apply budget changes from the Budget Proposals tab.

    Reads rows in the Budget Proposals tab where column F (New Budget) has a
    non-empty value parseable as a float > $1. For each qualifying row:
      - Validates the new budget is > $1 and reasonably sized (> $0).
      - Calls CampaignBudgetService.mutate_campaign_budgets() to update amount_micros.
      - Logs the before/after values for audit.

    Posts a commit summary to the main Google Chat space.
    Returns: applied count, error count, and detail list.
    """
    import os
    from datetime import datetime, timezone

    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if not spreadsheet_id:
        raise EnvironmentError("GOOGLE_ADS_SHEETS_DASHBOARD_ID is not set.")

    client = get_client()
    decision_rows = read_budget_decisions(spreadsheet_id)

    if not decision_rows:
        return {
            "status": "ok",
            "applied": 0,
            "errors": 0,
            "detail": [],
            "message": "No rows with a New Budget value found in the Budget Proposals tab.",
        }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results_detail: list[dict] = []
    applied_log: list[dict] = []
    applied = 0
    errors = 0

    for row in decision_rows:
        new_budget = row["_new_budget_float"]
        customer_id = row.get("Customer ID", "").strip()
        campaign_id = row.get("Campaign ID", "").strip()
        campaign_name = row.get("Campaign Name", "").strip()
        account_name = row.get("Account Name", "").strip()
        budget_id = row.get("Budget ID", "").strip()

        try:
            old_budget = float(row.get("Current Budget ($)", 0) or 0)
        except (ValueError, TypeError):
            old_budget = 0.0

        # Validate minimum new budget ($1)
        if new_budget < 1.0:
            err_detail = {
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "budget_id": budget_id,
                "old_budget": old_budget,
                "new_budget": new_budget,
                "status": "error",
                "error": f"New budget ${new_budget:.2f} is below the $1 minimum.",
            }
            results_detail.append(err_detail)
            applied_log.append({
                "applied_date": today,
                "customer_id": customer_id,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "account_name": account_name,
                "old_budget": round(old_budget, 2),
                "new_budget": round(new_budget, 2),
                "change": round(new_budget - old_budget, 2),
                "direction": "UP" if new_budget > old_budget else "DOWN",
                "status": "error",
                "error": err_detail["error"],
            })
            errors += 1
            continue

        result = apply_budget_change(
            client=client,
            customer_id=customer_id,
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            budget_id=budget_id,
            old_budget=old_budget,
            new_budget=new_budget,
        )
        results_detail.append(result)
        applied_log.append({
            "applied_date": today,
            "customer_id": customer_id,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "account_name": account_name,
            "old_budget": round(old_budget, 2),
            "new_budget": round(new_budget, 2),
            "change": round(new_budget - old_budget, 2),
            "direction": "UP" if new_budget > old_budget else "DOWN",
            "status": result["status"],
            "error": result.get("error", ""),
        })

        if result["status"] == "applied":
            applied += 1
        else:
            errors += 1

    # Persist to Budget Log tab before posting to Chat
    if applied_log:
        try:
            append_budget_log(applied_log, spreadsheet_id)
        except Exception:
            pass

    # Build card data and post to tROAS Chat space
    from datetime import date
    date_str = date.today().strftime("%B %-d, %Y")
    log_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    commit_applied_items: list[BudgetCommitItem] = []
    commit_error_items: list[BudgetErrorItem] = []
    for r in results_detail:
        if r["status"] == "applied":
            direction = "UP" if r["new_budget"] > r["old_budget"] else "DOWN"
            commit_applied_items.append(BudgetCommitItem(
                campaign_name=r["campaign_name"],
                account_name=r.get("account_name", ""),
                old_budget=r["old_budget"],
                new_budget=r["new_budget"],
                change=round(r["new_budget"] - r["old_budget"], 2),
                direction=direction,
            ))
        elif r["status"] == "error":
            commit_error_items.append(BudgetErrorItem(
                campaign_name=r["campaign_name"],
                error=r.get("error", ""),
            ))

    card_data: BudgetCommitCardData = BudgetCommitCardData(
        date_str=date_str,
        applied=applied,
        errors=errors,
        applied_items=commit_applied_items,
        error_items=commit_error_items,
        log_url=log_url,
    )
    try:
        post_budget_commit_card(card_data)
    except Exception:
        pass

    return {
        "status": "ok",
        "applied": applied,
        "errors": errors,
        "detail": results_detail,
    }


@mcp.tool()
def commit_all_changes() -> dict:
    """Apply all pending changes from both the tROAS Proposals and Budget Proposals tabs.

    Equivalent to running commit_troas_changes and commit_budget_changes together.
    Use this when the user says "commit" without specifying which sheet.

    tROAS changes require Decision = 'Approve' in the tROAS Proposals tab.
    Budget changes require a non-empty value in the New Budget ($) column of
    the Budget Proposals tab.

    Returns: combined summary dict with keys 'troas' and 'budget', each
    containing the same structure as the individual commit tools return.
    """
    troas_result = commit_troas_changes()
    budget_result = commit_budget_changes()

    return {
        "status": "ok",
        "troas": troas_result,
        "budget": budget_result,
    }


# ---------------------------------------------------------------------------
# Brand analytics + image asset tools (Phase 4)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_google_ads_brand_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
) -> list[BrandRow]:
    """Return brand-level performance from Shopping and Performance Max campaigns.

    Aggregates spend, conversions, conversion_value, ROAS, impressions, and clicks
    by product brand (segments.product_brand) across all campaigns in the account.
    Sorted by conversion_value descending -- use this to rank brands for campaign creation.

    customer_id: 10-digit account ID (e.g. "1864748540" for ToolUp).
    date_range: preset like LAST_30_DAYS, LAST_7_DAYS, or explicit
                'start_date=YYYY-MM-DD,end_date=YYYY-MM-DD'.

    Returns: list of BrandRow dicts with brand, spend, conversions, conversion_value,
             roas, impressions, clicks. Brands with no data in the period are excluded.
    """
    return get_brand_performance(get_client(), customer_id, _parse_date_range(date_range))


@mcp.tool()
def list_google_ads_image_assets(
    customer_id: str,
) -> list[ImageAssetInfo]:
    """List all image assets already uploaded in a Google Ads account.

    Returns resource_name, name, file_size, width_pixels, height_pixels, and
    serving URL for each IMAGE type asset. Use the resource_name values when
    building PMax campaign configs (landscape_image_resource, square_image_resource,
    logo_image_resource fields in AssetGroupConfig / PMaxCampaignConfig).

    customer_id: 10-digit account ID.
    """
    return list_image_assets(get_client(), customer_id)


@mcp.tool()
def upload_google_ads_image_asset(
    customer_id: str,
    image_url: str,
    asset_name: str,
) -> dict:
    """Fetch an image from a public URL and upload it as a Google Ads image asset.

    The image is fetched, base64-encoded, and uploaded via AssetService.
    Returns the resource_name of the new asset -- use this in PMax campaign configs.

    customer_id: 10-digit account ID.
    image_url: publicly accessible URL. Must return a valid image (JPEG, PNG, etc.).
    asset_name: human-readable name for the asset (e.g. "Milwaukee Hero Landscape").

    Required dimensions:
      - Landscape (1.91:1): min 600x314 px, recommended 1200x628 px
      - Square (1:1): min 300x300 px, recommended 1200x1200 px
      - Logo (1:1): min 128x128 px, recommended 512x512 px

    Raises an error if the URL is unreachable or the image is rejected by Google Ads.
    """
    resource_name = upload_image_asset(get_client(), customer_id, image_url, asset_name)
    return {"resource_name": resource_name, "asset_name": asset_name, "status": "uploaded"}


@mcp.tool()
def propose_google_ads_pmax_campaign(
    customer_id: str,
    config: dict,
) -> PMaxProposal:
    """Validate a PMax campaign config and store it as a pending proposal.

    Validates all copy requirements (headline/description counts, char limits),
    confirms required fields are present, and writes a proposal file.
    Returns the proposal with a proposal_id for use in commit_google_ads_pmax_campaign.

    IMPORTANT: This tool does NOT make any changes to Google Ads.
    Review the returned proposal before calling commit_google_ads_pmax_campaign.

    config must be a dict matching PMaxCampaignConfig:
      campaign_name         -- string
      daily_budget_usd      -- float (e.g. 50.0)
      target_roas_pct       -- float (e.g. 400.0 for 400% ROAS)
      business_name         -- string, max 25 chars
      logo_image_resource   -- resource_name from upload_google_ads_image_asset or
                               list_google_ads_image_assets (1:1 logo)
      geo_target_ids        -- list of strings, e.g. ["2840"] for USA
      language_ids          -- list of strings, e.g. ["1000"] for English
      asset_groups          -- list of AssetGroupConfig dicts (one per brand):
        name                -- string
        brand_name          -- string (brand to subdivide by) or null (all products)
        final_url           -- string
        headlines           -- list of 3-15 strings, max 30 chars each
        long_headlines      -- list of 1-5 strings, max 90 chars each
        descriptions        -- list of 2-5 strings, max 90 chars; 1 must be <=60 chars
        landscape_image_resource  -- resource_name of a 1.91:1 image
        square_image_resource     -- resource_name of a 1:1 image
        search_themes        -- list of up to 25 search theme strings

    customer_id: 10-digit account ID.
    """
    return propose_pmax_campaign(get_client(), customer_id, config)  # type: ignore[arg-type]


@mcp.tool()
def get_google_ads_pmax_proposal(proposal_id: str) -> PMaxProposal:
    """Read and return a pending PMax campaign proposal by ID.

    Use this to review the full proposal (config, copy, asset references) before
    calling commit_google_ads_pmax_campaign to execute it.

    proposal_id: the short ID returned by propose_google_ads_pmax_campaign.
    """
    return get_pmax_proposal(proposal_id)


@mcp.tool()
def commit_google_ads_pmax_campaign(proposal_id: str) -> PMaxCreationResult:
    """Execute a pending PMax campaign proposal via a single atomic Google Ads API call.

    ALL campaigns and asset groups are created in PAUSED status.
    No live serving occurs until the campaign is manually enabled in Google Ads.

    Reads the proposal stored by propose_google_ads_pmax_campaign, builds the full
    mutate operation list (budget, campaign, criteria, brand guidelines assets,
    asset groups, copy assets, image links, search themes, listing group filters),
    and fires it as one atomic request. Either the entire campaign is created or
    nothing is -- no partial states.

    Writes a creation record to the audit log (audit.db) on success.
    Deletes the proposal file after a successful commit.

    proposal_id: the short ID returned by propose_google_ads_pmax_campaign.

    Returns: campaign_resource_name, asset_group_resource_names, status="created_paused".
    """
    return commit_pmax_campaign(get_client(), proposal_id)


# ---------------------------------------------------------------------------
# DataFeedWatch lookup table tools
# ---------------------------------------------------------------------------

def _dfw_sheet_id() -> str:
    import os
    sid = os.environ.get("DFW_LOOKUP_SHEET_ID", "").strip()
    if not sid:
        raise EnvironmentError(
            "DFW_LOOKUP_SHEET_ID is not set. Create a Google Sheet, share it as Editor "
            "with mcp-server@adam-mcp-496818.iam.gserviceaccount.com, add its ID to .env "
            "as DFW_LOOKUP_SHEET_ID, then connect that sheet in DataFeedWatch as a lookup source."
        )
    return sid


@mcp.tool()
def update_dfw_lookup_table(rows: list[dict], tab: str = "Sheet1", clear: bool = True) -> dict:
    """Overwrite a DataFeedWatch lookup-table tab in the configured Google Sheet.

    DataFeedWatch reads this sheet as a lookup table: it matches a feed field
    (e.g. `sku`) against a column here and pulls another column (e.g. custom_label_0).
    Apply feed attribute changes here, NOT in the Shopify Google app or a Merchant
    Center supplemental feed, or DFW will overwrite them.

    rows: list of flat dicts that all share the same keys. The keys become the
          header row in column order, e.g.
          [{"sku": "835470", "custom_label_0": "pws_stage1_3m"}, ...].
    tab: the sheet tab to write (created if missing). Use one tab per lookup.
    clear: overwrite the whole tab (default). Set False to leave other cells intact.

    Requires DFW_LOOKUP_SHEET_ID in .env. Returns the tab URL and row count.
    """
    url = write_dfw_lookup_table(rows, _dfw_sheet_id(), tab=tab, clear=clear)
    return {"tab": tab, "rows_written": len(rows), "sheet_url": url}


@mcp.tool()
def get_dfw_lookup_table(tab: str = "Sheet1") -> list[dict]:
    """Read back a DataFeedWatch lookup-table tab as a list of header-keyed dicts.

    tab: the sheet tab to read. Returns an empty list if the tab is missing or empty.
    Requires DFW_LOOKUP_SHEET_ID in .env.
    """
    return read_dfw_lookup_table(_dfw_sheet_id(), tab=tab)


# ---------------------------------------------------------------------------
# Standard Shopping campaign creation tools (propose / get / commit)
# ---------------------------------------------------------------------------

@mcp.tool()
def propose_google_ads_standard_shopping_campaign(
    customer_id: str,
    config: dict,
) -> ShoppingProposal:
    """Validate a Standard Shopping campaign config and store it as a pending proposal.

    IMPORTANT: This tool does NOT make any changes to Google Ads. Review the returned
    proposal, then call commit_google_ads_standard_shopping_campaign to execute it.

    Standard Shopping gated to a curated roster via a feed custom_label. Campaign and
    ad group are created PAUSED. Cold accounts cannot use conversion-based Shopping
    bidding (the API blocks it), so Stage 1 uses manual_cpc; switch to value/tROAS in
    Stage 2 once conversions accumulate.

    config must be a dict matching StandardShoppingConfig:
      campaign_name        -- string (required)
      daily_budget_usd     -- float, >= 1.0 (required)
      merchant_id          -- int, Merchant Center account ID (required)
      custom_label_value   -- string gating the roster, e.g. "pws_stage1_3m" (required)
      custom_label_index   -- int 0-4, default 0 (which custom_label_N to gate on)
      bidding_strategy     -- "manual_cpc" (default) | "maximize_clicks" |
                              "maximize_conversion_value" | "target_roas"
      max_cpc_usd          -- float, default 0.55 (manual_cpc unit bid, or maximize_clicks ceiling)
      target_roas_pct      -- float, required only for target_roas
      feed_label           -- string, default "US"
      campaign_priority    -- int 0/1/2, default 0 (Low)
      geo_target_ids       -- list of strings, default ["2840"] (USA). No language criterion (Shopping uses feed language).
      ad_group_name        -- string, default "<campaign_name> Ad Group"
      enable_search_partners -- bool, default True
      pause_campaign_ids   -- list of campaign IDs to pause in the same commit
                              (e.g. a starved PMax), default []

    customer_id: 10-digit account ID.
    """
    return propose_standard_shopping_campaign(get_client(), customer_id, config)  # type: ignore[arg-type]


@mcp.tool()
def get_google_ads_standard_shopping_proposal(proposal_id: str) -> ShoppingProposal:
    """Read and return a pending Standard Shopping proposal by ID for review.

    proposal_id: the short ID returned by propose_google_ads_standard_shopping_campaign.
    """
    return get_shopping_proposal(proposal_id)


@mcp.tool()
def commit_google_ads_standard_shopping_campaign(proposal_id: str) -> ShoppingCreationResult:
    """Execute a pending Standard Shopping proposal via one atomic Google Ads API call.

    The campaign and ad group are created in PAUSED status. No live serving occurs
    until the campaign is manually enabled in Google Ads. Builds budget, campaign
    (SHOPPING, Maximize Conversions, shopping settings, networks), geo/language
    criteria, ad group, product ad, and the listing-group tree gating to the
    custom_label. If config.pause_campaign_ids is set, those campaigns are paused in
    the same atomic request. Either everything applies or nothing does.

    Writes a creation record to the audit log (audit.db). Marks the proposal committed.

    proposal_id: the short ID returned by propose_google_ads_standard_shopping_campaign.

    Returns: campaign_resource_name, ad_group_resource_name, paused_campaign_ids,
    status="created_paused".
    """
    return commit_standard_shopping_campaign(get_client(), proposal_id)


# ---------------------------------------------------------------------------
# Standard Search campaign creation tools (propose / get / commit)
# ---------------------------------------------------------------------------

@mcp.tool()
def propose_google_ads_search_campaign(
    customer_id: str,
    config: dict,
) -> SearchProposal:
    """Validate a Standard Search campaign config and store it as a pending proposal.

    IMPORTANT: This tool does NOT make any changes to Google Ads. Review the returned
    proposal, then call commit_google_ads_search_campaign to execute it.

    Builds a Search campaign with one or more ad groups, each with its own keywords
    and a Responsive Search Ad. Campaign, ad groups, and ads are all created PAUSED.
    Cold accounts start on manual_cpc (or maximize_clicks); switch to Smart Bidding in
    Stage 2 once conversions accumulate. Validate with validate_only before committing.

    config must be a dict matching SearchCampaignConfig:
      campaign_name          -- string (required)
      daily_budget_usd       -- float, >= 1.0 (required)
      ad_groups              -- list of ad group dicts (required, >= 1), each:
          name         -- string (required)
          final_url    -- landing page URL, http(s) (required)
          keywords     -- list of strings (default PHRASE) OR {text, match_type}
                          dicts; match_type EXACT/PHRASE/BROAD (required, >= 1)
          headlines    -- list of 3-15 strings, <= 30 chars each (required)
          descriptions -- list of 2-4 strings, <= 90 chars each (required)
          path1, path2 -- optional display-path segments, <= 15 chars each
          cpc_bid_usd  -- optional ad-group max CPC; defaults to default_cpc_usd
      bidding_strategy       -- "manual_cpc" (default) | "maximize_clicks"
      default_cpc_usd        -- float, default 0.40 (manual_cpc bid / max_clicks ceiling)
      geo_target_ids         -- list of strings, default ["2840"] (USA)
      language_ids           -- list of strings, default ["1000"] (English)
      enable_search_partners -- bool, default False
      negative_keywords      -- list of strings added as campaign-level BROAD negatives

    customer_id: 10-digit account ID.
    """
    return propose_search_campaign(get_client(), customer_id, config)  # type: ignore[arg-type]


@mcp.tool()
def get_google_ads_search_proposal(proposal_id: str) -> SearchProposal:
    """Read and return a pending Search proposal by ID for review.

    proposal_id: the short ID returned by propose_google_ads_search_campaign.
    """
    return get_search_proposal(proposal_id)


@mcp.tool()
def commit_google_ads_search_campaign(proposal_id: str) -> SearchCreationResult:
    """Execute a pending Search proposal via one atomic Google Ads API call.

    The campaign, ad groups, and ads are created in PAUSED status. No live serving
    occurs until manually enabled. Builds budget, campaign (SEARCH, networks), geo and
    language criteria, campaign-level negative keywords, and each ad group with its
    keyword criteria and a Responsive Search Ad. Either everything applies or nothing does.

    Writes a creation record to the audit log (audit.db). Marks the proposal committed.

    proposal_id: the short ID returned by propose_google_ads_search_campaign.

    Returns: campaign_resource_name, ad_group_resource_names, keyword_count, ad_count,
    status="created_paused".
    """
    return commit_search_campaign(get_client(), proposal_id)


if __name__ == "__main__":
    mcp.run()
