"""In-process pull scheduler.

Runs as an asyncio task inside the web app process. Locally, launchd keeps
that process alive; hosted, the Railway service is always-on. Fires a data
pull + detector run at the configured operator-local times (CC_TIMEZONE,
default America/Los_Angeles -- NOT the container clock, which is UTC on
Railway) and fans out alerts for any new flags.

On a fresh database (first boot on a new volume) it runs the 180-day
backfill first so the anomaly baselines and sparklines have history,
mirroring the documented first-run behavior of the local install.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, time, timedelta

from control_center.clock import now_local

PULL_TIMES = (time(7, 0), time(12, 30), time(17, 30))
BACKFILL_DAYS = int(os.environ.get("CC_BACKFILL_DAYS", "180"))


def _seconds_until_next_pull(now: datetime) -> float:
    candidates = []
    for t in PULL_TIMES:
        candidate = datetime.combine(now.date(), t)
        if candidate <= now:
            candidate += timedelta(days=1)
        candidates.append(candidate)
    return (min(candidates) - now).total_seconds()


def pull_job() -> None:
    """One scheduled cycle: pull 3 trailing days, detect, alert."""
    from ads_mcp.client import get_client
    from control_center import store
    from control_center.alerts import send_alerts
    from control_center.detectors import run_detectors

    conn = store.connect()
    try:
        store.run_data_pull(conn, get_client(), days=3, kind="scheduled")
        new_flags, resolved = run_detectors(conn)
        # Stamp flag counts onto the pull row for the history screen.
        conn.execute(
            "UPDATE pulls SET new_flags=?, resolved_flags=? "
            "WHERE id=(SELECT MAX(id) FROM pulls)",
            (len(new_flags), resolved),
        )
        conn.commit()
        send_alerts(new_flags)
    finally:
        conn.close()


def _backfill_if_empty() -> None:
    """First boot on an empty DB: load history so detectors have baselines."""
    from ads_mcp.client import get_client
    from control_center import store
    from control_center.detectors import run_detectors

    conn = store.connect()
    try:
        has_rows = conn.execute("SELECT 1 FROM daily_metrics LIMIT 1").fetchone()
        if has_rows:
            return
        print(
            f"[control_center.scheduler] empty database; running {BACKFILL_DAYS}-day backfill",
            file=sys.stderr,
        )
        store.run_data_pull(conn, get_client(), days=BACKFILL_DAYS, kind="backfill")
        run_detectors(conn)
    finally:
        conn.close()


async def scheduler_loop() -> None:
    try:
        await asyncio.to_thread(_backfill_if_empty)
    except Exception as exc:
        print(f"[control_center.scheduler] startup backfill failed: {exc}", file=sys.stderr)

    while True:
        wait = _seconds_until_next_pull(now_local())
        print(
            f"[control_center.scheduler] next pull in {wait / 3600:.1f}h",
            file=sys.stderr,
        )
        await asyncio.sleep(wait)
        try:
            await asyncio.to_thread(pull_job)
        except Exception as exc:
            print(f"[control_center.scheduler] pull cycle failed: {exc}", file=sys.stderr)
