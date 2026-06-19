# Pro Work Supply (PWS) - Decision Log

Account: Pro Work Supply (`1532947017`) | Shopify: `wood-shop-outlet` | Breakeven ROAS: 500%

This is the running, ratified decision log for the PWS account rebuild. Append new decisions with a date; do not rewrite history. Newest at the bottom of each section.

## Hard rules (standing)
- **No account changes without explicit approval.** No campaign, feed, budget, or bid change is pushed to the account until Adam says go. Everything lives here as a proposal first.
- **Margin:** flat 20% assumed (Shopify cost-per-item is not exposed by the connector; revisit with a cost export for Stage 2 profit ranking).
- **No em dashes in user-facing output** (project convention).

## Ratified decisions

| # | Date | Decision | Rationale / source |
|---|---|---|---|
| D1 | 2026-06-15 | Fixed MCP connector configs: `google-ads` and `shopify-toolup` used `${HOME}` instead of hardcoded usernames | Dropbox folder is shared across two machines with different macOS usernames (`adam.paquette` vs `adampaquette`); absolute paths broke cross-machine |
| D2 | 2026-06-16 | **Store identity = 100% 3M.** Woodworking-tool concept fully replaced from domain down; old woodworking collections/resources are unpublished and disregarded | Adam |
| D3 | 2026-06-16 | **Margin 20-25%, use flat 20% where cost is empty. Breakeven ROAS ~500%** | Adam |
| D4 | 2026-06-16 | **Stage 1 budget = $40/day Shopping + ~$5/day branded Search.** Floor option $25/day | Buys ~30 conversions/mo at ~$0.40 CPC / ~1% CVR, enough for Smart Bidding to learn |
| D5 | 2026-06-16 | **Stage 1 bidding = Maximize Conversions (no ROAS target).** Impose tROAS only in Stage 2 after ~30 conversions banked | Account has ~1 lifetime conversion; a 500-700% tROAS starves the campaign (current PMax self-throttles to ~$0.70/day) |
| D6 | 2026-06-16 | **Channel = Standard Shopping for Stage 1, not PMax** | No conversion history; PMax leaks to Display/video. Build clean conversion data on Shopping first, test PMax in Stage 2 |
| D7 | 2026-06-16 | **Lead with high-demand 3M lines, not commodity.** Exclude scotch brite / steel wool / duct tape type terms | 31,307 historical search terms -> 0 conversions; demand + AOV live in PPE (respirators, hearing, welding, hard hats) per Ahrefs |
| D8 | 2026-06-16 | **DRAFT and genuinely non-sellable items: excluded from feed** | Adam confirms DRAFT items are already excluded |
| D9 | 2026-06-16 | **No MAP constraint on these SKUs** - free to advertise discounted prices | Adam |
| D10 | 2026-06-16 | **Backorder / out-of-stock sellable items STAY in the feed.** Do not gate to in-stock only. Assume a lowered CVR for backorder items. Items do not auto-drop when OoS | Adam: nearly all catalog is sellable when OoS. Replenishment monitoring deferred to a later phase |
| D11 | 2026-06-16 | **Scope includes all PPE and Fall Protection** as fair game for the roster | Adam |
| D12 | 2026-06-16 | **All PWS project artifacts live in `pro-work-supply/`** with a running decision log (this file) | Adam |
| D13 | 2026-06-16 | **OoS inclusion bar (refines D10):** out-of-stock items are included only if they clear a HIGHER bar - high demand (strong Ahrefs line volume and/or Top-decile 3M/Amazon sales rank) AND excellent price vs market. In-stock items keep the normal criteria. **Speedglas welding helmets are explicitly included** regardless. | Adam (R3) |
| D14 | 2026-06-16 | **AOV floor: exclude any item priced $10.00 or below.** Advertise only items priced above $10. | Adam (R1) |
| D15 | 2026-06-16 | **Backorder availability flagging is NOT a project concern** - Adam owns the feed side; do not treat it as a blocker. | Adam (R2: "don't worry about it") |
| D16 | 2026-06-16 | **Stage 2 trigger confirmed: ~30 conversions / 30 days** before switching Shopping from Maximize Conversions to Target ROAS. | Adam |
| D17 | 2026-06-17 | **Pause the live "PMax-A - ALL SKUS" campaign when Stage 1 launches.** It is the only ENABLED campaign; leaving it on risks auction overlap and dirties the clean conversion signal Stage 1 is built to produce. | Adam |
| D18 | 2026-06-17 | **Stage 1 Search targets high-demand 3M category terms we are strong in ("3M [widget type]", e.g. 3M respirator, 3M peltor, 3M full face respirator), NOT the store name "pro work supply"** (store-name brand demand is near zero). Canonical public domain is **proworksupply.com**. Supersedes the "pro work supply variants" framing in STAGE1_PROPOSAL.md. | Adam |
| D19 | 2026-06-17 | **Stage 2 goal ROAS ~800% after volume is proven.** Path: Stage 1 Maximize Conversions (no target) -> Stage 2 Target ROAS starting ~400%, stepping up toward 800%. 800% clears the 500% gross breakeven with cushion for net costs (shipping, payment fees, returns). | Adam |
| D20 | 2026-06-17 | **Stage 1 is Shopping ONLY. Drop the Search campaign from Stage 1; introduce it in Stage 2** once there is conversion history and a tROAS. Concentrates 100% of budget and conversion signal into one learning campaign. The D18 3M-category-term strategy and proworksupply.com domain still govern the Stage 2 Search build; only the timing moves. A $5/day Maximize-Conversions Search campaign cannot reach the 15-30 conv/mo learning threshold (~333 clicks/mo) and would only fragment signal. | Adam |
| D21 | 2026-06-17 | **Stage 1 Shopping budget: start at the $25/day floor, scale to $40/day once early CVR is non-zero.** Replaces the flat $40/day. Rationale: Shopify shows only 15 sales / $1,422.80 across ALL channels in the trailing year, so the ~1% CVR assumption is unproven. Starting at the floor limits tuition while we get the first read on whether this is a traffic problem or a conversion problem; step up on signal. | Adam |
| D22 | 2026-06-19 | **Stage 1 bidding = Manual CPC, Claude-managed max CPC (start $0.55).** Supersedes D5's "Maximize Conversions." Forced by the platform: a validate_only matrix showed this cold account rejects every conversion-based strategy on Standard Shopping -- `maximize_conversions` and `maximize_conversion_value` -> OPERATION_NOT_PERMITTED_FOR_CONTEXT, `target_roas` -> NOT_ENOUGH_CONVERSIONS. Only Manual CPC and Maximize Clicks are permitted. Manual CPC chosen over Maximize Clicks for spend control on a low-CVR store; Claude owns the bid (Adam's call 2026-06-19). | Adam |
| D23 | 2026-06-19 | **Weekly Stage 1 ops (Claude-run):** (1) bid review -- move the single max CPC by impression share vs budget delivery; (2) roster pruning -- drop non-converting SKUs from the DFW lookup sheet, concentrate budget on converters; (3) **negative-keywords pass** -- pull Shopping search terms, add negatives for irrelevant / commodity / no-convert queries; (4) tripwire -- ~150+ clicks with 0 conversions over 2-3 weeks => pause for storefront CRO. **Stage 2 unlock:** when conversions clear NOT_ENOUGH_CONVERSIONS, switch to Maximize Conversion Value, then tROAS toward the 800% goal (D19). | Adam |

## Stage 1 campaign (created PAUSED 2026-06-19)
- Campaign `23958300224` "PWS | Shopping | Stage 1 Learning (3M Core)" -- Standard Shopping, Manual CPC, $25/day, PAUSED.
- Ad group `197719002237` "3M Core Roster" (SHOPPING_PRODUCT_ADS). Listing gate: `custom_label_2 = pws_stage1_3m` biddable @ $0.55, everything else excluded.
- PMax-A `23702140220` paused in the same atomic commit (D17). Audit row in `audit.db` (shopping_creation_log).
- Not yet enabled. Enable only after confirming the DFW feed is stamping `custom_label_2` on the 60 items.

## Verification finding (2026-06-17, from live account data)
- The account has 7 campaigns, not 1. Six are PAUSED; only **PMax-A - ALL SKUS** is ENABLED (Max Conversion Value, 700% tROAS, $40/day budget, ~$0.70/day actual spend, 0 conversions last 30 days).
- The commodity-term spend came from the now-PAUSED manual-CPC Shopping campaigns (Bottom/Mid/Top Funnel = $1,054, 72% of all spend, 0 conversions). Already off.
- The single lifetime conversion ($145.20) fired through PMax-A, so a purchase conversion action exists and has fired. Full conversion-action configuration (import source, primary status, captures all purchases) is **not yet verified** - needs the Google Ads Goals > Conversions screen. Recommended before Stage 1 launch.

## Operational consequence of D13 - Speedglas
- Complete Speedglas ADF welding helmets are all OoS today. ACTIVE OoS helmets (SKUs 850212 $170, 849985 $344, 850211 $636, 850014 $789) are included on a backorder basis.
- Two strong ADF helmets are in **DRAFT** (excluded by D8): 837170 9002NC ADF ($428), 835548 9100 ADF 9100XXi ($925). **To advertise them they must be published** and set to backorder availability. Merchandising action for Adam.
- Speedglas accessories/plates ($6-95 parts) stay excluded (AOV floor / low intent).

## "High demand + excellent price vs market" - measurement note
- High demand proxy available now: Ahrefs line volume + stored `3m_sales_rank_decile` / `amazon_sales_rank_decile` metafields.
- **Price vs market: no competitor-price data source is wired up yet.** Interim proxy = discount depth (compareAtPrice vs price) plus Adam's general "we are price competitive" stance. A true check needs a competitor price feed or manual spot-checks. Flagged for Stage 2 profit work.

## Recommendations - all resolved
- **R1: RATIFIED as D14** (exclude items priced $10.00 or below).
- **R2: CLOSED as D15** (Adam owns feed availability; not a project concern).
- **R3: RATIFIED as D13** (Speedglas included; OoS higher bar).

## Open questions
- **Conversion tracking: resolved as working.** The $145.20 Ads conversion maps to a real Shopify order (3M XC-DC Scotch-Brite disc, net sales $145.20 in the trailing-year report), so the purchase action fires correctly. A glance at Goals > Conversions to confirm primary status / import source is still worthwhile but not a blocker.
- **Store conversion capability is the live risk, now managed by D21** (staged $25 -> $40 budget). Shopify: 15 sales / $1,422.80 all channels, trailing year.
- All Stage 1 decisions are complete (D1-D21). Next step on Adam's go: write the exact campaign + feed-filter spec - now Shopping-only (D20), $25/day to start scaling to $40 (D21), pause PMax-A (D17).
