"""In-process pull scheduler.

Runs as an asyncio task inside the web app process (launchd keeps that
process alive, so one KeepAlive covers both serving and pulling). Fires a
data pull + detector run at the configured local times and fans out alerts
for any new flags.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, time, timedelta

PULL_TIMES = (time(7, 0), time(12, 30), time(17, 30))


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


async def scheduler_loop() -> None:
    while True:
        wait = _seconds_until_next_pull(datetime.now())
        print(
            f"[control_center.scheduler] next pull in {wait / 3600:.1f}h",
            file=sys.stderr,
        )
        await asyncio.sleep(wait)
        try:
            await asyncio.to_thread(pull_job)
        except Exception as exc:
            print(f"[control_center.scheduler] pull cycle failed: {exc}", file=sys.stderr)
