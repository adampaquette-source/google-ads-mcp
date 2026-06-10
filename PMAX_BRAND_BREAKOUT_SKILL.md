# PMax Brand Breakout -- Skill

## What this skill does

Builds a single new Performance Max campaign with one asset group per target brand, where each asset group is restricted via a listing group filter to serve only that brand's products. Identifies the next N largest brands (by conversion value) in an account that do not yet have dedicated brand breakout asset groups.

## Inherits from (read these first)

- **`CAMPAIGN_CREATION_BEST_PRACTICES.md`** -- task-agnostic rules: PAUSED creation, propose/commit, audit log, pre-flight research (Ahrefs, store profile, existing campaigns, existing assets), copy composition rules (counts / char limits / brand-term search theme rule / free shipping verbiage rule), campaign-level settings, common failure modes.
- **`STORE_PROFILES.md`** -- the matching `customer_id`'s section carries: free shipping verbiage, URL patterns, campaign naming convention, brand string casing, default logo asset, business name, default geo + language, account quirks.
- **`PMAX_IMAGE_BEST_PRACTICES.md`** -- 10-image target, sourcing priority (existing → Shopify MCP → manufacturer → other sellers → web → generation supplement), at least 3 generated supplemental images per asset group, per-campaign folder convention + manifest schema, direct-image-link rule for any generation prompt, hero product rule, 3-prompt supplement structure.

This skill does not restate any of those rules. It only documents the **brand-breakout-specific execution** on top of them. If a step seems thin, that's deliberate -- the canonical rules already cover it.

## Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `customer_id` | str | (operator specifies) | The Google Ads account to build in. Look up the matching profile in `STORE_PROFILES.md`. |
| `brand_count` | int | `5` | How many new brands to include as asset groups in the new campaign. |
| `date_range` | str | `"LAST_30_DAYS"` | Lookback for brand analytics and existing-campaign tROAS baselines. |
| `daily_budget_usd` | float | (operator must specify) | Daily campaign budget. Halt at Step 5 until confirmed. |
| `target_roas_pct` | float | (operator must specify or accept suggested baseline) | Campaign tROAS target. Halt at Step 5 until confirmed. |

All store-specific defaults are sourced from the `customer_id`'s section in `STORE_PROFILES.md`. None are hardcoded here.

## Working artifact: `PROPOSAL.md`

Per `CAMPAIGN_CREATION_BEST_PRACTICES.md` § Required: PROPOSAL.md, this skill maintains a working proposal markdown at:

```
campaign_assets/<campaign_slug>/PROPOSAL.md
```

Create it right after Step 1 with `Status: drafting`. Update it at every revision and after every checkpoint confirmation. Surface it as the read-target for each `🛑 PAUSE FOR ADAM`. At commit, append the returned `proposal_id`, `campaign_resource_name`, and `asset_group_resource_names`.

## Human-in-the-loop checkpoints

`🛑 PAUSE FOR ADAM` markers appear inline below. Never bypass one without explicit confirmation. There are four:

1. After **Step 2** -- brand selection (the N target brands)
2. After **Step 5** -- copy + settings review
3. After **Step 6** -- image plan + uploaded resource names
4. After **Step 8** -- proposal go-ahead before commit

At each checkpoint, `PROPOSAL.md` must reflect the current state Adam is being asked to confirm.

---

## Step 1 -- Pull brand performance

```
get_google_ads_brand_performance(customer_id=<customer_id>, date_range=<date_range>)
```

Returns brands sorted by conversion_value descending. Note the top 10-15 brands for reference.

---

## Step 2 -- Identify brands without existing breakout campaigns

```
get_google_ads_campaign_performance(customer_id=<customer_id>, date_range=<date_range>)
```

Scan campaign names for existing brand breakout PMax campaigns. Cross-reference against Step 1 to find the next `brand_count` brands without dedicated campaigns. Also pull the tROAS of existing brand breakout campaigns -- the mean becomes the suggested baseline for `target_roas_pct`. Flag any candidate brand whose current account ROAS is materially below the proposed tROAS (it will restrict delivery during learning).

🛑 **PAUSE FOR ADAM** -- present the proposed brand list (conv value, current ROAS, flags). Wait for explicit confirmation.

---

## Step 3 -- Keyword research

For each confirmed brand, run Ahrefs per `CAMPAIGN_CREATION_BEST_PRACTICES.md` § Pre-flight research / Ahrefs. Use the standard 3-tool sequence (`overview`, `matching-terms`, `related-terms`) seeded with `<brand>` and `<brand> tools`.

Brand-breakout-specific output: extract the **top 5 highest-volume brand-anchored terms** per brand to use as that asset group's search themes (the brand-term-in-every-theme rule applies).

---

## Step 4 -- Write copy per brand

Write copy per `CAMPAIGN_CREATION_BEST_PRACTICES.md` § Asset group composition. Use the free shipping verbiage and other facts from the matching profile in `STORE_PROFILES.md`, live-verified against the store header / shipping policy page.

Brand-breakout-specific: ground copy in the brand's Ahrefs findings from Step 3 (top transactional phrases for headlines and descriptions). Every search theme must contain the brand term.

---

## Step 5 -- Determine campaign settings and final URLs

Apply `CAMPAIGN_CREATION_BEST_PRACTICES.md` § Campaign-level settings, pulling all defaults from the matching profile in `STORE_PROFILES.md`. Live-verify URLs against Shopify MCP `get-collection`.

Brand-breakout-specific:

- **Campaign name**: substitute the store's `campaign_naming_convention` with a batch label (e.g. `QT - PMax - Brand Batch 2`).
- **tROAS baseline**: the mean tROAS of existing brand breakout campaigns surfaced in Step 2.
- **Final URLs**: one `final_url` per asset group, using the store's `brand_collection_url_pattern` with each confirmed brand slug.

🛑 **PAUSE FOR ADAM** -- present all copy, search themes, settings, budget, tROAS, and final URLs in a single structured proposal. Wait for explicit confirmation.

---

## Step 6 -- Prepare image assets

Follow `PMAX_IMAGE_BEST_PRACTICES.md` end-to-end: create the per-campaign folder, work through the sourcing priority, prepare 10 approved images per asset group, include at least 3 generated supplemental images, populate `manifest.md`, move rejected candidates into `sourced/rejected/` or `generated/rejected/`, upload approved images via `upload_google_ads_image_asset`, record `resource_name` per file.

Brand-breakout-specific:

- Folder structure has one subfolder per brand: `campaign_assets/<campaign_slug>/<brand_slug>/`
- Each asset group needs its own 10-image pool with at least 3 generated supplemental images. Don't share images across asset groups.
- Reject accessories, parts, add-ons, consumables, and off-brand generated outputs before upload. Keep rejects in the relevant `rejected/` folder with manifest reasons.
- The hero product cinematic prompt (mandated) names a brand-specific signature product. Pull the reference image URL via Shopify MCP `get-product` from the brand's collection.

🛑 **PAUSE FOR ADAM** -- present the per-brand sourcing summary, gap analysis, and any generation prompts (with direct image links embedded per the canonical rule). Wait for hosted image URLs / green light on existing assets before uploading.

---

## Step 7 -- Propose

```
propose_google_ads_pmax_campaign(
    customer_id=<customer_id>,
    config={
        "campaign_name": "<from Step 5>",
        "daily_budget_usd": <daily_budget_usd>,
        "target_roas_pct": <target_roas_pct>,
        "business_name": "<from STORE_PROFILES.md>",
        "logo_image_resource": "<from STORE_PROFILES.md>",
        "geo_target_ids": <from STORE_PROFILES.md>,
        "language_ids": <from STORE_PROFILES.md>,
        "asset_groups": [
            {
                "name": "<Brand> Asset Group",
                "brand_name": "<exact brand from segments.product_brand>",
                "final_url": "<from Step 5>",
                "headlines": [...],
                "long_headlines": [...],
                "descriptions": [...],
                "landscape_image_resource": "<resource_name>",
                "square_image_resource": "<resource_name>",
                "search_themes": [...]
            },
            ...
        ]
    }
)
```

Tool validates copy minimums + char limits, writes the proposal file, returns a `proposal_id`.

Brand-breakout-specific reminder: `brand_name` must exactly match the brand string from `segments.product_brand` (casing per the store profile's `brand_string_casing` field). A mismatch means the listing group filter matches zero products.

---

## Step 8 -- Review

```
get_google_ads_pmax_proposal(proposal_id="<id>")
```

🛑 **PAUSE FOR ADAM** -- surface the full proposal for review. No commit without explicit go-ahead.

---

## Step 9 -- Commit

```
commit_google_ads_pmax_campaign(proposal_id="<id>")
```

Single atomic API call. All objects created in **PAUSED** status. Returns `campaign_resource_name`, `asset_group_resource_names`, `status: "created_paused"`. Logged to `audit.db`.

---

## Step 10 -- Verify

```
get_google_ads_campaign_performance(customer_id=<customer_id>, date_range="TODAY")
```

Confirm `status: PAUSED`. Then in the Google Ads UI verify per asset group: status Paused, copy reads correctly, product groups tab shows the brand subdivision, ad strength shows assets loaded. Adam enables when ready.
