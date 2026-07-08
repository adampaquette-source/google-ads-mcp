# Negative-Keyword (Wasted-Keyword) Audit Skill

Parameterized, self-contained procedure for finding wasted search terms and
turning them into negative keywords, with human approval. This is the repeatable
version of the 2026-07-03 Pro Work Supply pass. Runs for one account or all.

Inherits the project hard rules: no account change without Adam's explicit
approval; every write goes through propose then commit; no em dashes in
user-facing output.

## When to run
- Monthly across all accounts (the `google-ads-monthly-negatives` scheduled task).
- Ad hoc on one account after a spend spike or when reviewing an account.

## Inputs
- `customer_id` (optional): one 10-digit account, or omit for all ENABLED accounts.
- `date_range` (default `LAST_30_DAYS`): the lookback window for search terms.

## What counts as waste (tranches)
Each proposed negative lands in exactly one tranche (first match wins), after the
protect list is applied. Grouping by tranche is what lets you bulk-approve a whole
category at once.

| Tranche | Rule | Suggested match |
|---|---|---|
| `competitor_brand` | Search term contains a competitor/retailer brand from the account config | BROAD (the root brand) |
| `off_product` | Contains an off-category word (e.g. lawn, mower) | BROAD (the root word) |
| `foreign_language` | Out-of-language query (non-ASCII, or a configured Spanish stem) | BROAD stem if a stem matched, else EXACT |
| `below_breakeven` | Converted, but ROAS below the account breakeven | EXACT |
| `non_branded` | Strict brand-gated accounts only: 0 conversions and no brand token | EXACT |
| `zero_conv_spend` | 0 conversions AND (spend >= min_spend **or** clicks >= min_clicks); defaults **$50 or 20 clicks** (tier-scaled; scales to `k x target_cpa` when set) | EXACT |
| `ngram_waste` | Diffuse waste: a **two-word phrase** with **zero total conversions across ALL its terms**, rolled-up spend over `ngram_min_spend`, spanning `ngram_min_terms`+ distinct terms, with <25% brand/model spend. Brands (`brand_terms`), part/model numbers, and any converting phrase are excluded automatically. Single-word BROAD n-grams are intentionally NOT proposed (too destructive on a broad catalog) | PHRASE (bigram) |

BROAD tranches collapse every matching query onto one root negative (so "miller
welding helmet", "miller hood"... become one BROAD negative "miller"). EXACT
tranches keep one negative per distinct search term. `ngram_waste` catches the
long tail no single-term rule sees (e.g. "milwaukee" across 1,100+ tiny queries);
review the broad/phrase block for collateral damage before approving.

## The protect list (never propose these)
Per account, `waste_audit_config.json` lists `protect_terms` and `protect_regexes`.
A search term matching any of them is never proposed, even with zero conversions.
This is the "keep all 3M / sub-brand + hearing terms" rule from PWS, generalized.
The audit reports a `protected_count` so you can see how much was shielded.

## Per-account config: `waste_audit_config.json`
Keyed by customer_id, with a `_defaults` block. Per-account keys override; list
keys are replaced, not merged. Relevant keys: `breakeven_roas_pct`, `min_spend`,
`min_clicks`, `flag_foreign_language`, `flag_below_breakeven`, `block_non_branded`,
`protect_terms`, `protect_regexes`, `competitor_terms`, `off_product_terms`.
Before a first run on a new account, fill in its brand protect list and any
known competitor/off-product terms. Pull the breakeven from `<slug>/NOTES.md`
when a folder exists.

## Procedure

### 1. Refresh config
Confirm the target account has a block in `waste_audit_config.json`. If it is a
brand-gated account (only wants its own brand's traffic, like PWS), set
`block_non_branded: true`. Otherwise leave it false so only real spend-wasters,
below-breakeven, and competitor/off-product terms are proposed.

### 2. Run the audit (propose only)
Call the MCP tool `run_waste_audit(customer_id=<id or omit>, date_range=<range>)`.
It classifies terms, applies the protect list, and writes proposals to the control
center Negatives tab, grouped by tranche. Nothing is written to Google Ads. It
posts a Chat summary with the tab link. (Equivalent: the "Run audit" button on
http://localhost:8770/negatives .)

### 3. 🛑 PAUSE FOR ADAM: review and approve
Open http://localhost:8770/negatives . For each account, review the tranches.
Three per-row actions plus a per-tranche bulk approve:
- **Approve** (or "Approve all N" for a whole tranche) - queue the negative to commit.
- **Skip** - dismiss this one proposal for this run (it can resurface next audit).
- **Protect** - keep this term: it is added to the account's protect list (stored
  in the control center DB) and the term plus its sibling proposals are cleared
  immediately and **never resurface** in future audits. Use Protect (not Skip) for
  a legitimate brand or converting term. Undo on a protected row removes the
  protect term again.

Protect decisions live in the CC DB and are merged into each account's
`protect_terms` by `control_center/waste.py` at audit time (the deployed service
cannot write the repo config). To make a protect term permanent/versioned across
machines, also add it to `waste_audit_config.json`. Nothing is applied until Adam
approves and commits. Do not bypass this checkpoint.

### 4. Commit (apply approved negatives)
Per account, click "Commit approved to Google Ads" on the Negatives tab (or call
the MCP tool `commit_negative_keywords(customer_id)`). This adds the approved
terms to the account's shared negative keyword list "Waste Audit Negatives"
(created if missing) and attaches it to eligible ENABLED Search, Shopping **and
Performance Max** campaigns (PMax list attachment went GA 2025-08-07). The commit
is audit-logged before and after. Committed terms are never re-proposed.

For universal junk that should never serve anywhere, `commit_account_level_negatives(customer_id)`
instead writes to the account-level negative list (`ACCOUNT_LEVEL_NEGATIVE_KEYWORDS`),
one object covering Search + Shopping + PMax + App + Smart + Local. That list is
capped at 1,000, so it applies highest-spend-first and reports anything over the
cap; use the shared list (far higher caps) for a big account's long tail.

### 5. Record
- Update the target account's `<slug>/STATE.md`: note the audit date, how many
  negatives were added by tranche, and the shared-list name.
- If the run surfaced an evergreen lesson (a competitor term worth adding to the
  defaults, a new off-product pattern), propose it to Adam before editing
  `waste_audit_config.json` `_defaults`.

## Notes and guardrails
- Propose-only by default. The monthly scheduled task runs step 2 for all accounts
  and stops. Approval and commit are always human, matching the tROAS audit and
  `pws-weekly-ops`.
- The shared list attaches to Search, Shopping and PMax. Per-PMax-term cost is not
  exposed by the API (see `WASTED_SPEND_REMEDIATION.md` section 6), so PMax waste is
  blocked via the shared vocabulary + n-grams, not per-PMax-term spend.
- The engine skips terms already excluded (existing negatives) so re-runs do not
  duplicate.
- Regression anchor: on PWS with `block_non_branded: true`, the codified rule
  reproduces the 2026-07-03 hand pass (186 EXACT + 47 BROAD split), with all
  3M / sub-brand / hearing terms protected. See `ads_mcp/reporting/waste_audit.py`.

## Related files
- `ads_mcp/reporting/waste_audit.py` -- the classification engine.
- `ads_mcp/reporting/waste_config.py` + `waste_audit_config.json` -- per-account config.
- `ads_mcp/proposals/negatives.py` -- the shared-list and account-level apply logic (commit).
- `control_center/waste.py`, `control_center/app.py` (/negatives routes),
  `control_center/templates/negatives.html` -- the review surface.
- MCP tools: `run_waste_audit`, `commit_negative_keywords`, `commit_account_level_negatives`.
