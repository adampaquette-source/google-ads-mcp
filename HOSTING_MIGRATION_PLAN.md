# Hosting and Centralization Migration Plan

Goal: get the custom MCP servers and local utility web apps off Adam's laptop and onto a cloud host so the tooling is centralized and reachable by anyone in the company. Two consumption modes confirmed:

1. **MCP clients** (Claude Desktop / claude.ai connectors / Claude Code) reaching the MCP servers as remote connectors.
2. **Web UI** (browser) for non-technical staff opening the dashboards directly.

Recommended stack (unchanged from the scoping discussion): **Railway** for compute (one project, one service per server/app, GitHub-connected deploys) plus **Cloudflare Access** federated to Google Workspace as the single front door. Both are tools the company already runs. The MER dashboard already sits behind Cloudflare Access, so the access pattern is proven; this plan generalizes it to everything else.

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
| **Ads Control Center** | `Google Ads MCP/control_center/app.py` (uvicorn) | Starlette | binds `127.0.0.1:8770`, launchd service, **no auth** | SQLite in `~/Library/Application Support/ads-control-center/`; scheduler at 07:00 / 12:30 / 17:30 local time |
| **MER dashboard** | (confirm location) | already exposed behind Cloudflare Access | already partly solved | n/a |

### Things that should NOT be hosted (stay local / CI)

- `toolup-themes/scripts/deploy.sh` and the theme deploy/backup scripts (they push themes to Shopify from a trusted host; file-based locks; not a service).
- `email-gif-builder` and other `.claude/skills/` scripts (invoked ad hoc by Claude Code, stateless).
- `scripts/smoke_test.py`, `run_product_exclusion.py`, `.migration/` audit scripts (one-off, run by hand).

---

## 2. The two hard parts (everything else is mechanical)

Most of this is boilerplate. Two pieces deserve real attention:

**A. Auth for MCP servers behind SSO.** Browser SSO for the web apps is trivial (Cloudflare Access in front, Google login, done; same as the MER dashboard today). Putting an MCP endpoint behind auth that an MCP *client* can negotiate is the one genuinely fiddly piece. Two viable paths:
- **Service tokens** (Cloudflare Access): issue a token per consumer, the MCP client sends it as a header. Simple, works now, but it is a shared static credential per client rather than per-person SSO.
- **Cloudflare's MCP / remote-OAuth support**: per-user OAuth through the same Google Workspace identity. Cleaner and audited per person, but more setup.
- **Recommendation:** validate this with a one-server spike (Google Ads MCP) before converting the other two. Do not convert all three and then discover the auth shape.

**B. Persistent state in containers.** Containers are ephemeral. Anything written to local disk vanishes on redeploy. These must move to a Railway volume (or a managed DB):
- `audit.db` (Google Ads), `audit.log` (Klaviyo), `mcp/rollbacks/` and `accounts/*/rollbacks/` (Shopify/Klaviyo), control center SQLite.
- Audit logs and rollback snapshots are the load-bearing ones. Losing them silently breaks the proposal/commit safety model. Volume now; consider Postgres for the audit trail later.

---

## 3. Migration order

Sequenced lowest-risk-first, and so each phase produces a reusable template.

### Phase 0 — Decisions and prep (no deploy)
- Lock platform: Railway. Lock secrets home: **Railway secrets** (one platform; avoids implementing the GCP Secret Manager stub in `ads_mcp/auth.py`, which currently raises `NotImplementedError` for `ADS_MCP_ENV=cloud`). Feed the Google service account JSON in as a Railway secret/var rather than a checked-in file.
- Lock auth: Cloudflare Access, federated to Google Workspace, in front of every endpoint.
- Confirm where the MER dashboard actually runs so it folds into the same registry.

### Phase 1 — Web apps first (fastest "company can reach it" win)
1. **Ads Control Center** to Railway:
   - Bind `0.0.0.0` and read `PORT` from env (currently hardcoded `127.0.0.1:8770`).
   - Move SQLite onto a Railway volume.
   - Replace the launchd scheduler. Either a Railway cron service or keep the in-process scheduler but set the container `TZ` (it currently assumes local Pacific time; containers default to UTC, so 07:00/12:30/17:30 would fire at the wrong hours).
   - Inject `.env` values as Railway secrets.
   - Put Cloudflare Access in front. Non-technical staff get a URL and a Google login. No MCP client needed.
2. **MER dashboard**: already behind Cloudflare Access; just confirm it is on the same host/registry.

Outcome: every browser user in the company can reach the dashboards through one SSO, immediately.

### Phase 2 — MCP servers to HTTP, one at a time
Convert each from stdio to Streamable HTTP (the only transport to target; HTTP+SSE is deprecated). FastMCP makes this small:
```python
import os
mcp.run(transport="http", host="0.0.0.0", port=int(os.environ["PORT"]))
```
Order, each becoming the template for the next:
1. **Google Ads MCP** (the worked template; also where we validate the MCP-behind-SSO auth from part 2A). Persist `audit.db` to a volume; secrets to Railway.
2. **Shopify MCP** (persist `rollbacks/`; 36 creds to Railway).
3. **Klaviyo MCP** (persist `rollbacks/` + `audit.log`; 9 keys to Railway).

Keep the servers **dual-mode** if easy: stdio when run locally for development, HTTP when `PORT` is set in the container. That way Claude Code keeps working locally and prod runs hosted from the same code.

### Phase 3 — Registry and onboarding
- One internal page (Confluence is already connected, or a README) listing each endpoint URL, what it does, and how to add it as a connector. This is the "centralized, discoverable" half of the goal.

---

## 4. Cost estimate

| Item | Estimate |
|---|---|
| Railway compute (≈5 small always-on Python services + volumes) | ~$20 to $40 / mo total |
| Cloudflare Access (Zero Trust free tier, up to 50 users) | $0 (already in use) |
| **All-in** | **~$20 to $40 / mo** |

For context, Letaido is $99/mo entry (and the headline AI-citation use case sits behind a $699 Brand Radar bundle), and it would not host your own Streamlit/Starlette apps at all. Self-hosting on tools you already own is both cheaper and broader for this need.

---

## 5. Risks and gotchas (carry into execution)

1. **MCP-behind-SSO auth** is the one non-trivial design choice. Spike it on Google Ads MCP first (see 2A).
2. **State persistence**: audit logs and rollback snapshots must land on volumes or they disappear on redeploy and break the safety model (2B).
3. **Scheduler timezone**: the control center fires on local Pacific times; set container `TZ` or convert, or jobs run at the wrong hour.
4. **Secret Manager stub**: `ads_mcp/auth.py` raises `NotImplementedError` for cloud mode. Sidestepped by using Railway secrets and keeping the file-path code path, OR implement the stub if you later move to GCP.
5. **Dropbox / SQLite**: the whole repo lives in Dropbox and the control center DB was deliberately moved out of it because Dropbox corrupts SQLite WAL files. Containers remove this problem entirely; just do not mount a Dropbox path into a container.
6. **Local vs hosted cutover**: decide whether Claude Code keeps using the local stdio servers or points at the hosted HTTP ones. Dual-mode (Phase 2) avoids forcing the choice.

---

## 6. Open question before execution

The only thing that blocks starting Phase 1 cleanly: confirm the MER dashboard's actual code location and host, so it is captured in the registry rather than left as a one-off. Everything else above can proceed on the decisions in Phase 0.
