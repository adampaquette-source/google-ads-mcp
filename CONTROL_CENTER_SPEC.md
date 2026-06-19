# Ads Control Center -- Requirements and Architecture Spec

Status: v1 BUILT and running 2026-06-09. launchd service `com.toolup.ads-control-center`, dashboard at http://localhost:8770.
This is the working spec for the local command and control center. It supersedes nothing; it builds on top of `ads_mcp/` and runs beside the MCP server.

## Operations (how it runs)

- **Deploy model:** the service runs from a code copy at `~/Library/Application Support/ads-control-center/app/`, NOT from this project folder. macOS blocks background launchd processes from reading the Dropbox CloudStorage mount (python hangs in interpreter startup), so the installer rsyncs code + `.env` + `credentials/` + `shopify_mcp/` there and builds a venv.
- **After any code change to `control_center/` or `ads_mcp/`, redeploy:** `./scripts/install_control_center.sh` (also restarts the agent).
- Dashboard: http://localhost:8770 (binds 127.0.0.1 only). Logs: `~/Library/Logs/ads-control-center.log`.
- Data: `~/Library/Application Support/ads-control-center/control_center.db`. The deployed service writes its audit rows to `~/Library/Application Support/ads-control-center/audit.db` (table `control_center_change_log`); the project `audit.db` continues to serve the MCP flows.
- Stop: `launchctl bootout gui/$(id -u)/com.toolup.ads-control-center`. Start: re-run the installer.
- Cooldown sharing: control center commits append to the Sheets tROAS Log / Budget Log tabs, and stage-time cooldown checks read the same tROAS Log, so the M/W/F audit flow and the control center cannot stack changes on each other inside the 3-day window.
- Alert webhook: uses `GOOGLE_ADS_CC_WEBHOOK_URL` if set, else falls back to `GOOGLE_CHAT_WEBHOOK_URL`.

## Problem statement

The consultation priority stack (CONSULTATION_RESULTS.md) flags tROAS drift management, budget cap opportunities, and spend anomalies as the highest-value unbuilt tooling. Adam wants these surfaced in a user-friendly review queue instead of chat transcripts: scheduled pulls keep data fresh, flagged campaigns are scannable with helper data, changes are entered inline and committed in batch back to the mapped account, and alerts fire when new flags appear.

## Requirements (locked 2026-06-09)

| Decision | Choice |
|---|---|
| Access | Local web app on this Mac (localhost), no cloud hosting |
| Flag types v1 | tROAS drift, budget cap opportunity, spend anomalies (adaptive baseline) |
| Write types v1 | tROAS changes, budget changes |
| Pull cadence | 2-3x daily (07:00, 12:30, 17:30 local) |
| Alerts | Google Chat webhook AND macOS desktop notification, on new flags per pull |
| Helper data | Suggested change pre-filled, 7/30-day trend sparklines, account MER + tier context |
| Submit flow | Batch: stage changes across flags, single review screen, one commit |
| Flag lifecycle | Snooze with duration (1d / 3d / 7d); flag returns after snooze expires |
| Account scope | All accounts, tiered sensitivity (Tier 1 normal thresholds, Tier 2/3 only larger deviations, per digest tier logic) |
| Anomaly baseline | Full ~180-day backfill of daily campaign metrics on first run |
| Ops model | Always-on via launchd (server keepalive; pulls scheduled in-process) |
| AI layer | None in v1; fully deterministic. Bolt-on later if wanted. |

## Dependency posture (the "fewest dependencies" answer)

- **No cloud services.** No Cloud Run, Firestore, Secret Manager. Credentials stay in `.env` / `credentials/`.
- **No new database.** SQLite, same as `audit.db`. New file: `control_center.db` at `~/Library/Application Support/ads-control-center/` (override with `ADS_CC_DB_PATH`). It deliberately does NOT live in the project folder: the project is Dropbox-synced, and cloud sync silently lost committed SQLite writes during the first backfill attempt (2026-06-09). Never move the DB into a synced directory.
- **No JS toolchain.** Server-rendered Jinja2 templates plus one vendored `htmx.min.js` static file. No node, no npm, no build step.
- **Minimal new Python packages:** `jinja2` (and `uvicorn` if not already transitive via fastmcp; Starlette comes with fastmcp). Everything else is stdlib or already installed.
- **Scheduling:** launchd (built into macOS) keeps the server process alive across reboots; the server runs pulls in-process with a plain asyncio loop. No cron daemon, no APScheduler.
- **macOS notifications:** `osascript` (built into macOS), no notifier package.
- **MER context (durable, revised 2026-06-09):** the control center owns its own Shopify connectivity instead of depending on digest-run freshness. Adam copied the credentials file from his separate Shopify MCP server into `shopify_mcp/.env` (gitignored): per-store blocks of myshopify domain + `SHOPIFY_<SLUG>_MCP_CLIENT_ID` / `_CLIENT_SECRET` + `STORE_NAME_IDENTIFIERS`, 18 stores. Access tokens are minted on demand via the OAuth client credentials grant and cached ~24h (never stored in the file). A `control_center/shopify.py` module loads this registry, mints tokens, and pulls net sales per store per period via the Admin GraphQL API, joined to ads accounts through `stores_mapping.json`. Scope note: the file header lists only product/theme scopes; if the sales query fails on authorization, the fix is adding the reports/orders read scope to the `toolup-mcp-bot` app in the Shopify Dev Dashboard and reinstalling -- verify during build against ToolUp first.

## Architecture

```
control_center/
├── app.py            # Starlette/FastAPI app: routes, Jinja2 templates
├── scheduler.py      # asyncio pull loop (07:00 / 12:30 / 17:30), backfill entry
├── detectors.py      # flag detection: troas drift, budget cap, anomaly
├── store.py          # SQLite schema + access (control_center.db)
├── shopify.py        # store registry from shopify_mcp/.env, token mint + cache, net sales query
├── alerts.py         # Chat webhook + osascript notification fan-out
├── templates/        # queue.html, detail.html, review.html, history.html
├── static/htmx.min.js
└── launchd/com.toolup.ads-control-center.plist
```

Reused from `ads_mcp/` (no logic duplicated):
- `reporting/troas_audit.py` -- drift thresholds, step bands, suggested tROAS change
- `reporting/budget_audit.py` + pacing logic -- budget cap detection input
- `reporting/performance.py` + `queries.py` -- daily metrics pulls
- `proposals/troas.py`, `proposals/budget.py` -- the actual mutate calls at commit
- `audit.py` -- every commit logged before and after, same as everything else
- `notify.py` -- Chat webhook delivery
- `sheets.py` -- read MER tab for account context

### Data model (control_center.db)

- `daily_metrics(customer_id, campaign_id, date, cost, conv_value, conversions, budget_amount, troas_target, ...)` -- backfilled 180d, appended each pull
- `store_sales(shopify_key, date, net_sales)` -- pulled per store each cycle via `shopify.py`, makes MER durable and locally computable for any window
- `flags(id, type, customer_id, campaign_id, severity, payload_json, first_seen, last_seen, status[open|snoozed|resolved|committed], snooze_until)`
- `staged_changes(id, flag_id, change_type, current_value, new_value, created_at, status[staged|committed|failed])`
- `pulls(id, started_at, finished_at, accounts_scanned, new_flags, errors)`

### Detectors (tiered sensitivity)

| Flag | Logic | Tier 1 | Tier 2/3 |
|---|---|---|---|
| tROAS drift | drift vs target, troas_audit step bands | drift > 10% | drift > 30% or actual ROAS = 0 |
| Budget constrained | spend >= 80% of daily budget on >= N of last 7 full days (mirrors budget_audit.py) | 2 days | 2 days (uniform, per the audit) |
| Budget excess | L7 avg daily spend < 40% of budget, L7 spend >= $1 (mirrors budget_audit.py) | uniform | uniform |
| Spend anomaly | z-score of daily spend vs trailing 180d weekday-matched baseline | \|z\| >= 2.0 | \|z\| >= 3.0 |

Budget constraint is an opportunity signal, not a warning (CONSULTATION_RESULTS.md philosophy) -- the flag copy says "review for increase."

**Ad-group-managed tROAS (v1.1, 2026-06-10):** campaigns whose tROAS lives on
their ad groups (Standard Shopping pattern, e.g. the Margin Bands campaigns)
are evaluated per ad group. The pull stores each ad group's own tROAS plus L7
and prior-week metrics in `adgroup_troas`; the queue renders them as indented
editable child rows under the campaign flag; staged rows carry `ad_group_id`
and commit through `apply_troas_adgroup_change` (ad group mutate). The
campaign-level row itself never offers a write for these campaigns.

A flag auto-resolves when its condition clears for 2 consecutive pulls. Snoozed flags reopen when `snooze_until` passes if the condition still holds.

### Pull cycle

1. Per account (all, from `list_accounts` / stores_mapping): pull yesterday + today campaign metrics via `search_stream`, upsert into `daily_metrics`.
1b. Per store: pull yesterday + today net sales via `shopify.py`, upsert into `store_sales` (MER trailing-7-day computed locally from both tables).
2. Run the three detectors; diff against open flags.
3. New flags -> insert, then alert: one Chat card (counts by type + top items + `http://localhost:8770` link) and one macOS notification.
4. Record the pull row. Quota note: 2-3 pulls/day across ~19 accounts is well inside the 15k ops/day Basic Access budget; paged follow-ups don't count.

### UI (4 screens)

Styled with vendored **Tabler 1.4.0** (Bootstrap 5.3 admin kit; dark mode via
`data-bs-theme="dark"`; static files in `control_center/static/`, no build
step). Two queue tabs: **Performance** (tROAS drift + spend anomaly) and
**Budgets** (constrained + excess), plain links with server-set active class
(deliberately not Bootstrap tab JS, which fights htmx).

1. **Queue** -- flags grouped by account (tier, then total L7 spend); within an account campaigns sort by L7 spend descending. Key metric column leads with L7 revenue and L7 spend. Each row: sparkline, suggested change pre-filled in an inline input, [stage] and [snooze 1d/3d/7d] actions. Ad-group-managed campaigns expand into indented child rows, each stageable.
2. **Detail drawer** -- 7/30-day spend, conv value, ROAS trends; suggestion rationale (drift math or pacing math); account MER badge and tier.
3. **Review & commit** -- all staged diffs (current -> new), one Commit button. Commit walks staged changes through the existing propose/commit paths with audit logging; per-change success/failure shown after.
4. **History** -- past pulls, committed changes with before/after, failures.

### Safety rails (unchanged from project rules)

- Every write goes through the existing propose/commit pattern and lands in `audit.db` before and after the API call.
- The commit screen is the approval surface; nothing writes without Adam clicking Commit there.
- tROAS cooldown from `troas_audit` is enforced as a blocking warning on stage (override allowed, recorded in the audit payload).
- No em dashes in any user-facing string.

## Build order

1. `store.py` + backfill (180d daily metrics, quota-aware) -- verifiable against real data immediately
2. `detectors.py` + first real pull -- compare flags against known account state
3. `app.py` queue + detail + snooze (read-only release; usable same day)
4. Staging + review + commit path wired to proposals/ -- the write release
5. `scheduler.py` + alerts + launchd plists -- the always-on release
6. Polish: history screen, MER badge, sparklines

Each step is independently testable; Adam can start using the read-only queue before any write code exists.

## Out of scope for v1 (noted for later)

- Negative keyword pass (priority #6) -- different review UX, Phase 3 extension
- MoM/YoY comparison tool (priority #7) -- natural History-screen extension later
- AI analysis layer -- deterministic only in v1
- Phone access -- would require hosting or tunneling; revisit only if the Mac-local constraint chafes
