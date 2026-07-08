# Wasted Spend Remediation (problem-space skill)

Canonical knowledge for finding and eliminating wasted Google Ads spend across the MCC. Read this
FIRST whenever you work on: search-term waste, negative keywords, "we're spending on junk queries",
brand/competitor spend, PMax/Shopping query bleed, or tuning the waste-audit tooling. It is the
advisor layer; the executable procedure is `NEGATIVE_KEYWORD_AUDIT_SKILL.md` and the engine is
`ads_mcp/reporting/waste_audit.py`.

Synthesized 2026-07-07 from repo research (`REPORTING_RESEARCH.md` §2.3, `COLD_START_RESEARCH.md`,
`AI_MAX_SKILL.md`) plus a fresh 2025-2026 web research pass. Numbers flagged "verify" drift; confirm
on the live Google Help account-limits page before hard-coding.

Inherits the project hard rules: no account change without Adam's explicit approval; propose then
commit; no em dashes in user-facing output.

---

## 1. The core mental model: waste has several levers, pick the right one

"Add a negative keyword" is only one of several remediation levers, and often not the best one. Match
the lever to the failure mode:

| Failure mode | Best lever | Why |
|---|---|---|
| One irrelevant query bleeding spend | **Negative exact** | Surgical; blocks only that string |
| A recurring irrelevant phrase ("for sale", "how to make") | **Negative phrase** | Ordered multi-word block |
| A whole junk theme keyed on one word ("free", "used", "jobs", off-category root) | **Negative broad (single word)** | Theme kill switch; but over-blocks, human-review |
| Own-brand or competitor-brand queries | **Brand exclusion list** (not negatives) | Auto-covers misspellings + foreign scripts; Google recommends over negatives; saves negative budget |
| Universal junk that should die everywhere incl. PMax | **Account-level negative keywords** | One place, applies to Search + Shopping + PMax (cap ~1,000) |
| Converts, but below breakeven | **Bid / tROAS / budget**, not a negative | It works, just priced wrong; negativing throws away a converter |
| A whole converting theme worth its own treatment | **Structural** (asset group / campaign split) | Shopping/PMax have no keywords to "add"; you restructure |

Corollary: a term that **converts at or above breakeven is not waste**, even if expensive. Protect it.

## 2. When is a term actually wasteful (thresholds)

Practitioners converge on **relative thresholds tied to the account's own economics, not fixed click
counts** (Store Growers, Optmyzr, Seer; older fixed "20 clicks no conv" rules are considered too
aggressive for low-CR accounts).

- **Primary rule:** flag if `cost >= k x target_CPA` AND `conversions = 0` (k = 1 aggressive, 2-3
  conservative). You paid a full expected acquisition and got nothing.
- **Where no target CPA:** `clicks >= ceil(k / account_conversion_rate)` with 0 conversions, k = 2-3.
  Self-scaling: ~100 clicks at 2% CR, ~40-60 at 5%. This is the correct cross-account approach; a flat
  click/spend bar over- or under-fires depending on the account.
- **Absolute spend floor** to kill noise (ignore sub-$5 to $10 terms unless aggregated via n-gram).
- **Unprofitable converters (softer):** `CPA > 2x target` or `ROAS < breakeven` over enough clicks.
  Surface for review; usually fix bids, do not hard-negative.
- **Shopping/PMax run the bar higher** (feed-matched queries are noisier) and lean on n-gram + account
  /campaign-level negatives rather than surgical per-term exacts.

## 3. N-gram analysis: the technique that catches diffuse waste

Per-term rules miss the long tail: thousands of unique low-click queries, each below any threshold,
that collectively bleed real money through a shared bad word ("free", "manual", a competitor token).
The fix is **n-gram aggregation**: tokenize every search term into unigrams + bigrams, sum
cost/clicks/conv/value **per gram**, and rank grams with near-zero conversions above a spend floor.
This is the single highest-value automatable analysis for Shopping/PMax. Reference implementations:
Google Ads Scripts (Nils Rooijmans, Brainlabs), Optmyzr and Adalysis n-gram tools. A one-word offender
becomes a negative broad (human-reviewed); a bigram becomes a negative phrase.

## 4. Negative match-type mechanics (easy to get wrong)

- **Negatives do NOT match close variants, plurals, synonyms, or misspellings** (opposite of positive
  match). Expand variants explicitly. (support.google.com/google-ads/answer/2453972)
- **Negative broad** blocks queries containing **all** the words in **any order**. A single-word broad
  negative is powerful (kills a theme) but over-blocks; a two-word broad is narrower than people expect
  (needs both words). Always show the reviewer the set of currently-matched queries a broad negative
  would block, to catch collateral damage.
- **Negative phrase**: ordered, contiguous multi-word patterns. Preferred for multi-word themes.
- **Negative exact**: one specific query, no neighbors.

## 5. The canonical waste-category taxonomy

Bucket every candidate so the reviewer sees WHY it was flagged and can bulk-approve a category:
1. Competitor brands (policy-dependent). 2. Informational/research ("how to", "what is", "review",
"manual", "vs"). 3. Irrelevant verticals / wrong products. 4. Wrong purchase intent. 5. Free / no-cost.
6. Used / refurbished / rental. 7. Jobs / careers / education / training. 8. DIY / homemade / "how to
build". 9. Brand misspellings / wrong-brand (policy-dependent). 10. Geo out-of-area / wrong-language.
11. Adult / offensive / brand-safety. 12. Wholesale / bulk / trade (if B2C). 13. Near-match
wrong-product. Seed a shared "universal junk" list from published templates (WordStream, Klientboost,
Store Growers), then let n-gram find account-specific patterns. Soft-flag competitor + brand (never
auto-approve).

## 6. Channel-specific reality (2025-2026)

Different campaign types differ sharply in what you can see and what you can block. This matters because
the MCC is Shopping + PMax heavy.

**Search:** full per-term visibility via `search_term_view`; target-CPA-per-term rules apply cleanest.
Negatives at campaign, shared-list, and account level. Positive keywords exist.

**Standard Shopping:** feed-matched, noisier queries; `search_term_view` DOES return Shopping terms.
No positive keywords, so negatives are the only keyword lever. n-gram matters most here.

**Performance Max** (the big caveat):
- **`search_term_view` does NOT and never has returned PMax terms** (confirmed via the adwords-api
  Google Group). The UI has a per-term PMax search-terms report (data since March 2023), but **the API
  does not expose PMax cost per term.** The only API path is `campaign_search_term_insight`, which is
  **category-level (`category_label`), has NO `metrics.cost_micros`, and requires a single-campaign
  filter** (`REQUIRES_FILTER_BY_SINGLE_RESOURCE`). Do NOT assume `campaign_search_term_view` gives
  per-PMax-term cost - that is unverified and Google's own PMax guidance never points to it. Practical
  consequence: **a cost-based "wasted PMax query" tranche cannot be computed from the API.** Block PMax
  waste using the negative levers below (seeded from the Search/Shopping waste vocabulary and n-grams)
  plus brand exclusions, not per-term PMax spend.
- **PMax negatives (all three levers work and are API-writable):** account-level negative keywords
  (cap **1,000**) apply to PMax; campaign-level negatives for PMax were expanded to **10,000 per campaign**
  (March 2025); and **shared negative keyword lists attach to PMax too - GA 2025-08-07** (developer blog
  "Unlocking enhanced Performance Max targeting"; this closed the old allowlist-only gap). A single
  `NEGATIVE_KEYWORDS` shared set holds **5,000**. All PMax negatives affect Search + Shopping inventory
  only (not Display/YouTube/Discover within PMax).
- **Account-level negative keywords (the one-object blanket):** a `SharedSet` of type
  `ACCOUNT_LEVEL_NEGATIVE_KEYWORDS` + keyword `SharedCriterion` rows, linked to the account via a
  `CustomerNegativeCriterion.negative_keyword_list`. `CustomerNegativeCriterion` does NOT take raw
  keywords - the shared-set indirection is required. Cap 1,000, covers Search + Shopping + PMax + App +
  Smart + Local at once. Right for a curated universal-junk core; too small for a big account's full tail.
- **Brand exclusions are the recommended tool for brand/competitor blocking on PMax** (and Search):
  they auto-cover misspellings and foreign scripts, apply to Search + Shopping + YouTube-search
  inventory, and Google advises using them instead of burning negative budget on brand variants. They
  are "leaky", so pair with campaign-level negatives when tight control is needed. API-writable via a
  `SharedSet` of type `BRANDS` + `SharedCriterion` (BrandInfo) + a `CampaignCriterion` `brand_list`
  with `negative=true`.

**AI Max for Search** (bundle on Search campaigns, GA ~2025-2026): respects both campaign- AND
ad-group-level negatives (an advantage over PMax); expanded matching can spend on irrelevant queries
fast, so review search terms ~2x as often and lock brand/negative controls before enabling. All core
controls are API-writable (v21+): `campaign.ai_max_setting.enable_ai_max`, ad-group
`disable_search_term_matching`, asset-automation opt-outs.

## 7. Cautions

- **Do not over-negative, especially on Smart Bidding / PMax.** An Optmyzr study of 24,702 PMax
  campaigns found 58% saw flat-or-better performance with NO exclusions; over-restriction starves the
  algorithm. Block clearly irrelevant / non-converting terms, not everything.
- **Human-in-the-loop is the validated pattern.** Suggest-then-approve; never auto-apply single-word
  broad negatives. (This is exactly the propose -> review -> commit design already in the tooling.)
- **Brand exclusions are "leaky"** and may need a dedicated brand Search/Shopping campaign to catch the
  traffic you pull out of PMax.
- **Respect list limits** (verify live): per-campaign 10,000; shared list 5,000; shared lists/account
  ~20; account-level negatives ~1,000. When proposals exceed a cap (e.g. a big account produces >1,000),
  prioritize by rolled-up spend.

## 8. Cadence

Weekly for high-spend / Tier 1 accounts; biweekly-to-monthly for low-spend; **gate on accumulated
spend/clicks, not the calendar**, so thin-data accounts produce fewer proposals rather than bad ones.
Manual per-term review is reduced under Smart Bidding but not dead; automated detection + human-approved
negatives is more valuable than ever.

## 9. Positive-side harvesting is mostly deprecated (2025-2026)

Harvesting converting terms into exact-match / SKAGs is largely outdated under Smart Bidding + broad
match (Google already bids those queries; harvesting fragments data and starves the algorithm).
Surface high-spend converting terms only as a low-priority "consider a dedicated asset group / campaign"
flag; do not auto-add keywords. Genuine shift from ~2018 practice.

## 10. Current implementation status and known gaps

What exists today: the waste-audit engine `ads_mcp/reporting/waste_audit.py` (per-term
dictionary-root-collapse classifier into 6 tranches **plus n-gram diffuse-waste rollup**), per-account
config `waste_audit_config.json`, the control center Negatives tab (per-account picker), commit paths in
`ads_mcp/proposals/negatives.py` - a per-account **shared negative list** now attached to Search +
Shopping **+ PMax**, and an **account-level negative list** (`ACCOUNT_LEVEL_NEGATIVE_KEYWORDS` +
`CustomerNegativeCriterion`) - MCP tools `run_waste_audit` / `commit_negative_keywords` /
`commit_account_level_negatives`, and the monthly `google-ads-monthly-negatives` routine. Propose-only;
human approves and commits. See `NEGATIVE_KEYWORD_AUDIT_SKILL.md`.

Built 2026-07-07 (gap 1-3 remediation):
- **PMax now blocked** - shared negative list attaches to `PERFORMANCE_MAX` (GA 2025-08-07), and
  `commit_account_level_negatives` blankets Search + Shopping + PMax in one 1,000-cap object. Note:
  per-PMax-term *cost* is still not API-exposed (§6), so PMax proposals are seeded from the
  Search/Shopping waste vocabulary + n-grams, not PMax spend.
- **N-gram aggregation** - `flag_ngram` (default on) aggregates word-pairs over ALL of an account's
  terms and proposes only **two-word PHRASE** patterns with **zero total conversions** (so brands and
  real demand self-exclude), above `ngram_min_spend`, spanning `ngram_min_terms`+ distinct terms, and
  <25% brand/model spend. Part/model numbers and configured `brand_terms` are excluded. Single-word
  BROAD n-grams are intentionally not proposed (a lone product noun over-blocks on a broad catalog); a
  unigram concentration filter is the parked fallback. Rows carry real conv/value.
- **Economics-scaled threshold** - default zero-conv bar is **$50 spend or 20 clicks**; `target_cpa` +
  `zero_conv_cpa_mult` scale it to `k x target CPA` when configured.
- **Chaff controls** - raised defaults + the zero-total-conv n-gram rule cut a first all-accounts pass
  from ~5,900 proposals to ~600. Negatives tab tranches are collapsible; each row shows conv + value;
  a per-row **Protect** action adds the term to the account protect list so it never resurfaces.

Known gaps still open (prioritized):
1. **Brand tranches use negatives, not brand exclusions.** `competitor_brand` (and brand-language) are
   proposed as negatives; brand exclusion lists are the recommended, misspelling/foreign-robust tool
   (§6). Fix: route brand/competitor tranches to a `BRANDS` SharedSet + `brand_list` campaign criterion.
2. **Thin category taxonomy.** 6 tranches (+ngram) vs the 13-category standard (§5); informational /
   free / used / jobs / DIY / adult / wholesale are lumped into `zero_conv_spend` or `non_branded`. Fix:
   dictionary-driven category tagging + a seeded universal-junk list.
3. **Uniform monthly cadence + partial limit guards.** Best practice is weekly for high-spend, gated on
   accumulated data (§8). Account-level commit respects the 1,000 cap (spend-prioritized); per-campaign
   /shared-list caps (5,000 / 10,000) are not yet guarded in the commit.
4. **No target-architecture layering in the UI.** The commit picks shared-list vs account-level per
   call; there is no automatic Layer 1 (account universal junk) / Layer 2 (themed shared) / Layer 3
   (campaign) routing. Operator chooses.

## Sources
Repo: `REPORTING_RESEARCH.md` §2.3, `COLD_START_RESEARCH.md`, `AI_MAX_SKILL.md`. Web (2025-2026):
support.google.com/google-ads (negative match types /answer/2453972, account-limits /answer/6372658,
account-level negatives, brand settings /answer/13721847, PMax search terms report /answer/16327396);
developers.google.com/google-ads/api (search_term_view, campaign_search_term_view v21+,
campaign_search_term_insight v19+, shared-sets BRANDS, AI Max getting-started); searchengineland.com
(PMax negatives raised to 10k Mar 2025 /google-ads-expands-negative-keyword-limits-pmax-453154; PMax
search terms Apr 2025; brand settings 452578); optmyzr.com (n-gram, 24,702-campaign exclusion study,
cannibalization study); storegrowers.com (search-terms report, brand lists, n-gram); blog.google
(new PMax features 2025, AI Max May 2025); jumpfly.com, smarter-ecommerce.com, adalysis.com,
wordstream.com, seerinteractive.com. Numeric limits should be re-confirmed on the live Google Help
account-limits page before hard-coding.
