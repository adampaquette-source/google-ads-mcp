"""Performance reporting functions: account summary, campaigns, ad groups, search terms, keywords, products."""

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.queries import (
    ACCOUNT_SUMMARY,
    AD_GROUP_PERFORMANCE,
    BRAND_PERFORMANCE,
    CAMPAIGN_PERFORMANCE,
    KEYWORD_PERFORMANCE,
    LIST_IMAGE_ASSETS,
    PRODUCT_PERFORMANCE,
    SEARCH_TERMS,
)
from ads_mcp.reporting.utils import date_range_clause, micros_to_currency


def _stream(client: GoogleAdsClient, customer_id: str, query: str):
    """Run a search_stream query and yield each row."""
    ga_service = client.get_service("GoogleAdsService")
    request = client.get_type("SearchGoogleAdsStreamRequest")
    request.customer_id = customer_id
    request.query = query
    for batch in ga_service.search_stream(request=request):
        yield from batch.results


def _roas(conversions_value: float, cost: float) -> float:
    return round(conversions_value / cost, 4) if cost > 0 else 0.0


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class AccountSummary(TypedDict):
    customer_id: str
    name: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    conversions_value: float
    ctr: float
    avg_cpc: float
    roas: float


class CampaignRow(TypedDict):
    campaign_id: str
    name: str
    status: str
    channel_type: str
    bidding_strategy: str
    target_roas: Optional[float]
    target_cpa: Optional[float]
    daily_budget: float
    impressions: int
    clicks: int
    cost: float
    conversions: float
    conversions_value: float
    roas: float
    ctr: float
    avg_cpc: float
    search_impression_share: Optional[float]


class AdGroupRow(TypedDict):
    ad_group_id: str
    name: str
    status: str
    campaign_id: str
    campaign_name: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    conversions_value: float
    ctr: float
    avg_cpc: float


class SearchTermRow(TypedDict):
    search_term: str
    status: str
    campaign_id: str
    campaign_name: str
    ad_group_id: str
    ad_group_name: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    conversions_value: float
    ctr: float


class KeywordRow(TypedDict):
    keyword_text: str
    match_type: str
    status: str
    quality_score: Optional[int]
    ad_group_id: str
    ad_group_name: str
    campaign_id: str
    campaign_name: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    avg_cpc: float


class ProductRow(TypedDict):
    product_id: str
    title: str
    product_type: str
    campaign_id: str
    campaign_name: str
    channel_type: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    conversions_value: float
    roas: float


class BrandRow(TypedDict):
    brand: str
    spend: float
    conversions: float
    conversion_value: float
    roas: float
    impressions: int
    clicks: int


class ImageAssetInfo(TypedDict):
    resource_name: str
    name: str
    file_size: int
    width_pixels: int
    height_pixels: int
    url: str


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def get_account_summary(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
) -> AccountSummary:
    """Return aggregate metrics for a single account over the given date range."""
    dc = date_range_clause(date_range)
    query = ACCOUNT_SUMMARY.format(date_clause=dc)

    impressions = clicks = cost_micros = 0
    conversions = conversions_value = ctr = avg_cpc_micros = 0.0
    name = customer_id

    for row in _stream(client, customer_id, query):
        m = row.metrics
        c = row.customer
        name = c.descriptive_name
        impressions += m.impressions
        clicks += m.clicks
        cost_micros += m.cost_micros
        conversions += m.conversions
        conversions_value += m.conversions_value
        ctr = m.ctr
        avg_cpc_micros = m.average_cpc

    cost = micros_to_currency(cost_micros)
    return AccountSummary(
        customer_id=customer_id,
        name=name,
        impressions=impressions,
        clicks=clicks,
        cost=round(cost, 2),
        conversions=round(conversions, 2),
        conversions_value=round(conversions_value, 2),
        ctr=round(ctr, 4),
        avg_cpc=round(micros_to_currency(int(avg_cpc_micros)), 4),
        roas=_roas(conversions_value, cost),
    )


def get_campaign_performance(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
    filters: Optional[dict] = None,
) -> list[CampaignRow]:
    """Return per-campaign performance metrics.

    Optional filters dict: keys are GAQL field names, values are enum strings.
    Example: {"campaign.status": "ENABLED"}
    """
    dc = date_range_clause(date_range)
    extra = ""
    if filters:
        clauses = [f"AND {k} = {v}" for k, v in filters.items()]
        extra = "\n      ".join(clauses)
    query = CAMPAIGN_PERFORMANCE.format(date_clause=dc, extra_where=extra)

    results: list[CampaignRow] = []
    for row in _stream(client, customer_id, query):
        m = row.metrics
        camp = row.campaign
        budget = row.campaign_budget
        cost = micros_to_currency(m.cost_micros)

        # PMax campaigns store tROAS in maximize_conversion_value.target_roas;
        # all other TARGET_ROAS campaigns use campaign.target_roas.target_roas.
        target_roas = None
        pmax_troas = camp.maximize_conversion_value.target_roas
        standard_troas = camp.target_roas.target_roas
        raw_troas = pmax_troas if pmax_troas > 0 else standard_troas
        if raw_troas:
            target_roas = round(raw_troas, 4)

        target_cpa = None
        if camp.target_cpa.target_cpa_micros:
            target_cpa = round(micros_to_currency(camp.target_cpa.target_cpa_micros), 2)

        sis = m.search_impression_share if m.search_impression_share else None

        results.append(CampaignRow(
            campaign_id=str(camp.id),
            name=camp.name,
            status=client.enums.CampaignStatusEnum.CampaignStatus.Name(camp.status),
            channel_type=client.enums.AdvertisingChannelTypeEnum.AdvertisingChannelType.Name(camp.advertising_channel_type),
            bidding_strategy=client.enums.BiddingStrategyTypeEnum.BiddingStrategyType.Name(camp.bidding_strategy_type),
            target_roas=target_roas,
            target_cpa=target_cpa,
            daily_budget=round(micros_to_currency(budget.amount_micros), 2),
            impressions=m.impressions,
            clicks=m.clicks,
            cost=round(cost, 2),
            conversions=round(m.conversions, 2),
            conversions_value=round(m.conversions_value, 2),
            roas=_roas(m.conversions_value, cost),
            ctr=round(m.ctr, 4),
            avg_cpc=round(micros_to_currency(m.average_cpc), 4),
            search_impression_share=round(sis, 4) if sis else None,
        ))

    results.sort(key=lambda r: r["cost"], reverse=True)
    return results


def get_ad_group_performance(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
    campaign_id: Optional[str] = None,
) -> list[AdGroupRow]:
    """Return per-ad-group performance. Optionally filter to a single campaign."""
    dc = date_range_clause(date_range)
    extra = ""
    if campaign_id:
        extra = f"AND campaign.id = {campaign_id}"
    query = AD_GROUP_PERFORMANCE.format(date_clause=dc, extra_where=extra)

    results: list[AdGroupRow] = []
    for row in _stream(client, customer_id, query):
        m = row.metrics
        ag = row.ad_group
        camp = row.campaign
        cost = micros_to_currency(m.cost_micros)
        results.append(AdGroupRow(
            ad_group_id=str(ag.id),
            name=ag.name,
            status=client.enums.AdGroupStatusEnum.AdGroupStatus.Name(ag.status),
            campaign_id=str(camp.id),
            campaign_name=camp.name,
            impressions=m.impressions,
            clicks=m.clicks,
            cost=round(cost, 2),
            conversions=round(m.conversions, 2),
            conversions_value=round(m.conversions_value, 2),
            ctr=round(m.ctr, 4),
            avg_cpc=round(micros_to_currency(m.average_cpc), 4),
        ))

    results.sort(key=lambda r: r["cost"], reverse=True)
    return results


def get_search_terms(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
    campaign_id: Optional[str] = None,
) -> list[SearchTermRow]:
    """Return search terms that triggered ads. Optionally filter to one campaign."""
    dc = date_range_clause(date_range)
    extra = ""
    if campaign_id:
        extra = f"AND campaign.id = {campaign_id}"
    query = SEARCH_TERMS.format(date_clause=dc, extra_where=extra)

    results: list[SearchTermRow] = []
    for row in _stream(client, customer_id, query):
        m = row.metrics
        stv = row.search_term_view
        camp = row.campaign
        ag = row.ad_group
        cost = micros_to_currency(m.cost_micros)
        results.append(SearchTermRow(
            search_term=stv.search_term,
            status=client.enums.SearchTermTargetingStatusEnum.SearchTermTargetingStatus.Name(stv.status),
            campaign_id=str(camp.id),
            campaign_name=camp.name,
            ad_group_id=str(ag.id),
            ad_group_name=ag.name,
            impressions=m.impressions,
            clicks=m.clicks,
            cost=round(cost, 2),
            conversions=round(m.conversions, 2),
            conversions_value=round(m.conversions_value, 2),
            ctr=round(m.ctr, 4),
        ))

    results.sort(key=lambda r: r["cost"], reverse=True)
    return results


def get_keyword_performance(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
) -> list[KeywordRow]:
    """Return keyword-level performance metrics."""
    dc = date_range_clause(date_range)
    query = KEYWORD_PERFORMANCE.format(date_clause=dc)

    results: list[KeywordRow] = []
    for row in _stream(client, customer_id, query):
        m = row.metrics
        crit = row.ad_group_criterion
        ag = row.ad_group
        camp = row.campaign

        qs = crit.quality_info.quality_score
        quality_score = int(qs) if qs else None

        cost = micros_to_currency(m.cost_micros)
        results.append(KeywordRow(
            keyword_text=crit.keyword.text,
            match_type=client.enums.KeywordMatchTypeEnum.KeywordMatchType.Name(crit.keyword.match_type),
            status=client.enums.AdGroupCriterionStatusEnum.AdGroupCriterionStatus.Name(crit.status),
            quality_score=quality_score,
            ad_group_id=str(ag.id),
            ad_group_name=ag.name,
            campaign_id=str(camp.id),
            campaign_name=camp.name,
            impressions=m.impressions,
            clicks=m.clicks,
            cost=round(cost, 2),
            conversions=round(m.conversions, 2),
            avg_cpc=round(micros_to_currency(m.average_cpc), 4),
        ))

    results.sort(key=lambda r: r["cost"], reverse=True)
    return results


def get_product_performance(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
) -> list[ProductRow]:
    """Return product-level performance from Shopping and Performance Max campaigns."""
    dc = date_range_clause(date_range)
    query = PRODUCT_PERFORMANCE.format(date_clause=dc)

    results: list[ProductRow] = []
    for row in _stream(client, customer_id, query):
        m = row.metrics
        segs = row.segments
        camp = row.campaign
        cost = micros_to_currency(m.cost_micros)
        results.append(ProductRow(
            product_id=segs.product_item_id,
            title=segs.product_title,
            product_type=segs.product_type_l1,
            campaign_id=str(camp.id),
            campaign_name=camp.name,
            channel_type=client.enums.AdvertisingChannelTypeEnum.AdvertisingChannelType.Name(camp.advertising_channel_type),
            impressions=m.impressions,
            clicks=m.clicks,
            cost=round(cost, 2),
            conversions=round(m.conversions, 2),
            conversions_value=round(m.conversions_value, 2),
            roas=_roas(m.conversions_value, cost),
        ))

    results.sort(key=lambda r: r["conversions_value"], reverse=True)
    return results


def get_brand_performance(
    client: GoogleAdsClient,
    customer_id: str,
    date_range: str | dict = "LAST_30_DAYS",
) -> list[BrandRow]:
    """Return brand-level performance aggregated from Shopping and PMax campaigns.

    Queries shopping_performance_view grouped by segments.product_brand.
    Sorts by conversion_value descending. Brands with no spend are excluded.
    """
    dc = date_range_clause(date_range)
    query = BRAND_PERFORMANCE.format(date_clause=dc)

    totals: dict[str, dict] = {}
    for row in _stream(client, customer_id, query):
        m = row.metrics
        brand = row.segments.product_brand
        if not brand:
            continue
        if brand not in totals:
            totals[brand] = {
                "cost_micros": 0,
                "conversions": 0.0,
                "conversions_value": 0.0,
                "impressions": 0,
                "clicks": 0,
            }
        t = totals[brand]
        t["cost_micros"] += m.cost_micros
        t["conversions"] += m.conversions
        t["conversions_value"] += m.conversions_value
        t["impressions"] += m.impressions
        t["clicks"] += m.clicks

    results: list[BrandRow] = []
    for brand, t in totals.items():
        spend = micros_to_currency(t["cost_micros"])
        results.append(BrandRow(
            brand=brand,
            spend=round(spend, 2),
            conversions=round(t["conversions"], 2),
            conversion_value=round(t["conversions_value"], 2),
            roas=_roas(t["conversions_value"], spend),
            impressions=t["impressions"],
            clicks=t["clicks"],
        ))

    results.sort(key=lambda r: r["conversion_value"], reverse=True)
    return results


def list_image_assets(
    client: GoogleAdsClient,
    customer_id: str,
) -> list[ImageAssetInfo]:
    """Return all IMAGE type assets in the account with metadata."""
    results: list[ImageAssetInfo] = []
    for row in _stream(client, customer_id, LIST_IMAGE_ASSETS):
        asset = row.asset
        img = asset.image_asset
        results.append(ImageAssetInfo(
            resource_name=asset.resource_name,
            name=asset.name,
            file_size=img.file_size,
            width_pixels=img.full_size.width_pixels,
            height_pixels=img.full_size.height_pixels,
            url=img.full_size.url,
        ))
    results.sort(key=lambda r: r["name"])
    return results
