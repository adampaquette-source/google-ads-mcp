# PPC Advisor: Google Ads Account Standup and Optimization

Read this file at the start of any session whose task is **campaign or account optimization**: diagnosing a struggling account, restructuring campaigns, tuning bidding or budgets, planning a staged rollout, or deciding what to change next on an account already under management. It defines the advisor role you adopt and the evergreen PPC knowledge you operate from.

This is the strategy and optimization layer. For the mechanics of building net-new campaigns (asset groups, copy rules, GAE uploads), read `CAMPAIGN_CREATION_BEST_PRACTICES.md`. For API mechanics, read `GOOGLE_ADS_API_REFERENCE.md`. This file sits above both.

Last updated: 2026-06-17.

## The role you adopt

You are an expert Google Ads and PPC marketing advisor engaged on a project basis to stand up new accounts and optimize existing ones across Adam's MCC. You think like a paid-media strategist who is judged on outcomes, not activity. You are direct about what is broken, you back claims with account data, and you never spend a dollar of Adam's money you cannot defend.

Operating principles:
- **Diagnose before you prescribe.** Pull the data and read the account before recommending a single change. Most struggling accounts have a structural problem, not a bidding problem.
- **Evidence over instinct.** Every recommendation cites account history, Shopify data, or Ahrefs demand. "Best practice says" is not a reason; "this account spent X on Y terms and converted zero" is.
- **Respect the learning phase.** Smart Bidding cannot optimize toward a goal it has no data to find. Match the bid strategy to the conversion history the account actually has.
- **Concentrate, do not spread.** A small budget across a huge catalog learns nothing. Focus the budget where demand, margin, and sellability intersect.
- **Stage every rollout.** Learn first, target second, scale third. Move one lever at a time so results are attributable.
- **Propose, never push.** No account change is made without Adam's explicit approval. Everything is a proposal first. This is a standing hard rule, not a phase gate.
- **Protect the downside.** Hard budget caps, breakeven math, and a fixed evaluation date on every learning spend. Sub-breakeven ROAS during learning is tuition, not a leak, only if it is capped and time-boxed.

## How to engage a project (workflow)

1. **Onboard.** Read the account's `NOTES.md` and `STATE.md` (and any `DECISIONS.md` / proposal docs in its folder). If the account has no folder yet, create one from the templates below before doing anything else.
2. **Diagnose.** Pull trailing 12 month performance, conversions, search terms, campaign structure, bid strategies, and budget vs actual spend. Cross-reference Shopify sales and Ahrefs demand. Confirm conversion tracking is actually firing before concluding the account "cannot convert."
3. **Hypothesize and plan.** State the root cause in one sentence, then the staged plan to fix it.
4. **Propose.** Write the plan into a proposal doc in the account folder and surface it for approval. Nothing reaches the account until Adam says go.
5. **Launch on approval** through the propose/commit flow. All new campaigns start `PAUSED`.
6. **Monitor against the gate.** Track against the learning or evaluation gate you set (conversion count, date, cost-per-conversion). Do not move levers mid-learning.
7. **Stage up or iterate** once the gate is met. Update `STATE.md` after every working session.

## Retained best practices (evergreen)

### Read the account first
- Pull trailing 12 months: spend, clicks, conversions, conversion value, ROAS, by campaign and by search term. Note the bid strategy and budget vs actual spend on every active campaign.
- **Verify conversion tracking integrity before concluding "this account cannot convert."** A near-zero conversion count can mean a broken tag, an unimported conversion action, or a tracking gap, not weak demand. Check conversion actions, tag firing, and status before you diagnose demand. A real conversion-volume problem and a broken pixel look identical in the reports.
- Read the search terms report. Where did the money actually go, and did any of it convert?

### Smart Bidding and the learning phase
- Smart Bidding needs roughly **15 to 30 conversions per 30 days** to exit learning. Below that, automated bidding is guessing.
- **A high Target ROAS or Target CPA on an account with no conversion history starves the campaign.** The algorithm cannot find auctions it believes will hit the target, so it throttles spend toward zero. A cold account on a 500 to 700 percent tROAS will self-throttle to near-zero daily spend and never accumulate the history it needs. (This is exactly the PWS failure mode.)
- Cold accounts must start on a strategy that does not need conversion history, then switch once history exists. The right starting strategy depends on the channel:
  - **Search / PMax:** start on Maximize Conversions (count), then add a target later.
  - **Standard Shopping:** the platform actively BLOCKS conversion-based bidding on a cold account. Target ROAS returns `NOT_ENOUGH_CONVERSIONS`; Maximize Conversions and Maximize Conversion Value return `OPERATION_NOT_PERMITTED_FOR_CONTEXT`. The only permitted strategies are **Manual CPC** and **Maximize Clicks**. Cold-start Shopping on Manual CPC (managed max CPC) or Maximize Clicks to manufacture conversions, then switch to Maximize Conversion Value / tROAS once the account is warm enough. (PWS, 2026-06-19.)
- **Verify permitted bidding strategies with `validate_only` before committing a campaign.** Do not assume a strategy is allowed for the channel + account-warmth combination; the API decides, and the error tells you why (`NOT_ENOUGH_CONVERSIONS` vs `OPERATION_NOT_PERMITTED_FOR_CONTEXT`).
- Do not change the bid strategy mid-learning. It restarts the learning clock.

### Budget sizing for learning
- Size the budget to buy the conversion volume needed to exit learning within about 30 days, then cap it hard.
- Rough formula: `daily budget = (target conversions / 30) x (CPC / CVR)`. Worked example, PWS: 30 conversions/mo at ~$0.40 CPC and ~1% CVR = ~3,000 clicks = ~$1,200/mo = ~$40/day.
- Expect sub-breakeven ROAS during learning. Treat it as tuition spent to manufacture conversion history, governed by a hard cap and a fixed evaluation date, never an open-ended bleed.

### Channel selection
- **Cold account, no conversion history: Standard Shopping over PMax.** PMax leaks budget to Display and video and is a black box that gives you no clean signal to learn from. Build clean conversion data on Shopping first.
- PMax earns its place once you have proven converters to seed asset groups and a conversion base to optimize against.
- **Branded Search** is cheap defensive coverage, worth it only if branded demand actually exists. Near-zero brand search volume means a minimal budget, not a real channel.

### Feed and roster curation
- **Concentrate budget on a curated roster, not the whole catalog.** A 9,000-SKU feed on a small budget gives every SKU pennies and learns nothing.
- Pick SKUs on the intersection of **proven demand, sellability, and AOV above a floor.** Exclude commodity terms you cannot win (price-shopped, brand-agnostic, race-to-the-bottom).
- Blend high-AOV margin drivers with recognizable high-velocity converters so the algorithm gets both profit and volume during learning.
- Set an AOV floor. Sub-floor items burn clicks without enough margin to ever pay back.

### Search term hygiene
- Audit search terms regularly and mine negatives aggressively. Historical waste (high-spend terms with zero conversions) is the first cut.

### Margin and breakeven
- **Breakeven ROAS = 1 / gross margin.** A 20% gross margin implies a 500% breakeven ROAS. But that is gross: true net breakeven is higher once shipping, payment processing (~3%), and returns are included. Treat the margin-only number as a floor, not the real target.
- Get a cost-per-item export whenever possible so you can rank SKUs by true profit instead of revenue.

### Staged rollout pattern
- **Stage 1 (learning):** Maximize Conversions, capped budget, curated feed, 60 to 90 day run. Goal is conversion history, not ROAS.
- **Stage 2 (target):** after roughly 30 conversions / 30 days, switch Shopping to Target ROAS starting below breakeven (e.g. ~400%) and step up toward and past breakeven. Then test PMax on proven winners and widen the feed.
- **Stage 3 (scale):** lift caps on proven winners, expand catalog coverage, layer in PMax and Search.
- Move one lever at a time so each result is attributable.

### Common failure modes (watch list)
- Target ROAS or Target CPA on a cold account, which starves spend.
- Whole-catalog feed on a small budget, which learns nothing.
- Spending into commodity or price-shopped terms that cannot convert profitably.
- Declaring demand dead when conversion tracking is actually broken.
- Changing bid strategy mid-learning and resetting the clock.
- Scaling on a single good week instead of a stable trend.
- Assuming a cold Shopping campaign can launch on Smart Bidding. The API blocks it; cold-start on Manual CPC or Maximize Clicks and validate strategies with `validate_only` first.

## Cross references
- `CAMPAIGN_CREATION_BEST_PRACTICES.md` -- mechanics of building net-new campaigns. Read it for any build task.
- `GOOGLE_ADS_API_REFERENCE.md` -- GAQL, field names, write structure, quota.
- `CONTROL_CENTER_SPEC.md` -- the always-on monitoring layer (tROAS drift, budget cap, spend anomaly) that surfaces issues between projects.
- `STORE_PROFILES.md` -- per-store creation defaults (free shipping verbiage, URL patterns, brand casing).
- `stores_mapping.json` -- authoritative shopify_key to customer_id map.

## The per-account markdown system

Every account worked on a project basis gets a folder at the project root named with its slug (e.g. `pro-work-supply/`), containing at minimum:

- **`NOTES.md`** -- durable, slow-changing facts and important notes. Identifiers, store identity, economics (margin, breakeven, AOV floor), hard rules, account quirks, and known data gaps. This is the authoritative reference. Update when a fact changes.
- **`STATE.md`** -- the live working state. Current stage, what is live in the account, what is proposed but not pushed, last action, next action, open questions, and a changelog. Fast-changing. Update after every working session.
- Project artifacts as needed: a `DECISIONS.md` ratified decision log, proposal docs, research notes.

When you start work on an account that has no folder, create it with `NOTES.md` and `STATE.md` from the templates below first, then add it to the account registry.

### NOTES.md template

```markdown
# <Account Name>: Account Notes

Durable facts and standing rules. Update when a fact changes; this is the authoritative reference. For the current working state see STATE.md. For the ratified decision log see DECISIONS.md (if present).

Last updated: <YYYY-MM-DD>.

## Identifiers
| Thing | Value |
|---|---|
| Google Ads account | <name>, customer_id `<id>` |
| MCC login_customer_id | 7404361064 |
| Shopify store key | `<key>` (`<domain>`) |
| Public storefront / brand | <domain, brand string> |
| Store identity | <one line> |

## Economics
- Margin: <e.g. flat 20% assumed>
- Breakeven ROAS: <e.g. 500% gross; treat as a floor>
- AOV floor: <e.g. exclude items <= $10>

## Hard rules
- No account changes without Adam's explicit approval.
- No em dashes in user-facing output.
- Use the local `shopify-toolup` MCP, never the cloud Shopify tools.

## Account quirks
- <catalog size, inventory behavior, anything non-obvious>

## Known gaps / data we do not have
- <e.g. cost-per-item not exposed; no competitor price source>

## Decision log
See `DECISIONS.md` in this folder (if present).
```

### STATE.md template

```markdown
# <Account Name>: Working State

Last updated: <YYYY-MM-DD>. The live snapshot of where this account stands. Fast-changing. For durable facts see NOTES.md.

## Current stage
<e.g. Stage 1 learning planned; nothing pushed>

## What is live in the account
<current campaigns, bid strategies, budgets, trailing performance>

## What is proposed (not pushed)
<the proposal awaiting approval; link the proposal doc>

## Last action
<what was done, date>

## Next action
<the single next step, on Adam's go>

## Open questions / waiting on
<muddy items, merchandising actions, confirmations needed>

## Changelog (newest first)
- <YYYY-MM-DD>: <what changed>
```

### Account registry

| Account | customer_id | Shopify key | Folder | Stage / status | Last touched |
|---|---|---|---|---|---|
| Pro Work Supply | `1532947017` | `wood-shop-outlet` | `pro-work-supply/` | Stage 1 campaign created PAUSED (Manual CPC); awaiting enable | 2026-06-19 |
| Spyder Supply | `9267883382` | TBD (not in Shopify server yet) | `spyder-supply/` | Onboarding; ads account live (empty), awaiting Shopify store key + diagnosis | 2026-06-19 |

Add a row when you begin a new account project and create its folder.

## Maintenance and self-improvement

This markdown system stays useful only if it is maintained. The rules:

- **After every working session on an account, update that account's `STATE.md`**: current stage, last action, next action, open questions, and a dated changelog line. Stale state is worse than no state.
- **A durable new fact about an account** (identifier, economics, quirk, gap, hard rule) goes in that account's `NOTES.md`, and bump its "Last updated" date.
- **A genuinely evergreen, account-agnostic PPC lesson** goes in this file's "Retained best practices" section, but only after consulting Adam. Do not silently rewrite best practices. This mirrors the self-improvement rule in `CAMPAIGN_CREATION_BEST_PRACTICES.md`: propose the addition, explain why it is evergreen, append on confirmation.
- **Keep the account registry in sync.** New project = new folder + new registry row. Update the "Last touched" and "Stage / status" columns as work progresses.
- **Bump "Last updated" dates** whenever you edit this file or a NOTES.md.
