"""Operator-local time for the control center.

Every timestamp the control center stores or compares (pull schedule, snooze
windows, tROAS cooldowns, audit rows) is a naive ISO string in the operator's
timezone. On the Mac that was implicitly the system zone; in a hosted container
the system zone is UTC, which would shift the 07:00/12:30/17:30 pull times and
silently stretch or shrink cooldown windows by the UTC offset.

These helpers pin all of it to CC_TIMEZONE (default America/Los_Angeles) and
return NAIVE values so existing string comparisons against stored rows keep
working unchanged. tzdata (pure-python zoneinfo data) is a project dependency
so this works on slim images without OS tzdata.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

_DEFAULT_TZ = "America/Los_Angeles"


def tz() -> ZoneInfo:
    return ZoneInfo(os.environ.get("CC_TIMEZONE", _DEFAULT_TZ))


def now_local() -> datetime:
    """Current operator-local time, naive (drop-in for datetime.now())."""
    return datetime.now(tz()).replace(tzinfo=None)


def today_local() -> date:
    """Current operator-local date (drop-in for date.today())."""
    return now_local().date()
