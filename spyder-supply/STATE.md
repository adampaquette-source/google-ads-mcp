# Spyder Supply: Working State

Last updated: 2026-06-19. The live snapshot of where this account stands. Fast-changing. For durable facts see `NOTES.md`.

## Current stage
**Strategy RATIFIED (2026-06-19); blocked on build-time prerequisites.** Path approved (D4-D7): Standard Shopping (curated high-AOV feed) + small Branded Search first, PMax deferred to Stage 2. Google Ads account **`9267883382`** is live, empty. Shopify side is the **`weather-guard-store`** key (Truck Box Outlet rebranded in place), accessible; Spyder catalog ACTIVE, old line DRAFT. Before anything can serve: (1) feed/Merchant Center wired to `9267883382`, (2) conversion tracking verified, (3) curated Stage 1 SKU roster + daily budget set.

## What is live in the account
Nothing -- new account `9267883382` is empty (0 campaigns). The predecessor TBO account `3174244337` is separately ENABLED with old truck-box history (not yet wound down).

## What is proposed (not pushed) -- see STRATEGY.md + DECISIONS.md D4-D7
**Path: Standard Shopping + small Branded Search first; PMax deferred to Stage 2.** Cold account, zero history -> PMax-first is the classic burn-budget failure mode; cheap $0.20-0.50 CPCs make Shopping a cheap first-conversion engine. Stage 1 = curated high-AOV Shopping feed (kits + carbide hole saws, gated via DFW custom_label) on Manual CPC / Max Clicks + a tiny branded Search campaign (`spyder hole saw kit`, `spyder drill bits`, etc.). Stage 2 (after ~15-30 conv) = Max Conversion Value -> tROAS ~333%+, then PMax + a category-Search test. Awaiting the cold-start research brief (reconcile budget/thresholds) + Adam approval.

## What is proposed (not pushed)
Nothing yet.

## Last action
2026-06-19: Ran brand + keyword research (Ahrefs) and catalog pull. Confirmed catalog families (hole saws/kits, drill+spade bits, arbors, blades, scrapers). Branded demand ~3,600/mo (hero: `spyder hole saw kit` 1,100, `spyder drill bits` 800); CPCs $0.20-0.50; AOV reality check (kits are the ad-worthy SKUs). Wrote STRATEGY.md + DECISIONS.md (D1-D7). Launched a separate background research task on cold-start ad strategies. Proposed the Shopping+Branded-Search-first path (D4).

## Next action
1. **DONE: path approved (D4-D7) + cold-start research** (`COLD_START_RESEARCH.md`) reconciled into STRATEGY.md and its evergreen distillation promoted into `PPC_ADVISOR.md` (D8).
2. **Build-time prerequisites (Adam / setup):** wire feed + Merchant Center to `9267883382`; verify conversion tracking (Recording conversions, true purchases Primary, reconcile vs Shopify).
3. **On prerequisites done:** set curated Stage 1 roster (kits + carbide hole saws) + daily budget (~$25-40/day Manual CPC), then propose/commit the Standard Shopping campaign PAUSED via the existing pipeline, and decide build-vs-UI for the branded Search campaign.
3. On approval: set the curated Stage 1 SKU roster + daily budget, wire the feed/Merchant Center to `9267883382` and confirm conversion tracking (the deferred prerequisites), then propose/commit the Standard Shopping campaign (PAUSED) via the existing pipeline, and decide build-vs-UI for branded Search.

## Account creation + billing (answer to Adam's 2026-06-19 question)
Create it **from inside the MCC** (Accounts > + > Create new account) so it is natively manager-owned and the service account inherits Standard access. For payment, during the new account's billing setup pick the **existing Google payments profile** rather than creating a new one -- a payments profile can back many Ads accounts, so it reuses the same business profile + funding source (card). If the MCC has consolidated/manager billing (monthly invoicing) enabled, the sub-account can bill straight through the manager. Claude cannot create the account or set up billing (account creation + payment entry are off-limits); Adam does it, then hands over the customer_id.

## Open questions / waiting on
- Spyder margin / AOV / target geo (for breakeven + bid floors).
- Predecessor account `3174244337` (TBO) + its Merchant Center feed: wind down vs repurpose? Is a Merchant Center account linked to the new `9267883382` yet, and where does the Spyder product feed point?

## Changelog (newest first)
- 2026-06-19: Adam RATIFIED the path (D4-D8). Promoted cold-start evergreen distillation into PPC_ADVISOR.md. Account now blocked only on build-time prerequisites (feed/MC wiring, tracking verify, roster/budget).
- 2026-06-19: Cold-start research brief completed (COLD_START_RESEARCH.md) and reconciled into STRATEGY.md; path confirmed; graduation gates + budget math pinned. Proposed promoting the evergreen distillation to PPC_ADVISOR.md (pending Adam).
- 2026-06-19: Brand + keyword research + catalog pull. Wrote STRATEGY.md (keyword tables, AOV reality check, path recommendation) + DECISIONS.md (D1-D7). Proposed Shopping + Branded-Search-first, PMax deferred. Launched background cold-start research task.
- 2026-06-19: Confirmed Shopify access via existing `weather-guard-store` key (rebrand in place). Spyder catalog ACTIVE (50+), old line DRAFT. Trailing-365d sales $11,436.91 all from old truck-box line, zero Spyder. Store-key blocker resolved. Logged economics, quirks, predecessor-account `3174244337` question.
- 2026-06-19: Google Ads account `9267883382` created under the MCC and confirmed accessible (empty). Onboarding item 1 done; blocker is now the Shopify store key.
- 2026-06-19: Added context: Spyder brand power tool accessories, replacing Truck Box Outlet, spydersupply.com live, no ads account yet. Recorded the account-creation/billing guidance.
- 2026-06-19: Folder scaffolded; flagged as pending provisioning.
