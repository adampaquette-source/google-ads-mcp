# Google Ads Agency Reporting Structures: A Practitioner Reference

*Research compiled May 2026. Intended audience: Adam Paquette, for shaping the Google Ads MCP reporting tool set.*

---

## Overview: What Separates High-Impact Reporting from Noise

The best-run Google Ads agencies operate on a two-layer reporting model. The **executive layer** surfaces KPIs, trends, and anomalies for clients and account owners. The **operational layer** is a daily instrument panel for the account team: granular health checks, action item queues, and early warning signals.

Most practitioners waste time building reports that look polished but drive no decisions. The pattern that consistently works at scale is:

1. **Automate the data pull** so humans never touch exports
2. **Standardize the structure** so the same questions get answered in the same place every time
3. **Flag exceptions, not totals** -- the report should tell you what changed, not just what happened
4. **Link every section to an action** -- a good report ends with a list of things to do, not a gallery of charts

At MCC scale (10+ accounts), an additional principle applies: **triage before depth**. Cross-account rollups surface which accounts need attention; per-account detail is only opened for the accounts that flag red.

---

## Section 1: Reporting Cadences

### Standard Agency Cadence Table

| Cadence | Report Type | Primary Audience | Time Investment |
|---|---|---|---|
| **Daily** | Spend pacing vs. budget | Account team | 5-10 min per account |
| **Daily** | Anomaly digest (spend, CTR, conversions) | Account team | Automated scan |
| **Daily** | Disapproval / policy flag check | Account team | Spot check |
| **Daily** | Conversion tracking status | Account team | Automated |
| **Weekly** | Campaign performance vs. ROAS/CPA targets | Account team + client | 30-60 min |
| **Weekly** | Search term review and negative keyword mining | Account team | 30-45 min per account |
| **Weekly** | Budget pacing (mid-week and end-of-week) | Account team | 15 min |
| **Weekly** | Quality score and keyword health | Account team | 20 min |
| **Weekly** | Executive summary (high-level KPIs, key changes) | Client | 15 min to produce |
| **Monthly** | Full account performance review | Client + internal | 90-120 min |
| **Monthly** | Auction insights and competitive position | Account team | 30 min |
| **Monthly** | Change history review | Account team | 20 min |
| **Monthly** | Shopping / PMax product performance | Account team | 30-45 min |
| **Monthly** | Conversion tracking and attribution audit | Account team | 30 min |
| **Quarterly** | Strategic review: budget reallocation, campaign structure | Client + account lead | 2-3 hours |
| **Quarterly** | Year-over-year trend analysis | Client | Included in QBR |
| **Quarterly** | Keyword expansion and pruning audit | Account team | 60-90 min |

**Notes on cadence:**
- For accounts with daily budgets above ~$500 or with tight CPA/ROAS targets, daily anomaly checks are non-negotiable.
- For smaller or stable accounts, weekly reviews can replace daily checks -- but automated alerts should still run daily.
- Monthly conversion tracking audits are underused by most agencies. One misconfigured tag that fires twice counts double for 30 days before anyone notices.
- Quarterly reviews are strategic, not operational. They answer: "Is this campaign structure still right for the business goal?"

---

## Section 2: Key Report Types

### 2.1 Campaign and Account Performance Reports

**What data is pulled:**
- Impressions, clicks, CTR
- Cost, average CPC
- Conversions, conversion rate, cost-per-conversion
- Conversion value, ROAS
- Impression share (search and display), lost IS (budget), lost IS (rank)

**How it is structured:**
- Summary row at account level, then broken down by campaign
- Date comparison (this period vs. prior period, or vs. same period last year)
- Segment by device, network, or day of week for diagnostic purposes
- Color-coded cells or delta columns showing direction of change

**Who it is for:** Account team weekly; clients monthly (simplified version).

**What decisions it drives:** Budget reallocation between campaigns; bidding adjustments; campaign pausing or activation.

**GAQL resources:** `campaign`, `metrics.*`, `segments.date`

---

### 2.2 Ad Group and Keyword Performance Reports

**What data is pulled:**
- Same core metrics as campaign level, broken down by ad group and keyword
- Match type breakdown
- Quality Score components (expected CTR, ad relevance, landing page experience)
- Average position / top-of-page rate

**How it is structured:**
- Filtered to show keywords with significant spend (typically 2x target CPA with zero conversions)
- Sorted by cost descending to surface waste at the top
- Separate view for converting keywords (to identify winners to scale)

**Who it is for:** Account team. Rarely shown to clients in raw form; summarized into "we paused X keywords that were not converting."

**What decisions it drives:** Keyword bids, pause/enable decisions, match type changes, Quality Score improvement work (ad copy, landing page alignment).

**GAQL resources:** `ad_group`, `ad_group_criterion`, `keyword_view`, `metrics.*`

---

### 2.3 Search Term Reports and Negative Keyword Mining

**What data is pulled:**
- All search terms that triggered ads (last 7 days is standard; 30 days for discovery)
- Cost, clicks, conversions, and conversion rate per term
- Campaign and ad group it matched to

**Standard workflow:**
1. Pull search terms for the last 7 days, sorted by cost descending
2. Flag any term spending more than 2x target CPA with zero conversions as a negative candidate
3. Cross-reference against existing negative keyword lists to avoid duplicates
4. Categorize candidates: competitor terms, informational queries, irrelevant verticals, brand misspellings
5. Add to the appropriate shared list (account-level for universal negatives; campaign-level for specific exclusions)
6. Flag high-spend converting terms as potential new keywords to add explicitly

**Automation note:** This workflow takes 30-45 minutes per account manually. MCC-scale operations (10+ accounts) should automate the export and filtering, with a human doing final review on flagged terms only. Automated tools reduce 3-hour analysis to under 90 seconds for the data pull.

**Who it is for:** Account team. Internal operational task.

**What decisions it drives:** Negative keyword additions, new keyword candidates, match type strategy.

**GAQL resources:** `search_term_view`, `metrics.*`

---

### 2.4 Budget Pacing and Spend Velocity Reports

**What data is pulled:**
- Daily spend vs. daily budget per campaign
- Month-to-date spend vs. monthly budget cap
- Projected month-end spend at current pace
- Budget utilization percentage

**How it is structured:**
- Pacing = (actual spend to date) / (budget * (days elapsed / days in month))
- Pacing ratio above 1.0 = overpacing (risk of budget exhaustion)
- Pacing ratio below 0.85 = underpacing (opportunity being missed)
- Traffic light view: green (0.85-1.10), yellow (0.75-0.85 or 1.10-1.20), red (below 0.75 or above 1.20)

**Key nuance (2026 update):** Google now paces all campaigns toward 30.4x daily budget regardless of ad schedule days, which shifts the pacing math for campaigns not running 7 days a week.

**Who it is for:** Account team daily; account leads at end of month.

**What decisions it drives:** Budget adjustments, bid strategy changes, campaign schedule modifications.

**GAQL resources:** `campaign`, `campaign_budget`, `metrics.cost_micros`, `segments.date`

---

### 2.5 ROAS / CPA Performance Against Targets

**What data is pulled:**
- Actual ROAS and CPA per campaign, ad group, or product category
- Target ROAS / target CPA set on campaign
- Variance from target (actual vs. goal)
- 7-day rolling average vs. 30-day rolling average to smooth noise

**How it is structured:**
- Dashboard view showing each campaign's ROAS vs. its target in a single table
- Trend lines for ROAS/CPA over the last 30-90 days
- Drift alert: campaigns where current 7-day ROAS has moved more than 10-15% from the 30-day average

**Who it is for:** Account team weekly; clients monthly in simplified form showing trend direction.

**What decisions it drives:** tROAS bid adjustments, budget reallocation from underperforming to overperforming campaigns, bid strategy review.

**GAQL resources:** `campaign`, `bidding_strategy`, `metrics.conversions_value`, `metrics.cost_micros`

---

### 2.6 Auction Insights and Competitive Position

**What data is pulled:**
- Impression share (your account)
- Overlap rate (how often a competitor's ad showed when yours did)
- Outranking share (how often your ad ranked above a competitor's)
- Position above rate (how often a competitor's ad ranked above yours)
- Top-of-page rate and absolute top-of-page rate

**How it is structured:**
- Run at campaign level for branded campaigns (brand defense)
- Run at account or campaign level for key competitive products
- Compare 30-day to 90-day windows to identify structural shifts vs. temporary noise
- Trend over time to detect competitor entry or exit

**Who it is for:** Account team monthly; strategic portion included in quarterly client reviews.

**What decisions it drives:** Bid increases for brand defense; competitive spend justification; identification of new competitors.

**GAQL resources:** Auction insights are primarily available via UI or API batch reports; limited direct GAQL access.

---

### 2.7 Shopping and Performance Max Product-Level Reporting

**What data is pulled:**
- Product-level: impressions, clicks, CTR, cost, conversions, ROAS by product ID, category, brand, custom label
- PMax channel breakdown: Search, Shopping, Display, YouTube, Gmail, Demand Gen
- Feed-based vs. asset-based ad performance split
- Product disapprovals and feed errors from Merchant Center

**How it is structured:**
- Product performance sorted by ROAS to identify top and bottom performers
- Segment by category or brand to find structural patterns
- Cross-reference with Merchant Center feed health (disapprovals, pending items, feed errors)
- PMax asset group performance (when available) by headline/image combination

**Key limitation:** PMax campaigns do not expose ad group or keyword data. Reporting relies on `asset_group`, `shopping_performance_view`, and the channel performance report.

**Who it is for:** Account team weekly for active Shopping/PMax campaigns; monthly for strategic review.

**What decisions it drives:** Product exclusions (low-ROAS products pulled from feed), listing group structure changes, budget allocation between PMax and standard Shopping.

**GAQL resources:** `shopping_performance_view`, `asset_group`, `asset_group_listing_group_filter`, `metrics.*`

---

### 2.8 Disapprovals and Policy Issue Reports

**What data is pulled:**
- Ads with disapproval status and disapproval reason
- Keywords with policy restrictions
- Extensions with disapprovals
- Campaigns with limited reach due to policy

**How it is structured:**
- Daily automated scan with exception-only output
- Group disapprovals by reason (policy category) to identify systemic issues vs. one-off problems
- Flag new disapprovals (today vs. yesterday) separately from known standing issues

**Who it is for:** Account team. Disapprovals are almost never surfaced to clients -- they are fixed before the client sees them.

**What decisions it drives:** Immediate ad copy revision, policy appeal submissions, landing page compliance fixes.

**GAQL resources:** `ad_group_ad`, `ad_group_ad.policy_summary`, `ad_group_criterion` (policy status fields)

---

### 2.9 Change History Reports

**What data is pulled:**
- All changes made to the account in a given window (last 7 days, last 30 days)
- Change type, what changed, old value, new value, who made the change, timestamp
- Automated changes (Smart Bidding adjustments) vs. manual changes

**How it is structured:**
- Sorted by timestamp descending
- Filtered to show significant changes only (budget changes, bid strategy changes, ad additions/removals, keyword status changes)
- Correlated with performance inflection points: did performance shift around the same time as a change?

**Who it is for:** Account team. Used for troubleshooting ("something changed -- what was it?") and for audit purposes.

**What decisions it drives:** Rollback decisions, documentation of what was done and why, identifying unauthorized changes.

**GAQL resources:** `change_event` resource (available via GAQL)

---

### 2.10 Conversion Tracking Health and Attribution Reports

**What data is pulled:**
- Conversion action status (enabled, removed, no recent conversions)
- Tag firing status (confirmed, unverified, tag inactive)
- Recent conversion volume trend (looking for sudden drops or spikes)
- Attribution model in use per conversion action
- Enhanced conversions status

**How it is structured:**
- Monthly audit checklist format
- Green/yellow/red status per conversion action
- Comparison of Google Ads-reported conversions vs. CRM or analytics data (discrepancy check)

**Monthly checklist items:**
- Conversion tags fire correctly on conversion pages only (not site-wide)
- Conversion linker tag present and firing on all pages
- Attribution model matches business goals (data-driven preferred where volume allows)
- Enhanced conversions configured to fill privacy gaps (iOS, cookie restrictions)
- Cross-domain tracking set up correctly if checkout is on a separate domain
- Conversion windows match typical sales cycle (B2B often needs 90-day windows)
- No duplicate conversion actions counting the same event twice

**Who it is for:** Account team. A broken conversion tag silently corrupts every optimization signal.

**What decisions it drives:** Tag fixes, attribution model changes, Smart Bidding retraining periods after tracking changes.

**GAQL resources:** `conversion_action`, `customer.conversion_tracking_setting`

---

## Section 3: Executive vs. Operational Reporting

### Executive Layer (Client-Facing)

The executive layer answers three questions: Are we on track? What changed? What are we doing about it?

**Structure:**
- One-page summary with 4-6 headline KPIs vs. targets (ROAS, CPA, total conversions, total spend, impression share)
- Period-over-period comparison with direction indicators (up/down vs. prior period, vs. same period last year)
- 2-3 sentences of plain-language narrative: what drove the changes, and what action is being taken
- No raw data tables, no granular keyword lists, no technical jargon

**Format:** PDF or Looker Studio dashboard with a pre-built template that updates automatically.

**Frequency:** Weekly summary email + monthly detailed review meeting.

**What to exclude:** Individual keyword performance, disapproval details, raw search term data, Quality Score breakdowns. These are operational details that confuse clients and invite micromanagement.

### Operational Layer (Internal Team)

The operational layer answers: What needs my attention today? What is broken? What should I change?

**Structure:**
- Daily anomaly digest: accounts with red flags since yesterday
- Weekly action item list: keywords to pause, negatives to add, budgets to adjust
- Health check dashboard: conversion tracking status, disapprovals, budget pacing for all accounts

**Format:** Google Sheets dashboard updated via Ads API, or a purpose-built tool (the Google Ads MCP server fills this role).

**Key design principle:** The operational layer should surface exceptions, not totals. A manager with 15 accounts does not have time to review every account every day -- they need a tool that says "accounts 3, 7, and 12 need attention today."

---

## Section 4: MCC Multi-Account Reporting Patterns

### The Core Problem at Scale

With 10+ accounts, manual reporting creates a compounding time debt. Checking each account individually takes hours per day. The solution is a cross-account triage view that aggregates the most critical signals into a single surface.

### Rollup vs. Per-Account

**What gets rolled up (MCC level):**
- Total MCC spend vs. budget (day, week, month)
- Total MCC conversions and blended ROAS
- Account-level status flags (red = needs attention, green = on track)
- Disapproval count by account
- Budget utilization percentage by account
- Spend change vs. same window yesterday (day-over-day alert)

**What stays per-account:**
- Campaign-level breakdowns
- Search term review
- Auction insights
- Product performance
- Change history

### MCC Script and API Architecture

The standard MCC monitoring pattern uses `AdsManagerApp` (not `AdsApp`) to iterate across all child accounts. A well-built MCC monitoring system:

1. Runs on a schedule (nightly for summary; real-time for critical alerts)
2. Checks each account against thresholds (spend, conversions, CTR)
3. Writes exceptions to a Google Sheet (one row per account per day)
4. Sends a digest only when accounts fall outside thresholds

Practical time savings: agencies report MCC-level automation reduces 8 hours of manual account checking to 15 minutes of exception review.

### Cross-Account Metrics That Matter at MCC Level

- **Portfolio ROAS:** Total conversion value / total spend across all accounts
- **Budget utilization rate:** Percentage of total allocated budget being spent
- **Accounts in red:** How many accounts have a critical flag (disapproval spike, conversion tracking break, budget exhaustion, anomaly)
- **Aggregate impression share lost (budget):** Shows where structural budget constraints are limiting performance portfolio-wide

### Permission Structure at MCC Scale

- MCC admin (account owner): full access to all accounts
- Account strategist: Standard access to assigned accounts only
- Analyst / reporting role: Read-only across the full MCC
- This structure applies automatically to all child accounts when set at the MCC level

---

## Section 5: Anomaly Detection and Alerting

### High-Priority Alert Signals

The metrics worth automated alerting are those where a change of a certain magnitude is unlikely to be normal variance and is likely to require immediate action:

- **Spend deviation:** +/- 30-50% vs. same time window yesterday (or vs. 7-day rolling average)
- **Conversion count drops to zero** for any account that normally converts daily
- **CTR drops more than 20%** without a corresponding impression share increase (often signals disapprovals or quality issues)
- **CPA spike above 2x target** on any campaign spending above a minimum threshold
- **ROAS drift of more than 15%** from the 30-day average over a 7-day window
- **Impression share drops of more than 15 percentage points** (can indicate budget exhaustion or Quality Score drops)

### Medium-Priority Signals (Weekly Digest)

- Quality Score changes of 2+ points on high-volume keywords
- New competitors appearing in auction insights
- Search term query volume shifts
- Ad frequency capping issues (Display or PMax)

### Alert Threshold Design

The right threshold calibration: **2-3 standard deviations from the campaign-specific baseline**, not an account-wide average. A 30% CTR fluctuation is normal for a small ad group with 50 impressions per day and alarming for a high-volume branded campaign with 10,000 impressions per day.

**Practical approach:**
1. Calculate a 7-day or 14-day rolling average per campaign for spend, conversions, and CTR
2. Set alert thresholds at 2-2.5 standard deviations from that average
3. For spend specifically, also use a simpler absolute rule: flag any campaign that spends more than 2x its daily budget in a single day
4. Tune thresholds monthly for the first quarter; expect 30%+ false positive rate initially

**Alert fatigue management:** Use a tiered system -- critical issues (spend to zero, conversion tracking broken, major disapproval spike) trigger immediate alerts; performance drift triggers a daily digest, not a per-event ping.

---

## Section 6: Google Ads-Native Reporting Tools

### Report Editor

The Google Ads Report Editor provides flexible drag-and-drop report building in the UI, including auction insights data not available via GAQL. Best for ad-hoc exploration rather than recurring reports.

### Google Ads Scripts

Scripts (JavaScript) run in the Google Ads environment and can read and modify account data. MCC-level scripts use `AdsManagerApp` to iterate across all child accounts.

**High-value uses:**
- Daily budget pacing tracker writing to Google Sheets
- Nightly anomaly detector with email alerts
- Weekly search term miner flagging high-cost non-converting terms
- Conversion goal health auditor across all accounts

**Limitation:** Scripts are stateless; they cannot reference previous runs without writing to an external store (Google Sheets or Apps Script properties).

### Looker Studio (formerly Data Studio)

The standard client-facing dashboard tool. Connects natively to Google Ads and can display cross-account data when connected to an MCC. Automated, branded client reports that update daily without manual intervention.

### Google Ads API

Provides programmatic access to all reporting data via GAQL. Supports `search_stream()` for large result sets. Rate limit on Basic Access: 15,000 operations/day. At 19 accounts, approximately 789 operations per account per day -- sufficient for all standard reporting functions if queries are designed efficiently.

---

## Section 7: Third-Party Agency Tools

### Supermetrics

**What it does:** Data pipeline tool. Pulls Google Ads data into Google Sheets, Looker Studio, or BigQuery. Does not do analysis -- it moves data.

**Best for:** Agencies with a BI analyst who builds their own reporting layer. Requires technical setup but highly flexible.

**Limitations:** Not a reporting tool itself; requires Looker Studio or similar for visualization.

### Optmyzr

**What it does:** Full PPC management platform with 80+ automation tools. Supports Google Ads, Microsoft Ads, Amazon Ads, and Meta.

**Most valued features for reporting:**
- PPC Investigator: diagnoses why performance changed
- Campaign Automator: rule-based optimization with audit trail
- Account Scorecard: health check across multiple dimensions
- Custom report builder with client-facing templates

### Adalysis

**What it does:** Google Ads auditing and optimization platform. Strong in Quality Score monitoring, ad testing, and account health checks.

**Most valued features:**
- Continuous Quality Score monitoring and alerting
- Automated A/B ad testing management
- Account audit reports surfacing structural issues
- Search term categorization and negative keyword suggestions

### AgencyAnalytics

**What it does:** Client reporting platform. Connects 80+ marketing data sources into branded, automated reports and dashboards.

**Most valued features:**
- White-labeled client dashboards with custom branding
- Automated monthly report generation and email delivery
- KPI alerts sent to account managers

### What Third-Party Tools Provide That Native Tools Do Not

- **Cross-channel views:** Blending Google Ads with Meta, LinkedIn, and CRM data in one dashboard
- **White-labeled client reports:** Branded PDFs with agency logo
- **Annotation and commentary layers:** Human narrative added alongside automated data
- **Scheduled automated delivery:** Reports emailed to clients on a schedule without manual action
- **Historical data retention beyond Google's limits:** Google Ads UI only stores 9 months of data in some views

---

## Section 8: Action-Oriented Reporting Design

### The Core Principle

Data without a recommended action is entertainment, not reporting. Every section of a useful operations report should end with an explicit recommendation or a threshold flag.

### Structures That Drive Decisions

**Exception tables:** Show only the rows that deviate from expectation -- not all 200 campaigns, just the 8 that are off target.

**Delta columns:** Always show change (this period vs. prior period) alongside absolute values. A ROAS of 4.2 means nothing without knowing it was 5.8 last week.

**Traffic light indicators:** Green/yellow/red status per account or campaign instantly creates a priority queue. The color is the answer.

**Ranked action lists:** The report ends with a numbered list of actions, prioritized by impact. "1. Pause keyword X ($340 spent, 0 conversions). 2. Add 12 negatives from search term review. 3. Raise budget on Campaign Y -- pacing at 68%."

### Segmentations That Matter Most

- **Device:** Mobile vs. desktop performance often differs enough to justify different bids or landing pages
- **Day of week:** B2B accounts show weekend degradation; e-commerce shows weekend peaks
- **Network:** Search vs. Search Partners vs. Display for campaigns still running on expanded networks
- **Time of day:** For high-budget campaigns, hourly segmentation identifies when to concentrate spend
- **New vs. returning customers:** Particularly important for PMax and Shopping campaigns

### The Digest Narrative Model

The most sophisticated agencies use AI-generated narrative above the data tables. Rather than letting clients interpret charts themselves, a 3-5 sentence narrative explains what happened, why it likely happened, and what action is being taken. This is the model implemented in the Google Ads MCP digest worker (Phase 2): the digest worker fetches structured data, then Claude writes the narrative.

---

## Section 9: Consultation Questions for Adam

Organized by theme. Answers will directly shape which MCP tools to prioritize and how to structure the digest output.

### Cadence and Rhythm

1. How often do you review account performance today -- daily, a few times a week, or weekly? What does that review currently look like?
2. Do you want automated daily alerts pushed to you (Google Chat), or do you prefer to pull reports on demand?
3. Is there a specific time of day you review performance? Morning check vs. end-of-day?
4. Are there accounts in the MCC that need more frequent attention (high budget, new campaigns, aggressive targets) vs. accounts that are stable and can get weekly check-ins?

### Executive vs. Operational Needs

5. Are you the only person reviewing these reports, or do you need to produce client-facing reports for external stakeholders?
6. If there are external stakeholders, how much Google Ads context do they have? Do they want raw metrics or narrative summaries?
7. What does your ideal "morning briefing" look like -- a one-paragraph digest, a structured table, or a chat conversation where you ask questions?

### Alert Thresholds

8. At what spend change vs. yesterday do you want to be alerted? The MCC spend alert script currently uses +/- 50% -- is that the right threshold for the MCP alerts too?
9. Is a zero-conversion day on an account an automatic alert, or only a concern if it persists for 2+ days?
10. Do you want ROAS/CPA drift alerts per campaign, or only at the account level?

### Account-Specific Priorities

11. Which accounts in the MCC are Performance Max or Shopping campaigns? (Those need different reporting logic than Search-only accounts.)
12. Are any accounts running tROAS or tCPA bidding? Those benefit most from bid drift monitoring.
13. Are there any accounts where spend control is especially critical (fixed monthly budget, client sensitive to overspend)?

### Search Terms and Negative Keywords

14. Do you want search term review to be a tool you run on-demand, or part of the weekly digest output?
15. Is there a shared negative keyword list across the MCC, or does each account manage its own?

### Visualization and Integration

16. Is Google Sheets an acceptable primary output for tabular reports, or do you want everything surfaced in the chat interface?
17. Would you ever want the MCP to push data into a Looker Studio dashboard, or is the Google Sheets dashboard sufficient?
18. The digest posts to Google Chat. Is there a preference for how much detail appears in the Chat message vs. behind the dashboard link?
19. Do you want digest history archived anywhere beyond the History tab in the Sheets dashboard?

### Priorities and Gaps

20. Of the current 14 MCP tools, which 3-4 do you find yourself reaching for most? Are there any reporting patterns from your current manual workflow that are not yet covered?

---

*End of document. Next step: work through Section 9 with Adam to finalize reporting priorities and any gaps to fill in the MCP tool set.*
