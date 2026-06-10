# Google Ads Digest Skill

Parameterized execution skill for daily and weekly cross-platform digests.
Invoked by scheduled tasks or manually. Run all steps autonomously without asking for confirmation.

For business rationale, alert logic detail, and edge case explanations see DIGEST_SOP.md.

---

## Parameters

| Parameter | Daily | Weekly |
|---|---|---|
| date_range | LAST_7_DAYS | LAST_30_DAYS |
| shopify_days | 14 | 60 |
| current_period_days | 7 | 30 |
| narrative_mode | concise | detailed |
| narrative_limit | 3000 chars | 3500 chars |

---

## Step 1 -- Google Ads digest + Sheets dashboard

Call `get_google_ads_cross_account_digest` with the date_range parameter. Save the full result as `digest_data`.

Call `update_google_ads_sheets_dashboard` passing `digest_data`. Save the returned `dashboard_url`.
If this returns a 403 error, note it and continue without a dashboard link.

---

## Step 2 -- Google Ads MER spend data

Call `get_google_ads_mer_data` with the same date_range. Save the result as `ads_mer_data`.
This returns Google Ads spend per store keyed by `shopify_key`.

---

## Step 3 -- Shopify net sales per store (current + prior periods)

For each store in `ads_mer_data.stores` where cost > 0:
- Call `shopify_query_sales` with `store_key=<shopify_key>`, `metrics=["net_sales"]`, `dimensions=["day"]`, `days=<shopify_days>`, `limit=500`
  - This returns up to 14 days of daily rows (daily mode) or 60 days (weekly mode).
- Read the full CSV file at the returned file path.
- Each row has a date column. Split rows into two periods based on date:
  - Current period: rows where date >= (today minus <current_period_days> days). Sum net_sales.
  - Prior period: remaining rows (the earlier half). Sum net_sales.
  - Include negative values in both sums -- do not zero out returns.
- Stores that error or return no rows: net_sales=0, prior_net_sales=0.

Build two dicts from this step:
- `net_sales_by_key`: shopify_key -> current period net_sales
- `prior_net_sales_by_key`: shopify_key -> prior period net_sales

Skip `weather-guard-store` (No Spend, $0 ads cost).

---

## Step 4 -- Assemble and write MER report

MER formula: Ad Spend % = (cost / net_sales) x 100. Lower is better.

Status thresholds:
- Strong: <= 5%
- Good: 5 to 10%
- Watch: 10 to 20%
- Poor: > 20%
- No Sales: net_sales = 0 with cost > 0
- No Spend: cost = 0

Portfolio MER = (total_cost / total_net_sales) x 100.

Build `mer_data` dict:
```
{
  "date_range": "<date_range parameter>",
  "generated_at": "<ISO timestamp>",
  "total_cost": <sum of all store costs>,
  "total_net_sales": <sum of all store net_sales>,
  "portfolio_mer": <(total_cost / total_net_sales) * 100, rounded to 2>,
  "portfolio_mer_status": <per thresholds above>,
  "total_prior_net_sales": <sum of all store prior_net_sales>,
  "portfolio_prior_mer": <(total_prior_cost / total_prior_net_sales) * 100, rounded to 2; 0 if no prior data>,
  "portfolio_mer_delta": <portfolio_mer - portfolio_prior_mer, rounded to 2; 0 if no prior data>,
  "portfolio_trend": <"Improving" | "Worsening" | "Stable" | "No Prior Data">,
  "stores": [
    {
      "shopify_key": "...",
      "store_name": "...",
      "ads_customer_id": "...",
      "cost": ...,
      "net_sales": ...,
      "mer": <(cost / net_sales) * 100 if net_sales > 0, else 0>,
      "mer_status": <per thresholds above>,
      "prior_net_sales": <from prior_net_sales_by_key>,
      "prior_mer": <(prior_cost / prior_net_sales) * 100 if prior_net_sales > 0, else 0>,
      "mer_delta": <mer - prior_mer; positive = worsening; 0 if no prior data>,
      "trend": <"Improving" | "Worsening" | "Stable" | "No Prior Data">
    },
    ...
  ]
}
```

Call `update_mer_report_tab` passing `mer_data`. Save the returned `mer_tab_url`.
If this errors, note it and continue without a MER link.

---

## Step 5 -- Assemble card data

Assemble a `card_data` dict and pass it to `post_digest_card_to_google_chat` in Step 6.
All fields are plain text or structured dicts -- the card builder applies all color tokens
and HTML formatting automatically. No raw HTML needed except `strategic_summary_html`.

**Scalar fields:**

| Field | Type | Source |
|---|---|---|
| `date_str` | str | Today as "Month DD, YYYY" (e.g. "May 21, 2026") |
| `date_range_label` | str | "Last 7 Days" (daily) or "Last 30 Days" (weekly) |
| `portfolio_mer` | float | `mer_data.portfolio_mer` |
| `portfolio_mer_status` | str | `mer_data.portfolio_mer_status` |
| `portfolio_trend` | str | `mer_data.portfolio_trend` |
| `portfolio_mer_delta` | float | `mer_data.portfolio_mer_delta` (negative = improving) |
| `total_net_sales` | float | `mer_data.total_net_sales` |
| `total_cost` | float | `mer_data.total_cost` |
| `portfolio_roas` | float | `digest_data.total_roas` |
| `total_conversions` | float | `digest_data.total_conversions` |
| `total_clicks` | int | `digest_data.total_clicks` |
| `budget_pacing_note` | str | Plain text pacing summary (see below); empty string if no underpacing |
| `disapproval_count` | int | Total disapproval count across all accounts |
| `strategic_summary_html` | str | Weekly only; empty string for daily (HTML ok here) |
| `dashboard_url` | str | From Step 1 or empty string if unavailable |
| `mer_tab_url` | str | From Step 4 or empty string if unavailable |

---

**`mer_stores` -- list of store dicts**

Include all stores where cost > 0, sorted by MER ascending (best first).
The card builder groups them into Best and Watch/Poor automatically.

```python
mer_stores = [
    {"name": "ToolUp",        "mer": 2.1, "status": "Strong", "spend": 3200.0,  "net_sales": 152000.0},
    {"name": "Dewalt",        "mer": 4.3, "status": "Strong", "spend": 1800.0,  "net_sales": 41900.0},
    {"name": "Sumner Outlet", "mer": 18.5, "status": "Watch", "spend": 2100.0,  "net_sales": 11300.0},
]
```

Status values: "Strong" (<= 5%), "Good" (5-10%), "Watch" (10-20%), "Poor" (> 20%), "No Sales".

---

**`troas_alerts` -- list of flagged campaign dicts**

Tier-aware: include all Tier 1 flagged campaigns. Include Tier 2/3 only if drift_pct > 30%
or actual_roas = 0.

```python
troas_alerts = [
    {"account": "ToolUp",          "campaign": "PMax",         "actual_roas": 3.1, "target_roas": 4.0, "drift_pct": -22.0, "status": "UNDER"},
    {"account": "Red Tool Store",  "campaign": "Brand Search", "actual_roas": 1.8, "target_roas": 2.5, "drift_pct": -28.0, "status": "UNDER"},
]
```

Empty list if no alerts.

---

**`zero_conv_accounts` -- list of zero-conversion account dicts**

```python
zero_conv_accounts = [
    {"account": "Sumner Outlet", "spend": 420.0},
]
```

Empty list if none.

---

**`budget_overpacing` -- list of overpacing campaign dicts**

```python
budget_overpacing = [
    {"account": "ToolUp", "campaign": "Brand PMax"},
]
```

Empty list if none.

---

**`disapproval_accounts` -- list of account name strings**

```python
disapproval_accounts = ["Gearwrench Shop", "Hand Tool Outlet"]
```

Empty list if all accounts clean.

---

**`priority_actions` -- list of plain text strings**

2-5 specific, actionable items. Builder numbers them automatically.

```python
priority_actions = [
    "Review ToolUp PMax tROAS -- actual ROAS 3.1 is 22% below target 4.0; consider loosening to 3.5",
    "Red Tool Store Brand Search underperforming; check budget cap and search impression share",
    "Sumner Outlet Ad Spend % at 18.5% -- investigate return rate or pause low-ROAS campaigns",
]
```

---

**`budget_pacing_note` -- plain text**

- Before 09:00 local (before ~16:00 UTC): "X accounts underpacing -- early-day, monitor at end of day."
  Do not list individual campaigns.
- After 09:00 local: list underpacing accounts by name in the note.
- If no underpacing and no overpacing: empty string (budget_overpacing list handles OVERPACING display).

---

**`strategic_summary_html` -- weekly only**

3-5 sentences: what is performing well, what needs attention, one concrete recommended action.
Plain text is fine; use `<b>` sparingly if needed. No em dashes.

```
ToolUp and Red Tool Store continue to anchor the portfolio. The primary concern this week is
MTS Standard Shopping persisting at 0 ROAS despite $340 spend -- this campaign should be reviewed
or paused. Three Tier 2 accounts improved Ad Spend % this period, suggesting recent tROAS
tightening is working. Recommended action: investigate MTS Standard Shopping conversion tracking
and consider a 30-day pause while diagnosing.
```

For daily: set `strategic_summary_html` to `""`.

---

## Step 6 -- Post to Google Chat

Call `post_digest_card_to_google_chat` with the assembled `card_data` dict.

---

## Quick reference: store to shopify_key mapping

| Account Name | shopify_key |
|---|---|
| ToolUp | toolupstore |
| Themilwaukeestore.com | the-milwaukee-store |
| Authorizedtooloutlet.com | the-dewalt-store |
| Electrician Shop | greenlee-store |
| Total Fastening | fasteners-store |
| Gearwrench Shop | gearwrench-shop |
| Tool Belt Outlet | occidentalleatheroutlet |
| Sumner Outlet | the-sumner-store |
| Plumbingtoolstore.com | the-ridgid-store |
| MyToolStore Official | toolup-my-tool-store |
| Jobsite Power Tools | the-makita-store |
| Fall Protection Depot | fall-protection-store |
| Jobsite Tool Boxes | knaack-store |
| PLS Store | the-pls-store |
| Hand Tool Outlet | the-klein-store |
| Pro Work Supply | wood-shop-outlet |
| Weather Guard Store | weather-guard-store (skip -- No Spend) |
