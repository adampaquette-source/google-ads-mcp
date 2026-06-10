# Reporting Consultation Results

*Captured May 2026. Used to shape MCP tool priorities, digest format, alert logic, and phase roadmap.*

---

## Account Tier Structure

Three tiers drive all monitoring cadence, alert sensitivity, and digest formatting decisions.

| Tier | Accounts | Review Cadence | Alert Sensitivity | Digest Treatment |
|---|---|---|---|---|
| **Tier 1** | Toolup, Red Tool Store (+ top 3 by spend) | Daily | Highest | Named scorecard in every daily digest, per-campaign drill-down |
| **Tier 2** | Middle 5 by spend | Weekly | Medium | Account-level in weekly digest, named in daily only if outlier flagged |
| **Tier 3** | Remaining 8 | Bi-weekly | Lower | Account-level in weekly digest only, unless critical flag |

Tier assignment is dynamic — maps to monthly spend rank, not fixed account names. Toolup and Red Tool Store are anchored as Tier 1 regardless of any given month's spend.

---

## Cadence and Delivery

- **Daily morning digest** pushed to Google Chat. Timing: morning before the day starts.
- **Weekly digest** (Monday) covers LAST_30_DAYS with full account breakdown.
- **Red flag alerts** fire immediately and independently of the digest schedule.
- Format: clearly scannable bulleted list, named scorecard for Tier 1 accounts, one-sentence callouts for anything demanding attention, link to full dashboard.
- Audience: Adam (operator/execution) + VP (executive view — summary only).

---

## Alert Logic

### Spend Anomaly Detection
- **Do not use a fixed ±50% threshold.** Smaller accounts have higher natural day-over-day volatility.
- Use **adaptive thresholds based on 6-month historical spend variance** per account. Flag when deviation exceeds 2-2.5 standard deviations from the account's own baseline.
- This means a $50/day account needs a wider band than a $2,000/day account.

### Zero Conversion Alerts
- **Tier 1 accounts:** zero conversions within a 4-hour window during active hours = immediate alert.
- **Tier 2/3 accounts:** zero conversions persisting for 2+ consecutive days = alert.

### Budget Pacing -- Inverted Logic
- **Philosophy: budgetless operation.** If a campaign is pencilling out (positive ROAS), budget should not cap it.
- Budget cap alerts are **opportunity signals, not warnings.** A campaign consistently hitting its daily budget cap should be flagged for a budget increase review, not flagged as overspending.
- Build: flag any campaign hitting 95%+ of daily budget for 3+ consecutive days as "Budget Constrained -- Review for Increase."

### ROAS / tROAS Drift
- **Tier 1 accounts:** per-campaign drift alerts.
- **Tier 2/3 accounts:** account-level drift alerts only.
- Drift thresholds use the same adaptive methodology as spend: compare current 7-day window vs. 6-month per-campaign baseline.

---

## Campaign Attention Framework

When drilling into an account, the three states that demand action:

| State | Signal | Action |
|---|---|---|
| **Underspending** | Period-over-period downward trend in spend | Investigate: budget cap, disapproval, quality issue, bid too restrictive |
| **Overspending** | ROAS consistently below target | tROAS increase (tighten bid) or pause review |
| **Accelerating** | Period-over-period spend increase AND on/near tROAS target | tROAS loosen or budget increase to capture more volume |

This framework directly drives the tROAS audit tool (see Priority #1 below).

---

## Product Velocity Tiers

For PMax and Shopping accounts, product performance segments into four actionable tiers:

| Tier | Signal | Action |
|---|---|---|
| **New Winners** | Recent strong ROAS, low prior spend history | Increase exposure, consider dedicated campaigns |
| **Winners Turning Losers** | Previously strong ROAS, now declining | Investigate: pricing, inventory, seasonality, ad fatigue |
| **Consistent Losers** | High spend, low/no conversion value | Exclude from feed or demote in listing groups |
| **Untapped** | Minimal spend, unknown ROAS | Structured test to qualify |

---

## Campaign Mix

- **Vast majority of volume is PMax and Shopping.** Standard Search is secondary.
- **tROAS is the standard bidding strategy** across the portfolio.
- **MaxCPC exceptions:** select campaigns on Toolup and Red Tool Store only.
- Implications: ROAS reporting and tROAS audit tools are the highest-leverage tools in the stack. Keyword-level reporting is secondary to product-level reporting.

---

## Negative Keyword Workflow

- Currently managed at the account level, inconsistently applied due to attention bandwidth.
- **Target workflow:** weekly agentic pass using identify → propose → approve → add pattern.
- This is a Phase 3 addition, aligned with the proposal/commit flow already planned.
- Opportunity: significant wasted spend recovery potential across the portfolio.

---

## Reporting Display Preferences

- **MER display format:** Ad Spend % = (Google Ads Spend / Shopify Net Sales) x 100. Lower is better. A 4.3% MER means ads cost $4.30 per $100 in net sales.
- **MER status thresholds:** Strong (<=5%), Good (5-10%), Watch (10-20%), Poor (>20%), No Sales (zero net sales with spend present), No Spend (zero ads cost).
- **MER gradient in Sheets:** green at 0% (most efficient), white at 10%, red at 20%+ (inverted from ROAS -- lower is better here).
- **No em dashes** in any user-facing output (digest narratives, Chat messages, Sheets cells, log messages).

---

## Immediate Build: Trailing 7-Day MER Report

**MER = Marketing Efficiency Ratio = Total Shopify Net Sales / Total Google Ads Spend.**

This is a cross-platform metric requiring both the Shopify MCP and Google Ads MCP working in parallel. Adam has a template to provide as reference for the report format.

- Scope: all 18 stores, trailing 7 days, using the stores_mapping.json for account-to-store joins.
- Output: per-store MER + blended portfolio MER.
- This is the first concrete cross-platform deliverable.
- **Status: immediate priority.** Adam to provide template.

---

## Visual Layer

- Google Sheets is a starting point but will be outgrown quickly as a primary visual layer.
- Requirements: mature presentation, low or no cost, not overkill.
- Looker Studio is a candidate for the VP-facing executive layer (free, connects natively to Google Ads and Google Sheets).
- Decision deferred pending MER template review and further ideation.
- The Sheets dashboard remains the operational data layer regardless of what sits on top.

---

## Conversational Claude Use Cases

When opening a Claude session for per-account drill-down, the standard starting questions are:

1. **Which campaigns demand attention?** Identify underspending, overspending, and accelerating campaigns using the three-state framework above.
2. **Account MoM and YoY comparison.** Month-over-month and year-over-year spend and conversion value for the account.
3. **Product velocity changes.** New winners, winners turning losers, consistent losers (high spend / low conversion value).

These three use cases define the core conversational tool set needed beyond the current 14 tools.

---

## Priority Stack

Ranked by time savings and revenue impact based on consultation:

| Priority | Build | Phase | Rationale |
|---|---|---|---|
| **1** | tROAS audit → propose → edit loop | Phase 3 fast-track | Single biggest time suck. Per-campaign tighten/loosen logic based on drift state. |
| **2** | Trailing 7-day MER report | Cross-platform (now) | On Adam's to-do list, both MCPs now live, template incoming. |
| **3** | Adaptive spend anomaly alerts | Improvement to existing | Replace fixed 50% threshold with 6-month volatility baseline. |
| **4** | Budget cap opportunity flag | Improvement to existing | Flip pacing alert from warning to opportunity signal. |
| **5** | Product velocity tiering tool | New tool | New winners / turning losers / consistent losers segmentation. |
| **6** | Negative keyword agentic pass | Phase 3 | Identify → propose → approve → add, weekly cadence. |
| **7** | MoM / YoY account comparison tool | New tool | Requested as standard drill-down starting point. |
| **8** | Visual layer upgrade | TBD | Looker Studio or equivalent, VP-facing, deferred pending ideation. |

---

## Key Decisions Captured

- **Budgetless philosophy:** budget caps are opportunity signals, not warnings.
- **Tiered monitoring:** monitoring depth and alert sensitivity scale with account spend rank.
- **tROAS is the primary lever** across the portfolio -- the audit/propose/edit loop is the single most impactful tool not yet built.
- **PMax and Shopping dominate volume** -- product-level reporting matters more than keyword-level.
- **MER is the true north metric** for cross-platform performance -- Google Ads ROAS alone is not sufficient.
- **Negative keyword automation** is high-opportunity due to consistent under-investment.
