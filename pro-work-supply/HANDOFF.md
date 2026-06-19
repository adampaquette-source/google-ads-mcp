# Pro Work Supply (PWS) - Project Handoff

Last updated: 2026-06-17. Read this first, then `DECISIONS.md`, then `STAGE1_PROPOSAL.md`.

## TL;DR
Pro Work Supply is a Google Ads account that has never converted (1 sale on ~4,600 clicks / ~$1,470 over the trailing year). The fix is not a bidding tweak; it is a conversion-volume problem on a 9,283-SKU mostly-commodity catalog. The plan is to concentrate a capped budget on a curated ~60-SKU 3M roster so Smart Bidding can finally learn. All Stage 1 decisions are ratified (D1-D16). Nothing has been pushed to the account. The next action is to write the exact campaign + feed-filter build spec, on Adam's go.

## Identifiers
| Thing | Value |
|---|---|
| Google Ads account | Pro Work Supply, customer_id `1532947017` |
| Shopify store key | `wood-shop-outlet` (domain `wood-shop-outlet.myshopify.com`) |
| Store identity | 100% 3M. Old woodworking concept fully replaced and unpublished - disregard it (D2). |
| Margin | Flat 20% assumed (cost-per-item not exposed by the connector) |
| Breakeven ROAS | 500% |
| Stage 1 budget | $40/day Shopping + ~$5/day branded Search |

## Hard rules
- **No account changes without Adam's explicit approval.** Everything stays a proposal until he says go.
- No em dashes in user-facing output.
- Use the local `shopify-toolup` MCP for Shopify, never the cloud `claude.ai Shopify` tools.

## Connector setup (important - was broken, now fixed)
The Dropbox project folder is shared across two machines with different macOS usernames (`adam.paquette` here vs `adampaquette`), so any hardcoded absolute path in a shared config breaks on the other machine.
- `google-ads` server: project `.mcp.json` now uses `${HOME}/.local/bin/uv` (D1).
- `shopify-toolup` server: registered in user config with `${HOME}`-based paths. The other machine needs its own `claude mcp add` once (see chat history / DECISIONS.md D1). Confirm `uv` is at `~/.local/bin/uv` on that machine.
- Ahrefs connector is live and was used for demand sizing.

## The diagnosis (evidence)
- Trailing 12 months: $1,468.71 spent, 4,632 clicks, **1 conversion ($145.20)**, ROAS 0.10.
- All 31,307 historical search terms combined produced **0 conversions**; budget went to commodity terms (scotch brite, steel wool, duct tape).
- Current live campaign "PMax-A - ALL SKUS" runs Maximize Conversion Value at a **700% tROAS** across the whole catalog and self-throttles to ~$0.70/day. With no conversion history it cannot learn.
- Store-wide Shopify sales (all channels, trailing year): ~$1,400-1,800 across ~14-18 orders. Near-zero proven conversion rate.
- Ahrefs: real demand + workable AOV live in PPE (3m respirator 3,700/mo, 3m peltor 2,300, full face respirator 1,500, speedglas welding helmet 900). Abrasives have little branded search (Shopping-feed play only). CPCs are cheap ($0.30-0.60).

## The plan (Stage 1, 60-90 day learning run)
- **One Standard Shopping campaign**, **Maximize Conversions (no ROAS target)** - not PMax, not tROAS yet (D5, D6). A 500-700% target would starve it exactly like the current PMax.
- **Branded Search** ~$5/day, minimal (brand demand is near zero).
- **Feed = curated ~60-SKU roster** (see STAGE1_PROPOSAL.md), not all 9,283 SKUs.
- **Budget $40/day** - the level that buys ~30 conversions/mo at ~$0.40 CPC / ~1% CVR. Floor option $25/day. Expect sub-breakeven ROAS during learning; that is tuition.
- **Stage 2 (after ~30 conversions / 30 days, D16):** switch Shopping to Target ROAS (start ~400%, step to 500-600%), then test PMax on proven winners and widen the feed.

## Roster logic (how the ~60 SKUs were chosen)
Intersection of: proven demand (Ahrefs line volume + stored `3m_sales_rank_decile` / `amazon_sales_rank_decile` metafields), sellability, and price band above the AOV floor. Deliberate blend of high-AOV margin drivers (respirators, helmets, SRLs, Cubitron) and deep-stock recognizable conversion generators (N95s, earmuffs) to feed the algorithm volume during learning. Groups A-H are detailed in STAGE1_PROPOSAL.md.

## Decisions that govern the feed (all ratified)
- **D8:** DRAFT and non-sellable excluded.
- **D9:** No MAP constraint on these SKUs.
- **D10 + D13:** Backorder / OoS sellable items stay in, BUT an OoS item is only included if it clears a higher bar (high demand AND excellent price vs market). In-stock items use normal criteria. **Speedglas welding helmets are explicitly included** on backorder.
- **D14:** AOV floor - exclude any item priced $10.00 or below.
- **D15:** Feed availability flagging is Adam's concern, not a project blocker.
- Classify each-vs-case from the title `(N Pack)`, not the unreliable `each` tag.

## Known gaps / caveats
- **Cost-per-item is not exposed by the Shopify connector.** Flat 20% is used. For Stage 2 true-profit ranking, get a SKU+cost export.
- **No competitor-price data source** is wired up, so D13's "excellent price vs market" currently leans on discount depth + Adam's stance. Consider a real source before scaling backorder SKUs.
- **Thin inventory** per SKU (often 1-20). Items do not auto-drop when OoS (D10); replenishment monitoring is a later phase.
- **Backorder CVR** is assumed lower than in-stock; watch cost-per-conversion in the first 2-3 weeks and adjust the cap if learning stalls.

## Action items
- **Adam (merchandising, optional):** publish the two DRAFT Speedglas ADF helmets (SKU 837170 $428, 835548 $925) so they can be advertised. Other complete Speedglas ADF helmets are ACTIVE-OoS and already in the roster on backorder.
- **Next build step (on Adam's go):** write the exact campaign settings + the precise feed filter (SKU/tag/price logic implementing D8/D10/D13/D14) as a build spec. Still a proposal - no account changes without approval.

## Files in this folder
| File | Purpose |
|---|---|
| `HANDOFF.md` | This document. Start here. |
| `DECISIONS.md` | Ratified decision log (D1-D16). Append new decisions with a date; do not rewrite history. |
| `STAGE1_PROPOSAL.md` | The staged plan, budget math, and full ~60-SKU roster by group. |
