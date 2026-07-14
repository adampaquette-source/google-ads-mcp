"""Alert fan-out: Google Chat webhook plus macOS desktop notification.

Fires after a scheduled pull when new flags appeared. Chat reuses the same
webhook env vars as the digest; the desktop notification uses osascript so
there is no extra dependency (and is skipped automatically off-macOS).

CC_ALERTS_ENABLED=0 disables the fan-out entirely. Set it on whichever
instance should stay quiet while both the local launchd service and the
hosted Railway service are pulling, so Chat is not notified twice per flag.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()


def _dashboard_url() -> str:
    return os.environ.get("CC_BASE_URL", "").rstrip("/") or "http://localhost:8770"

_TYPE_LABELS = {
    "troas_drift": "tROAS drift",
    "budget_cap": "Budget opportunity",
    "spend_anomaly": "Spend anomaly",
}


def _chat_webhook_url() -> str:
    return (
        os.environ.get("GOOGLE_ADS_CC_WEBHOOK_URL", "").strip()
        or os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "").strip()
    )


def _summarize(new_flags: list[dict]) -> str:
    counts: dict[str, int] = {}
    for f in new_flags:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    parts = [f"{n} {_TYPE_LABELS.get(t, t)}" for t, n in sorted(counts.items())]
    return ", ".join(parts)


def post_chat_alert(new_flags: list[dict]) -> bool:
    url = _chat_webhook_url()
    if not url or not new_flags:
        return False

    high = [f for f in new_flags if f.get("severity") == "high"]
    lines = [f"*Control center: {len(new_flags)} new flags* ({_summarize(new_flags)})"]
    for f in (high or new_flags)[:5]:
        p = f.get("payload", {})
        lines.append(
            f"- [{f.get('severity', '')}] {_TYPE_LABELS.get(f['type'], f['type'])}: "
            f"{p.get('campaign_name', f.get('campaign_id', ''))}"
        )
    if len(new_flags) > 5:
        lines.append(f"...and {len(new_flags) - 5} more.")
    lines.append(f"Review queue: {_dashboard_url()}")

    body = json.dumps({"text": "\n".join(lines)}).encode()
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        print(f"[control_center.alerts] chat post failed: {exc}", file=sys.stderr)
        return False


def post_desktop_alert(new_flags: list[dict]) -> bool:
    if not new_flags or sys.platform != "darwin":
        return False
    title = f"Ads Control Center: {len(new_flags)} new flags"
    body = _summarize(new_flags)
    script = (
        f'display notification "{body}" with title "{title}" sound name "Submarine"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=10)
        return True
    except Exception as exc:
        print(f"[control_center.alerts] desktop notification failed: {exc}", file=sys.stderr)
        return False


def send_alerts(new_flags: list[dict]) -> None:
    if not new_flags:
        return
    if os.environ.get("CC_ALERTS_ENABLED", "1") == "0":
        print(
            f"[control_center.alerts] {len(new_flags)} new flags; alerts disabled "
            "(CC_ALERTS_ENABLED=0)",
            file=sys.stderr,
        )
        return
    post_chat_alert(new_flags)
    post_desktop_alert(new_flags)
