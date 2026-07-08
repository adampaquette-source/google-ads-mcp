# Asset Creation Skill (Google Ads: PMax and Search)

Canonical, task-agnostic skill for writing and assembling **assets** (headlines, long headlines, descriptions, images, search themes, audience signals, extensions) for any Google Ads account in this project. Invoke this whenever a task involves creating or editing ad assets, for a new campaign or an existing one.

This skill is about **asset craft and specs**. It sits underneath `CAMPAIGN_CREATION_BEST_PRACTICES.md` (the parent, task-agnostic build guide) and beside the campaign-type skills (`PMAX_BRAND_BREAKOUT_SKILL.md`, etc.). For image creative specifics, `PMAX_IMAGE_BEST_PRACTICES.md` is the authority; this file only summarizes image specs and cross-references it.

Last verified against Google Ads Help: 2026-07-06.

---

## 0. When to invoke

Any session that writes or edits: PMax asset group text, Search RSA text, search themes, audience signals, image/logo/video assets, or extensions (sitelinks, callouts, structured snippets, price, promotion). Read this before drafting a single headline.

---

## 1. Hard rules (carried inline so they cannot be missed)

- **No em dashes in any asset text or any file this project writes.** Use commas, periods, or "and". This is a standing project rule.
- **Sales data dictates the exemplar products and categories we feature, not assumption.** Before writing copy, search themes, or sourcing images for a brand or category, pull that brand's real sellers from Shopify (or Google Ads shopping conversion value) and let the top sellers by revenue drive the featured products, the category language, and the themes. See Section 3. This is a hard rule (memory: sales-driven-exemplar-products).
- **All campaigns created via the API are PAUSED.** Editing assets on an existing paused campaign is fine; enabling is a separate human step.
- **New campaigns go through propose/commit.** Editing text assets on an existing committed asset group is done by a direct, reversible mutate (add new asset links, remove obsolete ones), only with explicit approval, and always shown to Adam before running.
- **For brand-affiliated asset groups, every search theme must contain the brand term** (project rule from `CAMPAIGN_CREATION_BEST_PRACTICES.md`).
- **Verify every factual claim against the live store**: free-shipping verbiage and threshold (store header), final URLs (Shopify MCP `get-collection`), price/promo currency and dates. Never assert an offer we cannot confirm is live.
- **One theme per asset group.** Copy, images, listing-group product filter, final URL, search themes, and audience signal must all describe the same thing.

---

## 2. Current specs (Google Ads Help, verified 2026-07-06)

### PMax text assets

| Asset | Char limit | Min | Recommended | Max |
|---|---|---|---|---|
| Headlines (short) | 30 (include at least one <= 15) | 3 | 11+ (fill 15 for Excellent) | 15 |
| Long headlines | 90 (keep each >= 30) | 1 | 2+ (fill 5 for Excellent) | 5 |
| Descriptions | 90 each | 2 | 4+ (fill 5 for Excellent) | 5 |
| Business name | 25 | 1 | 1 | 1 |
| Call to action | n/a (auto or pick) | 1 | 1 | 1 |
| Final URL | n/a | 1 | 1 | 1 |
| Display path | 15 per path | 0 | - | 2 |

**Important correction (April 2025):** all five PMax description slots are now **90 characters**. The old separate 60-character short-description slot no longer exists. Any doc or code that still says "1 short ~60-char + 4 at ~90-char" is stale. It is still smart practice to write at least one description under ~60 characters so it renders in compact placements, but that is a convention, not a system limit.

### PMax images and logos

| Asset | Ratio | Recommended px | Min to build | For Excellent | Max |
|---|---|---|---|---|---|
| Landscape | 1.91:1 | 1200 x 628 | 1 | 4+ | 20 (all images combined) |
| Square | 1:1 | 1200 x 1200 | 1 | 4+ | 20 |
| Portrait | 4:5 | 960 x 1200 | 0 | 2+ | 20 |
| Square logo | 1:1 | 1200 x 1200 | 1 | 1 | 5 |
| Landscape logo | 4:1 | 1200 x 300 | 0 | 1 | 5 |

JPG or PNG, <= 5 MB, keep content in the center 80%. Total images across all orientations max 20. Videos: up to 5, each >= 10 sec, hosted on YouTube; if none provided Google auto-generates one (auto-video does not reach Excellent). See `PMAX_IMAGE_BEST_PRACTICES.md` for sourcing, prompts, and the no-interaction / no-garbled-logo rules.

### Search RSA text (for reference)

Headlines: up to 15, 30 char, min 3, provide as many unique as possible. Descriptions: up to 4, 90 char, provide all 4 unique. Only ~2 descriptions and ~3 headlines show at once, assembled in any order.

### Extensions (apply to PMax and Search)

Sitelinks (link text 25 char, 2 description lines 35 char each; provide 6+ for Excellent), callouts (25 char), structured snippets (values 25 char, pick from fixed headers), price assets (3 to 8 items, 25 char header/desc), promotion assets (put time-boxed offers here so they expire cleanly, not in headlines).

---

## 3. Sales-driven exemplar selection (do this FIRST)

The single most important input to good asset copy is knowing what actually sells. Assets that lead with a brand's real best-sellers capture the highest-value demand; assets built on an assumed flagship starve the categories that drive revenue.

**Procedure before writing any copy for a brand or category:**

1. Pull sales for the brand. Preferred: Shopify MCP `get_product_sales` / `query_sales` for the store, filtered to the vendor, 365-day window, ranked by net sales. If Shopify sales tools are unavailable, use Google Ads shopping conversion value as the proxy: query `shopping_performance_view` with `segments.product_brand`, `segments.product_type_l1/l2`, `segments.product_title`, and `metrics.conversions_value` over the last 365 days (GAQL requires `segments.product_brand` in the SELECT when you filter on it).
2. Rank categories (product_type) and individual products by value.
3. Let the ranking drive:
   - **Headlines and long headlines:** name the top one or two categories and the flagship product lines by their real names.
   - **Descriptions:** carry the top categories as distinct value angles.
   - **Search themes:** the brand term plus the top product lines and category phrases that people actually search.
   - **Images:** feature the top sellers (see `PMAX_IMAGE_BEST_PRACTICES.md`).
4. Re-check sales when revisiting an existing asset group. Category mix shifts.

**Worked example (why this matters):** ToolUp's Sumner asset group first led with "pipe stands." A sales pull showed material lifts were 69% of Sumner's value (Contractor Lifts, Roust-a-Bouts, Lil' Hoister) and pipe stands barely registered. The fix was to lead with material lifts. Reed had been built around pipe cutters and Tristand vises; sales showed plastic pipe joiners and hydrostatic test pumps were the real drivers and Tristand vises did not sell at all.

---

## 4. Headlines (30 char)

- **Provide 11 at minimum, fill all 15** for Ad Strength Excellent (about 6% more conversions on average at Excellent, per Google).
- **Include at least one headline <= 15 characters** and **vary the lengths deliberately.** Do not max every headline to 30 characters. Short ones serve tight Search and mobile placements; longer ones serve elsewhere.
- **One distinct angle per headline.** Map headlines across: brand, top category, second category, a benefit, a differentiator, an offer (free shipping over the store threshold), a CTA, social proof / authority. If two headlines could swap without changing meaning, one is wasted.
- **Every headline must stand alone and combine with any other.** Any headline can appear with any other headline, description, or image. Redundancy is both a quality drag and an editorial policy violation.
- **Keywords:** include real search terms in a few headlines (lead with the top category), but keep several non-keyword benefit and CTA headlines so the system has varied angles. A keyword must fit entirely within one headline.
- **Brand:** a few brand-bearing headlines are enough. The business-name field already carries the brand; do not spend every slot on the brand name.
- **CTAs:** make them specific and vary them across slots ("Shop the full lineup", "Free ship over $199"), not one generic "Shop Now" repeated.

## 5. Long headlines (90 char)

- Provide 2 at minimum, **fill all 5** for Excellent. Keep each **>= 30 characters**; a trivially short long headline wastes the slot.
- Each must read as a **complete, standalone value proposition sentence**, because in Display and Discover placements a long headline can be shown largely on its own.
- Vary the angle across the 5 and do not duplicate short-headline text verbatim.

## 6. Descriptions (90 char, up to 5)

- Provide **5 descriptions, all unique**. Write **at least one <= ~60 characters** to survive compact placements (convention).
- **Front-load the value in the first ~40 to 60 characters** of each. Any single description may be the only one shown, or gets truncated.
- **Distinct angles, do not echo the headlines.** A strong default set of 5: (1) core selection / top category, (2) second category or price/value, (3) free shipping and returns (verified), (4) authority / official dealer / guarantee, (5) a short punchy CTA-led line <= 60 char.
- Put prices, promotions, and exclusives in descriptions where true and current. Time-boxed promos belong in promotion assets, not baked into description text.

## 7. Search themes

- Up to **50 per asset group** (raised from 25 in May 2025), each **< 80 characters**. Quality and uniqueness beat quantity; you rarely need to max it. Five to ten strong, non-overlapping themes is a good working number.
- Keep themes unique. Do not add both "material lift" and "material lifts" style near-duplicates; do not add both a word and its synonym if they capture the same intent.
- **Brand-affiliated asset groups: every theme contains the brand term** (project rule).
- Themes are additive to what PMax already infers and get the same priority as phrase/broad keywords. Negative keywords and exclusions still apply. Base themes on the real top product lines and category searches from the sales pull.

## 8. Audience signals

Signals suggest who is likely to convert; they do not restrict who sees ads. Prioritize first-party data (customer lists, converters from the last 180 to 540 days, 30-day and 180-day site visitors), then custom segments that layer search behavior with URL/visit behavior, then in-market and detailed demographics. Do **not** split asset groups just to mirror audiences; split by theme and creative relevance and attach signals within.

## 9. Policy and disapproval triggers (avoid these)

- **Capitalization:** no ALL CAPS ("FREE SHIPPING"), no inter-caps ("FrEe"), no spaced letters ("F.R.E.E."). Use sentence or title case. Standard acronyms and real trademark casing are fine. Improper capitalization is a named policy violation.
- **Superlatives:** "best", "#1", "cheapest", "fastest" require third-party proof visible on the landing page (customer testimonials do not count). Avoid unless we can back them.
- **Punctuation and symbols:** no repeated punctuation ("!!!"), no emoji, no character substitution ("f1owers", "fl@wers"), no gimmicky spacing. Asterisks for star ratings and standard symbols are fine. Safest stance: no exclamation marks in headlines.
- **Repetition:** repeating words or phrases across assets is a policy violation and drags Ad Strength. Keep every asset unique.
- **Business name:** brand or legal name only, 25 char, no promotional text or extra symbols.
- **Claims:** no misleading, unverifiable, or expired offers. Only claim what is live on the landing page.

## 10. Ad Strength "Excellent" checklist

Only "Incomplete" blocks serving; higher Ad Strength correlates with performance, not eligibility. Aim for Excellent anyway. To reach it:

- [ ] 11+ headlines (target 15), at least one <= 15 char, varied lengths and angles
- [ ] All 5 long headlines, each >= 30 char, distinct
- [ ] All 5 descriptions, distinct, one <= ~60 char, front-loaded value
- [ ] 4+ landscape images, 4+ square, 2+ portrait (all under 20 total)
- [ ] Square logo (1:1); landscape logo (4:1) if available
- [ ] Custom videos in all three orientations (16:9, 1:1, 9:16); auto-video will not reach Excellent
- [ ] 6+ sitelinks, plus callouts and structured snippets
- [ ] Copy, images, listing filter, final URL, themes, and audience signal all one theme
- [ ] Every claim verified against the live store; no em dashes

## 11. Asset group structure for an e-commerce catalog

One theme per asset group. Structure axes in rough priority: by product category or brand line (default), by margin or business objective at the campaign level (hero vs standard vs clearance, so tROAS targets can differ), and by brand for multi-brand catalogs. Start with 2 to 4 asset groups and expand to about 3 to 7 as data justifies distinct creative. Do not split by audience.

## 12. 2025-2026 changes worth knowing

- All PMax descriptions now 90 char (April 2025); the 60-char slot is gone.
- Search themes limit raised 25 to 50 (May 2025), with a usefulness indicator.
- Campaign-level negative keywords rolled out; limit raised to 10,000; negative keyword lists supported in PMax.
- Asset-level reporting now shows impressions, clicks, cost, and conversions per asset (downloadable). Note conversions are credited to every component asset, so per-asset totals exceed the asset-group total; do not sum them.
- Asset Studio generative image tools available to all accounts.

## 13. Sources

Google Ads Help (official): PMax specs 17091269, text assets 14528373, best practices for text assets 15996555, image assets 14530211, Ad Strength 14143250, best practices for asset groups 14528220, creative best practices 14528221, search themes 14767319, audience signals 14530785, final URL expansion 10724817, RSAs 7684791, effective RSAs 6167122, capitalization 14848295, punctuation and symbols 14847994, editorial 6021546, misrepresentation 6020955, 2025 highlights 16756291. Reputable PPC secondary: Store Growers, WordStream, Optmyzr, GROAS, Stackmatix, Search Engine Land, PPC.land. Full URLs are recorded in the research briefs archived for the 2026-07-06 build.

---

## Self-improvement

If a new evergreen asset finding emerges during a task (a spec change, a policy pitfall, a copy pattern that measurably helps), consult Adam and then update this file. Register any change here and, if it affects campaign-type behavior, in the relevant campaign-type skill.
