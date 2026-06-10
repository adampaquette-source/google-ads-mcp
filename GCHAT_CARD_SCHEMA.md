# Google Chat Card Schema and Formatting Reference

Living reference for all Google Chat notification work in this project.
Read this before writing or modifying any function that produces a Chat message.
Update this file when a formatting preference is discovered or changed.

---

## When to read this file

- Any session touching `ads_mcp/notify.py`
- Any session modifying digest output (DIGEST_SKILL.md Step 5 or Step 6)
- Any session adding a new Chat notification (tROAS audit, budget audit, new tools)

---

## Current card implementation

Entry point: `ads_mcp/notify.py`

| Function | Webhook env var | Format | Used by |
|---|---|---|---|
| `post_digest_card_to_google_chat` | `GOOGLE_CHAT_WEBHOOK_URL` | cardsV2 | Daily + weekly digest |
| `post_budget_audit_card` | `GOOGLE_ADS_TROAS_WEBHOOK_URL` | cardsV2 | Budget audit (proposals ready) |
| `post_budget_commit_card` | `GOOGLE_ADS_TROAS_WEBHOOK_URL` | cardsV2 | Budget commit result |
| `post_troas_audit_card` | `GOOGLE_ADS_TROAS_WEBHOOK_URL` | cardsV2 | tROAS audit (proposals ready) |
| `post_troas_commit_card` | `GOOGLE_ADS_TROAS_WEBHOOK_URL` | cardsV2 | tROAS commit result |
| `post_troas_rollback_card` | `GOOGLE_ADS_TROAS_WEBHOOK_URL` | cardsV2 | tROAS rollback alert |
| `post_to_troas_chat` | `GOOGLE_ADS_TROAS_WEBHOOK_URL` | plain text | tROAS reminder nudges only |

MCP tool: `post_digest_card_to_google_chat(card_data: dict)` in `mcp_server/server.py`.
Input schema: `DigestCardData` TypedDict in `notify.py`.

---

## cardsV2 payload structure

```json
{
  "cardsV2": [
    {
      "cardId": "string",
      "card": {
        "header": { "title": "...", "subtitle": "...", "imageUrl": "...", "imageType": "CIRCLE|SQUARE" },
        "sections": [ ... ],
        "fixedFooter": {
          "primaryButton": { "text": "...", "onClick": { "openLink": { "url": "..." } } },
          "secondaryButton": { ... }
        }
      }
    }
  ]
}
```

### Section object

```json
{
  "header": "SECTION TITLE",
  "collapsible": false,
  "widgets": [ ... ]
}
```

Sections with a `header` string automatically get a visual divider above them.
`hasDivider` is NOT supported via incoming webhooks -- omit it entirely.

---

## Widget reference

### `textParagraph`

```json
{ "textParagraph": { "text": "<b>label:</b>  value<br>next line" } }
```

Supported HTML: `<b>`, `<i>`, `<u>`, `<s>`, `<br>`, `<a href="url">`, `<font color="...">`

`<font color>` accepts hex (`#1a7f4b`) or names: `red`, `green`, `blue`, `orange`, `teal`, `yellow`, `purple`, `cyan`, `grey`.

### `decoratedText`

Best widget for labelled metrics. All fields optional except `text`.

```json
{
  "decoratedText": {
    "topLabel": "small grey label above",
    "text": "<b>main value</b>",
    "bottomLabel": "small grey label below",
    "wrapText": true,
    "startIcon": { "knownIcon": "DOLLAR" },
    "button": { ... }
  }
}
```

### `buttonList`

```json
{
  "buttonList": {
    "buttons": [
      {
        "text": "Label",
        "onClick": { "openLink": { "url": "https://..." } },
        "color": { "red": 0.18, "green": 0.46, "blue": 0.83, "alpha": 1.0 }
      }
    ]
  }
}
```

Buttons without `color` render with a border (outlined style). Blue fill hex: `{"red": 0.18, "green": 0.46, "blue": 0.83, "alpha": 1.0}`.

### `divider`

Thin horizontal line. Use between widgets within a section for visual separation.

```json
{ "divider": {} }
```

### `image`

```json
{ "image": { "imageUrl": "https://...", "altText": "description", "onClick": { "openLink": { "url": "..." } } } }
```

### `columns`

Two-column side-by-side layout. Each column holds its own widget list.

```json
{
  "columns": {
    "columnItems": [
      { "horizontalSizeStyle": "FILL_AVAILABLE_SPACE", "widgets": [ ... ] },
      { "horizontalSizeStyle": "FILL_AVAILABLE_SPACE", "widgets": [ ... ] }
    ]
  }
}
```

---

## Icon reference

### `knownIcon` (small set, always available)

`STAR`, `BOOKMARK`, `CLOCK`, `DOLLAR`, `EMAIL`, `PERSON`, `PHONE`, `STORE`,
`SHOPPING_CART`, `DESCRIPTION`, `MAP_PIN`, `TICKET`, `TRAIN`, `BUS`, `CAR`,
`HOTEL`, `RESTAURANT_ICON`, `INVITE`, `MEMBERSHIP`, `MULTIPLE_PEOPLE`, `OFFER`

### `materialIcon` (full Material Design set)

```json
{ "materialIcon": { "name": "trending_up", "fill": true, "weight": 400 } }
```

Useful icon names for this project:

| Icon name | Use |
|---|---|
| `trending_up` | Improving trend |
| `trending_down` | Worsening trend |
| `trending_flat` | Stable trend |
| `check_circle` | All clear / Strong status |
| `warning` | Watch status / pacing alerts |
| `error` | Poor status / zero conversions |
| `info` | Informational note |
| `attach_money` | Spend / budget |
| `percent` | MER / Ad Spend % |
| `campaign` | Campaign-level alert |
| `flag` | Flagged item |
| `notifications` | Alert count |

---

## Token palette

Standard colors and HTML helpers used by `_build_digest_card` in `notify.py`.
All token functions are defined in `notify.py`. Do not hardcode hex values elsewhere.

### Status colors

| Token | Hex | Meaning |
|---|---|---|
| `_COLOR_GREEN` | `#1a7f4b` | Strong -- at or above target |
| `_COLOR_BLUE` | `#1d6fa4` | Good -- acceptable |
| `_COLOR_AMBER` | `#d97706` | Watch -- needs monitoring |
| `_COLOR_RED` | `#dc2626` | Poor / critical |
| `_COLOR_GREY` | `#6b7280` | Neutral / No Spend |

### Token functions (proposed -- see upgrade plan below)

```python
tok_status(status: str) -> str
# Returns color-coded bold status label
# "Strong" -> <font color="#1a7f4b"><b>Strong</b></font>

tok_direction(direction: str) -> str
# Returns color-coded UNDER/OVER label
# "UNDER" -> red bold, "OVER" -> amber bold

tok_drift(pct: float) -> str
# Returns color-coded drift percentage
# -22.0 -> <font color="#dc2626">-22%</font>
# +15.0 -> <font color="#d97706">+15%</font>

tok_currency(amount: float) -> str
# Returns plain formatted currency (no color)
# 12300.0 -> $12,300
```

---

## DigestCardData schema (current)

```python
class DigestCardData(TypedDict):
    date_str: str               # "May 21, 2026"
    date_range_label: str       # "Last 7 Days" | "Last 30 Days"

    # Structured metric fields (card builder formats these)
    portfolio_mer: float        # 6.2
    portfolio_mer_status: str   # "Strong" | "Good" | "Watch" | "Poor" | "No Sales"
    portfolio_trend: str        # "Improving" | "Worsening" | "Stable" | "No Prior Data"
    portfolio_mer_delta: float  # pp change vs prior; negative = improving; 0 if no prior
    total_net_sales: float
    total_cost: float
    portfolio_roas: float
    total_conversions: float
    total_clicks: int

    # HTML-formatted section bodies (Claude writes these)
    mer_by_store_html: str
    alerts_html: str
    priority_actions_html: str
    strategic_summary_html: str  # empty string for daily

    # Links -- empty string if unavailable
    dashboard_url: str
    mer_tab_url: str
```

The structured fields at the top are rendered by the card builder with consistent
formatting. The `_html` fields are written by Claude using `<b>`, `<br>`, `<font color>`.

---

## tROAS card schemas

### `TroasAuditCardData`

```python
class TroasAuditCardData(TypedDict):
    date_str: str           # "May 21, 2026"
    total_proposals: int
    tighten_count: int
    loosen_count: int
    accounts_count: int
    top_proposals: list[TroasProposalItem]  # up to 10
    proposals_url: str

class TroasProposalItem(TypedDict):
    account: str
    campaign: str
    direction: str      # "TIGHTEN" | "LOOSEN"
    current_pct: float
    proposed_pct: float
    drift_pct: float    # negative = actual below target
```

### `TroasCommitCardData`

```python
class TroasCommitCardData(TypedDict):
    date_str: str
    applied: int
    errors: int
    skipped: int
    applied_items: list[TroasCommitItem]
    error_items: list[TroasErrorItem]
    proposals_url: str

class TroasCommitItem(TypedDict):
    campaign_name: str
    account_name: str
    old_pct: float
    new_pct: float
    change_pp: int
    direction: str   # "UP" (TIGHTEN) | "DOWN" (LOOSEN)

class TroasErrorItem(TypedDict):
    campaign_name: str
    error: str
```

### `TroasRollbackCardData`

```python
class TroasRollbackCardData(TypedDict):
    date_str: str
    flags: list[TroasRollbackItem]
    proposals_url: str

class TroasRollbackItem(TypedDict):
    account_name: str
    campaign_name: str
    direction: str           # "TIGHTEN" | "LOOSEN" (what was applied)
    old_roas_pct: float
    new_roas_pct: float
    current_72h_convs: float
    prior_72h_convs: float
    drop_pct: float
```

---

## v1 baseline screenshot review

*Captured May 21, 2026. Reference point for upgrade decisions.*

**What works:**
- Card header (title + subtitle) is clean and immediately readable
- `decoratedText` widget for AD SPEND % communicates status and trend at a glance
- Section headers (AD SPEND % BY STORE, ALERTS, PRIORITY ACTIONS) give clear structure
- Button row (Ads Dashboard + MER Report) is exactly right -- blue fill on primary, outlined on secondary

**What is unpleasant to read (problems to fix):**

1. **ALERTS is one monolithic text block.** The four subsections (tROAS, Zero Conversions, Budget Pacing, Disapprovals) are separated only by `<br><br>` gaps. They carry no visual weight difference from each other. The eye has no anchor when scanning.

2. **Status words have no color.** "Strong", "Watch", "UNDER", "OVER" are plain white text. A "Watch" alert looks identical to an "All clear." The key signal the reader needs to grab first is buried in undifferentiated type.

3. **Priority actions run together.** Items 1, 2, 3 are indistinguishable at a glance. A numbered wall of text requires reading from the top rather than scanning.

---

## Proposed upgrade: token-driven structural rewrite

This is the next planned improvement to the card format. Implement when time allows.

### Core change: split alerts into separate widgets

Instead of `alerts_html` as one HTML string, pass structured alert data. The builder renders each alert type as its own widget with a `divider` between them. This is the single highest-impact change.

```
Current:     [one textParagraph widget -- 4 alert types squashed together]

Proposed:    [textParagraph: tROAS]
             [divider]
             [textParagraph: Zero Conversions]
             [divider]
             [textParagraph: Budget Pacing]
             [divider]
             [textParagraph: Disapprovals]
```

### Core change: move to structured alert fields

Replace `alerts_html: str` with typed per-alert fields. The builder applies token colors.

```python
# Replace alerts_html with these four fields:
troas_alerts: list[dict]      # [{account, campaign, actual, target, drift_pct, status}]
zero_conv_accounts: list[str] # ["Account ($X spend)"] or []
budget_pacing_note: str       # plain text note -- builder wraps it
budget_overpacing: list[str]  # ["Account: Campaign"] or []
disapproval_count: int
disapproval_accounts: list[str]  # [] if clean
```

The builder then calls `tok_status()`, `tok_direction()`, `tok_drift()` to apply color
consistently without Claude needing to write any `<font>` tags.

### Core change: priority actions as a list

Replace `priority_actions_html: str` with `priority_actions: list[str]`.
The builder renders each item as a separate `textParagraph` with a numbered bold prefix
and spacing, or as `decoratedText` items for even cleaner layout.

```python
priority_actions: list[str]  # plain text strings, builder handles styling
```

### Core change: MER by store as structured data

Replace `mer_by_store_html: str` with `mer_stores: list[dict]`.
Builder applies `tok_status()` colors on each store's status word.

```python
mer_stores: list[dict]  # [{name, mer, status, spend, net_sales}]
```

### Files to update when implementing

Per the change routing table in CLAUDE.md: `ads_mcp/notify.py` + `mcp_server/server.py` + `DIGEST_SKILL.md` (Step 5) + this file.

---

## Formatting preferences log

Record preferences here when discovered. Include the date and context.

| Date | Preference | Context |
|---|---|---|
| 2026-05-21 | Use `fixedFooter` for dashboard links rather than a button section widget | Better UX -- buttons always visible without scrolling. Not yet implemented. |
| 2026-05-21 | Alerts section should use per-type widgets with dividers, not one HTML blob | v1 screenshot review -- subsections visually merged |
| 2026-05-21 | Status words (Strong, Watch, Poor, UNDER, OVER) must be color-coded | v1 screenshot review -- no visual weight on key signals |
