# Pro Work Supply: Working State

Last updated: 2026-06-17. The live snapshot of where this account stands. Fast-changing. For durable facts see `NOTES.md`. For the full staged plan and roster see `STAGE1_PROPOSAL.md`. For the decision log see `DECISIONS.md`.

## Current stage
Stage 1 (learning) is fully specced. The build spec is written: `STAGE1_BUILD_SPEC.md` (Shopping-only, $25/day start, pause PMax-A, 60-SKU custom-label feed gate). **Nothing has been pushed to the account.** Awaiting Adam's go + the 4 pre-flight confirmations.

## What is live in the account (verified 2026-06-17)
- 7 campaigns exist; **6 are PAUSED**. Only **"PMax-A - ALL SKUS"** is ENABLED: Maximize Conversion Value at a **700% tROAS**, $40/day budget, ~$0.70/day actual spend, **0 conversions in the last 30 days**. Classic cold-account starvation.
- The commodity-term bleed came from the now-PAUSED manual-CPC Shopping campaigns (Bottom/Mid/Top Funnel = $1,054, **72% of lifetime spend, 0 conversions**). Worst offenders are already off.
- Trailing 12 months: **$1,468.93 spent, 4,643 clicks, 1 conversion ($145.20), ROAS 0.10.** The single conversion fired through PMax-A.

## What is proposed (not pushed)
The Stage 1 learning plan in `STAGE1_PROPOSAL.md`, with the 2026-06-17 decisions folded in:
- **Pause PMax-A at launch** (D17) so it does not compete with the new campaign.
- **Shopping ONLY in Stage 1** (D20). One **Standard Shopping** campaign, **Maximize Conversions (no ROAS target)**, feed gated to a curated ~60-SKU 3M roster (Groups A through H). No Search campaign in Stage 1.
- **Budget: start $25/day, scale to $40/day once early CVR is non-zero** (D21). Expect sub-breakeven ROAS during a 60 to 90 day learning run.
- **Stage 2:** introduce the 3M-category Search campaign (D18 strategy, proworksupply.com), switch Shopping to Target ROAS starting ~400% **stepping toward an ~800% goal** (D19), and test PMax on proven winners. Trigger: ~30 conversions / 30 days.

## Last action
2026-06-19: Built the MCP tooling (permission granted). New: Standard Shopping propose/commit (`ads_mcp/creation/shopping.py` + 3 server tools) and DataFeedWatch lookup-sheet tools (`update_dfw_lookup_table` / `get_dfw_lookup_table` + `ads_mcp/sheets.py`). Mutate builder validated offline against the live client. Updated GOOGLE_ADS_API_REFERENCE.md (§12), CLAUDE.md routing, .env.example (DFW_LOOKUP_SHEET_ID), and STAGE1_BUILD_SPEC.md execution path.

## Next action
1. **DONE 2026-06-19:** DFW lookup Google Sheet created + shared with the service account; `DFW_LOOKUP_SHEET_ID` in `.env`; 60-SKU roster seeded to tab **PWS_Stage1** (sku -> custom_label_0 = pws_stage1_3m), verified by readback. Sheet ID `1F8uQYzjLg3GK3ZDG6Xq5l6KpsyiNXy9LJvoRbZ20OHs`.
2. **Adam, in DataFeedWatch:** add that sheet/tab (PWS_Stage1) as a lookup source matched on `sku`, writing `custom_label_0`. Confirm the feed output shows the 60 items labeled.
3. **Adam pre-flight:** confirm MC link, conversion action primary, geo/language (US/English), feed match key (sku).
4. On approval: I `propose_…` then `commit_google_ads_standard_shopping_campaign` (pauses PMax-A + creates the PAUSED Shopping campaign atomically). Then Adam enables. No account changes without approval.
5. Future lookup-table updates go through the `update_dfw_lookup_table` MCP tool (needs the session restart to load).

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
