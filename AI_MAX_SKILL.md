# AI Max for Search Skill (Google Ads)

Canonical skill for creating and configuring **AI Max for Search** campaigns in this project. AI Max is a feature suite layered onto standard Search campaigns, not a standalone campaign type, so this is a creation supplement that sits beside the Search build path and inherits the project's campaign-creation rules.

## Inherits from

Read [CAMPAIGN_CREATION_BEST_PRACTICES.md](CAMPAIGN_CREATION_BEST_PRACTICES.md) first (task-agnostic build rules), then [ASSET_CREATION_SKILL.md](ASSET_CREATION_SKILL.md) (asset craft, which overlaps AI Max text customization). This file adds only the AI-Max-specific detail on top. For account-level optimization judgment, [PPC_ADVISOR.md](PPC_ADVISOR.md) governs.

Last researched against Google Ads Help, the Google Ads API docs, and reputable PPC sources: 2026-07-07. AI Max moves fast (see the self-improvement clause at the end); re-verify specs before a build.

---

## 1. What AI Max is (and is not)

AI Max is "a comprehensive suite of targeting and creative enhancements" you toggle on inside an existing or new **Search** campaign (blog.google/products/ads-commerce/google-ai-max-for-search-campaigns/). It is **not** a new campaign type like Performance Max. Turning it on activates three bundled features (search term matching, text customization, final URL expansion) plus a set of precision controls (brand, location, URL) and enhanced reporting (support.google.com/google-ads/answer/15910187).

Google positions AI Max as the evolution and eventual replacement of Dynamic Search Ads (DSA), automatically created assets (ACA), and campaign-level broad match.

Lifecycle dates that matter:
- Announced May 2025 (Google Marketing Live), open beta through late May 2025 (blog.google GML 2025).
- General availability April 15, 2026 (marketingdive.com; blog.google/products/ads-commerce/dsa-upgrade-to-ai-max-2026/).
- Forced migrations: ACA and campaign-level broad match auto-upgrade to AI Max in **September 2026**; DSA auto-migration was delayed from September 2026 to **February 2027** (searchengineland.com/google-delays-dynamic-search-ads-migration-to-ai-max-480049; ppc.land). New DSA campaign creation is removed January 2027.

---

## 2. Hard rules (carried inline)

Inherited, non-negotiable:
- **No em dashes** in any asset text or file this project writes.
- **New campaigns created via the API are PAUSED**; enabling is a separate human step. Enabling AI Max on an existing live campaign is a real change; treat it as a proposal and get Adam's explicit go before flipping it.
- **Sales data dictates featured products and copy** (see [ASSET_CREATION_SKILL.md](ASSET_CREATION_SKILL.md) Section 3 and the sales-driven-exemplar-products memory). AI Max text customization will generate copy from the landing page, so the landing page and any seed assets must lead with real best-sellers.
- **Verify every factual claim** (free shipping verbiage and threshold, final URLs) against the live store.

AI-Max-specific hard rules:
- **AI Max requires a conversion-based Smart Bidding strategy** (Maximize Conversions or Maximize Conversion Value, with optional tCPA/tROAS). Search term matching will not work on Manual CPC (wordstream.com/blog/ai-max-for-search; support.google.com/google-ads/answer/15909989). Do not propose AI Max for a campaign that is not on conversion Smart Bidding with trustworthy conversion tracking.
- **On a multi-brand account, lock the brand, URL, and negative controls BEFORE enabling** (Section 5). Final URL expansion is default-on and will route to any indexable page unless scoped.
- **Start small and review search terms roughly twice as often as standard Search** during the learning period (Section 10). Expanded matching can spend on irrelevant queries fast.
- **Do not conflate the performance figures** in Section 6; Google's headline number understates CPA risk for retail.

---

## 3. Eligibility and prerequisites

Firmly official (support.google.com/google-ads/answer/15909989; developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started):
- Campaign type must be **Search**.
- Bid strategy must be **conversion-based Smart Bidding** (Max Conversions or Max Conversion Value, including tCPA/tROAS forms). Manual CPC cripples the feature.

Best-practice readiness (third-party, not a Google-published gate, treat as guidance): roughly **30+ conversions in the trailing 30 days** and a meaningful daily budget (~$50+ cited), with 100+ monthly conversions performing better (almcorp.com; groas.com). Before proposing AI Max, confirm conversion tracking is firing correctly (diagnose per PPC_ADVISOR.md); expanded matching on broken tracking wastes money.

---

## 4. The components (defaults and dependencies)

| Feature | Level | Default when AI Max on | Independently toggleable | Notes |
|---|---|---|---|---|
| Search term matching | Ad group (must be on at campaign first) | On | Yes (per ad group) | Broad match + "keywordless" tech; expands beyond your keywords using keywords, creatives, and URLs |
| Text customization (formerly automatically created assets) | Campaign | On | Yes | Generates headlines/descriptions from existing ads, landing pages, and generative AI |
| Final URL expansion | Campaign | On | **No, requires text customization** | Picks the most relevant landing page (DSA-like). Turning off text customization forces this off |
| Locations of interest | Ad group | n/a | Yes | Reach by geographic intent in keywordless matches (note: standard Search sets location only at campaign level) |
| Brand inclusions | Campaign and ad group (ad group overrides) | n/a | Yes | Brands your ads should associate with |
| Brand exclusions | Campaign only | n/a | Yes | Prevent association with specific brands |
| URL inclusions | Ad group | n/a | Yes | Add URLs not captured by final URL expansion |
| URL exclusions | Campaign | n/a | Yes | Exclude pages from serving as landing pages |
| Page feeds | Campaign | n/a | Yes | Feed of allowed URLs; simpler than maintaining inclusion/exclusion lists |
| Text disclaimers | Campaign | n/a | Yes | Force required text to always appear (regulated industries) |

Sources: support.google.com/google-ads/answer/15910187 and .../15909989; searchengineland.com/ai-max-for-search-everything-you-need-to-know-462923.

Key dependency to remember: **final URL expansion cannot run without text customization.** If you want AI's expanded matching but full control of landing pages, keep search term matching on and turn text customization (and therefore final URL expansion) off, or scope expansion tightly with page feeds and URL exclusions.

---

## 5. Controls and brand safety (highest-stakes section for our accounts)

Google's own framing of the control levers (blog.google/products/ads-commerce/ai-max-new-features/; support.google.com/google-ads/answer/15910187):

> Bad query -> negative keyword. Bad destination -> URL exclusion. Bad cannibalization -> brand exclusion.

The six levers:
1. **Negative keywords.** Retained standard control at campaign and ad group level; not part of the AI Max toggle. Still essential because expanded matching can misroute queries. Brand filters leak misspellings and variants, so negative keyword lists remain the backstop.
2. **Brand controls.** A native "Branded Searches" control (shipped mid-2026) offers three options: show on all relevant searches, control via brand inclusions/exclusions, or unbranded-only (delegates brand recognition to Google's entity index) (ppc.land/google-ads-gets-branded-search-controls-inside-ai-max/). Brand lists themselves are **account-level, built in the Shared Library** (Tools > Shared library > Brand lists) and applied to a campaign; brand exclusions are campaign-level only, brand inclusions are campaign or ad group (ad group overrides). Two gotchas for a multi-brand catalog: (a) creating any brand list now requires AI Max enabled (gated since May 2025), and (b) a brand not already in Google's brand library must be requested and takes about 3 to 6 weeks to review, so audit library coverage of our house and niche brands before relying on inclusions. Also, a negative keyword that overlaps a brand inclusion term will suppress that traffic, so do not fight your own inclusion list with negatives. For our accounts: **exclude our own store brand and any brand that has its own dedicated campaign** (or set Branded Searches to unbranded-only) so AI Max does not cannibalize existing branded Search at a higher CPC; use inclusions only when a campaign is meant to own a specific manufacturer brand and you accept that inclusions suppress all non-brand queries.
3. **Text Guidelines.** Global for all advertisers since February 26, 2026 (ppc.land). Up to **25 term exclusions** and up to **40 messaging restrictions** per campaign. Use these to keep generated copy on-brand and compliant (exclude off-brand terms, forbidden claims).
4. **AI Brief.** Steer AI Max generation in plain natural language (ppc.land/ai-brief-google-lets-advertisers-steer-ai-max-in-plain-language/).
5. **Final URL expansion opt-out** plus **URL exclusions / page feeds** to keep destinations inside the right site sections. In the API, URL controls use `webpage.conditions` (URL_CONTAINS, PAGE_TITLE_CONTAINS) with `negative=TRUE` at campaign level.
6. **Ads Advisor policy scanning.**

Documented pitfalls and mitigations (ppc.live; lunio.ai; groas.ai; adalysis.com):
- Final URL expansion can route users to outdated pages, blog posts, or About Us pages. Mitigate with page feeds, URL exclusions, or by disabling expansion.
- **Asset pinning does NOT work when final URL expansion is enabled.** If you must pin (legal or brand text), you cannot rely on it with expansion on; use text disclaimers instead.
- Broad triggering can consume a meaningful share of budget on irrelevant impressions in competitive verticals. Mitigate with tight negatives, brand exclusions, and frequent search-term review.
- **Search Partner Network waste.** A documented case ran ~500k SPN impressions/month at 0.07% conversion versus 3.04% on Google Search (about 43x worse). Monitor SPN impression share and conversion rate; exclude SPN if its rate is a fraction of Google Search.
- **Locations of interest can mismatch shipping or inventory** by serving on geographic-intent queries outside our fulfillment area. Watch impressions and search terms by location; toggle it off if it expands geo reach in ways we cannot serve.
- **Text guidelines detail:** brand-voice description (concrete do/don't rules work; vague ones do not), up to 25 term exclusions (30 chars each) for forbidden words/claims, and up to 40 messaging restrictions (300 chars each). Pin required legal or tagline assets to keep them verbatim (pinned assets are used as-is, though final URL expansion can still override the destination).

---

## 6. Performance expectations and honest evidence

Set expectations from the independent data, not the headline.

Google-official (label as best-case marketing):
- "Typically 14% more conversions or conversion value at similar CPA/ROAS," up to 27% for exact/phrase-heavy campaigns (blog.google, May 2025). Google notes this is from beta participants and **excludes retail**, so it is best-case, not typical for us.
- A separate, more conservative figure: ~7% more conversions/value using the full feature suite versus search term matching alone (support.google.com/google-ads/answer/15910187). The 14%, 27%, and 7% are three different baselines; do not merge them.

Both official figures **explicitly exclude retail**, and Google has published no retail benchmark. Treat the headline numbers as not applicable to a tool store.

Independent (most load-bearing for us, all vendor-reported):
- Smarter Ecommerce, 250+ retail campaigns, ~1M AI Max impressions: **median revenue +13% but median CPA +16%**, no median ROAS gain, ROAS spread **+42% to -35%**, and only about 22% of campaigns landed near their original ROAS target (searchengineland.com/google-ai-max-revenue-higher-cpa-study-470928; searchenginejournal.com). AI Max conversions showed roughly 35% lower ROAS than other match types in the same campaigns, at lower AOV.
- The lift is largely **reshuffled, not incremental**. SMEC's impression mix was about 80% exact, 19.5% phrase, and only 0.38% truly broad, meaning most "AI Max" volume was re-attributed existing coverage. Brainlabs found only about 46% of "new" queries were genuinely new (roughly 3% true account-wide incremental value versus 7% at campaign level), and every successful test was in an account with low or no DSA adoption (searchengineland.com/google-ai-max-performance-tests-471366).
- Benjamin Wenner's case studies found AI Max conversion rate consistently below exact match and around or below broad match across travel, fashion e-commerce, and B2B SaaS.
- Documented waste modes: one account saw competitor brand terms take ~69% of impressions; a Search Partner Network case ran 0.07% conversion rate versus 3.04% on Google Search; Monks reported ~99% of AI Max impressions producing zero conversions across ~30k terms. Sentiment poll: only ~16% of PPC pros reported good performance. (Sources in Section 12; treat groas.com $-figures as directional marketing only.)

Google-featured case studies (Royal Canin +263% conversions, ClickUp +20% conversions, L'Oreal 2x conversion rate, Klook +161% value) are vendor-selected wins; do not treat as generalizable (business.google.com/think).

Bottom line for our accounts: expect AI Max to grow revenue and reach while degrading efficiency (CPA up, ROAS flat to down), with outcomes highly account-dependent. Run it only as a contained, experiment-gated test where a higher CPA at higher volume is an acceptable trade, and gate rollout on the exit criteria in Section 10.

---

## 7. Interaction with our other campaigns

- **Branded Search cannibalization.** AI Max expanded matching will pick up branded queries. Protect dedicated branded Search campaigns with brand exclusions on the AI Max campaign (Section 5, lever 2).
- **Reporting credit inflation.** AI Max "takes credit" for queries that exact/phrase keywords were already winning, inflating its apparent performance (adalysis.com). Evaluate incrementally (experiment, Section 10), not on raw in-platform attribution.
- **Performance Max overlap and auction priority (Google-official, confirmed).** AI Max gets no special auction advantage; it sits in the same serving-priority ladder as standard Search and PMax (support.google.com/google-ads/answer/2756257; blog.google). The ladder: (1) a keyword whose text is identical to the query wins, including over PMax (match type does not matter, identical text does); (2) phrase/broad keywords "(including AI Max)" and search themes identical to the query are the next, equal tier; (3) AI relevance for non-identical matches; (4) Ad Rank is the final tiebreaker. So when neither AI Max nor PMax has an identical-text keyword for a query, **neither wins by rule and the higher Ad Rank serves**: that is the mechanism by which AI Max and PMax self-cannibalize on Search inventory. Critical caveat: the exact-match protection only holds when the Search campaign is actually eligible (not budget-capped, not limited by status or targeting). Optmyzr's 503-account study found Search/PMax overlap in about 91% of accounts across all match types, largely because the "protected" Search campaign was ineligible and PMax filled the void (optmyzr.com/blog/is-pmax-cannibalizing-search). AI Max being **Search-only** is the one structural fact that limits the overlap: it never collides with PMax on Shopping, YouTube, or Display. Keep proven converters as exact-match keywords in dedicated Search so they retain priority, and keep those Search campaigns funded so they stay eligible.
- **Reshuffle, not just growth.** Independent data (Section 6) shows much of AI Max's reported lift is redistributed from existing coverage, not net-new. Measure account-wide incrementality via the built-in experiment, not raw in-platform credit.
- **DSA replacement.** AI Max is the sanctioned successor to DSA. Dynamic ad groups migrate into standard ad groups with all three features on by default. Voluntarily migrate early with your controls pre-set rather than accepting Google's defaults at the February 2027 forced upgrade (ACA and campaign-level broad match auto-upgrade earlier, September 2026). Do not run AI Max, DSA, and PMax on the same query space at once; it fractures conversion data and starves Smart Bidding.

---

## 8. Reporting and measurement

- **Search-terms "Source" column** distinguishes query origin. API enum values: `AI_MAX_KEYWORDLESS` (matched from site/landing-page content, no keyword) and `AI_MAX_BROAD_MATCH` (AI-expanded from an existing keyword) (developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/ai-max-reporting).
- **"Search terms and landing pages from AI Max"** view lists triggering queries plus the headlines, landing pages, campaigns, and ad groups in the full ad journey (support.google.com/google-ads/answer/16470459). Landing-pages report adds a "Selected by" column.
- Reporting view `ai_max_search_term_ad_combination_view` gives performance by combinations of search term, headline, and landing page.
- **`expanded_landing_page_view` (`expanded_final_url`)** is the audit surface for final URL expansion: it shows which pages FUE actually sent traffic to. Pull it regularly and add URL exclusions for any wrong or thin pages.
- The Keywords report adds two aggregate rows, "AI Max expanded matches" (broad expansion) and "AI Max landing page matches" (keywordless/asset), and the Asset report marks AI-built assets "Google AI" in the "Added by" column.

Measurement blind spots (know what we cannot audit):
- **Never sum metrics across `search_term_view` and `ai_max_search_term_ad_combination_view`.** Many AI Max terms appear in both; they are different dimensions on the same traffic and summing double-counts.
- **Low-volume search terms are omitted** from the search-terms report for privacy; their clicks are in campaign totals but hidden from the terms view, so term reports will not reconcile to campaign totals (ppc.land clarification on attribution discrepancies).
- **Match-type evaluation is muddied.** AI Max treats keywords as broad regardless of specified match type, so if a campaign runs only exact/phrase keywords, AI Max traffic gets attributed to those restrictive types and per-match-type analysis breaks (adalysis.com). Workaround: add broad-match variants so AI Max traffic separates cleanly in reporting.

---

## 9. Google Ads API representation

Support landed in **Google Ads API v21** (~August 2025) and persists in v22+ (ppc.land; developers.google.com/google-ads/api/reference/rpc/v23/Campaign.AiMaxSetting). Key fields:

- Enable at campaign level: `campaign.ai_max_setting.enable_ai_max = true`.
- `campaign.ai_max_setting.bundling_required` controls whether AI Max must be on to modify text customization and brand-list controls.
- Search term matching per ad group: `AdGroup.AiMaxAdGroupSetting.disable_search_term_matching` (disable per ad group even when the campaign has AI Max on).
- Asset automation: `campaign.asset_automation_settings` with `AssetAutomationStatusEnum` (`OPTED_IN` / `OPTED_OUT`) for types `TEXT_ASSET_AUTOMATION` and `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION`.
- Text guidelines: `campaign.text_guidelines` (term exclusions max 30 chars each, up to 25 items; messaging restrictions max 300 chars each, up to 40 items).
- URL controls: `webpage.conditions` (URL_CONTAINS, PAGE_TITLE_CONTAINS) with `negative=TRUE` at campaign level.
- Reporting: `segments.search_term_match_source` (values `ADVERTISER_PROVIDED_KEYWORD`, `AI_MAX_BROAD_MATCH`, `AI_MAX_KEYWORDLESS`) on `search_term_view`; the `ai_max_search_term_ad_combination_view` (search term x headline x landing page); and `expanded_landing_page_view.expanded_final_url` for auditing where final URL expansion actually sent traffic. `campaign.ai_max_setting.enable_ai_max` and `.bundling_required` are queryable to read state.
- Page feeds: create an `AssetSet` of type `PAGE_FEED` and link it to the campaign via `CampaignAssetSetService` BEFORE adding ad-group `webpage` inclusions that reference it (hard ordering dependency). `bundling_required` also imposes ordering: enable AI Max before or in the same mutate as the related control writes.
- Experiments: `ADOPT_AI_MAX` experiment type (v24.1) runs the built-in 50/50 test.

Version history: v21 (Aug 2025) added the core `ai_max_setting`, the match-source segment, and the combination view; v23.1 (Feb 2026) added `text_guidelines`; v24.1 (May 2026) added the `ADOPT_AI_MAX` experiment type. Current line is v24. **Unverified field paths (confirm against the live v24 field reference before coding):** the exact brand-list resource (likely a campaign/ad-group criterion referencing an account-level brand list asset set) and the location-of-interest field/criterion type are documented as features but not pinned to field names in the API docs. Never sum metrics across `search_term_view` and `ai_max_search_term_ad_combination_view`; they are different dimensions on the same traffic and will double-count.

**Our tooling status (updated 2026-07-08):** `ads_mcp/creation/search.py` now supports enabling AI Max at campaign creation via an `ai_max` config block on `propose_google_ads_search_campaign` / `commit_google_ads_search_campaign`. Verified against the installed google-ads v31 (API v24) client: `campaign.ai_max_setting.enable_ai_max` (bool) and `.bundling_required` (enum `AiMaxBundlingRequired`: NOT_REQUIRED / REQUIRED, **not a bool** despite the field name), `campaign.asset_automation_settings[]` with `asset_automation_type` (`TEXT_ASSET_AUTOMATION`, `FINAL_URL_EXPANSION_TEXT_ASSET_AUTOMATION`) and `asset_automation_status` (`OPTED_IN` / `OPTED_OUT`), `campaign.text_guidelines.term_exclusions` (repeated string), and `AdGroup.ai_max_ad_group_setting.disable_search_term_matching` (bool). The `ai_max` block covers: enable, bundling_required, text_customization, final_url_expansion (defaults OFF), and term_exclusions; the per-ad-group `disable_search_term_matching` flag is on `SearchAdGroupConfig`.

Now in tooling too (added 2026-07-08, verified against google-ads v31 / API v24):
- **Page feeds + URL exclusions.** `ads_mcp/creation/search.py` supports `page_feed_urls` (a `PAGE_FEED` `AssetSet` linked via `CampaignAssetSet`) and `url_exclusions` (negative campaign `webpage` criteria, operand URL / operator CONTAINS) both at creation and, for an existing campaign, via `add_page_feed_to_campaign(...)` (MCP tool `configure_google_ads_ai_max_scope`, which can also flip FUE on in the same mutate). Ordering is handled: AssetSet is created before its AssetSetAssets and the CampaignAssetSet. Enable final URL expansion only after the page feed + URL exclusions are in place (the tool enforces the sequence when `enable_final_url_expansion=True`).
- **Built-in 50/50 experiment (`ADOPT_AI_MAX`).** `ads_mcp/creation/experiments.py` implements propose -> commit (creates the Experiment in SETUP + control/treatment arms, `dry_run` supported) -> schedule (starts it; the spend step, gated) -> end. MCP tools: `propose_/get_/commit_/schedule_/end_google_ads_ai_max_experiment`. `Experiment.type_ = ADOPT_AI_MAX`, `ExperimentArm` control vs treatment with `traffic_split`, `campaigns=[base]`; scheduling is a long-running op via `ExperimentService.schedule_experiment`.

Still NOT in tooling (do these in the UI / a separate API pass): the account-level **brand list** (Shared Library; creating one requires AI Max on, and a brand missing from Google's library takes 3-6 weeks), **messaging_restrictions** and the natural-language **AI Brief**.

---

## 10. Launch playbook for a multi-brand e-commerce account

Order of operations, tightest controls first:

1. **Qualify the campaign.** Search type, conversion Smart Bidding, healthy conversion tracking, enough conversion volume (Section 3). If not, fix those first; do not enable AI Max to rescue a starved or mistracked campaign.
2. **Lock brand controls.** Exclude our store brand and any manufacturer brand that has its own campaign; include the brand(s) this campaign should own.
3. **Lock negatives.** Apply the account/campaign negative keyword lists; add obvious off-intent and competitor-mismatch negatives.
4. **Scope destinations.** Decide on final URL expansion. If keeping it on, constrain with a page feed and URL exclusions so expansion stays in the right collections. If landing-page control matters more than reach, turn text customization off (which turns expansion off) and keep only search term matching.
5. **Set Text Guidelines and an AI Brief.** Exclude off-brand terms and forbidden claims; write a short natural-language brief describing the brand voice and what to feature (lead with real best-sellers per the sales-driven rule).
6. **Pick the test campaign narrowly.** Start on one mid-volume, non-brand generic Search campaign, never account-wide and never a brand campaign. Consider enabling search term matching only first, adding text customization and final URL expansion after brand safety and landing-page routing check out.
7. **Bid Max Conversion Value with tROAS held at the true target.** Do not loosen the target for the test. Expanded, lower-intent, lower-AOV queries make the algorithm pay more per conversion, so a loose tROAS lets AI Max chase cheap low-value volume and efficiency craters. Manual CPC is not an option (it disables search term matching).
8. **Launch as an experiment.** Use the built-in 50/50 experiment (Experiments > Campaign features and settings > AI Max; API `ADOPT_AI_MAX`) rather than flipping the whole campaign, so lift is measured incrementally against the non-AI-Max control. Run a 14-day minimum, ideally 4 weeks. Note you cannot create the built-in experiment if the campaign uses legacy features, targets Display, uses a Portfolio bid strategy or Shared Budget, or already has an active experiment. Start modest on budget through the learning ramp.
9. **Monitor weeks 1 to 4, about twice as often as standard Search:** the search-terms report with the Source column (kill irrelevant AI-Max queries, especially competitor and off-catalog terms); `expanded_landing_page_view` (add URL exclusions for wrong or thin pages); Search Partner Network conversion rate versus Google Search (exclude SPN if it is a fraction); AOV and CPA/ROAS versus the control arm; and branded cannibalization.
10. **Exit and rollback criteria.** Pause if CPA runs more than ~20% over the control arm after four weeks with no improving trend; roll back if competitor or brand terms dominate impressions and negatives cannot contain it; disable final URL expansion if landing-page mismatches are frequent; revert if ROAS falls materially below target with no AOV or value recovery. Because it is a toggle, rollback is turning the features off, not deleting the campaign.

---

## 11. Setup steps (reference)

UI (support.google.com/google-ads/answer/15909989): existing campaign -> Campaigns -> Settings -> select the Search campaign -> "AI Max" section -> opt in -> choose which features. New campaign: opt in on the "AI Max" page during creation. Bulk: Settings -> select campaigns -> Edit -> "Change AI Max settings". Search term matching must be on at campaign level before it can be toggled per ad group.

API (Section 9): set `campaign.ai_max_setting.enable_ai_max = true`, configure `asset_automation_settings`, `text_guidelines`, brand lists, and `webpage.conditions` URL controls, on v21+.

---

## 12. Sources

Google official: blog.google/products/ads-commerce/google-ai-max-for-search-campaigns/, .../dsa-upgrade-to-ai-max-2026/, .../ai-max-new-features/; support.google.com/google-ads/answer 15910187 (how it works), 15909989 (setup), 15910366 (about), 16230205 (final URL expansion), 16470459 (reporting), 15913066 (FAQ); developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/ (getting-started, ai-max-reporting) and reference/rpc/v23/Campaign.AiMaxSetting; support.google.com/google-ads/editor/answer/16320144. Reputable PPC: Search Engine Land (overview 462923, match-type 465612, DSA delay 480049, smec study 470928), Smarter Ecommerce, Adalysis (search-term reporting), PPC.land (API v21, branded controls, Text Guidelines global, attribution clarification, DSA delay), WordStream, Karooya, Lunio, Optmyzr, Search Engine Journal, Digiday, Marketing Dive. Full URLs are recorded in the research briefs archived for the 2026-07-07 build.

---

## 13. Self-improvement clause

AI Max is changing rapidly (features, defaults, forced-migration dates, and API fields have all shifted since launch, and Google's own performance framing has been revised down). This skill will rot if left static. Standing rules:

- **Re-verify before each build.** Before creating or enabling an AI Max campaign, confirm the current defaults, control levers, eligibility, API field names, and migration dates against Google Ads Help and the API docs. Do not trust this file's specifics blindly; treat them as a starting point and check the "Last researched" date at the top.
- **Record what you learn.** When a build surfaces a new fact (a changed default, a new control, an API field that differs from Section 9, a real performance or cannibalization result on our accounts), update this file and bump the "Last researched" date.
- **Consult Adam before promoting evergreen claims.** Genuinely account-agnostic optimization lessons belong in [PPC_ADVISOR.md](PPC_ADVISOR.md); asset-craft lessons in [ASSET_CREATION_SKILL.md](ASSET_CREATION_SKILL.md). Propose the addition, say why it is evergreen, and append on Adam's confirmation, per the self-improvement rules in those files.
- **Keep the evidence honest.** When adding performance claims, label Google-official versus vendor-reported versus our own measured results, and keep the independent/skeptical data (like the retail CPA-increase finding) visible so we do not over-trust the headline numbers.
- **When our creation tooling gains AI Max support**, update Section 9 and register any new MCP tool per the change-routing table in [CLAUDE.md](CLAUDE.md).
