# Google Ads MCP Project — Handoff Brief for Claude Code

This file is the working spec for the Google Ads MCP server project. Read it at the start of every session. The companion document `Google_Ads_MCP_Scoping.docx` in this folder contains the full scoping rationale. This file is the actionable subset.

## Owner

Adam Paquette (adam.paquette@pcstools.com). Limited coding background, relies on Claude Code for implementation. Be explicit about every command and code change. Explain non-obvious decisions.

## Voice input aliases

Adam often uses voice dictation, which causes misspellings. Map these to the correct store:

| Voice input | Actual store | Store key |
|---|---|---|
| tulip, tulip.com | ToolUp / toolup.com | `toolupstore` |

## Project goal

Build a custom MCP (Model Context Protocol) server that lets Claude (via Claude Code and Cowork desktop) assist with managing 10+ Google Ads accounts under a single MCC. The server exposes tools for performance reporting, health checks, change proposals with approval, and (later) net-new campaign creation.

## Architecture: two processes, one shared library

```
project/
├── ads_mcp/                # Shared library — all Google Ads logic lives here
│   ├── auth.py             # OAuth + credential management
│   ├── client.py           # google-ads client factory
│   ├── reporting/          # Read functions (Phase 1)
│   ├── proposals/          # Write proposal builders (Phase 3)
│   ├── creation/           # Campaign creation builders (Phase 4)
│   ├── audit.py            # Audit log writer
│   └── notify.py           # Google Chat / Slack / Dropbox digest delivery
│
├── mcp_server/             # Process A: local stdio MCP server
│   └── server.py           # FastMCP server exposing tools from ads_mcp/
│
├── digest_worker/          # Process B: scheduled cloud worker
│   ├── main.py             # Cloud Run entry point
│   ├── Dockerfile
│   └── cloudbuild.yaml
│
├── scripts/
│   └── deploy_digest_worker.sh
│
├── tests/
├── .env.example
├── pyproject.toml          # uv or poetry
└── README.md
```

Both processes import from `ads_mcp/`. Reporting logic is written once.

## Tech stack (locked)

- **Language:** Python 3.11+
- **Package manager:** uv (or poetry — pick one and stick with it)
- **MCP framework:** `fastmcp` (https://github.com/jlowin/fastmcp)
- **Google Ads client:** `google-ads` (official, https://github.com/googleads/google-ads-python)
- **Merchant API client:** `google-shopping-merchant-*` (Phase 5)
- **Cloud deployment target:** Google Cloud Run, region us-central1 (or closest to Adam)
- **Scheduler:** Google Cloud Scheduler
- **Secrets:** local .env (dev), Google Secret Manager (prod digest worker)
- **Audit log:** SQLite for local MCP, Firestore for cloud digest worker
- **Linting/formatting:** ruff + black
- **Type checking:** mypy (strict on ads_mcp/, loose on top-level scripts)

## Authentication

**This project uses service account + JWT authentication, not OAuth installed-app flow.** An internal engineer is already using a service account for a related labels script, and we follow the same pattern. No browser consent flow. No refresh tokens to manage.

The service account's JSON key file is stored at the project root (gitignored) and referenced by path from `.env`. The service account is added as a user on the Google Ads MCC with Standard access (so it inherits access to all sub-accounts and can perform writes in Phase 3+).

For Phase 2 (Cloud Run digest worker), the JSON key contents will be stored in Google Secret Manager. The library code should support both modes: read from a local JSON file path when running locally, read from Secret Manager when running on Cloud Run. Detect via the `ADS_MCP_ENV` env var.

The `google-ads-python` client supports service account auth natively via the `json_key_file_path` configuration property, or by passing `google.oauth2.service_account.Credentials` directly. Use the latter pattern so credentials can come from either a file (local) or a Secret Manager fetch (cloud) without changing the client construction code.

## Environment variables

`.env` at project root (gitignored). `.env.example` checked in.

```
# Google Ads API
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH=./credentials/adam-mcp-496818-9eefc00dccae.json
GOOGLE_ADS_LOGIN_CUSTOMER_ID=     # The MCC ID, no dashes

# Notifications (used by digest worker)
GOOGLE_CHAT_WEBHOOK_URL=
SLACK_WEBHOOK_URL=
DROPBOX_DIGEST_PATH=/Users/.../Dropbox/.../001-Google Ads MCP Project/digests

# Project config
ADS_MCP_ENV=local                  # local | cloud
ADS_MCP_AUDIT_LOG_PATH=./audit.db
```

**Gitignore is already in place** (`.gitignore` at project root) and excludes:
- `.env`
- `credentials/` (where the service account JSON key lives)
- `audit.db`
- Standard Python tooling junk

The service account JSON key lives at `credentials/adam-mcp-496818-9eefc00dccae.json`. The Cloud project is `adam-mcp-496818`. The service account email is `mcp-server@adam-mcp-496818.iam.gserviceaccount.com`.

## Phase plan

### Phase 0: Prerequisites (no code, Adam-owned)
- Apply for Google Ads API Basic Access dev token from MCC
- Create Google Cloud project `ads-mcp-prod`, enable Google Ads API
- Create OAuth 2.0 client (Desktop app type), save client ID + secret
- Create Google Chat space + Incoming Webhook
- Create Slack free workspace + Incoming Webhooks app
- Create Dropbox `/digests` subfolder

### Phase 1: Read-only MCP server (MVP) — START HERE WHEN PREREQUISITES READY
**Definition of done:** Claude can call `list_accounts` and `get_campaign_performance` from Cowork or Claude Code against Adam's real MCC and receive correct structured data.

Steps:
1. Scaffold the project structure above. Use `uv init` if uv is preferred, otherwise `poetry init`.
2. Build `ads_mcp/auth.py` to load the service account JSON key (path from `.env`) and produce `google.oauth2.service_account.Credentials`. No refresh token flow needed.
3. Build `ads_mcp/client.py` to construct a `GoogleAdsClient` using those credentials plus the developer token and login customer ID from `.env`.
4. Write a smoke test that calls `customer_service.list_accessible_customers()` and prints results. Run against Adam's real MCC to verify the service account has the right permissions.
5. Build the Phase 1 read-only tool set in `ads_mcp/reporting/`:
   - `list_accounts()`
   - `get_account_summary(customer_id, date_range)`
   - `get_campaign_performance(customer_id, date_range, filters=None)`
   - `get_ad_group_performance(customer_id, campaign_id, date_range)`
   - `get_search_terms(customer_id, campaign_id, date_range)`
   - `get_keyword_performance(customer_id, date_range)`
   - `get_product_performance(customer_id, date_range)` # Shopping/PMax
   - `check_troas_pacing(customer_id, drift_pct=10)`
   - `check_budget_pacing(customer_id)`
   - `find_anomalies(customer_id, metric, sensitivity=2.0)`
   - `find_disapprovals(customer_id)`
6. Expose them as FastMCP tools in `mcp_server/server.py`.
7. Configure Claude Code / Cowork to run the server (stdio). Write the exact MCP configuration JSON for Adam.
8. Verify end-to-end: ask Claude in Cowork "Give me a performance summary across all my accounts for the last 30 days." Confirm the response is correct.

### Phase 2: Scheduled digest worker
- Build `digest_worker/main.py` that imports `ads_mcp.reporting`, runs a templated cross-account report, calls Claude via the Anthropic API to write a digest narrative, and posts to Google Chat + Slack + writes to Dropbox.
- Containerize and deploy to Cloud Run.
- Wire Cloud Scheduler to trigger it daily (and weekly long-form on Mondays).

### Phase 3: Targeted adjustments with batch approval
- Add `ads_mcp/proposals/` with builder functions per change type
- Add MCP tools: `propose_troas_change`, `propose_budget_change`, `propose_campaign_status`, `propose_negative_keywords`, `propose_asset_group_signals`, `propose_bid_adjustments`
- Write all changes to the audit log on commit
- **As-built approval flow (this is what actually exists).** The token design described below was planned but never implemented. The real flow is approval-by-spreadsheet: `propose_*` tools (tROAS, budget) write proposed changes to a Google Sheets tab; a human sets each row's `Decision` to `Approve` or `Skip` (or uses the Control Center web UI as the approval surface); then `commit_troas_changes()`, `commit_budget_changes()`, or `commit_all_changes()` (no arguments) read the sheet and apply every `Approve` row, logging each to the Log tab. Campaign creation uses `propose_*` returning a `proposal_id`, committed via `commit_google_ads_pmax_campaign(proposal_id)` / `commit_google_ads_standard_shopping_campaign(proposal_id)`.
- **Known gap (matters for hosting).** The as-built flow is a single-trusted-operator control: it assumes whoever edits the sheet and whoever runs commit are the same trusted person. There is no token, no expiry, no single-use enforcement, no caller binding, and no actor identity in the audit rows. Acceptable on one local machine; NOT an authorization control. Build the real gate before any networked or multi-user exposure (see `HOSTING_MIGRATION_PLAN.md` Section 3 and gate G5).
- **Original planned design, NOT implemented (kept for reference):** `get_change_plan(plan_id)` and `commit_change_plan(plan_id, approval_token)`, where commit required a short-lived (5 min), single-use approval token surfaced to Adam in chat.

### Phase 4: Net-new campaign creation
- Add `ads_mcp/creation/` for campaign builders
- Add MCP tools: `create_branded_search_campaign`, `create_pmax_campaign`, `create_asset_group`, `link_merchant_feed`
- Integrate with the existing `google-ads-pmax-builder` skill: that skill produces structured asset group inputs, this MCP turns them into real campaigns
- Creation goes through the same plan/commit pattern as Phase 3

### Phase 5: Merchant Center
- Add `ads_mcp/merchant/` for Merchant API client
- Add MCP tools: `list_merchant_accounts`, `get_feed_health`, `get_disapproved_products`, `get_product_issues`
- Tie feed health to PMax campaigns in the digest worker output

### Phase 6: Google Chat bot (ChatOps interface)
- Build a Google Chat app (bot) with an HTTPS endpoint (Cloud Run)
- Receives @mentions and DMs from Chat, parses the message, calls relevant MCP/ads_mcp functions
- Responds inline in Chat -- enables queries like "@GoogleAds digest" or "@GoogleAds campaign performance for ToolUp" without opening Claude Code
- Requires: persistent HTTPS endpoint, Chat app registration in GCP, event verification, optional Anthropic API call for natural language intent parsing
- Parked: implement after Phase 5, or as a standalone spike if ChatOps becomes a priority

### Phase 7: Guardrails and proactive automation
- Add a YAML config defining safe-change envelopes per change type
- Below-envelope proposals auto-commit (still audited)
- Above-envelope proposals fall back to Phase 3 batch approval
- Add scheduled actions in the digest worker (e.g. propose tROAS shifts on Monday for drift detected during the week)

## Coding conventions

- **No em dashes in any text output** (user preference). This includes log messages, docstrings, error messages, digest content, anything user-facing.
- **All public functions in `ads_mcp/` are typed.** Use TypedDict or Pydantic models for structured returns. MCP tools must return JSON-serializable structures.
- **GAQL queries live in `ads_mcp/reporting/queries.py`** as constants, not inline strings scattered through code. One source of truth.
- **Pagination is mandatory.** Google Ads API pages results. Use `search_stream` or handle pagination explicitly. Never assume a single page is the full result.
- **Date ranges accept either a preset string** (`LAST_7_DAYS`, `LAST_30_DAYS`, `THIS_MONTH`, etc.) **or an explicit `{start_date, end_date}` dict.** Adam will use both patterns.
- **All write operations log to the audit table** before AND after the API call so partial failures are visible.
- **Customer IDs are strings, not ints.** Google Ads customer IDs can have leading zeros depending on context. Always strings.
- **Use the official google-ads logging config** for the underlying client; surface high-level info to stderr.

## Approval and safety rules (for Phase 3+)

- All accounts in the MCC are owned by Adam's org. No agency clients. No per-account compliance allowlist needed.
- Operationally still treat writes carefully. Audit log everything. Make rollback queries easy (`get_recent_changes(account_id, hours=24)`).
- Never expose a tool that performs a write without going through the proposal/commit flow.
- **Approval is currently by spreadsheet, not by token.** The `approval_token` / `commit_change_plan` model is documented in Phase 3 but was never built. Today approval = a human marks `Approve` in the Google Sheet (or commits via the Control Center UI), then runs the relevant `commit_*` tool. This holds only for a single trusted local operator. See `HOSTING_MIGRATION_PLAN.md` (Section 3, gate G5) before exposing any write surface to the network.

## Notifications (Phase 2+)

Google Chat is primary. Slack is backup (same content posted to both). Dropbox is archival.

- Google Chat: simple incoming webhook, POST `{"text": "..."}` for plain or `{"cards": [...]}` for rich
- Slack: simple incoming webhook, POST `{"text": "..."}` or block kit
- Dropbox: write `digests/YYYY-MM-DD_daily.md` and `digests/YYYY-MM-DD_weekly.md`

Digest content is **written by Claude via the Anthropic API**, not hand-templated. The digest worker fetches the data, gathers structured summaries, then prompts Claude to write the narrative. This keeps the prose adaptive instead of robotic.

## File index and relationships

| File | Role | Read when |
|---|---|---|
| `CLAUDE.md` | Session entry point. Coding conventions, phase plan, file relationships, change routing. | Every session. |
| `CONSULTATION_RESULTS.md` | Business decisions. Account tiers, alert philosophy, display preferences, priority build stack. | Session start for any ads work. Update when a business decision changes. |
| `DIGEST_SKILL.md` | Execution. Parameterized step-by-step for daily and weekly digest runs. Self-contained. | Every digest run (manual or scheduled). Update when digest behavior changes. |
| `DIGEST_SOP.md` | Rationale. WHY behind the skill: edge case explanations, tier logic detail, build stack context. | When modifying digest tooling or investigating unexpected output. Update when rationale or edge cases change. |
| `ads_mcp/reporting/troas_audit.py` | tROAS audit logic. Proposal generation, drift thresholds, step bands, rollback check. | Every session touching tROAS tools. |
| `ads_mcp/proposals/troas.py` | tROAS apply logic. Google Ads mutate call for target_roas.target_roas. | When modifying the write operation or adding rollback apply. |
| `ads_mcp/reporting/waste_audit.py` + `waste_config.py` + `waste_audit_config.json` | Wasted-keyword (negative-keyword) audit engine: pull search terms, apply the per-account protect list, classify into tranches (competitor / off-product / foreign / below-breakeven / non-branded / zero-conv / ngram-waste) with n-gram diffuse-waste rollup and economics-scaled (`target_cpa`) thresholds. Config is per customer_id. Propose-only. | Any session touching the negative-keyword audit. Read `NEGATIVE_KEYWORD_AUDIT_SKILL.md` first. |
| `ads_mcp/proposals/negatives.py` | Negative-keyword apply logic: find-or-create the account's "Waste Audit Negatives" shared set, add approved keywords (deduped), attach to eligible Search/Shopping campaigns. | When modifying the negative-keyword commit/write. |
| `WASTED_SPEND_REMEDIATION.md` | Problem-space advisor skill for wasted spend: lever selection (negatives vs brand exclusions vs account/campaign/shared-list vs bid/structural), economics-scaled thresholds, n-gram technique, waste taxonomy, per-channel reality (Search/Shopping/PMax/AI Max visibility + negative mechanics + API resources), cautions, cadence, and the current-implementation gap list. Synthesized from repo research + a 2025-2026 web pass. | FIRST, whenever working on search-term waste / negative keywords / brand or PMax query bleed, or tuning the waste-audit tooling. |
| `NEGATIVE_KEYWORD_AUDIT_SKILL.md` | The repeatable wasted-keyword audit procedure: tranche definitions, protect-list rule, per-account config, propose -> pause -> approve -> commit. Has a `🛑 PAUSE FOR ADAM` checkpoint. | When running or modifying the negative-keyword audit (after `WASTED_SPEND_REMEDIATION.md`). |
| `ads_mcp/creation/shopping.py` | Standard Shopping campaign creation (propose/get/commit), mirroring `pmax.py`. Maximize Conversions, gated to a feed custom_label, PAUSED, optional `pause_campaign_ids`. Used for cold-account Stage 1 learning. | Any session building or modifying Standard Shopping campaigns. Read `GOOGLE_ADS_API_REFERENCE.md` §12 first. |
| `ads_mcp/creation/search.py` | Standard Search creation (propose/get/commit) with Smart Bidding, campaign-level sitelinks/callouts/structured snippets, AI Max (`ai_max` block), and page feed + URL exclusions (`page_feed_urls`, `url_exclusions`). `add_page_feed_to_campaign()` scopes AI Max final URL expansion on an existing campaign (can flip FUE on). | Any session building/modifying Search or AI Max campaigns. Read `AI_MAX_SKILL.md` for AI Max, `GOOGLE_ADS_API_REFERENCE.md` §14. |
| `ads_mcp/creation/experiments.py` | AI Max built-in experiment (`ADOPT_AI_MAX`): propose -> commit (SETUP + control/treatment arms, `dry_run`) -> schedule (the spend step) -> end. The repeatable, incrementality-gated launch path. | Any session launching or managing an AI Max 50/50 experiment. Read `AI_MAX_SKILL.md` sections 9-10 first. |
| `GOOGLE_ADS_API_REFERENCE.md` | API reference. GAQL syntax, field names, quota rules, write operation structure. | Any session touching `ads_mcp/` or `mcp_server/`. |
| `GCHAT_CARD_SCHEMA.md` | Google Chat card schema. Widget types, color token palette, DigestCardData schema, formatting preferences log, and the v2 upgrade plan. | Any session touching `ads_mcp/notify.py`, digest output, or any Chat notification. Update when a formatting preference is discovered or changed. |
| `stores_mapping.json` | Store registry. Authoritative 1-to-1 map of shopify_key to ads_customer_id for all 18 stores. | Any session joining Shopify and Google Ads data. Update when a store is added, removed, or renamed. |
| `STORE_PROFILES.md` | Per-store conventions and facts (free shipping verbiage and threshold, URL patterns, campaign naming, brand string casing, default logo asset, business name, default geo + language, account quirks). One section per store. ToolUp is fully filled; other 17 stores are stubs to fill on first encounter. | Any campaign creation task -- look up the target customer_id's section before pulling defaults. Update the relevant section when a store-level fact is discovered or changes; bump `last_verified`. |
| `NOTES.md` | Cross-session scratch pad. Created by Claude Code as needed. | If it exists, read at session start. |
| `SESSION_HANDOFF.md` | Latest precompaction session handoff: live state, what was built, environment gotchas (incl. stale running MCP server), open items, and which canonical files to read next. | If it exists, read at session start (after this file). |
| `CAMPAIGN_CREATION_BEST_PRACTICES.md` | Canonical, task-agnostic guide for all campaign creation work. Always rules, pre-flight research, asset group composition rules, brand-term search theme rule, free shipping verbiage rule, Shopify MCP for final URLs, brand_name matching, **skill registry**, self-improvement rule. | Any campaign creation task -- read this BEFORE the campaign-type skill. Update when a new evergreen finding emerges (after consulting Adam). |
| `ASSET_CREATION_SKILL.md` | Cross-cutting asset craft + specs skill for all Google Ads assets (headlines, long headlines, descriptions, search themes, images, audience signals, extensions). Current 2025-2026 specs, per-asset-type rules, the sales-driven exemplar rule (pull Shopify/shopping sales first, feature real best-sellers), policy pitfalls, Ad Strength Excellent checklist. Sits under `CAMPAIGN_CREATION_BEST_PRACTICES.md`, beside the campaign-type skills. | Any session that writes or edits ad assets. Read alongside the campaign-type skill. |
| `AI_MAX_SKILL.md` | AI Max for Search skill. AI Max is a feature suite toggled onto a Search campaign (not a new campaign type). Covers what it is, components + dependencies, controls and brand safety, honest performance evidence, PMax/DSA/broad-match interaction and auction priority, reporting/blind spots, the API representation (v21+ `campaign.ai_max_setting`), a multi-brand launch playbook, and a self-improvement clause. Inherits from `CAMPAIGN_CREATION_BEST_PRACTICES.md` and `ASSET_CREATION_SKILL.md`. | Any session enabling or configuring AI Max on a Search campaign. Re-verify specs first (fast-moving feature). |
| `PMAX_BRAND_BREAKOUT_SKILL.md` | PMax brand breakout skill. Parameterized execution: brand analytics, Ahrefs research, copy + settings, image prep, propose, commit. Has explicit `🛑 PAUSE FOR ADAM` checkpoints. Inherits rules from `CAMPAIGN_CREATION_BEST_PRACTICES.md`. | When executing a brand breakout campaign creation task. |
| `PMAX_IMAGE_BEST_PRACTICES.md` | Evergreen PMax image creative guide. ~10 images per asset group target. Sourcing priority (existing assets, Shopify MCP, manufacturer, other sellers, general web, then generation). Mandatory direct-image-link rule for any generation prompt. Hero product rule. 3-prompt supplement structure. Per-campaign folder convention and manifest schema. | Any campaign creation task that needs new image assets or image prompts. Update when new creative findings or preferences are discovered. |
| `campaign_assets/` (directory) | Local working storage for per-campaign artifacts. Structure: `campaign_assets/<campaign_slug>/PROPOSAL.md` + per-asset-group `<slug>/{sourced,generated}/` + `manifest.md`. PROPOSAL.md is the required human-readable working artifact (header table, per-step sections, checkpoint markers, outstanding items, revision log -- see `CAMPAIGN_CREATION_BEST_PRACTICES.md` § Required: PROPOSAL.md). Gitignored except the README. | Created and populated by every campaign creation skill -- PROPOSAL.md is initialized right after the initial data pull and maintained through every revision. Adam reads PROPOSAL.md at every pause checkpoint. |
| `CONTROL_CENTER_SPEC.md` | Ads Control Center spec AND ops runbook. Locked requirements (2026-06-09), architecture, data model, detector thresholds, deploy/restart commands. v1 is BUILT: launchd service, dashboard at localhost:8770. | Any session touching `control_center/` or the flag/alert/commit workflow. Update when a requirement or threshold changes. |
| `control_center/` (directory) | The control center code: `shopify.py` (store registry + net sales), `store.py` (SQLite + pulls), `detectors.py` (tROAS drift / budget cap / spend anomaly), `app.py` (web UI + commit path), `webauth.py` (hosted-mode Google OAuth + forced view-only), `scheduler.py`, `alerts.py`. Local: runs as a deployed copy under `~/Library/Application Support/ads-control-center/` -- after editing, redeploy with `scripts/install_control_center.sh`. Hosted: Railway service, view-only (see `CONTROL_CENTER_SPEC.md` § Hosted mode). | Any control center change. Read `CONTROL_CENTER_SPEC.md` first. |
| `PPC_ADVISOR.md` | The Google Ads / PPC advisor persona AND canonical evergreen optimization knowledge (diagnosis framework, learning-phase rules, budget-for-learning math, channel selection, feed curation, staged rollout, failure modes). Also defines the per-account markdown system (NOTES.md + STATE.md), the account registry, and the maintenance / self-improvement rules for it. | At the start of any campaign or account optimization session. Update evergreen best practices only after consulting Adam. |
| `<account-slug>/NOTES.md` | Per-account durable facts and standing rules (identifiers, store identity, economics, hard rules, quirks, known data gaps). Authoritative reference for the account. One per account folder. | Any session optimizing that account. Update when an account fact changes; bump the date. |
| `<account-slug>/STATE.md` | Per-account live working state (current stage, what is live, what is proposed, last/next action, open questions, changelog). Fast-changing. One per account folder. | Any session optimizing that account. Update after every working session on it. |
| `pro-work-supply/` (directory) | PWS account project: `NOTES.md` (durable facts), `STATE.md` (working state), `DECISIONS.md` (ratified D1-D23 log), `STAGE1_PROPOSAL.md` + `STAGE1_BUILD_SPEC.md` (plan + executed build), `pws_stage1_3m_lookup.csv` (DFW roster), `weekly_reviews/` (dated weekly ops reports from the `pws-weekly-ops` scheduled task). Stage 1 Shopping campaign `23958300224` is LIVE (Manual CPC, $25/day). | Any session touching Pro Work Supply (`1532947017`). |
| `spyder-supply/` (directory) | Spyder Supply account project (`9267883382`, US-wide cold store; Spyder power-tool accessories, rebrand of Truck Box Outlet, spydersupply.com; Shopify key `weather-guard-store`). `NOTES.md`, `STATE.md`, `DECISIONS.md` (D1-D10), `STRATEGY.md` (research + path), `CAMPAIGN_BUILD_SPEC.md` (executable plan: 2 Standard Shopping campaigns curated/fallback + branded Search), and roster CSVs (`spyder_dfw_lookup.csv`, `spyder_curated_roster.csv`, `spyder_fallback_roster.csv`). Path ratified, built and PAUSED-ready; blocked only on MC feed + DFW + conversion tracking. | Any session touching Spyder Supply. |
| `Google_Ads_MCP_Scoping.docx` | Original scoping rationale. Background only. | Rarely -- only if re-evaluating architecture. |

Scheduled tasks read `DIGEST_SKILL.md` at runtime. They are thin wrappers:
- `google-ads-daily-digest` calls DIGEST_SKILL.md in DAILY mode (LAST_7_DAYS)
- `google-ads-weekly-digest` calls DIGEST_SKILL.md in WEEKLY mode (LAST_30_DAYS)
- `pws-weekly-ops` (Fridays ~9:23am local) runs the Pro Work Supply Stage 1 weekly review (D23) and writes a dated report to `pro-work-supply/weekly_reviews/`. Self-contained prompt; diagnoses and proposes only, no account/feed changes.
- `google-ads-monthly-negatives` (1st of month ~9am local) runs the wasted-keyword audit across all accounts via `run_waste_audit`, populating the control center Negatives tab grouped by tranche. Propose-only: Adam reviews, approves, and commits. Reads `NEGATIVE_KEYWORD_AUDIT_SKILL.md`.

To view or edit scheduled task prompts: use the `mcp__scheduled-tasks__list_scheduled_tasks` and `mcp__scheduled-tasks__update_scheduled_task` tools.

---

## Change routing

When tasked with a change, use this table to find every file that needs updating. Missing an entry means stale behavior in production.

| Change type | Files to update |
|---|---|
| MER threshold or formula | `ads_mcp/reporting/mer.py` (_mer_status, assemble_mer_report) + `DIGEST_SKILL.md` (Step 4 thresholds) + `DIGEST_SOP.md` (MER table) + `CONSULTATION_RESULTS.md` (Reporting Display Preferences) |
| Narrative format or section order | `DIGEST_SKILL.md` (Step 5 format rules and templates) + `DIGEST_SOP.md` (narrative format rules section) |
| Alert threshold (tROAS drift %, zero-conversion window, budget pacing ratio) | `ads_mcp/reporting/health.py` (check functions) + `DIGEST_SKILL.md` (relevant step) + `DIGEST_SOP.md` (alert logic section) + `CONSULTATION_RESULTS.md` (Alert Logic section) |
| Account tier assignment or tier behavior | `CONSULTATION_RESULTS.md` (Account Tier Structure) + `DIGEST_SKILL.md` (tier-aware alert depth) + `DIGEST_SOP.md` (tier table) |
| New or removed store | `stores_mapping.json` + `DIGEST_SKILL.md` (store mapping table) + `DIGEST_SOP.md` (Shopify stores mapping section) |
| Store edge case behavior | `DIGEST_SKILL.md` (edge cases section in Step 5) + `DIGEST_SOP.md` (Known edge cases section) |
| New MCP tool | `ads_mcp/<module>.py` (logic) + `mcp_server/server.py` (tool registration) + `GOOGLE_ADS_API_REFERENCE.md` (if new GAQL queries) |
| New or modified campaign creation tool | `ads_mcp/creation/<module>.py` (logic) + `mcp_server/server.py` (tool registration) + `GOOGLE_ADS_API_REFERENCE.md` (sections 10-14; §12 = Standard Shopping, §14 = Standard Search) |
| DataFeedWatch lookup table / feed custom_label change | Use the `update_dfw_lookup_table` MCP tool (writes the `DFW_LOOKUP_SHEET_ID` Google Sheet that DFW reads). Code: `ads_mcp/sheets.py` (`write_dfw_lookup_table`) + `mcp_server/server.py`. NEVER set the label via the Shopify Google app or a Merchant Center supplemental feed -- DFW overwrites those. |
| Evergreen / task-agnostic campaign creation finding (copy rule, pre-flight step, failure mode, store-level fact, etc.) | `CAMPAIGN_CREATION_BEST_PRACTICES.md` (canonical) -- after consulting Adam per the self-improvement rule in that file |
| PMax image creative finding or preference (sourcing, prompts, mix, anti-patterns) | `PMAX_IMAGE_BEST_PRACTICES.md` (canonical) + any active campaign creation skill that references it (e.g. `PMAX_BRAND_BREAKOUT_SKILL.md`) |
| New campaign-type skill needed | Create `<TYPE>_SKILL.md` + register it in the skill registry table inside `CAMPAIGN_CREATION_BEST_PRACTICES.md` + add a row to the file index in this file (`CLAUDE.md`) |
| Store-level fact discovered or changed (URL pattern, free shipping verbiage / threshold, campaign naming convention, brand string casing, logo asset, business name, geo/language defaults, account quirk) | `STORE_PROFILES.md` (the relevant store's section). Bump `last_verified`. |
| Chat card format or widget layout | `ads_mcp/notify.py` + `GCHAT_CARD_SCHEMA.md` (Formatting preferences log) + `DIGEST_SKILL.md` (Step 5 if DigestCardData fields change) |
| Chat card formatting preference discovered | `GCHAT_CARD_SCHEMA.md` (Formatting preferences log table) |
| tROAS audit thresholds (drift %, step bands, spend scaling %, cooldown days) | `ads_mcp/reporting/troas_audit.py` (constants at top of file) |
| tROAS proposal Sheets formatting or columns | `ads_mcp/sheets.py` (_TROAS_PROPOSALS_HEADERS + _setup_troas_proposals_formatting + write_troas_proposals) |
| tROAS rollback threshold (drop %, min spend) | `ads_mcp/reporting/troas_audit.py` (_ROLLBACK_DROP_PCT + _ROLLBACK_MIN_SPEND_L7) |
| tROAS Chat space webhook | `.env` (GOOGLE_ADS_TROAS_WEBHOOK_URL) + `.env.example` |
| Scheduled task timing or cadence | `mcp__scheduled-tasks__update_scheduled_task` (cronExpression field only -- do not touch the prompt unless behavior is also changing) |
| Digest step sequence | `DIGEST_SKILL.md` (step order) + `DIGEST_SOP.md` (tool sequence section) |
| Google Sheets tab structure or formatting | `ads_mcp/sheets.py` + `DIGEST_SOP.md` (Google Sheets dashboard section) |
| Display preference (format, units, labels) | `CONSULTATION_RESULTS.md` (Reporting Display Preferences) + whichever files implement the preference |
| Control center detector threshold (drift %, cap ratio/days, anomaly z, tier rules) | `control_center/detectors.py` (constants at top) + `CONTROL_CENTER_SPEC.md` (detector table). Redeploy via `scripts/install_control_center.sh`. |
| Wasted-keyword audit rule (tranche logic, thresholds, match-type) or per-account protect/competitor lists | `ads_mcp/reporting/waste_audit.py` (constants + `classify_term`) for logic; `waste_audit_config.json` for per-account protect/competitor/off-product/breakeven. Operator "Protect" clicks in the Negatives tab persist to the CC DB (`negative_protect_terms`) and are merged into `protect_terms` by `control_center/waste.py` at audit time (`store.protect_overrides` / `add_protect_term` / `protect_open_matching`). Redeploy control center after config/logic changes. Update `NEGATIVE_KEYWORD_AUDIT_SKILL.md` if the process changes. |
| Wasted-keyword commit / shared-list or account-level behavior | `ads_mcp/proposals/negatives.py` (`apply_negatives` shared list attaches to Search+Shopping+PMax; `apply_account_level_negatives` for the 1,000-cap account-level list) + `control_center/app.py` (`/negatives/commit`) + `mcp_server/server.py` (`commit_negative_keywords`, `commit_account_level_negatives`). |
| Control center pull times or alert channel | `control_center/scheduler.py` (PULL_TIMES) / `control_center/alerts.py` + `CONTROL_CENTER_SPEC.md`. Redeploy after change. |
| Control center UI or commit flow | `control_center/app.py` + `control_center/templates/` + `CONTROL_CENTER_SPEC.md`. Redeploy after change. |
| Evergreen / account-agnostic PPC optimization finding (diagnosis, bidding, budget-for-learning, channel choice, feed curation, staging, failure mode) | `PPC_ADVISOR.md` (Retained best practices) -- after consulting Adam per the self-improvement rule in that file |
| Account durable fact or important note changed (identifiers, brand, economics, breakeven, quirk, hard rule, data gap) | `<account-slug>/NOTES.md` (bump the date) |
| Account working state changed (stage, what is live, what is proposed, next action, open question) | `<account-slug>/STATE.md` (bump the date, add a changelog line) |
| New account taken on as an optimization project | Create `<account-slug>/` with `NOTES.md` + `STATE.md` from the templates in `PPC_ADVISOR.md` + add a row to the account registry in `PPC_ADVISOR.md` |

---

## When generating a digest (manual or scheduled)

Execute `DIGEST_SKILL.md` directly. Do not read `DIGEST_SOP.md` first -- it is rationale, not execution.
Key reminders inline:
- MER = Ad Spend % = (Ads Spend / Net Sales) x 100. Lower is better. Strong <= 5%.
- Budget pacing UNDERPACING before 9am local = normal. Summarize in one line, do not list campaigns.
- Tier 1 (Toolup, Red Tool Store, top 3 by spend): per-campaign detail on all alerts.
- Tier 2/3: account-level only unless drift > 30% or actual ROAS = 0.
- No em dashes. Digest Chat messages use cardsV2 format -- see GCHAT_CARD_SCHEMA.md.

## When working on campaign or account optimization (any session diagnosing, restructuring, tuning bidding/budgets, or standing up / optimizing an account)

**Read `PPC_ADVISOR.md` first and adopt the advisor persona it defines.** It is the canonical, evergreen PPC optimization knowledge (diagnosis framework, learning-phase rules, budget-for-learning math, channel selection, feed curation, staged rollout, failure modes) and the home of the per-account markdown system.

Then read the target account's per-account files before touching anything:
- `<account-slug>/NOTES.md` -- durable facts, economics, hard rules, quirks, data gaps.
- `<account-slug>/STATE.md` -- current stage, what is live, what is proposed, next action, open questions.
- any `<account-slug>/DECISIONS.md` and proposal docs in that folder.

If the account has no folder yet, create one with `NOTES.md` and `STATE.md` from the templates in `PPC_ADVISOR.md` and add it to the account registry before doing the work.

Hard rules carried inline so they cannot be missed:
- **No account change without Adam's explicit approval.** Diagnose and propose first; everything is a proposal until he says go.
- **Diagnose before prescribing.** Pull account history and verify conversion tracking is firing before concluding an account "cannot convert."
- **Match the bid strategy to the conversion history.** A Target ROAS on a cold account starves it; cold accounts learn on Maximize Conversions first.
- **Update `STATE.md` after every working session**, and promote evergreen lessons to `PPC_ADVISOR.md` only after consulting Adam.

## When working on campaign creation (any session touching ads_mcp/creation/ or mcp_server/ creation tools, or any campaign build)

**Read `CAMPAIGN_CREATION_BEST_PRACTICES.md` first.** It is the canonical, task-agnostic guide and contains the skill registry. Then read the campaign-type skill that matches the task (e.g. `PMAX_BRAND_BREAKOUT_SKILL.md`). Also read the matching customer_id's section in `STORE_PROFILES.md` for store-level defaults, and `PMAX_IMAGE_BEST_PRACTICES.md` if the task touches image assets.

**Honor every `🛑 PAUSE FOR ADAM` checkpoint inside the skill file** -- those are non-negotiable human-in-the-loop gates. Never bypass one.

Hard rules carried inline so they cannot be missed:
- **All campaigns created via the API must be in `PAUSED` status.**
- **Every write goes through propose/commit.** Never write directly.
- **Read `GOOGLE_ADS_API_REFERENCE.md` sections 10 and 11** before writing or modifying any creation tool.
- **Always run Ahrefs keyword research** before finalizing search themes or copy. For brand-affiliated asset groups, every search theme must contain the brand term.
- **Verify free shipping verbiage and final URLs against the actual store** (Shopify MCP `get-collection` for collection links, store website header for promo verbiage). Never assume.
- **If you learn something evergreen during the task, consult Adam about appending it to `CAMPAIGN_CREATION_BEST_PRACTICES.md`** per the self-improvement rule in that file.

## When working on wasted spend (search-term waste, negative keywords, brand/PMax query bleed, or the waste-audit tooling)

**Read `WASTED_SPEND_REMEDIATION.md` first** and adopt its lever model. It is the canonical, evergreen
knowledge (thresholds, n-gram technique, waste taxonomy, per-channel visibility and negative mechanics,
API resources, cautions, cadence, and the current-implementation gap list). Then read
`NEGATIVE_KEYWORD_AUDIT_SKILL.md` for the executable propose -> approve -> commit procedure.

Hard rules carried inline:
- **Waste is remediated by more than negatives.** Match the lever to the failure mode: negatives (exact
  /phrase/broad), brand exclusion lists, account-level vs shared-list vs campaign-level, or bid/structural.
- **A term that converts at or above breakeven is not waste.** Protect it.
- **Do not over-negative**, especially on Smart Bidding / PMax; propose then human-approve, never auto-apply single-word broad negatives.
- **`search_term_view` does not cover PMax** - use `campaign_search_term_view` for PMax terms.
- Evergreen findings go in `WASTED_SPEND_REMEDIATION.md` only after consulting Adam.

## When working on MCP tools (any session touching ads_mcp/ or mcp_server/)

Read `GOOGLE_ADS_API_REFERENCE.md` before writing or modifying any tool. It covers:
- GAQL syntax, date ranges, and field selectability rules
- Correct resource field names and enum values for campaigns, ad groups, keywords, PMax asset groups, shopping, and customer_client
- `search_stream()` vs `search()` and quota cost of each
- MCC query pattern (queries are per customer_id; login_customer_id is always the MCC `7404361064`)
- Write operation structure (update_mask, mutate request format) for Phase 3+
- Error codes and retry pattern for quota exhaustion
- Rate limits: 15,000 ops/day on Basic Access across 19 accounts

## What to ask Adam at the start of a new session

- "Did Google Ads API Basic Access get approved yet?" (until it has)
- "Which phase are we working on today?"
- "Any account-specific quirks I should know about before I run queries?"

## Shopify MCP: always use the local server

Two Shopify MCP servers may be available in a session:

| Server | Type | Tools prefix | Use? |
|---|---|---|---|
| `shopify-toolup` (local, project `.mcp.json`) | Local stdio, API keys for all 18 stores | `mcp__shopify-toolup__shopify_*` (e.g. `shopify_search_products`, `shopify_get_product_sales`) | **YES -- always use this one** |
| `claude.ai Shopify` (cloud) | Cloud-hosted, OAuth per-store | `mcp__claude_ai_Shopify__*` | **NO -- never call these tools** |

**Rule:** Never call any `mcp__claude_ai_Shopify__*` tool. Always use the local `shopify-toolup` server's `shopify_*` tools for all Shopify operations (product search, analytics, collections, metafields, etc.). The local server already has API access to all 18 stores and does not require per-session OAuth authorization.

**Registration (this machine, added 2026-06-17):** the server is in this project's `.mcp.json` as `shopify-toolup`, running `uv run --directory "${HOME}/Toolup Dropbox/Adam Paquette/MCP Servers/Shopify-Klaviyo MCP/toolup-themes/mcp" python server.py`. The actual server code and its `.env` live in that theme-repo `mcp/` directory; `.env` is loaded by absolute path so CWD does not matter. A new MCP server only loads at session start, so after adding it you must restart the Claude Code session (and approve the new project server when prompted).

**Troubleshooting "Shopify won't connect / needs kickstarting":** the usual cause is a stale `.venv` in `.../toolup-themes/mcp/` whose Python symlink points at a removed interpreter, so the stdio subprocess fails to launch. Fix by rebuilding it once: `uv run --directory "${HOME}/Toolup Dropbox/Adam Paquette/MCP Servers/Shopify-Klaviyo MCP/toolup-themes/mcp" python -c "import server"` (uv recreates the venv and installs deps), then restart the session. A stray unused `shopify_mcp/.env` copy exists at this project root; it is not read by the server and can be ignored.

## What NOT to do

- Don't make live writes to any account before the proposal/commit flow is built and tested
- Don't store credentials anywhere except .env (local) or Google Secret Manager (cloud)
- Don't commit .env, refresh tokens, or any secret to git
- Don't use em dashes in any user-facing string
- Don't bypass the audit log
- Don't deploy to Cloud Run from a local machine without first running tests
- Don't call `mcp__claude_ai_Shopify__*` tools (use local `shopify-toolup` server instead)

## Account optimization markdown system: maintenance and self-improvement

The advisor knowledge in `PPC_ADVISOR.md` and the per-account `NOTES.md` / `STATE.md` files are a living system. Keep them current, or they rot into noise. Standing rules:

- **`STATE.md` is updated after every working session on an account.** Refresh the current stage, last action, next action, open questions, and add a dated changelog line. Stale state is worse than none.
- **Durable account facts go in that account's `NOTES.md`** (identifiers, economics, breakeven, quirks, data gaps, hard rules) and the date gets bumped.
- **Genuinely evergreen, account-agnostic PPC lessons go in `PPC_ADVISOR.md`** under Retained best practices, **but only after consulting Adam.** Do not silently rewrite best practices. Propose the addition, say why it is evergreen, append on confirmation. This mirrors the self-improvement rule in `CAMPAIGN_CREATION_BEST_PRACTICES.md`.
- **Taking on a new account as a project** means: create `<account-slug>/` with `NOTES.md` + `STATE.md` from the templates in `PPC_ADVISOR.md`, then add a row to the account registry in `PPC_ADVISOR.md`.
- **Keep the account registry in `PPC_ADVISOR.md` in sync** (status and last-touched columns) as work progresses.
