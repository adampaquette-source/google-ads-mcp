# Spyder Supply: Launch Strategy & Research

Last updated: 2026-06-19. Brand + keyword research and the campaign-path recommendation for the cold launch of Spyder Supply (`9267883382`, US-wide). PRELIMINARY pending (a) the cold-start strategy research brief and (b) Adam's approval. Nothing here is pushed.

## Inputs / context
- Account `9267883382`, brand-new, zero conversion history. US-wide. Margin ~30% (breakeven ROAS ~3.3x / 333%). AOV assumed $100-200 (see AOV reality check below).
- Store: spydersupply.com, Shopify key `weather-guard-store` (Truck Box Outlet rebranded in place). Spyder catalog ACTIVE; old WeatherGuard line DRAFT. Ignore pre-transition sales and the old TBO ads account `3174244337`.
- Brand: Spyder Products, founded 2007 (the Spyder Scraper), a value/innovation challenger in power-tool accessories. Competes against category leaders Diablo, Milwaukee, Lenox, MK Morse. Known lines: bi-metal + carbide hole saws, Rapid Core Eject kits, Mach-Blue / Stinger drill bits, spade bits, recip ("Sawzall") blades incl. double-edged 3X3, scrapers, grout-out attachments.

## Keyword research (Ahrefs, US, 2026-06-19)

### Branded demand (~3,600/mo total, cheap, high intent) -- the near-free win
| Keyword | Vol/mo | CPC | Notes |
|---|---|---|---|
| spyder hole saw kit | 1,100 | $0.20 | transactional + branded -- the hero term |
| spyder drill bits | 800 | $0.20 | drill-bit cluster (catalog carries spade bits + arbors; Mach-Blue/Stinger are the famous twist bits) |
| spyder hole saw | 300 | $0.25 | |
| spyder bits | 300 | $0.20 | |
| spyder drill bit set | 150 | $0.45 | |
| spyder blades | 100 | $0.30 | |
| spyder sawzall blades | 100 | $0.30 | |
| spyder hole saw arbor | 90 | $0.30 | accessory/attach |
| spyder mach blue drill bits | 80 | $0.45 | |
| spyder hole saw bits | 80 | $0.35 | |
| spyder scraper / scraper blade | 80 | $0.20 | the origin product |
| spyder saw blades / recip / jigsaw | 130 | $0.25 | |
Noise to exclude as negatives: "spyder bite/bit/bites" (low-CPC spider-game traffic), "maserati biturbo spyder".

### Category (non-brand) demand -- bigger, cheap, but competitive vs big brands
| Keyword | Vol/mo | CPC | Intent |
|---|---|---|---|
| grout removal tool | 7,300 | $0.20 | commercial |
| hole saw kit | 4,700 | $0.25 | transactional |
| reciprocating saw blades | 2,800 | $0.25 | transactional |
| carbide hole saw | 900 | $0.30 | transactional |
| carbide tipped hole saw | 200 | $0.45 | transactional |
| bi-metal hole saw | 150 | $0.45 | commercial |
| demolition saw blades | 60 | $0.50 | transactional |

**The single most important economic fact: CPCs are $0.20-0.50 across the board.** Cheap clicks mean a cold account can accumulate the first conversions fast and cheaply -- the opposite of the commodity-bleed that sank PWS. This makes the account economically attractive *if the products convert*.

## AOV reality check (catalog pricing)
- Hero / ad-worthy: 13-pc Rapid Core hole saw kit $81.20, 4" carbide hole saw $79.10, spade-bit set $12.30, larger carbide hole saws $50-79.
- Long tail: single bi-metal hole saws $5-19, spade bits $2-3, arbors $16-20.
- Implication: the $100-200 AOV only holds with kits / multi-item baskets. Sub-$10 single consumables lose money sold solo (ad + shipping > ~30% gross profit). **Curate the Shopping feed to kits + higher-ticket carbide pieces + sets first;** keep the $2-15 singles out of the cold-start campaign (they ride along once a basket/free-ship threshold exists).

## Path recommendation: Standard Shopping + small Branded Search FIRST; PMax deferred

**Recommended Stage 1 (cold start):**
1. **Standard Shopping**, cold-start bidding (Manual CPC ~$0.30-0.50 or Maximize Clicks), US-wide, feed gated via DFW custom_label to a curated high-AOV roster (kits, carbide hole saws, sets). Same DFW lookup -> custom_label gate -> propose/commit pipeline already built for PWS. This is the cheap data-generation engine to earn the first conversions.
2. **Branded Search** (small), exact/phrase on `spyder hole saw kit`, `spyder drill bits`, `spyder hole saw`, `spyder blades`, `spyder scraper`, `spyder hole saw kit` + Rapid Core. Near-free brand capture/defense at $0.20-0.45 CPC, highest intent. (No brand-Search tool exists yet -- would need a small builder, or launch via UI.)

**Deferred to Stage 2 (after ~15-30 conversions clear learning):**
- Switch Shopping to Maximize Conversion Value -> tROAS stepping toward 333%+ (above breakeven for net costs; lower ceiling than PWS's 800% because Spyder margins are thinner).
- Introduce PMax on proven winners (now that there is conversion signal to feed it).
- Test category Search (hole saw kit, reciprocating saw blades) -- but expect tough competition vs Diablo/Milwaukee/Lenox on a no-authority new domain; Shopping is the better vehicle for category demand (compete on price/image, not Quality Score on a cold domain).

### Why NOT PMax-first
- Zero conversion history is PMax's worst-case cold start: it burns budget with no signal, is opaque (no search-term control), leans on Google's audience guesses, and cannibalizes the cheap branded traffic. Practitioner consensus is to feed PMax conversion history first. (To be confirmed/quantified by the cold-start research brief.)
- Standard Shopping + branded Search gives transparent, cheap, controllable first-conversion generation, then graduates into Smart Bidding / PMax once the data exists -- the PWS pattern, but with far better unit economics.

## Cold-start research reconciliation (2026-06-19, see COLD_START_RESEARCH.md)
The dedicated cold-start research brief CONFIRMS this path and pins the numbers:

- **Path validated.** Practitioner consensus: a greenfield account (no history anywhere) has an empty signal pool, so PMax has nothing to borrow and "shoots randomly"; under ~$1k/mo or zero history -> Standard Shopping + Search first, PMax only after ~30 conv/mo. Brand Search = cheapest highest-intent early conversions.
- **Graduation gates (use these as the Stage triggers):**
  - Exit Stage 1 -> Maximize Conversion Value (no target): **15-20 conv / 30 days**.
  - Add Target ROAS: **50+ conv / month** (30 minimum) + ~4 weeks stable value reporting. Set first tROAS within 10-20% of observed, never aspirational (so first target ~observed, stepping toward 333%+).
  - Launch PMax: **30+ conv / month**, feed-first, **with brand exclusions** (so it can't cannibalize the cheap branded Search/Shopping traffic and report inflated ROAS).
- **Budget-for-learning (matters at Stage 2, not Stage 1):**
  - Stage 1 is Manual CPC / Max Clicks -> **no learning phase**, so budget is just "enough cheap clicks to manufacture the first conversions." With $0.20-0.50 CPCs, **$25-40/day buys ~60-160 clicks/day**; at a 1-2% CVR that is roughly 0.5-3 conv/day -> the 15-30 conv graduation threshold is reachable in 2-4 weeks IF the store converts. Mirrors the PWS $25/day Stage 1 floor.
  - Stage 2 (Max Conversion Value) needs budget >= **3-5x daily CPA** to avoid stalling learning. Est. CPA at cheap CPCs ~$15-30 -> ~**$45-150/day**; take the higher of that and the accumulation formula (conv needed x CPA / ~14-day window). Size once; changing budget/settings mid-learning resets the phase (keep changes <=20%, or make big changes all at once).
- **Hard pre-launch gate (failure mode #7):** verify conversion tracking on `9267883382` BEFORE serving -- only true purchases as Primary, confirm "Recording conversions," reconcile vs Shopify. Smart Bidding "lives or dies on data quality." This re-confirms the deferred tracking check is a prerequisite, not optional.

### API-rejection reconciliation (our codebase vs the brief)
The brief could not verify a `NOT_ENOUGH_CONVERSIONS` enum in public docs and says the cold failure is usually operational (starved delivery), not a rejected mutate. **But our own PWS `validate_only` test empirically returned real rejections on STANDARD SHOPPING specifically:** `OPERATION_NOT_PERMITTED_FOR_CONTEXT` for maximize_conversions / maximize_conversion_value, and `NOT_ENOUGH_CONVERSIONS` for target_roas. Both can be true (the brief's doc-search was general/Search-oriented; Standard Shopping enforces differently). Practical rule unchanged: **always `validate_only` the intended bidding strategy before committing on a cold account; do not assume which strategies are permitted.**

## Open items before build
- Reconcile this with the cold-start strategy research brief (in progress) -- especially learning-phase conversion thresholds and budget-for-learning math.
- Adam approval of the path.
- Feed/Merchant Center wiring to `9267883382` (deferred per Adam, but required before Shopping can serve).
- Confirm conversion tracking on the new account (deferred per Adam).
- Set the curated Stage 1 roster (which kits/carbide SKUs) and a daily budget sized to exit learning in ~30 days.
