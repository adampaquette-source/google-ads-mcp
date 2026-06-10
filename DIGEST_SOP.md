# Daily Digest SOP

*Distilled from the May 2026 reporting consultation and live session tuning. Read this before generating any digest, whether triggered by the scheduler or run manually.*

---

## What the digest is

A cross-platform performance summary covering all 18 active Google Ads accounts and their paired Shopify stores. Delivered to Google Chat each morning. The daily digest covers LAST_7_DAYS; the Monday weekly digest covers LAST_30_DAYS and goes deeper.

Audience: Adam (operational detail) and the VP (executive summary only). The Chat message serves both -- lead with the headline numbers, put action items at the bottom.

---

## Tool sequence

Run these steps in order. Steps 1 and 3 can be called simultaneously since they are independent.

1. `get_google_ads_cross_account_digest` (date_range: LAST_7_DAYS daily, LAST_30_DAYS weekly)
2. `update_google_ads_sheets_dashboard` -- passes the full digest_data dict from step 1
3. `get_google_ads_mer_data` (same date_range) -- returns Google Ads spend keyed by shopify_key
4. `shopify_query_sales` -- one call per store, metrics=["net_sales"], dimensions=["day"], days=7 (or 30). Read the full CSV at the returned file path and sum the net_sales column. Stores with no data or errors get net_sales=0.
5. `update_mer_report_tab` -- passes the assembled mer_data dict (see MER section below)
6. Write narrative, then `post_digest_to_google_chat`

If `update_google_ads_sheets_dashboard` returns a 403, the service account does not have Editor access to the spreadsheet. Note the error but continue. Post the Chat message without a dashboard link.

---

## Account tiers

Tier assignment is dynamic, based on monthly spend rank. Toolup and Red Tool Store are permanently Tier 1 regardless of spend.

| Tier | Accounts | Review Cadence | Digest Treatment |
|---|---|---|---|
| Tier 1 | Toolup, Red Tool Store, + top 3 by spend | Daily | Named scorecard, per-campaign detail on all alerts |
| Tier 2 | Middle 5 by spend | Weekly | Account-level in weekly; named in daily only if an alert fires |
| Tier 3 | Remaining 8 | Bi-weekly | Account-level in weekly only, unless critical flag |

In practice for the daily narrative: always name Tier 1 campaigns explicitly. For Tier 2/3, name the account and the alert type but skip per-campaign breakdown unless the alert is severe (e.g. zero conversions for 2+ consecutive days or tROAS drift > 50%).

---

## MER calculation

MER = Ad Spend % = (Google Ads Spend / Shopify Net Sales) x 100

Lower is better. A 4.3% MER means $4.30 in ads per $100 in net sales.

| Status | Threshold |
|---|---|
| Strong | <= 5% |
| Good | 5 - 10% |
| Watch | 10 - 20% |
| Poor | > 20% |
| No Sales | net_sales = 0 with ads spend present |
| No Spend | ads cost = 0 |

Portfolio MER = (total ads spend across all stores / total net sales across all stores) x 100.

The `mer` field in `MerReportRow` and `MerReportData` stores the raw float (e.g. 4.3 means 4.3%). Display with a % suffix in all user-facing output.

In the Chat narrative, lead with portfolio MER, then flag any stores with Poor or No Sales status that have meaningful spend (> $50/day equivalent).

---

## Alert logic

### tROAS drift
- Compare actual 7-day ROAS vs campaign target_roas.
- Flag when deviation exceeds the drift_pct threshold (default 10%).
- Status: OVER (actual > target), UNDER (actual < target), ON_TRACK.
- In the narrative: name the campaign, state target vs actual, and the drift percentage. Do not simply say "tROAS alert" -- give the numbers.
- Tier 1: report all flagged campaigns. Tier 2/3: report only if drift > 30% or actual ROAS = 0.

### Zero conversion alerts
- Tier 1 accounts: zero conversions within a 4-hour window during active hours = immediate priority.
- Tier 2/3 accounts: zero conversions persisting for 2+ consecutive days = flag in digest.
- If the digest data shows an account with 0 conversions and > $200 spend for the LAST_7_DAYS window, flag it regardless of tier.

### Budget pacing
- Philosophy: budget caps are opportunity signals, not warnings. A campaign consistently hitting its daily budget cap should be flagged for a budget increase review, not flagged as overspending.
- UNDERPACING alerts: interpret with awareness of time of day. If the digest runs before 9am local time (before roughly 16:00 UTC), widespread UNDERPACING across many accounts is normal and should be noted as "early-day pacing, monitor at end of day" rather than listed as individual alerts.
- OVERPACING alerts: always flag regardless of time of day.
- A campaign at 95%+ of daily budget for 3+ consecutive days = flag as "Budget Constrained -- Review for Increase."

### Spend anomaly
- Currently uses pacing ratio vs expected spend. Future: adaptive 6-month volatility baseline (Priority 3 on the build stack).
- Do not use a fixed +/-50% threshold. Smaller accounts have higher natural day-over-day volatility.

---

## Campaign attention framework

When naming campaigns in the narrative, classify them into one of three states:

| State | Signal | How to surface it |
|---|---|---|
| Underspending | Period-over-period downward spend trend, or heavy underpacing | "Investigate: budget cap, disapproval, quality issue, bid too restrictive" |
| Overspending | ROAS consistently below target | "tROAS tighten or pause review" |
| Accelerating | Spend increasing AND on/near tROAS target | "tROAS loosen or budget increase to capture more volume" |

---

## Card format rules

The Chat message uses Google Chat cardsV2 format (structured card, not plain text).
The card builder in `ads_mcp/notify.py` handles the JSON structure. Claude's job is to
populate the `_html` fields and the structured metric fields.

**HTML field rules**
- Use `<b>label</b>` for section labels and key values
- Use `<br>` for line breaks
- No em dashes. Use `--` or commas instead.
- No markdown (no asterisks, no `## headers`)
- No bullet point characters

**Metric fields** (portfolio_mer, total_net_sales, etc.) are plain numbers; the card
builder handles formatting (currency symbols, decimal places, trend arrows).

**Card section order (daily)**
1. Portfolio Overview: Ad Spend % (decoratedText widget), net sales, ads spend, ROAS, conversions, clicks
2. Ad Spend % by Store: best performers, then Watch/Poor stores with spend context
3. Alerts: tROAS, zero conversions, budget pacing, disapprovals
4. Priority Actions: 2-5 specific numbered items
5. Link buttons: Ads Dashboard, MER Report (omitted if URLs unavailable)

**Card section order (weekly, adds)**
- After Priority Actions: Strategic Summary (3-5 sentences, one concrete recommendation)

---

## Shopify stores mapping

All 18 stores have a 1-to-1 mapping between shopify_key and Google Ads customer_id in `stores_mapping.json` at the project root. The Jet Tool Store (customer_id 5796649170) is SUSPENDED in Google Ads and has no active Shopify presence -- skip it. Powermatic Tool Store (2923679101) is SUSPENDED with no Shopify counterpart -- skip it.

Use `shopify_key` as the `store_key` parameter in `shopify_query_sales`.

---

## Known edge cases

- **Sumner Outlet** has had large negative net_sales days (bulk returns/refunds). A negative total for the period is valid data -- do not zero it out. Note it in the digest as "net returns period."
- **MyToolStore Official (MTS)** Standard Shopping campaigns frequently show 0 ROAS. These run on TROAS bidding set to 8.5 but have historically had conversion issues. Flag consistently if persisting.
- **Weather Guard Store** has $0 Google Ads spend. It appears in the stores mapping but will never have ads data. Skip in MER calculations (No Spend status).
- **Makita/JPT (Jobsite Power Tools)** is a very low-volume store. Single-digit sales days are normal; do not flag as anomalous unless spend is growing.
- **Shopify CSV date ordering:** results are returned ordered by net_sales desc, not by date. Always sum all rows rather than reading only the top rows.

---

## Google Sheets dashboard

Spreadsheet ID: `11CcymBpqMtgR2vjeuqtuplUI5dgc2KnIhUHNjUZWMG0`
Service account that requires Editor access: `mcp-server@adam-mcp-496818.iam.gserviceaccount.com`

Tabs maintained by the digest:
- **Dashboard** -- summary KPIs + three bar charts (Cost, ROAS, Conversions by account). Updated on every run.
- **Latest** -- full per-account table for the most recent digest. ROAS gradient (red=0, white=2, green=5). Alert columns highlighted orange/red.
- **Alerts** -- current tROAS and budget pacing issues.
- **History** -- append-only archive, one row per account per run.
- **MER** -- current Ad Spend % per store. Overwritten each run. Gradient: green at 0%, white at 10%, red at 20%+. Row 2 is portfolio blended (bold grey).
- **MER History** -- append-only archive of MER runs.

---

## Weekly digest additions

The Monday weekly digest (LAST_30_DAYS) adds:
- Top 3 and bottom 3 stores by Ad Spend % efficiency
- Top 3 accounts by spend with individual ROAS
- Bottom 3 accounts by ROAS (with spend > 0)
- Full tROAS alert breakdown with drift percentages
- Strategic summary: what is performing well, what needs attention, one concrete recommended action

---

## Priority build stack (for context)

The most impactful tools not yet built, in ranked order:

1. tROAS audit, propose, edit loop (Phase 3 fast-track) -- single biggest time saver
2. Adaptive spend anomaly alerts -- replace fixed 50% threshold with 6-month volatility baseline
3. Budget cap opportunity flag -- campaigns hitting 95%+ of daily budget for 3+ days flagged as "Budget Constrained -- Review for Increase"
4. Product velocity tiering tool -- New Winners / Winners Turning Losers / Consistent Losers / Untapped
5. Negative keyword agentic pass -- identify, propose, approve, add; weekly cadence
6. MoM/YoY account comparison tool
