# PROPOSAL — RTS Milwaukee Brand Search Campaign

| Field | Value |
|---|---|
| Status | **V1 drafting — awaiting Checkpoint 1 (scope)** |
| Customer ID | `4033622485` (Themilwaukeestore.com / Red Tool Store) |
| Skill | ToolUp brand-search methodology (`toolup-brand-search-breakouts` as template), adapted single-brand |
| Created | 2026-07-12 |
| Last revised | 2026-07-12 |
| Proposal ID | (assigned at commit) |
| Campaign resource name | (assigned at commit) |

## Step 1 — Scope and account context (pre-flight complete)

30-day account state: $114,981 spend, 3,349 conv, $1.18M value, ROAS 10.29. **No dedicated Milwaukee-brand Search campaign exists.** Milwaukee = $60.4k/30d spend (over half the account) flowing through PMax (`Top IDs`, `Authorized Bundles`, `CL2 high-end-milwaukee`) and Shopping (`Margin Bands`) with zero keyword-level control. The only Search coverage is `QT - Search - TM` (store-trademark defense, ROAS 70.75) and `QT - Search - NB DSA Products` (DSA, $200/day, capped at 10% impression share, 78% of its 6,838 search terms contain "milwaukee").

**The structural difference vs ToolUp:** at ToolUp, Milwaukee is one brand among many; here Milwaukee effectively IS the store. This "brand campaign" is functionally the account's category-level Search buildout.

### 🛑 Checkpoint 1 (scope) — ✅ CONFIRMED by Adam 2026-07-12:

1. **Category scope: full Milwaukee coverage confirmed** per the ad group plan below.
2. **Model/part numbers: build a SEPARATE companion Search campaign** covering the store's top ~100 products with model-number ad groups (Campaign B below). Rationale from Adam: DSA is sunsetting (Google is folding DSA into AI Max) and he is skeptical of AI Max — so the structured pair (this category campaign + the top-100 products campaign) becomes the deliberate replacement for the DSA harvest, keeping keyword-level control instead of migrating to AI Max.
3. **PACKOUT history: a packout campaign was tested and never penciled out on ROAS.** Adam wants the why explored — PACKOUT is a huge category and worth focusing on. Post-mortem data pull on `packout-search` is underway; the PACKOUT ad groups in this campaign will be shaped by those findings (and get their own measurement note) before build.

## PACKOUT post-mortem — why `packout-search` failed, and why this build is different

Campaign `18291700466`, examined 2026-07-12. Lifetime: $1,148 spend, 20.4 conv, $6,447 value, ROAS 5.62x vs a 10x target, across two thin windows (2022: 7.56x; 2026: 4.46x) with a 3-year dormancy and zero structural change between attempts.

**Diagnosis — four compounding structural failures, none of them "PACKOUT can't pencil":**

1. **Starved smart bidding.** MaxConvValue + tROAS 10x on a $50/day silo that collected ~10 conversions per activation. A value bidder cannot exit learning on that volume; the high tROAS then throttles delivery further (the classic cold-start failure mode in PPC_ADVISOR). The 2026 rerun re-used the same setup and did worse, as expected in a pricier auction.
2. **No structure.** One ad group for the campaign's entire life. 29 added keywords total; 99.6% of the 7,132 matched queries were never deliberately targeted, and those uncontrolled broad matches ate 63% of visible spend. It behaved like a bad DSA, not a keyword campaign.
3. **Diffuse spend on a concentrated category.** 91% of matched terms never got a click; only 13 terms ever converted. Meanwhile "milwaukee packout" + "milwaukee packout sale" alone carried ~47% of converted value ("packout sale": $42.64 -> $1,308, ~30x).
4. **Landing/routing quality gap.** Today the DSA campaign's packout queries convert at ~36x on product-page landings (small sample: 32 clicks/30d). The demand converts when the click lands somewhere specific.

**What this build does differently (already reflected in the ad group plan):** PACKOUT split into two themed ad groups with sub-intent keywords, exact + phrase ONLY (no broad discovery), sale/deal phrasings kept as keywords with promo-forward RSA copy (the store's signature bundle offers match that intent), each group landing on its precise collection page, and bidding shared across the whole ~20-group campaign at a realistic tROAS instead of a starving 10x silo. Measurement note: judge PACKOUT groups inside the blended campaign, not as a silo — the prior campaign died partly from being judged as one.

**Category verdict: worth focusing on, as Adam suspected.** The prior test proves the core terms convert; it never disproved the category.

## Campaign B — `QT - Search - Milwaukee Top Products` (added at Checkpoint 1)

Roster pulled 2026-07-12: `red-tool-store/rts_top100_products_365d.csv` (top 100 listings by trailing-365d net sales = $8.9M; top-10 = 29.7%). Key structural facts: 17 rows are duplicate models across separate listings (consolidate per model); 20 rows are signature "w/ FREE [item]" bundles; the `48-59-1852B` M18 Starter Kit family alone spans 7+ listings totaling ~$1.7M; 14 rows currently out of stock; 2 rows lack a printed model number.

### V3 design (revised per Adam 2026-07-12: bundles are a distinctly different group)

**Budgets/tROAS across all campaigns are BEST-GUESS DRAFTS. Adam sets final values himself before publishing — not a checkpoint blocker.** Drafts: A = tROAS 10.5 / $200 day; B = tROAS 12.0 / $150 day; C = tROAS 11.0 / $75 day.

**Campaign B — standard distinct SKUs ONLY (primary).** All "w/ FREE [item]" promotion-bundle listings removed from B (20 of the top-100 rows). What remains: distinct-model catalog products.
- **Unit of design = unique model.** Duplicate-model listings consolidate so bids never compete against themselves.
- **Keyword pattern per model:** exact `milwaukee <model>`, exact bare `<model>` (Milwaukee SKU patterns like 2967-20 / 48-11-1852 are unambiguous; bare-model queries are DSA's best converters), phrase `milwaukee <model>`. Landing = the product page.
- **Ad groups (~14, draft), one product family each, ad group name carries the model(s) for stock-sync mapping** (`B | 2967-20 | M18 FUEL High Torque Impact`): (1) M18 Batteries by SKU — 48-11-1852 / 1850 / 1862 / 1813 FORGE; (2) HOTSHOT Jump Starter 3841-20; (3) Impact Wrenches — 2967-20, 2854-20; (4) PACKOUT SKUs — 48-22-8427 rolling box, 48-22-9495 master set; (5) Combo Kits — 3697-27 / 3697-22; (6) Blowers — 0887-20, 3017-20; (7) Tire Inflators — 2848-20; (8) Lasers — 3632-21; (9) Trade/Specialty high-AOV — 5150-20 conduit bender; (10+) remaining distinct-SKU families from the roster.
- **Held out:** heated-gear SKUs (existing heated campaigns own them); the 14 OOS models at launch; 2 no-model rows.

**Campaign C — `QT - Search - Milwaukee Top Bundles` (Adam open to it; inventory-gated).** The promotion-bundle franchise as its own campaign so its distinct economics and volatile availability never contaminate B:
- Ad groups per offer family: the 48-59-1852B Starter Kit + FREE-item family (~$1.7M/365d across 7+ listings), battery 2-pack + FREE battery offers (48-11-1852 / 48-11-1862 families), Starter Kit 48-59-1850/1852 variants.
- Keywords: `milwaukee starter kit`, `m18 starter kit`, `milwaukee battery deal/bundle/free tool` phrasings + the kit SKUs; RSA copy leads with the FREE-item offer (the store's signature). Landing = the bundle listing (or bundle collection if one exists — verify).
- **Inventory-gated by design:** bundle ad groups are enabled/paused per current offer availability via the stock-sync mechanism below. Bundles rotate; the campaign structure persists.
- **DSA wind-down path:** once A + B (+ C) are stable and covering, reduce DSA budget on Adam's call (no AI Max migration).

### Stock-out maintenance (Adam's side question — proposed mechanism)

Search RSAs are not feed-connected: unlike Shopping/PMax, nothing native pauses a Search ad group when its product goes OOS. Proposed solution using existing infrastructure:

1. **Convention makes it mechanical:** every B/C ad group name embeds its model number(s), and the roster CSV maps model -> Shopify handle.
2. **Control center stock-sync job (new, small):** the existing scheduler pulls Shopify `totalInventory` per roster SKU daily; compares to each mapped ad group's status; any mismatch (OOS + ENABLED, or restocked + PAUSED) becomes a row in a new Stock tab — same propose -> human approve -> commit pattern as tROAS/budget/negatives. One click to pause/re-enable the affected ad groups.
3. **Start propose-only.** Once trusted, OOS-pause could graduate to auto-commit under a Phase 7 guardrail envelope (pausing on OOS is low-risk; auto RE-ENABLE stays human-approved since restocks can be partial).
4. Until the job is built, interim cadence: the monthly audits + a manual stock check against the roster before any budget change.

Open items for B/C: units data unavailable (ShopifyQL `*_item_quantity` columns error on this store — tool gap), public store domain STILL unverified (blocks final URLs), family->landing mapping needs Shopify verification per ad group.

## Step 2 — Proposed structure (V1)

- **Campaign:** `QT - Search - Milwaukee Brand` (matches account naming convention)
- **Bidding:** Maximize Conversion Value + tROAS **10.5** (between Shopping Margin Bands 9.0 and DSA 14.5; Milwaukee blended account ROAS 8.87; PMax breakouts 10-12) — Adam to confirm
- **Budget:** **$200/day** initial (mirrors DSA; small vs the $114k/mo account) — Adam to confirm
- **Settings:** Search Partners OFF, Display Expansion OFF, US, English, created PAUSED
- **Landing pages:** every ad group lands on its precise category collection page, verified published via Shopify MCP before build (ToolUp v4 lesson: never point a category ad group at the full catalog). Store profile is a stub — public site domain, URL patterns, free-shipping verbiage all must be verified live at build time and backfilled into `STORE_PROFILES.md`.

### Ad group plan (~20 groups, phrase + exact only)

Tier 1 — isolated, pausable guardrail group:

| # | Ad group | Seed keywords (top Ahrefs vol/mo, US) |
|---|---|---|
| 1 | Brand - Bare | milwaukee tools (179k), milwaukee tool (30k), milwaukee power tools (7.1k), tools sale/deals/on sale (5.9k combined), near me (3.3k), who sells / where to buy (1.9k), store (350) |

Tier 2 — brand + category groups (each -> its own collection URL):

| # | Ad group | Anchor keywords (vol/mo) | Note |
|---|---|---|---|
| 2 | PACKOUT - Boxes and Storage | milwaukee packout (105k), tool box (5.7k), organizer (6.6k), drawers (4.9k) | largest cluster in the account's niche |
| 3 | PACKOUT - Accessories | backpack (4.8k), radio (4.6k), cooler (3.1k), socket set (2k), mechanics tool set fold-in (~2.2k) | absorbs mechanics-set cluster per Ahrefs verdict |
| 4 | M18 Batteries and Chargers | m18 battery (16k+3.5k+2.2k variants), charger (1.4k), 12ah (1.4k), forge (700) | top Shopify seller category (5 of top 6) |
| 5 | Drills | drill (22k), hammer drill (11k), drill set (10k), right angle (2.3k) | mag/core drill only if stocked |
| 6 | Impact Wrenches and Drivers | impact wrench (10k), 1/2 (4.7k), 3/8 (1.6k), 3/4 (600), impact driver/impact drill (4k) | #6 Shopify seller is the 2967-20 |
| 7 | Ratchets | ratchet (13k), 3/8 (5.9k), electric (4.7k), insider (3.3k), set (2.9k), m12 (2.7k) | |
| 8 | Combo Kits | combo kit (3.3k), fuel combo kit (2.8k), m18 fuel (2.5k), m12 fuel 2-tool (2.1k) | #13 Shopify seller |
| 9 | Nailers | framing (8.1k), brad (5.9k), finish (2.8k), roofing (2.5k), pin (1.6k), palm (1.2k) | |
| 10 | Circular Saws | circular saw (9.2k), m18 variants (4.8k combined) | |
| 11 | Recip Saws / Sawzall | reciprocating saw (1.8k) + variants | follow-up Ahrefs pull on "milwaukee sawzall" before finalizing |
| 12 | Miter Saws | miter saw (6.8k), stand (1.2k) | |
| 13 | Table Saws | table saw (6.8k), stand (700) | |
| 14 | Blowers | blower (18k), leaf blower (17k), backpack (2k), compact (1.1k) | snow blower (5.9k) only if stocked — verify |
| 15 | Vacuums | vacuum (25k), m18 (5.8k), cordless (5.6k), backpack (3.7k) | exclude vacuum pump (HVAC) unless stocked; packout vacuum owned here, negatived in PACKOUT groups |
| 16 | Grinders | grinder (12k), die grinder (8.1k), angle grinder (5.6k) | exclude meat grinder |
| 17 | Tire Inflators | tire inflator (8.4k), m18 (3.4k combined), m12 (500) | #5 and #12 Shopify sellers |
| 18 | Lighting | flashlight (6.8k), rechargeable (900), m18 (600) | |
| 19 | Heat Guns | heat gun (6k), m18 (700), cordless (500) | |
| 20 | Laser Levels | laser level (11k), 360 (500), tripod (400) | head-term CPC soft ($0.10); weight to accessory terms |
| 21 | Outdoor - Trimmers and Mowers | string trimmer (4.9k+), lawn mower (8k), mower (3.4k), push (1.3k) | |
| 22 | Chainsaws | chainsaw (22k), top handle (1.4k), battery (1.3k) | **mandatory negative: "recall"** — ~19.7k/mo of the cluster is recall queries (see negatives) |

Dropped per Ahrefs economics: FORCE LOGIC/crimpers (~400/mo aggregate — the $55k crimper Shopify sales are part-number driven, stays with DSA), standalone mechanics-set group (merged into PACKOUT), inspection cameras (hold for v2 — small but $0.40-0.60 CPC trade buyer, revisit).

**Held out deliberately: Heated Gear.** The account already runs 3 dedicated ENABLED heated-gear campaigns. This campaign adds heated-gear negatives instead (see below) despite the 55k/mo cluster — that demand belongs to the existing campaigns.

### Negatives (campaign level)

- `recall` (chainsaw liability cluster, near-zero intent)
- careers, jobs, warranty, repair, parts, manual, serial number, register, who owns, who makes, where are ... made, logo, catalog
- home depot, lowes, harbor freight, ace hardware (competitor-retailer intent) — also candidates for account-level shared negatives
- red tool store, the red store (owned by `QT - Search - TM`)
- heated (owned by the Heated Gear campaigns)
- meat grinder, vacuum pump (unless stocked), snow blower (unless stocked)

### Cross-campaign interaction — deliberate deviation from ToolUp method

ToolUp added brand negatives to its DSA campaigns so the new Search campaigns would not compete with DSA. **Here that is not viable: 78% of the DSA campaign's queries contain "milwaukee" — negativing the brand would gut it.** Instead: rely on exact/phrase keyword priority over DSA (Google serves the keyword campaign when eligible), monitor the DSA search-terms report post-launch, and add specific category phrases as DSA negatives only if double-serving appears. Flagged for Adam's sign-off as a methodology deviation.

### Measurement framing (carried from ToolUp)

Judge as a **reallocation, blended** with the PMax/Shopping campaigns that currently absorb Milwaukee queries — not incremental in isolation. Capture a 90-day pre-launch baseline for `QT - PMax - Top IDs`, `AB | PMax - Authorized Bundles`, `QT - Shopping - Margin Bands`, and the DSA campaign before enabling.

## Step 3 — Copy, extensions, URLs (V3 draft, 2026-07-13)

Copy rules applied (per `ASSET_CREATION_SKILL.md`): sentence case, no em dashes, at least one <=15 char headline per RSA, varied lengths, one angle per headline, every headline standalone-combinable, no unproven superlatives, no price claims on MAP ("See Price In Cart") SKUs, every factual claim verified live 2026-07-12 (free ship $199 ground, 4.56/5 x 1,303 reviews, PACKOUT Builder). NO "authorized dealer" claim anywhere until Adam confirms the store may make it (not found on the live site).

### Shared asset pool (mixed into every RSA below, filling each to 15 headlines / 4 descriptions)

Shared headlines: `Red Tool Store` (14) | `Milwaukee tool superstore` (25) | `Free ground ship over $199` (26) | `Rated 4.6/5 by 1,300+ buyers` (28) | `Huge Milwaukee selection` (24) | `Deals on Milwaukee tools` (24) | `Order today` (11) | `Shop the full lineup` (20)

Shared descriptions: `Free ground shipping over $199. Huge in-stock Milwaukee selection with fast delivery.` | `Rated 4.6 out of 5 by more than 1,300 verified buyers. Shop Milwaukee with confidence.`

Campaign-level callouts (all 3 campaigns): `Free Ship Over $199` | `4.6/5 From 1,300+ Buyers` | `Huge Milwaukee Selection` | `Fast Order Fulfillment`

Structured snippet (header: Types), Campaign A: `Drills, Saws, Batteries, PACKOUT, Grinders, Nailers, Lighting`. Campaign B: `Batteries, Impact Wrenches, Combo Kits, Inflators, Lasers`.

Sitelinks (4, campaign level, handles pending the collection-map pull): PACKOUT Storage -> /collections/packout-storage | M18 Tools -> /collections/m18-tools | Batteries + Chargers -> (handle TBD) | Limited Time Deals -> (handle TBD).

### Campaign A per-ad-group uniques (headlines <=30 chars, descriptions <=90; keywords per the Step 2 tables; landing handles filled after the collection-map pull)

1. **Brand - Bare**: H: Milwaukee tools in stock / Shop Milwaukee tools / Milwaukee tools on sale / Every M18 and M12 tool / New Milwaukee releases / Milwaukee deals live now. D: "Shop the full Milwaukee lineup, M18 FUEL to PACKOUT. Free ground shipping over $199." / "Deep Milwaukee inventory with fast fulfillment and frequent limited time deals."
2. **PACKOUT - Boxes and Storage**: H: Milwaukee PACKOUT in stock / PACKOUT tool boxes / Build your PACKOUT system / PACKOUT organizers, drawers / PACKOUT rolling tool boxes / PACKOUT deals live now. D: "Boxes, organizers, drawers and rolling chests. Build a complete PACKOUT system today." / "Use the PACKOUT Builder to plan your stack, then ship it free on orders over $199."
3. **PACKOUT - Accessories**: H: PACKOUT backpacks, coolers / PACKOUT radio in stock / PACKOUT socket sets / Mechanics sets w/ PACKOUT / PACKOUT accessories. D: "Backpacks, coolers, radios and PACKOUT mechanics sets, all in stock and ready to ship." / "Complete your PACKOUT system with the accessories pros actually use on the job."
4. **M18 Batteries and Chargers**: H: M18 batteries in stock / Milwaukee M18 batteries / M18 FORGE HD12.0 here / XC5.0 and XC6.0 packs / M18 battery 2-packs / Six bay chargers in stock / M18 battery deals. D: "XC5.0, XC6.0, HIGH OUTPUT and FORGE packs plus rapid chargers, in stock right now." / "Real Milwaukee M18 batteries with fast shipping. Add to cart to see today's price."
5. **Drills**: H: Milwaukee drills in stock / M18 FUEL hammer drills / Drill and driver kits / Right angle drills / Milwaukee drill sets / M12 compact drills. D: "Hammer drills, drill/driver kits and right angle drills from M12 compact to M18 FUEL." / "Find the right Milwaukee drill for the job and ship it free on orders over $199."
6. **Impact Wrenches and Drivers**: H: Milwaukee impact wrenches / 2967-20 high torque / 1/2 in high torque impacts / 3/8 in mid torque in stock / M18 FUEL impact drivers. D: "From 3/8 in mid torque to the 2967-20 1/2 in high torque, in stock and ready to ship." / "M18 FUEL impact wrenches and drivers with the torque pros demand. Fast free ship $199+."
7. **Ratchets**: H: Milwaukee ratchets / M12 FUEL ratchets / 3/8 in electric ratchets / Insider extended ratchet / Cordless ratchet sets. D: "M12 electric ratchets, the Insider extended reach line and full ratchet kits in stock." / "The cordless ratchets automotive pros carry. Add to cart to see today's price."
8. **Combo Kits**: H: Milwaukee combo kits / M18 FUEL combo kits / 3697-27 7-tool kit / 2-tool to 7-tool kits / M12 FUEL combo kits / Kit up and save. D: "From 2-tool M12 sets to the 3697-27 M18 FUEL 7-tool kit. One box, a full lineup." / "Combo kits bundle the core Milwaukee tools pros reach for first. In stock now."
9. **Nailers**: H: Milwaukee nailers in stock / M18 FUEL framing nailers / Brad and finish nailers / Roofing nailers ready / Cordless pin nailers. D: "Framing, brad, finish, roofing and pin nailers, all cordless, all in stock." / "Skip the compressor. M18 FUEL nailers drive all day on a single battery."
10. **Circular Saws**: H: Milwaukee circular saws / M18 FUEL circular saws / Rear handle 7-1/4 in saws / Cordless circular saws. D: "M18 FUEL circular saws including rear handle 7-1/4 in models. In stock, ready to ship." / "Cut all day cordless. Free ground shipping on orders over $199."
11. **Recip Saws / SAWZALL**: H: Milwaukee SAWZALL saws / M18 FUEL SAWZALL / Cordless recip saws / HACKZALL one hand saws. D: "The original SAWZALL recip saw plus compact HACKZALL models, in stock now." / "Demo-ready M18 FUEL recip saws. Free ground shipping over $199." (keywords pending the sawzall Ahrefs pull)
12. **Miter Saws**: H: Milwaukee miter saws / M18 FUEL miter saws / Miter saws and stands / Cordless miter saws. D: "M18 FUEL miter saws and stands for the trim carpenter who moves site to site." / "Dial in your angles cordless. Add to cart to see today's price."
13. **Table Saws**: H: Milwaukee table saws / M18 FUEL table saws / 8-1/4 in jobsite table saw / Table saws and stands. D: "The M18 FUEL 8-1/4 in table saw cuts like corded without the cord." / "Jobsite table saws and stands in stock with fast free shipping over $199."
14. **Blowers**: H: Milwaukee blowers in stock / M18 FUEL leaf blowers / 0887-20 precision blower / Compact + backpack blowers. D: "Leaf blowers, the 0887-20 precision blower and backpack models, all cordless." / "Clear the site or the driveway. M18 blowers ship fast, free over $199."
15. **Vacuums**: H: Milwaukee vacuums / M18 wet/dry vacuums / Cordless shop vacs / Backpack vacuums / 0880-20 wet/dry vac. D: "Wet/dry, stick and backpack vacuums that run on the batteries you already own." / "Jobsite cleanup without the cord. In stock and ready to ship today."
16. **Grinders**: H: Milwaukee grinders / M18 FUEL angle grinders / Die grinders in stock / Cordless cutoff tools. D: "Angle grinders, die grinders and cutoff tools from M12 to M18 FUEL." / "Grind, cut and polish cordless. Free ground shipping over $199."
17. **Tire Inflators**: H: Milwaukee tire inflators / 2848-20 M18 inflator / M12 compact inflators / Cordless tire inflators. D: "The 2848-20 M18 inflator tops off truck tires in minutes, no compressor needed." / "M12 and M18 tire inflators in stock. Add to cart to see today's price."
18. **Lighting**: H: Milwaukee flashlights / M18 jobsite lighting / Rechargeable flashlights / Tower and area lights. D: "Flashlights, headlamps and jobsite area lights that share your M18 batteries." / "Light the whole site cordless. Fast shipping, free over $199."
19. **Heat Guns**: H: Milwaukee heat guns / M18 cordless heat guns / Compact heat gun ready. D: "Cordless M18 heat guns heat up in seconds for wrap, shrink and repair work." / "Skip the cord. Milwaukee heat guns in stock and ready to ship."
20. **Laser Levels**: H: Milwaukee laser levels / M12 green beam lasers / 360 plane laser kits / 3632-21 3-plane laser. D: "M12 green beam 360 lasers including the 3632-21 3-plane kit for full room layout." / "Layout-grade accuracy with batteries you already own. In stock now."
21. **Outdoor - Trimmers and Mowers**: H: Milwaukee string trimmers / M18 FUEL mowers / Cordless lawn care / Quik-Lok attachments. D: "M18 FUEL string trimmers and self-propelled mowers powered by the same batteries." / "Pro lawn care without gas. Free ground shipping on orders over $199."
22. **Chainsaws**: H: Milwaukee chainsaws / M18 FUEL chainsaws / Top handle chainsaws / Battery chainsaws ready. D: "M18 FUEL chainsaws from top handle to 16 in bar, no gas, no pull cord." / "Pro cutting power on battery. In stock with fast shipping." (campaign negative: recall)

### Campaign B per-family copy pattern (MAP-safe, product-page landings)

Every B ad group uses: 2 model-number headlines (`Milwaukee <model>`, bare `<model>` as the <=15 short) + 3-4 product-line headlines + `Add to cart for best price` (26) + `In stock, ships fast` (20) + shared pool. Descriptions: one product-specific + `Add to cart to see today's price. In stock with fast, tracked delivery.` (73). Family uniques:

- **M18 Batteries by SKU**: 48-11-1852 / 48-11-1862 / 48-11-1850 / 48-11-1813 FORGE. H uniques: `48-11-1852 XC5.0 2-pack`, `48-11-1813 FORGE HD12.0`, `M18 HIGH OUTPUT XC6.0`. D: "Genuine Milwaukee M18 packs: XC5.0, XC6.0 HIGH OUTPUT and FORGE HD12.0, in stock."
- **HOTSHOT Jump Starter 3841-20**: H: `3841-20 HOTSHOT`, `M18 HOTSHOT jump starter`, `Jump start from your M18`. D: "The M18 HOTSHOT jump starter boosts trucks and equipment off the batteries you own."
- **Impact Wrenches**: 2967-20, 2854-20. H: `2967-20 in stock`, `1/2 in high torque impact`, `2854-20 mid torque`. D: "The 2967-20 M18 FUEL 1/2 in high torque impact with friction ring, ready to ship."
- **PACKOUT SKUs**: 48-22-8427, 48-22-9495. H: `48-22-8427 rolling box`, `366pc mechanics set`, `PACKOUT rolling tool box`. D: "From the 48-22-8427 rolling box to the 366pc master mechanics PACKOUT set."
- **Combo Kits**: 3697-27, 3697-22. H: `3697-27 7-tool kit`, `M18 FUEL 7-tool combo`. D: "The 3697-27 M18 FUEL 7-tool combo kit: the full trade loadout in one order."
- **Blowers**: 0887-20, 3017-20. H: `0887-20 precision blower`, `3017-20 FUEL blower`. D: "M18 blowers from the compact 0887-20 precision to the full-size 3017-20 FUEL."
- **Tire Inflators**: 2848-20. H: `2848-20 M18 inflator`, `M18 tire inflator`. D: "The 2848-20 M18 inflator: set the PSI, press run, done in minutes."
- **Lasers**: 3632-21. H: `3632-21 green laser kit`, `M12 3-plane 360 laser`. D: "The 3632-21 M12 green 360 3-plane laser kit for one-person full room layout."
- **Trade/Specialty**: 5150-20. H: `5150-20 conduit bender`, `M18 FUEL conduit bender`. D: "The 5150-20 M18 FUEL branch conduit bender saves shoulders and setup time."
- (Remaining distinct-SKU families from the roster follow the same pattern at build time.)

### Campaign C (Top Bundles) copy pattern

Offer-led, inventory-gated. H pool: `FREE tool with starter kit` (26) / `M18 starter kit deals` (21) / `Battery bundle, FREE extras` (27) / `48-59-1852B starter kit` (23) / `Buy the kit, get a FREE tool` (28) / `Bundle and save big` (19 — replace "big": `Bundle up and save` 18). D: "M18 starter kits with a FREE bare tool: inflator, blower, recip saw, router and more." / "Battery bundles with FREE extra packs. Limited time offers while inventory lasts." Landing: the specific bundle listing per ad group; RSAs updated as offers rotate (stock-sync mechanism governs enable/pause).

🛑 **Checkpoint 2 (copy + settings):** copy drafted above; awaiting (a) collection-map/landing verification pull (in progress), (b) Adam's read of the copy + the no-dealer-claim rule + MAP language, (c) final budgets/tROAS (Adam sets at publish).

## Outstanding items

1. ~~🛑 Checkpoint 1~~ ✅ CONFIRMED 2026-07-12 (full scope; B = distinct SKUs; C = bundles optional; PACKOUT diagnosed)
2. ~~Verify domain + URL patterns~~ ✅ DONE 2026-07-12: **redtoolstore.com** (apex canonical), "Free Ground Shipping Over $199", `/collections/<slug>` taxonomy verified (m18-tools, packout-storage, impact-wrenches, mechanic-tool-sets...), `/products/<handle>`, business name "Red Tool Store", 4.56/5 x 1,303 reviews for copy. MAP quirk: "See Price In Cart" SKUs get no price claims. STORE_PROFILES.md backfilled. Still TBD: Merchant Center domain match, logo asset, per-ad-group collection handle verification at copy time.
3. Follow-up Ahrefs pull: "milwaukee sawzall" standalone volume
4. Catalog checks: snow blower, vacuum pump, mag/core drill, riding mower stocked?
5. Budget + tROAS confirmation ($200/day, 10.5)
6. 90-day PMax/Shopping/DSA baseline snapshot before enable
7. `get_google_ads_keyword_performance` failed twice on this account (MCP connection closed) — retry; no keyword-level QS data yet
8. Create `red-tool-store/` account folder (NOTES.md + STATE.md) + PPC_ADVISOR registry row

## Revision log

| Rev | Date | Author | Change |
|---|---|---|---|
| V1 | 2026-07-12 | Claude (Fable 5) | Initial draft from account audit + Ahrefs research (25 clusters) + Shopify 90d sales. Structure, ad group plan, negatives, methodology deviations documented. Awaiting Checkpoint 1. |
| V2 | 2026-07-12 | Claude (Fable 5) | Checkpoint 1 CONFIRMED by Adam: full category scope; added Campaign B (top-100 products, model-number ad groups) as the DSA-sunset replacement per Adam (skeptical of AI Max); PACKOUT post-mortem on `packout-search` launched, findings to shape the PACKOUT groups. Top-100 roster pull launched. |
| V3 | 2026-07-12 | Claude (Fable 5) | Per Adam: budgets/tROAS are best-guess drafts (he finalizes at publish); roster CSV permanently local-only (now gitignored); Campaign B restructured to standard distinct SKUs only; promotion bundles carved into optional Campaign C `QT - Search - Milwaukee Top Bundles` (inventory-gated); stock-out maintenance mechanism designed (control center stock-sync job, propose -> approve -> commit, ad group names carry model numbers). |
| V2.1 | 2026-07-12 | Claude (Fable 5) | PACKOUT post-mortem section added (failure = starved tROAS 10x silo + single ad group + 63% broad-match waste; category itself proven: core terms ~30x, DSA packout routing ~36x). Campaign B designed from the roster: ~15 family ad groups, exact+phrase model keywords incl. bare SKUs, tROAS 12 / $150 day draft, Starter-Kit-bundle franchise group first, heated SKUs held out, OOS exclusions. |
