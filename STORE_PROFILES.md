# Store Profiles

Per-store conventions and facts that campaign creation skills and other automations consume. This file is the canonical source for store-level facts. `stores_mapping.json` remains the canonical source for the `shopify_key ↔ ads_customer_id` mapping only.

**When a fact changes (free shipping threshold, URL pattern, naming convention, etc.), update the relevant store's section here and bump its `last_verified` date.**

When a skill or proposal reads a fact from a profile, it should also do a quick live verification (a `WebFetch` of the store header, a Shopify `get-collection` call, etc.) so that drift is caught at the moment it matters. If the live state differs from the profile, update the profile and ask Adam to confirm.

---

## Profile schema

Every store section follows this structure:

```
### <Ads account name> (`<ads_customer_id>`)

| Field | Value |
|---|---|
| shopify_key | <key from stores_mapping.json> |
| shopify_domain | <key>.myshopify.com |
| public_website | https://<store>.com  |
| merchant_center_domain | <domain Google Merchant Center is verified against> |
| free_shipping_threshold | <dollar amount> (<details: ground only, small parcel, etc.>) |
| free_shipping_verbiage | <exact text used in store header / banner / policy page> |
| brand_collection_url_pattern | <e.g. /collections/<brand>> |
| category_collection_url_pattern | <e.g. /collections/<category>> |
| product_detail_url_pattern | <e.g. /products/<handle>> |
| campaign_naming_convention | <e.g. "QT - PMax - <Brand>" for brand breakouts> |
| brand_string_casing | <how segments.product_brand returns values: lowercase / titlecase / mixed> |
| logo_asset_resource_name | <Google Ads asset resource name for the store logo> |
| business_name | <max 25 chars, used for PMax brand guidelines> |
| default_geo_target_ids | <e.g. ["2840"] for USA> |
| default_language_ids | <e.g. ["1000"] for English> |
| account_quirks | <free-form list of anything weird about this account> |
| last_verified | YYYY-MM-DD |
```

---

## Stores (active, ENABLED)

### ToolUp (`1864748540`)

| Field | Value |
|---|---|
| shopify_key | `toolupstore` |
| shopify_domain | `toolupstore.myshopify.com` |
| public_website | `https://toolup.com` |
| merchant_center_domain | `toolup.com` |
| merchant_center_id | `1153808` (feed_label `US`, enable_local true) -- set `campaign.shopping_setting` on any PMax/Shopping create so listing filters (SHOPPING source) are allowed |
| free_shipping_threshold | $199 (small parcel ground only, items below 140 lbs and within size/packaging limits) |
| free_shipping_verbiage | "Free Ground Shipping on Orders Over $199" -- source: `https://toolup.com/pages/toolup-shipping-policy` |
| brand_collection_url_pattern | `/collections/<brand>` (e.g. `/collections/ridgid`, `/collections/dewalt`, `/collections/greenlee`, `/collections/southwire`). **Exception: Milwaukee is `/collections/milwaukee-tools` (bare `/collections/milwaukee` 404s).** Always verify the exact handle before use. |
| category_collection_url_pattern | `/collections/<category-slug>` |
| product_detail_url_pattern | `/products/<handle>` |
| campaign_naming_convention | `QT - PMax - <Brand or Label>` for brand breakouts; `QT - Shopping - <Label>`; `QT Search - <Label>` for branded search. "AB \| ..." prefix is used by a different operator for test campaigns. |
| brand_string_casing | **Lowercase** in `segments.product_brand` (e.g. `"southwire"`, `"makita"`, `"itoolco"`, `"milwaukee"`). Listing group filter `brand_name` must match exactly. |
| logo_asset_resource_name | `customers/1864748540/assets/13063456975` (`Toolup-Logo-square.png`, 1200x1200) |
| business_name | `ToolUp` (6 chars) |
| default_geo_target_ids | `["2840"]` (USA) |
| default_language_ids | `["1000"]` (English) |
| account_quirks | Existing brand breakout campaigns: Ridgid (tROAS 9.5x), Greenlee (10.0x), Milwaukee (10.75x), Dewalt (11.0x), Heated Gear (15.0x). Use the average (~10x) as the baseline tROAS for new brand breakouts. **Brand breakouts segment via a custom-label listing tree (NOT a plain product_brand filter):** cl2 exclude `is-bundle` -> cl0 `in stock` only -> `product_brand` = <brand> -> cl1 include `default`/`low-performers`/`top-ids`, exclude `zombie` + unlabeled. custom_label_0=availability, cl1=performance tier, cl2=product flags (populated catalog-wide by DataFeedWatch). Use `propose_google_ads_pmax_campaign` asset-group `listing_filter="brand_breakout"`. Brand token "ego" trips Google's TOBACCO (vape) policy filter on search themes -- add EGO themes via a policy-violation exemption. |
| last_verified | 2026-07-07 |

---

### Hand Tool Outlet (`1669270772`)

| Field | Value |
|---|---|
| shopify_key | `the-klein-store` |
| shopify_domain | `the-klein-store.myshopify.com` |
| public_website | TBD -- verify on first encounter |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD -- inspect existing campaigns |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` (USA assumed) |
| default_language_ids | `["1000"]` (English assumed) |
| account_quirks | -- |
| last_verified | -- |

---

### PLS Store (`5467804732`)

| Field | Value |
|---|---|
| shopify_key | `the-pls-store` |
| shopify_domain | `the-pls-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Jobsite Tool Boxes (`1303776622`)

| Field | Value |
|---|---|
| shopify_key | `knaack-store` |
| shopify_domain | `knaack-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### MyToolStore Official (`4454933108`)

| Field | Value |
|---|---|
| shopify_key | `toolup-my-tool-store` |
| shopify_domain | `toolup-my-tool-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Jobsite Power Tools (`8243583623`)

| Field | Value |
|---|---|
| shopify_key | `the-makita-store` |
| shopify_domain | `the-makita-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Fall Protection Depot (`9847716139`)

| Field | Value |
|---|---|
| shopify_key | `fall-protection-store` |
| shopify_domain | `fall-protection-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Weather Guard Store (`3174244337`)

| Field | Value |
|---|---|
| shopify_key | `weather-guard-store` |
| shopify_domain | `weather-guard-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Total Fastening (`4034017727`)

| Field | Value |
|---|---|
| shopify_key | `fasteners-store` |
| shopify_domain | `fasteners-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Sumner Outlet (`5567964560`)

| Field | Value |
|---|---|
| shopify_key | `the-sumner-store` |
| shopify_domain | `the-sumner-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Authorizedtooloutlet.com (`9190601069`)

| Field | Value |
|---|---|
| shopify_key | `the-dewalt-store` |
| shopify_domain | `the-dewalt-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Electrician Shop (`8673147832`)

| Field | Value |
|---|---|
| shopify_key | `greenlee-store` |
| shopify_domain | `greenlee-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Plumbingtoolstore.com (`9976741128`)

| Field | Value |
|---|---|
| shopify_key | `the-ridgid-store` |
| shopify_domain | `the-ridgid-store.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Gearwrench Shop (`5327742235`)

| Field | Value |
|---|---|
| shopify_key | `gearwrench-shop` |
| shopify_domain | `gearwrench-shop.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Pro Work Supply (`1532947017`)

| Field | Value |
|---|---|
| shopify_key | `wood-shop-outlet` |
| shopify_domain | `wood-shop-outlet.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Tool Belt Outlet (`9173836783`)

| Field | Value |
|---|---|
| shopify_key | `occidentalleatheroutlet` |
| shopify_domain | `occidentalleatheroutlet.myshopify.com` |
| public_website | TBD |
| merchant_center_domain | TBD |
| free_shipping_threshold | TBD |
| free_shipping_verbiage | TBD |
| brand_collection_url_pattern | TBD |
| category_collection_url_pattern | TBD |
| product_detail_url_pattern | TBD |
| campaign_naming_convention | TBD |
| brand_string_casing | TBD |
| logo_asset_resource_name | TBD |
| business_name | TBD |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | -- |
| last_verified | -- |

---

### Themilwaukeestore.com / Red Tool Store (`4033622485`)

| Field | Value |
|---|---|
| shopify_key | `the-milwaukee-store` |
| shopify_domain | `the-milwaukee-store.myshopify.com` |
| public_website | **redtoolstore.com** (canonical, apex). `themilwaukeestore.com` 301s to `www.redtoolstore.com` which resolves to the apex. Site title: "Red Tool Store: Milwaukee Tool Superstore". Use `https://redtoolstore.com/...` for final URLs. |
| merchant_center_domain | TBD -- verify it matches redtoolstore.com before any PMax/Shopping build |
| free_shipping_threshold | $199 (ground) |
| free_shipping_verbiage | "Free Ground Shipping Over $199" (announcement bar, verified live 2026-07-12). Individual products also carry per-item "Free Shipping" badges. |
| brand_collection_url_pattern | n/a -- single-brand store; the catalog IS Milwaukee. Category collections serve the role. |
| category_collection_url_pattern | `/collections/<category-slug>` -- rich taxonomy verified live: `m18-tools`, `m12-tools`, `mx-fuel`, `packout-storage`, `packout-shop-storage`, `impact-wrenches`, `milwaukee-mechanic-tool-sets`, `milwaukee-ratchets`, `milwaukee-crimpers`, `hole-saws`, `drill-bits`, `saw-blades`, `hand-tools`, `apparel`, etc. Verify each handle before use. |
| product_detail_url_pattern | `/products/<handle>` |
| campaign_naming_convention | `QT - <Channel> - <Label>` (e.g. `QT - Search - TM`, `QT - PMax - Top IDs`, `QT - Shopping - Margin Bands`); `AB \| ...` prefix = the other operator's test campaigns. |
| brand_string_casing | `"milwaukee"` lowercase in `segments.product_brand` (consistent with ToolUp). |
| logo_asset_resource_name | TBD -- pull via `list_google_ads_image_assets` at build time |
| business_name | `Red Tool Store` |
| default_geo_target_ids | `["2840"]` |
| default_language_ids | `["1000"]` |
| account_quirks | Tier 1 account (per `CONSULTATION_RESULTS.md`). **MAP compliance: many products show "See Price In Cart"** -- do not quote prices in ad copy for those SKUs; per-SKU check required before any price claim. Social proof available for copy: 4.56/5 average across 1,303 reviews (Reviews.io style widget, verified 2026-07-12). Signature merchandising: "w/ FREE [item]" bundle offers ("Exclusive Deals"), "Limited Time Deals", and a "Milwaukee PACKOUT Builder" experience (strong PACKOUT landing candidate). Store trademark defense campaign (`QT - Search - TM`) owns "red tool store" queries. |
| last_verified | 2026-07-12 |

---

## Stores (SUSPENDED)

### Jet Tool Store / Metal Shop Tools (`5796649170`)
Status: SUSPENDED. Skip for any campaign creation work unless explicitly reactivated.

### Powermatic Tool Store (`2923679101`)
Status: SUSPENDED. No Shopify counterpart. Skip.
