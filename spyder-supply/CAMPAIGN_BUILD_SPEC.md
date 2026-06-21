# Spyder Supply: Campaign Build Spec (ready to push once DFW + MC are online)

Last updated: 2026-06-21. Executable build plan for the Spyder Supply cold launch on account **`9267883382`** (US-wide, ~30% margin, breakeven ROAS ~3.3x). Implements the ratified path (DECISIONS D4-D8): two Standard Shopping campaigns + a branded Search campaign, all created **PAUSED** via propose/commit. Nothing here serves until the hard prerequisites below are met.

Read `STRATEGY.md` (research + path) and `PPC_ADVISOR.md` (cold-start rules) first. Catalog as of 2026-06-21: **728 active Spyder SKUs, 455 in stock.**

## HARD PREREQUISITES (build is blocked until all three are true)
1. **Merchant Center feed live for `9267883382`** with the Spyder catalog (vendor Spyder, `status:active`), feed_label "US". Capture the **merchant_id** -- required for both Shopping campaigns.
2. **DataFeedWatch writing `custom_label_2`** from the Spyder lookup sheet (see DFW section). Confirm the field maps to `custom_label_2` (PWS confirmed DFW uses index 2, not 0).
3. **Conversion tracking verified** on `9267883382`: a purchase conversion action showing "Recording conversions," only true purchases set Primary, reconciled against Shopify. (Cold-start failure mode #7 -- non-negotiable before any spend.)

## Catalog segmentation (the roster logic)
Rule (applied in `scratchpad/spyder/segment.py`; rosters persisted here):
- **Curated** = vendor Spyder AND in stock (inv>0) AND price >= $15 AND in a demand-bearing category (kits, hole saws, arbors, recip/circular/jig/oscillating blades, spade/auger/twist/step bits, cut-off/grinding). **191 SKUs**, median $29.70, max $213.06.
- **Fallback** = vendor Spyder AND price >= $5 AND not curated. **388 SKUs** (171 currently in stock; the rest auto-serve when restocked -- MC gates live availability).
- **Excluded** (no label, advertised nowhere) = the **149 sub-$5 SKUs** (lose money sold solo at 30% margin once CPC + shipping are counted).

Files in this folder:
- `spyder_dfw_lookup.csv` -- the DFW lookup table: `sku,custom_label_2` (579 rows: curated + fallback; sub-$5 omitted). Source of truth to load into the DFW Google Sheet.
- `spyder_curated_roster.csv` / `spyder_fallback_roster.csv` -- human-readable (sku, label, title, price, inv, cat).

## DataFeedWatch lookup setup
- Create a Spyder tab in the DFW lookup Google Sheet (or a new sheet); load `spyder_dfw_lookup.csv` via the `update_dfw_lookup_table` MCP tool. Position-based: col1 = sku (match key), col2 = `spyder_curated` | `spyder_fallback`.
- In DFW: map the lookup output to **custom_label_2**, with the "Only IF ... is in list" safety filter so unmatched SKUs (the sub-$5 set) get no label.
- Sheet sharing: Anyone-with-link = Viewer (DFW reads) + Editor to the service account (MCP writes). Adam sets sharing.

## Campaign A -- Curated Standard Shopping (the learning engine)
`propose_google_ads_standard_shopping_campaign` on `9267883382`, then `commit_...(proposal_id)`. Config:
| Field | Value |
|---|---|
| campaign_name | `Spyder | Shopping | Curated (Core)` |
| daily_budget_usd | **30.00** (bulk of spend; tune after first 2 weeks) |
| merchant_id | (from prereq 1) |
| custom_label_value | `spyder_curated` |
| custom_label_index | **2** |
| feed_label | `US` |
| campaign_priority | **2** (High) |
| bidding_strategy | **`manual_cpc`** (account is cold; validate_only first) |
| max_cpc_usd | **0.45** |
| geo_target_ids | `["2840"]` (USA) |
| status | PAUSED (enforced by the tool) |

Hero SKUs (highest-AOV in-stock, the items the curated campaign exists to sell):
- Kits: 600938 18-pc TCT ($213), 601008 Rapid Core BiMetal ($143.50, inv 38), 600880 14-pc TCT ($139), 600925 9-pc Carbide RCE ($87).
- Recip multipacks: 200307-50 / 200306-50 12" ($208-210), 200304/200305-50 9" ($125).
- Deep-cut carbide hole saws: 600838 6" ($128), 600837 5-1/4" ($122), 600836 4-3/4" ($90).
- Circular blades: 13506 14" 72T ($137), 13505 12" 60T ($108).

## Campaign B -- Fallback Standard Shopping (long tail, low priority)
Second propose/commit. Config differs from A:
| Field | Value |
|---|---|
| campaign_name | `Spyder | Shopping | Fallback (All >= $5)` |
| daily_budget_usd | **10.00** |
| custom_label_value | `spyder_fallback` |
| custom_label_index | **2** |
| campaign_priority | **0** (Low) |
| bidding_strategy | **`manual_cpc`** |
| max_cpc_usd | **0.30** (lower -- thinner-margin long tail) |
| merchant_id / feed_label / geo / status | same as A (PAUSED) |

The two campaigns are gated to mutually-exclusive `custom_label_2` values, so no product is eligible in both -- priority is belt-and-suspenders, not arbitration. (`pause_campaign_ids` not needed; the account is empty.)

## Campaign C -- Branded Search (cheap, high-intent; defends + harvests brand demand)
Branded demand ~3,600/mo, CPCs $0.20-0.45. **No Standard-Search creation tool exists yet** -- decision pending (build a small builder vs. launch via the Google Ads UI). Spec below is launch-ready either way. One campaign, US-wide, Manual CPC (~$0.40 cap) or a small daily budget (~$8-10), PAUSED. Ad groups (each keyword carries the brand term; phrase + exact; final URL = the matching collection):

| Ad group | Keywords (phrase/exact) | Vol/mo | Final URL (collection handle) |
|---|---|---|---|
| Hole Saw Kits (hero) | spyder hole saw kit, spyder hole saw kits, spyder carbide hole saw kit, spyder tct hole saw kit, spyder rapid core kit | ~1,150 | `/collections/spyder-hole-saws` |
| Hole Saws | spyder hole saw, spyder hole saws, spyder carbide hole saw, spyder diamond hole saw, spyder bi-metal hole saw, spyder deep cut hole saw | ~360 | `/collections/spyder-metal-and-wood-hole-saws` |
| Hole Saw Arbors | spyder hole saw arbor, spyder hole saw arbors, spyder hole saw bits, spyder arbor | ~170 | `/collections/spyder-arbors-and-pilot-bits` |
| Drill Bits (hero) | spyder drill bits, spyder bits, spyder drill bit set, spyder bit set, spyder drill bit | ~1,360 | `/collections/spyder-drilling-driving` |
| Spade & Wood Bits | spyder spade bit, spyder spade bits, spyder auger bit, spyder stinger drill bits, spyder stinger | ~110 | `/collections/spyder-wood-drilling` |
| Step Bits | spyder step bit, spyder step drill bit, spyder mach blue step drill bits | ~60 | `/collections/spyder-step-drill-bits` |
| Recip & Saw Blades | spyder blades, spyder sawzall blades, spyder reciprocating saw blades, spyder saw blades, spyder recip blades | ~300 | `/collections/spyder-reciprocating-saw-blades` |
| Circular/Jig/Oscillating | spyder circular saw blade, spyder circular saw blades, spyder jigsaw blades, spyder oscillating blades | ~70 | `/collections/spyder-circular-saw-blades` |
| Mach-Blue (sub-brand) | spyder mach blue, spyder mach-blue, spyder mach blue drill bits, spyder mach blue impact bits | ~110 | `/collections/spyder-mach-blue` |
| Impact & Driver Bits | spyder impact bits, spyder driver bits, spyder mach blue impact bits | ~50 | `/collections/spyder-driving-and-fastening` |
| Brand catch-all | spyder products, spyder tools, spyder tarantula, spyder black series | ~150 | homepage / `/collections/all-products` |

Paused / hold ad groups (demand exists but product is OOS as of 2026-06-21 -- launch when restocked):
- Scrapers: spyder scraper, spyder scraper blade (~80/mo) -- Scraper category 0 in stock.
- Grout: spyder grout out, grout removal tool (brand ~0; category 7,300 is non-brand, route via Shopping) -- Grout 0 in stock.

Match-type + negatives:
- Phrase + exact only (brand terms are cheap/high-intent; broad invites waste). Add the misspell/irrelevant set as campaign negatives: `spyder bite`, `spyder bit` (singular, game traffic), `maserati`, `biturbo`, `spider-man`, `spider`, `paintball`, `ski`.
- Exclude brand terms from PMax when PMax launches in Stage 2 (so Search keeps the cheap branded conversions; cold-start failure mode).

## Bidding, budget, and the graduation path (from PPC_ADVISOR.md / COLD_START_RESEARCH.md)
- **Stage 1 = Manual CPC** on all three campaigns. Manual CPC has no learning phase, so budget is just "enough cheap clicks." Total ~$48/day ($30 curated + $10 fallback + ~$8 branded Search). At $0.20-0.45 CPC that is ~120-200 clicks/day.
- **`validate_only` every Shopping bidding strategy before committing.** PWS empirically hit `OPERATION_NOT_PERMITTED_FOR_CONTEXT` (max-conv/value) and `NOT_ENOUGH_CONVERSIONS` (tROAS) on cold Standard Shopping; only manual_cpc / maximize_clicks were permitted.
- **Graduate the Curated campaign** at 15-20 conv/30d -> Maximize Conversion Value (no target); add Target ROAS at 50+ conv/mo, first target near observed, stepping toward ~333%+ (above breakeven for net costs). Do NOT change strategy/budget mid-learning (<=20% changes, or all at once).
- **Stage 2:** introduce PMax (feed-first, brand-excluded, 30+ conv/mo) and a category-Search test. Not before.

## Build sequence (once prerequisites met)
1. Load `spyder_dfw_lookup.csv` into the DFW sheet (`update_dfw_lookup_table`); confirm DFW writes `custom_label_2`; confirm the feed shows the labels in Merchant Center.
2. `validate_only` then propose/commit **Campaign A** (curated).
3. propose/commit **Campaign B** (fallback).
4. Branded Search **Campaign C** (build tool or UI).
5. Verify structure (campaign, ad group, listing-group gate, budget) on each. Leave everything PAUSED.
6. Enable only after Adam's go + a final conversion-tracking check.

## Open build-time questions for Adam
- Confirm the $30 / $10 / ~$8 daily budget split and the $0.45 / $0.30 max-CPC caps (proposals).
- Branded Search: build a creation tool, or launch via UI?
- Curated price floor is $15 -- raise to $20 (142 SKUs) or lower to $10 (256) if you prefer a tighter/looser core.
- Free-shipping verbiage / threshold for Search ad copy (verify against spydersupply.com before writing RSAs).
