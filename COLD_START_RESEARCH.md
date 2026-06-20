# Google Ads Cold-Start Strategy Research (evergreen reference)

Provenance: produced 2026-06-19 by a dedicated research task during Spyder Supply onboarding (the cold-start research that should have been done for Pro Work Supply). Account-agnostic. This is the raw, citable reference brief. The distilled rules are proposed for promotion into `PPC_ADVISOR.md` (Retained best practices) -- per the self-improvement rule, that promotion is PENDING Adam's consult, so this file is the holding place until then.

Reference economics used in the worked examples below: ~30% margin (breakeven ROAS ~3.3x), AOV ~$100-200 (the Spyder Supply profile).

---

# Google Ads Cold-Start Strategy for a Zero-History Ecommerce Account
**An evergreen, account-agnostic reference brief for the in-house PPC advisor**

*Scope: a brand-new Google Ads account, US-wide, no conversion history anywhere. Sources skew 2023-2026 because Smart Bidding and PMax behavior changed materially in that window (ECPC retirement March 2025; PMax search-term insights + negatives mid-2025).*

## 1. The Learning Phase on a Cold Account
- Smart Bidding enters "Learning" when newly created, when a setting changes, or when campaign composition changes (campaigns/ad groups/keywords/products added/removed). Does NOT apply to Manual CPC.
- Google's ceiling: up to ~50 conversion events or 3 conversion cycles to calibrate; prior conversion data speeds it up, so a zero-history account runs the full course.
- Practitioner shorthand by weekly volume: 50+/wk clears in ~5-7 days; 15-50/wk in ~7-14 days; under 15/wk takes 3+ weeks or never fully exits ("Learning limited").
- Corrections (accuracy):
  - tROAS genuinely starves a cold account; Google's hard eligibility floor is 15 conv / past 30 days (Search & Shopping) plus ~4 weeks of stable value reporting.
  - tCPA is technically PERMITTED with no history (Google's words); the "30 conv/30d" figure is an evaluation recommendation, not an activation gate. So "tROAS starves cold" is the strong claim; "tCPA literally fails" is not.
  - The API enum literally named `NOT_ENOUGH_CONVERSIONS` could NOT be verified in current public docs. The general failure is operational (starved delivery / "Learning limited"), not a rejected mutate. (NB: our own PWS validate_only test DID return real rejections on STANDARD SHOPPING specifically -- see the reconciliation note in spyder-supply/STRATEGY.md.)

## 2. The Cold-Start Bidding Ladder (ECPC retired for Search/Display Mar 31 2025)
- Rung 1 (zero conv): Manual CPC or Maximize Clicks. Google itself: a brand-new campaign should "use Maximize Clicks to build traffic and conversion data first."
- Rung 2 (cold automated, NO target): Maximize Conversions, or -- ecommerce-correct -- Maximize Conversion Value (no target), because plain Max Conversions is value-blind. Google floor: ~15 conv/30d before applying.
- Rung 3 (add a target): Target CPA first, then Target ROAS, set within 10-20% of observed average, never aspirational.
- Minority views: some stay manual up to 6 months; savvyrevenue moves to a loose tROAS sooner.

## 3. PMax vs Standard Shopping vs Search Cold (the central question)
- Google says PMax can run cold (search themes + audience signals substitute for history). Practitioners disagree for a TRULY new account.
- Practitioner consensus (Store Growers, Search Engine Land/Hopkins, SEJ/Adam): under $1k/mo or no history -> stay on Standard Shopping + Search; PMax needs ~30 conv/mo to exit learning, ~60 to thrive.
- Why Google's "PMax cold" claim is weakest for greenfield: Smart Bidding borrows query-level data across the account/MCC -- but a greenfield account's signal pool is empty, so there's nothing to borrow. Audience signals are a hint ("not hard targeting constraints"), not conversion data.
- Standard Shopping (Manual CPC / Max Clicks) = transparent, controllable first-conversion engine (full search-term visibility). Brand Search = cheapest highest-intent early conversions; run separately and EXCLUDE brand from PMax later so conversions don't inflate PMax ROAS.
- Recommended sequence: Standard Shopping (+ controlled brand/high-intent Search) on manual/clicks -> accumulate ~15-30+ conv -> graduate to PMax, feed-first, with brand exclusions.
- PMax cold risks: brand cannibalization / inflated ROAS (Optmyzr 503-account study: 97.26% had Search/PMax overlap; brand >30% of conv = "burning money"); budget burn with no signal; search-term blindspot (partially fixed ~Jun/Jul 2025 with Search Terms Insights + campaign-level negatives); fragmentation of thin conversion data.

## 4. Budget for Learning
- Synthesized heuristic (defensible, not a Google quote): min daily budget ~= (conversions needed to exit learning) x (expected CPA) / (learning window days). Example: 30 conv x $30 / 14 days ~= $64/day.
- Practitioner sizing rule: keep daily budget at 3-5x the intended CPA (Google's literal wording is only "comfortable spending up to 2x your average daily budget" -- a headroom statement, not a CPA multiplier). Aggressive view: up to 10x.
- For planning, take the HIGHER of the accumulation figure and the 3-5x-CPA figure.
- Too-thin budget -> data starvation -> "the learning phase may never end"; with a tight target, tCPA underdelivers rather than overshoots (quietly stalls). Watch for "Limited by budget."
- Cold accounts have no reliable CPA yet -> estimate from category benchmarks, run Max Conversions to discover the real number, size the budget once (changing it resets learning).

## 5. Staged Rollout / Graduation Triggers
Staircase: build signal cheaply -> graduate to a conversion-getting strategy -> add an efficiency target -> only then scale into PMax.

| Gate | Conversions | Purpose |
|---|---|---|
| Maximize Conversions floor | 15-20 / 30 days | exit Stage 1 |
| Enable Target CPA | 15 eligible / 30 recommended /30d | Stage 3 |
| Trust Target ROAS | 50+ / month (30 min) | Stage 3 |
| Launch PMax | 30+ / month, history first | Stage 4 |
| Learning recalibration | ~50 conv OR 3 cycles | all stages |
| Safe change size | <=20% budget/bid, wait ~1 week | avoid reset |
| Budget vs target | 3-5x daily CPA (min 2x) | avoid stalling |

- Set first target within 10-20% of historical; to un-throttle, loosen 15-20%; allow ~4 weeks after a switch to stabilize.

## 6. Common Cold-Start Failure Modes
1. Target ROAS/CPA too high (or used at all) too early -> starves the account.
2. Budget too thin to ever exit learning (default 3-5x target CPA/day).
3. Too many campaigns fragmenting limited data -> each operates blind; consolidate by shared objective.
4. Changing settings mid-learning resets the phase. The "keep changes <20%" rule is practitioner lore (matches Google's Display bid guidance only), not on Google's general learning page; if big changes are needed, make them all at once.
5. Launching PMax with no signal ("PMax shoots randomly"); no-history products read as risky and get zero impressions.
6. Impatience -- judging/changing before learning completes; don't judge before ~2 weeks (4-6 for thin cold accounts).
7. Conversion tracking not verified before launch. Confirm "Recording conversions," set only true purchases as Primary (micro-conversions as primary make Smart Bidding chase cheap low-value actions), reconcile 30-day Google-reported vs backend.

## Three caveats to carry forward
1. `NOT_ENOUGH_CONVERSIONS` API enum unverified in docs -> the cold failure is generally operational, not a rejected mutate. (Our PWS Standard Shopping test is the empirical exception -- see STRATEGY.md reconciliation.)
2. tCPA can start with no history (per Google); only tROAS has a hard 15-conv floor.
3. Present as ranges, not facts: the budget-vs-CPA multiplier (2x / 3-5x / 10x) and the "20% change resets learning" rule.

## Sources
Google official: learning period https://support.google.com/google-ads/answer/13020501 ; bid strategy statuses https://support.google.com/google-ads/answer/6263057 ; Maximize conversions https://support.google.com/google-ads/answer/7381968 ; Target CPA https://support.google.com/google-ads/answer/6268632 ; Target ROAS https://support.google.com/google-ads/answer/6268637 ; Max conversion value https://support.google.com/google-ads/answer/7684216 ; Smart Bidding signal pooling https://support.google.com/google-ads/answer/11095984 ; Getting started with PMax https://support.google.com/google-ads/answer/14951594 ; About PMax https://support.google.com/google-ads/answer/10724817 ; API bidding strategy types https://developers.google.com/google-ads/api/docs/campaigns/bidding/strategy-types ; API BiddingStrategyError https://developers.google.com/google-ads/api/reference/rpc/v15/BiddingStrategyErrorEnum.BiddingStrategyError

Practitioner: Store Growers tCPA https://www.storegrowers.com/target-cpa/ , tROAS https://www.storegrowers.com/target-roas/ , PMax guide https://www.storegrowers.com/performance-max-campaigns/ ; Optmyzr smart bidding https://www.optmyzr.com/blog/smart-bidding-strategies/ , PMax cannibalization study https://www.optmyzr.com/blog/is-pmax-cannibalizing-search/ ; Search Engine Land PMax playbook https://searchengineland.com/the-performance-max-playbook-best-practices-and-emerging-tactics-for-2024-439585 , smart bidding signals https://searchengineland.com/new-smart-bidding-features-in-google-ads-top-signals-for-target-roas-and-max-conversions-manager-account-level-seasonality-adjustments-and-more-348736 ; SEJ PMax hybrid https://www.searchenginejournal.com/performance-max-for-ecommerce-the-hybrid-strategy-thats-actually-working/571885/ , consolidation https://www.searchenginejournal.com/google-clarifies-its-stance-on-campaign-consolidation/567295/ ; smec Shopping alongside PMax https://smarter-ecommerce.com/blog/en/google-shopping/how-to-run-google-shopping-alongside-performance-max-in-2026/ ; savvyrevenue tROAS vs MaxConvValue https://savvyrevenue.com/blog/target-roas-vs-max-conversion-value/ ; JumpFly PMax search terms https://www.jumpfly.com/blog/visibility-in-performance-max-search-terms-negative-keywords/ ; groas.com learning 2026 https://www.groas.com/post/google-ads-smart-bidding-learning-period-2026-tcpa-vs-troas-strategy-guide , learning phase https://www.groas.com/post/google-ads-learning-phase-why-your-ai-takes-2-weeks-to-fail ; PPCChat/Ginny Marvin https://officialppcchat.com/2022/02/22/your-performance-max-questions-answered-by-ginny-marvin-of-google-ads/ ; Seer https://www.seerinteractive.com/insights/account-structure-smart-bidding ; PPC Mastery https://www.ppcmastery.com/newsletter/tpe-94-why-consolidation-is-the-key-to-success-with-google-ads ; jetfuel https://jetfuel.agency/google-ads-ecommerce-guide-2026/ ; Define Digital https://www.definedigitalacademy.com/blog/google-ads-bidding-strategies-in-2025-how-to-avoid-costly-mistakes-and-maximize-results

Unverified: PPC Hero "Running PMax Against Brand is a Waste" (403; thesis corroborated by Optmyzr). ALM Corp Feb-2026 API conversion-data change (third-party; verify against official release notes). No primary Mike Rhodes / Brad Geddes page surfaced for the specific cold-start progression.
