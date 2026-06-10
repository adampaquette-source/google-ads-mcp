# Phase 0 Checklist — Do These Before Any Code

**Update (May 18, 2026):** Adam confirmed an existing Google Ads API developer token is already in production use by an internal engineer for a weekly product-labels script. We are reusing that token. Auth is **service account + JWT**, not OAuth — the engineer's existing pattern. This skips the OAuth browser-consent flow entirely and is simpler to operate, both locally and in cloud. The labels script consumes 4-8 API ops/day, so the entire 15,000 ops/day Basic Access quota is effectively available to the MCP.

## Save credentials here as you go

Open a notes file (or 1Password / your password manager) and capture each value as you generate or collect it.

```
GOOGLE_ADS_DEVELOPER_TOKEN              = ___ (from API Center, step 1)
GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH    = ./ads-mcp-sa-key.json (the file lives in project root, step 2)
GOOGLE_ADS_LOGIN_CUSTOMER_ID            = ___ (your MCC ID, no dashes, step 3)
GOOGLE_CHAT_WEBHOOK_URL                 = ___ (from step 4)
SLACK_WEBHOOK_URL                       = ___ (from step 5)
```

---

## 1. Copy the existing developer token

You found this already. From the Google Ads MCC, go to **Tools & Settings → Setup → API Center** (or directly at https://ads.google.com/aw/apicenter). Copy the 22-character developer token. That's `GOOGLE_ADS_DEVELOPER_TOKEN`.

While you're there, note the access level shown. We're assuming Basic Access. If it's Standard, even better.

---

## 2. Get a service account JSON key from your engineer

Send him this request:

> "Could you spin up a separate service account for the MCP project (something like `ads-mcp-sa@<project>.iam.gserviceaccount.com`), generate a JSON key, send me the key file, and add the service account as a user on the MCC with Standard access (not Read-only — Phase 3 writes will need it)?"

A separate service account is cleaner than sharing the labels job's one because revocation or rotation won't affect the other tool. If he insists on reusing the existing service account, that works too, just confirm:

- The service account is added as a user on the **MCC** (not just on individual sub-accounts)
- The access level on the MCC is **Standard** or **Admin**, not Read-only

**When the JSON key file arrives:**

1. Save it to the project root with the filename `ads-mcp-sa-key.json` (or whatever Claude Code names it during scaffold).
2. Treat it like a password. Anyone with that file can act as the service account. The file MUST be gitignored. Claude Code will set that up.
3. You do not need to extract any values from it. The Python code reads the file directly.

---

## 3. Note your MCC login customer ID

1. In Google Ads at https://ads.google.com with the MCC selected, look at the top-right corner. The customer ID is shown with dashes, like `123-456-7890`.
2. Remove the dashes. That's `GOOGLE_ADS_LOGIN_CUSTOMER_ID` = `1234567890`.

---

## 4. Set up the Google Chat webhook

1. Open Google Chat.
2. Create a new **Space**. Suggested name: `Ads MCP Updates`. Just yourself for now.
3. Click the space name at top → **Apps & integrations** → **Webhooks** → **Add webhook**.
4. Name: `Ads MCP Worker`. Avatar URL optional.
5. Click **Save**.
6. **Copy the webhook URL.** That's `GOOGLE_CHAT_WEBHOOK_URL`.

If you don't see the Webhooks option, your Google Workspace admin may have disabled it. Either ask them to enable it or rely on the Slack backup as primary.

---

## 5. Set up the Slack workspace (backup)

1. Go to https://slack.com/get-started and create a free workspace. Suggested name: `adam-agentic` or similar. Just you as a member.
2. Create a channel: `#ads-mcp-updates`.
3. Go to https://api.slack.com/apps and click **Create New App → From scratch**.
4. App name: `Ads MCP Worker`. Pick your workspace.
5. In the app settings, click **Incoming Webhooks** → toggle **Activate Incoming Webhooks** ON.
6. Scroll down → **Add New Webhook to Workspace** → pick `#ads-mcp-updates` → **Allow**.
7. **Copy the webhook URL.** That's `SLACK_WEBHOOK_URL`.

---

## 6. Create the Dropbox digests folder

1. Inside your existing folder `Claude CoWork/0001 - Google Ads/001-Google Ads MCP Project/`, create a subfolder called `digests`.
2. The digest worker will write `YYYY-MM-DD_daily.md` and `YYYY-MM-DD_weekly.md` files here once Phase 2 is built.

---

## 7. (Optional, but recommended) Stand up a GitHub repo

1. Go to https://github.com/new.
2. Name: `ads-mcp` (or whatever you like). **Private.**
3. Don't initialize with a README; Claude Code will set up the project structure locally and push.
4. Note the SSH or HTTPS clone URL.

---

## Once all of the above is done

You're ready to start the Phase 1 build with Claude Code.

1. Open a Claude Code session in this folder (`001-Google Ads MCP Project`).
2. Claude Code will read `CLAUDE.md` in this folder for full project context, including the service-account auth pattern.
3. First request to Claude Code: "Let's scaffold the project per CLAUDE.md. The service account JSON key is in the project root. Build the auth + client modules, then ship `list_accounts` as the first verified tool against my MCC."

That single prompt is enough. Claude Code will take it from there.
