# Spyder Supply: Working State

Last updated: 2026-06-19. The live snapshot of where this account stands. Fast-changing. For durable facts see `NOTES.md`.

## Current stage
**Onboarding, blocked on provisioning.** Spyder Supply (Spyder brand power tool accessories) is **replacing Truck Box Outlet**; storefront live at spydersupply.com. No Google Ads account yet; the Shopify store (rebranded Truck Box Outlet) is not yet in the `shopify-toolup` server. Folder scaffolded per the advisor system. Diagnosis starts once the ads account exists under the MCC and the store key is added.

## What is live in the account
Nothing known yet (account not yet visible).

## What is proposed (not pushed)
Nothing yet.

## Last action
2026-06-19: Created the account folder (NOTES.md + STATE.md) and registry row. Confirmed Spyder Supply is absent from both the MCC account list and the Shopify store list.

## Next action
Onboarding checklist (what I need before diagnosis can start):
1. **Create the Google Ads account under the MCC** (`7404361064`) so the service account inherits access and it shares your payment profile (see the creation/billing note below). Then it appears in `list_google_ads_accounts` automatically.
2. **Shopify:** add the store (rebranded Truck Box Outlet) to the `shopify-toolup` server's `stores.config.json` + `.env`; give me the store key.
3. **Context:** rough margin, target geo, and whether Truck Box Outlet had any ad history / Merchant feed worth migrating or disregarding.
Once 1-2 are done I run the standard cold-account diagnosis (trailing performance if any, conversion-tracking check, Shopify all-channel sales, Ahrefs demand) and propose a staged plan. Expect the same cold-Shopping pattern as PWS: too cold for Smart Bidding at first, so Manual CPC / Maximize Clicks to start (validate with `validate_only`).

## Account creation + billing (answer to Adam's 2026-06-19 question)
Create it **from inside the MCC** (Accounts > + > Create new account) so it is natively manager-owned and the service account inherits Standard access. For payment, during the new account's billing setup pick the **existing Google payments profile** rather than creating a new one -- a payments profile can back many Ads accounts, so it reuses the same business profile + funding source (card). If the MCC has consolidated/manager billing (monthly invoicing) enabled, the sub-account can bill straight through the manager. Claude cannot create the account or set up billing (account creation + payment entry are off-limits); Adam does it, then hands over the customer_id.

## Open questions / waiting on
- All of the onboarding checklist above.

## Changelog (newest first)
- 2026-06-19: Added context: Spyder brand power tool accessories, replacing Truck Box Outlet, spydersupply.com live, no ads account yet. Recorded the account-creation/billing guidance.
- 2026-06-19: Folder scaffolded; flagged as pending provisioning.
