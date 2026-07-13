# Spyder Supply: Account Notes

Durable facts and standing rules for the Spyder Supply account. Update when a fact changes; this is the authoritative reference. For current working state see `STATE.md`.

Last updated: 2026-07-12.

Status: **BUILT, PAUSED-ready.** Cold store, **replacing Truck Box Outlet** (in-place rebrand), storefront live at **spydersupply.com**. Starter campaigns (branded Search + curated Standard Shopping) created PAUSED 2026-07-03 in `9267883382`; DFW `custom_label_2` wiring done. Blocked on MC misrepresentation clear + conversion tracking verify + Adam's enable go. See `STATE.md`.

## Identifiers
| Thing | Value |
|---|---|
| Google Ads account | **Spyder Supply, customer_id `9267883382`** -- created under MCC `7404361064`, status ENABLED, accessible via the service account (verified 2026-06-19, account empty / no campaigns). |
| MCC login_customer_id | `7404361064` |
| Shopify store key | **`weather-guard-store`** (env slug `TBO_STORE`) -- the Truck Box Outlet store, rebranded in place. Already in the `shopify-toolup` server; accessible (verified 2026-06-19). Same Shopify store, now Spyder. |
| Public storefront | **spydersupply.com** (live) |
| Merchant Center | **`5812518721`** -- linked to `9267883382`; flagged for misrepresentation as of 2026-07-03 (Shopping cannot serve until cleared). |
| Starter campaigns (PAUSED) | Search `23999926235` "Spyder \| Search \| Branded"; Shopping `23999925116` "Spyder \| Shopping \| Curated (Core)" (gate `custom_label_2 = spyder_curated`). Created 2026-07-03. |
| Target geo | US-wide. |
| Store identity | **Spyder brand power tool accessories** (replaces Truck Box Outlet). Catalog: scrapers, hole saws, bi-metal reciprocating/demolition saw blades. Spyder products are ACTIVE (50+); old WeatherGuard truck-box catalog set to DRAFT (retiring). |
| Predecessor ads account | **Weather Guard Store, customer_id `3174244337`** (identifiers Truck Box Outlet / TBO), still ENABLED under the MCC. Holds truck-box ad history + likely a Merchant Center link. Default plan: start clean on the new Spyder account `9267883382` and wind down `3174244337` + its feed (the old history is irrelevant to Spyder). Decision pending Adam. |

## Economics (confirmed by Adam 2026-06-19)
- Margin: **~30%**.
- Breakeven ROAS: **~3.3x (333%)** = 1 / 0.30. Real target above it for net costs (shipping, returns) -- aim ~400%+ once proven.
- AOV: Adam's working assumption **$100-200**, BUT catalog pricing says that only holds for kits/baskets. Hero ad SKUs: 13-pc Rapid Core hole saw kit $81.20, 4" carbide hole saw $79.10, sets $12-30. Long tail of single hole saws $5-19, spade bits $2-3 that lose money sold solo. **Curate ads to the high-ticket SKUs.**
- CPCs (Ahrefs): **$0.20-0.50 across both brand and category terms** -- very cheap clicks, the key economic advantage for cold-start learning.
- **Trailing 365-day store net sales: $11,436.91, but 100% from the OLD WeatherGuard/Knaack truck-box line (pack-rat parts, locks, gas springs, dividers). Zero Spyder sales yet** (Spyder catalog is brand new). Verified 2026-06-19 via shopify-toolup get_product_sales.
- **Store-conversion risk is LOWER than PWS:** this domain has a working, converting checkout (~$11.4k/yr on the old line), unlike PWS which barely converted. The open risk here is Spyder product-market fit on this domain, not cart capability.

## Hard rules
- No account changes without Adam's explicit approval.
- No em dashes in user-facing output.
- Use the local `shopify-toolup` MCP, never the cloud Shopify tools.

## Brand (Spyder Products)
- Founded 2007 (the Spyder Scraper); value/innovation challenger brand in power-tool accessories. Competes vs category leaders Diablo, Milwaukee, Lenox, MK Morse -- not the category leader, so category-term Search on a no-authority new domain is tough; brand + Shopping are the stronger plays.
- Product families in the catalog: bi-metal + carbide hole saws, Rapid Core Eject hole saw KITS, spade/drill bits + arbors, recip ("Sawzall") blades incl. double-edged 3X3, scrapers, grout-out attachments.
- Branded search demand ~3,600/mo total, concentrated in `spyder hole saw kit` (1,100) and `spyder drill bits` (800). Full keyword table in STRATEGY.md.

## Account quirks
- **In-place rebrand on one Shopify store.** `weather-guard-store` simultaneously holds the retiring WeatherGuard truck-box catalog (DRAFT) and the new Spyder catalog (ACTIVE). When pulling catalog/sales, filter to `vendor:Spyder` / `status:active` so the old line does not contaminate the read.
- **Two ads accounts share this one store:** old `3174244337` (TBO) and new `9267883382` (Spyder). Feed/Merchant-Center wiring must point the Spyder feed at the new account, not the old.

## Known gaps / data we do not have
- Conversion tracking on the new `9267883382` (untested -- account has never served). The store checkout converts, but the new Ads account's conversion action import must be confirmed before scaling.
- Wind-down decision for the predecessor account `3174244337` (TBO) and its old Merchant Center feed. Pending Adam.

(Resolved since 2026-06-19: margin/breakeven/AOV confirmed (Economics above); geo = US-wide; MC `5812518721` linked (Identifiers above); full catalog pulled 2026-06-21: 728 active Spyder SKUs, 455 in stock.)

## Decision log
See `DECISIONS.md` (D1-D10). Path ratified by Adam 2026-06-19: Standard Shopping + branded Search first, PMax deferred to Stage 2.
