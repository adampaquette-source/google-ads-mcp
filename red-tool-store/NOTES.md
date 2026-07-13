# Red Tool Store: Account Notes

Durable facts and standing rules. Update when a fact changes. For current working state see `STATE.md`.

Last updated: 2026-07-12.

Status: **ACTIVE, Tier 1.** Large healthy account taken on as an optimization project 2026-07-12 (Milwaukee brand Search buildout).

## Identifiers
| Thing | Value |
|---|---|
| Google Ads account | **Themilwaukeestore.com, customer_id `4033622485`** under MCC `7404361064` |
| Shopify store key | `the-milwaukee-store` (env slug `RTS_STORE`) |
| Aliases | Milwaukee Store, Red Tool Store, RTS |
| Public storefront | likely themilwaukeestore.com — UNVERIFIED, confirm before any final_url use |
| Merchant Center | TBD |

## Economics / performance (baseline 2026-07-12, LAST_30_DAYS)
- $114,981 spend, 3,349 conv, $1.18M conv value, ROAS 10.29 blended.
- Milwaukee brand slice: $60.4k spend, ROAS 8.87 — over half the account. Milwaukee effectively IS the store.
- Top sellers are M18 battery bundles (5 of top 6 by 90d net sales), then FUEL tools, combo kits, PACKOUT, tire inflators.

## Hard rules
- No account changes without Adam's explicit approval. Propose/commit only, campaigns created PAUSED.
- No em dashes in user-facing output.
- Use local `shopify-toolup` MCP only.

## Account structure quirks
- 12 ENABLED campaigns, 27 PAUSED legacy. Value concentrates in PMax (`QT - PMax - Top IDs`, `AB | PMax - Authorized Bundles`) + Shopping (`QT - Shopping - Margin Bands`).
- `QT - Search - TM` = store-trademark defense (ROAS 70+). Owns "red tool store" queries.
- `QT - Search - NB DSA Products` = DSA, $200/day, capped ~10% impression share; 78% of its queries contain "milwaukee"; model/part numbers are its best-converting cluster. Do NOT negative "milwaukee" on it.
- 3 small ENABLED Heated Gear campaigns own the heated-gear demand (55k/mo cluster) — exclude from other builds.
- Paused history: `Milwaukee Top/Mid/Bottom Level` Shopping tiers, `packout-search`, `RTS Part Number Search`, `DSA Google Build` — prior Milwaukee structures tried and abandoned, reasons unknown (ask Adam).

## Known gaps / data we do not have
- `STORE_PROFILES.md` RTS section is a stub: domain, URL patterns, free-shipping verbiage, naming convention, logo asset all TBD — verify live at build time and backfill.
- `get_google_ads_keyword_performance` errored twice on this account (MCP connection closed) — no keyword-level QS data yet.
- Why the prior Milwaukee-specific campaigns were paused.

## Decision log
See `campaign_assets/rts-milwaukee-brand-search/PROPOSAL.md` for the active build's checkpoints.
