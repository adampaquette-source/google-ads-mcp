"""GAQL query constants. All queries live here -- never inline in calling code."""

# ---------------------------------------------------------------------------
# Account listing
# ---------------------------------------------------------------------------

# Run against the MCC customer ID. level > 0 excludes the MCC itself.
LIST_ACCOUNTS = """
    SELECT
        customer_client.id,
        customer_client.descriptive_name,
        customer_client.currency_code,
        customer_client.time_zone,
        customer_client.status,
        customer_client.manager,
        customer_client.level
    FROM customer_client
    WHERE customer_client.level > 0
"""

# ---------------------------------------------------------------------------
# Performance reporting
# ---------------------------------------------------------------------------

# Caller appends: "AND {date_range_clause}"
ACCOUNT_SUMMARY = """
    SELECT
        customer.id,
        customer.descriptive_name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.ctr,
        metrics.average_cpc
    FROM customer
    WHERE {date_clause}
"""

# Caller appends extra WHERE conditions for filters (e.g. campaign.status = ENABLED)
CAMPAIGN_PERFORMANCE = """
    SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.advertising_channel_type,
        campaign.bidding_strategy_type,
        campaign.target_roas.target_roas,
        campaign.maximize_conversion_value.target_roas,
        campaign.target_cpa.target_cpa_micros,
        campaign_budget.amount_micros,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.ctr,
        metrics.average_cpc,
        metrics.search_impression_share
    FROM campaign
    WHERE {date_clause}
      AND campaign.status != REMOVED
    {extra_where}
"""

# Caller may append: "AND ad_group.campaign = '{campaign_resource_name}'"
AD_GROUP_PERFORMANCE = """
    SELECT
        ad_group.id,
        ad_group.name,
        ad_group.status,
        campaign.id,
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.ctr,
        metrics.average_cpc
    FROM ad_group
    WHERE {date_clause}
      AND ad_group.status != REMOVED
    {extra_where}
"""

# Caller may append campaign filter
SEARCH_TERMS = """
    SELECT
        search_term_view.search_term,
        search_term_view.status,
        campaign.id,
        campaign.name,
        ad_group.id,
        ad_group.name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.ctr
    FROM search_term_view
    WHERE {date_clause}
      AND campaign.status != REMOVED
    {extra_where}
"""

KEYWORD_PERFORMANCE = """
    SELECT
        ad_group_criterion.keyword.text,
        ad_group_criterion.keyword.match_type,
        ad_group_criterion.status,
        ad_group_criterion.quality_info.quality_score,
        ad_group_criterion.cpc_bid_micros,
        ad_group.id,
        ad_group.name,
        campaign.id,
        campaign.name,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.average_cpc
    FROM keyword_view
    WHERE {date_clause}
      AND ad_group_criterion.status != REMOVED
      AND campaign.status != REMOVED
"""

# Shopping and PMax product performance via shopping_performance_view
PRODUCT_PERFORMANCE = """
    SELECT
        segments.product_item_id,
        segments.product_title,
        segments.product_type_l1,
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.advertising_channel_type,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value
    FROM shopping_performance_view
    WHERE {date_clause}
      AND campaign.status != REMOVED
"""

# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

# Used by check_troas_pacing: actual vs target ROAS over a trailing window.
TROAS_PACING = """
    SELECT
        campaign.id,
        campaign.name,
        campaign.bidding_strategy_type,
        campaign.target_roas.target_roas,
        campaign.maximize_conversion_value.target_roas,
        metrics.cost_micros,
        metrics.conversions_value
    FROM campaign
    WHERE {date_clause}
      AND campaign.status = ENABLED
      AND campaign.bidding_strategy_type IN (TARGET_ROAS, MAXIMIZE_CONVERSION_VALUE)
"""

# Used by check_budget_pacing: today's spend vs daily budget.
BUDGET_PACING = """
    SELECT
        campaign.id,
        campaign.name,
        campaign_budget.amount_micros,
        metrics.cost_micros
    FROM campaign
    WHERE segments.date DURING TODAY
      AND campaign.status = ENABLED
      AND campaign_budget.amount_micros > 0
"""

# Used by find_anomalies: daily metric breakdown for 30 days.
# {metric_field} is replaced by the caller with e.g. "metrics.clicks"
ANOMALY_DAILY = """
    SELECT
        segments.date,
        {metric_field}
    FROM campaign
    WHERE segments.date DURING LAST_30_DAYS
      AND campaign.status != REMOVED
"""

# ---------------------------------------------------------------------------
# Disapprovals
# ---------------------------------------------------------------------------

# Status filters for disapproval queries. ACTIVE excludes paused/removed
# campaigns so health metrics only reflect live traffic. ALL includes paused
# campaigns (useful for legacy audits) but excludes permanently removed ones.
DISAPPROVALS_STATUS_ACTIVE = (
    "campaign.status = ENABLED AND ad_group.status = ENABLED"
)
DISAPPROVALS_STATUS_ALL = (
    "campaign.status != REMOVED AND ad_group.status != REMOVED"
)

# ---------------------------------------------------------------------------
# tROAS audit (Phase 3)
# ---------------------------------------------------------------------------

# Used by build_troas_proposals: ENABLED TARGET_ROAS campaigns with full metrics.
# {date_clause} is either LAST_7_DAYS or an explicit date range.
TROAS_AUDIT = """
    SELECT
        campaign.id,
        campaign.name,
        campaign.bidding_strategy_type,
        campaign.target_roas.target_roas,
        campaign.maximize_conversion_value.target_roas,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value
    FROM campaign
    WHERE {date_clause}
      AND campaign.status = ENABLED
      AND campaign.bidding_strategy_type IN (TARGET_ROAS, MAXIMIZE_CONVERSION_VALUE)
"""
# bidding_strategy_type IN (TARGET_ROAS, MAXIMIZE_CONVERSION_VALUE) captures:
#   TARGET_ROAS          -> Standard Shopping / Search / Display with tROAS
#   MAXIMIZE_CONVERSION_VALUE -> Performance Max with a tROAS target
# Python caller picks the right tROAS field:
#   PMax  -> campaign.maximize_conversion_value.target_roas
#   Other -> campaign.target_roas.target_roas
# PMax campaigns have no traditional ad_groups, so they never appear in
# TROAS_AUDIT_ADGROUP and are always evaluated at campaign level.

# Used by build_troas_proposals: ad group level tROAS for TARGET_ROAS campaigns
# where tROAS is managed per ad group (Standard Shopping).
# Returns ad groups that have their own target_roas > 0.
# Caller uses this to replace campaign-level proposals with ad-group proposals
# for any campaign that has ad groups with their own tROAS set.
TROAS_AUDIT_ADGROUP = """
    SELECT
        campaign.id,
        campaign.name,
        campaign.target_roas.target_roas,
        ad_group.id,
        ad_group.name,
        ad_group.target_roas.target_roas,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value
    FROM ad_group
    WHERE {date_clause}
      AND campaign.status = ENABLED
      AND campaign.bidding_strategy_type = TARGET_ROAS
      AND ad_group.status = ENABLED
"""
# Note: ad_group.target_roas.target_roas is not filterable in GAQL.
# Python caller filters to rows where ag.target_roas.target_roas > 0.

# Used by check_rollback_flags: conversions per campaign for an explicit date window.
# Caller filters results to the specific campaign IDs being monitored.
TROAS_CONVERSION_WINDOW = """
    SELECT
        campaign.id,
        metrics.conversions
    FROM campaign
    WHERE {date_clause}
      AND campaign.status != REMOVED
"""

# ---------------------------------------------------------------------------
# Budget audit (Phase 3)
# ---------------------------------------------------------------------------

# Used by build_budget_proposals: daily spend and budget for ENABLED campaigns
# over the last 7 days, one row per campaign per day (segments.date).
# Python caller evaluates spend-to-budget ratio per day and counts qualifying days.
BUDGET_PROPOSALS = """
    SELECT
        campaign.id,
        campaign.name,
        campaign.advertising_channel_type,
        campaign_budget.id,
        campaign_budget.amount_micros,
        metrics.cost_micros,
        metrics.conversions_value,
        segments.date
    FROM campaign
    WHERE segments.date DURING LAST_7_DAYS
      AND campaign.status = ENABLED
"""

# ---------------------------------------------------------------------------
# Brand analytics (Phase 4)
# ---------------------------------------------------------------------------

# Brand-level performance aggregated from shopping_performance_view.
# Segments by segments.product_brand. Excludes empty brand labels.
# Caller must format {date_clause} using date_range_clause().
BRAND_PERFORMANCE = """
    SELECT
        segments.product_brand,
        campaign.status,
        metrics.cost_micros,
        metrics.conversions,
        metrics.conversions_value,
        metrics.impressions,
        metrics.clicks
    FROM shopping_performance_view
    WHERE {date_clause}
      AND campaign.status != REMOVED
      AND segments.product_brand != ''
"""

# Image assets in an account -- used by list_image_assets().
# Returns all IMAGE type assets with metadata needed for campaign creation.
LIST_IMAGE_ASSETS = """
    SELECT
        asset.resource_name,
        asset.name,
        asset.type,
        asset.image_asset.file_size,
        asset.image_asset.full_size.width_pixels,
        asset.image_asset.full_size.height_pixels,
        asset.image_asset.full_size.url
    FROM asset
    WHERE asset.type = IMAGE
"""

# ---------------------------------------------------------------------------
# Disapprovals
# ---------------------------------------------------------------------------

DISAPPROVALS_ADS = """
    SELECT
        ad_group_ad.resource_name,
        ad_group_ad.policy_summary.approval_status,
        ad_group_ad.policy_summary.policy_topic_entries,
        ad_group.id,
        ad_group.name,
        ad_group.status,
        campaign.id,
        campaign.name,
        campaign.status
    FROM ad_group_ad
    WHERE ad_group_ad.policy_summary.approval_status = DISAPPROVED
      AND {status_filter}
"""

DISAPPROVALS_KEYWORDS = """
    SELECT
        ad_group_criterion.resource_name,
        ad_group_criterion.keyword.text,
        ad_group_criterion.keyword.match_type,
        ad_group_criterion.approval_status,
        ad_group_criterion.disapproval_reasons,
        ad_group.id,
        ad_group.name,
        ad_group.status,
        campaign.id,
        campaign.name,
        campaign.status
    FROM ad_group_criterion
    WHERE ad_group_criterion.type = KEYWORD
      AND ad_group_criterion.approval_status = DISAPPROVED
      AND {status_filter}
"""
