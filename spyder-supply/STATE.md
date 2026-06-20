# Spyder Supply: Working State

Last updated: 2026-06-19. The live snapshot of where this account stands. Fast-changing. For durable facts see `NOTES.md`.

## Current stage
**Onboarding -- ads account live (empty), now blocked only on the Shopify store key.** Google Ads account **`9267883382`** is created under MCC `7404361064`, ENABLED, and accessible via the service account (verified 2026-06-19: empty, no campaigns/data). Spyder brand power tool accessories, replacing Truck Box Outlet, storefront live at spydersupply.com. Remaining before diagnosis: add the (rebranded Truck Box Outlet) store to the `shopify-toolup` server and get its store key, plus margin/geo/history context.

## What is live in the account
Nothing known yet (account not yet visible).

## What is proposed (not pushed)
Nothing yet.

## Last action
2026-06-19: Confirmed the new Google Ads account `9267883382` is visible + queryable through the MCC via the service account (empty account). Recorded the customer_id in NOTES + the advisor registry.

## Next action
Onboarding checklist (what I still need before diagnosis can start):
1. **DONE:** Google Ads account `9267883382` created under MCC `7404361064` and accessible.
2. **Shopify:** add the store (rebranded Truck Box Outlet) to the `shopify-toolup` server's `stores.config.json` + `.env`; give me the store key. (This is the current blocker for diagnosis.)
3. **Context:** rough margin, target geo, and whether Truck Box Outlet had any ad history / Merchant feed worth migrating or disregarding.
Once 1-2 are done I run the standard cold-account diagnosis (trailing performance if any, conversion-tracking check, Shopify all-channel sales, Ahrefs demand) and propose a staged plan. Expect the same cold-Shopping pattern as PWS: too cold for Smart Bidding at first, so Manual CPC / Maximize Clicks to start (validate with `validate_only`).

## Account creation + billing (answer to Adam's 2026-06-19 question)
Create it **from inside the MCC** (Accounts > + > Create new account) so it is natively manager-owned and the service account inherits Standard access. For payment, during the new account's billing setup pick the **existing Google payments profile** rather than creating a new one -- a payments profile can back many Ads accounts, so it reuses the same business profile + funding source (card). If the MCC has consolidated/manager billing (monthly invoicing) enabled, the sub-account can bill straight through the manager. Claude cannot create the account or set up billing (account creation + payment entry are off-limits); Adam does it, then hands over the customer_id.

## Open questions / waiting on
- All of the onboarding checklist above.

## Changelog (newest first)
- 2026-06-19: Google Ads account `9267883382` created under the MCC and confirmed accessible (empty). Onboarding item 1 done; blocker is now the Shopify store key.
- 2026-06-19: Added context: Spyder brand power tool accessories, replacing Truck Box Outlet, spydersupply.com live, no ads account yet. Recorded the account-creation/billing guidance.
- 2026-06-19: Folder scaffolded; flagged as pending provisioning.
