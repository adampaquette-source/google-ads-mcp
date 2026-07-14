# Hosting and Centralization Migration Plan

> **Addendum 2026-07-13 (executed):** the Control Center read-only migration greenlit on
> 2026-07-12 is BUILT and DEPLOYED. See Section 0 (as-built state) for what exists, which
> gates are satisfied, and the decisions taken (SQLite on a Railway volume, not Postgres;
> in-app Google OAuth, not Cloudflare Access). The commit/stage routes are hard-disabled in
> hosted mode -- no env flag can enable them -- until G5 (approval gate, proposal in Section
> 10) and G6 wiring on the write routes are complete.

---

## 0. As-built state (updated 2026-07-13)

This section supersedes the planning language below where they disagree. Everything here is
deployed and verified.

### Hosted today (Railway project `toolup-mcp`, PCS Projects workspace)

| Service | What | Auth | Writes? |
|---|---|---|---|
| `googleads-mcp` | Google Ads MCP server, Streamable HTTP (dual-mode: stdio locally when PORT unset) | Google OAuth via FastMCP GoogleProvider + `MCP_ROLE_MAP` per-user per-tool grants (default-deny, `MCP_ADMIN_ONLY_TOOLS` fence for `commit_*`) | Gated by role map; commit tools admin-only |
| `shopify-mcp`, `klaviyo-mcp`, `imagegen-mcp` | Sibling MCP services (separate repo for imagegen) | Same pattern | Per-service allowlists |
| `ads-control-center` | Control Center web dashboard (this migration), `https://ads-control-center-production.up.railway.app` | In-app Google OAuth (`control_center/webauth.py`) + `CC_ROLE_MAP` (default-deny, admin/viewer) + CSRF + signed sessions | **NO. Read-only: every POST returns 403 except admin `/pull`.** |

### Decisions taken

- **Auth model deviation from the original plan:** the plan called for Cloudflare Access as the
  single front door with origin lockdown (G1). The as-built MCP hosting (2026-07-07/08) went
  with per-app Google OAuth directly on the Railway public domain instead, and the control
  center follows the same pattern for consistency. Consequence: there is no Cloudflare layer;
  the app IS the front door, so its auth must stay fail-closed (both `mcp_server/authn.py` and
  `control_center/webauth.py` refuse to start in HTTP mode without complete auth config).
  G1 is therefore recast: "no unauthenticated surface on the public origin" rather than
  "origin reachable only via Cloudflare."
- **SQLite on a Railway volume, not Postgres.** `control_center/store.py` is raw sqlite3 with
  SQLite-dialect SQL throughout; the app is single-process single-writer; the volume removes
  the Dropbox-sync corruption risk that dictated the local DB location. Postgres would be a
  rewrite with no payoff at this scale (~19 accounts, low MB). Revisit only if multiple
  services ever need to share the DB (see "known seam" below).
- **Hosted = read-only means read-only for decisions too.** Approve/skip/snooze/stage are
  local-DB writes, not Google Ads writes, but allowing them hosted would record decisions in a
  database the local (write-capable) instance never sees -- split-brain approvals. So hosted
  blocks ALL POSTs except `/pull` (admin-only data refresh). When G5 lands and the hosted
  instance becomes the operative surface, this flips and the local launchd service retires.
- **Secrets:** Railway variables. The control center references the `googleads-mcp` service's
  variables (`${{googleads-mcp.GOOGLE_ADS_SERVICE_ACCOUNT_JSON}}` etc.) so secrets live in
  exactly one place. Shopify per-store creds arrive as `SHOPIFY_MCP_ENV` (the local
  `shopify_mcp/.env` file contents pasted into one variable); until set, the dashboard shows
  "No sales data" for MER and everything else works.
- **Timezone:** all control-center time math goes through `control_center/clock.py`
  (`CC_TIMEZONE`, default America/Los_Angeles), fixing the Section 7 risk (pull times,
  snooze windows, tROAS cooldowns shifting in a UTC container).
- **Alerts:** `CC_ALERTS_ENABLED=0` on the hosted service for now so Chat is not double-notified
  while the local launchd service also pulls. Flip when the local service retires.

### Known seam (accepted for now)

There are now up to three control-center SQLite databases: the local Mac one (operative for
commits), the hosted `ads-control-center` volume (read-only dashboard, fills itself via its own
backfill + scheduler), and the `googleads-mcp` volume copy used by that service's waste-audit
MCP tools. They do not sync. The local DB remains the source of truth for decisions until G5.
This is the strongest argument for Postgres later -- one shared DB for the CC service and the
MCP service -- and should be part of the G5 build.

### Gate status

| Gate | Status |
|---|---|
| G1 origin lockdown | Recast (see above): no Cloudflare; fail-closed in-app OAuth on the public origin. |
| G2 authn != authz | Done on both surfaces (OAuth authenticates; role maps authorize, default-deny). |
| G3 authz tier | Done for exposed surfaces: `MCP_ROLE_MAP` (per-tool), `CC_ROLE_MAP` (admin/viewer + read-only gate). |
| G4 actor attribution | Done for exposed surfaces: JSON-line audit of every MCP tool call and every CC mutating request with actor email. NOT yet threaded into the Google Ads write audit rows (part of G5). |
| G5 approval gate | NOT BUILT. Proposal in Section 10 awaiting Adam's sign-off. Until then hosted writes are hard-disabled. |
| G6 CSRF | Built in `webauth.py` and enforced on the one live POST (`/pull`); already wired in templates for the write routes so enabling them later inherits it. |
| G7 no static MCP tokens | Done (per-user OAuth on all MCP services). |
| G8 rate limiting | Not built (unchanged risk; hosted CC adds only scheduled pulls + admin manual pull). |
| G9 supply chain | Partial: `uv sync --frozen` from the reviewed lockfile, pinned uv binary, non-root runtime. No egress restriction, no rotation plan yet. |
| G10 credential segmentation | Not done: the CC service holds the same full-write service account as the MCP service even though it only reads. A read-only Google Ads login is not offered by the API (access level is per MCC user), so segmentation means G5's write-broker idea, not a weaker credential. |

Goal: get the custom MCP servers and local utility web apps off Adam's laptop and onto a cloud host so the tooling is centralized and reachable by anyone in the company. Two consumption modes confirmed:

1. **MCP clients** (Claude Desktop / claude.ai connectors / Claude Code) reaching the MCP servers as remote connectors.
2. **Web UI** (browser) for non-technical staff opening the dashboards directly.

Recommended stack: **Railway** for compute (one project, one service per server/app, GitHub-connected deploys) plus **Cloudflare Access** federated to Google Workspace as the single front door. Both are tools the company already runs.

> **Revision note (post adversarial security review).** This plan was re-sequenced after a security pass. The original draft optimized for "fastest reachable," which front-loaded the most dangerous, least-protected surfaces. The current version gates all internet exposure on a set of security requirements (Section 4) and exposes **read-only surfaces before any write-capable surface**. Read Section 3 (the approval-gate reality) before anything else; it is the load-bearing finding.

---

## 1. Inventory: what exists

### MCP servers (all currently stdio, all FastMCP, all Python 3.11 + uv)

| Server | Entry point | Tools | State to preserve | Secrets |
|---|---|---|---|---|
| **Google Ads** | `Google Ads MCP/mcp_server/server.py` (`mcp.run()`, stdio) | 40+ (reporting, health, propose/commit, image assets, Sheets) | `audit.db` | Service account JSON (`Credentials/adam-mcp-496818-9eefc00dccae.json`), dev token, webhook URLs, sheet IDs |
| **Shopify** | `Shopify-Klaviyo MCP/toolup-themes/mcp/server.py` (`mcp.run()`, stdio) | 32 (catalog, collections, metafields, themes, analytics, files) | `mcp/rollbacks/` snapshots | 36 OAuth creds (18 stores x id+secret) |
| **Klaviyo** | `Shopify-Klaviyo MCP/toolup-themes/Klaviyo MCP/server.py` (`mcp.run()`, stdio) | 16 (templates, campaigns, flows, analytics, images) | `accounts/<acct>/rollbacks/`, `audit.log` | 9 private API keys |

### Web apps (browser-consumed)

| App | Entry point | Framework | Today | State |
|---|---|---|---|---|
| **Ads Control Center** | `Google Ads MCP/control_center/app.py` (uvicorn) | Starlette | binds `127.0.0.1:8770`, launchd service, **no auth**, **no CSRF** | SQLite in `~/Library/Application Support/ads-control-center/`; scheduler at 07:00 / 12:30 / 17:30 local time |
| **MER dashboard** | (confirm location) | already exposed behind Cloudflare Access | already partly solved; read-only | n/a |

### Things that should NOT be hosted (stay local / CI)

- `toolup-themes/scripts/deploy.sh` and the theme deploy/backup scripts (push themes to Shopify from a trusted host; file-based locks; not a service).
- `email-gif-builder` and other `.claude/skills/` scripts (invoked ad hoc by Claude Code, stateless).
- `scripts/smoke_test.py`, `run_product_exclusion.py`, `.migration/` audit scripts (one-off, run by hand).

---

## 2. The transition that makes this high-stakes

Today every tool runs only on one person's laptop over stdio, implicitly trusted, with zero network exposure. The implicit trust boundary IS the security model: one person, one machine, one set of hands on the keyboard. This plan dissolves that boundary. Tools that mutate live Google Ads campaigns (19 accounts), 18 live Shopify storefronts, and 9 Klaviyo marketing accounts go from single-trusted-user to multi-user network service.

The danger is not the hosting mechanics (those are mostly boilerplate). The danger is that the write tools were built assuming the one-trusted-operator boundary, and that assumption is invisible in the code. Removing the boundary without replacing it is the core risk.

---

## 3. The approval gate, as it actually exists (read this first)

The project docs (`CLAUDE.md` and `AGENTS.md`) describe a strong approval model:

> "No write tool executes directly. Each `propose_*` returns a plan ID and a structured diff. `commit_change_plan` requires the operator to pass an approval token that the MCP client surfaces to Adam in chat. The token is short-lived (5 min) and single-use."

**This model does not exist in the code.** `approval_token`, `commit_change_plan`, and `get_change_plan` appear only in those two markdown files. There is no token, no 5-minute expiry, no single-use enforcement, no caller binding. Confirmed by grep across both repos.

### What is actually implemented

Approval-by-spreadsheet plus bare commit tools:

- **tROAS and budget changes.** `commit_troas_changes()` ([mcp_server/server.py:643](mcp_server/server.py:643)) and `commit_budget_changes()` ([mcp_server/server.py:966](mcp_server/server.py:966)) take **no arguments**. Each reads its Google Sheets proposal tab and applies **every row where the `Decision` cell equals `Approve`**, then writes a log row. `commit_all_changes()` ([mcp_server/server.py:1127](mcp_server/server.py:1127)) runs both.
- **Campaign creation.** `commit_google_ads_pmax_campaign(proposal_id)` ([mcp_server/server.py:1269](mcp_server/server.py:1269)) and `commit_google_ads_standard_shopping_campaign(proposal_id)` ([mcp_server/server.py:1390](mcp_server/server.py:1390)) gate only on a `proposal_id` string. No token, no caller check.
- **Control Center.** `POST /commit` ([control_center/app.py](control_center/app.py)) applies every staged change to live accounts. No token, no CSRF protection, no per-user check. The spec states the assumption plainly: "The commit screen is the approval surface; nothing writes without Adam clicking Commit" (`CONTROL_CENTER_SPEC.md`). That sentence only holds for one local user.

### Why this is acceptable today and dangerous hosted

The real gate is **"a trusted human edited a cell, then a trusted human ran the commit tool."** On one laptop those are the same person, so the gate works in practice. It is a legitimate human-in-the-loop control for a single operator.

It is not an authorization control, and it breaks in specific ways under multi-user exposure:

1. **No binding between approver and committer.** The `Decision = Approve` edit and the `commit_*` call are fully decoupled. Person A marks rows Approve in the shared sheet; Person B (or an automated client, or anyone who can reach the tool) triggers the apply. There is no record or requirement that the committer reviewed anything.
2. **The "token" is shared, persistent state, not single-use.** An `Approve` sits in the cell indefinitely until someone changes it. Re-calling `commit_*` re-reads whatever is currently Approved. This is the opposite of the documented short-lived, single-use design.
3. **Scope is "everything currently Approved," not a specific reviewed plan.** Because `commit_troas_changes()` takes no argument, the caller cannot scope to "the plan I looked at." They apply the whole current Approve set, including rows someone else added.
4. **`proposal_id` is the only gate on campaign creation.** Anyone who can call the tool with a valid `proposal_id` commits that campaign. Whether `proposal_id` is unguessable and access-scoped needs to be verified before exposure; if it is sequential or enumerable, it is not a control at all.
5. **No actor attribution.** The audit/log rows record what changed, not who approved or who committed, because today there is only one actor. Post-exposure you cannot answer "who moved this budget."

### Implication

This is a **live gap in the current local setup too**, in the narrow sense that the documented safety control was never built. It is tolerable now only because the laptop trust boundary substitutes for it. The moment any write surface is on the network, the documented control needs to actually exist. The docs should also be corrected so nobody relies on a token that is not there (recommend updating `CLAUDE.md` / `AGENTS.md` Phase 3 section to describe the real Sheets-based flow, or better, build the token and make the docs true).

---

## 4. Security requirements (hard gates for internet exposure)

Derived from the adversarial review. Nothing write-capable (web or MCP) goes on the internet until all of these exist. Read-only surfaces may go earlier (Section 5, Phase 1) provided G1, G2, and G4 hold.

| ID | Requirement | Why |
|---|---|---|
| **G1. Origin lockdown** | The Railway origin must not be reachable except through Cloudflare. Use Cloudflare Tunnel (no public port) or origin mTLS + Cloudflare IP allowlist. Verify with a direct-to-origin `curl` that returns 403. | Railway hands out a public `*.up.railway.app` URL by default. If it stays reachable, Cloudflare Access is bypassable and provides zero protection. The plan must prove the bypass is closed. |
| **G2. Authentication = Cloudflare Access only, never authorization** | Treat the SSO JWT as identity, not permission. | Passing the front door must not by itself grant any tool. |
| **G3. Real authorization tier below the door** | Per-tool, and ideally per-account, role gating enforced in-app, independent of Cloudflare. At minimum: read vs. commit separation; an allowlist of identities permitted to commit. | Without it, every authenticated employee can mutate all 19 ad accounts, 18 storefronts, 9 Klaviyo accounts. |
| **G4. Per-user identity threaded into every action and audit row** | Read `Cf-Access-Authenticated-User-Email` from the Access JWT and record it on every commit and every audit/log write. | Restores non-repudiation. Today the audit log cannot name an actor. |
| **G5. Real approval gate that binds approver to a reviewed plan** | Replace approval-by-bare-cell with the documented model or equivalent: commit takes a specific plan/proposal id, the commit is authorized only for an identity permitted to commit, the approval is single-use and expires, and approver + committer identities are logged. | This is the Section 3 gap. It is the difference between a control and a convention. |
| **G6. CSRF protection on all Control Center mutating routes** | `POST /commit`, `/stage`, `/snooze`, `/pull` need CSRF tokens once a browser session is authenticated. | Otherwise any authenticated session can be made to commit cross-site. |
| **G7. No static service tokens on any write-capable MCP server** | If per-user OAuth for MCP is not ready, write tools stay local (stdio); only read tools go remote. | Static shared tokens give no attribution, no revocation, and live in client config files on many laptops. |
| **G8. Rate limiting / quota protection** | Per-user, per-tool limits at the gateway; alert on Google Ads quota burn. | The 15,000 ops/day Basic Access quota is shared across all 19 accounts. One careless or malicious user can exhaust it and break reporting and the scheduled audits for everyone. |
| **G9. Supply-chain + secrets hardening** | Frozen, hash-verified deps (enforce `uv.lock` with `--frozen`); restrict container egress to known API hosts (Google Ads, Shopify, Klaviyo, Sheets, Chat); a credential rotation plan; leaked-secret detection. | Secrets in env are readable by every transitive dependency. One malicious package exfiltrates all 45+ creds in one shot. |
| **G10. Credential segmentation** | Split read-only reporting (minimal creds) from write surfaces (write creds) into separate services. Consider a write-broker service as the only holder of write-capable creds. | One compromised container today reaches everything: full MCC write, all storefronts, all Klaviyo accounts. |

---

## 5. Migration order (re-sequenced: read-only first)

### Phase 0 — Decisions, prep, and security gates (no exposure)
- Lock platform: Railway. Lock secrets home: **Railway secrets** (avoids implementing the GCP Secret Manager stub in `ads_mcp/auth.py`, which raises `NotImplementedError` for `ADS_MCP_ENV=cloud`).
- Lock auth model: Cloudflare Access (authn) + an in-app authorization tier (G2, G3).
- **Build and verify G1 (origin lockdown) and G9 (supply-chain/secrets hardening) now.** These gate everything, read-only included.
- Design G3, G4, G5 (authz tier, actor attribution, real approval gate). These gate the write surfaces in Phase 2/3.
- Correct `CLAUDE.md` / `AGENTS.md` to describe the real approval flow (Section 3) so no one relies on a control that is not there.
- Confirm the MER dashboard's code location and host so it joins the registry.

### Phase 1 — Read-only surfaces only (the fast "company can reach it" win)
Exposes the value the plan wants without exposing a path to live mutations. Requires G1, G2, G4.
1. **MER dashboard**: already behind Cloudflare Access; confirm origin lockdown (G1) and fold into the registry.
2. **Ads Control Center in view-only mode**: ✅ DONE 2026-07-13 (Section 0). Deployed to Railway
   as `ads-control-center` behind in-app Google OAuth; all POSTs 403 except admin `/pull`
   (snooze included, stricter than planned -- see the split-brain rationale in Section 0);
   SQLite on a Railway volume; scheduler timezone fixed via `control_center/clock.py`;
   secrets as Railway variables referencing the `googleads-mcp` service.
3. **Read-only reporting MCP tools**: ✅ effectively done via the hosted `googleads-mcp` role map
   (viewer grants see only readOnlyHint tools; `MCP_ADMIN_ONLY_TOOLS` fences `commit_*`).

Outcome: browser users across the company reach the dashboards through one SSO, immediately, with no write exposure.

### Phase 2 — Write-capable MCP servers (only after G3, G4, G5, G7, G8, G10)
Convert each from stdio to Streamable HTTP (the only transport to target; HTTP+SSE is deprecated):
```python
import os
mcp.run(transport="http", host="0.0.0.0", port=int(os.environ["PORT"]))
```
Keep servers **dual-mode**: stdio locally for development, HTTP when `PORT` is set in the container, so Claude Code keeps working locally and prod runs hosted from the same code.

Order, each becoming the template for the next:
1. **Google Ads MCP** (template; also where the MCP-behind-per-user-OAuth design is proven). Persist `audit.db` to a volume.
2. **Shopify MCP** (persist `rollbacks/`; extend the existing mutation allowlist coverage).
3. **Klaviyo MCP** (persist `rollbacks/` + `audit.log`; add a per-operation allowlist parallel to Shopify's, since the client currently exposes generic `post/patch/delete` guarded only by PII-path blocking).

### Phase 3 — Control Center write mode + registry
- Enable the Control Center commit/stage routes only after G5 (real approval gate, Section 10
  proposal) is built. G6 (CSRF) is already implemented and pre-wired into the write-route
  templates; the write enablement inherits it.
- Write enablement also includes: retiring the local launchd instance (or demoting it to
  emergency-only) so there is one decision database; threading actor emails into
  `control_center_change_log` and the staged/approved rows; flipping `CC_ALERTS_ENABLED`.
- Publish one internal registry page (Confluence is already connected, or a README) listing each endpoint URL, what it does, and how to add it as a connector.

---

## 6. Cost estimate

| Item | Estimate |
|---|---|
| Railway compute (≈5 small always-on Python services + volumes) | ~$20 to $40 / mo total |
| Cloudflare Access (Zero Trust free tier, up to 50 users) | $0 (already in use) |
| **All-in** | **~$20 to $40 / mo** |

For context, Letaido is $99/mo entry (the AI-citation use case sits behind a $699 Brand Radar bundle), and it would not host your own Starlette/Streamlit apps at all. Self-hosting on tools already owned is cheaper and broader for this need.

---

## 7. Other risks and gotchas

1. **Scheduler timezone (correctness, not cosmetic).** ✅ FIXED 2026-07-13: all control-center
   time math routes through `control_center/clock.py` (`CC_TIMEZONE`, tzdata dependency), so
   pull times, snooze windows, and cooldown math are operator-local regardless of container TZ.
2. **Secret Manager stub.** `ads_mcp/auth.py` raises `NotImplementedError` for cloud mode. Sidestepped: hosted services set `GOOGLE_ADS_SERVICE_ACCOUNT_JSON` (inline JSON, checked first in `get_credentials`); only implement the stub if moving to GCP.
3. **Dropbox / SQLite.** The repos live in Dropbox, which corrupts SQLite WAL files (the Control Center DB was deliberately moved out of Dropbox for this reason). Containers remove the problem; just never mount a Dropbox path into a container.
4. **EU data residency.** Shopify storefronts likely process EU customer personal data. Routing 18 stores through a US Railway host needs a residency/DPA check. The Klaviyo PII-path block helps, but Shopify order/sales queries may surface personal data. Confidence: medium, depends on store geography and which tools are actually called.
5. **Incident response / kill switch.** No current plan for fast access cutoff + credential rotation if a token or container is compromised. Add one before exposure.
6. **Container hardening.** Run non-root, read-only filesystem where possible, minimal base image. Not addressed today.

---

## 8. Corrections to earlier claims

- **".env files committed with plaintext creds" was NOT confirmed.** The security review checked git history in both repos: `.env` and `credentials/` are correctly gitignored and absent from history; only `.env.example` and non-secret config JSON are tracked. The secrets-in-git risk appears not real. The operational secret-sprawl risk under Railway env vars (G9) is separate and stands.

---

## 9. Open question before execution

Confirm the MER dashboard's actual code location and host, so it is captured in the registry and its origin lockdown (G1) is verified rather than assumed. Everything else can proceed on the Phase 0 decisions above.

---

## 10. G5 approval-gate design (PROPOSAL -- awaiting Adam's sign-off, not built)

This is the design that unlocks hosted writes (Phase 3). It replaces approval-by-bare-cell
with a plan-bound, single-use, expiring, actor-attributed approval, closing every failure
mode listed in Section 3. Nothing below is implemented; the hosted dashboard stays read-only
until Adam approves this section (or an amended version) and it ships.

### Core object: the change plan

A new `change_plans` table in the control-center DB:

```
change_plans(
    id            TEXT PRIMARY KEY,      -- UUID4, unguessable
    kind          TEXT NOT NULL,         -- troas_budget_batch | negatives_batch | campaign_creation
    payload       TEXT NOT NULL,         -- immutable JSON snapshot of the exact changes
    created_by    TEXT NOT NULL,         -- actor email
    created_at    TEXT NOT NULL,
    approved_by   TEXT,                  -- actor email, admin role required
    approved_at   TEXT,
    approval_expires_at TEXT,            -- approved_at + 15 minutes
    committed_by  TEXT,                  -- actor email
    committed_at  TEXT,
    status        TEXT NOT NULL          -- draft | approved | committed | expired | cancelled
)
```

### Flow (Control Center UI)

1. **Stage** (admin): staging rows creates or updates a DRAFT plan whose payload is a frozen
   snapshot of the staged diffs. Any later edit to staged rows invalidates the draft and makes
   a new plan id. What you approve is exactly what commits, byte for byte.
2. **Approve** (admin): the review screen renders the plan payload and an Approve button.
   Approval stamps `approved_by` + `approval_expires_at` (15 min). One approval per plan.
3. **Commit** (admin): `POST /commit` now REQUIRES `plan_id`. The server verifies, atomically
   (single SQL transaction): status is `approved`, not expired, payload hash matches the staged
   rows, and flips status to `committed` before the first mutate call -- making the approval
   single-use even under concurrent requests. Approver and committer emails are written to
   `control_center_change_log` (new columns: `plan_id`, `approved_by`, `committed_by`).
4. **Two-person option** (config flag `CC_REQUIRE_SEPARATE_APPROVER`, default off while the
   org is one operator): commit rejects when `committed_by == approved_by`.

### Same gate for the MCP commit tools

`commit_troas_changes()` / `commit_budget_changes()` / `commit_all_changes()` gain a required
`plan_id` argument (finally matching the documented-but-never-built design in CLAUDE.md Phase 3);
the bare no-argument forms are removed from HTTP mode. The Sheets Decision column stays as the
review convenience but stops being the gate: commit applies the plan payload, not "whatever is
currently marked Approve."

### Consolidation prerequisite

Before enabling hosted writes, collapse the three-DB seam (Section 0): either point the CC
service and the googleads-mcp service at one Postgres, or declare the hosted CC DB the single
decision store and retire the local instance. Approvals recorded in one DB and committed from
another would rebuild the split-brain this design exists to prevent.

### Effort estimate

Schema + plan lifecycle + UI changes + MCP tool signatures + tests: roughly one focused session.
The CSRF, session, role, and audit plumbing it depends on shipped with the read-only migration.
