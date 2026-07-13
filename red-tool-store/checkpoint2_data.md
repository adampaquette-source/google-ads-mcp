# Red Tool Store (the-milwaukee-store) — Checkpoint 2 Data Pull

Store key verified via `shopify_list_stores`: `the-milwaukee-store` (confirmed present in the 18-store list). Live site: redtoolstore.com, collection pattern `/collections/<handle>`.

Note on methodology: `shopify_list_collections` for this store has 2,000+ total collections (mostly promo/deal collections), so instead of exhaustive pagination I ran targeted keyword/title searches per theme and cross-checked the 16 "known handles" given in the brief. All handles below were confirmed to exist and be published with the listed live product count at time of pull (2026-07-13).

---

## 1. Collection map for ad-group landings

| Ad-group theme | Best-matching handle | Exists / Published? | Product count | Notes / fallback |
|---|---|---|---|---|
| PACKOUT boxes/storage | `packout-storage` | Yes | 72 | Title "Milwaukee PACKOUT Tool Boxes"; there's also a broader `packout-rolling-storage` (109) and `packout-shop-storage` (86, wall-mount) if you want to split rolling vs. shop storage |
| PACKOUT accessories (backpack/cooler/radio/socket sets) | `packout-accessories` | Yes | 15 | Narrow but on-theme. No dedicated backpack/cooler/radio sub-collection exists; `milwaukee-storage-gear` (42) is a reasonable adjacent fallback if 15 products is too thin |
| M18 batteries and chargers | `m18-batteries-and-chargers` | Yes | 62 | Also a combined `batteries-and-chargers` (129, both platforms) if you want one ad group |
| M12 batteries | `m12-batteries-and-chargers` | Yes | 31 | Same combined-parent option as above |
| Drills (drill/driver, hammer drill) | `drills` | Yes | 51 | Sub-splits exist: `m18-drills` (24), `m12-drills` (21), `milwaukee-drill-drivers` (16), `milwaukee-hammer-drills` (10, M18-specific hammer drills), `milwaukee-drilling-and-driving` (97, drilling+driving combined). Use `drills` as the parent landing; use `milwaukee-hammer-drills` if you split out a hammer-drill-specific ad group |
| Impact wrenches | `impact-wrenches` | Yes | 83 | Voltage splits: `m18-impact-wrenches` (61), `m12-impact-wrenches` (22) |
| Impact drivers | `impact-drivers` | Yes | 25 | Voltage splits: `m18-impact-drivers` (14), `m12-impact-drivers` (11) |
| Ratchets | `milwaukee-ratchets` | Yes | 16 | Thin; consider folding into Mechanic Tool Sets or Automotive Tools if standalone volume is low |
| Combo kits | `combo-kits` | Yes | 170 | Voltage splits: `m18-combo-kits` (36), `m12-combo-kits-1` (16) |
| Nailers | `nailers` | Yes | 24 | — |
| Circular saws | `milwaukee-circular-saws` | Yes | 14 | There's also `milwaukee-metal-circular-saws` (4) if you want a metal-cutting variant |
| Recip saws / sawzall | `milwaukee-recip-saws` | Yes | 21 | See Ahrefs section below on "sawzall" vs "recip saw" phrasing in copy/keywords |
| Miter saws | `milwaukee-miter-saws` | Yes | 4 | Very thin (4 products) — verify feed coverage before building a dedicated ad group; consider folding into a general Saws landing if inventory doesn't support standalone spend |
| Table saws | `milwaukee-table-saws` | Yes | 2 | Extremely thin (2 products) — same caution as miter saws, even more so. Flag: this ad group may not be worth a dedicated build |
| Blowers | `milwaukee-blowers` | Yes | 14 | Voltage splits: `milwaukee-m18-blowers` (8), `milwaukee-m12-blowers` (2) |
| Vacuums | `vacuums` | Yes | 21 | — |
| Grinders | `grinders` | Yes | 57 | Also `milwaukee-angle-grinders` (31) and `milwaukee-die-grinders` (14) as sub-splits |
| Tire inflators | `milwaukee-inflators` | Yes | 5 | Voltage splits: `m12-inflators` (3), `milwaukee-m18-inflators` (2). Thin category overall |
| Lighting / flashlights | `lighting` | Yes | 90 | Healthy count, no dedicated "flashlight" sub-collection found — `lighting` covers it |
| Heat guns | `heat-guns` | Yes | 6 | Thin but exists |
| Laser levels | `lasers` | Yes | 35 | Healthy count |
| String trimmers / mowers | `milwaukee-string-trimmers` | Yes | 6 | **Flag:** no true "mower" collection with meaningful inventory — `milwaukee-lawn-mowers` (1) and `milwaukee-m18-mowers` (2) exist but are essentially empty. Milwaukee doesn't have a real walk-behind mower lineup; see also Job 2 (riding mower = NOT FOUND). Recommend a String Trimmers ad group only, drop "mower" as its own theme or fold it into Outdoor Power Tools (`outdoor-power-tools`, 80 products) |
| Chainsaws | `milwaukee-chainsaws` | Yes | 12 | Also `milwaukee-m18-chainsaws` (9) |
| Mechanics tool sets | `milwaukee-mechanic-tool-sets` | Yes | 52 | Also `milwaukee-packout-mechanics-tool-sets` (19) if you want a PACKOUT-specific angle |
| Hand tools | `hand-tools` | Yes | 764 | Very broad parent, healthy inventory |

All 16 handles supplied in the brief as "known from the live nav" were verified to exist and be published: `m18-tools` (658), `m12-tools` (301), `mx-fuel` (47), `packout-storage` (72), `packout-shop-storage` (86), `milwaukee-storage-gear` (42), `impact-wrenches` (83), `milwaukee-mechanic-tool-sets` (52), `milwaukee-ratchets` (16), `milwaukee-crimpers` (29), `hole-saws` (201), `drill-bits` (486), `saw-blades` (271), `hand-tools` (764), `apparel` (411), `power-tools` (909).

**No theme was left with zero reasonable collection.** The only real gap is "mower" (flagged above) — treat it as a drop or a fold-in, not a standalone ad group.

---

## 2. Catalog fit checks (Shopify product search, active-status verified)

| Query | Result |
|---|---|
| milwaukee snow blower | **STOCKED (1 product)** — "Milwaukee 3036-22HD M18 FUEL 21" Auger Propelled Dual Battery Single Stage Snow Blower Kit", ACTIVE, $1,499.00 (compare-at $2,629.00), 10 in inventory |
| milwaukee vacuum pump (HVAC/refrigerant type) | **STOCKED (1 product)** — "Milwaukee 2941-21 M18 FUEL 5 CFM Vacuum Pump Kit", ACTIVE, $899.00, 5 in inventory. (Search also surfaced several "Vac-U-Rig" diamond-coring-rig accessories and a DRAFT duplicate of the same 2941-21 kit — those are irrelevant/non-active and excluded from the count.) |
| milwaukee mag drill | **NOT FOUND (active)** — every magnetic drill press product in the catalog is DRAFT / 0 inventory: 2787-22 (M18 FUEL Cordless Magnetic Drill Press Kit), 2788-22 (Lineman Magnetic Drill Kit), 4208-1, 4210-1 (Electromagnetic Drill Presses), 4253-1 (drill motor for mag stands), 48-10-0130 (mag drill pipe adapter). Do not build a "mag drill" ad group pointing at active inventory — there is none currently live |
| milwaukee core drill | **NOT FOUND (active, as a complete tool)** — all diamond coring motors, rigs, and base stands (4004-20, 4094, 4096, 4097-20, 4115, 4120, 4120-22, 4136) are DRAFT / 0 inventory. The only genuinely ACTIVE "core" items are individual core bits and small accessories (e.g. "48-17-0112 1-1/4" Diamond Ultra Dry Core Bit", ACTIVE, $139, 2 in stock; various concrete/masonry core bits and bit adapters). There is no active core drill motor/rig to sell as a hero product |
| milwaukee riding mower | **NOT FOUND** — 0 results. Milwaukee does not make a riding mower; consistent with the "mower" gap flagged in Job 1 |

**Bottom line:** Snow Blower and Vacuum Pump are legitimately stockable ad-group targets (1 SKU each, low depth but real). Mag Drill, Core Drill, and Riding Mower should NOT get dedicated ad groups against current inventory — nothing sellable is active.

---

## 3. Sawzall keyword research (Ahrefs, US)

### Overview (`keywords-explorer-overview`)

| Keyword | Volume/mo | CPC | KD |
|---|---|---|---|
| sawzall | 66,000 | $30 | 3 |
| milwaukee sawzall | 13,000 | $25 | 3 |
| milwaukee hackzall | 4,100 | $25 | 1 |
| milwaukee sawzall blades | 1,500 | $25 | 1 |
| m18 sawzall | 1,300 | $25 | 6 |

### Matching terms on "milwaukee sawzall" (top by volume)

| Keyword | Volume/mo | CPC | KD |
|---|---|---|---|
| milwaukee sawzall | 13,000 | $25 | 3 |
| milwaukee sawzall 12 amp saw kit | 4,100 | — | — |
| milwaukee m18 super sawzall saw | 2,300 | — | — |
| milwaukee sawzall m18 | 2,000 | $25 | 6 |
| sawzall milwaukee | 1,600 | $20 | 0 |
| milwaukee sawzall blades | 1,500 | $25 | 1 |
| milwaukee 15 amp super sawzall orbital sawzall | 1,400 | — | — |
| milwaukee super sawzall | 1,300 | $30 | 5 |
| milwaukee electric sawzall 11 amp | 1,200 | — | — |
| milwaukee m18 sawzall | 1,100 | $20 | 8 |
| milwaukee sawzall cordless saw | 1,100 | — | — |
| milwaukee fuel sawzall | 900 | $20 | 2 |
| milwaukee sawzall corded | 800 | $25 | 0 |
| milwaukee cordless sawzall | 800 | $25 | 3 |
| milwaukee m18 fuel sawzall | 700 | $25 | 3 |

### Verdict

Yes — "sawzall" phrasing materially outweighs "reciprocating saw" for this ad group. The bare term "sawzall" alone pulls 66,000/mo nationally, and "milwaukee sawzall" alone (13,000/mo) is more than 7x the stated "reciprocating saw" figure (1,800/mo). Even the long tail is dominated by "sawzall" variants (m18 sawzall, hackzall, super sawzall, sawzall blades) rather than generic "recip saw" language, and difficulty is very low across the board (KD 0-8). Recommendation: lead search themes/headlines with "Sawzall" and "Milwaukee Sawzall," and use "reciprocating saw" only as a secondary/technical variant, not the primary term, for the `milwaukee-recip-saws` ad group.

---

## 4. Campaign B flagship model verification (roster: `rts_top100_products_365d.csv`)

All 13 handles resolved via `shopify_get_product` / handle-scoped search. (Note: `shopify_get_product` requires a numeric/GID product ID, not a handle — handles were resolved via `shopify_search_products` with a `handle:` filter query instead, then status read from the result.)

| Model | Handle | Status / Stock |
|---|---|---|
| 3841-20 | `milwaukee-3841-20-m18-hotshot-jump-starter` | ACTIVE — 389 in stock, $299.00 |
| 48-11-1813 | `milwaukee-48-11-1813-m18-redlithium-forge-hd12-0-battery-pack` | ACTIVE — 752 in stock, $259.00 |
| 2967-20 | `milwaukee-2967-20-m18-fuel-1-2-high-torque-impact-wrench-w-friction-ring-bare` | ACTIVE — 249 in stock, $299.00 |
| 48-22-9495 | `milwaukee-48-22-9495-366pc-master-mechanics-hand-tool-set-with-packout-drawers-and-dolly` | ACTIVE — 49 in stock, $3,999.99 |
| 48-22-8427 | `milwaukee-48-22-8427-packout-rolling-tool-box` | ACTIVE — 259 in stock, $169.00 |
| 3697-27 | `milwaukee-3697-27-m18-fuel-7-tool-combo-kit` | ACTIVE — 33 in stock, $1,249.00 |
| 0887-20 | `milwaukee-0887-20-m18-brushless-precision-blower` | ACTIVE — 33 in stock, $179.00 |
| 2848-20 | `milwaukee-m18-compact-tire-inflator-bare-tool` | ACTIVE — 353 in stock, $166.05 |
| 3632-21 | `milwaukee-3632-21-m12-green-360-3-plane-laser-kit` | ACTIVE — 93 in stock, $525.79. **Caveat:** the roster CSV's top-ranked row for this model used handle `...-kit-1` (flagged `duplicate_model_diff_listing` in the CSV), which is a DRAFT/unpublished duplicate (12 units). The live/published version is the un-suffixed handle above — use that one for any Ahrefs/landing-page work, not the `-1` variant |
| 5150-20 | `milwaukee-5150-20-m18-fuel-branch-conduit-bender-w-auto-zero` | ACTIVE — 15 in stock, $2,999.00 |
| 48-11-1852 | `milwaukee-48-11-1852-m18-battery-2-pack-w-free-48-11-1850-m18-battery-pack` | ACTIVE — 321 in stock, $215.07 |
| 48-11-1862 | `milwaukee-48-11-1862-m18-redlithium-high-output-xc6-0-battery-2-pack` | ACTIVE — 7,898 in stock, $261.26 |
| 48-11-1850 | `milwaukee-48-11-1850-m18-redlithium-xc-5-0-extended-capacity-battery-pack` | ACTIVE — 1,251 in stock, $169.00 |

All 13 flagship models are ACTIVE and in stock. Only flag: 3632-21's specific CSV-ranked row/handle is a draft duplicate — use the canonical published handle noted above instead.
