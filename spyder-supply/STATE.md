# Spyder Supply: Working State

Last updated: 2026-07-12. The live snapshot of where this account stands. Fast-changing. For durable facts see `NOTES.md`.

## Current stage
**Starter campaigns CREATED (PAUSED) 2026-07-03.** Both live in account `9267883382`, not serving:
- **Search** `23999926235` "Spyder | Search | Branded" -- SEARCH, Manual CPC $0.40, **$10/day**, **11 ad groups / 45 keywords / 11 RSAs**, 18 campaign negatives (paintball/ski/car/arachnid to dodge the Spyder-brand collisions). Free-shipping-over-$99 in copy. Needs neither MC nor DFW -> can be enabled first.
- **Shopping** `23999925116` "Spyder | Shopping | Curated (Core)" -- SHOPPING, Manual CPC $0.45, **$30/day**, gated `custom_label_2 = spyder_curated` (root SUBDIVISION + biddable UNIT + excluded everything-else, verified). Merchant Center **`5812518721`** (linked; flagged for misrepresentation -> cannot serve until cleared).
- Both validated via `validate_only` before commit. Config artifacts: `starter_search_campaign.json`, `starter_shopping_campaign.json`. Proposals 80029a71 (search) / f381a04b (shopping), committed.

**DFW `custom_label_2` lookup CONFIGURED + saved 2026-07-03** on the Spyder Google Shopping channel (DFW shop 156280, channel 340159), mirroring PWS: rule `Use lookup table` -> input `sku` -> `Add from URL` (Spyder tab CSV export `.../export?format=csv&gid=1369536402`), `Only IF sku is in list [same URL]`, ELSE leave empty. Live preview confirmed values flowing from the sheet. Data is in the shared DFW sheet's **`Spyder` tab** (gid 1369536402; PWS uses the first tab, gid 2073384052). Labels reach MC `5812518721` on the next feed refresh.

**Before serving (Adam publishes as he sees fit):** (1) MC misrepresentation flag cleared, (2) **DONE - DFW writing `custom_label_2`** (curated/fallback), (3) conversion tracking verified. Search can go live independent of MC/DFW.

## What is live in the account
Nothing -- new account `9267883382` is empty (0 campaigns). The predecessor TBO account `3174244337` is separately ENABLED with old truck-box history (not yet wound down).

## Build spec is written (2026-06-21) -- see CAMPAIGN_BUILD_SPEC.md
Three campaigns specced and ready to push once the prereqs clear: **Campaign A** curated Standard Shopping (191 in-stock demand SKUs >= $15, gate `custom_label_2=spyder_curated`, $30/day Manual CPC $0.45, priority High); **Campaign B** fallback Standard Shopping (388 SKUs >= $5, gate `spyder_fallback`, $10/day Manual CPC $0.30, priority Low); **Campaign C** branded Search (~11 ad groups by demand cluster, phrase/exact, ~$8/day). Sub-$5 (149 SKUs) advertised nowhere. Rosters + DFW lookup persisted: `spyder_dfw_lookup.csv` (579 rows), `spyder_curated_roster.csv`, `spyder_fallback_roster.csv`. Catalog snapshot: 728 active Spyder SKUs, 455 in stock.

## What is proposed (not pushed) -- see STRATEGY.md + DECISIONS.md D4-D7
**Path: Standard Shopping + small Branded Search first; PMax deferred to Stage 2.** Cold account, zero history -> PMax-first is the classic burn-budget failure mode; cheap $0.20-0.50 CPCs make Shopping a cheap first-conversion engine. Stage 1 = curated high-AOV Shopping feed (kits + carbide hole saws, gated via DFW custom_label) on Manual CPC / Max Clicks + a tiny branded Search campaign (`spyder hole saw kit`, `spyder drill bits`, etc.). Stage 2 (after ~15-30 conv) = Max Conversion Value -> tROAS ~333%+, then PMax + a category-Search test. Awaiting the cold-start research brief (reconcile budget/thresholds) + Adam approval.

## What is proposed (not pushed)
Nothing yet.

## Last action
2026-06-19: Ran brand + keyword research (Ahrefs) and catalog pull. Confirmed catalog families (hole saws/kits, drill+spade bits, arbors, blades, scrapers). Branded demand ~3,600/mo (hero: `spyder hole saw kit` 1,100, `spyder drill bits` 800); CPCs $0.20-0.50; AOV reality check (kits are the ad-worthy SKUs). Wrote STRATEGY.md + DECISIONS.md (D1-D7). Launched a separate background research task on cold-start ad strategies. Proposed the Shopping+Branded-Search-first path (D4).

## Next action
0. **DONE (2026-07-03): Standard Search creation tool built** (`ads_mcp/creation/search.py`, tools `propose/get/commit_google_ads_search_campaign`, API ref section 14). Validated against `9267883382` via `validate_only`. Merchant Center id for the Shopping campaign = **`5812518721`** (flagged for misrepresentation, being fixed -> Shopping can build PAUSED but cannot serve until cleared). Pivot to a lean STARTER: one curated Shopping + one branded Search (hero ad groups), not the full 11 yet.
1. **DONE: full build spec** (`CAMPAIGN_BUILD_SPEC.md`) + rosters/DFW lookup persisted. Catalog pulled (728 active Spyder SKUs), segmented (curated 191 / fallback 388 / excluded 149), branded Search ad groups defined against Ahrefs demand.
2. **Build-time prerequisites (Adam / setup), still the only blockers:** (a) Merchant Center feed live for `9267883382` -> capture merchant_id; (b) DFW writing `custom_label_2` from the Spyder lookup sheet; (c) conversion tracking verified.
3. **Adam's build-time confirmations:** budget split ($30/$10/~$8), max-CPC caps ($0.45/$0.30), curated price floor ($15 vs $10/$20), branded-Search build-vs-UI, free-shipping verbiage for RSAs.
4. **On prereqs + confirmations:** load DFW lookup, `validate_only`, then propose/commit Campaign A, B, then build/launch Campaign C -- all PAUSED. Enable only on Adam's go.
3. On approval: set the curated Stage 1 SKU roster + daily budget, wire the feed/Merchant Center to `9267883382` and confirm conversion tracking (the deferred prerequisites), then propose/commit the Standard Shopping campaign (PAUSED) via the existing pipeline, and decide build-vs-UI for branded Search.

## Account creation + billing (answer to Adam's 2026-06-19 question)
Create it **from inside the MCC** (Accounts > + > Create new account) so it is natively manager-owned and the service account inherits Standard access. For payment, during the new account's billing setup pick the **existing Google payments profile** rather than creating a new one -- a payments profile can back many Ads accounts, so it reuses the same business profile + funding source (card). If the MCC has consolidated/manager billing (monthly invoicing) enabled, the sub-account can bill straight through the manager. Claude cannot create the account or set up billing (account creation + payment entry are off-limits); Adam does it, then hands over the customer_id.

## Open questions / waiting on
- MC `5812518721` misrepresentation flag: cleared yet? Serving on the Shopping campaign is blocked until it is.
- Conversion tracking on `9267883382`: still unverified (account has never served).
- Adam's go to enable the two PAUSED starter campaigns. Search `23999926235` needs neither MC nor DFW and can go live first.
- Predecessor account `3174244337` (TBO) + its old Merchant Center feed: wind down vs repurpose? Decision pending Adam. The Spyder feed now points at MC `5812518721` on the new account.

(Resolved and moved to `NOTES.md`: margin ~30% / breakeven 333%, AOV concentrated in kits, geo = US-wide, MC linkage. These were stale open questions from 2026-06-19.)

## Changelog (newest first)
- 2026-07-12: Housekeeping reconcile. Removed stale open questions already answered in NOTES.md since 2026-06-19 (margin/AOV/geo, MC linkage) and replaced them with the actual current blockers: MC misrepresentation clear, tracking verify, Adam's enable go, TBO wind-down decision. No account changes.
- 2026-07-03: Loaded the Spyder DFW lookup + configured `custom_label_2` on the Google Shopping channel (via Claude-in-Chrome), mirroring PWS (Use lookup table + Add from URL of the Spyder tab CSV export + Only IF sku is in list + ELSE empty). Wrote 579 rows to the `Spyder` tab of the shared DFW sheet via the service account. Saved successfully; preview confirmed. DFW prerequisite now DONE.
- 2026-07-03: Built the Standard Search creation tool (`ads_mcp/creation/search.py`, API ref section 14), then CREATED both starter campaigns PAUSED in `9267883382`: Search `23999926235` (11 ad groups/45 kw, full branded set) and Shopping `23999925116` (curated, gate `spyder_curated`, MC `5812518721`). 3 keywords (`spyder mach blue`/`mach-blue`/`black series`) dropped -- flagged EXEMPTIBLE under Google's "Guns" policy (Spyder = also a paintball brand); worth a policy-exemption feature later. MC linked but flagged for misrepresentation (serving blocked until cleared).
- 2026-06-21: Built the full campaign plan. Pulled + segmented the 728-SKU active catalog; wrote CAMPAIGN_BUILD_SPEC.md (two Standard Shopping campaigns curated/fallback + branded Search 11 ad groups), persisted rosters + DFW lookup CSVs. Ready to push once MC feed + DFW + tracking are live.
- 2026-06-19: Adam RATIFIED the path (D4-D8). Promoted cold-start evergreen distillation into PPC_ADVISOR.md. Account now blocked only on build-time prerequisites (feed/MC wiring, tracking verify, roster/budget).
- 2026-06-19: Cold-start research brief completed (COLD_START_RESEARCH.md) and reconciled into STRATEGY.md; path confirmed; graduation gates + budget math pinned. Proposed promoting the evergreen distillation to PPC_ADVISOR.md (pending Adam).
- 2026-06-19: Brand + keyword research + catalog pull. Wrote STRATEGY.md (keyword tables, AOV reality check, path recommendation) + DECISIONS.md (D1-D7). Proposed Shopping + Branded-Search-first, PMax deferred. Launched background cold-start research task.
- 2026-06-19: Confirmed Shopify access via existing `weather-guard-store` key (rebrand in place). Spyder catalog ACTIVE (50+), old line DRAFT. Trailing-365d sales $11,436.91 all from old truck-box line, zero Spyder. Store-key blocker resolved. Logged economics, quirks, predecessor-account `3174244337` question.
- 2026-06-19: Google Ads account `9267883382` created under the MCC and confirmed accessible (empty). Onboarding item 1 done; blocker is now the Shopify store key.
- 2026-06-19: Added context: Spyder brand power tool accessories, replacing Truck Box Outlet, spydersupply.com live, no ads account yet. Recorded the account-creation/billing guidance.
- 2026-06-19: Folder scaffolded; flagged as pending provisioning.
