# Pro Work Supply: Working State

Last updated: 2026-06-17. The live snapshot of where this account stands. Fast-changing. For durable facts see `NOTES.md`. For the full staged plan and roster see `STAGE1_PROPOSAL.md`. For the decision log see `DECISIONS.md`.

## Current stage
**Stage 1 LIVE (enabled 2026-06-19).** Campaign `23958300224` (Standard Shopping, Manual CPC $0.55, ~$25/day) is ENABLED and serving against `custom_label_2 = pws_stage1_3m` (DFW feed confirmed green); campaign + ad group + product ad all ENABLED. PMax-A stays paused. Bidding is Manual CPC (D22): account too cold for conversion-based Shopping bidding. Weekly ops (D23) clock starts now; first review ~2026-06-26.

## What is live in the account (as of 2026-06-19)
- **8 campaigns, ALL PAUSED.** Nothing is serving. The new `23958300224` "PWS | Shopping | Stage 1 Learning (3M Core)" (Standard Shopping, Manual CPC $0.55, $25/day, gate `custom_label_2=pws_stage1_3m`, ad group `197719002237`) is PAUSED awaiting enable. PMax-A `23702140220` was paused by the commit (D17). The 6 older campaigns remain paused.
- Trailing 12 months (pre-launch baseline): **$1,468.93 spent, 4,643 clicks, 1 conversion ($145.20), ROAS 0.10.** The commodity-term bleed came from the now-paused manual-CPC Shopping campaigns (72% of lifetime spend, 0 conv).

## What is proposed (not pushed)
The Stage 1 learning plan in `STAGE1_PROPOSAL.md`, with the 2026-06-17 decisions folded in:
- **Pause PMax-A at launch** (D17) so it does not compete with the new campaign.
- **Shopping ONLY in Stage 1** (D20). One **Standard Shopping** campaign, **Maximize Conversions (no ROAS target)**, feed gated to a curated ~60-SKU 3M roster (Groups A through H). No Search campaign in Stage 1.
- **Budget: start $25/day, scale to $40/day once early CVR is non-zero** (D21). Expect sub-breakeven ROAS during a 60 to 90 day learning run.
- **Stage 2:** introduce the 3M-category Search campaign (D18 strategy, proworksupply.com), switch Shopping to Target ROAS starting ~400% **stepping toward an ~800% goal** (D19), and test PMax on proven winners. Trigger: ~30 conversions / 30 days.

## Last action
2026-06-19: Committed the Stage 1 campaign (PAUSED) after fixing three platform issues the commit surfaced (required `contains_eu_political_advertising`; Shopping rejects conversion-based bidding on this cold account -> Manual CPC; Shopping rejects a language criterion). Made bidding configurable in `ads_mcp/creation/shopping.py`. Verified the campaign, ad group, budget, and listing-group gate. Pre-flight resolved by self-serve: Merchant Center `5748251237` (via product_link); primary purchase conversion = "Google Shopping App Purchase" (works).

## Next action
1. **First weekly ops pass ~2026-06-26 (D23):** bid review + roster pruning + negative-keywords pass + CRO tripwire. Decide manual vs scheduled task. Watch early: is it getting impressions/clicks, and are any conversions registering.
3. **Conversion-action tidy (optional):** secondary duplicate purchase actions ("Purchase", "Purchase (1)") exist alongside the primary; harmless for bidding, worth cleaning in Goals.
4. **Stage 2 unlock:** when conversions clear NOT_ENOUGH_CONVERSIONS, switch the campaign to Maximize Conversion Value (one propose/commit; bidding is now configurable), then tROAS toward 800%.

Done earlier 2026-06-19: built MCP tooling (Standard Shopping + DFW tools); DFW sheet created, shared, seeded (tab PWS_Stage1, sheet `1F8uQYzjLg3GK3ZDG6Xq5l6KpsyiNXy9LJvoRbZ20OHs`) and connected in DFW mapping `custom_label_2`.

## Open questions / waiting on
1. **RESOLVED (D17):** pause PMax-A at Stage 1 launch.
2. **PARTIALLY RESOLVED:** a purchase conversion action exists and has fired (the $145.20, via PMax-A), so tracking is not dead. Still confirm via Goals > Conversions that it imports all Shopify/GA4 purchases and is primary, before scaling $40/day. (Tools here cannot read conversion-action config; needs the UI.)
3. **RESOLVED (D18):** domain proworksupply.com; Search targets 3M category terms, not the store name.
4. **RESOLVED (D19):** Stage 2 goal ROAS ~800% (clears net breakeven with cushion); path is 400% stepping up.
5. **Open, merchandising (Adam's side, optional):** publish the two DRAFT Speedglas ADF helmets (SKU 837170 $428, 835548 $925) so they can be advertised.
6. **RESOLVED (D20):** Search dropped from Stage 1 (Shopping only); Search introduced in Stage 2.
7. **RESOLVED (D21):** Shopping budget starts at $25/day floor, scales to $40/day on non-zero CVR signal. Manages the store-CVR risk by limiting tuition until traffic-vs-CVR is read.
8. **Watch item (not a blocker):** store conversion capability. If the $25/day run shows near-zero CVR after the first 2-3 weeks, the bottleneck is the storefront, not the ads; pause and do store-readiness/CRO work before scaling.

## Changelog (newest first)
- 2026-06-19: ENABLED campaign `23958300224` (campaign + ad group + product ad). PWS is live for the first time with a coherent strategy. ~$25/day Manual CPC on the 60-SKU 3M roster.
- 2026-06-19: COMMITTED Stage 1 campaign `23958300224` (PAUSED) + paused PMax-A, atomically. Ratified D22 (Manual CPC, account too cold for Smart Bidding) and D23 (weekly ops incl. negative-keywords pass). Made bidding configurable in the tool. Verified structure. First push to the account.
- 2026-06-19: DFW lookup sheet seeded + connected. Discovered DFW maps **custom_label_2** (not _0); re-seeded sheet header to `custom_label_2`, updated build spec/NOTES to gate on index 2. Codified the DFW loop in memory. Pushed repo to GitHub (adampaquette-source/google-ads-mcp).
- 2026-06-19: Built MCP tooling: Standard Shopping propose/commit (creation/shopping.py, 3 tools) + DFW lookup-sheet tools (sheets.py, 2 tools). Validated the mutate builder offline. Docs updated (API ref §12, CLAUDE.md, .env.example, build spec). Pending: session restart + Adam's sheet/pre-flight setup, then propose/commit on approval.
- 2026-06-17: Wrote STAGE1_BUILD_SPEC.md (executable Shopping-only build spec). Current stage / last action / next action updated.
- 2026-06-17: Ratified D20 (Stage 1 Shopping only; Search to Stage 2) and D21 (budget $25/day scaling to $40 on signal). Updated NOTES, DECISIONS, STAGE1_PROPOSAL, STATE.
- 2026-06-17: Fixed Shopify MCP (root cause: not registered for this project on this machine + stale broken `.venv`). Registered `shopify-toolup` in project `.mcp.json` (needs session restart). Pulled trailing-year wood-shop-outlet sales: $1,422.80 / 15 products, all channels. The $145.20 Ads conversion maps to a real Shopify order, so tracking works; store conversion capability is the real constraint. Flagged Search-budget structure and store-CVR risk for decision.
- 2026-06-17: Verified live account. Ratified D17/D18/D19. Updated NOTES, DECISIONS, STAGE1_PROPOSAL. Resolved open questions 1/3/4; refined 2 with verification findings.
- 2026-06-17: Created NOTES.md and STATE.md under the PPC advisor markdown system.
- 2026-06-17: HANDOFF.md written; project handed off in a ready-to-spec state.
- 2026-06-16: Ratified D14 (AOV floor), D15 (feed availability is Adam's concern), D16 (Stage 2 trigger). All Stage 1 decisions closed.
- 2026-06-16: Ratified D13 (Speedglas included; OoS higher bar) and D8 through D12. Roster finalized at ~60 SKUs.
- 2026-06-16: Initial roster and structure drafted from Google Ads history, Shopify catalog, and Ahrefs demand.
