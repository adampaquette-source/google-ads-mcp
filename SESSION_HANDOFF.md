# Session Handoff (precompaction) — 2026-06-19

A snapshot for continuing this work in a fresh context. Read `CLAUDE.md` first (project bible), then this. For account detail, read the per-account `STATE.md` / `NOTES.md` / `DECISIONS.md`. This doc is a synthesis + pointers, not the source of truth.

## TL;DR of this session
1. Stood up a **PPC advisor markdown system** (`PPC_ADVISOR.md` + per-account `NOTES.md`/`STATE.md` + registry + maintenance clause in `CLAUDE.md`).
2. Fixed the **Shopify MCP** (`shopify-toolup`): it was unregistered on this machine + had a stale `.venv`. Registered in project `.mcp.json`, rebuilt venv. Live now.
3. Diagnosed and **launched Pro Work Supply (PWS) Stage 1**: a Standard Shopping campaign, now LIVE.
4. Built **new MCP tooling**: Standard Shopping propose/commit (`ads_mcp/creation/shopping.py`) and DataFeedWatch lookup-sheet tools (`ads_mcp/sheets.py`).
5. Wired the **DataFeedWatch feed loop** (Google Sheet lookup table → custom_label → feed gate).
6. Created the **GitHub repo** `adampaquette-source/google-ads-mcp` (private) and pushed everything.
7. Scheduled the **PWS weekly ops review** (writes reports to disk).
8. Scaffolded **Spyder Supply** as a new onboarding account.

## Current live account state (verified 2026-06-19)
- **PWS (`1532947017`) is LIVE.** Campaign `23958300224` "PWS | Shopping | Stage 1 Learning (3M Core)" — Standard Shopping, **Manual CPC $0.55**, **$25/day**, ad group `197719002237`, gated to **`custom_label_2 = pws_stage1_3m`** (60-SKU 3M roster). Campaign + ad group + product ad all ENABLED. PMax-A (`23702140220`) and the other 6 campaigns are PAUSED.
- Merchant Center `5748251237`. Primary conversion action: "Google Shopping App Purchase" (works; the lone historical $145.20 sale mapped to a real Shopify order).
- Why Manual CPC, not the originally-planned Maximize Conversions: the account is too cold — the API blocks all conversion-based Shopping bidding (tROAS → NOT_ENOUGH_CONVERSIONS; Max Conv/Value → OPERATION_NOT_PERMITTED_FOR_CONTEXT). See D22.

## What was built (with pointers)
- **PPC advisor system:** `PPC_ADVISOR.md` (persona + evergreen optimization knowledge + account registry + maintenance rules). Read at the start of any optimization session.
- **Standard Shopping creation:** `ads_mcp/creation/shopping.py` — propose/get/commit, configurable bidding (`manual_cpc` default, plus `maximize_clicks`/`maximize_conversion_value`/`target_roas` for the Stage-2 switch), gates to a custom_label, all PAUSED, optional `pause_campaign_ids`. Tools registered in `mcp_server/server.py`. API details + cold-account constraints in `GOOGLE_ADS_API_REFERENCE.md` §12.
- **DataFeedWatch loop:** `ads_mcp/sheets.py` `write_dfw_lookup_table` / `read_dfw_lookup_table`; tools `update_dfw_lookup_table` / `get_dfw_lookup_table`. Sheet `DFW_LOOKUP_SHEET_ID` (`1F8uQYzjLg3GK3ZDG6Xq5l6KpsyiNXy9LJvoRbZ20OHs`), tab `PWS_Stage1`, cols `sku, custom_label_2`. Memory note: `datafeedwatch-feed-tool`.
- **Weekly ops:** scheduled task `pws-weekly-ops` (Fridays ~9:23am local, first run 2026-06-26) writes dated reports to `pro-work-supply/weekly_reviews/`. Proposes only.
- **GitHub:** `git@github.com:adampaquette-source/google-ads-mcp.git` (private). All work committed + pushed through `9ac0152`.

## IMPORTANT environment gotchas
- **The running MCP `google-ads` server is STALE.** Code changes made after the last session restart (the `os` import fix in `_dfw_sheet_id`, and the configurable-bidding / EU-field / no-language fixes in `shopping.py`) are on disk + pushed but NOT loaded in the running server. **Restart the Claude Code session** to load them. Until then, the `update_dfw_lookup_table` / `get_dfw_lookup_table` MCP tools will error (`os` bug) and the shopping propose/commit MCP tools have the old broken builder.
- **Workaround used this session:** account writes were executed via one-off `uv run --directory <project> python - <<'PY' ...` scripts that import the on-disk `ads_mcp` code and load `.env` with `load_dotenv(".env")` (auto-discovery fails from stdin — always pass the path). Use `validate_only` (`MutateGoogleAdsRequest.validate_only=True`) to dry-run any mutate before committing.
- **Two machines, one Dropbox.** The project folder syncs across machines with different macOS usernames (`adam.paquette` vs `adampaquette`); use `${HOME}` in any path, never hardcode the username. The git repo guards against silent Dropbox divergence — commit often.
- The google-ads client runs `use_proto_plus=False` (raw protobuf: enums are ints, no `_pb`).

## Key learnings now codified
- Cold accounts can be too cold for Smart Bidding even on Shopping; validate strategies with `validate_only`, cold-start on Manual CPC / Max Clicks, then switch (PPC_ADVISOR.md + API ref §12).
- DFW is the feed source of truth; set custom labels there (lookup table), never in the Shopify Google app or MC supplemental feed (memory `datafeedwatch-feed-tool`).
- Shopify MCP "needs kickstarting" = unregistered per-machine + stale venv (memory `shopify-mcp-connection-fix`).

## Open items / waiting on Adam
- **PWS:** click "Run now" on the `pws-weekly-ops` task once to pre-approve its tools. Then the first real review is 2026-06-26. Optional: tidy the duplicate secondary "Purchase" conversion actions in Goals.
- **PWS Stage 2 (later):** when conversions clear NOT_ENOUGH_CONVERSIONS (~15-30), switch the campaign to Maximize Conversion Value (one propose/commit; bidding is configurable), then tROAS stepping toward the 800% goal. Build a negative-keyword propose/commit tool (none exists yet) for the weekly pass.
- **Spyder Supply (onboarding, blocked):** Spyder power-tool accessories, replacing Truck Box Outlet, storefront live at spydersupply.com. Needs: (1) Ads account created under MCC `7404361064` (reusing the existing Google payments profile; Adam does this, hands over the customer_id), (2) the rebranded Truck Box Outlet store added to the `shopify-toolup` server (`stores.config.json` + `.env`) with its store key, (3) margin/geo/history context. Then run the cold-account diagnosis — expect the same cold-Shopping pattern as PWS. See `spyder-supply/STATE.md`.

## Canonical files to read next session
- `CLAUDE.md` — project bible, change-routing, file index.
- `PPC_ADVISOR.md` — advisor persona + evergreen knowledge + account registry.
- `pro-work-supply/STATE.md` + `NOTES.md` + `DECISIONS.md` (D1-D23) + `STAGE1_BUILD_SPEC.md`.
- `spyder-supply/STATE.md` + `NOTES.md`.
- `GOOGLE_ADS_API_REFERENCE.md` §12 (Standard Shopping creation + cold-account constraints).
- Memory: `MEMORY.md` index → `shopify-mcp-connection-fix`, `datafeedwatch-feed-tool`.
