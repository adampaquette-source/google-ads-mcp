# Pro Work Supply - Stage 1 Shopping - BUILD SPEC

| Field | Value |
|---|---|
| Account | Pro Work Supply (`1532947017`), MCC login `7404361064` |
| Store | `wood-shop-outlet` / proworksupply.com (100% 3M) |
| Status | **DRAFT PROPOSAL - nothing created or pushed. Build only on Adam's go.** |
| Date | 2026-06-17 |
| Governing decisions | D5 (Max Conversions), D6 (Standard Shopping), D8/D9/D10/D13/D14 (feed rules), D17 (pause PMax-A), D20 (Shopping only), D21 ($25 -> $40 budget ramp) |

This is the exact, executable Stage 1 build. It is Shopping-only (D20). Search and tROAS come in Stage 2. Read `STAGE1_PROPOSAL.md` for the why, `NOTES.md` for durable account facts, `DECISIONS.md` for the decision log.

---

## Hard rules (non-negotiable)
- **Create the campaign PAUSED.** Adam enables it manually after review.
- **No direct writes.** This spec is the proposal; build it through the Google Ads UI / Editor (human-in-the-loop) or a propose/commit tool. See "Execution path" at the bottom.
- **No account change until Adam says go.**

---

## Pre-flight (confirm before building)
1. **Merchant Center link.** Confirm the Google Ads account is linked to the Merchant Center account that carries the wood-shop-outlet feed, and that the roster SKUs are approved (not disapproved) in that feed.
2. **Conversion action.** Primary conversion = "Purchase". Confirmed firing (the $145.20 Ads conversion matched a real Shopify order). A glance at Goals > Conversions to confirm it is set Primary and imports all purchases is worthwhile but not a blocker.
3. **Geo / language.** Spec assumes **United States** and **English** (US demand, USD pricing, US Ahrefs data). Confirm no other geos are wanted.
4. **Feed match key in DataFeedWatch.** The roster and lookup CSV are keyed by **Shopify SKU**. Confirm DFW can match the lookup table on the SKU field (or tell me whether it keys on `id` / `mpn` so the CSV column maps cleanly).

---

## Step 0 - Pause the old campaign (D17)
- Pause **`PMax-A - ALL SKUS`** (campaign_id `23702140220`), the only ENABLED campaign. Rationale: PMax outranks Standard Shopping for the same products whenever both are eligible, so it must be off or it starves the new campaign.
- Verify the other 6 campaigns stay PAUSED (they already are): Sales-Shopping-Bottom/Mid/Top-Funnel, PMax-B Tapes, PMax-C PPE, PMax-01 Abrasives.

---

## Step 1 - Feed prep: tag the roster in DataFeedWatch (per D15)
Apply a custom label to **exactly the 60 SKUs in Step 5** so the campaign can be gated to them. A custom label is required because a brand or product_type filter cannot isolate these 60 from the other ~9,200 SKUs (the whole store is 3M).

- **Attribute:** `custom_label_2 = pws_stage1_3m` (DFW field chosen 2026-06-19; _0/_1 reserved for other feed uses). The Step 2 inventory gate must use index 2 to match.
- **Do it IN DataFeedWatch**, the source of truth that feeds Merchant Center. Setting the label via the Shopify Google app or a Merchant Center supplemental feed would be overwritten by DFW's output feed.
- **Method (LIVE 2026-06-19): Google Sheet lookup table.** Sheet `1F8uQYzjLg3GK3ZDG6Xq5l6KpsyiNXy9LJvoRbZ20OHs`, tab **PWS_Stage1**, columns `sku, custom_label_2`, seeded with the 60 SKUs via `update_dfw_lookup_table`. DFW maps `custom_label_2` with "Use lookup table" on `sku` + "Only IF sku is in list" + ELSE leave empty. **The sheet must be shared Anyone-with-link = Viewer** for DFW to read it (and Editor to the service account for the MCP to write). `pws_stage1_3m_lookup.csv` in this folder mirrors the sheet.
- **Rule alternative:** in DFW, `IF sku is any of [the 60 values] THEN custom_label_0 = pws_stage1_3m`.
- Backorder / out-of-stock roster items stay labeled (D10) - do not gate to in-stock only.
- **Exclusions to keep unlabeled:** the two DRAFT Speedglas helmets (837170, 835548) until Adam publishes them; the two sub-$10 eye singles (837129, 837254) per D14.

---

## Step 2 - Standard Shopping campaign settings

| Setting | Value |
|---|---|
| Campaign type | Shopping -> **Standard Shopping** (NOT Performance Max, NOT Smart Shopping) |
| Campaign name | `PWS | Shopping | Stage 1 Learning (3M Core)` |
| Merchant Center | the wood-shop-outlet MC account (confirm in pre-flight) |
| Country of sale | United States |
| **Inventory filter** | **`custom_label_2 = pws_stage1_3m`** (only advertise products that match; propose with `custom_label_index: 2`) |
| **Bidding strategy** | **Maximize Conversions** (no target CPA) |
| **Daily budget** | **$25.00** to start; raise to **$40.00** per the D21 trigger below |
| Campaign priority | Low |
| Networks | Google Search Network: Yes (Shopping ads serve on Search + the Shopping tab). Search partners: Yes (cheap incremental reach; can be turned off if we want pure Google data). |
| Local inventory ads | Off |
| Locations | United States |
| Languages | English |
| Devices | All (default) |
| Ad schedule | All day |
| Start / end date | Start on Adam's enable; no end date (manual evaluation at 60 to 90 days) |
| **Status on creation** | **PAUSED** |

---

## Step 3 - Ad group and listing group
- **One Product Shopping ad group:** `3M Core Roster`.
- **Listing group:** single node = **All products** (which, given the campaign inventory filter, resolves to only the 60 labeled SKUs). Do not subdivide in Stage 1: Maximize Conversions automates bids, so subdividing only adds noise. We can subdivide by group for reporting in Stage 2.

---

## Step 4 - Launch checklist
1. Campaign built to the settings above, **PAUSED**.
2. Inventory filter confirms a product count of ~60 (matches the roster). If it shows thousands, the label did not apply - fix the feed before enabling.
3. Budget = $25.00/day. Bidding = Maximize Conversions, no target.
4. PMax-A confirmed paused (Step 0).
5. Hand to Adam to enable.

---

## Step 5 - The roster (60 SKUs, the include list)
Prices are the listed price (case price where the title says `(N Pack)`, per the each-vs-case rule). "BO" = ACTIVE but out of stock, advertised on backorder (D10/D13).

### A. Full Face Respirators (7)
835470, 837168, 835531, 835533, 835535, 238083, 238084

### B. Hearing / Peltor (8)
837256, 837257, 837258, 844673, 844667, 844676, 844681, 844773

### C. Hard Hats / SecureFit Helmets (18)
835478, 837121, 837126, 837255, 439384, 439388, 439390, 439391, 439392, 439398, 439399, 439400, 439401, 439402, 439406, 439407, 439409, 439416

### D. Welding / Speedglas (6 now; +2 when DRAFTs publish)
In stock: 835801, 835523. Backorder (BO): 850212, 849985, 850211, 850014.
Pending publish (NOT labeled yet): 837170 ($428), 835548 ($925).

### E. Cubitron II Abrasives (6)
835459, 835462, 835465, 835484, 835526, 835586

### F. Disposable Respirators (9)
23280, 23288, 23376, 23287, 23260, 379740, 23293, 23372, 837169

### G. Fall Protection (5; thin stock, treat as BO)
839704, 839703, 839705, 839758, 837125

### H. Eye Protection (1; multipack only)
840206
(Excluded by D14: 837129 $8.36, 837254 $2.13.)

Full titles, prices, and inventory are in `STAGE1_PROPOSAL.md` Stage 1 roster.

---

## Monitoring and gates (post-launch)
- **Budget ramp (D21):** start $25/day. **Raise to $40/day** once early conversions appear (non-zero CVR with a non-catastrophic cost-per-conversion), typically within the first 1 to 2 weeks.
- **Store-readiness watch item:** if 2 to 3 weeks at $25/day produce ~0 conversions, the storefront is the bottleneck, not the ads. Pause and do store-readiness / CRO work (trust, pricing, checkout friction, product pages) before scaling. Shopify shows only 15 sales / $1,422.80 across all channels last year, so this is a real risk, not a formality.
- **Learning gate:** Maximize Conversions needs ~15 to 30 conversions / 30 days to exit learning. Do not change the bid strategy mid-learning (it resets the clock).
- **Stage 2 trigger (D16, D19):** at ~30 conversions / 30 days, switch Shopping to Target ROAS (~400%, stepping toward the ~800% goal), introduce the 3M-category Search campaign (D18), and test a PMax fed by proven winners.

---

## Execution path (built 2026-06-19)
The MCP now has a Standard Shopping propose/commit flow, so I build this campaign directly:
- `propose_google_ads_standard_shopping_campaign(customer_id, config)` -- validates and stores a proposal, NO account change. Config carries the budget, merchant_id, `custom_label_value = pws_stage1_3m` with `custom_label_index = 2`, geo/language, and `pause_campaign_ids = ["23702140220"]` (PMax-A, D17).
- `get_google_ads_standard_shopping_proposal(proposal_id)` -- review the stored proposal.
- `commit_google_ads_standard_shopping_campaign(proposal_id)` -- ONE atomic mutate: pause PMax-A, create budget + SHOPPING campaign (Maximize Conversions) + ad group + product ad + listing-group tree gating to the custom_label. Everything PAUSED. Writes `audit.db`. This is the only account-affecting step, gated on Adam's approval + pre-flight.

Notes: the new tools load only after a Claude Code session restart (MCP servers attach at startup). The mutate builder was validated offline against the live client (op order, enums, listing tree) on 2026-06-19; first real run is the PWS commit. The Google Ads UI / Editor remains a fallback.

## Outstanding items / flags for Adam
1. Confirm the 4 pre-flight items (MC link, conversion action primary, geo/language, feed match key).
2. In DataFeedWatch, apply `custom_label_0 = pws_stage1_3m` to the 60 SKUs (upload `pws_stage1_3m_lookup.csv` as a lookup table, or use the rule alternative).
3. Optional merchandising: publish the 2 DRAFT Speedglas helmets (837170, 835548) to add them to the roster.
4. Tell me which execution path you want (UI/Editor now, or build the MCP tool).
