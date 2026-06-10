"""Health check functions: tROAS pacing, budget pacing, anomaly detection, disapprovals."""

from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from typing import Optional
from typing_extensions import TypedDict

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.queries import (
    ANOMALY_DAILY,
    BUDGET_PACING,
    DISAPPROVALS_ADS,
    DISAPPROVALS_KEYWORDS,
    DISAPPROVALS_STATUS_ACTIVE,
    DISAPPROVALS_STATUS_ALL,
    TROAS_PACING,
)
from ads_mcp.reporting.utils import date_range_clause, micros_to_currency

_VALID_ANOMALY_METRICS = {
    "impressions": "metrics.impressions",
    "clicks": "metrics.clicks",
    "cost": "metrics.cost_micros",
    "conversions": "metrics.conversions",
    "conversions_value": "metrics.conversions_value",
}


def _stream(client: GoogleAdsClient, customer_id: str, query: str):
    ga_service = client.get_service("GoogleAdsService")
    request = client.get_type("SearchGoogleAdsStreamRequest")
    request.customer_id = customer_id
    request.query = query
    for batch in ga_service.search_stream(request=request):
        yield from batch.results


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class TroasPacingResult(TypedDict):
    campaign_id: str
    name: str
    target_roas: float
    actual_roas: float
    drift_pct: float
    status: str  # ON_TRACK | OVER | UNDER


class BudgetPacingResult(TypedDict):
    campaign_id: str
    name: str
    daily_budget: float
    spend_today: float
    expected_spend: float
    pacing_ratio: float
    status: str  # ON_TRACK | OVERPACING | UNDERPACING


class AnomalyDay(TypedDict):
    date: str
    value: float
    deviation_sigmas: float


class AnomalyResult(TypedDict):
    metric: str
    mean: float
    std_dev: float
    anomalies: list[AnomalyDay]
    latest_date: str
    latest_value: float
    latest_deviation_sigmas: float


class DisapprovedAd(TypedDict):
    resource_name: str
    campaign_id: str
    campaign_name: str
    campaign_status: str
    ad_group_id: str
    ad_group_name: str
    ad_group_status: str
    policy_topics: list[str]


class DisapprovedKeyword(TypedDict):
    resource_name: str
    keyword_text: str
    match_type: str
    campaign_id: str
    campaign_name: str
    campaign_status: str
    ad_group_id: str
    ad_group_name: str
    ad_group_status: str
    policy_topics: list[str]


class DisapprovalsResult(TypedDict):
    ads: list[DisapprovedAd]
    keywords: list[DisapprovedKeyword]
    total_count: int


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def check_troas_pacing(
    client: GoogleAdsClient,
    customer_id: str,
    drift_pct: float = 10.0,
) -> list[TroasPacingResult]:
    """Check actual vs target ROAS for TARGET_ROAS and PMax campaigns.

    Uses LAST_7_DAYS for stability (avoids single-day noise).
    Returns only campaigns where abs(drift) >= drift_pct threshold.
    PMax campaigns use campaign.maximize_conversion_value.target_roas;
    all other TARGET_ROAS campaigns use campaign.target_roas.target_roas.
    """
    dc = date_range_clause("LAST_7_DAYS")
    query = TROAS_PACING.format(date_clause=dc)

    results: list[TroasPacingResult] = []
    for row in _stream(client, customer_id, query):
        m = row.metrics
        camp = row.campaign

        pmax_troas = camp.maximize_conversion_value.target_roas
        standard_troas = camp.target_roas.target_roas
        target_roas = pmax_troas if pmax_troas > 0 else standard_troas
        if not target_roas:
            continue

        cost = micros_to_currency(m.cost_micros)
        actual_roas = round(m.conversions_value / cost, 4) if cost > 0 else 0.0
        drift = round((actual_roas - target_roas) / target_roas * 100, 2) if target_roas else 0.0

        if abs(drift) < drift_pct:
            status = "ON_TRACK"
        elif drift > 0:
            status = "OVER"
        else:
            status = "UNDER"

        results.append(TroasPacingResult(
            campaign_id=str(camp.id),
            name=camp.name,
            target_roas=round(target_roas, 4),
            actual_roas=actual_roas,
            drift_pct=drift,
            status=status,
        ))

    results.sort(key=lambda r: abs(r["drift_pct"]), reverse=True)
    return results


def check_budget_pacing(
    client: GoogleAdsClient,
    customer_id: str,
) -> list[BudgetPacingResult]:
    """Check today's spend vs expected pace for each campaign.

    Expected spend = daily_budget * (current_hour / 24).
    Thresholds: ratio > 1.2 = OVERPACING, < 0.5 = UNDERPACING.
    """
    query = BUDGET_PACING

    now_utc = datetime.now(timezone.utc)
    hour_fraction = (now_utc.hour + now_utc.minute / 60) / 24

    results: list[BudgetPacingResult] = []
    for row in _stream(client, customer_id, query):
        m = row.metrics
        camp = row.campaign
        budget = row.campaign_budget

        daily_budget = micros_to_currency(budget.amount_micros)
        spend_today = micros_to_currency(m.cost_micros)
        expected_spend = round(daily_budget * hour_fraction, 2)

        if expected_spend > 0:
            ratio = round(spend_today / expected_spend, 3)
        else:
            ratio = 0.0

        if ratio > 1.2:
            status = "OVERPACING"
        elif ratio < 0.5:
            status = "UNDERPACING"
        else:
            status = "ON_TRACK"

        results.append(BudgetPacingResult(
            campaign_id=str(camp.id),
            name=camp.name,
            daily_budget=round(daily_budget, 2),
            spend_today=round(spend_today, 2),
            expected_spend=expected_spend,
            pacing_ratio=ratio,
            status=status,
        ))

    results.sort(key=lambda r: abs(r["pacing_ratio"] - 1.0), reverse=True)
    return results


def find_anomalies(
    client: GoogleAdsClient,
    customer_id: str,
    metric: str,
    sensitivity: float = 2.0,
) -> AnomalyResult:
    """Detect statistical anomalies in a daily metric over the last 30 days.

    metric: one of "impressions", "clicks", "cost", "conversions", "conversions_value"
    sensitivity: number of standard deviations required to flag an anomaly

    Returns mean, std_dev, flagged anomaly days, and the most recent day's deviation.
    """
    if metric not in _VALID_ANOMALY_METRICS:
        raise ValueError(
            f"Invalid metric {metric!r}. Valid options: {sorted(_VALID_ANOMALY_METRICS)}"
        )

    metric_field = _VALID_ANOMALY_METRICS[metric]
    query = ANOMALY_DAILY.format(metric_field=metric_field)

    daily: dict[str, float] = {}
    for row in _stream(client, customer_id, query):
        date_str = row.segments.date
        m = row.metrics

        if metric == "impressions":
            val = float(m.impressions)
        elif metric == "clicks":
            val = float(m.clicks)
        elif metric == "cost":
            val = micros_to_currency(m.cost_micros)
        elif metric == "conversions":
            val = m.conversions
        else:
            val = m.conversions_value

        daily[date_str] = daily.get(date_str, 0.0) + val

    if not daily:
        return AnomalyResult(
            metric=metric, mean=0.0, std_dev=0.0, anomalies=[],
            latest_date="", latest_value=0.0, latest_deviation_sigmas=0.0,
        )

    values = list(daily.values())
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

    anomalies: list[AnomalyDay] = []
    for date_str, val in sorted(daily.items()):
        sigmas = round((val - mean) / std_dev, 2) if std_dev > 0 else 0.0
        if abs(sigmas) >= sensitivity:
            anomalies.append(AnomalyDay(date=date_str, value=round(val, 4), deviation_sigmas=sigmas))

    latest_date = max(daily.keys())
    latest_value = daily[latest_date]
    latest_sigmas = round((latest_value - mean) / std_dev, 2) if std_dev > 0 else 0.0

    return AnomalyResult(
        metric=metric,
        mean=round(mean, 4),
        std_dev=round(std_dev, 4),
        anomalies=anomalies,
        latest_date=latest_date,
        latest_value=round(latest_value, 4),
        latest_deviation_sigmas=latest_sigmas,
    )


def find_disapprovals(
    client: GoogleAdsClient,
    customer_id: str,
) -> DisapprovalsResult:
    """Return all disapproved ads and keywords with their policy topics."""
    disapproved_ads: list[DisapprovedAd] = []
    for row in _stream(client, customer_id, DISAPPROVALS_ADS):
        aga = row.ad_group_ad
        topics = [
            entry.topic
            for entry in aga.policy_summary.policy_topic_entries
        ]
        disapproved_ads.append(DisapprovedAd(
            resource_name=aga.resource_name,
            campaign_id=str(row.campaign.id),
            campaign_name=row.campaign.name,
            ad_group_id=str(row.ad_group.id),
            ad_group_name=row.ad_group.name,
            policy_topics=topics,
        ))

    disapproved_keywords: list[DisapprovedKeyword] = []
    for row in _stream(client, customer_id, DISAPPROVALS_KEYWORDS):
        crit = row.ad_group_criterion
        topics = list(crit.disapproval_reasons)
        disapproved_keywords.append(DisapprovedKeyword(
            resource_name=crit.resource_name,
            keyword_text=crit.keyword.text,
            match_type=client.enums.KeywordMatchTypeEnum.KeywordMatchType.Name(crit.keyword.match_type),
            campaign_id=str(row.campaign.id),
            campaign_name=row.campaign.name,
            ad_group_id=str(row.ad_group.id),
            ad_group_name=row.ad_group.name,
            policy_topics=topics,
        ))

    return DisapprovalsResult(
        ads=disapproved_ads,
        keywords=disapproved_keywords,
        total_count=len(disapproved_ads) + len(disapproved_keywords),
    )
