# Spyder Supply: Account Notes

Durable facts and standing rules for the Spyder Supply account. Update when a fact changes; this is the authoritative reference. For current working state see `STATE.md`.

Last updated: 2026-06-19.

Status: **ONBOARDING / greenfield.** New cold store flagged by Adam 2026-06-19. **Replacing Truck Box Outlet** (rebrand). Storefront is already live at **spydersupply.com**. No Google Ads account yet; not yet in the `shopify-toolup` server. Identifiers below fill in as it is provisioned.

## Identifiers
| Thing | Value |
|---|---|
| Google Ads account | **Spyder Supply, customer_id `9267883382`** -- created under MCC `7404361064`, status ENABLED, accessible via the service account (verified 2026-06-19, account empty / no campaigns). |
| MCC login_customer_id | `7404361064` |
| Shopify store key | **`weather-guard-store`** (env slug `TBO_STORE`) -- the Truck Box Outlet store, rebranded in place. Already in the `shopify-toolup` server; accessible (verified 2026-06-19). Same Shopify store, now Spyder. |
| Public storefront | **spydersupply.com** (live) |
| Store identity | **Spyder brand power tool accessories** (replaces Truck Box Outlet). Catalog: scrapers, hole saws, bi-metal reciprocating/demolition saw blades. Spyder products are ACTIVE (50+); old WeatherGuard truck-box catalog set to DRAFT (retiring). |
| Predecessor ads account | **Weather Guard Store, customer_id `3174244337`** (identifiers Truck Box Outlet / TBO), still ENABLED under the MCC. Holds truck-box ad history + likely a Merchant Center link. Default plan: start clean on the new Spyder account `9267883382` and wind down `3174244337` + its feed (the old history is irrelevant to Spyder). Decision pending Adam. |

## Economics
- Margin: TBD
- Breakeven ROAS: TBD (1 / gross margin as a floor; treat the real target above it for net costs)
- AOV floor: TBD (Spyder accessories -- blades, hole saws, scrapers -- are low-AOV; confirm before setting a floor)
- **Trailing 365-day store net sales: $11,436.91, but 100% from the OLD WeatherGuard/Knaack truck-box line (pack-rat parts, locks, gas springs, dividers). Zero Spyder sales yet** (Spyder catalog is brand new). Verified 2026-06-19 via shopify-toolup get_product_sales.
- **Store-conversion risk is LOWER than PWS:** this domain has a working, converting checkout (~$11.4k/yr on the old line), unlike PWS which barely converted. The open risk here is Spyder product-market fit on this domain, not cart capability.

## Hard rules
- No account changes without Adam's explicit approval.
- No em dashes in user-facing output.
- Use the local `shopify-toolup` MCP, never the cloud Shopify tools.

## Account quirks
- **In-place rebrand on one Shopify store.** `weather-guard-store` simultaneously holds the retiring WeatherGuard truck-box catalog (DRAFT) and the new Spyder catalog (ACTIVE). When pulling catalog/sales, filter to `vendor:Spyder` / `status:active` so the old line does not contaminate the read.
- **Two ads accounts share this one store:** old `3174244337` (TBO) and new `9267883382` (Spyder). Feed/Merchant-Center wiring must point the Spyder feed at the new account, not the old.

## Known gaps / data we do not have
- Margin / breakeven, target geo, AOV floor for the Spyder line.
- Whether the predecessor account `3174244337` and its Merchant Center feed should be paused/wound down, and whether a Merchant Center account is already linked to the new `9267883382`.
- Full active Spyder SKU count (search returned 50+, capped by limit; pull full count at diagnosis).
- Conversion tracking on the new `9267883382` (untested -- empty account). The store checkout converts, but the new Ads account's conversion action import must be confirmed before scaling.

## Decision log
None yet. Add a `DECISIONS.md` when decisions begin.
