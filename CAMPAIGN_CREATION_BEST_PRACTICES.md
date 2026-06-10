# Campaign Creation Best Practices

This is the canonical, task-agnostic guide for any Google Ads campaign creation task. Read it before starting any new campaign build. Task-specific **skills** (e.g. `PMAX_BRAND_BREAKOUT_SKILL.md`) inherit these rules and only add the situation-specific execution detail on top.

If you discover a new evergreen finding while working on a campaign creation task, see the **Self-improvement rule** at the bottom of this file -- consult Adam about appending it here so it carries forward to the next campaign.

---

## Campaign creation skill registry

Each campaign type has a dedicated skill file with its own parameters, steps, and `🛑 PAUSE FOR ADAM` checkpoints. Pick the skill that matches the task and read both this file and the skill file before starting.

| When the task is... | Invoke skill |
|---|---|
| Building a PMax brand breakout (one asset group per brand, brand-restricted listing groups) | `PMAX_BRAND_BREAKOUT_SKILL.md` |
| Launching a PMax campaign for a product category (no brand restriction) | `PMAX_CATEGORY_LAUNCH_SKILL.md` *(TBD -- create when first needed)* |
| Building branded trademark search | `SEARCH_TRADEMARK_SKILL.md` *(TBD)* |
| Setting up shopping campaigns for a new store | `SHOPPING_NEW_STORE_SKILL.md` *(TBD)* |
| Any campaign type not yet covered above | Use this file's rules to scaffold the work, then propose a new skill file when the pattern is clear. |

**Adding a new skill:** when a campaign type appears for the second time and the work is repeating, create a new `<TYPE>_SKILL.md` file, register it in this table, and add the file to the `CLAUDE.md` file index. The skill must start with an `## Inherits from` block pointing back to this file.

---

## Companion files

- `STORE_PROFILES.md` -- per-store conventions and facts (URL patterns, free shipping verbiage, campaign naming, brand string casing, default logo asset, etc.). Read the relevant store's profile at the start of every campaign creation task. Update it whenever you discover or correct a store-level fact.
- `PMAX_IMAGE_BEST_PRACTICES.md` -- image creative guide (formats, optimal mix, hero product rule, 3-prompt structure, anti-patterns). Read for any task that needs new image assets or prompts.
- `GOOGLE_ADS_API_REFERENCE.md` -- API reference. Sections 10 (brand analytics) and 11 (campaign creation) are mandatory reading for any creation tool work.

---

## The "always" rules -- non-negotiable for every campaign creation task

1. **All campaigns are created in `PAUSED` status.** No serving occurs until Adam manually enables them in the UI. This applies to every channel type, every bidding strategy, every account.
2. **Every write goes through the propose/commit pattern.** Never write directly to the API. Build a proposal, surface it for review, then commit. See the tROAS and budget proposal flows as the canonical pattern.
3. **Maintain a `PROPOSAL.md` in the campaign assets folder** -- this is the human-readable working artifact for the task (see "Required: PROPOSAL.md" below).
4. **Audit log every creation.** Use `_write_audit()` (or the equivalent for the relevant module) to record what was created, when, and by which proposal.
5. **Read `GOOGLE_ADS_API_REFERENCE.md` sections 10 and 11 before writing or modifying any creation tool.** It covers asset requirements, brand guidelines, listing group filter trees, image upload via base64, and mutate operation ordering.
6. **Campaigns must be created atomically.** A single `GoogleAdsService.mutate()` call -- either the full campaign succeeds or nothing is created.

---

## Required: `PROPOSAL.md`

Every campaign creation task maintains a human-readable proposal markdown file at:

```
campaign_assets/<campaign_slug>/PROPOSAL.md
```

Where `<campaign_slug>` is a kebab-case version of the planned campaign name (e.g. `qt-pmax-brand-batch-2`). This file is the working artifact for the entire task -- it captures everything Adam needs to review before approving each checkpoint, and remains as the post-creation record.

**Lifecycle:**

1. **Create the file as soon as the campaign type and rough scope are known** (typically right after Step 1 / pre-flight data pull). Initial revision can be a skeleton with `Status: drafting`.
2. **Update it at every revision** (V1 -> V2 -> V3 as feedback comes in). Always bump the `Last revised` field and append a row to the revision log table at the bottom.
3. **Use it as the surface for each `🛑 PAUSE FOR ADAM` checkpoint** -- Adam reads PROPOSAL.md (and the inline checkpoint markers in the section the skill is currently executing), then confirms via chat. Confirmations get reflected back into PROPOSAL.md (status flips, blockers close).
4. **At commit time, append the returned `proposal_id`, `campaign_resource_name`, and `asset_group_resource_names`** to the file. Flip `Status` to `committed` and the commit timestamp.
5. **Keep the file after commit** -- it is the audit narrative paired with the row in `audit.db`.

**Required sections** (a campaign-type skill may add more; these are the floor):

- Header table: `Status`, `Customer ID`, `Skill`, `Created`, `Last revised`, `Proposal ID` (assigned at commit), `Campaign resource name` (assigned at commit)
- One section per workflow step the skill defines (e.g. brand selection, copy, settings, image plan, etc.)
- Inline `🛑 Checkpoint N` markers showing approval status (pending / confirmed by Adam YYYY-MM-DD)
- "Outstanding items" list of blockers
- "Revision log" table at the bottom

**The proposal lives next to the campaign's working images** -- it's in the same `campaign_assets/<campaign_slug>/` directory that holds the `sourced/`, `generated/`, and `manifest.md` per brand (or asset group). This co-location keeps the entire task self-contained: copy / settings / image manifest / final resource names all in one folder for audit.

The `campaign_assets/` directory itself is gitignored (binary images), but PROPOSAL.md is text -- if you want it in version control, move it explicitly or store a copy elsewhere. Default behavior is local-only.

---

## Pre-flight research (do this every time, before writing any copy or config)

### 1. Ahrefs keyword research (mandatory before any copy or search themes)
Use the Ahrefs MCP connector for every brand or category the campaign will target:
- `keywords-explorer-overview` -- volume and difficulty for seed terms
- `keywords-explorer-matching-terms` -- high-volume brand/product variations
- `keywords-explorer-related-terms` -- related intent clusters

From the results:
- Select the top 5 highest-volume, brand-relevant terms as search themes (subject to the brand-term rule below).
- Identify top transactional phrases (high volume + "buy", "shop", "sale", "price", etc.) for headlines and descriptions.
- Note high-competition terms that suggest pricing or urgency angles in copy.

### 2. Existing campaigns review
Run `get_google_ads_campaign_performance(customer_id, date_range)` and look for:
- **Naming conventions** -- match the existing account convention (e.g. ToolUp uses `QT - PMax - [Brand]` for brand breakouts).
- **tROAS baselines** -- average the tROAS of similar existing campaigns to inform the new campaign's target. Flag any brand whose current account ROAS is materially below your proposed tROAS.
- **Budget patterns** -- existing campaigns of similar scope give a defensible starting budget.

### 3. Existing image assets
Run `list_google_ads_image_assets(customer_id)` before sourcing or generating new images. Brand-named existing assets may already cover the need.

### 4. Store profile (read first, verify live)
Look up the target account's section in `STORE_PROFILES.md`. The profile carries the canonical record of: free shipping verbiage and threshold, brand / category / product URL patterns, campaign naming convention, brand string casing, default logo asset, business name, default geo + language.

**The profile is a starting point, not the final truth.** Always perform a quick live verification of any fact you're about to use in copy or config (e.g. `WebFetch` the store header for the free shipping line, Shopify MCP `get-collection` for a brand URL). If the live state differs from the profile, update the profile and ask Adam to confirm before continuing.

### 5. Free shipping / promo verbiage from the actual store
**Never assume.** Re-verify the current promotional verbiage on the actual store's website header or shipping policy page even if the profile has it recorded. Copy the exact threshold and phrasing. Examples of what to confirm:
- Free shipping threshold (e.g. "$199 small parcel ground" -- not assumed `$50`)
- Return policy callouts
- Any "Official Dealer" or partner claims you intend to use

### 6. Final URLs via Shopify MCP
Use the Shopify MCP server (`get-collection` for brand and category collections, `get-product` for product-specific landing pages) to confirm the correct landing page URL before assigning it to a `final_url` field. **The URL must match the Merchant Center website domain** -- mismatches block PMax campaigns from serving Shopping inventory.

If the Shopify MCP doesn't surface what you need (no search tool available, or specific GID unknown), fall back to a targeted `site:<store>.com` web search to identify the right collection or product URL.

---

## Asset group composition rules

### Copy (text assets)

| Field | Min count | Max count | Char limit | Notes |
|---|---|---|---|---|
| Headlines | 3 | 15 | 30 chars | Recommend 10. Mix brand name, top Ahrefs phrases, value props, CTAs. |
| Long headlines | 1 | 5 | 90 chars | Recommend 3. Incorporate keyword phrase + the verified value prop. |
| Descriptions | 2 | 5 | 90 chars | Recommend 4. **At least 1 must be 60 chars or fewer** (Google requirement). Cover: brand authority, product breadth, shipping (with the verified threshold), transactional intent. |
| Search themes | 0 | 25 | n/a | Recommend 5. See "Search themes -- brand-term rule" below. |

**Copy content rules:**
- **Reference the store directly by name in copy** where it fits naturally (e.g. "Shop Makita at ToolUp", "Free Ship Over $199 at ToolUp"). Direct store reference improves CTR and reinforces the destination.
- **Use the verified free shipping verbiage** -- match the actual threshold and language from the store header / shipping policy page.
- **No em dashes anywhere in copy** (project-wide convention).
- **No text overlay on images** (PMax renders headlines separately -- text inside images causes ad strength penalties).

### Search themes -- brand-term rule

For any asset group affiliated with a particular brand (which is the vast majority of campaign creation tasks), **every search theme must contain the brand term**. This focuses the campaign on lower-funnel branded intent and prevents Google from broadening into unrelated category traffic.

- Correct: `milwaukee drill bits`, `milwaukee cordless tools`, `milwaukee m18 battery`
- Wrong: `cordless drill`, `power tool battery`, `drill bits`

For brands with very low standalone brand search volume, append the brand term to category modifiers (e.g. `itoolco cable puller` instead of just `cable puller`).

For category-level or non-brand asset groups (uncommon), this rule is relaxed -- but document why you're skipping the brand-term rule and what the search themes will target instead.

### Images (asset images)

See `PMAX_IMAGE_BEST_PRACTICES.md` for the full guide. Summary:
- **Target ~10 images per asset group** (Google's optimal mix: studio + lifestyle + close-up + context). Required minimums for the campaign config: 1 landscape (1.91:1, min 600x314), 1 square (1:1, min 300x300).
- **Source from existing material first, generate as supplement.** Sourcing priority: (1) existing account assets, (2) Shopify MCP `get-product` / `get-collection`, (3) manufacturer media library / PDPs, (4) other authorized sellers of the brand, (5) general web image search. Only then (6) ChatGPT generation to fill the gap.
- **Per-campaign working folder**: `campaign_assets/<campaign_slug>/<brand_slug>/` with `sourced/`, `generated/`, and `manifest.md` subfolders. Gitignored. See `PMAX_IMAGE_BEST_PRACTICES.md` for the manifest schema.
- **Hero product rule**: at least one image per asset group set must be a hero cinematic of one specific named item. Realistic trade environment, dramatic lighting.
- **Source image input rule for any generation prompt**: every generation pass must include the actual source image pixels as visible or attached reference input. In Codex, call `view_image` on each selected local source file immediately before `image_gen`. Direct `.jpg`/`.png`/`.webp` URLs are still recorded for audit, but URL text alone is not enough and produces off-brand fantasy products.
- **Source preservation prompt rule**: the prompt must explicitly say to use the visible source image as the product identity source and preserve the exact product silhouette, proportions, color blocking, major parts, and physical details. Do not ask the model to "make a product like..." or rely on the brand/product name alone.
- **Generated image QA rule**: visually review every generated image against its exact source image(s) before leaving it active. Reject and regenerate anything with hallucinated product features, product misrepresentation, strange or unsafe use, impossible geometry, fake text, wrong colorway, or a context that misstates what the product does.
- **3-prompt structure when generating**: (1) studio hero supplement (skip if sourced studio is strong), (2) lifestyle / in-use, (3) hero product cinematic (mandated). All three require source image input plus explicit source-preservation wording.

### `brand_name` matching (for brand-restricted listing group filters)
The `brand_name` field in any asset group listing group filter must **exactly match** the brand string as it appears in `segments.product_brand` from the Merchant Center feed. Case-sensitive. A mismatch means the filter matches zero products and the asset group serves nothing. Pull the brand string from the brand analytics query results -- never type it from memory.

---

## Campaign-level settings

| Setting | How to choose |
|---|---|
| Campaign name | Follow the existing account convention exactly. Look at similar existing campaigns in the account before naming. |
| Budget | Adam's preference, or match the daily budget of similar existing campaigns. Flag the suggestion and wait for confirmation. |
| Bidding strategy / tROAS | Match the tROAS of comparable existing campaigns. Flag any brand or product set whose current ROAS is materially below the proposed target -- it may restrict delivery during learning. |
| Geo targeting | Default `["2840"]` for USA unless the brief specifies otherwise. |
| Language targeting | Default `["1000"]` for English unless the brief specifies otherwise. |
| Business name | Store name, max 25 chars. Lives at campaign level (brand guidelines), not asset group level. |
| Logo | One shared logo per campaign, pre-uploaded as a 1:1 image asset, min 128x128 (recommended 1200x1200). Lives at campaign level (brand guidelines), not asset group level. |
| `brand_guidelines_enabled` | `True` (default since v21). This is what makes the campaign-level logo + business name take effect. |

---

## Common failure modes -- check before propose

- **Asset image dimensions below minimum**: landscape < 600x314 or square < 300x300 will fail validation.
- **Final URL domain mismatch with Merchant Center website**: PMax will reject the campaign.
- **`brand_name` casing mismatch with `segments.product_brand`**: listing group filter matches zero products, asset group serves nothing.
- **Missing campaign-level logo or business name** when `brand_guidelines_enabled=True`: API returns an error.
- **No description under 60 chars**: Google requires at least one description to be 60 chars or fewer.
- **Free shipping threshold copy doesn't match site policy**: misleading ads risk disapproval and erode trust.
- **Search themes without brand term on a brand-affiliated asset group**: campaign broadens out of branded intent, ROAS drops.

---

## Self-improvement rule -- ALWAYS CONSULT ADAM IF YOU LEARN SOMETHING NEW

This file is the canonical, evergreen source for task-agnostic campaign creation guidance. **Every time you work on a campaign creation task, watch for findings that should live here.**

Examples of findings worth appending:
- A new copy convention that improved CTR or ad strength
- A new tool or MCP server that should be part of pre-flight research
- A new failure mode discovered during creation
- A new store-level fact (e.g. updated free shipping threshold, new domain pattern)
- A new image creative rule (those go in `PMAX_IMAGE_BEST_PRACTICES.md` -- but the pointer stays here)
- A platform-level behavior change in Google Ads (those mostly go in `GOOGLE_ADS_API_REFERENCE.md` -- but if it affects creation workflow, mention here too)

**When you spot one:**

1. Pause the current task at a safe point.
2. Ask Adam: "I noticed [finding] while working on this. Should I append a note about it to `CAMPAIGN_CREATION_BEST_PRACTICES.md` (or one of its companion files) so we carry the lesson forward?"
3. If yes, write the addition in the right file:
   - **Evergreen rule across all stores and campaign types** -> this file.
   - **Store-specific fact** (URL pattern, free shipping verbiage, campaign naming, account quirk) -> `STORE_PROFILES.md` (the relevant store's section). Bump `last_verified`.
   - **Image creative finding** -> `PMAX_IMAGE_BEST_PRACTICES.md`.
   - **Campaign-type-specific execution detail** -> the relevant `<TYPE>_SKILL.md` file.
4. Keep additions succinct -- evergreen rules only, no task-specific narrative.
5. Update the change routing table in `CLAUDE.md` if the new finding introduces a new "where this lives" relationship.
