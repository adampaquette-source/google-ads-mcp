# Spyder Supply: Working State

Last updated: 2026-06-19. The live snapshot of where this account stands. Fast-changing. For durable facts see `NOTES.md`.

## Current stage
**Onboarding -- both Ads and Shopify access confirmed; ready for diagnosis once economics/geo context is in.** Google Ads account **`9267883382`** is live under MCC `7404361064`, ENABLED, accessible, empty. Shopify side is the **`weather-guard-store`** key (the in-place rebrand of Truck Box Outlet) -- already in the `shopify-toolup` server, accessible. Spyder catalog ACTIVE (50+ SKUs: scrapers, hole saws, recip/demo blades); old WeatherGuard truck-box catalog set to DRAFT. The store-key blocker is resolved. Remaining before a build plan: margin/AOV/geo for the Spyder line, and the decision on the predecessor account `3174244337` + Merchant Center.

## What is live in the account
Nothing -- new account `9267883382` is empty (0 campaigns). The predecessor TBO account `3174244337` is separately ENABLED with old truck-box history (not yet wound down).

## What is proposed (not pushed)
Nothing yet.

## Last action
2026-06-19: Confirmed Shopify access. The store is the existing `weather-guard-store` key (Truck Box Outlet, rebranded in place) -- no new key needed. Pulled catalog + trailing sales: Spyder line ACTIVE (50+ SKUs), old WeatherGuard line DRAFT; trailing-365d store net sales $11,436.91, all from the OLD truck-box line, zero Spyder sales yet. Recorded store key, economics, quirks, and the predecessor-account question in NOTES.

## Next action
Onboarding checklist:
1. **DONE:** Google Ads account `9267883382` created under MCC `7404361064` and accessible.
2. **DONE:** Shopify access confirmed (`weather-guard-store`).
3. **Need from Adam (context, light):** rough Spyder margin / AOV, target geo, and the call on the predecessor account `3174244337` + its Merchant Center feed (default: start clean on `9267883382`, wind down the old one).
4. **Then I run the cold-account diagnosis:** full active Spyder SKU count + demand sizing (Ahrefs on Spyder blade/hole-saw terms), confirm a Merchant Center feed is (or will be) linked to `9267883382` and conversion tracking imports, then propose a staged plan. Expect the cold-Shopping pattern (too cold for Smart Bidding -> Manual CPC / Maximize Clicks to start, validate with `validate_only`), BUT store-CVR risk is lower than PWS because this checkout already converts.

## Account creation + billing (answer to Adam's 2026-06-19 question)
Create it **from inside the MCC** (Accounts > + > Create new account) so it is natively manager-owned and the service account inherits Standard access. For payment, during the new account's billing setup pick the **existing Google payments profile** rather than creating a new one -- a payments profile can back many Ads accounts, so it reuses the same business profile + funding source (card). If the MCC has consolidated/manager billing (monthly invoicing) enabled, the sub-account can bill straight through the manager. Claude cannot create the account or set up billing (account creation + payment entry are off-limits); Adam does it, then hands over the customer_id.

## Open questions / waiting on
- Spyder margin / AOV / target geo (for breakeven + bid floors).
- Predecessor account `3174244337` (TBO) + its Merchant Center feed: wind down vs repurpose? Is a Merchant Center account linked to the new `9267883382` yet, and where does the Spyder product feed point?

## Changelog (newest first)
- 2026-06-19: Confirmed Shopify access via existing `weather-guard-store` key (rebrand in place). Spyder catalog ACTIVE (50+), old line DRAFT. Trailing-365d sales $11,436.91 all from old truck-box line, zero Spyder. Store-key blocker resolved. Logged economics, quirks, predecessor-account `3174244337` question.
- 2026-06-19: Google Ads account `9267883382` created under the MCC and confirmed accessible (empty). Onboarding item 1 done; blocker is now the Shopify store key.
- 2026-06-19: Added context: Spyder brand power tool accessories, replacing Truck Box Outlet, spydersupply.com live, no ads account yet. Recorded the account-creation/billing guidance.
- 2026-06-19: Folder scaffolded; flagged as pending provisioning.
