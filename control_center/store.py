"""SQLite data store for the control center.

Owns control_center.db at the project root: daily campaign metrics (180-day
backfill plus scheduled pulls), daily store net sales, flags, staged changes,
and pull records. See CONTROL_CENTER_SPEC.md for the data model.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from google.ads.googleads.client import GoogleAdsClient

from ads_mcp.reporting.queries import DAILY_CAMPAIGN_METRICS
from ads_mcp.reporting.utils import micros_to_currency

from control_center.shopify import fetch_all_store_sales, load_store_registry

PROJECT_ROOT = Path(__file__).parent.parent

# The DB must NOT live inside the Dropbox-synced project folder: cloud sync
# engines snapshot/restore the main db file underneath SQLite's WAL and
# silently lose committed writes (observed 2026-06-09 during the first
# backfill: the last 7 accounts' rows vanished after process exit).
_DEFAULT_DB = Path.home() / "Library" / "Application Support" / "ads-control-center" / "control_center.db"
DB_PATH = Path(os.environ.get("ADS_CC_DB_PATH", _DEFAULT_DB)).expanduser()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_metrics (
    customer_id     TEXT NOT NULL,
    campaign_id     TEXT NOT NULL,
    date            TEXT NOT NULL,
    campaign_name   TEXT,
    campaign_status TEXT,
    channel_type    TEXT,
    bidding_strategy TEXT,
    troas_target    REAL,
    budget_id       TEXT,
    budget_amount   REAL,
    cost            REAL NOT NULL DEFAULT 0,
    conversions     REAL NOT NULL DEFAULT 0,
    conv_value      REAL NOT NULL DEFAULT 0,
    pulled_at       TEXT,
    PRIMARY KEY (customer_id, campaign_id, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date);

-- Ad groups that carry their own tROAS (Standard Shopping pattern), with L7
-- and prior-week metrics. Campaigns appearing here never get campaign-level
-- tROAS suggestions; instead the queue renders these as indented editable
-- child rows. Fully replaced on every pull.
CREATE TABLE IF NOT EXISTS adgroup_troas (
    customer_id   TEXT NOT NULL,
    campaign_id   TEXT NOT NULL,
    ad_group_id   TEXT NOT NULL,
    ad_group_name TEXT,
    campaign_name TEXT,
    troas_target  REAL NOT NULL,
    l7_cost       REAL NOT NULL DEFAULT 0,
    l7_conv_value REAL NOT NULL DEFAULT 0,
    prior_cost    REAL NOT NULL DEFAULT 0,
    updated_at    TEXT,
    PRIMARY KEY (customer_id, campaign_id, ad_group_id)
);

CREATE TABLE IF NOT EXISTS store_sales (
    shopify_key TEXT NOT NULL,
    date        TEXT NOT NULL,
    net_sales   REAL NOT NULL DEFAULT 0,
    pulled_at   TEXT,
    PRIMARY KEY (shopify_key, date)
);

CREATE TABLE IF NOT EXISTS flags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,             -- troas_drift | budget_cap | spend_anomaly
    customer_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    severity    TEXT NOT NULL,             -- high | medium | low
    payload     TEXT NOT NULL,             -- JSON: metrics, suggestion, rationale
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',  -- open | snoozed | resolved | committed
    snooze_until TEXT,
    clean_pulls INTEGER NOT NULL DEFAULT 0     -- consecutive pulls with condition clear
);
-- At most one live flag per condition per campaign.
CREATE UNIQUE INDEX IF NOT EXISTS idx_flags_live
    ON flags(type, customer_id, campaign_id)
    WHERE status IN ('open', 'snoozed');

CREATE TABLE IF NOT EXISTS staged_changes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_id       INTEGER REFERENCES flags(id),
    customer_id   TEXT NOT NULL,
    campaign_id   TEXT NOT NULL,
    campaign_name TEXT,
    ad_group_id   TEXT,                     -- set for ad-group-level tROAS changes
    ad_group_name TEXT,
    change_type   TEXT NOT NULL,            -- troas | troas_adgroup | budget
    current_value REAL,
    new_value     REAL NOT NULL,
    cooldown_override INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'staged',  -- staged | committed | failed | discarded
    result        TEXT                       -- JSON: commit response or error
);

CREATE TABLE IF NOT EXISTS pulls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,               -- backfill | scheduled | manual
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    accounts_scanned INTEGER NOT NULL DEFAULT 0,
    stores_scanned   INTEGER NOT NULL DEFAULT 0,
    new_flags        INTEGER NOT NULL DEFAULT 0,
    resolved_flags   INTEGER NOT NULL DEFAULT 0,
    errors      TEXT                          -- JSON list of error strings
);

-- Wasted-keyword (negative-keyword) audit proposals, grouped by tranche.
-- One row per proposed negative (BROAD root or EXACT term). Open rows are
-- refreshed on each audit run; committed/skipped rows are preserved so a term
-- is not re-proposed after a decision. See ads_mcp/reporting/waste_audit.py.
CREATE TABLE IF NOT EXISTS negative_proposals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id   TEXT NOT NULL,
    account_name  TEXT,
    tranche       TEXT NOT NULL,            -- competitor_brand | off_product | foreign_language | below_breakeven | non_branded | zero_conv_spend
    keyword       TEXT NOT NULL,            -- the negative to add (root for BROAD, full term for EXACT)
    match_type    TEXT NOT NULL,            -- EXACT | BROAD
    example_term  TEXT,                      -- representative triggering search term
    matched_count INTEGER NOT NULL DEFAULT 1,
    l_spend       REAL NOT NULL DEFAULT 0,
    l_clicks      INTEGER NOT NULL DEFAULT 0,
    l_conversions REAL NOT NULL DEFAULT 0,
    l_conv_value  REAL NOT NULL DEFAULT 0,
    l_roas_pct    REAL NOT NULL DEFAULT 0,
    severity      TEXT NOT NULL DEFAULT 'low',
    rationale     TEXT,
    status        TEXT NOT NULL DEFAULT 'open',  -- open | approved | skipped | committed | failed
    audit_run_id  TEXT,
    created_at    TEXT NOT NULL,
    committed_at  TEXT,
    result        TEXT,                      -- JSON: commit response or error
    UNIQUE (customer_id, keyword, match_type)
);
CREATE INDEX IF NOT EXISTS idx_negprop_status ON negative_proposals(status);

CREATE TABLE IF NOT EXISTS negative_protect_terms (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  TEXT NOT NULL,
    term         TEXT NOT NULL,            -- lowercased; substring-matched by the audit engine
    created_at   TEXT NOT NULL,
    UNIQUE (customer_id, term)
);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for DBs created by earlier versions."""
    staged_cols = {r["name"] for r in conn.execute("PRAGMA table_info(staged_changes)")}
    if "ad_group_id" not in staged_cols:
        conn.execute("ALTER TABLE staged_changes ADD COLUMN ad_group_id TEXT")
        conn.execute("ALTER TABLE staged_changes ADD COLUMN ad_group_name TEXT")
    conn.execute("DROP TABLE IF EXISTS adgroup_troas_campaigns")
    conn.commit()


# ---------------------------------------------------------------------------
# Google Ads daily metrics
# ---------------------------------------------------------------------------

@dataclass
class DailyMetricRow:
    customer_id: str
    campaign_id: str
    date: str
    campaign_name: str
    campaign_status: str
    channel_type: str
    bidding_strategy: str
    troas_target: Optional[float]
    budget_id: Optional[str]
    budget_amount: Optional[float]
    cost: float
    conversions: float
    conv_value: float


def fetch_daily_campaign_metrics(
    client: GoogleAdsClient,
    customer_id: str,
    start: date,
    end: date,
) -> list[DailyMetricRow]:
    """One row per campaign per day for the inclusive date range."""
    ga_service = client.get_service("GoogleAdsService")
    request = client.get_type("SearchGoogleAdsStreamRequest")
    request.customer_id = customer_id
    date_clause = f"segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}'"
    request.query = DAILY_CAMPAIGN_METRICS.format(date_clause=date_clause)

    rows: list[DailyMetricRow] = []
    for batch in ga_service.search_stream(request=request):
        for r in batch.results:
            c = r.campaign
            strategy = client.enums.BiddingStrategyTypeEnum.BiddingStrategyType.Name(
                c.bidding_strategy_type
            )
            # PMax keeps tROAS under maximize_conversion_value; others under target_roas.
            troas = c.maximize_conversion_value.target_roas or c.target_roas.target_roas or None
            rows.append(
                DailyMetricRow(
                    customer_id=customer_id,
                    campaign_id=str(c.id),
                    date=r.segments.date,
                    campaign_name=c.name,
                    campaign_status=client.enums.CampaignStatusEnum.CampaignStatus.Name(c.status),
                    channel_type=client.enums.AdvertisingChannelTypeEnum.AdvertisingChannelType.Name(
                        c.advertising_channel_type
                    ),
                    bidding_strategy=strategy,
                    troas_target=troas,
                    budget_id=str(r.campaign_budget.id) if r.campaign_budget.id else None,
                    budget_amount=micros_to_currency(r.campaign_budget.amount_micros)
                    if r.campaign_budget.amount_micros
                    else None,
                    cost=micros_to_currency(r.metrics.cost_micros),
                    conversions=r.metrics.conversions,
                    conv_value=r.metrics.conversions_value,
                )
            )
    return rows


def upsert_daily_metrics(conn: sqlite3.Connection, rows: Iterable[DailyMetricRow]) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    count = 0
    with conn:
        for row in rows:
            d = asdict(row)
            d["pulled_at"] = now
            conn.execute(
                """
                INSERT INTO daily_metrics (
                    customer_id, campaign_id, date, campaign_name, campaign_status,
                    channel_type, bidding_strategy, troas_target, budget_id, budget_amount,
                    cost, conversions, conv_value, pulled_at
                ) VALUES (
                    :customer_id, :campaign_id, :date, :campaign_name, :campaign_status,
                    :channel_type, :bidding_strategy, :troas_target, :budget_id, :budget_amount,
                    :cost, :conversions, :conv_value, :pulled_at
                )
                ON CONFLICT(customer_id, campaign_id, date) DO UPDATE SET
                    campaign_name=excluded.campaign_name,
                    campaign_status=excluded.campaign_status,
                    channel_type=excluded.channel_type,
                    bidding_strategy=excluded.bidding_strategy,
                    troas_target=excluded.troas_target,
                    budget_id=excluded.budget_id,
                    budget_amount=excluded.budget_amount,
                    cost=excluded.cost,
                    conversions=excluded.conversions,
                    conv_value=excluded.conv_value,
                    pulled_at=excluded.pulled_at
                """,
                d,
            )
            count += 1
    return count


def fetch_adgroup_troas(client: GoogleAdsClient, customer_id: str) -> list[dict]:
    """Ad groups with their own tROAS, plus L7 and prior-week cost metrics.

    Two streamed queries (L7 and the prior week) of TROAS_AUDIT_ADGROUP,
    merged per ad group. Mirrors the windows troas_audit uses.
    """
    from ads_mcp.reporting.queries import TROAS_AUDIT_ADGROUP
    from ads_mcp.reporting.utils import date_range_clause

    ga_service = client.get_service("GoogleAdsService")

    def run(date_range) -> dict[str, dict]:
        request = client.get_type("SearchGoogleAdsStreamRequest")
        request.customer_id = customer_id
        request.query = TROAS_AUDIT_ADGROUP.format(date_clause=date_range_clause(date_range))
        rows: dict[str, dict] = {}
        for batch in ga_service.search_stream(request=request):
            for r in batch.results:
                # Not GAQL-filterable; only ad groups with their own tROAS count.
                if r.ad_group.target_roas <= 0:
                    continue
                rows[f"{r.campaign.id}:{r.ad_group.id}"] = {
                    "campaign_id": str(r.campaign.id),
                    "campaign_name": r.campaign.name,
                    "ad_group_id": str(r.ad_group.id),
                    "ad_group_name": r.ad_group.name,
                    "troas_target": r.ad_group.target_roas,
                    "cost": micros_to_currency(r.metrics.cost_micros),
                    "conv_value": r.metrics.conversions_value,
                }
        return rows

    today = date.today()
    prior_range = {
        "start_date": (today - timedelta(days=14)).isoformat(),
        "end_date": (today - timedelta(days=8)).isoformat(),
    }
    current = run("LAST_7_DAYS")
    prior = run(prior_range)

    out = []
    for key, row in current.items():
        out.append({
            "customer_id": customer_id,
            "campaign_id": row["campaign_id"],
            "campaign_name": row["campaign_name"],
            "ad_group_id": row["ad_group_id"],
            "ad_group_name": row["ad_group_name"],
            "troas_target": row["troas_target"],
            "l7_cost": row["cost"],
            "l7_conv_value": row["conv_value"],
            "prior_cost": prior.get(key, {}).get("cost", 0.0),
        })
    return out


def replace_adgroup_troas(
    conn: sqlite3.Connection, customer_id: str, rows: list[dict]
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with conn:
        conn.execute("DELETE FROM adgroup_troas WHERE customer_id=?", (customer_id,))
        conn.executemany(
            """
            INSERT INTO adgroup_troas
                (customer_id, campaign_id, ad_group_id, ad_group_name, campaign_name,
                 troas_target, l7_cost, l7_conv_value, prior_cost, updated_at)
            VALUES (:customer_id, :campaign_id, :ad_group_id, :ad_group_name, :campaign_name,
                    :troas_target, :l7_cost, :l7_conv_value, :prior_cost, :updated_at)
            """,
            [{**r, "updated_at": now} for r in rows],
        )


def upsert_store_sales(
    conn: sqlite3.Connection, sales_by_store: dict[str, dict[str, float]]
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    count = 0
    with conn:
        for shopify_key, daily in sales_by_store.items():
            for day, net_sales in daily.items():
                conn.execute(
                    """
                    INSERT INTO store_sales (shopify_key, date, net_sales, pulled_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(shopify_key, date) DO UPDATE SET
                        net_sales=excluded.net_sales, pulled_at=excluded.pulled_at
                    """,
                    (shopify_key, day, net_sales, now),
                )
                count += 1
    return count


# ---------------------------------------------------------------------------
# Pull records
# ---------------------------------------------------------------------------

def start_pull(conn: sqlite3.Connection, kind: str) -> int:
    with conn:
        cur = conn.execute(
            "INSERT INTO pulls (kind, started_at) VALUES (?, ?)",
            (kind, datetime.now().isoformat(timespec="seconds")),
        )
    return cur.lastrowid


def finish_pull(
    conn: sqlite3.Connection,
    pull_id: int,
    accounts_scanned: int,
    stores_scanned: int,
    new_flags: int = 0,
    resolved_flags: int = 0,
    errors: Optional[list[str]] = None,
) -> None:
    with conn:
        conn.execute(
            """
            UPDATE pulls SET finished_at=?, accounts_scanned=?, stores_scanned=?,
                new_flags=?, resolved_flags=?, errors=?
            WHERE id=?
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                accounts_scanned,
                stores_scanned,
                new_flags,
                resolved_flags,
                json.dumps(errors or []),
                pull_id,
            ),
        )


# ---------------------------------------------------------------------------
# Backfill and incremental pulls
# ---------------------------------------------------------------------------

def ads_accounts() -> list[dict]:
    """ENABLED ads accounts from stores_mapping.json (the scan universe)."""
    registry = load_store_registry()
    return [
        {"customer_id": s.ads_customer_id, "name": s.ads_name, "shopify_key": s.shopify_key}
        for s in registry
        if s.ads_status == "ENABLED"
    ]


def pull_window(days: int, end: Optional[date] = None) -> tuple[date, date]:
    end = end or date.today()
    return end - timedelta(days=days - 1), end


def run_data_pull(
    conn: sqlite3.Connection,
    client: GoogleAdsClient,
    days: int,
    kind: str,
) -> tuple[int, list[str]]:
    """Pull ads metrics + store sales for the trailing window into the DB.

    Returns (pull_id, errors). Detector runs are layered on top by the caller
    (control_center.detectors) so backfill and scheduled pulls share this path.
    """
    pull_id = start_pull(conn, kind)
    errors: list[str] = []
    start, end = pull_window(days)

    accounts = ads_accounts()
    metric_rows = 0
    for account in accounts:
        try:
            rows = fetch_daily_campaign_metrics(client, account["customer_id"], start, end)
            metric_rows += upsert_daily_metrics(conn, rows)
            replace_adgroup_troas(
                conn,
                account["customer_id"],
                fetch_adgroup_troas(client, account["customer_id"]),
            )
        except Exception as exc:
            msg = f"ads pull failed for {account['customer_id']} ({account['name']}): {exc}"
            print(f"[control_center.store] {msg}", file=sys.stderr)
            errors.append(msg)

    try:
        sales = asyncio.run(fetch_all_store_sales(start, end))
        upsert_store_sales(conn, sales)
        stores_scanned = len([k for k, v in sales.items() if v])
    except Exception as exc:
        msg = f"store sales pull failed: {exc}"
        print(f"[control_center.store] {msg}", file=sys.stderr)
        errors.append(msg)
        stores_scanned = 0

    finish_pull(
        conn,
        pull_id,
        accounts_scanned=len(accounts),
        stores_scanned=stores_scanned,
        errors=errors,
    )
    print(
        f"[control_center.store] pull {pull_id} ({kind}): {metric_rows} metric rows, "
        f"{stores_scanned} stores, {len(errors)} errors",
        file=sys.stderr,
    )
    return pull_id, errors


def backfill(days: int = 180) -> None:
    """One-time historical load. Safe to re-run; upserts are idempotent."""
    from ads_mcp.client import get_client

    conn = connect()
    client = get_client()
    run_data_pull(conn, client, days=days, kind="backfill")
    conn.close()


# ---------------------------------------------------------------------------
# Negative-keyword audit proposals
# ---------------------------------------------------------------------------

def refresh_negative_proposals(
    conn: sqlite3.Connection,
    proposals: Iterable[dict],
    audit_run_id: str,
) -> int:
    """Refresh open proposals for the audited accounts.

    Deletes existing OPEN rows for every customer_id present in proposals, then
    inserts the new proposals as open. Committed / skipped / failed rows are
    preserved (a decided term is never re-proposed). Returns rows inserted.
    """
    proposals = list(proposals)
    now = datetime.now().isoformat(timespec="seconds")
    audited = {str(p["customer_id"]) for p in proposals}

    for cid in audited:
        conn.execute(
            "DELETE FROM negative_proposals WHERE customer_id=? AND status='open'",
            (cid,),
        )

    inserted = 0
    for p in proposals:
        # Skip if a decided (committed/skipped/failed) row already owns this key.
        existing = conn.execute(
            "SELECT status FROM negative_proposals "
            "WHERE customer_id=? AND keyword=? AND match_type=?",
            (str(p["customer_id"]), p["keyword"], p["suggested_match_type"]),
        ).fetchone()
        if existing is not None and existing["status"] != "open":
            continue
        conn.execute(
            """
            INSERT INTO negative_proposals
                (customer_id, account_name, tranche, keyword, match_type, example_term,
                 matched_count, l_spend, l_clicks, l_conversions, l_conv_value, l_roas_pct,
                 severity, rationale, status, audit_run_id, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'open', ?, ?)
            ON CONFLICT(customer_id, keyword, match_type) DO UPDATE SET
                tranche=excluded.tranche, example_term=excluded.example_term,
                matched_count=excluded.matched_count, l_spend=excluded.l_spend,
                l_clicks=excluded.l_clicks, l_conversions=excluded.l_conversions,
                l_conv_value=excluded.l_conv_value, l_roas_pct=excluded.l_roas_pct,
                severity=excluded.severity, rationale=excluded.rationale,
                audit_run_id=excluded.audit_run_id
            """,
            (
                str(p["customer_id"]), p.get("account_name", ""), p["tranche"], p["keyword"],
                p["suggested_match_type"], p.get("example_term", ""), int(p.get("matched_count", 1)),
                float(p.get("l_spend", 0.0)), int(p.get("l_clicks", 0)),
                float(p.get("l_conversions", 0.0)), float(p.get("l_conv_value", 0.0)),
                float(p.get("l_roas_pct", 0.0)), p.get("severity", "low"),
                p.get("rationale", ""), audit_run_id, now,
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


def negative_proposals(conn: sqlite3.Connection, status: str = "open") -> list[dict]:
    """Return proposals with the given status, ordered for display."""
    rows = conn.execute(
        "SELECT * FROM negative_proposals WHERE status=? "
        "ORDER BY account_name, tranche, l_spend DESC",
        (status,),
    ).fetchall()
    return [dict(r) for r in rows]


def count_open_negatives(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM negative_proposals WHERE status='open'"
    ).fetchone()
    return int(row["n"]) if row else 0


def count_approved_negatives(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM negative_proposals WHERE status='approved'"
    ).fetchone()
    return int(row["n"]) if row else 0


def set_negative_status(conn: sqlite3.Connection, prop_id: int, status: str) -> Optional[dict]:
    conn.execute(
        "UPDATE negative_proposals SET status=? WHERE id=?", (status, prop_id)
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM negative_proposals WHERE id=?", (prop_id,)
    ).fetchone()
    return dict(row) if row else None


def approve_negative_tranche(conn: sqlite3.Connection, customer_id: str, tranche: str) -> int:
    """Bulk-approve every open proposal in one account+tranche. Returns count."""
    cur = conn.execute(
        "UPDATE negative_proposals SET status='approved' "
        "WHERE customer_id=? AND tranche=? AND status='open'",
        (str(customer_id), tranche),
    )
    conn.commit()
    return cur.rowcount


def add_protect_term(conn: sqlite3.Connection, customer_id: str, term: str) -> bool:
    """Record a term the operator wants protected (never re-proposed as a negative).

    Stored lowercased; the audit engine substring-matches protect terms against
    search terms. Returns True if newly added, False if already present.
    """
    t = (term or "").strip().lower()
    if not t:
        return False
    cur = conn.execute(
        "INSERT OR IGNORE INTO negative_protect_terms (customer_id, term, created_at) "
        "VALUES (?, ?, ?)",
        (str(customer_id), t, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return cur.rowcount > 0


def remove_protect_term(conn: sqlite3.Connection, customer_id: str, term: str) -> None:
    """Remove a protect term (undo). The next audit will re-propose it if wasteful."""
    conn.execute(
        "DELETE FROM negative_protect_terms WHERE customer_id=? AND term=?",
        (str(customer_id), (term or "").strip().lower()),
    )
    conn.commit()


def protect_overrides(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Return {customer_id: [protect terms]} from operator Protect decisions.

    Merged into each account's protect_terms by control_center/waste.py before the
    audit runs, so protected terms never resurface. This is the durable, app-local
    home for protect decisions (the deployed service cannot write the repo config).
    """
    out: dict[str, list[str]] = {}
    for r in conn.execute(
        "SELECT customer_id, term FROM negative_protect_terms ORDER BY customer_id, term"
    ):
        out.setdefault(r["customer_id"], []).append(r["term"])
    return out


def protect_open_matching(conn: sqlite3.Connection, customer_id: str, term: str) -> int:
    """Mark open proposals whose NEGATIVE KEYWORD contains the protected term as
    'protected', so protecting one term clears its own siblings immediately.

    Matches on keyword only, not example_term: protecting "dewalt" should retire
    the negatives that target dewalt (the "dewalt" n-gram, "dewalt framing nailer"),
    not an "ebay" competitor negative that merely had a dewalt-containing example.
    Returns rows updated."""
    t = (term or "").strip().lower()
    if not t:
        return 0
    cur = conn.execute(
        "UPDATE negative_proposals SET status='protected' "
        "WHERE customer_id=? AND status='open' AND lower(keyword) LIKE ?",
        (str(customer_id), f"%{t}%"),
    )
    conn.commit()
    return cur.rowcount


def approved_negatives_for(conn: sqlite3.Connection, customer_id: str) -> list[dict]:
    """Approved proposals for one account, ready to commit."""
    rows = conn.execute(
        "SELECT * FROM negative_proposals WHERE customer_id=? AND status='approved' "
        "ORDER BY tranche, keyword",
        (str(customer_id),),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_negative_committed(
    conn: sqlite3.Connection, prop_id: int, status: str, result: str
) -> None:
    conn.execute(
        "UPDATE negative_proposals SET status=?, result=?, committed_at=? WHERE id=?",
        (status, result, datetime.now().isoformat(timespec="seconds"), prop_id),
    )
    conn.commit()


if __name__ == "__main__":
    backfill(days=int(sys.argv[1]) if len(sys.argv) > 1 else 180)
