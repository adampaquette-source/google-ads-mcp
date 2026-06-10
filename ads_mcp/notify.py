"""Notification delivery: Google Chat incoming webhook."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Shared result type
# ---------------------------------------------------------------------------

class PostResult(TypedDict):
    status: str
    message_length: int


# ---------------------------------------------------------------------------
# Color token palette
# ---------------------------------------------------------------------------

_COLOR_GREEN = "#1a7f4b"   # Strong -- at or above target
_COLOR_BLUE  = "#1d6fa4"   # Good -- acceptable
_COLOR_AMBER = "#d97706"   # Watch / OVER -- caution
_COLOR_RED   = "#dc2626"   # Poor / UNDER / critical
_COLOR_GREY  = "#6b7280"   # Neutral / No Spend

_STATUS_COLORS: dict[str, str] = {
    "Strong":   _COLOR_GREEN,
    "Good":     _COLOR_BLUE,
    "Watch":    _COLOR_AMBER,
    "Poor":     _COLOR_RED,
    "No Sales": _COLOR_RED,
    "No Spend": _COLOR_GREY,
}

_TREND_ICONS: dict[str, dict] = {
    "Improving":    {"materialIcon": {"name": "trending_up",   "fill": True}},
    "Worsening":    {"materialIcon": {"name": "trending_down", "fill": True}},
    "Stable":       {"materialIcon": {"name": "trending_flat", "fill": True}},
    "No Prior Data": {"knownIcon": "DOLLAR"},
}


def tok_status(status: str) -> str:
    """Color-coded bold status label: Strong, Good, Watch, Poor, No Sales, No Spend."""
    color = _STATUS_COLORS.get(status, _COLOR_GREY)
    return f'<font color="{color}"><b>{status}</b></font>'


def tok_direction(direction: str) -> str:
    """Color-coded bold UNDER (red) or OVER (amber) label."""
    color = _COLOR_RED if direction == "UNDER" else _COLOR_AMBER
    return f'<font color="{color}"><b>{direction}</b></font>'


def tok_drift(pct: float) -> str:
    """Color-coded drift percentage: negative = red, positive = amber."""
    color = _COLOR_RED if pct < 0 else _COLOR_AMBER
    sign = "+" if pct > 0 else ""
    return f'<font color="{color}">{sign}{pct:.0f}%</font>'


def _fmt_currency(amount: float) -> str:
    return f"${amount:,.0f}"


# ---------------------------------------------------------------------------
# DigestCardData schema
# ---------------------------------------------------------------------------

class TroasAlertItem(TypedDict):
    account: str
    campaign: str
    actual_roas: float
    target_roas: float
    drift_pct: float    # negative = actual below target (UNDER)
    status: str         # "UNDER" | "OVER"


class ZeroConvItem(TypedDict):
    account: str
    spend: float


class BudgetOverpaceItem(TypedDict):
    account: str
    campaign: str


class MerStoreItem(TypedDict):
    name: str
    mer: float
    status: str     # "Strong" | "Good" | "Watch" | "Poor" | "No Sales" | "No Spend"
    spend: float
    net_sales: float


class DigestCardData(TypedDict):
    """Structured data for a Google Chat cardsV2 digest message.

    All text fields are plain strings. The card builder applies color tokens and
    HTML formatting. No raw HTML needed in any field except strategic_summary_html.
    """

    date_str: str           # "May 21, 2026"
    date_range_label: str   # "Last 7 Days" | "Last 30 Days"

    # Headline portfolio metrics
    portfolio_mer: float
    portfolio_mer_status: str   # "Strong" | "Good" | "Watch" | "Poor" | "No Sales"
    portfolio_trend: str        # "Improving" | "Worsening" | "Stable" | "No Prior Data"
    portfolio_mer_delta: float  # pp change vs prior; negative = improving; 0 if no prior
    total_net_sales: float
    total_cost: float
    portfolio_roas: float
    total_conversions: float
    total_clicks: int

    # MER by store -- all non-zero-spend stores sorted by MER ascending
    mer_stores: list[MerStoreItem]

    # Alert data -- structured, builder applies token colors
    troas_alerts: list[TroasAlertItem]
    zero_conv_accounts: list[ZeroConvItem]
    budget_pacing_note: str             # plain text note; empty string if no underpacing
    budget_overpacing: list[BudgetOverpaceItem]
    disapproval_count: int
    disapproval_accounts: list[str]     # account names; empty list if clean

    # Priority actions -- plain text strings, builder numbers and styles them
    priority_actions: list[str]

    # Strategic summary (weekly only; empty string for daily)
    # This one field accepts HTML since it is free-form narrative
    strategic_summary_html: str

    # Links -- empty string if unavailable
    dashboard_url: str
    mer_tab_url: str


# ---------------------------------------------------------------------------
# Card section builders
# ---------------------------------------------------------------------------

def _build_portfolio_widgets(data: DigestCardData) -> list[dict]:
    trend = data["portfolio_trend"]
    delta = data["portfolio_mer_delta"]
    status = data["portfolio_mer_status"]

    mer_line = (
        f"<b>{data['portfolio_mer']:.1f}%</b>  {tok_status(status)}"
    )

    if trend == "No Prior Data":
        trend_label = "No prior period data"
    else:
        sign = "+" if delta > 0 else ""
        trend_label = f"{trend}  |  {sign}{delta:.1f}pp vs prior period"

    icon = _TREND_ICONS.get(trend, {"knownIcon": "DOLLAR"})

    return [
        {
            "decoratedText": {
                "topLabel": "AD SPEND %",
                "text": mer_line,
                "bottomLabel": trend_label,
                "wrapText": True,
                "startIcon": icon,
            }
        },
        {
            "textParagraph": {
                "text": (
                    f"Net Sales: <b>{_fmt_currency(data['total_net_sales'])}</b>"
                    f"    Ads Spend: <b>{_fmt_currency(data['total_cost'])}</b>"
                )
            }
        },
        {
            "textParagraph": {
                "text": (
                    f"ROAS: <b>{data['portfolio_roas']:.2f}</b>"
                    f"    Conversions: <b>{data['total_conversions']:,.0f}</b>"
                    f"    Clicks: <b>{data['total_clicks']:,}</b>"
                )
            }
        },
    ]


def _build_mer_widgets(stores: list[MerStoreItem]) -> list[dict]:
    active = [s for s in stores if s["status"] != "No Spend"]
    if not active:
        return [{"textParagraph": {"text": "No store data available."}}]

    healthy = sorted(
        [s for s in active if s["status"] in ("Strong", "Good")],
        key=lambda s: s["mer"],
    )
    attention = [s for s in active if s["status"] in ("Watch", "Poor", "No Sales")]

    lines: list[str] = []

    if healthy:
        top = healthy[:4]
        items = ",  ".join(
            f'{s["name"]} ({s["mer"]:.1f}% {tok_status(s["status"])})'
            for s in top
        )
        lines.append(f"<b>Best:</b>  {items}")

    for s in attention:
        if s["net_sales"] > 0:
            detail = (
                f'{s["mer"]:.1f}% {tok_status(s["status"])}'
                f",  {_fmt_currency(s['spend'])} spend / {_fmt_currency(s['net_sales'])} sales"
            )
        else:
            detail = f'{tok_status(s["status"])},  {_fmt_currency(s["spend"])} spend, no sales data'
        lines.append(f"<b>{s['name']}:</b>  {detail}")

    return [{"textParagraph": {"text": "<br>".join(lines)}}]


def _build_alert_widgets(data: DigestCardData) -> list[dict]:
    widgets: list[dict] = []

    # tROAS
    troas = data.get("troas_alerts") or []
    if troas:
        lines = [f"<b>tROAS ({len(troas)} flagged):</b>"]
        for a in troas:
            lines.append(
                f'{a["account"]}: {a["campaign"]}'
                f"  {a['actual_roas']:.2f} actual vs {a['target_roas']:.2f} target"
                f"  ({tok_drift(a['drift_pct'])} {tok_direction(a['status'])})"
            )
        widgets.append({"textParagraph": {"text": "<br>".join(lines)}})
    else:
        widgets.append({"textParagraph": {"text": "<b>tROAS:</b>  No alerts."}})

    widgets.append({"divider": {}})

    # Zero conversions
    zero = data.get("zero_conv_accounts") or []
    if zero:
        items = ",  ".join(
            f'{z["account"]} ({_fmt_currency(z["spend"])} spend)' for z in zero
        )
        widgets.append({"textParagraph": {"text": f"<b>Zero Conversions:</b>  {items}"}})
    else:
        widgets.append({"textParagraph": {"text": "<b>Zero Conversions:</b>  None"}})

    widgets.append({"divider": {}})

    # Budget pacing
    note = (data.get("budget_pacing_note") or "").strip()
    overpacing = data.get("budget_overpacing") or []
    pacing_lines: list[str] = []
    if note:
        pacing_lines.append(f"<b>Budget Pacing:</b>  {note}")
    if overpacing:
        for op in overpacing:
            flag = f'<font color="{_COLOR_AMBER}"><b>OVERPACING</b></font>'
            pacing_lines.append(f"{flag}  {op['account']}: {op['campaign']}")
    if not pacing_lines:
        pacing_lines.append("<b>Budget Pacing:</b>  No alerts.")
    widgets.append({"textParagraph": {"text": "<br>".join(pacing_lines)}})

    widgets.append({"divider": {}})

    # Disapprovals
    count = data.get("disapproval_count") or 0
    accounts = data.get("disapproval_accounts") or []
    if count == 0:
        widgets.append({"textParagraph": {"text": "<b>Disapprovals:</b>  None. All accounts clean."}})
    else:
        acct_str = ",  ".join(accounts) if accounts else f"{count} accounts"
        flag = f'<font color="{_COLOR_AMBER}"><b>{count}</b></font>'
        widgets.append({"textParagraph": {"text": f"<b>Disapprovals:</b>  {flag}  {acct_str}"}})

    return widgets


def _build_actions_widgets(actions: list[str]) -> list[dict]:
    if not actions:
        return []
    lines = [f"<b>{i + 1}.</b>  {action}" for i, action in enumerate(actions)]
    return [{"textParagraph": {"text": "<br>".join(lines)}}]


# ---------------------------------------------------------------------------
# Card assembler
# ---------------------------------------------------------------------------

def _build_digest_card(data: DigestCardData) -> dict:
    """Return a cardsV2 dict ready for JSON serialisation and POST to Chat webhook."""

    sections: list[dict] = []

    # Section 1: Portfolio overview (no header -- first section, no top divider)
    sections.append({"widgets": _build_portfolio_widgets(data)})

    # Section 2: AD SPEND % BY STORE
    mer_stores = data.get("mer_stores") or []
    if mer_stores:
        sections.append({
            "header": "AD SPEND % BY STORE",
            "widgets": _build_mer_widgets(mer_stores),
        })

    # Section 3: Alerts (split into 4 sub-widgets with dividers)
    sections.append({
        "header": "ALERTS",
        "widgets": _build_alert_widgets(data),
    })

    # Section 4: Priority actions
    priority_widgets = _build_actions_widgets(data.get("priority_actions") or [])
    if priority_widgets:
        sections.append({
            "header": "PRIORITY ACTIONS",
            "widgets": priority_widgets,
        })

    # Section 5: Strategic summary (weekly only)
    summary_html = (data.get("strategic_summary_html") or "").strip()
    if summary_html:
        sections.append({
            "header": "STRATEGIC SUMMARY",
            "widgets": [{"textParagraph": {"text": summary_html}}],
        })

    # Link buttons (omit section if no valid URLs)
    buttons: list[dict] = []
    dashboard_url = (data.get("dashboard_url") or "").strip()
    mer_url = (data.get("mer_tab_url") or "").strip()
    if dashboard_url:
        buttons.append({
            "text": "Ads Dashboard",
            "onClick": {"openLink": {"url": dashboard_url}},
            "color": {"red": 0.18, "green": 0.46, "blue": 0.83, "alpha": 1.0},
        })
    if mer_url:
        buttons.append({
            "text": "MER Report",
            "onClick": {"openLink": {"url": mer_url}},
        })
    if buttons:
        sections.append({"widgets": [{"buttonList": {"buttons": buttons}}]})

    return {
        "cardsV2": [
            {
                "cardId": "ads-digest",
                "card": {
                    "header": {
                        "title": "Google Ads + MER Digest",
                        "subtitle": f"{data['date_range_label']}  |  {data['date_str']}",
                    },
                    "sections": sections,
                },
            }
        ]
    }


# ---------------------------------------------------------------------------
# Public send functions
# ---------------------------------------------------------------------------

def post_to_google_chat(message: str) -> PostResult:
    """POST a plain-text message to the Google Chat space via incoming webhook.

    Reads GOOGLE_CHAT_WEBHOOK_URL from the environment. Raises EnvironmentError
    if the variable is missing or blank. Raises urllib.error.HTTPError on non-2xx
    responses. message should be under 4000 characters for Google Chat compatibility.
    """
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise EnvironmentError(
            "GOOGLE_CHAT_WEBHOOK_URL is not set. Add it to your .env file:\n"
            "GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=..."
        )

    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        resp.read()

    return PostResult(status="ok", message_length=len(message))


def post_digest_card_to_google_chat(data: DigestCardData) -> PostResult:
    """POST a structured digest as a Google Chat cardsV2 message via incoming webhook.

    Renders with named sections, token-colored status/direction/drift values,
    per-type alert widgets with dividers, and clickable link buttons.
    Reads GOOGLE_CHAT_WEBHOOK_URL from the environment.
    """
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise EnvironmentError(
            "GOOGLE_CHAT_WEBHOOK_URL is not set. Add it to your .env file:\n"
            "GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=..."
        )

    payload = json.dumps(_build_digest_card(data)).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        resp.read()

    return PostResult(status="ok", message_length=len(payload))


def post_to_troas_chat(message: str) -> PostResult:
    """POST a plain-text message to the tROAS Google Chat space via incoming webhook.

    Reads GOOGLE_ADS_TROAS_WEBHOOK_URL from the environment. Raises EnvironmentError
    if the variable is missing or blank. message should be under 4000 characters.
    """
    webhook_url = os.environ.get("GOOGLE_ADS_TROAS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise EnvironmentError(
            "GOOGLE_ADS_TROAS_WEBHOOK_URL is not set. Add it to your .env file:\n"
            "GOOGLE_ADS_TROAS_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=..."
        )

    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        resp.read()

    return PostResult(status="ok", message_length=len(message))


# ---------------------------------------------------------------------------
# tROAS card TypedDicts
# ---------------------------------------------------------------------------

class TroasProposalItem(TypedDict):
    account: str
    campaign: str
    direction: str      # "TIGHTEN" | "LOOSEN"
    current_pct: float  # display percentage, e.g. 1000.0
    proposed_pct: float
    drift_pct: float    # negative = actual below target (TIGHTEN)


class TroasAuditCardData(TypedDict):
    date_str: str          # "May 21, 2026"
    total_proposals: int
    tighten_count: int
    loosen_count: int
    accounts_count: int
    top_proposals: list[TroasProposalItem]   # up to 10 to display in card
    proposals_url: str


class TroasCommitItem(TypedDict):
    campaign_name: str
    account_name: str
    old_pct: float
    new_pct: float
    change_pp: int
    direction: str   # "UP" (TIGHTEN -- tROAS value raised) | "DOWN" (LOOSEN -- tROAS value lowered)


class TroasErrorItem(TypedDict):
    campaign_name: str
    error: str


class TroasCommitCardData(TypedDict):
    date_str: str
    applied: int
    errors: int
    skipped: int
    applied_items: list[TroasCommitItem]
    error_items: list[TroasErrorItem]
    proposals_url: str   # empty string if unavailable


class TroasRollbackItem(TypedDict):
    account_name: str
    campaign_name: str
    direction: str           # "TIGHTEN" | "LOOSEN" (what was applied)
    old_roas_pct: float
    new_roas_pct: float
    current_72h_convs: float
    prior_72h_convs: float
    drop_pct: float


class TroasRollbackCardData(TypedDict):
    date_str: str
    flags: list[TroasRollbackItem]
    proposals_url: str   # link to tROAS Log sheet; empty if unavailable


class BudgetAuditCardData(TypedDict):
    date_str: str
    constrained_count: int
    excess_count: int
    total_proposals: int
    accounts_count: int    # unique accounts across both proposal types
    proposals_url: str     # Budget Proposals tab URL


class BudgetCommitItem(TypedDict):
    campaign_name: str
    account_name: str
    old_budget: float
    new_budget: float
    change: float
    direction: str   # "UP" (increase) | "DOWN" (decrease)


class BudgetErrorItem(TypedDict):
    campaign_name: str
    error: str


class BudgetCommitCardData(TypedDict):
    date_str: str
    applied: int
    errors: int
    applied_items: list[BudgetCommitItem]
    error_items: list[BudgetErrorItem]
    log_url: str   # Budget Log tab URL; empty string if unavailable


# ---------------------------------------------------------------------------
# tROAS card builders
# ---------------------------------------------------------------------------

def _build_troas_audit_card(data: TroasAuditCardData) -> dict:
    sections: list[dict] = []

    total = data["total_proposals"]
    tighten = data["tighten_count"]
    loosen = data["loosen_count"]
    accounts = data["accounts_count"]

    icon = {"materialIcon": {"name": "campaign", "fill": True}}
    sections.append({
        "widgets": [{
            "decoratedText": {
                "topLabel": "NEW PROPOSALS",
                "text": f"<b>{total}</b> across {accounts} account{'s' if accounts != 1 else ''}",
                "bottomLabel": f"{tighten} TIGHTEN  |  {loosen} LOOSEN",
                "startIcon": icon,
            }
        }]
    })

    proposals = data.get("top_proposals") or []
    if proposals:
        lines: list[str] = []
        tighten_props = [p for p in proposals if p["direction"] == "TIGHTEN"]
        loosen_props  = [p for p in proposals if p["direction"] == "LOOSEN"]

        if tighten_props:
            lines.append(
                f'<font color="{_COLOR_RED}"><b>TIGHTEN ({len(tighten_props)}):</b></font>'
            )
            for p in tighten_props[:6]:
                lines.append(
                    f'{p["account"]}: {p["campaign"]}'
                    f'  {p["current_pct"]:.0f}% → {p["proposed_pct"]:.0f}%'
                    f'  drift {tok_drift(p["drift_pct"])}'
                )

        if loosen_props:
            if lines:
                lines.append("")
            lines.append(
                f'<font color="{_COLOR_GREEN}"><b>LOOSEN ({len(loosen_props)}):</b></font>'
            )
            for p in loosen_props[:4]:
                lines.append(
                    f'{p["account"]}: {p["campaign"]}'
                    f'  {p["current_pct"]:.0f}% → {p["proposed_pct"]:.0f}%'
                    f'  drift {tok_drift(p["drift_pct"])}'
                )

        sections.append({
            "header": "PROPOSALS",
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}],
        })

    url = (data.get("proposals_url") or "").strip()
    if url:
        sections.append({"widgets": [{"buttonList": {"buttons": [{
            "text": "Review Proposals",
            "onClick": {"openLink": {"url": url}},
            "color": {"red": 0.18, "green": 0.46, "blue": 0.83, "alpha": 1.0},
        }]}}]})

    return {
        "cardsV2": [{
            "cardId": "troas-audit",
            "card": {
                "header": {
                    "title": "tROAS Proposals Ready",
                    "subtitle": data["date_str"],
                },
                "sections": sections,
            },
        }]
    }


def _build_troas_commit_card(data: TroasCommitCardData) -> dict:
    sections: list[dict] = []

    applied = data["applied"]
    errors  = data["errors"]
    skipped = data["skipped"]

    if errors > 0 and applied == 0:
        status_icon = {"materialIcon": {"name": "error", "fill": True}}
    elif errors > 0:
        status_icon = {"materialIcon": {"name": "warning", "fill": True}}
    else:
        status_icon = {"materialIcon": {"name": "check_circle", "fill": True}}

    err_color = _COLOR_RED if errors > 0 else _COLOR_GREY
    summary = (
        f'<font color="{_COLOR_GREEN}"><b>Applied: {applied}</b></font>'
        f'    <font color="{err_color}"><b>Errors: {errors}</b></font>'
        f'    <font color="{_COLOR_GREY}">Skipped: {skipped}</font>'
    )
    sections.append({
        "widgets": [{
            "decoratedText": {
                "topLabel": "COMMIT RESULT",
                "text": summary,
                "wrapText": True,
                "startIcon": status_icon,
            }
        }]
    })

    applied_items = data.get("applied_items") or []
    if applied_items:
        lines: list[str] = []
        for item in applied_items:
            dir_color = _COLOR_AMBER if item["direction"] == "UP" else _COLOR_GREEN
            dir_label = f'<font color="{dir_color}"><b>{item["direction"]}</b></font>'
            lines.append(
                f'<b>{item["campaign_name"]}</b>  ({item["account_name"]})<br>'
                f'  {item["old_pct"]:.0f}% → {item["new_pct"]:.0f}%  '
                f'{dir_label} {item["change_pp"]}pp'
            )
        sections.append({
            "header": "APPLIED",
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}],
        })

    error_items = data.get("error_items") or []
    if error_items:
        lines = []
        for item in error_items:
            lines.append(
                f'<font color="{_COLOR_RED}"><b>{item["campaign_name"]}</b></font>'
                f'  {item["error"]}'
            )
        sections.append({
            "header": "ERRORS",
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}],
        })

    url = (data.get("proposals_url") or "").strip()
    if url:
        sections.append({"widgets": [{"buttonList": {"buttons": [{
            "text": "View tROAS Log",
            "onClick": {"openLink": {"url": url}},
        }]}}]})

    return {
        "cardsV2": [{
            "cardId": "troas-commit",
            "card": {
                "header": {
                    "title": "tROAS Commit",
                    "subtitle": data["date_str"],
                },
                "sections": sections,
            },
        }]
    }


def _build_troas_rollback_card(data: TroasRollbackCardData) -> dict:
    sections: list[dict] = []
    flags = data.get("flags") or []

    for flag in flags:
        direction_word = "tightened" if flag["direction"] == "TIGHTEN" else "loosened"
        drop = flag["drop_pct"]
        lines = [
            f'<b>{flag["account_name"]}: {flag["campaign_name"]}</b>',
            f'{direction_word}: {flag["old_roas_pct"]:.0f}% → {flag["new_roas_pct"]:.0f}%',
            f'Conversions (72h): <b>{flag["current_72h_convs"]:.1f}</b>'
            f'  (was {flag["prior_72h_convs"]:.1f})'
            f'  drop: <font color="{_COLOR_RED}"><b>-{drop:.0f}%</b></font>',
        ]
        sections.append({
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}]
        })

    sections.append({
        "header": "NEXT STEPS",
        "widgets": [{"textParagraph": {
            "text": (
                "Options: rollback to prior tROAS via <b>run_troas_audit + approve</b>"
                " | hold and monitor | proceed as normal"
            )
        }}],
    })

    url = (data.get("proposals_url") or "").strip()
    if url:
        sections.append({"widgets": [{"buttonList": {"buttons": [{
            "text": "View tROAS Log",
            "onClick": {"openLink": {"url": url}},
            "color": {"red": 0.18, "green": 0.46, "blue": 0.83, "alpha": 1.0},
        }]}}]})

    n = len(flags)
    return {
        "cardsV2": [{
            "cardId": "troas-rollback",
            "card": {
                "header": {
                    "title": "tROAS Rollback Alert",
                    "subtitle": f"{data['date_str']}  |  {n} campaign{'s' if n != 1 else ''} flagged",
                },
                "sections": sections,
            },
        }]
    }


# ---------------------------------------------------------------------------
# tROAS card send functions
# ---------------------------------------------------------------------------

def _post_to_troas_webhook(payload: bytes) -> PostResult:
    webhook_url = os.environ.get("GOOGLE_ADS_TROAS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise EnvironmentError(
            "GOOGLE_ADS_TROAS_WEBHOOK_URL is not set. Add it to your .env file:\n"
            "GOOGLE_ADS_TROAS_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=..."
        )
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        resp.read()
    return PostResult(status="ok", message_length=len(payload))


def post_troas_audit_card(data: TroasAuditCardData) -> PostResult:
    """POST a tROAS audit summary as a cardsV2 message to the tROAS Chat space."""
    return _post_to_troas_webhook(json.dumps(_build_troas_audit_card(data)).encode("utf-8"))


def post_troas_commit_card(data: TroasCommitCardData) -> PostResult:
    """POST a tROAS commit result as a cardsV2 message to the tROAS Chat space."""
    return _post_to_troas_webhook(json.dumps(_build_troas_commit_card(data)).encode("utf-8"))


def post_troas_rollback_card(data: TroasRollbackCardData) -> PostResult:
    """POST a tROAS rollback alert as a cardsV2 message to the tROAS Chat space."""
    return _post_to_troas_webhook(json.dumps(_build_troas_rollback_card(data)).encode("utf-8"))


# ---------------------------------------------------------------------------
# Budget card builders
# ---------------------------------------------------------------------------

def _build_budget_audit_card(data: BudgetAuditCardData) -> dict:
    sections: list[dict] = []

    total = data["total_proposals"]
    constrained = data["constrained_count"]
    excess = data["excess_count"]
    accounts = data["accounts_count"]

    bottom_parts: list[str] = []
    if constrained:
        bottom_parts.append(f"{constrained} constrained")
    if excess:
        bottom_parts.append(f"{excess} excess budget")

    sections.append({
        "widgets": [{
            "decoratedText": {
                "topLabel": "PROPOSALS READY",
                "text": f"<b>{total}</b> campaign{'s' if total != 1 else ''} across {accounts} account{'s' if accounts != 1 else ''}",
                "bottomLabel": "  |  ".join(bottom_parts) if bottom_parts else "Review the sheet",
                "startIcon": {"materialIcon": {"name": "attach_money", "fill": True}},
            }
        }]
    })

    url = (data.get("proposals_url") or "").strip()
    if url:
        sections.append({"widgets": [{"buttonList": {"buttons": [{
            "text": "Review Proposals",
            "onClick": {"openLink": {"url": url}},
            "color": {"red": 0.18, "green": 0.46, "blue": 0.83, "alpha": 1.0},
        }]}}]})

    return {
        "cardsV2": [{
            "cardId": "budget-audit",
            "card": {
                "header": {
                    "title": "Budget Proposals Ready",
                    "subtitle": data["date_str"],
                },
                "sections": sections,
            },
        }]
    }


def post_budget_audit_card(data: BudgetAuditCardData) -> PostResult:
    """POST a budget audit summary as a cardsV2 message to the tROAS Chat space."""
    return _post_to_troas_webhook(json.dumps(_build_budget_audit_card(data)).encode("utf-8"))


# ---------------------------------------------------------------------------
# Budget commit card builder
# ---------------------------------------------------------------------------

def _build_budget_commit_card(data: BudgetCommitCardData) -> dict:
    sections: list[dict] = []

    applied = data["applied"]
    errors  = data["errors"]

    if errors > 0 and applied == 0:
        status_icon = {"materialIcon": {"name": "error", "fill": True}}
    elif errors > 0:
        status_icon = {"materialIcon": {"name": "warning", "fill": True}}
    else:
        status_icon = {"materialIcon": {"name": "check_circle", "fill": True}}

    err_color = _COLOR_RED if errors > 0 else _COLOR_GREY
    summary = (
        f'<font color="{_COLOR_GREEN}"><b>Applied: {applied}</b></font>'
        f'    <font color="{err_color}"><b>Errors: {errors}</b></font>'
    )
    sections.append({
        "widgets": [{
            "decoratedText": {
                "topLabel": "COMMIT RESULT",
                "text": summary,
                "wrapText": True,
                "startIcon": status_icon,
            }
        }]
    })

    applied_items = data.get("applied_items") or []
    if applied_items:
        lines: list[str] = []
        for item in applied_items:
            dir_color = _COLOR_GREEN if item["direction"] == "UP" else _COLOR_AMBER
            dir_label = f'<font color="{dir_color}"><b>{item["direction"]}</b></font>'
            change_sign = "+" if item["change"] >= 0 else ""
            lines.append(
                f'<b>{item["campaign_name"]}</b>  ({item["account_name"]})<br>'
                f'  ${item["old_budget"]:.2f} → ${item["new_budget"]:.2f}  '
                f'{dir_label} {change_sign}${item["change"]:.2f}'
            )
        sections.append({
            "header": "APPLIED",
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}],
        })

    error_items = data.get("error_items") or []
    if error_items:
        lines = []
        for item in error_items:
            lines.append(
                f'<font color="{_COLOR_RED}"><b>{item["campaign_name"]}</b></font>'
                f'  {item["error"]}'
            )
        sections.append({
            "header": "ERRORS",
            "widgets": [{"textParagraph": {"text": "<br>".join(lines)}}],
        })

    url = (data.get("log_url") or "").strip()
    if url:
        sections.append({"widgets": [{"buttonList": {"buttons": [{
            "text": "View Budget Log",
            "onClick": {"openLink": {"url": url}},
        }]}}]})

    return {
        "cardsV2": [{
            "cardId": "budget-commit",
            "card": {
                "header": {
                    "title": "Budget Commit",
                    "subtitle": data["date_str"],
                },
                "sections": sections,
            },
        }]
    }


def post_budget_commit_card(data: BudgetCommitCardData) -> PostResult:
    """POST a budget commit result as a cardsV2 message to the tROAS Chat space."""
    return _post_to_troas_webhook(json.dumps(_build_budget_commit_card(data)).encode("utf-8"))
