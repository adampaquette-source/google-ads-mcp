# Pro Work Supply - 3M Shopping Stage 1 (Learning) - PROPOSAL

| Field | Value |
|---|---|
| Account | Pro Work Supply (`1532947017`) |
| Shopify store | `wood-shop-outlet` |
| Status | DRAFT PROPOSAL - nothing created or pushed to the account |
| Author | Claude (research pass) |
| Date | 2026-06-16 |
| Margin assumption | Flat 20% (per Adam; cost-per-item not exposed by connector) |
| Breakeven ROAS | 500% |
| Stage 1 budget | $40/day Shopping + ~$5/day Branded Search |

## Objective

Move the account out of its holding pattern by concentrating a capped budget on a small, in-stock, high-demand roster so Smart Bidding can accumulate enough conversions to learn, instead of spreading dollars across 9,283 mostly-commodity, mostly-backordered SKUs. Stage 1 is a 60-90 day learning run; expect sub-breakeven ROAS while buying the account's first real conversion history.

## Why the old approach failed (evidence)

- Trailing 12 months: $1,468.71 spent, 4,632 clicks, **1 conversion ($145.20)**, account ROAS 0.10.
- All 31,307 historical search terms combined: **0 conversions**. Top spend went to commodity terms (scotch brite, steel wool, duct tape, brillo pad).
- Current "PMax-A - ALL SKUS" runs `MAXIMIZE_CONVERSION_VALUE` at **700% tROAS** on the full catalog; with no conversion history it self-throttles to ~$0.70/day actual spend.
- Store-wide Shopify sales (all channels, trailing year): ~$1,400-1,800 across ~14-18 orders. The store has essentially no proven conversion rate yet.

## Demand evidence (Ahrefs, US monthly; CPC in USD)

| 3M line | Volume | CPC | Verdict |
|---|---|---|---|
| 3m respirator | 3,700 | $0.45 | Lead line |
| 3m vhb tape | 2,700 | $0.60 | High ticket, competitive (diff 44) |
| 3m peltor | 2,300 | $0.30 | Lead line |
| 3m full face respirator | 1,500 | $0.45 | Lead line |
| speedglas welding helmet | 900 | $0.35 | Demand exists, restock needed |
| 3m speedglas | 500 | $0.45 | |
| 3m cubitron | 500 | $0.30 | Shopping-suited (not Search) |
| 3m hard hat | 300 | $0.30 | Include |
| 3m cut off wheel / flap disc / hookit / cubitron ii | 30-70 | $0.40-0.60 | Low branded search - Shopping feed only |
| scotch brite / steel wool | 6,500 / 28,000 | $0.30 | EXCLUDE (commodity, unwinnable) |

## Budget math

- Smart Bidding needs ~15-30 conversions / 30 days to exit learning.
- At ~$0.40 CPC and a 1% Shopping CVR: 30 conversions = ~3,000 clicks = ~$1,200/mo = ~$40/day.
- **Budget plan (D21): start at the $25/day floor, scale to $40/day once early CVR is non-zero.** The 1% CVR is an assumption, not proven: Shopify shows only 15 sales / $1,422.80 across ALL channels in the trailing year. Starting at the floor limits tuition while we get the first read on whether this is a traffic problem (store starved of qualified clicks) or a conversion problem (storefront cannot convert). Step up to $40/day on signal.
- Expect months 1-2 at sub-breakeven ROAS (below 500%). This is tuition to manufacture conversion history. The discipline is the hard cap plus the 60-90 day evaluation gate.
- **Watch item:** if CVR is near zero after 2-3 weeks at $25/day, the bottleneck is the storefront, not the ads. Pause and do store-readiness / CRO work before scaling.

## Structure

- **Pause PMax-A at launch (D17).** "PMax-A - ALL SKUS" is the only ENABLED campaign today; pause it when Stage 1 goes live so it does not compete in auction or split the conversion signal.
- **Stage 1 (now): Shopping ONLY (D20).** ONE Standard Shopping campaign, **Maximize Conversions (no ROAS target)**, feed gated to the roster below. Not PMax (PMax leaks to Display/video with no conversion history). No Search campaign in Stage 1: a $5/day Maximize-Conversions Search campaign cannot reach the 15-30 conv/mo learning threshold (~333 clicks/mo at ~$0.45 CPC) and would only fragment signal away from Shopping.
- **Search moves to Stage 2 (D18 + D20):** when introduced, it targets high-demand **3M category terms we are strong in** ("3M [widget type]": 3M respirator, 3M peltor, 3M full face respirator, 3M hard hat, speedglas welding helmet), NOT the store name (near-zero brand demand). Canonical domain: proworksupply.com.
- **Stage 2 (after ~30 conversions banked):** introduce the Search campaign above, switch Shopping to Target ROAS starting ~400%, **stepping up toward an ~800% goal ROAS (D19)** which clears the 500% gross breakeven with cushion for net costs; then test a PMax fed by proven winners and widen the feed.

## Feed rules (ratified - see DECISIONS.md)

1. **Include ACTIVE + published + sellable SKUs, including backorder / out-of-stock** (D10). Do not gate to in-stock only; items do not auto-drop when OoS. Assume a lowered CVR for backorder items.
2. **Exclude DRAFT and genuinely non-sellable products** (D8 - confirmed already excluded).
3. **No MAP constraint on these SKUs** (D9) - free to advertise discounted prices.
4. **AOV floor (D14):** exclude any item priced **$10.00 or below**. Advertise only items priced above $10.
5. **Backorder availability (D15):** Adam owns feed-side availability handling - not a project concern or blocker.
6. Classify each-vs-case from the title `(N Pack)`, not the `each` tag (tag is unreliable).

Note: the roster below lists current inventory for prioritization, but per D10 low/zero-stock sellable SKUs remain eligible on a backorder basis.

## Stage 1 roster (in-stock, ACTIVE, verified from titles)

### Group A - Full Face Respirators (lead demand 3,700 / 1,500)
| SKU | Title | Price | Inv |
|---|---|---|---|
| 835470 | FF-401 Ultimate FX Full Facepiece, Small | $248.44 | 4 |
| 837168 | FF-402 Ultimate FX Full Facepiece, Medium | $248.44 | 3 |
| 835531 | FF-801 Secure Click Full Facepiece, Small | $257.21 | 4 |
| 835533 | FF-802 Secure Click Full Facepiece, Medium | $257.21 | 3 |
| 835535 | FF-803 Secure Click Full Facepiece, Large | $257.21 | 4 |
| 238083 | 6800 Full Facepiece, Medium | $236.66 | 10 |
| 238084 | 6900 Full Facepiece, Large | $236.26 | 13 |

### Group B - Hearing / Peltor (demand 2,300 / 250) - each units, good stock
| SKU | Title | Price | Inv |
|---|---|---|---|
| 837256 | X4P51E Peltor Full Brim Helmet Attached Earmuffs | $34.42 | 14 |
| 837257 | X4A Peltor Over-the-Head Earmuffs 27 dB | $31.43 | 6 |
| 837258 | X4P5E-OR Peltor Hard Hat Attached Earmuffs | $32.30 | 15 |
| 844673 | X5P3E Peltor Hard Hat Attached Earmuffs 31 dB | $38.06 | 10 |
| 844667 | H6A/V Peltor Optime 95 OTH | $19.29 | 10 |
| 844676 | H10A Peltor Optime 105 OTH 30 dB | $35.49 | 5 |
| 844681 | H10B Peltor Optime 105 BTH 29 dB | $35.49 | 8 |
| 844773 | H7P3E Peltor Optime 101 Hard Hat Attached | $27.17 | 10 |

(Excluded for Stage 1: $800-1,290 Peltor LiteCom/WS comm headsets at qty 1 - revisit in Stage 2 as high-AOV niche.)

### Group C - Hard Hats / Safety Helmets (demand 300)
| SKU | Title | Price | Inv |
|---|---|---|---|
| 835478 | H-807SFR-UV SecureFit Full Brim, Hi-Vis Orange | $16.92 | 20 |
| 837121 | H-811SFR-UV SecureFit Full Brim, Tan | $16.92 | 20 |
| 837126 | H-806SFR-UV SecureFit Full Brim, Orange | $16.92 | 20 |
| 837255 | H-805SFR-UV SecureFit Full Brim, Red | $16.92 | 18 |
| 439384 | X5001 SecureFit Helmet, White | $88.20 | 9 |
| 439388 | X5005 SecureFit Helmet, Red Climbing | $88.20 | 9 |
| 439390 | X5012 SecureFit Helmet, Black | $88.20 | 6 |
| 439391 | X5014 SecureFit Helmet, Hi-Vis Green | $96.08 | 9 |
| 439392 | X5001V SecureFit Helmet, Vented White | $88.20 | 6 |
| 439398 | X5012V SecureFit Helmet, Vented Black | $91.53 | 13 |
| 439399 | X5014V SecureFit Helmet, Vented Hi-Vis Green | $88.20 | 9 |
| 439400 | X5001X SecureFit Helmet, White | $112.27 | 4 |
| 439401 | X5002X SecureFit Helmet, Yellow Climbing | $104.80 | 4 |
| 439402 | X5003X SecureFit Helmet, Blue | $104.79 | 5 |
| 439406 | X5012X SecureFit Helmet, Black Reflective | $104.79 | 3 |
| 439407 | X5014X SecureFit Helmet, Hi-Vis Green Reflective | $104.79 | 4 |
| 439409 | X5002VX SecureFit Helmet, Yellow Vented | $104.79 | 4 |
| 439416 | X5014VX SecureFit Helmet, Hi-Vis Green Vented | $104.79 | 4 |

### Group D - Welding / Speedglas (demand 900 / 500) - included per D13
Complete ADF welding helmets are the demand match. All helmets are OoS today, so these ride on a backorder basis (R2 availability flagging required).

In stock:
| SKU | Title | Price | Inv |
|---|---|---|---|
| 835801 | Speedglas 9100X Auto Darkening Filter, Sh 5/8-13 | $590.80 | 2 |
| 835523 | Speedglas Heavy-Duty Back Pack | $136.00 | 6 |

ACTIVE, OoS - include on backorder (D13):
| SKU | Title | Price | Inv |
|---|---|---|---|
| 850212 | Speedglas G5-03 Pro Welding Helmet w/ Hard Hat (No ADF) | $170.26 | 0 |
| 849985 | Speedglas 100V Welding Helmet, ADF Sh 8-12 | $344.00 | 0 |
| 850211 | Speedglas G5-03 Pro Welding Helmet w/ G5TW ADF | $635.69 | 0 |
| 850014 | Speedglas 9100 Welding Helmet w/ ADF 9100X | $788.57 | 0 |

DRAFT - must be PUBLISHED before they can be advertised (merchandising action):
| SKU | Title | Price | Status |
|---|---|---|---|
| 837170 | Speedglas 9002NC Welding Helmet w/ NC ADF | $428.28 | DRAFT |
| 835548 | Speedglas 9100 Welding Helmet w/ ADF 9100XXi | $925.19 | DRAFT |

(Speedglas accessories/plates at $6-95 excluded - parts, low intent, below AOV floor.)

### Group E - Cubitron II Abrasives (low branded search, high Shopping intent + AOV)
| SKU | Title | Price | Inv |
|---|---|---|---|
| 835459 | 775L Xtract Cubitron II Film Disc 120+ 5in (50pk) | $54.00 | 5 |
| 835462 | 775L Xtract Cubitron II Film Disc 120+ 6in (50pk) | $75.38 | 4 |
| 835465 | 775L Xtract Cubitron II Film Disc 180+ 5in (50pk) | $54.00 | 3 |
| 835484 | 967A Cubitron II Flap Disc 40+ 4.5in (10pk) | $93.60 | 2 |
| 835526 | 982C Cubitron II Fibre Disc 60+ (25pk) | $172.69 | 4 |
| 835586 | 987C Cubitron II Fibre Disc 36+ (25pk) | $126.19 | 4 |

(Excluded by D14 AOV floor: 835775 969F Cubitron II Flap Disc Giant, $8.75.)

### Group F - Disposable Respirators (deep stock, recognizable - conversion generators)
| SKU | Title | Price | Inv |
|---|---|---|---|
| 23280 | 8511 N95 w/ Cool Flow Valve (Box of 10) | $34.48 | 188 |
| 23288 | 8210 N95 Cup Style (20 Pack) | $17.99 | 207 |
| 23376 | 8210V N95 | $21.35 | 275 |
| 23287 | 8200 N95 Cup Style (20 Pack) | $12.99 | 118 |
| 23260 | 8233 N100 Particulate Respirator | $13.84 | 26 |
| 379740 | 8577 P95 w/ Vapor Relief (10 Pack) | $64.39 | 52 |
| 23293 | 8214 N95 Faceseal + OV Relief (10 Pack) | $112.00 | 21 |
| 23372 | 8212 Welding Respirator (10 Pack) | $98.77 | 11 |
| 837169 | 8246 R95 Acid Gas Relief (20 Pack) | $91.69 | 9 |

### Group G - Fall Protection (high AOV; thin stock = backorder per D10)
| SKU | Title | Price | Inv |
|---|---|---|---|
| 839704 | Protecta SRL, Galvanized Cable, 33 ft | $604.44 | 2 |
| 839703 | Protecta SRL, Stainless Cable, 33 ft | $771.57 | 1 |
| 839705 | Protecta SRL, Stainless Cable | $909.97 | 1 |
| 839758 | Protecta 60 ft Horizontal Lifeline System | $437.85 | 1 |
| 837125 | Quick Wrap Tape, tool tethering | $26.11 | 1 |

### Group H - Eye Protection (mostly EXCLUDED per AOV floor R1)
| SKU | Title | Price | Inv | Note |
|---|---|---|---|---|
| 840206 | Nuvo Z87 Safety Glasses (20 Pack) | $167.20 | 2 | Include (multipack) |
| 837129 | Nuvo Z87 Safety Glasses (each) | $8.36 | 54 | EXCLUDE - below AOV floor |
| 837254 | Tekk Virtua Safety Glasses (each) | $2.13 | 19 | EXCLUDE - below AOV floor |

Roster total: ~57 advertised SKUs (excludes the two sub-$10 eye singles). Blend is intentional: high-AOV margin drivers (respirators, helmets, SRLs, Cubitron) plus deep-stock recognizable conversion generators (N95s, earmuffs) to feed Smart Bidding enough conversions during learning.

## Open items / flags for Adam

1. **All Stage 1 decisions ratified (D1-D16).** No open decisions remain.
2. **Merchandising action (Adam's side):** publish the two DRAFT Speedglas ADF helmets (837170 $428, 835548 $925) if you want them advertised.
3. **Lowered-CVR assumption for backorder:** budget math used ~1% blended CVR; backorder-heavy mix may run lower. Watch cost-per-conversion in the first 2-3 weeks and adjust the cap if learning stalls.
4. **Cost-per-item not exposed by the Shopify connector.** Using flat 20%. For Stage 2 profit ranking, a SKU+cost export would let me rank by true margin.
5. **Price-vs-market data:** no competitor-price source wired up; D13's "excellent price vs market" test currently leans on discount depth + your stance. Worth a real source before scaling backorder SKUs.

## Revision log
- 2026-06-16: Initial roster and structure drafted from Google Ads history, Shopify catalog, and Ahrefs demand. No account changes made.
- 2026-06-16: Ratified D8-D12. Feed rules updated (backorder stays in, lowered CVR). Added Disposable Respirators (Group F), Fall Protection (Group G), Eye Protection w/ AOV floor (Group H). Roster ~57 advertised SKUs.
- 2026-06-16: Ratified D13 (OoS higher bar; Speedglas included). Group D expanded with actual Speedglas ADF welding helmets (4 ACTIVE-OoS on backorder; 2 DRAFT needing publish). Roster ~61 advertised SKUs + 2 pending DRAFT publish.
- 2026-06-16: Ratified D14 (AOV floor: exclude items $10.00 or below), D15 (feed availability is Adam's concern, not a blocker), D16 (Stage 2 trigger ~30 conversions/30 days). All Stage 1 decisions closed.
- 2026-06-17: Verified live account (6 of 7 campaigns already paused; commodity bleed from paused manual-CPC Shopping; PMax-A starvation confirmed). Ratified D17 (pause PMax-A at launch), D18 (Search targets 3M category terms on proworksupply.com, not the store name), D19 (Stage 2 goal ROAS ~800%). Updated Structure section accordingly.
- 2026-06-17: Pulled trailing-year Shopify sales (15 products / $1,422.80, all channels); the single $145.20 Ads conversion maps to a real Shopify order, confirming tracking works. Ratified D20 (Stage 1 Shopping only, Search to Stage 2) and D21 (budget starts $25/day, scales to $40 on CVR signal). Updated Structure and Budget math.
