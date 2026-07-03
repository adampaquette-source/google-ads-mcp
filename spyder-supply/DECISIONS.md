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

## Build decisions (2026-06-21, in CAMPAIGN_BUILD_SPEC.md)
- **D9.** Two Standard Shopping campaigns, gated to mutually-exclusive `custom_label_2` values: **Campaign A `spyder_curated`** (in-stock, >= $15, demand categories; 191 SKUs; priority High, $30/day, Manual CPC $0.45) and **Campaign B `spyder_fallback`** (>= $5, not curated; 388 SKUs; priority Low, $10/day, Manual CPC $0.30). Sub-$5 (149 SKUs) get no label = advertised nowhere.
- **D10.** Branded Search = one campaign, ~11 ad groups grouped by Ahrefs demand cluster (hole saw kits, hole saws, arbors, drill bits, spade/wood bits, step bits, recip/saw blades, circular/jig/oscillating, Mach-Blue, impact/driver, brand catch-all), phrase + exact, each final-URL'd to its collection. Scraper + grout ad groups held until restocked (OOS).

## Build decisions (2026-07-03, campaigns created PAUSED)
- **D11 (Ratified/built).** Starter = **full 11-ad-group branded Search** ($10/day, Manual CPC $0.40) + **one curated Shopping campaign** ($30/day, Manual CPC $0.45, gate `spyder_curated`). Fallback Shopping (Campaign B) deferred. Adam builds the tool (D3 answered: yes) and publishes/enables as he sees fit. Created PAUSED in `9267883382`: Search `23999926235`, Shopping `23999925116`. Merchant Center = `5812518721`.
- **D12 (Ratified).** "Spyder" collides with Spyder paintball markers and Spyder ski apparel -> 18 campaign-level BROAD negatives (paintball, marker, ski, jacket, coat, snowboard, apparel, clothing, maserati, biturbo, spider, spiderman, game, victor, hoodie, vest, convertible). Three sub-brand keywords (`spyder mach blue`, `spyder mach-blue`, `spyder black series`) tripped Google's **"Guns" policy (EXEMPTIBLE)** and were dropped (~30/mo, negligible); revisit via a policy-exemption request if ever worth it. The productive `spyder mach blue drill bits` / `impact bits` were not flagged and stayed in.

## Search creation tool built (2026-07-03)
`ads_mcp/creation/search.py` + tools `propose/get/commit_google_ads_search_campaign` (API ref section 14). Follow-up: add optional policy-exemption support so exemptible violations (e.g. "Guns") don't hard-block a commit.

## Pending / to decide (build-time)
- **Hard prerequisites before Shopping serves:** MC misrepresentation flag cleared; DFW writing `custom_label_2` so `spyder_curated` has products; conversion tracking verified (Recording conversions, true purchases Primary, reconciled vs Shopify).
- Curated/fallback boundary (the $15-floor vs category-based question) still open -- only matters when the DFW `spyder_curated` roster is loaded; the campaign gate is agnostic to membership.
- Fallback Shopping campaign (Campaign B) -- add later once curated is serving.
