"""Google Sheets dashboard writer for digest and tROAS proposal data.

Maintains a single living spreadsheet with tabs:
  Dashboard       -- summary KPIs + bar charts (auto-refresh from Latest data)
  Latest          -- full per-account table for the most recent digest run
  Alerts          -- current tROAS, budget pacing, and disapproval issues
  History         -- append-only archive, one row per account per run
  MER             -- current Ad Spend % per store
  MER History     -- append-only MER archive
  tROAS Proposals -- current M/W/F audit proposals awaiting approval (overwrite)
  tROAS Log       -- append-only record of every applied tROAS change
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from ads_mcp.reporting.digest import DigestData
from ads_mcp.reporting.mer import MerReportData
from ads_mcp.reporting.troas_audit import TroasProposal
from ads_mcp.reporting.budget_audit import BudgetProposal

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_LATEST_HEADERS = [
    "Account Name", "Customer ID", "Cost ($)", "Conversions",
    "Conv. Value ($)", "ROAS", "Clicks", "Impressions",
    "tROAS Alerts", "Budget Alerts", "Disapprovals",
]

_ALERTS_HEADERS = [
    "Account Name", "Campaign", "Alert Type", "Detail",
]

_HISTORY_HEADERS = [
    "Date", "Date Range", "Account Name", "Customer ID",
    "Cost ($)", "Conversions", "Conv. Value ($)", "ROAS",
    "Clicks", "Impressions",
]

_MER_HEADERS = [
    "Store Name", "Customer ID", "Ads Spend ($)", "Net Sales ($)",
    "Ad Spend %", "Status", "Prior Ad Spend %", "Change (pp)", "Trend",
]

_MER_HISTORY_HEADERS = [
    "Date", "Date Range", "Store Name", "Customer ID",
    "Ads Spend ($)", "Net Sales ($)", "Ad Spend %", "Status",
    "Prior Ad Spend %", "Change (pp)", "Trend",
]

_TROAS_PROPOSALS_HEADERS = [
    # A-C: identifiers visible without scrolling
    "Account Name", "Campaign Name", "Ad Group Name",
    # D-F: action columns — direction and decision side by side
    "Direction", "Current tROAS (%)", "Decision",
    # G onwards: proposal detail
    "Proposed tROAS (%)", "Change (pp)",
    "L7 Actual ROAS (%)", "L7 Target ROAS (%)", "Drift (%)",
    "L7 Spend ($)", "L7 Conv. Value ($)", "Prior L7 Spend ($)", "Spend Change (%)",
    # P-S: reference IDs and bidding type at the far right
    "Campaign ID", "Customer ID", "Ad Group ID", "Bidding Type",
]
# Column index reference (0-based):
#   A=0  Account Name      D=3  Direction          G=6  Proposed tROAS (%)
#   B=1  Campaign Name     E=4  Current tROAS (%)  H=7  Change (pp)
#   C=2  Ad Group Name     F=5  Decision           K=10 Drift (%)
#   P=15 Campaign ID       Q=16 Customer ID        R=17 Ad Group ID
#   S=18 Bidding Type

_TROAS_LOG_HEADERS = [
    "Applied Date", "Customer ID", "Campaign ID", "Campaign Name",
    "Ad Group ID", "Ad Group Name",
    "Account Name", "Direction", "Old tROAS (%)", "New tROAS (%)",
    "Change (pp)", "L7 Spend ($)",
]


# ---------------------------------------------------------------------------
# Service + helpers
# ---------------------------------------------------------------------------

def _service(credentials_path: str):
    # Hosted mode: the key JSON is pasted into a platform secret variable —
    # prefer it over a key file so no credential file enters the image.
    inline = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON")
    if inline:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(inline), scopes=_SCOPES,
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=_SCOPES,
        )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _sheet_map(svc, spreadsheet_id: str) -> dict[str, int]:
    """Return {title: sheetId} for every tab in the spreadsheet."""
    meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in meta["sheets"]
    }


def _has_charts(svc, spreadsheet_id: str, sheet_id: int) -> bool:
    meta = svc.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties/sheetId,charts)",
    ).execute()
    for sheet in meta["sheets"]:
        if sheet["properties"]["sheetId"] == sheet_id:
            return bool(sheet.get("charts"))
    return False


def _batch(svc, spreadsheet_id: str, requests: list[dict[str, Any]]) -> None:
    if not requests:
        return
    svc.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


def _write(svc, spreadsheet_id: str, range_: str, values: list[list]) -> None:
    svc.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


def _clear(svc, spreadsheet_id: str, range_: str) -> None:
    svc.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=range_,
    ).execute()


def _append(svc, spreadsheet_id: str, range_: str, values: list[list]) -> None:
    svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def _first_empty_row(svc, spreadsheet_id: str, tab: str) -> bool:
    """Return True if the tab has no data at all (not even a header)."""
    result = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{tab}!A1",
    ).execute()
    return not result.get("values")


# ---------------------------------------------------------------------------
# Tab setup
# ---------------------------------------------------------------------------

def _ensure_tabs(svc, spreadsheet_id: str) -> dict[str, int]:
    """Rename the default Sheet1 to Dashboard if needed; add missing tabs."""
    existing = _sheet_map(svc, spreadsheet_id)
    needed = ["Dashboard", "Latest", "Alerts", "History"]
    requests: list[dict[str, Any]] = []

    if "Sheet1" in existing and "Dashboard" not in existing:
        requests.append({
            "updateSheetProperties": {
                "properties": {"sheetId": existing["Sheet1"], "title": "Dashboard"},
                "fields": "title",
            }
        })
        existing["Dashboard"] = existing.pop("Sheet1")

    for title in needed:
        if title not in existing:
            requests.append({"addSheet": {"properties": {"title": title}}})

    if requests:
        _batch(svc, spreadsheet_id, requests)

    return _sheet_map(svc, spreadsheet_id)


# ---------------------------------------------------------------------------
# One-time formatting + chart creation
# ---------------------------------------------------------------------------

def _setup_latest_formatting(svc, spreadsheet_id: str, sheet_id: int) -> None:
    white = {"red": 1.0, "green": 1.0, "blue": 1.0}
    header_bg = {"red": 0.18, "green": 0.39, "blue": 0.67}

    _batch(svc, spreadsheet_id, [
        # Bold white header on blue background
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_bg,
                        "textFormat": {"bold": True, "foregroundColor": white},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        # Freeze header row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Auto-resize account name column
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1,
                }
            }
        },
        # ROAS gradient: red at 0, white at 2, green at 5
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 5,
                        "endColumnIndex": 6,
                    }],
                    "gradientRule": {
                        "minpoint": {
                            "color": {"red": 0.90, "green": 0.30, "blue": 0.30},
                            "type": "NUMBER",
                            "value": "0",
                        },
                        "midpoint": {
                            "color": white,
                            "type": "NUMBER",
                            "value": "2",
                        },
                        "maxpoint": {
                            "color": {"red": 0.20, "green": 0.78, "blue": 0.35},
                            "type": "NUMBER",
                            "value": "5",
                        },
                    },
                },
                "index": 0,
            }
        },
        # Disapprovals > 0: light red background
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 10,
                        "endColumnIndex": 11,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_GREATER",
                            "values": [{"userEnteredValue": "0"}],
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 0.80, "blue": 0.80},
                        },
                    },
                },
                "index": 1,
            }
        },
        # tROAS Alerts > 0: light orange background
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 8,
                        "endColumnIndex": 10,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_GREATER",
                            "values": [{"userEnteredValue": "0"}],
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 0.90, "blue": 0.70},
                        },
                    },
                },
                "index": 2,
            }
        },
    ])


def _create_charts(
    svc,
    spreadsheet_id: str,
    dashboard_id: int,
    latest_id: int,
    num_accounts: int,
) -> None:
    """Add spend and ROAS bar charts to the Dashboard tab."""
    end_row = num_accounts + 1  # header + data rows

    def src(col_start: int, col_end: int) -> dict:
        return {
            "sourceRange": {
                "sources": [{
                    "sheetId": latest_id,
                    "startRowIndex": 0,
                    "endRowIndex": end_row,
                    "startColumnIndex": col_start,
                    "endColumnIndex": col_end,
                }]
            }
        }

    chart_height = max(300, num_accounts * 22 + 80)

    _batch(svc, spreadsheet_id, [
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Cost by Account (USD)",
                        "basicChart": {
                            "chartType": "BAR",
                            "legendPosition": "NO_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Cost (USD)"},
                                {"position": "LEFT_AXIS", "title": ""},
                            ],
                            "domains": [{"domain": src(0, 1)}],
                            "series": [{"series": src(2, 3), "targetAxis": "BOTTOM_AXIS"}],
                            "headerCount": 1,
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": dashboard_id,
                                "rowIndex": 17,
                                "columnIndex": 0,
                            },
                            "widthPixels": 520,
                            "heightPixels": chart_height,
                        }
                    },
                }
            }
        },
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "ROAS by Account",
                        "basicChart": {
                            "chartType": "BAR",
                            "legendPosition": "NO_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "ROAS"},
                                {"position": "LEFT_AXIS", "title": ""},
                            ],
                            "domains": [{"domain": src(0, 1)}],
                            "series": [{"series": src(5, 6), "targetAxis": "BOTTOM_AXIS"}],
                            "headerCount": 1,
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": dashboard_id,
                                "rowIndex": 17,
                                "columnIndex": 9,
                            },
                            "widthPixels": 520,
                            "heightPixels": chart_height,
                        }
                    },
                }
            }
        },
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": "Conversions by Account",
                        "basicChart": {
                            "chartType": "BAR",
                            "legendPosition": "NO_LEGEND",
                            "axis": [
                                {"position": "BOTTOM_AXIS", "title": "Conversions"},
                                {"position": "LEFT_AXIS", "title": ""},
                            ],
                            "domains": [{"domain": src(0, 1)}],
                            "series": [{"series": src(3, 4), "targetAxis": "BOTTOM_AXIS"}],
                            "headerCount": 1,
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": dashboard_id,
                                "rowIndex": 17,
                                "columnIndex": 18,
                            },
                            "widthPixels": 520,
                            "heightPixels": chart_height,
                        }
                    },
                }
            }
        },
    ])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def write_digest(digest_data: DigestData, spreadsheet_id: str) -> str:
    """Write DigestData to the Google Ads Performance Dashboard spreadsheet.

    Creates tabs, formatting, and charts on first run. Updates data on every run.
    Returns the Dashboard tab URL.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    ids = _ensure_tabs(svc, spreadsheet_id)

    dashboard_id = ids["Dashboard"]
    latest_id = ids["Latest"]
    alerts_id = ids["Alerts"]

    # --- Latest tab ---
    _clear(svc, spreadsheet_id, "Latest!A:K")
    latest_rows: list[list] = [_LATEST_HEADERS]
    for acc in digest_data["accounts"]:
        latest_rows.append([
            acc["name"],
            acc["customer_id"],
            acc["cost"],
            acc["conversions"],
            acc["conversions_value"],
            acc["roas"],
            acc["clicks"],
            acc["impressions"],
            len(acc["troas_alerts"]),
            len(acc["budget_alerts"]),
            acc["disapproval_count"],
        ])
    _write(svc, spreadsheet_id, "Latest!A1", latest_rows)

    # --- Alerts tab ---
    _clear(svc, spreadsheet_id, "Alerts!A:D")
    alert_rows: list[list] = [_ALERTS_HEADERS]
    for acc in digest_data["accounts"]:
        for alert in acc["troas_alerts"]:
            alert_rows.append([
                acc["name"],
                alert["name"],
                f"tROAS {alert['status']}",
                f"Target: {alert['target_roas']}, Actual: {alert['actual_roas']}, Drift: {alert['drift_pct']}%",
            ])
        for alert in acc["budget_alerts"]:
            alert_rows.append([
                acc["name"],
                alert["name"],
                alert["status"],
                f"Budget: ${alert['daily_budget']}, Spend: ${alert['spend_today']}, Ratio: {alert['pacing_ratio']}",
            ])
    if len(alert_rows) == 1:
        alert_rows.append(["No active alerts", "", "", ""])
    _write(svc, spreadsheet_id, "Alerts!A1", alert_rows)

    # --- History tab (append-only) ---
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _first_empty_row(svc, spreadsheet_id, "History"):
        _write(svc, spreadsheet_id, "History!A1", [_HISTORY_HEADERS])
    history_rows: list[list] = []
    for acc in digest_data["accounts"]:
        history_rows.append([
            today,
            digest_data["date_range"],
            acc["name"],
            acc["customer_id"],
            acc["cost"],
            acc["conversions"],
            acc["conversions_value"],
            acc["roas"],
            acc["clicks"],
            acc["impressions"],
        ])
    _append(svc, spreadsheet_id, "History!A:J", history_rows)

    # --- Dashboard tab ---
    d = digest_data
    _write(svc, spreadsheet_id, "Dashboard!A1", [
        ["Google Ads Performance Dashboard"],
        [""],
        ["Generated", d["generated_at"]],
        ["Date Range", d["date_range"]],
        [""],
        ["SUMMARY", ""],
        ["Total Cost", d["total_cost"]],
        ["Total ROAS", d["total_roas"]],
        ["Total Conversions", d["total_conversions"]],
        ["Total Conv. Value", d["total_conversions_value"]],
        ["Total Clicks", d["total_clicks"]],
        ["Total Impressions", d["total_impressions"]],
        [""],
        ["ALERTS", ""],
        ["Accounts with tROAS Alerts", d["accounts_with_troas_alerts"]],
        ["Accounts with Budget Alerts", d["accounts_with_budget_alerts"]],
        ["Total Disapprovals", d["total_disapprovals"]],
    ])

    # One-time setup: formatting and charts
    if not _has_charts(svc, spreadsheet_id, dashboard_id):
        _setup_latest_formatting(svc, spreadsheet_id, latest_id)
        _create_charts(svc, spreadsheet_id, dashboard_id, latest_id, len(digest_data["accounts"]))

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={dashboard_id}"


# ---------------------------------------------------------------------------
# MER tab helpers
# ---------------------------------------------------------------------------

def _ensure_mer_tabs(svc, spreadsheet_id: str) -> dict[str, int]:
    """Add MER and MER History tabs if they do not already exist."""
    existing = _sheet_map(svc, spreadsheet_id)
    needed = ["MER", "MER History"]
    requests: list[dict[str, Any]] = []
    for title in needed:
        if title not in existing:
            requests.append({"addSheet": {"properties": {"title": title}}})
    if requests:
        _batch(svc, spreadsheet_id, requests)
    return _sheet_map(svc, spreadsheet_id)


def _setup_mer_formatting(svc, spreadsheet_id: str, mer_sheet_id: int) -> None:
    """Apply header formatting and MER gradient conditional format to the MER tab."""
    white = {"red": 1.0, "green": 1.0, "blue": 1.0}
    header_bg = {"red": 0.18, "green": 0.39, "blue": 0.67}

    _batch(svc, spreadsheet_id, [
        # Blue header row with bold white text
        {
            "repeatCell": {
                "range": {"sheetId": mer_sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_bg,
                        "textFormat": {"bold": True, "foregroundColor": white},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        # Freeze header row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": mer_sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Ad Spend % column (col E, index 4): green at 0%, white at 10%, red at 20%+
        # Lower ad spend % = better efficiency, so green is at the low end.
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": mer_sheet_id,
                        "startRowIndex": 2,       # skip header + portfolio summary row
                        "startColumnIndex": 4,
                        "endColumnIndex": 5,
                    }],
                    "gradientRule": {
                        "minpoint": {
                            "color": {"red": 0.20, "green": 0.78, "blue": 0.35},
                            "type": "NUMBER",
                            "value": "0",
                        },
                        "midpoint": {
                            "color": white,
                            "type": "NUMBER",
                            "value": "10",
                        },
                        "maxpoint": {
                            "color": {"red": 0.90, "green": 0.30, "blue": 0.30},
                            "type": "NUMBER",
                            "value": "20",
                        },
                    },
                },
                "index": 0,
            }
        },
        # Portfolio summary row (row index 1): light grey background + bold text
        {
            "repeatCell": {
                "range": {"sheetId": mer_sheet_id, "startRowIndex": 1, "endRowIndex": 2},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.90, "green": 0.90, "blue": 0.90},
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        # Change (pp) column (col H, index 7): green when negative (improving),
        # white at 0, red when positive (worsening). Range: -5pp to +5pp.
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": mer_sheet_id,
                        "startRowIndex": 1,   # include portfolio row
                        "startColumnIndex": 7,
                        "endColumnIndex": 8,
                    }],
                    "gradientRule": {
                        "minpoint": {
                            "color": {"red": 0.20, "green": 0.78, "blue": 0.35},
                            "type": "NUMBER",
                            "value": "-5",
                        },
                        "midpoint": {
                            "color": {"red": 1.0, "green": 1.0, "blue": 1.0},
                            "type": "NUMBER",
                            "value": "0",
                        },
                        "maxpoint": {
                            "color": {"red": 0.90, "green": 0.30, "blue": 0.30},
                            "type": "NUMBER",
                            "value": "5",
                        },
                    },
                },
                "index": 1,
            }
        },
        # Trend column (col I, index 8): 3 green shades + 3 red shades scaled by
        # the numeric Change (pp) value in col H. Custom formula rules reference $H
        # so colour intensity reflects magnitude. Most extreme threshold evaluated first.
        # Green shades (improving: H < threshold)
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": mer_sheet_id, "startRowIndex": 1, "startColumnIndex": 8, "endColumnIndex": 9}],
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=$H2<-3"}]},
                        "format": {"backgroundColor": {"red": 0.13, "green": 0.55, "blue": 0.13}},
                    },
                },
                "index": 2,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": mer_sheet_id, "startRowIndex": 1, "startColumnIndex": 8, "endColumnIndex": 9}],
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=$H2<-1"}]},
                        "format": {"backgroundColor": {"red": 0.34, "green": 0.74, "blue": 0.37}},
                    },
                },
                "index": 3,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": mer_sheet_id, "startRowIndex": 1, "startColumnIndex": 8, "endColumnIndex": 9}],
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=$H2<-0.5"}]},
                        "format": {"backgroundColor": {"red": 0.72, "green": 0.93, "blue": 0.74}},
                    },
                },
                "index": 4,
            }
        },
        # Red shades (worsening: H > threshold)
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": mer_sheet_id, "startRowIndex": 1, "startColumnIndex": 8, "endColumnIndex": 9}],
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=$H2>3"}]},
                        "format": {"backgroundColor": {"red": 0.80, "green": 0.10, "blue": 0.10}},
                    },
                },
                "index": 5,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": mer_sheet_id, "startRowIndex": 1, "startColumnIndex": 8, "endColumnIndex": 9}],
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=$H2>1"}]},
                        "format": {"backgroundColor": {"red": 0.94, "green": 0.43, "blue": 0.43}},
                    },
                },
                "index": 6,
            }
        },
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": mer_sheet_id, "startRowIndex": 1, "startColumnIndex": 8, "endColumnIndex": 9}],
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": "=$H2>0.5"}]},
                        "format": {"backgroundColor": {"red": 1.0, "green": 0.80, "blue": 0.80}},
                    },
                },
                "index": 7,
            }
        },
        # Auto-resize store name column
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": mer_sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1,
                }
            }
        },
    ])


# ---------------------------------------------------------------------------
# MER main entry point
# ---------------------------------------------------------------------------

def write_mer_report(mer_data: MerReportData, spreadsheet_id: str) -> str:
    """Write a fully assembled MerReportData to the MER tab in the dashboard spreadsheet.

    Creates MER and MER History tabs on first run with formatting.
    On subsequent runs, overwrites MER tab data and appends to MER History.
    Returns the MER tab URL.

    Row layout:
      Row 1: Headers (Store Name, Customer ID, Ads Spend, Net Sales, MER, Status)
      Row 2: PORTFOLIO blended summary (bold grey)
      Row 3+: Per-store rows sorted by Ads Spend descending
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    ids = _ensure_mer_tabs(svc, spreadsheet_id)

    mer_sheet_id = ids["MER"]

    # --- MER tab (overwrite) ---
    _clear(svc, spreadsheet_id, "MER!A:I")

    portfolio_row = [
        "PORTFOLIO (Blended)",
        "",
        mer_data["total_cost"],
        mer_data["total_net_sales"],
        mer_data["portfolio_mer"],
        mer_data["portfolio_mer_status"],
        mer_data["portfolio_prior_mer"],
        mer_data["portfolio_mer_delta"],
        mer_data["portfolio_trend"],
    ]

    store_rows: list[list] = []
    for store in mer_data["stores"]:
        store_rows.append([
            store["store_name"],
            store["ads_customer_id"],
            store["cost"],
            store["net_sales"],
            store["mer"],
            store["mer_status"],
            store["prior_mer"],
            store["mer_delta"],
            store["trend"],
        ])

    all_rows = [_MER_HEADERS, portfolio_row] + store_rows
    _write(svc, spreadsheet_id, "MER!A1", all_rows)

    # --- MER History tab (append-only) ---
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _first_empty_row(svc, spreadsheet_id, "MER History"):
        _write(svc, spreadsheet_id, "MER History!A1", [_MER_HISTORY_HEADERS])

    history_rows: list[list] = []
    # Append portfolio blended row first
    history_rows.append([
        today,
        mer_data["date_range"],
        "PORTFOLIO (Blended)",
        "",
        mer_data["total_cost"],
        mer_data["total_net_sales"],
        mer_data["portfolio_mer"],
        mer_data["portfolio_mer_status"],
        mer_data["portfolio_prior_mer"],
        mer_data["portfolio_mer_delta"],
        mer_data["portfolio_trend"],
    ])
    for store in mer_data["stores"]:
        history_rows.append([
            today,
            mer_data["date_range"],
            store["store_name"],
            store["ads_customer_id"],
            store["cost"],
            store["net_sales"],
            store["mer"],
            store["mer_status"],
            store["prior_mer"],
            store["mer_delta"],
            store["trend"],
        ])
    _append(svc, spreadsheet_id, "MER History!A:K", history_rows)

    # One-time formatting (check if portfolio summary row already bold)
    meta = svc.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=["MER!A2:A2"],
        fields="sheets(data/rowData/values/userEnteredFormat/textFormat/bold)",
    ).execute()
    already_formatted = False
    try:
        bold = (
            meta["sheets"][0]["data"][0]["rowData"][0]
            ["values"][0]["userEnteredFormat"]["textFormat"]["bold"]
        )
        already_formatted = bool(bold)
    except (KeyError, IndexError):
        already_formatted = False

    if not already_formatted:
        _setup_mer_formatting(svc, spreadsheet_id, mer_sheet_id)

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={mer_sheet_id}"


# ---------------------------------------------------------------------------
# tROAS Proposals tab helpers
# ---------------------------------------------------------------------------

def _clear_conditional_format_rules(svc, spreadsheet_id: str, sheet_id: int) -> None:
    """Delete all conditional format rules on a given sheet.

    Reads the current count from spreadsheet metadata, then issues a single
    batchUpdate deleting index 0 that many times (each deletion shifts the
    remaining rules down so index 0 always points to the next one).
    """
    meta = svc.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties/sheetId,conditionalFormats)",
    ).execute()

    count = 0
    for sheet in meta.get("sheets", []):
        if sheet.get("properties", {}).get("sheetId") == sheet_id:
            count = len(sheet.get("conditionalFormats", []))
            break

    if count == 0:
        return

    requests = [
        {"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": 0}}
        for _ in range(count)
    ]
    _batch(svc, spreadsheet_id, requests)


def _ensure_troas_tabs(svc, spreadsheet_id: str) -> dict[str, int]:
    """Add tROAS Proposals and tROAS Log tabs if they do not already exist."""
    existing = _sheet_map(svc, spreadsheet_id)
    needed = ["tROAS Proposals", "tROAS Log"]
    requests: list[dict[str, Any]] = []
    for title in needed:
        if title not in existing:
            requests.append({"addSheet": {"properties": {"title": title}}})
    if requests:
        _batch(svc, spreadsheet_id, requests)
    return _sheet_map(svc, spreadsheet_id)


def _setup_troas_proposals_formatting(
    svc, spreadsheet_id: str, sheet_id: int, num_rows: int
) -> None:
    """Apply header formatting, conditional colours, and Decision dropdown.

    Column layout (0-based indices):
      D=3  Direction    (TIGHTEN orange | LOOSEN green)
      F=5  Decision     (Approve green  | Skip grey)
      K=10 Drift (%)    (colour by magnitude band: 7-13 yellow, 13-22 orange,
                          22-30 dark-orange, 30+ red)

    Clears any existing conditional format rules on the sheet before re-adding,
    so rules do not accumulate across runs.
    """
    _clear_conditional_format_rules(svc, spreadsheet_id, sheet_id)

    white       = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
    header_bg   = {"red": 0.18, "green": 0.39, "blue": 0.67}
    green       = {"red": 0.20, "green": 0.78, "blue": 0.35}
    grey        = {"red": 0.85, "green": 0.85, "blue": 0.85}
    dir_orange  = {"red": 1.0,  "green": 0.75, "blue": 0.30}
    drift_y     = {"red": 1.0,  "green": 0.95, "blue": 0.70}   # 7-13%
    drift_o     = {"red": 1.0,  "green": 0.80, "blue": 0.40}   # 13-22%
    drift_do    = {"red": 1.0,  "green": 0.58, "blue": 0.20}   # 22-30%
    drift_r     = {"red": 0.90, "green": 0.30, "blue": 0.30}   # 30%+

    def _drift_range() -> list[dict]:
        return [{
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "startColumnIndex": 10,
            "endColumnIndex": 11,
        }]

    requests: list[dict[str, Any]] = [
        # Blue header row
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_bg,
                        "textFormat": {"bold": True, "foregroundColor": white},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        # Freeze header row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Direction col D (index 3): TIGHTEN orange
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 1,
                                "startColumnIndex": 3, "endColumnIndex": 4}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ",
                                      "values": [{"userEnteredValue": "TIGHTEN"}]},
                        "format": {"backgroundColor": dir_orange},
                    },
                },
                "index": 0,
            }
        },
        # Direction col D (index 3): LOOSEN green
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 1,
                                "startColumnIndex": 3, "endColumnIndex": 4}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ",
                                      "values": [{"userEnteredValue": "LOOSEN"}]},
                        "format": {"backgroundColor": green},
                    },
                },
                "index": 1,
            }
        },
        # Decision col F (index 5): Approve green
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 1,
                                "startColumnIndex": 5, "endColumnIndex": 6}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ",
                                      "values": [{"userEnteredValue": "Approve"}]},
                        "format": {"backgroundColor": green},
                    },
                },
                "index": 2,
            }
        },
        # Decision col F (index 5): Skip grey
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 1,
                                "startColumnIndex": 5, "endColumnIndex": 6}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ",
                                      "values": [{"userEnteredValue": "Skip"}]},
                        "format": {"backgroundColor": grey},
                    },
                },
                "index": 3,
            }
        },
        # Drift % col K (index 10): positive drift = green (over target = good)
        # This is index 4 (highest priority among drift rules) so it wins for any
        # positive value before the magnitude rules below are evaluated.
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _drift_range(),
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA",
                                      "values": [{"userEnteredValue": "=$K2>0"}]},
                        "format": {"backgroundColor": green},
                    },
                },
                "index": 4,
            }
        },
        # Drift % col K: negative drift 30%+ red
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _drift_range(),
                    "booleanRule": {
                        "condition": {"type": "CUSTOM_FORMULA",
                                      "values": [{"userEnteredValue": "=ABS($K2)>=30"}]},
                        "format": {"backgroundColor": drift_r},
                    },
                },
                "index": 5,
            }
        },
        # Drift % col K: negative drift 22-30% dark orange
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _drift_range(),
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=AND(ABS($K2)>=22,ABS($K2)<30)"}],
                        },
                        "format": {"backgroundColor": drift_do},
                    },
                },
                "index": 6,
            }
        },
        # Drift % col K: negative drift 13-22% orange
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _drift_range(),
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=AND(ABS($K2)>=13,ABS($K2)<22)"}],
                        },
                        "format": {"backgroundColor": drift_o},
                    },
                },
                "index": 7,
            }
        },
        # Drift % col K: negative drift 7-13% light yellow
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _drift_range(),
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=AND(ABS($K2)>=7,ABS($K2)<13)"}],
                        },
                        "format": {"backgroundColor": drift_y},
                    },
                },
                "index": 8,
            }
        },
        # Auto-resize name columns A-C
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 3,
                }
            }
        },
    ]

    # Decision dropdown (col F, index 5) for all data rows
    if num_rows > 0:
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": num_rows + 1,
                    "startColumnIndex": 5,
                    "endColumnIndex": 6,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [
                            {"userEnteredValue": "Approve"},
                            {"userEnteredValue": "Skip"},
                            {"userEnteredValue": "-"},
                        ],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        })

    _batch(svc, spreadsheet_id, requests)


def write_troas_proposals(
    proposals: list[TroasProposal], spreadsheet_id: str
) -> str:
    """Overwrite the tROAS Proposals tab with a fresh set of proposals.

    Creates the tab and tROAS Log tab if they do not exist. Applies header
    formatting, conditional colours, and a Decision dropdown on each run.
    Returns the tROAS Proposals tab URL.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    ids = _ensure_troas_tabs(svc, spreadsheet_id)
    proposals_sheet_id = ids["tROAS Proposals"]

    # Overwrite the tab (clear A:S to cover all 19 columns)
    _clear(svc, spreadsheet_id, "tROAS Proposals!A:S")

    rows: list[list] = [_TROAS_PROPOSALS_HEADERS]
    for p in proposals:
        rows.append([
            # A-C identifiers
            p["account_name"],
            p["campaign_name"],
            p["ad_group_name"],
            # D-F action
            p["direction"],
            p["current_target_roas"],
            p["decision"],
            # G-O proposal detail
            p["proposed_target_roas"],
            p["change_pp"],
            p["l7_actual_roas"],
            p["l7_target_roas"],
            p["drift_pct"],
            p["l7_spend"],
            p["l7_conversions_value"],
            p["prior_l7_spend"],
            p["spend_change_pct"],
            # P-S reference IDs and bidding type
            p["campaign_id"],
            p["customer_id"],
            p["ad_group_id"],
            p["bidding_type"],
        ])

    _write(svc, spreadsheet_id, "tROAS Proposals!A1", rows)

    # Re-apply formatting every run (handles new rows and cleared rules)
    _setup_troas_proposals_formatting(svc, spreadsheet_id, proposals_sheet_id, len(proposals))

    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/edit#gid={proposals_sheet_id}"
    )


def read_troas_decisions(spreadsheet_id: str) -> list[dict]:
    """Read the tROAS Proposals tab and return rows where Decision = 'Approve'.

    Each returned dict has the same keys as the _TROAS_PROPOSALS_HEADERS columns,
    lowercased and with spaces replaced by underscores, plus a 'decision' key.
    Returns an empty list if the tab does not exist or has no approved rows.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)

    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="tROAS Proposals!A:S",
        ).execute()
    except Exception:
        return []

    rows = result.get("values", [])
    if len(rows) < 2:
        return []

    # Use the canonical header definition (not the sheet's row 0) so that
    # stale or mismatched header rows in the sheet don't silently map columns
    # to wrong keys (e.g. missing "Customer ID" returning "" for every row).
    header = _TROAS_PROPOSALS_HEADERS
    approved: list[dict] = []
    for row in rows[1:]:
        # Pad short rows to header length
        padded = row + [""] * (len(header) - len(row))
        record = dict(zip(header, padded))
        if record.get("Decision", "").strip().lower() == "approve":
            approved.append(record)
    return approved


def has_pending_troas_decisions(spreadsheet_id: str) -> bool:
    """Return True if the tROAS Proposals tab has rows with Decision = '-' or empty.

    Used by the T/TH/S reminder check to decide whether to post a nudge message.
    Returns False if the tab does not exist, is empty, or all rows are decided.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        return False

    svc = _service(credentials_path)

    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="tROAS Proposals!F:F",  # Decision column (col F)
        ).execute()
    except Exception:
        return False

    rows = result.get("values", [])
    if len(rows) < 2:
        return False  # header only or empty

    # rows[0] is the header; check data rows
    for row in rows[1:]:
        val = row[0].strip() if row else ""
        if val in ("-", ""):
            return True
    return False


def append_troas_log(log_rows: list[dict], spreadsheet_id: str) -> None:
    """Append applied tROAS change records to the tROAS Log tab.

    Each dict in log_rows should have keys matching _TROAS_LOG_HEADERS:
    applied_date, customer_id, campaign_id, campaign_name,
    ad_group_id, ad_group_name, account_name, direction,
    old_target_roas, new_target_roas, change_pp, l7_spend.
    ad_group_id / ad_group_name may be absent for campaign-level entries.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    _ensure_troas_tabs(svc, spreadsheet_id)

    if _first_empty_row(svc, spreadsheet_id, "tROAS Log"):
        _write(svc, spreadsheet_id, "tROAS Log!A1", [_TROAS_LOG_HEADERS])

    rows: list[list] = []
    for r in log_rows:
        rows.append([
            r.get("applied_date", ""),
            r.get("customer_id", ""),
            r.get("campaign_id", ""),
            r.get("campaign_name", ""),
            r.get("ad_group_id", ""),
            r.get("ad_group_name", ""),
            r.get("account_name", ""),
            r.get("direction", ""),
            r.get("old_target_roas", ""),
            r.get("new_target_roas", ""),
            r.get("change_pp", ""),
            r.get("l7_spend", ""),
        ])

    _append(svc, spreadsheet_id, "tROAS Log!A:L", rows)


_BUDGET_LOG_HEADERS = [
    "Applied Date",       # A
    "Customer ID",        # B
    "Campaign ID",        # C
    "Campaign Name",      # D
    "Account Name",       # E
    "Old Budget ($)",     # F
    "New Budget ($)",     # G
    "Change ($)",         # H
    "Direction",          # I  UP | DOWN
    "Status",             # J  applied | error
    "Error",              # K  empty on success
]

_BUDGET_PROPOSALS_HEADERS = [
    # A-E: campaign info and threshold signal
    "Account Name",        # A col index 0
    "Campaign Name",       # B col index 1
    "Channel Type",        # C col index 2
    "Current Budget ($)",  # D col index 3
    "Days at 80%+",        # E col index 4  -- conditional colour by count
    # F: user input column
    "New Budget ($)",      # F col index 5  -- gold/amber background
    # G-J: spend context
    "Avg Daily Spend ($)", # G col index 6
    "Max Daily Spend ($)", # H col index 7
    "L7 Spend ($)",        # I col index 8
    "L7 ROAS",             # J col index 9
    # K-M: reference IDs
    "Campaign ID",         # K col index 10
    "Customer ID",         # L col index 11
    "Budget ID",           # M col index 12
]


def _ensure_budget_tab(svc, spreadsheet_id: str) -> dict[str, int]:
    """Add Budget Proposals tab if it does not already exist."""
    existing = _sheet_map(svc, spreadsheet_id)
    if "Budget Proposals" not in existing:
        _batch(svc, spreadsheet_id, [
            {"addSheet": {"properties": {"title": "Budget Proposals"}}}
        ])
    return _sheet_map(svc, spreadsheet_id)


def _setup_budget_proposals_formatting(
    svc, spreadsheet_id: str, sheet_id: int, num_rows: int
) -> None:
    """Apply header formatting and conditional colours to the Budget Proposals tab.

    Column layout (0-based indices):
      E=4  Days at 80%+  -- light orange for 2-3, orange for 4-5, red for 6-7
      F=5  New Budget ($) -- gold/amber background to signal user input required

    Clears any existing conditional format rules before re-adding so rules do
    not accumulate across runs.
    """
    _clear_conditional_format_rules(svc, spreadsheet_id, sheet_id)

    white     = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
    header_bg = {"red": 0.18, "green": 0.39, "blue": 0.67}
    gold      = {"red": 1.0,  "green": 0.85, "blue": 0.40}  # user input column
    lt_orange = {"red": 1.0,  "green": 0.90, "blue": 0.65}  # 2-3 days
    orange    = {"red": 1.0,  "green": 0.65, "blue": 0.20}  # 4-5 days
    red       = {"red": 0.90, "green": 0.30, "blue": 0.30}  # 6-7 days
    lt_teal   = {"red": 0.82, "green": 0.93, "blue": 0.92}  # excess budget rows

    def _days_range() -> list[dict]:
        return [{
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "startColumnIndex": 4,
            "endColumnIndex": 5,
        }]

    requests: list[dict[str, Any]] = [
        # Blue header row with bold white text
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": header_bg,
                        "textFormat": {"bold": True, "foregroundColor": white},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        # Freeze header row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Column F (index 5) gold/amber background for all data rows
        # (Signals user input required; applied before conditional rules so
        #  header blue overrides it on row 0 via the repeatCell above.)
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "startColumnIndex": 5,
                    "endColumnIndex": 6,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": gold,
                    }
                },
                "fields": "userEnteredFormat(backgroundColor)",
            }
        },
        # Days at 80%+ (col E, index 4): 6-7 = red (evaluated first; highest priority)
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _days_range(),
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=$E2>=6"}],
                        },
                        "format": {"backgroundColor": red},
                    },
                },
                "index": 0,
            }
        },
        # Days at 80%+: 4-5 = orange
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _days_range(),
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=$E2>=4"}],
                        },
                        "format": {"backgroundColor": orange},
                    },
                },
                "index": 1,
            }
        },
        # Days at 80%+: 2-3 = light orange
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": _days_range(),
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=$E2>=2"}],
                        },
                        "format": {"backgroundColor": lt_orange},
                    },
                },
                "index": 2,
            }
        },
        # Excess budget rows (days_at_threshold = 0): light teal on columns A:E
        # Column F (gold, user input) is excluded so it stays gold for all rows.
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 5,  # A through E inclusive
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=$E2=0"}],
                        },
                        "format": {"backgroundColor": lt_teal},
                    },
                },
                "index": 3,
            }
        },
        # Excess budget rows: light teal on columns G:M (skipping F)
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 6,   # G
                        "endColumnIndex": 13,    # M inclusive
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=$E2=0"}],
                        },
                        "format": {"backgroundColor": lt_teal},
                    },
                },
                "index": 4,
            }
        },
        # Auto-resize columns A (Account Name), B (Campaign Name), C (Channel Type)
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 3,
                }
            }
        },
    ]

    _batch(svc, spreadsheet_id, requests)


def write_budget_proposals(
    proposals: list[BudgetProposal], spreadsheet_id: str
) -> str:
    """Overwrite the Budget Proposals tab with a fresh set of proposals.

    Creates the tab if it does not exist. Applies header formatting and
    conditional colours on each run. Column F (New Budget) is gold/amber
    to prompt user input.

    Returns the Budget Proposals tab URL.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    ids = _ensure_budget_tab(svc, spreadsheet_id)
    sheet_id = ids["Budget Proposals"]

    # Overwrite tab (clear A:M to cover all 13 columns)
    _clear(svc, spreadsheet_id, "Budget Proposals!A:M")

    rows: list[list] = [_BUDGET_PROPOSALS_HEADERS]
    for p in proposals:
        rows.append([
            p["account_name"],       # A
            p["campaign_name"],      # B
            p["channel_type"],       # C
            p["current_budget"],     # D
            p["days_at_threshold"],  # E
            "",                      # F -- New Budget ($): user fills this in
            p["avg_daily_spend"],    # G
            p["max_daily_spend"],    # H
            p["l7_spend"],           # I
            p["l7_roas"],            # J
            p["campaign_id"],        # K
            p["customer_id"],        # L
            p["budget_id"],          # M
        ])

    _write(svc, spreadsheet_id, "Budget Proposals!A1", rows)

    # Re-apply formatting every run (handles new rows and cleared rules)
    _setup_budget_proposals_formatting(svc, spreadsheet_id, sheet_id, len(proposals))

    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/edit#gid={sheet_id}"
    )


def read_budget_decisions(spreadsheet_id: str) -> list[dict]:
    """Read the Budget Proposals tab and return rows where New Budget ($) has a value.

    Filters to rows where column F (New Budget) is non-empty and parseable as a
    float > 0. Each returned dict is keyed by the header names from
    _BUDGET_PROPOSALS_HEADERS, using the original header string as the key.

    Returns an empty list if the tab does not exist, is empty, or has no filled rows.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)

    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Budget Proposals!A:M",
        ).execute()
    except Exception:
        return []

    rows = result.get("values", [])
    if len(rows) < 2:
        return []

    header = rows[0]
    decisions: list[dict] = []

    for row in rows[1:]:
        # Pad short rows to header length so zip is always complete
        padded = row + [""] * (len(header) - len(row))
        record = dict(zip(header, padded))

        raw_new_budget = record.get("New Budget ($)", "").strip()
        if not raw_new_budget:
            continue
        try:
            new_budget_val = float(raw_new_budget)
        except (ValueError, TypeError):
            continue
        if new_budget_val <= 0:
            continue

        record["_new_budget_float"] = new_budget_val
        decisions.append(record)

    return decisions


def _ensure_budget_log_tab(svc, spreadsheet_id: str) -> dict[str, int]:
    """Add Budget Log tab if it does not already exist."""
    existing = _sheet_map(svc, spreadsheet_id)
    if "Budget Log" not in existing:
        _batch(svc, spreadsheet_id, [
            {"addSheet": {"properties": {"title": "Budget Log"}}}
        ])
    return _sheet_map(svc, spreadsheet_id)


def append_budget_log(log_rows: list[dict], spreadsheet_id: str) -> None:
    """Append applied budget change records to the Budget Log tab.

    Each dict in log_rows should have keys:
    applied_date, customer_id, campaign_id, campaign_name, account_name,
    old_budget, new_budget, change, direction, status, error.

    Creates the tab and writes the header row on first use.
    Appends one row per change on subsequent calls.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    _ensure_budget_log_tab(svc, spreadsheet_id)

    if _first_empty_row(svc, spreadsheet_id, "Budget Log"):
        _write(svc, spreadsheet_id, "Budget Log!A1", [_BUDGET_LOG_HEADERS])

    rows: list[list] = []
    for r in log_rows:
        rows.append([
            r.get("applied_date", ""),
            r.get("customer_id", ""),
            r.get("campaign_id", ""),
            r.get("campaign_name", ""),
            r.get("account_name", ""),
            r.get("old_budget", ""),
            r.get("new_budget", ""),
            r.get("change", ""),
            r.get("direction", ""),
            r.get("status", ""),
            r.get("error", ""),
        ])

    _append(svc, spreadsheet_id, "Budget Log!A:K", rows)


def read_troas_log_recent(spreadsheet_id: str, days: int = 3) -> list[dict]:
    """Return tROAS Log rows with applied_date within the last `days` calendar days.

    Used by the audit to determine the cooldown set (campaigns to skip) and by
    the rollback monitor to find recently adjusted campaigns to watch.
    Returns an empty list if the tab does not exist or has no recent rows.
    """
    from datetime import datetime, timedelta, timezone

    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        return []

    svc = _service(credentials_path)

    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="tROAS Log!A:L",
        ).execute()
    except Exception:
        return []

    rows = result.get("values", [])
    if len(rows) < 2:
        return []

    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    header = rows[0]
    recent: list[dict] = []

    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        record = dict(zip(header, padded))
        applied = record.get("Applied Date", "")
        if applied >= cutoff:
            recent.append({
                "applied_date": applied,
                "customer_id": record.get("Customer ID", ""),
                "campaign_id": record.get("Campaign ID", ""),
                "campaign_name": record.get("Campaign Name", ""),
                "account_name": record.get("Account Name", ""),
                "direction": record.get("Direction", ""),
                "old_target_roas": record.get("Old tROAS (%)", "0"),
                "new_target_roas": record.get("New tROAS (%)", "0"),
                "change_pp": record.get("Change (pp)", "0"),
                "l7_spend": record.get("L7 Spend ($)", "0"),
            })

    return recent


# ---------------------------------------------------------------------------
# DataFeedWatch lookup tables
#
# DataFeedWatch can read a Google Sheet as a lookup table (match a feed field
# such as `sku` against the sheet and pull another column, e.g. custom_label_0).
# These helpers let the MCP own and update that sheet. The sheet is a separate
# spreadsheet (DFW_LOOKUP_SHEET_ID), shared as Editor with the service account
# and connected inside DataFeedWatch as a Google Sheet lookup source.
# ---------------------------------------------------------------------------

def _ensure_named_tab(svc, spreadsheet_id: str, tab: str) -> int:
    """Return the sheetId for `tab`, creating the tab if it does not exist."""
    sheet_map = _sheet_map(svc, spreadsheet_id)
    if tab in sheet_map:
        return sheet_map[tab]
    _batch(svc, spreadsheet_id, [{"addSheet": {"properties": {"title": tab}}}])
    return _sheet_map(svc, spreadsheet_id)[tab]


def write_dfw_lookup_table(
    rows: list[dict],
    spreadsheet_id: str,
    tab: str = "Sheet1",
    clear: bool = True,
) -> str:
    """Overwrite a DataFeedWatch lookup tab with `rows` (a list of flat dicts).

    The header is the ordered union of keys across rows, so every row should
    share the same keys (e.g. {"sku": "835470", "custom_label_0": "pws_stage1_3m"}).
    Returns the tab URL. Raises EnvironmentError if creds are not configured and
    ValueError if rows is empty.
    """
    if not rows:
        raise ValueError("rows is empty; nothing to write")

    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    sheet_id = _ensure_named_tab(svc, spreadsheet_id, tab)

    # Ordered union of keys -> header
    header: list[str] = []
    for r in rows:
        for k in r:
            if k not in header:
                header.append(k)

    values = [header] + [[str(r.get(k, "")) for k in header] for r in rows]

    if clear:
        _clear(svc, spreadsheet_id, tab)
    _write(svc, spreadsheet_id, f"{tab}!A1", values)

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"


def read_dfw_lookup_table(spreadsheet_id: str, tab: str = "Sheet1") -> list[dict]:
    """Read a DataFeedWatch lookup tab back as a list of dicts (header-keyed).

    Returns an empty list if the tab is missing or has no data rows.
    """
    credentials_path = os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH", "").strip()
    if not credentials_path and not os.environ.get("GOOGLE_ADS_SERVICE_ACCOUNT_JSON"):
        raise EnvironmentError("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_PATH is not set.")

    svc = _service(credentials_path)
    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=tab,
        ).execute()
    except Exception:
        return []

    rows = result.get("values", [])
    if len(rows) < 2:
        return []

    header = rows[0]
    out: list[dict] = []
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        out.append(dict(zip(header, padded)))
    return out
