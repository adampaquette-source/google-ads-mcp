# Pro Work Supply: Account Notes

Durable facts and standing rules for the Pro Work Supply (PWS) account. Update when a fact changes; this is the authoritative reference. For the current working state see `STATE.md`. For the ratified decision log see `DECISIONS.md`. For the staged plan and full roster see `STAGE1_PROPOSAL.md`. `HANDOFF.md` is the original onboarding brief.

Last updated: 2026-06-17.

## Identifiers
| Thing | Value |
|---|---|
| Google Ads account | Pro Work Supply, customer_id `1532947017` |
| MCC login_customer_id | `7404361064` |
| Shopify store key | `wood-shop-outlet` (`wood-shop-outlet.myshopify.com`) |
| Public storefront | `proworksupply.com` (canonical). The myshopify subdomain `wood-shop-outlet.myshopify.com` is the backend store key. |
| Search brand strategy | Bid on high-demand **3M category terms** we are strong in ("3M [widget type]", e.g. 3M respirator, 3M peltor, 3M full face respirator), NOT the store name. Store-name brand demand is near zero (D18). |
| Store identity | 100% 3M. The old woodworking-tool concept was fully replaced from the domain down; old woodworking collections and resources are unpublished and disregarded (D2). |

## Economics
- **Margin:** flat 20% assumed. Shopify cost-per-item is not exposed by the connector, so true per-SKU margin is unknown (D3).
- **Breakeven ROAS:** 500% (derived from the 20% gross margin: 1 / 0.20). This is a gross floor; true net breakeven is higher once shipping, payment fees, and returns are counted.
- **Goal ROAS (Stage 2, after volume is proven):** ~800% (D19). This clears the 500% gross breakeven with cushion for net costs, which is why we target 800% rather than the gross floor.
- **AOV floor:** exclude any item priced $10.00 or below (D14).
- **Stage 1 budget:** Shopping only (D20). Start at the **$25/day floor, scale to $40/day** once early CVR is non-zero (D21). No Search campaign in Stage 1; Search (3M category terms, per D18) is introduced in Stage 2.

## Hard rules
- **No account changes without Adam's explicit approval.** Everything is a proposal first.
- No em dashes in user-facing output.
- Use the local `shopify-toolup` MCP for Shopify, never the cloud `claude.ai Shopify` tools.
- No MAP constraint on these SKUs; free to advertise discounted prices (D9).

## Account quirks
- Catalog is 9,283 SKUs, mostly commodity and mostly backordered.
- Items do not auto-drop from the feed when out of stock (D10). Replenishment monitoring is deferred to a later phase.
- **Campaign inventory (verified 2026-06-17):** 7 campaigns exist; 6 are PAUSED. Only **PMax-A - ALL SKUS** is ENABLED (Max Conversion Value, 700% tROAS, $40/day budget, ~$0.70/day actual spend, 0 conversions last 30 days). Classic cold-account tROAS starvation. The commodity-term bleed came from the now-PAUSED manual-CPC Shopping campaigns ($1,054 / 72% of lifetime spend, 0 conversions). PMax-A is paused at Stage 1 launch (D17).
- Classify each-vs-case from the product title `(N Pack)`, not the `each` tag (the tag is unreliable).
- Backorder items are assumed to convert at a lower rate than in-stock; out-of-stock SKUs are only included if they clear a higher demand-and-price bar (D10, D13). Speedglas welding helmets are explicitly included on backorder.

## Known gaps / data we do not have
- **Cost-per-item is not exposed by the Shopify connector.** Flat 20% margin is a stand-in. A SKU + cost export is needed for Stage 2 true-profit ranking.
- **No competitor-price data source is wired up.** D13's "excellent price vs market" test currently leans on discount depth plus Adam's stance. A real source is needed before scaling backorder SKUs.
- **Conversion-action configuration confirmed working (2026-06-17).** The single $145.20 Google Ads conversion maps exactly to a real Shopify order: the 3M XC-DC Scotch-Brite Clean and Strip disc, net sales $145.20 in the trailing-year Shopify sales report. So the purchase conversion action fires correctly for at least Ads-driven sales. (Primary status / GA4-vs-gtag import source still worth a glance on the Goals screen, but tracking is not the bottleneck.)
- **Store conversion capability is the real constraint (verified via Shopify 2026-06-17).** Trailing 365 days, ALL channels: only **15 product lines sold, $1,422.80 total net sales**. The store has essentially no proven conversion engine across any channel, not just Ads. The Stage 1 budget math assumed ~1% Shopping CVR; the demonstrated all-channel reality is far lower. This is the dominant risk to a $40/day learning run and should be weighed (store readiness / CRO) before funding it.

## Feed gate (DataFeedWatch, live 2026-06-19)
- Roster is gated by **`custom_label_2 = pws_stage1_3m`** (DFW field 2; _0/_1 reserved for other uses). The Shopping campaign must gate on index 2.
- DFW lookup table = Google Sheet `1F8uQYzjLg3GK3ZDG6Xq5l6KpsyiNXy9LJvoRbZ20OHs`, tab **PWS_Stage1**, columns `sku, custom_label_2`, 60 rows. Updated via the `update_dfw_lookup_table` MCP tool. Sheet must stay shared Anyone-with-link=Viewer (DFW reads) + Editor to the service account (MCP writes). See memory `datafeedwatch-feed-tool`.

## Decision log
See `DECISIONS.md` in this folder. D1 through D21 are ratified; Stage 1 decisions are complete.
