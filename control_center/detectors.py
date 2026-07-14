"""Flag detectors for the control center.

All three detectors run purely against the local SQLite tables (no API calls):
  - troas_drift: actual L7 ROAS vs target, tiered trigger, step-band suggestion
    (drift math and step bands mirror ads_mcp/reporting/troas_audit.py)
  - budget_cap: spend at >= 95% of daily budget for N consecutive days,
    surfaced as an opportunity signal per the budgetless philosophy
  - spend_anomaly: yesterday's campaign spend z-scored against the trailing
    weekday-matched 180-day baseline

Tier rules (CONSULTATION_RESULTS.md / DIGEST_SKILL.md): Tier 1 is ToolUp,
Red Tool Store, plus the top 3 accounts by trailing-30-day spend. Tier 1
flags at normal sensitivity; all other accounts only flag larger deviations.
"""

from __future__ import annotations

import json
import sqlite3
import statistics
import sys
from datetime import datetime, timedelta

from control_center.clock import now_local, today_local

from typing_extensions import TypedDict

# Mirrors ads_mcp/reporting/troas_audit.py constants.
MIN_SPEND_WEEK = 100.0          # $/L7 minimum for a tROAS flag
SPEND_SCALING_MIN_PCT = 15.0    # WoW spend growth required to suggest LOOSEN

TIER1_DRIFT_PCT = 10.0          # spec: Tier 1 drift trigger
TIER23_DRIFT_PCT = 30.0         # spec: Tier 2/3 only flag bigger deviations

# Budget audit thresholds, mirroring ads_mcp/reporting/budget_audit.py.
BUDGET_CONSTRAINED_PCT = 80.0       # daily spend / budget threshold
BUDGET_CONSTRAINED_MIN_DAYS = 2     # qualifying days in the L7 window
BUDGET_EXCESS_PCT = 40.0            # avg utilization below this = excess
BUDGET_EXCESS_MIN_L7_SPEND = 1.0    # ignore dormant campaigns
BUDGET_BUMP_PCT = 20.0              # suggested increase for constrained

TIER1_ANOMALY_Z = 2.0
TIER23_ANOMALY_Z = 3.0
ANOMALY_MIN_SPEND = 50.0        # yesterday spend floor for anomaly flags
ANOMALY_MIN_SAMPLES = 8         # weekday-matched history needed for a baseline

# Named Tier 1 accounts (always Tier 1 regardless of spend rank).
TIER1_NAMED_CUSTOMER_IDS = {
    "1864748540",  # ToolUp
    "4033622485",  # Red Tool Store (Themilwaukeestore.com)
}


class FlagCandidate(TypedDict):
    type: str
    customer_id: str
    campaign_id: str
    severity: str
    payload: dict


def _drift_to_step_pp(drift_pct_abs: float) -> int:
    """Same bands as troas_audit: 7-13% -> 25pp, 13-22% -> 50pp, 22-30% -> 75pp, 30%+ -> 100pp."""
    if drift_pct_abs >= 30.0:
        return 100
    if drift_pct_abs >= 22.0:
        return 75
    if drift_pct_abs >= 13.0:
        return 50
    return 25


def compute_tiers(conn: sqlite3.Connection) -> dict[str, int]:
    """{customer_id: 1|2} -- Tier 1 = named accounts + top 3 by L30 spend."""
    rows = conn.execute(
        """
        SELECT customer_id, SUM(cost) AS spend
        FROM daily_metrics
        WHERE date >= date('now', '-30 days')
        GROUP BY customer_id ORDER BY spend DESC
        """
    ).fetchall()
    tiers = {r["customer_id"]: 2 for r in rows}
    for r in rows[:3]:
        tiers[r["customer_id"]] = 1
    for cid in TIER1_NAMED_CUSTOMER_IDS:
        if cid in tiers:
            tiers[cid] = 1
    return tiers


# ---------------------------------------------------------------------------
# Detectors (each returns FlagCandidates from local data)
# ---------------------------------------------------------------------------

def _adgroup_drift_rows(conn: sqlite3.Connection, customer_id: str, campaign_id: str) -> list[dict]:
    """Per-ad-group drift evaluation for a campaign with ad-group-managed tROAS.

    Returns one dict per ad group with its own tROAS, drift math applied,
    suggested value populated only where the campaign-level rules would
    trigger (min spend, drift trigger, LOOSEN spend scaling).
    """
    out = []
    for r in conn.execute(
        "SELECT * FROM adgroup_troas WHERE customer_id=? AND campaign_id=? "
        "ORDER BY l7_cost DESC",
        (customer_id, campaign_id),
    ).fetchall():
        target = r["troas_target"]
        cost, value, prior = r["l7_cost"], r["l7_conv_value"], r["prior_cost"]
        actual = value / cost if cost > 0 else 0.0
        drift_pct = (actual - target) / target * 100 if target else 0.0
        spend_change_pct = (cost - prior) / prior * 100 if prior > 0 else 0.0
        step_pp = _drift_to_step_pp(abs(drift_pct))
        current_pct = target * 100.0

        suggested = None
        direction = "TIGHTEN" if drift_pct < 0 else "LOOSEN"
        triggers = cost >= MIN_SPEND_WEEK and (
            abs(drift_pct) >= TIER1_DRIFT_PCT or (actual == 0.0 and cost > 0)
        )
        if triggers:
            if direction == "TIGHTEN":
                suggested = current_pct + step_pp
            elif spend_change_pct >= SPEND_SCALING_MIN_PCT:
                suggested = max(current_pct - step_pp, 1.0)

        out.append({
            "ad_group_id": r["ad_group_id"],
            "ad_group_name": r["ad_group_name"],
            "current_troas_pct": round(current_pct, 1),
            "l7_actual_roas_pct": round(actual * 100, 1),
            "drift_pct": round(drift_pct, 1),
            "l7_spend": round(cost, 2),
            "l7_conv_value": round(value, 2),
            "spend_change_pct": round(spend_change_pct, 1),
            "direction": direction,
            "suggested_troas_pct": round(suggested, 1) if suggested else None,
            "triggers": triggers,
        })
    return out


def detect_troas_drift(conn: sqlite3.Connection, tiers: dict[str, int]) -> list[FlagCandidate]:
    adgroup_managed = {
        (r["customer_id"], r["campaign_id"])
        for r in conn.execute(
            "SELECT DISTINCT customer_id, campaign_id FROM adgroup_troas"
        ).fetchall()
    }
    rows = conn.execute(
        """
        SELECT customer_id, campaign_id,
               MAX(campaign_name) AS campaign_name,
               MAX(bidding_strategy) AS bidding_strategy,
               MAX(troas_target) AS troas_target,
               SUM(CASE WHEN date >= date('now','-7 days') THEN cost ELSE 0 END) AS l7_cost,
               SUM(CASE WHEN date >= date('now','-7 days') THEN conv_value ELSE 0 END) AS l7_value,
               SUM(CASE WHEN date < date('now','-7 days') AND date >= date('now','-14 days')
                        THEN cost ELSE 0 END) AS prior_cost
        FROM daily_metrics
        WHERE date >= date('now','-14 days')
          AND campaign_status = 'ENABLED'
          AND troas_target IS NOT NULL AND troas_target > 0
        GROUP BY customer_id, campaign_id
        """
    ).fetchall()

    out: list[FlagCandidate] = []
    for r in rows:
        cost, value, target = r["l7_cost"], r["l7_value"], r["troas_target"]
        if cost < MIN_SPEND_WEEK:
            continue
        actual = value / cost if cost > 0 else 0.0
        drift_pct = (actual - target) / target * 100
        tier = tiers.get(r["customer_id"], 2)
        zero_roas = actual == 0.0
        trigger = TIER1_DRIFT_PCT if tier == 1 else TIER23_DRIFT_PCT
        is_adgroup_managed = (r["customer_id"], r["campaign_id"]) in adgroup_managed

        prior = r["prior_cost"]
        spend_change_pct = (cost - prior) / prior * 100 if prior > 0 else 0.0
        step_pp = _drift_to_step_pp(abs(drift_pct))
        current_pct = target * 100.0

        if is_adgroup_managed:
            # tROAS lives on the ad groups: evaluate drift per ad group and
            # surface them as editable child rows. The campaign flags when any
            # ad group triggers (or the aggregate itself is far off).
            adgroups = _adgroup_drift_rows(conn, r["customer_id"], r["campaign_id"])
            triggering = [a for a in adgroups if a["triggers"]]
            if not triggering and abs(drift_pct) < trigger and not zero_roas:
                continue
            worst = max((abs(a["drift_pct"]) for a in triggering), default=abs(drift_pct))
            any_zero = any(
                a["l7_actual_roas_pct"] == 0 and a["l7_spend"] > 0 for a in triggering
            )
            severity = "high" if (any_zero or worst >= 30.0) else (
                "medium" if worst >= 15.0 else "low"
            )
            out.append(
                FlagCandidate(
                    type="troas_drift",
                    customer_id=r["customer_id"],
                    campaign_id=r["campaign_id"],
                    severity=severity,
                    payload={
                        "campaign_name": r["campaign_name"],
                        "bidding_strategy": r["bidding_strategy"],
                        "direction": "MIXED",
                        "current_troas_pct": round(current_pct, 1),
                        "suggested_troas_pct": None,
                        "l7_actual_roas_pct": round(actual * 100, 1),
                        "drift_pct": round(drift_pct, 1),
                        "l7_spend": round(cost, 2),
                        "l7_conv_value": round(value, 2),
                        "spend_change_pct": round(spend_change_pct, 1),
                        "tier": tier,
                        "adgroup_managed": True,
                        "adgroups": adgroups,
                        "rationale": (
                            f"tROAS is managed per ad group ({len(adgroups)} ad groups, "
                            f"{len(triggering)} drifting beyond trigger). Campaign aggregate: "
                            f"L7 actual ROAS {actual * 100:.0f}% vs blended target "
                            f"{current_pct:.0f}%. Stage changes on the ad group rows."
                        ),
                    },
                )
            )
            continue

        if abs(drift_pct) < trigger and not zero_roas:
            continue

        if drift_pct < 0:
            direction = "TIGHTEN"
            suggested_pct = current_pct + step_pp
        else:
            direction = "LOOSEN"
            suggested_pct = max(current_pct - step_pp, 1.0)
            if spend_change_pct < SPEND_SCALING_MIN_PCT:
                # Above target but not scaling spend: informational, no change suggested.
                suggested_pct = None

        severity = "high" if (zero_roas or abs(drift_pct) >= 30.0) else (
            "medium" if abs(drift_pct) >= 15.0 else "low"
        )
        out.append(
            FlagCandidate(
                type="troas_drift",
                customer_id=r["customer_id"],
                campaign_id=r["campaign_id"],
                severity=severity,
                payload={
                    "campaign_name": r["campaign_name"],
                    "bidding_strategy": r["bidding_strategy"],
                    "direction": direction,
                    "current_troas_pct": round(current_pct, 1),
                    "suggested_troas_pct": round(suggested_pct, 1) if suggested_pct else None,
                    "step_pp": step_pp,
                    "l7_actual_roas_pct": round(actual * 100, 1),
                    "drift_pct": round(drift_pct, 1),
                    "l7_spend": round(cost, 2),
                    "l7_conv_value": round(value, 2),
                    "spend_change_pct": round(spend_change_pct, 1),
                    "tier": tier,
                    "adgroup_managed": False,
                    "rationale": (
                        f"L7 actual ROAS {actual * 100:.0f}% vs target {current_pct:.0f}% "
                        f"({drift_pct:+.1f}% drift). "
                        + (
                            f"Suggest {direction} by {step_pp}pp."
                            if suggested_pct
                            else "Above target but spend not scaling; review only."
                        )
                    ),
                },
            )
        )
    return out


def detect_budget_flags(conn: sqlite3.Connection, tiers: dict[str, int]) -> list[FlagCandidate]:
    """Budget audit, adapted from ads_mcp/reporting/budget_audit.py.

    constrained: spend >= 80% of daily budget on >= 2 of the last 7 full days.
                 Opportunity signal per the budgetless philosophy: review for
                 an increase, not a warning.
    excess:      L7 average daily spend < 40% of the current budget and total
                 L7 spend >= $1. Candidate for decrease or reallocation.
    """
    rows = conn.execute(
        """
        SELECT customer_id, campaign_id, date, cost, conv_value, budget_amount,
               MAX(campaign_name) OVER (PARTITION BY customer_id, campaign_id) AS campaign_name,
               MAX(budget_id) OVER (PARTITION BY customer_id, campaign_id) AS budget_id
        FROM daily_metrics
        WHERE date >= date('now','-8 days') AND date < date('now')
          AND campaign_status = 'ENABLED'
          AND budget_amount IS NOT NULL AND budget_amount > 0
        ORDER BY customer_id, campaign_id, date DESC
        """
    ).fetchall()

    by_campaign: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for r in rows:
        by_campaign.setdefault((r["customer_id"], r["campaign_id"]), []).append(r)

    out: list[FlagCandidate] = []
    for (customer_id, campaign_id), days in by_campaign.items():
        tier = tiers.get(customer_id, 2)
        budget = days[0]["budget_amount"]
        if budget <= 0:
            continue
        l7_spend = sum(d["cost"] for d in days)
        l7_value = sum(d["conv_value"] for d in days)
        l7_roas_pct = (l7_value / l7_spend * 100) if l7_spend > 0 else 0.0
        max_daily = max(d["cost"] for d in days)
        common = {
            "campaign_name": days[0]["campaign_name"],
            "budget_id": days[0]["budget_id"],
            "daily_budget": budget,
            "l7_spend": round(l7_spend, 2),
            "l7_conv_value": round(l7_value, 2),
            "l7_roas_pct": round(l7_roas_pct, 1),
            "max_daily_spend": round(max_daily, 2),
            "tier": tier,
        }

        threshold_days = [
            d for d in days
            if d["budget_amount"] > 0
            and d["cost"] / d["budget_amount"] * 100 >= BUDGET_CONSTRAINED_PCT
        ]
        if len(threshold_days) >= BUDGET_CONSTRAINED_MIN_DAYS:
            avg_threshold_spend = sum(d["cost"] for d in threshold_days) / len(threshold_days)
            suggested = round(budget * (1 + BUDGET_BUMP_PCT / 100), 2)
            out.append(
                FlagCandidate(
                    type="budget_constrained",
                    customer_id=customer_id,
                    campaign_id=campaign_id,
                    severity="medium" if len(threshold_days) >= 4 else "low",
                    payload={
                        **common,
                        "days_at_threshold": len(threshold_days),
                        "avg_daily_spend": round(avg_threshold_spend, 2),
                        "suggested_budget": suggested,
                        "rationale": (
                            f"Hit {BUDGET_CONSTRAINED_PCT:.0f}%+ of the ${budget:,.0f}/day budget on "
                            f"{len(threshold_days)} of the last 7 days (L7 ROAS {l7_roas_pct:.0f}%). "
                            f"Budget constrained: review for increase (opportunity signal, "
                            f"not overspending)."
                        ),
                    },
                )
            )
            continue

        avg_daily = l7_spend / 7.0
        utilization_pct = avg_daily / budget * 100
        if l7_spend >= BUDGET_EXCESS_MIN_L7_SPEND and utilization_pct < BUDGET_EXCESS_PCT:
            # Suggest a budget that covers average spend with 30% headroom.
            suggested = max(round(avg_daily * 1.3, 0), 1.0)
            out.append(
                FlagCandidate(
                    type="budget_excess",
                    customer_id=customer_id,
                    campaign_id=campaign_id,
                    severity="low",
                    payload={
                        **common,
                        "avg_daily_spend": round(avg_daily, 2),
                        "utilization_pct": round(utilization_pct, 1),
                        "suggested_budget": suggested,
                        "rationale": (
                            f"Averaging ${avg_daily:,.0f}/day against a ${budget:,.0f}/day budget "
                            f"({utilization_pct:.0f}% utilization). Excess budget: candidate for "
                            f"decrease or reallocation."
                        ),
                    },
                )
            )
    return out


def detect_spend_anomaly(conn: sqlite3.Connection, tiers: dict[str, int]) -> list[FlagCandidate]:
    yesterday = (today_local() - timedelta(days=1)).isoformat()
    weekday = datetime.strptime(yesterday, "%Y-%m-%d").date().weekday()

    rows = conn.execute(
        """
        SELECT customer_id, campaign_id, date, cost,
               MAX(campaign_name) OVER (PARTITION BY customer_id, campaign_id) AS campaign_name
        FROM daily_metrics
        WHERE date >= date('now','-181 days') AND date < date('now')
          AND campaign_status = 'ENABLED'
        """
    ).fetchall()

    history: dict[tuple[str, str], dict[str, float]] = {}
    names: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r["customer_id"], r["campaign_id"])
        history.setdefault(key, {})[r["date"]] = r["cost"]
        names[key] = r["campaign_name"]

    out: list[FlagCandidate] = []
    for key, daily in history.items():
        x = daily.get(yesterday)
        if x is None or x < ANOMALY_MIN_SPEND:
            # A collapse to zero is also an anomaly: check it against the baseline below.
            x = daily.get(yesterday, 0.0)
        samples = [
            cost
            for day, cost in daily.items()
            if day != yesterday
            and datetime.strptime(day, "%Y-%m-%d").date().weekday() == weekday
        ]
        if len(samples) < ANOMALY_MIN_SAMPLES:
            continue
        mean = statistics.fmean(samples)
        stdev = statistics.stdev(samples)
        if mean < ANOMALY_MIN_SPEND and x < ANOMALY_MIN_SPEND:
            continue  # both baseline and observation too small to matter
        if stdev == 0:
            continue
        z = (x - mean) / stdev
        tier = tiers.get(key[0], 2)
        threshold = TIER1_ANOMALY_Z if tier == 1 else TIER23_ANOMALY_Z
        if abs(z) < threshold:
            continue
        out.append(
            FlagCandidate(
                type="spend_anomaly",
                customer_id=key[0],
                campaign_id=key[1],
                severity="high" if abs(z) >= threshold + 1.5 else "medium",
                payload={
                    "campaign_name": names[key],
                    "date": yesterday,
                    "spend": round(x, 2),
                    "baseline_mean": round(mean, 2),
                    "baseline_stdev": round(stdev, 2),
                    "z_score": round(z, 2),
                    "direction": "spike" if z > 0 else "drop",
                    "baseline_samples": len(samples),
                    "tier": tier,
                    "rationale": (
                        f"Yesterday spent ${x:,.0f} vs a same-weekday baseline of "
                        f"${mean:,.0f} (z = {z:+.1f}). "
                        + ("Unusual spike: check what changed." if z > 0
                           else "Unusual drop: check budget caps, disapprovals, or bid issues.")
                    ),
                },
            )
        )
    return out


# ---------------------------------------------------------------------------
# Flag lifecycle
# ---------------------------------------------------------------------------

RESOLVE_AFTER_CLEAN_PULLS = 2


def sync_flags(
    conn: sqlite3.Connection, candidates: list[FlagCandidate]
) -> tuple[list[dict], int]:
    """Reconcile detector output with the flags table.

    Returns (new_flags_as_dicts, resolved_count). Live flags matching a
    candidate are refreshed; snoozed flags whose snooze expired reopen; live
    flags with no matching candidate accumulate clean pulls and resolve after
    RESOLVE_AFTER_CLEAN_PULLS.
    """
    now = now_local().isoformat(timespec="seconds")
    new_flags: list[dict] = []
    candidate_keys = set()

    with conn:
        for c in candidates:
            key = (c["type"], c["customer_id"], c["campaign_id"])
            candidate_keys.add(key)
            existing = conn.execute(
                """
                SELECT id, status, snooze_until FROM flags
                WHERE type=? AND customer_id=? AND campaign_id=?
                  AND status IN ('open','snoozed')
                """,
                key,
            ).fetchone()
            if existing:
                status = existing["status"]
                if status == "snoozed" and (
                    not existing["snooze_until"] or existing["snooze_until"] <= now
                ):
                    status = "open"
                conn.execute(
                    """
                    UPDATE flags SET last_seen=?, payload=?, severity=?, clean_pulls=0, status=?
                    WHERE id=?
                    """,
                    (now, json.dumps(c["payload"]), c["severity"], status, existing["id"]),
                )
            else:
                cur = conn.execute(
                    """
                    INSERT INTO flags (type, customer_id, campaign_id, severity, payload,
                                       first_seen, last_seen, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        c["type"], c["customer_id"], c["campaign_id"], c["severity"],
                        json.dumps(c["payload"]), now, now,
                    ),
                )
                new_flags.append({"id": cur.lastrowid, **c})

        resolved = 0
        for row in conn.execute(
            "SELECT id, type, customer_id, campaign_id, clean_pulls FROM flags "
            "WHERE status IN ('open','snoozed')"
        ).fetchall():
            key = (row["type"], row["customer_id"], row["campaign_id"])
            if key in candidate_keys:
                continue
            clean = row["clean_pulls"] + 1
            if clean >= RESOLVE_AFTER_CLEAN_PULLS:
                conn.execute(
                    "UPDATE flags SET status='resolved', clean_pulls=?, last_seen=? WHERE id=?",
                    (clean, now, row["id"]),
                )
                resolved += 1
            else:
                conn.execute(
                    "UPDATE flags SET clean_pulls=? WHERE id=?", (clean, row["id"])
                )

    return new_flags, resolved


def run_detectors(conn: sqlite3.Connection) -> tuple[list[dict], int]:
    """Run all detectors and sync the flags table. Returns (new_flags, resolved)."""
    tiers = compute_tiers(conn)
    candidates: list[FlagCandidate] = []
    candidates += detect_troas_drift(conn, tiers)
    candidates += detect_budget_flags(conn, tiers)
    candidates += detect_spend_anomaly(conn, tiers)
    new_flags, resolved = sync_flags(conn, candidates)
    print(
        f"[control_center.detectors] {len(candidates)} conditions, "
        f"{len(new_flags)} new flags, {resolved} resolved",
        file=sys.stderr,
    )
    return new_flags, resolved


if __name__ == "__main__":
    from control_center.store import connect

    conn = connect()
    new, resolved = run_detectors(conn)
    for f in new:
        p = f["payload"]
        print(f"NEW [{f['severity']:>6}] {f['type']:<14} {p.get('campaign_name','')}: {p.get('rationale','')}")
