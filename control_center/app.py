"""Ads Control Center web app.

Local-only Starlette app (binds 127.0.0.1) serving the flag review queue.
Sync endpoints run in the threadpool; each request opens its own SQLite
connection. All writes to Google Ads go through commit_staged_changes which
audit-logs before and after every mutate call and appends to the Sheets
tROAS / Budget Log tabs so the existing audit flows share cooldown state.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from control_center import store
from control_center.detectors import run_detectors
from control_center.shopify import load_store_registry

load_dotenv()

HERE = Path(__file__).parent
templates = Environment(
    loader=FileSystemLoader(HERE / "templates"),
    autoescape=select_autoescape(["html"]),
)

TROAS_COOLDOWN_DAYS = 3

_TYPE_LABELS = {
    "troas_drift": "tROAS drift",
    "budget_cap": "Budget opportunity",
    "budget_constrained": "Budget constrained",
    "budget_excess": "Excess budget",
    "spend_anomaly": "Spend anomaly",
}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Tab -> flag types shown there.
_TABS = {
    "performance": ("troas_drift", "spend_anomaly"),
    "budgets": ("budget_constrained", "budget_excess", "budget_cap"),
}

# Negative-keyword audit tranches: label + display color, in review order.
_TRANCHE_META = {
    "competitor_brand": ("Competitor / retailer brands", "bg-red-lt"),
    "off_product": ("Off-category terms", "bg-orange-lt"),
    "foreign_language": ("Out-of-language queries", "bg-purple-lt"),
    "below_breakeven": ("Converts below breakeven", "bg-yellow-lt"),
    "non_branded": ("Non-branded queries", "bg-cyan-lt"),
    "zero_conv_spend": ("Spend, zero conversions", "bg-azure-lt"),
    "ngram_waste": ("Diffuse waste (word rollup)", "bg-pink-lt"),
}
_TRANCHE_DISPLAY_ORDER = list(_TRANCHE_META.keys())


def _render(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(templates.get_template(name).render(**ctx))


def _conn() -> sqlite3.Connection:
    return store.connect()


# ---------------------------------------------------------------------------
# Shared lookups
# ---------------------------------------------------------------------------

def account_names() -> dict[str, str]:
    return {s.ads_customer_id: s.ads_name for s in load_store_registry()}


def shopify_key_by_customer() -> dict[str, str]:
    return {s.ads_customer_id: s.shopify_key for s in load_store_registry()}


def mer_by_account(conn: sqlite3.Connection) -> dict[str, dict]:
    """Trailing 7 full days MER per account from local tables."""
    start = (date.today() - timedelta(days=7)).isoformat()
    end = (date.today() - timedelta(days=1)).isoformat()
    cost_rows = {
        r["customer_id"]: r["cost"]
        for r in conn.execute(
            "SELECT customer_id, SUM(cost) AS cost FROM daily_metrics "
            "WHERE date BETWEEN ? AND ? GROUP BY customer_id",
            (start, end),
        )
    }
    sales_rows = {
        r["shopify_key"]: r["net_sales"]
        for r in conn.execute(
            "SELECT shopify_key, SUM(net_sales) AS net_sales FROM store_sales "
            "WHERE date BETWEEN ? AND ? GROUP BY shopify_key",
            (start, end),
        )
    }
    key_map = shopify_key_by_customer()
    out: dict[str, dict] = {}
    for customer_id, cost in cost_rows.items():
        net_sales = sales_rows.get(key_map.get(customer_id, ""), 0.0)
        if net_sales > 0:
            mer = cost / net_sales * 100
            if mer < 5:
                status = "Strong"
            elif mer < 10:
                status = "Good"
            elif mer < 20:
                status = "Watch"
            else:
                status = "Poor"
            out[customer_id] = {"mer": round(mer, 1), "status": status}
        elif cost > 0:
            out[customer_id] = {"mer": None, "status": "No sales data"}
    return out


def _polyline(values: list[float], width: int, height: int, stroke: str) -> str:
    """Build one normalized SVG polyline, scaled to its own min/max. Empty if flat."""
    pts = [v for v in values if v is not None]
    if len(pts) < 2:
        return ""
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0
    n = len(values)
    step = width / (n - 1)
    coords = []
    for i, v in enumerate(values):
        v = v if v is not None else lo
        x = i * step
        y = height - 2 - ((v - lo) / span) * (height - 4)
        coords.append(f"{x:.1f},{y:.1f}")
    return f'<polyline points="{" ".join(coords)}" fill="none" stroke="{stroke}" stroke-width="1.5"/>'


def sparkline(
    values: list[float],
    width: int = 140,
    height: int = 30,
    overlay: list[float] | None = None,
) -> str:
    """Inline SVG sparkline. Returns empty string for flat or missing series.

    The primary series renders in blue. An optional overlay series (e.g. revenue)
    renders in yellow, scaled to its own range so both trends stay visible.
    """
    primary = _polyline(values, width, height, "#7aa2f7")
    if not primary:
        return ""
    inner = primary
    if overlay is not None:
        inner += _polyline(overlay, width, height, "#e0af68")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f"{inner}"
        f"</svg>"
    )


def campaign_series(conn: sqlite3.Connection, customer_id: str, campaign_id: str, days: int = 30):
    rows = conn.execute(
        "SELECT date, cost, conv_value, conversions FROM daily_metrics "
        "WHERE customer_id=? AND campaign_id=? AND date >= date('now', ?) "
        "ORDER BY date",
        (customer_id, campaign_id, f"-{days} days"),
    ).fetchall()
    return rows


def load_flags(conn: sqlite3.Connection, types: tuple, include_snoozed: bool = False):
    statuses = ("open", "snoozed") if include_snoozed else ("open",)
    placeholders_s = ",".join("?" * len(statuses))
    placeholders_t = ",".join("?" * len(types))
    rows = conn.execute(
        f"SELECT * FROM flags WHERE status IN ({placeholders_s}) "
        f"AND type IN ({placeholders_t}) ORDER BY last_seen DESC",
        (*statuses, *types),
    ).fetchall()
    flags = []
    staged_pairs = {
        (r["flag_id"], r["ad_group_id"] or "")
        for r in conn.execute(
            "SELECT flag_id, ad_group_id FROM staged_changes WHERE status='staged'"
        )
    }
    for r in rows:
        f = dict(r)
        f["payload"] = json.loads(r["payload"])
        f["type_label"] = _TYPE_LABELS.get(r["type"], r["type"])
        f["is_staged"] = (r["id"], "") in staged_pairs
        f["staged_adgroup_ids"] = {
            ag_id for flag_id, ag_id in staged_pairs if flag_id == r["id"] and ag_id
        }
        flags.append(f)
    return flags


def _attach_l7(conn: sqlite3.Connection, flags: list[dict]) -> None:
    """Attach uniform L7 spend and revenue from daily_metrics to every flag."""
    l7 = {
        (r["customer_id"], r["campaign_id"]): (r["cost"], r["value"])
        for r in conn.execute(
            "SELECT customer_id, campaign_id, SUM(cost) AS cost, SUM(conv_value) AS value "
            "FROM daily_metrics WHERE date >= date('now','-7 days') "
            "GROUP BY customer_id, campaign_id"
        )
    }
    for f in flags:
        cost, value = l7.get((f["customer_id"], f["campaign_id"]), (0.0, 0.0))
        f["l7_spend"] = cost
        f["l7_revenue"] = value


def _flag_sort_key(f: dict):
    return (
        f["payload"].get("tier", 2),
        -(f.get("l7_spend") or 0),
        _SEVERITY_ORDER.get(f["severity"], 3),
    )


# ---------------------------------------------------------------------------
# Queue and detail
# ---------------------------------------------------------------------------

def queue(request: Request):
    conn = _conn()
    try:
        show_snoozed = request.query_params.get("snoozed") == "1"
        tab = request.query_params.get("tab", "performance")
        if tab not in _TABS:
            tab = "performance"
        flags = load_flags(conn, _TABS[tab], include_snoozed=show_snoozed)
        names = account_names()
        mer = mer_by_account(conn)
        _attach_l7(conn, flags)

        for f in flags:
            series = campaign_series(conn, f["customer_id"], f["campaign_id"], days=30)
            f["spark"] = sparkline(
                [r["cost"] for r in series],
                overlay=[r["conv_value"] for r in series],
            )

        groups: dict[str, list] = {}
        for f in flags:
            groups.setdefault(f["customer_id"], []).append(f)
        for cid in groups:
            groups[cid].sort(key=_flag_sort_key)

        ordered = sorted(
            groups.items(),
            key=lambda kv: (
                kv[1][0]["payload"].get("tier", 2),
                -sum(x.get("l7_spend") or 0 for x in kv[1]),
            ),
        )
        accounts = [
            {
                "customer_id": cid,
                "name": names.get(cid, cid),
                "tier": items[0]["payload"].get("tier", 2),
                "mer": mer.get(cid),
                "flags": items,
            }
            for cid, items in ordered
        ]
        staged_count = conn.execute(
            "SELECT COUNT(*) FROM staged_changes WHERE status='staged'"
        ).fetchone()[0]
        snoozed_count = conn.execute(
            "SELECT COUNT(*) FROM flags WHERE status='snoozed'"
        ).fetchone()[0]
        tab_counts = {
            name: conn.execute(
                f"SELECT COUNT(*) FROM flags WHERE status='open' "
                f"AND type IN ({','.join('?' * len(types))})",
                types,
            ).fetchone()[0]
            for name, types in _TABS.items()
        }
        last_pull = conn.execute(
            "SELECT * FROM pulls ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _render(
            "queue.html",
            accounts=accounts,
            total_flags=len(flags),
            staged_count=staged_count,
            snoozed_count=snoozed_count,
            show_snoozed=show_snoozed,
            tab=tab,
            tab_counts=tab_counts,
            last_pull=dict(last_pull) if last_pull else None,
        )
    finally:
        conn.close()


def flag_detail(request: Request):
    flag_id = int(request.path_params["flag_id"])
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM flags WHERE id=?", (flag_id,)).fetchone()
        if not row:
            return HTMLResponse("Flag not found", status_code=404)
        payload = json.loads(row["payload"])
        series = campaign_series(conn, row["customer_id"], row["campaign_id"], days=30)
        costs = [r["cost"] for r in series]
        roas = [
            (r["conv_value"] / r["cost"] * 100) if r["cost"] > 0 else None for r in series
        ]
        l7 = [r for r in series if r["date"] >= (date.today() - timedelta(days=7)).isoformat()]
        l30_cost = sum(costs)
        l30_value = sum(r["conv_value"] for r in series)
        l7_cost = sum(r["cost"] for r in l7)
        l7_value = sum(r["conv_value"] for r in l7)
        mer = mer_by_account(conn).get(row["customer_id"])
        recent_changes = conn.execute(
            "SELECT * FROM staged_changes WHERE customer_id=? AND campaign_id=? "
            "AND status='committed' ORDER BY created_at DESC LIMIT 5",
            (row["customer_id"], row["campaign_id"]),
        ).fetchall()
        return _render(
            "detail.html",
            flag=dict(row),
            payload=payload,
            spark_cost=sparkline(costs, width=320, height=44),
            spark_roas=sparkline(roas, width=320, height=44),
            l7={"cost": l7_cost, "value": l7_value, "roas": (l7_value / l7_cost * 100) if l7_cost else 0},
            l30={"cost": l30_cost, "value": l30_value, "roas": (l30_value / l30_cost * 100) if l30_cost else 0},
            mer=mer,
            account_name=account_names().get(row["customer_id"], row["customer_id"]),
            recent_changes=[dict(r) for r in recent_changes],
        )
    finally:
        conn.close()


def snooze(request: Request):
    flag_id = int(request.path_params["flag_id"])
    days = int(request.query_params.get("days", "1"))
    if days not in (1, 3, 7):
        days = 1
    until = (datetime.now() + timedelta(days=days)).isoformat(timespec="seconds")
    conn = _conn()
    try:
        with conn:
            conn.execute(
                "UPDATE flags SET status='snoozed', snooze_until=? WHERE id=? AND status='open'",
                (until, flag_id),
            )
        return HTMLResponse(
            f'<tr class="muted-row"><td colspan="6">Snoozed for {days} day(s).</td></tr>'
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Staging
# ---------------------------------------------------------------------------

def _troas_cooldown_hit(conn: sqlite3.Connection, customer_id: str, campaign_id: str) -> str:
    """Non-empty reason string when the campaign had a tROAS change in the window."""
    cutoff = (datetime.now() - timedelta(days=TROAS_COOLDOWN_DAYS)).isoformat(timespec="seconds")
    local = conn.execute(
        "SELECT created_at FROM staged_changes WHERE customer_id=? AND campaign_id=? "
        "AND change_type='troas' AND status='committed' AND created_at >= ?",
        (customer_id, campaign_id, cutoff),
    ).fetchone()
    if local:
        return f"changed via control center on {local['created_at'][:10]}"

    spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
    if spreadsheet_id:
        try:
            from ads_mcp.sheets import read_troas_log_recent

            for r in read_troas_log_recent(spreadsheet_id, days=TROAS_COOLDOWN_DAYS):
                if r.get("customer_id") == customer_id and r.get("campaign_id") == campaign_id:
                    return f"changed via tROAS audit on {r.get('applied_date', '')[:10]}"
        except Exception as exc:
            print(f"[control_center.app] cooldown sheet check failed: {exc}", file=sys.stderr)
    return ""


async def stage(request: Request):
    flag_id = int(request.path_params["flag_id"])
    form = await request.form()
    new_value = float(form.get("new_value", "0") or 0)
    override = form.get("override") == "1"
    ad_group_id = (form.get("ad_group_id") or "").strip()

    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM flags WHERE id=?", (flag_id,)).fetchone()
        if not row or new_value <= 0:
            return HTMLResponse("Invalid flag or value", status_code=400)
        payload = json.loads(row["payload"])

        ad_group_name = ""
        if row["type"] == "troas_drift" and ad_group_id:
            change_type = "troas_adgroup"
            ag = next(
                (a for a in payload.get("adgroups", []) if a["ad_group_id"] == ad_group_id),
                None,
            )
            if not ag:
                return HTMLResponse("Unknown ad group for this flag", status_code=400)
            current = ag["current_troas_pct"]
            ad_group_name = ag["ad_group_name"]
        elif row["type"] == "troas_drift":
            change_type = "troas"
            current = payload.get("current_troas_pct")
        else:
            change_type = "budget"
            current = payload.get("daily_budget")

        if change_type in ("troas", "troas_adgroup"):
            reason = _troas_cooldown_hit(conn, row["customer_id"], row["campaign_id"])
            if reason and not override:
                return _render(
                    "cooldown_warning.html",
                    flag_id=flag_id,
                    new_value=new_value,
                    ad_group_id=ad_group_id,
                    reason=reason,
                    cooldown_days=TROAS_COOLDOWN_DAYS,
                )

        with conn:
            conn.execute(
                """
                INSERT INTO staged_changes
                    (flag_id, customer_id, campaign_id, campaign_name,
                     ad_group_id, ad_group_name, change_type,
                     current_value, new_value, cooldown_override, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'staged')
                """,
                (
                    flag_id,
                    row["customer_id"],
                    row["campaign_id"],
                    payload.get("campaign_name", ""),
                    ad_group_id or None,
                    ad_group_name or None,
                    change_type,
                    current,
                    new_value,
                    1 if override else 0,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
        unit = "%" if change_type.startswith("troas") else "/day $"
        return HTMLResponse(
            f'<span class="badge bg-green-lt">Staged: {current} to {new_value} {unit}'
            f'{" (cooldown override)" if override else ""}</span>'
        )
    finally:
        conn.close()


def discard_staged(request: Request):
    staged_id = int(request.path_params["staged_id"])
    conn = _conn()
    try:
        with conn:
            conn.execute(
                "UPDATE staged_changes SET status='discarded' WHERE id=? AND status='staged'",
                (staged_id,),
            )
        return RedirectResponse("/review", status_code=303)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Review and commit
# ---------------------------------------------------------------------------

def review(request: Request):
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM staged_changes WHERE status='staged' ORDER BY created_at"
        ).fetchall()
        names = account_names()
        staged = []
        for r in rows:
            d = dict(r)
            d["account_name"] = names.get(r["customer_id"], r["customer_id"])
            staged.append(d)
        return _render("review.html", staged=staged)
    finally:
        conn.close()


def _audit_db() -> sqlite3.Connection:
    path = os.environ.get("ADS_MCP_AUDIT_LOG_PATH", str(store.PROJECT_ROOT / "audit.db"))
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS control_center_change_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_before TEXT NOT NULL,
            ts_after TEXT,
            customer_id TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            campaign_name TEXT,
            change_type TEXT NOT NULL,
            old_value REAL,
            new_value REAL,
            staged_id INTEGER,
            flag_id INTEGER,
            cooldown_override INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            error TEXT
        )
        """
    )
    return conn


def commit(request: Request):
    """Apply every staged change. Audit before and after each mutate call."""
    from ads_mcp.client import get_client
    from ads_mcp.proposals.budget import apply_budget_change
    from ads_mcp.proposals.troas import apply_troas_adgroup_change, apply_troas_change

    conn = _conn()
    audit = _audit_db()
    results = []
    try:
        client = get_client()
        names = account_names()
        spreadsheet_id = os.environ.get("GOOGLE_ADS_SHEETS_DASHBOARD_ID", "").strip()
        troas_log_rows, budget_log_rows = [], []

        rows = conn.execute(
            "SELECT * FROM staged_changes WHERE status='staged' ORDER BY created_at"
        ).fetchall()

        for r in rows:
            flag = conn.execute("SELECT * FROM flags WHERE id=?", (r["flag_id"],)).fetchone()
            payload = json.loads(flag["payload"]) if flag else {}

            # Audit BEFORE the API call so partial failures are visible.
            cur = audit.execute(
                """
                INSERT INTO control_center_change_log
                    (ts_before, customer_id, campaign_id, campaign_name, change_type,
                     old_value, new_value, staged_id, flag_id, cooldown_override, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'attempting')
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    r["customer_id"], r["campaign_id"], r["campaign_name"],
                    r["change_type"], r["current_value"], r["new_value"],
                    r["id"], r["flag_id"], r["cooldown_override"],
                ),
            )
            audit.commit()
            audit_id = cur.lastrowid

            if r["change_type"] in ("troas", "troas_adgroup"):
                change_pp = int(abs((r["new_value"] or 0) - (r["current_value"] or 0)))
                if r["change_type"] == "troas_adgroup":
                    result = apply_troas_adgroup_change(
                        client,
                        customer_id=r["customer_id"],
                        campaign_id=r["campaign_id"],
                        campaign_name=r["campaign_name"],
                        ad_group_id=r["ad_group_id"],
                        current_target_roas_pct=r["current_value"] or 0,
                        proposed_target_roas_pct=r["new_value"],
                        change_pp=change_pp,
                    )
                else:
                    result = apply_troas_change(
                        client,
                        customer_id=r["customer_id"],
                        campaign_id=r["campaign_id"],
                        campaign_name=r["campaign_name"],
                        current_target_roas_pct=r["current_value"] or 0,
                        proposed_target_roas_pct=r["new_value"],
                        change_pp=change_pp,
                        bidding_type=payload.get("bidding_strategy", "TARGET_ROAS"),
                    )
                ok = result["status"] == "applied"
                error = result["error"]
                if ok:
                    direction = payload.get("direction", "")
                    if direction == "MIXED":
                        direction = (
                            "TIGHTEN"
                            if (r["new_value"] or 0) > (r["current_value"] or 0)
                            else "LOOSEN"
                        )
                    troas_log_rows.append({
                        "applied_date": date.today().isoformat(),
                        "customer_id": r["customer_id"],
                        "campaign_id": r["campaign_id"],
                        "campaign_name": r["campaign_name"],
                        "ad_group_id": r["ad_group_id"] or "",
                        "ad_group_name": r["ad_group_name"] or "",
                        "account_name": names.get(r["customer_id"], ""),
                        "direction": direction,
                        "old_target_roas": r["current_value"],
                        "new_target_roas": r["new_value"],
                        "change_pp": change_pp,
                        "l7_spend": payload.get("l7_spend", ""),
                    })
            else:
                budget_id = payload.get("budget_id", "")
                if not budget_id:
                    ok, error = False, "No budget_id on flag payload; re-pull data first."
                else:
                    result = apply_budget_change(
                        client,
                        customer_id=r["customer_id"],
                        campaign_id=r["campaign_id"],
                        campaign_name=r["campaign_name"],
                        budget_id=budget_id,
                        old_budget=r["current_value"] or 0,
                        new_budget=r["new_value"],
                    )
                    ok = result["status"] == "applied"
                    error = result["error"]
                if ok:
                    change = (r["new_value"] or 0) - (r["current_value"] or 0)
                    budget_log_rows.append({
                        "applied_date": date.today().isoformat(),
                        "customer_id": r["customer_id"],
                        "campaign_id": r["campaign_id"],
                        "campaign_name": r["campaign_name"],
                        "account_name": names.get(r["customer_id"], ""),
                        "old_budget": r["current_value"],
                        "new_budget": r["new_value"],
                        "change": round(change, 2),
                        "direction": "UP" if change >= 0 else "DOWN",
                        "status": "applied",
                        "error": "",
                    })

            # Audit AFTER.
            audit.execute(
                "UPDATE control_center_change_log SET ts_after=?, status=?, error=? WHERE id=?",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    "applied" if ok else "error",
                    error,
                    audit_id,
                ),
            )
            audit.commit()

            with conn:
                conn.execute(
                    "UPDATE staged_changes SET status=?, result=? WHERE id=?",
                    ("committed" if ok else "failed", json.dumps({"error": error}), r["id"]),
                )
                if ok:
                    conn.execute(
                        "UPDATE flags SET status='committed' WHERE id=?", (r["flag_id"],)
                    )
            results.append({
                "account_name": names.get(r["customer_id"], r["customer_id"]),
                "campaign_name": r["campaign_name"],
                "ad_group_name": r["ad_group_name"],
                "change_type": r["change_type"],
                "current_value": r["current_value"],
                "new_value": r["new_value"],
                "ok": ok,
                "error": error,
            })

        # Shared logs for cooldown visibility across flows. Failure to append
        # never undoes an applied change; it is surfaced in the results.
        sheet_errors = []
        if spreadsheet_id and troas_log_rows:
            try:
                from ads_mcp.sheets import append_troas_log

                append_troas_log(troas_log_rows, spreadsheet_id)
            except Exception as exc:
                sheet_errors.append(f"tROAS Log append failed: {exc}")
        if spreadsheet_id and budget_log_rows:
            try:
                from ads_mcp.sheets import append_budget_log

                append_budget_log(budget_log_rows, spreadsheet_id)
            except Exception as exc:
                sheet_errors.append(f"Budget Log append failed: {exc}")

        return _render("commit_results.html", results=results, sheet_errors=sheet_errors)
    finally:
        audit.close()
        conn.close()


# ---------------------------------------------------------------------------
# History and manual pull
# ---------------------------------------------------------------------------

def history(request: Request):
    conn = _conn()
    try:
        pulls = [dict(r) for r in conn.execute(
            "SELECT * FROM pulls ORDER BY id DESC LIMIT 30"
        )]
        changes = [dict(r) for r in conn.execute(
            "SELECT * FROM staged_changes WHERE status IN ('committed','failed') "
            "ORDER BY created_at DESC LIMIT 50"
        )]
        names = account_names()
        for c in changes:
            c["account_name"] = names.get(c["customer_id"], c["customer_id"])
        return _render("history.html", pulls=pulls, changes=changes)
    finally:
        conn.close()


def manual_pull(request: Request):
    from ads_mcp.client import get_client

    conn = _conn()
    try:
        store.run_data_pull(conn, get_client(), days=3, kind="manual")
        run_detectors(conn)
        return RedirectResponse("/", status_code=303)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Negatives tab (wasted-keyword audit)
# ---------------------------------------------------------------------------

def _negatives_row_html(prop: dict) -> str:
    """Inline swap fragment for a proposal after approve / skip / undo.

    Decided states (approved, skipped) show a badge + undo. The open state
    restores the Approve / Skip buttons so undo returns to an actionable row.
    """
    pid = prop["id"]
    if prop["status"] in ("approved", "skipped", "protected"):
        label = {"approved": "Approved", "skipped": "Skipped", "protected": "Protected"}[prop["status"]]
        color = {"approved": "bg-green-lt", "skipped": "bg-secondary-lt",
                 "protected": "bg-teal-lt"}[prop["status"]]
        inner = (
            f'<span class="badge {color}">{label}</span> '
            f'<button class="btn btn-sm btn-ghost-secondary px-2" '
            f'hx-post="/negatives/{pid}/open" hx-target="#neg-actions-{pid}" '
            f'hx-swap="outerHTML">undo</button>'
        )
    else:
        inner = (
            f'<button class="btn btn-sm btn-outline-success px-2" '
            f'hx-post="/negatives/{pid}/approve" hx-target="#neg-actions-{pid}" '
            f'hx-swap="outerHTML">Approve</button>'
            f'<button class="btn btn-sm btn-ghost-secondary px-2" '
            f'hx-post="/negatives/{pid}/skip" hx-target="#neg-actions-{pid}" '
            f'hx-swap="outerHTML">Skip</button>'
            f'<button class="btn btn-sm btn-outline-teal px-2" '
            f'title="Keep this term: add it to the account protect list so it never resurfaces" '
            f'hx-post="/negatives/{pid}/protect" hx-target="#neg-actions-{pid}" '
            f'hx-swap="outerHTML">Protect</button>'
        )
    return f'<div id="neg-actions-{pid}" class="btn-list flex-nowrap">{inner}</div>'


def negatives(request: Request):
    show = request.query_params.get("show", "open")
    status = "approved" if show == "approved" else "open"
    selected = (request.query_params.get("account") or "").strip()
    conn = _conn()
    try:
        names = account_names()

        # Lightweight per-account index (counts only, no row payload) so the
        # landing page stays small even with thousands of proposals.
        index_rows = conn.execute(
            "SELECT customer_id, account_name, COUNT(*) AS n, "
            "ROUND(SUM(l_spend), 2) AS spend FROM negative_proposals "
            "WHERE status=? GROUP BY customer_id ORDER BY spend DESC",
            (status,),
        ).fetchall()
        approved_by_acct = {
            r["customer_id"]: r["n"]
            for r in conn.execute(
                "SELECT customer_id, COUNT(*) AS n FROM negative_proposals "
                "WHERE status='approved' GROUP BY customer_id"
            )
        }
        account_index = [
            {
                "customer_id": r["customer_id"],
                "name": r["account_name"] or names.get(r["customer_id"], r["customer_id"]),
                "count": r["n"],
                "spend": r["spend"] or 0.0,
                "approved_count": approved_by_acct.get(r["customer_id"], 0),
            }
            for r in index_rows
        ]

        # Detail: only the selected account's rows are rendered.
        detail = None
        if selected:
            props = [
                p for p in store.negative_proposals(conn, status=status)
                if p["customer_id"] == selected
            ]
            tranches: dict[str, dict] = {}
            total_spend = 0.0
            for p in props:
                tr = tranches.setdefault(p["tranche"], {
                    "tranche": p["tranche"],
                    "label": _TRANCHE_META.get(p["tranche"], (p["tranche"], "bg-secondary-lt"))[0],
                    "color": _TRANCHE_META.get(p["tranche"], (p["tranche"], "bg-secondary-lt"))[1],
                    "rows": [],
                    "spend": 0.0,
                })
                tr["rows"].append(p)
                tr["spend"] += p["l_spend"] or 0.0
                total_spend += p["l_spend"] or 0.0
            detail = {
                "customer_id": selected,
                "name": names.get(selected, selected),
                "total": len(props),
                "total_spend": total_spend,
                "approved_count": approved_by_acct.get(selected, 0),
                "tranche_list": [tranches[t] for t in _TRANCHE_DISPLAY_ORDER if t in tranches],
            }

        last_audit = conn.execute(
            "SELECT MAX(created_at) AS ts, COUNT(*) AS n FROM negative_proposals"
        ).fetchone()
        return _render(
            "negatives.html",
            account_index=account_index,
            detail=detail,
            selected=selected,
            show=show,
            open_count=store.count_open_negatives(conn),
            approved_count=store.count_approved_negatives(conn),
            staged_count=conn.execute(
                "SELECT COUNT(*) FROM staged_changes WHERE status='staged'"
            ).fetchone()[0],
            neg_open_count=store.count_open_negatives(conn),
            last_audit=dict(last_audit) if last_audit and last_audit["ts"] else None,
        )
    finally:
        conn.close()


def set_negative(request: Request):
    prop_id = int(request.path_params["prop_id"])
    action = request.path_params["action"]
    status = {"approve": "approved", "skip": "skipped", "open": "open",
              "protect": "protected"}.get(action)
    if status is None:
        return HTMLResponse("bad action", status_code=400)
    conn = _conn()
    try:
        # Undo from Protected must also drop the protect term, or the next audit
        # would silently re-hide it.
        if action == "open":
            prior = conn.execute(
                "SELECT customer_id, keyword, status FROM negative_proposals WHERE id=?",
                (prop_id,),
            ).fetchone()
            if prior and prior["status"] == "protected":
                store.remove_protect_term(conn, prior["customer_id"], prior["keyword"])

        prop = store.set_negative_status(conn, prop_id, status)
        if not prop:
            return HTMLResponse("not found", status_code=404)

        # Protect: record the term (never re-proposed) and clear its open siblings.
        if action == "protect":
            term = (prop.get("keyword") or "").strip()
            store.add_protect_term(conn, prop["customer_id"], term)
            store.protect_open_matching(conn, prop["customer_id"], term)

        return HTMLResponse(_negatives_row_html(prop))
    finally:
        conn.close()


async def approve_tranche(request: Request):
    form = await request.form()
    customer_id = str(form.get("customer_id", ""))
    tranche = str(form.get("tranche", ""))
    conn = _conn()
    try:
        store.approve_negative_tranche(conn, customer_id, tranche)
        return RedirectResponse(f"/negatives?account={customer_id}#detail", status_code=303)
    finally:
        conn.close()


async def run_negatives_audit(request: Request):
    from ads_mcp.client import get_client
    from control_center.waste import run_waste_audit

    form = await request.form()
    customer_id = str(form.get("customer_id") or "").strip()
    date_range = str(form.get("date_range") or "LAST_30_DAYS").strip()
    customer_ids = [customer_id] if customer_id else None

    conn = _conn()
    try:
        run_waste_audit(conn, get_client(), date_range=date_range, customer_ids=customer_ids)
        return RedirectResponse("/negatives", status_code=303)
    finally:
        conn.close()


async def commit_negatives(request: Request):
    """Apply approved negatives to Google Ads via the account's shared list.

    One shared-list mutate batch per account. Audits before and after each
    account, mirroring the tROAS/budget commit path.
    """
    from ads_mcp.client import get_client
    from ads_mcp.proposals.negatives import DEFAULT_LIST_NAME, apply_negatives

    form = await request.form()
    only_customer = str(form.get("customer_id") or "").strip()

    conn = _conn()
    audit = _audit_db()
    results = []
    try:
        client = get_client()
        names = account_names()

        if only_customer:
            customer_ids = [only_customer]
        else:
            customer_ids = [
                r["customer_id"] for r in conn.execute(
                    "SELECT DISTINCT customer_id FROM negative_proposals WHERE status='approved'"
                )
            ]

        for cid in customer_ids:
            approved = store.approved_negatives_for(conn, cid)
            if not approved:
                continue
            keywords = [
                {"keyword": p["keyword"], "match_type": p["match_type"]} for p in approved
            ]

            cur = audit.execute(
                """
                INSERT INTO control_center_change_log
                    (ts_before, customer_id, campaign_id, campaign_name, change_type,
                     old_value, new_value, status)
                VALUES (?, ?, '', ?, 'negative_keywords', NULL, ?, 'attempting')
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    cid, DEFAULT_LIST_NAME, float(len(keywords)),
                ),
            )
            audit.commit()
            audit_id = cur.lastrowid

            res = apply_negatives(client, cid, keywords, list_name=DEFAULT_LIST_NAME)

            # Persist per-proposal outcome.
            outcome_by_kw = {
                (r["keyword"].lower(), r["match_type"]): r for r in res["results"]
            }
            for p in approved:
                r = outcome_by_kw.get((p["keyword"].lower(), p["match_type"]))
                if r and r["status"] in ("added", "duplicate"):
                    store.mark_negative_committed(conn, p["id"], "committed", json.dumps(r))
                else:
                    err = (r or {}).get("error", "") or res["error"] or "not applied"
                    store.mark_negative_committed(conn, p["id"], "failed", json.dumps({"error": err}))

            top_error = res["error"]
            ok = not top_error and res["errors"] == 0
            audit.execute(
                "UPDATE control_center_change_log SET ts_after=?, status=?, error=? WHERE id=?",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    "applied" if ok else "error",
                    top_error or (f"{res['errors']} keyword errors" if res["errors"] else ""),
                    audit_id,
                ),
            )
            audit.commit()

            results.append({
                "account_name": names.get(cid, cid),
                "customer_id": cid,
                "added": res["added"],
                "duplicates": res["duplicates"],
                "errors": res["errors"],
                "shared_set_created": res["shared_set_created"],
                "attached": len(res["attached_campaign_ids"]),
                "error": top_error,
            })

        return _render("negatives_commit.html", results=results)
    finally:
        audit.close()
        conn.close()


import contextlib


@contextlib.asynccontextmanager
async def _lifespan(app):
    import asyncio

    from control_center.scheduler import scheduler_loop

    task = asyncio.create_task(scheduler_loop())
    try:
        yield
    finally:
        task.cancel()


routes = [
    Route("/", queue),
    Route("/flags/{flag_id:int}/detail", flag_detail),
    Route("/flags/{flag_id:int}/snooze", snooze, methods=["POST"]),
    Route("/flags/{flag_id:int}/stage", stage, methods=["POST"]),
    Route("/staged/{staged_id:int}/discard", discard_staged, methods=["POST"]),
    Route("/review", review),
    Route("/commit", commit, methods=["POST"]),
    Route("/history", history),
    Route("/pull", manual_pull, methods=["POST"]),
    Route("/negatives", negatives),
    Route("/negatives/run", run_negatives_audit, methods=["POST"]),
    Route("/negatives/approve_tranche", approve_tranche, methods=["POST"]),
    Route("/negatives/commit", commit_negatives, methods=["POST"]),
    Route("/negatives/{prop_id:int}/{action}", set_negative, methods=["POST"]),
    Mount("/static", StaticFiles(directory=HERE / "static"), name="static"),
]

app = Starlette(routes=routes, lifespan=_lifespan)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8770)
