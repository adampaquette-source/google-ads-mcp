# Spyder Supply: Decision Log

Ratified decisions for the Spyder Supply account. Newest decisions appended. "Proposed" = awaiting Adam; "Ratified" = approved and binding. See `STRATEGY.md` for the research behind these and `NOTES.md` for durable facts.

## Context decisions (ratified 2026-06-19, from Adam)
- **D1 (Ratified).** Start clean on the new account `9267883382`. Ignore the predecessor TBO ads account `3174244337` (wind it down separately) and ignore all pre-transition Shopify sales.
- **D2 (Ratified).** Economics: ~30% margin -> breakeven ROAS ~3.3x (333%). AOV assumed $100-200. Geo: US-wide.
- **D3 (Ratified).** Feed wiring and conversion-tracking verification are deferred for now; focus first on brand/keyword research and campaign strategy. (These are still hard prerequisites before any campaign can serve.)

## Strategy decisions (RATIFIED 2026-06-19 by Adam)
- **D4 (Ratified).** Launch path: **Standard Shopping + a small Branded Search campaign first; defer PMax to Stage 2.** Rationale in STRATEGY.md (cold account + zero history makes PMax-first the classic failure mode; cheap $0.20-0.50 CPCs make Shopping a cheap first-conversion engine).
- **D5 (Ratified).** Curate the Stage 1 Shopping feed to high-AOV SKUs (kits, carbide hole saws, sets); keep sub-$10 single consumables out of the cold-start campaign because they lose money sold solo. Gate via the existing DFW custom_label pipeline.
- **D6 (Ratified).** Stage 1 bidding: Manual CPC (~$0.30-0.50) or Maximize Clicks; graduate to Maximize Conversion Value at **15-20 conv/30d**, then Target ROAS at **50+ conv/mo** (first target near observed, stepping toward ~333%+, above breakeven for net costs). Verify with `validate_only` before committing.
- **D7 (Ratified).** Stage 2 introduces PMax (fed by Stage 1 conversion history, **launched with brand exclusions**, at 30+ conv/mo) and a category-Search test; not before.
- **D8 (Ratified).** Cold-start research completed (`COLD_START_RESEARCH.md`) and its evergreen distillation promoted into `PPC_ADVISOR.md` (graduation gates, budget-for-learning, brand-exclusion-from-PMax, verify-tracking-before-launch, always-validate_only). Approved by Adam 2026-06-19.

## Pending / to decide (build-time)
- Daily budget for Stage 1 (Manual CPC has no learning phase; cheap CPCs mean ~$25-40/day buys enough clicks -- finalize when setting the roster).
- The specific curated SKU roster for the Stage 1 Shopping feed (kits + carbide hole saws + sets).
- Whether to build a branded-Search creation tool (none exists) or launch that campaign via the UI.
- **Hard prerequisites before serving:** feed/Merchant Center wired to `9267883382`, and conversion tracking verified (Recording conversions, true purchases as Primary, reconciled vs Shopify).
