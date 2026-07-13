# Hosting and Centralization Migration Plan

> **Addendum 2026-07-12 (Adam):** Control Center migration to Railway is GREENLIT as active work.
> Sequencing per this plan still applies: read-only dashboard can ship first; the commit/stage
> routes stay LOCAL-ONLY until G5 (real approval gate) and G6 (CSRF) are built. Migration scope:
> SQLite -> Railway volume or Postgres (decide), launchd service -> Railway service (scheduler.py
> already runs in-process), secrets -> Railway env vars (service account JSON via env, mirroring
> the MCP server's GOOGLE_ADS_SERVICE_ACCOUNT_JSON pattern), auth in front of the web UI before
> ANY exposure (even read-only), alerts unchanged (outbound webhooks). Note this doc predates the
> 2026-07-07/08 Docker/railway/authz commits and needs a refresh pass against the as-built state.

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
2. **Ads Control Center in view-only mode**: deploy with `/commit`, `/stage`, `/snooze`, `/pull` disabled (or returning 403). Read dashboards only. Move SQLite to a Railway volume; fix the scheduler timezone (Section 6); inject secrets as Railway secrets.
3. **Read-only reporting MCP tools** (if MCP auth is ready per G7): expose the reporting/health tools, not the commit tools. If MCP per-user auth is not ready, defer all MCP to Phase 2.

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
- Enable the Control Center commit/stage routes only after G5 (real approval gate) and G6 (CSRF) are in place.
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

1. **Scheduler timezone (correctness, not cosmetic).** The Control Center scheduler is in-process and fires at 07:00 / 12:30 / 17:30 local Pacific. Cooldown math (`_troas_cooldown_hit`, `TROAS_COOLDOWN_DAYS`) uses naive `datetime.now()`. In a UTC container, cooldown windows and snooze math shift by the offset, which can let staged changes slip a safety rail. Set container `TZ` and make time math timezone-aware before exposure.
2. **Secret Manager stub.** `ads_mcp/auth.py` raises `NotImplementedError` for cloud mode. Sidestepped by using Railway secrets and the file-path code path; only implement the stub if moving to GCP.
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
