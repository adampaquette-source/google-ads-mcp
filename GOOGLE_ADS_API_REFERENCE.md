# Google Ads API Reference — MCP Project

API version: **v24**. Python client: `google-ads` (official). All examples assume the service account + JWT auth pattern used in this project.

---

## 1. GAQL (Google Ads Query Language)

### Clause order

```sql
SELECT field1, field2, metrics.x, segments.y
FROM resource_name
WHERE condition
ORDER BY field ASC|DESC
LIMIT n
```

Only `SELECT` and `FROM` are required.

### WHERE operators

| Operator | Notes |
|----------|-------|
| `=` `!=` `>` `>=` `<` `<=` | Standard comparison |
| `IN (...)` `NOT IN (...)` | Set membership |
| `LIKE` | Pattern with `%` wildcard |
| `CONTAINS ANY` `CONTAINS ALL` | Multi-value match |
| `DURING` | Date range literal (see below) |
| `BETWEEN x AND y` | Inclusive range |
| `IS NULL` `IS NOT NULL` | Null check |
| `REGEXP_MATCH` | Regex match |

### Date ranges

Use `segments.date DURING <literal>` or `segments.date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`.

Predefined literals: `TODAY`, `YESTERDAY`, `LAST_7_DAYS`, `LAST_14_DAYS`, `LAST_30_DAYS`, `THIS_WEEK_SUN_TODAY`, `LAST_WEEK_SUN_SAT`, `THIS_MONTH`, `LAST_MONTH`, `LAST_QUARTER`, `LAST_YEAR`.

Explicit date: `WHERE segments.date = '2024-06-01'`

### Field attributes

Not every field is selectable, filterable, or sortable in every query. Check [fields/v24/{resource}](https://developers.google.com/google-ads/api/fields/v24/overview) when a query returns an error about an incompatible field.

---

## 2. Key resources and fields

### `customer_client` (MCC hierarchy)

Run from `login_customer_id` (the MCC). Returns all accounts in the hierarchy.

```sql
SELECT customer_client.id, customer_client.descriptive_name,
       customer_client.currency_code, customer_client.time_zone,
       customer_client.status, customer_client.manager, customer_client.level
FROM customer_client
WHERE customer_client.level > 0
```

`level = 0` is the MCC itself. `level = 1` are direct sub-accounts. `manager = true` means the row is itself an intermediate MCC.

Status enum values: `UNSPECIFIED`, `UNKNOWN`, `ENABLED`, `CANCELED`, `SUSPENDED`, `CLOSED`.

### `campaign`

Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `campaign.id` | int64 | |
| `campaign.name` | string | |
| `campaign.status` | enum | `ENABLED`, `PAUSED`, `REMOVED` |
| `campaign.advertising_channel_type` | enum | `SEARCH`, `SHOPPING`, `PERFORMANCE_MAX`, `DISPLAY`, `APP` |
| `campaign.campaign_budget` | resource name | `customers/{id}/campaignBudgets/{id}` |
| `campaign.bidding_strategy_type` | enum | `TARGET_ROAS`, `TARGET_CPA`, `MAXIMIZE_CONVERSIONS`, `MAXIMIZE_CONVERSION_VALUE`, `MANUAL_CPC`, `TARGET_IMPRESSION_SHARE` |
| `campaign.target_roas.target_roas` | double | e.g. `4.0` = 400% ROAS |
| `campaign.target_cpa.target_cpa_micros` | int64 | Divide by 1,000,000 for currency |
| `campaign.start_date` | string | `YYYY-MM-DD` |
| `campaign.end_date` | string | `YYYY-MM-DD` or empty |

### `campaign_budget`

| Field | Notes |
|-------|-------|
| `campaign_budget.amount_micros` | Daily budget. Divide by 1,000,000 for dollars. |
| `campaign_budget.delivery_method` | `STANDARD` or `ACCELERATED` |
| `campaign_budget.total_amount_micros` | Lifetime cap (shared budgets) |
| `campaign_budget.status` | `ENABLED`, `REMOVED` |

To get budget alongside campaign: join via `campaign.campaign_budget` using `campaign_budget` in FROM, or query `campaign_budget` directly with `FROM campaign_budget`.

### `ad_group`

| Field | Notes |
|-------|-------|
| `ad_group.id` | |
| `ad_group.name` | |
| `ad_group.status` | `ENABLED`, `PAUSED`, `REMOVED` |
| `ad_group.campaign` | Parent campaign resource name |
| `ad_group.cpc_bid_micros` | Default max CPC |
| `ad_group.target_roas_override` | Ad group level override |
| `ad_group.target_cpa_micros` | Ad group level override |

### `ad_group_criterion` (keywords)

Query from `ad_group_criterion` or `keyword_view` (same data, different resource name).

| Field | Notes |
|-------|-------|
| `ad_group_criterion.keyword.text` | Keyword text |
| `ad_group_criterion.keyword.match_type` | `EXACT`, `PHRASE`, `BROAD` |
| `ad_group_criterion.status` | `ENABLED`, `PAUSED`, `REMOVED` |
| `ad_group_criterion.quality_info.quality_score` | 1-10, may be null |
| `ad_group_criterion.cpc_bid_micros` | Keyword-level bid override |
| `ad_group_criterion.approval_status` | `APPROVED`, `DISAPPROVED`, `PENDING_REVIEW`, `UNDER_REVIEW` |

### `search_term_view`

```sql
SELECT search_term_view.search_term, search_term_view.status,
       metrics.impressions, metrics.clicks, metrics.cost_micros,
       metrics.conversions, metrics.conversions_value
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status = ENABLED
```

`search_term_view.status`: `ADDED` (already a keyword), `EXCLUDED` (negative), `ADDED_EXCLUDED`, `NONE`.

### `asset_group` (Performance Max)

| Field | Notes |
|-------|-------|
| `asset_group.id` | |
| `asset_group.name` | |
| `asset_group.campaign` | Parent PMax campaign |
| `asset_group.status` | `ENABLED`, `PAUSED`, `REMOVED` |
| `asset_group.final_urls` | Required landing pages |
| `asset_group.ad_strength` | `EXCELLENT`, `GOOD`, `POOR`, `PENDING`, `NO_ADS` |
| `asset_group.primary_status` | `ELIGIBLE`, `PAUSED`, `REMOVED`, `LIMITED`, `NOT_ELIGIBLE` |
| `asset_group.primary_status_reasons` | List of why it's limited |

### `shopping_performance_view` / `product_group_view`

For PMax and Shopping product performance:

```sql
SELECT segments.product_item_id, segments.product_title,
       segments.product_type_l1, metrics.impressions, metrics.clicks,
       metrics.cost_micros, metrics.conversions, metrics.conversions_value
FROM shopping_performance_view
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.advertising_channel_type = PERFORMANCE_MAX
```

### `metrics` (available on most resources)

| Field | Notes |
|-------|-------|
| `metrics.impressions` | |
| `metrics.clicks` | |
| `metrics.cost_micros` | Divide by 1,000,000 |
| `metrics.conversions` | |
| `metrics.conversions_value` | Revenue |
| `metrics.ctr` | Click-through rate (0.0 to 1.0) |
| `metrics.average_cpc` | In micros |
| `metrics.conversion_rate` | |
| `metrics.value_per_conversion` | Revenue per conversion |
| `metrics.search_impression_share` | Search IS (0.0 to 1.0) |
| `metrics.search_budget_lost_impression_share` | IS lost to budget |
| `metrics.search_rank_lost_impression_share` | IS lost to rank |
| `metrics.all_conversions` | Including view-through |
| `metrics.all_conversions_value` | |

Derived ROAS = `metrics.conversions_value / (metrics.cost_micros / 1_000_000)`. Not a native field; compute in code.

### `segments`

| Field | Notes |
|-------|-------|
| `segments.date` | `YYYY-MM-DD` |
| `segments.month` | `YYYY-MM-01` |
| `segments.device` | `MOBILE`, `DESKTOP`, `TABLET`, `CONNECTED_TV`, `OTHER` |
| `segments.ad_network_type` | `SEARCH`, `SEARCH_PARTNERS`, `CONTENT`, `YOUTUBE_SEARCH`, `YOUTUBE_WATCH` |
| `segments.product_item_id` | Shopping/PMax product ID |
| `segments.product_title` | Shopping/PMax product title |
| `segments.conversion_action` | Specific conversion action resource name |

Adding any segment to SELECT breaks the data out by that dimension. Including `segments.date` with a date range returns one row per day.

---

## 3. Pagination: `search()` vs `search_stream()`

| | `search()` | `search_stream()` |
|---|---|---|
| Returns | Pages up to 10,000 rows | Full result set (streamed in batches) |
| Quota cost | 1 op per page request | 1 op for the whole stream |
| Retry | Easy (per page) | Must restart stream |
| Use when | Large result sets where you need paging control | Standard reporting queries |

**Default in this project: `search_stream()`** for all reporting. Use `search()` only if a query may return millions of rows and you need incremental processing.

Paginated follow-up requests (passing `page_token`) do NOT count against daily quota.

---

## 4. Write operations (Phase 3+)

Each resource type has its own service: `CampaignService`, `AdGroupService`, `CampaignBudgetService`, etc. All follow the same mutate pattern.

### Mutate request structure (Python)

```python
campaign_service = client.get_service("CampaignService")
operation = client.get_type("CampaignOperation")

# UPDATE example
campaign = operation.update
campaign.resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"
campaign.status = client.enums.CampaignStatusEnum.PAUSED
field_mask = protobuf_helpers.field_mask(None, campaign._pb)
operation.update_mask.CopyFrom(field_mask)

response = campaign_service.mutate_campaigns(
    customer_id=customer_id,
    operations=[operation]
)
```

### Operation types

- **create**: Full resource object, no `resource_name` or ID required.
- **update**: Provide `resource_name` + only changed fields + `update_mask`.
- **remove**: Provide only `resource_name`.

### update_mask

Only fields listed in `update_mask` are changed. Use `google.api_core.protobuf_helpers.field_mask()` to generate it, or set manually via `.paths`. Forgetting this causes silent no-ops.

### GoogleAdsService.Mutate (cross-resource)

Allows creating a campaign + budget + ad groups in one atomic request using temporary resource names:

```python
temp_resource_name = campaign_service.campaign_path(-1)  # "-1" = temp ID
```

Useful in Phase 4 (campaign creation). For Phase 3 targeted adjustments, use per-resource services.

### Max operations per request: 10,000

---

## 5. MCC vs sub-account query patterns

**Every query targets a single `customer_id`.** There is no cross-account query. To report across all 19 accounts: loop over `list_accounts()` results, run the query per `customer_id`, aggregate in Python.

| Header | Purpose |
|--------|---------|
| `customer_id` | The account being queried or mutated |
| `login_customer_id` | The MCC providing access (always set to `7404361064` in this project) |

The Python client sets `login_customer_id` globally from `GOOGLE_ADS_LOGIN_CUSTOMER_ID` in `.env`. Per-account queries change only `customer_id` on the request.

`CustomerService.list_accessible_customers()` is special: it ignores `login_customer_id` and returns accounts the service account can directly touch. Returns the MCC resource name only (not all sub-accounts). Use the `customer_client` GAQL query instead to enumerate sub-accounts.

---

## 6. Error handling

```python
from google.ads.googleads.errors import GoogleAdsException

try:
    response = ga_service.search_stream(request=request)
    for batch in response:
        ...
except GoogleAdsException as ex:
    print(f"Request ID: {ex.request_id}")
    for error in ex.failure.errors:
        print(f"  Code: {error.error_code}")
        print(f"  Message: {error.message}")
        if error.location:
            for fe in error.location.field_path_elements:
                print(f"  Field: {fe.field_name}")
```

### Common error codes

| Code | Meaning | Action |
|------|---------|--------|
| `DEVELOPER_TOKEN_INVALID` | Bad dev token | Check `.env` value |
| `DEVELOPER_TOKEN_NOT_APPROVED` | Test token on prod account | Apply for Basic Access |
| `USER_PERMISSION_DENIED` | SA not added to account | Add SA as user on MCC |
| `CUSTOMER_NOT_ENABLED` | Account deactivated | Skip in loop |
| `RESOURCE_EXHAUSTED` | Daily quota exceeded | Exponential backoff; see below |
| `RESOURCE_TEMPORARILY_EXHAUSTED` | QPS rate limit | Back off 5s and retry |
| `RESOURCE_NOT_FOUND` | Bad resource name | Verify resource name format |
| `REQUIRED_FIELD_MISSING` | Malformed mutate | Check field mask / update fields |

### Retry pattern for quota errors

```python
import time
from google.ads.googleads.errors import GoogleAdsException

def with_retry(fn, retries=3):
    delays = [5, 15, 60]
    for attempt in range(retries + 1):
        try:
            return fn()
        except GoogleAdsException as ex:
            codes = [str(e.error_code) for e in ex.failure.errors]
            if any("EXHAUSTED" in c for c in codes) and attempt < retries:
                time.sleep(delays[attempt])
            else:
                raise
```

---

## 7. Quotas and rate limits

| Access level | Daily operations |
|---|---|
| Basic (current) | 15,000 |
| Standard | Unlimited (soft caps apply) |

**What counts as 1 operation:**
- 1 `search()` call (regardless of page size)
- 1 `search_stream()` call (regardless of result size)
- 1 mutate operation (each create/update/remove in a batch)
- 1 `list_accessible_customers()` call

Paginated follow-up requests (`page_token`) do NOT count.

**With 19 accounts and Basic Access:** 15,000 ops / 19 accounts = ~789 queries per account per day. Sufficient for Phase 1 reporting.

**QPS limit:** Not publicly specified but enforce exponential backoff on `RESOURCE_TEMPORARILY_EXHAUSTED`.

---

## 8. Resource name formats

All resource names follow this pattern: `customers/{customer_id}/{resource_type}/{id}`

| Resource | Format |
|----------|--------|
| Campaign | `customers/7404361064/campaigns/1234567890` |
| Ad group | `customers/7404361064/adGroups/1234567890` |
| Campaign budget | `customers/7404361064/campaignBudgets/1234567890` |
| Ad group criterion (keyword) | `customers/7404361064/adGroupCriteria/1234567890~9876543210` |
| Asset group | `customers/7404361064/assetGroups/1234567890` |

Customer IDs are always strings (no dashes) in API calls.

---

## 9. Useful doc links

- [GAQL overview](https://developers.google.com/google-ads/api/docs/query/overview)
- [GAQL grammar](https://developers.google.com/google-ads/api/docs/query/grammar)
- [Field reference v24](https://developers.google.com/google-ads/api/fields/v24/overview)
- [Date ranges](https://developers.google.com/google-ads/api/docs/query/date-ranges)
- [Mutating resources](https://developers.google.com/google-ads/api/docs/mutating/overview)
- [Rate limits](https://developers.google.com/google-ads/api/docs/productionize/rate-limits)
- [Error handling](https://developers.google.com/google-ads/api/docs/get-started/handle-errors)
- [Listing accounts (MCC)](https://developers.google.com/google-ads/api/docs/account-management/listing-accounts)
- [PMax asset groups](https://developers.google.com/google-ads/api/performance-max/asset-groups)
- [Python client library](https://developers.google.com/google-ads/api/docs/client-libs/python)
- [PMax retail campaigns](https://developers.google.com/google-ads/api/performance-max/retail)
- [Listing group filters](https://developers.google.com/google-ads/api/performance-max/listing-groups)
- [Asset requirements](https://developers.google.com/google-ads/api/performance-max/asset-requirements)
- [Temporary resource IDs](https://developers.google.com/google-ads/api/docs/batch-processing/temporary-ids)

---

## 10. Brand analytics

### `segments.product_brand` in `shopping_performance_view`

Available in `SELECT` on `shopping_performance_view`. Returns the brand attribute from the Merchant Center feed. Empty string (`""`) means no brand is set on the product.

The `BRAND_PERFORMANCE` query in `queries.py` aggregates cost, conversions, and conversion_value by brand. **Note:** `segments.product_brand` is not filterable in GAQL -- filter empty brands in Python by checking `row.segments.product_brand != ""`.

The brand string in `segments.product_brand` is case-sensitive and must exactly match what is set in the Merchant Center feed. Before using a brand name in a listing group filter, verify it against the brand performance query output.

| Field | Notes |
|---|---|
| `segments.product_brand` | Manufacturer brand from feed. Not selectable in all resources -- use `shopping_performance_view`. |
| `segments.product_type_l1` | Top-level product type (user-defined in feed). Different from brand. |
| `segments.product_item_id` | Individual SKU. Use for product-level analysis. |

---

## 11. PMax campaign creation

### Access level requirement

Basic Access (15,000 ops/day) supports campaign creation. A single atomic `GoogleAdsService.mutate()` call creating a full PMax campaign (budget + campaign + 5 asset groups + all assets + listing group filters) counts as **1 API operation** against quota.

### Mandatory asset minimums per asset group

| Asset type | Field type | Min | Max | Char limit |
|---|---|---|---|---|
| Headline | HEADLINE | 3 | 15 | 30 |
| Long headline | LONG_HEADLINE | 1 | 5 | 90 |
| Description | DESCRIPTION | 2 | 5 | 90 (at least 1 must be <=60) |
| Landscape image (1.91:1) | MARKETING_IMAGE | 1 | 20 | min 600x314 px |
| Square image (1:1) | SQUARE_MARKETING_IMAGE | 1 | 20 | min 300x300 px |

**Campaign-level (brand guidelines, required when `brand_guidelines_enabled=True`):**

| Asset type | Field type | Notes |
|---|---|---|
| Business name | BUSINESS_NAME | Max 25 chars. Link via `CampaignAsset`, NOT `AssetGroupAsset`. |
| Logo (1:1) | LOGO | Min 128x128 px. Link via `CampaignAsset`, NOT `AssetGroupAsset`. |

`brand_guidelines_enabled=True` is the default for new campaigns (since v21). Setting it to `False` requires providing BUSINESS_NAME and LOGO at the asset group level instead -- not recommended.

### Immutable fields

| Field | Notes |
|---|---|
| `advertising_channel_type` | Cannot change campaign type after creation. |
| `shopping_settings.merchant_id` | Cannot change Merchant Center link after creation. |
| `brand_guidelines_enabled` | Set at creation; cannot toggle after. |

### Image asset upload

Images must be provided as base64-encoded bytes. Upload via `AssetService.mutate_assets()` with `asset.image_asset.data`. The `ads_mcp/creation/assets.py` module handles fetching from URL + encoding.

```python
asset.image_asset.data = base64.b64encode(image_bytes).decode("utf-8")
```

### Mutate operation ordering

For a multi-asset-group PMax campaign in a single `GoogleAdsService.mutate()` call, operations must be ordered as follows. Temporary IDs (`-1`, `-2`, ...) are used for forward references.

1. `CampaignBudget` (temp -1)
2. `Campaign` (temp -2, references budget temp ID)
3. `CampaignCriterion` (geo + language; reference campaign temp ID)
4. Business name `Asset` (temp -3) + `CampaignAsset` link
5. `CampaignAsset` link for logo (existing resource name + campaign temp ID)
6. `AssetGroup` operations (one per group; temps -100, -101, ...)
7. **ALL** text `Asset` create operations across every group
8. **ALL** `AssetGroupAsset` link operations across every group (text then image)
9. **ALL** `AssetGroupSignal` (search themes) across every group
10. **ALL** `AssetGroupListingGroupFilter` operations across every group

**Critical:** Steps 7 and 8 must not be interleaved. All `Asset` creates before all `AssetGroupAsset` links, or the API fails mid-batch.

### Listing group filter tree for brand subdivision

Three nodes per asset group:

```
root (SUBDIVISION)
|-- brand = "Milwaukee"  (UNIT_INCLUDED)   <- only Milwaukee products serve
+-- [other]              (UNIT_EXCLUDED)   <- all other brands excluded
```

The "other" node has no `case_value.product_brand` set. The API interprets this as the catch-all sibling.

`listing_source` must be `SHOPPING` for Merchant Center-linked campaigns.

See `ads_mcp/creation/listing_groups.py` for the implementation: `build_brand_subdivision_ops()` and `build_root_listing_group_ops()`.

### Common creation errors

| Error | Cause | Fix |
|---|---|---|
| `AssetLinkError.BRAND_ASSETS_NOT_LINKED_AT_CAMPAIGN_LEVEL` | BUSINESS_NAME or LOGO linked at asset group level | Move to `CampaignAsset` operation |
| `AssetGroupError.NOT_ENOUGH_HEADLINE_ASSET` | Fewer than 3 headlines | Add more headlines |
| `AssetGroupError.SHORT_DESCRIPTION_REQUIRED` | No description <= 60 chars | Shorten one description |
| `RESOURCE_NOT_FOUND` on image resource | Wrong resource name for pre-uploaded asset | Re-run `list_google_ads_image_assets()` to get current names |
| `FINAL_URL_SHOPPING_MERCHANT_HOME_PAGE_URL_DOMAINS_DIFFER` | Asset group final URL domain doesn't match Merchant Center | Use the same domain as the Merchant Center website |
