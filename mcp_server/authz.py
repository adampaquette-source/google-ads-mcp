"""Role-based authorization + actor-attributed audit for hosted (HTTP) mode.

Default-deny: an identity not present in the role map sees zero tools and
cannot call any.

MCP_ROLE_MAP is a JSON object of email -> grant. A grant is either a role
string or an object with per-tool overrides:

  {
    "admin@x.com":   "admin",
    "viewer@x.com":  "viewer",
    "ops@x.com":     {"base": "admin",  "deny":  ["shopify_delete_*"]},
    "analyst@x.com": {"base": "viewer", "allow": ["run_waste_audit"]}
  }

  base   admin (every tool) | viewer (readOnlyHint tools only) | none
  allow  extra tool names granted on top of base (fnmatch patterns OK)
  deny   tool names removed regardless of base/allow — deny always wins

MCP_ADMIN_ONLY_TOOLS (optional, comma-separated fnmatch patterns, e.g.
"commit_*") names tools that only a base=admin grant may use — an allow list
can never grant them. Use it to keep approval-gated writes above the
per-tool override mechanism.

Emails are matched case-insensitively and must be verified by Google
(email_verified claim) to count. A malformed MCP_ROLE_MAP aborts startup
(fail-closed) rather than silently granting nothing/everything.

MCP_RATE_LIMIT_PER_MIN (default 120, 0 disables) caps tool calls per actor
per rolling minute. MCP_TOOL_DAILY_CAPS (JSON tool-name -> int, fnmatch
patterns OK) caps calls per actor per UTC day for cost-bearing tools. Both
are enforced only for calls authorization already permits.

Every tool call is audited as a JSON line to stdout (captured by Railway
logs) and, when MCP_HTTP_AUDIT_PATH is set, appended to that file.
"""

import json
import os
import sys
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from fnmatch import fnmatch

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext

_BASES = {"admin", "viewer", "none"}


@dataclass(frozen=True)
class _Grant:
    base: str
    allow: tuple = field(default_factory=tuple)
    deny: tuple = field(default_factory=tuple)


def _parse_grant(email: str, raw) -> _Grant:
    if isinstance(raw, str):
        if raw not in _BASES - {"none"}:
            raise ValueError(f"MCP_ROLE_MAP: unknown role {raw!r} for {email!r}")
        return _Grant(base=raw)
    if isinstance(raw, dict):
        unknown = set(raw) - {"base", "allow", "deny"}
        if unknown:
            raise ValueError(f"MCP_ROLE_MAP: unknown keys {sorted(unknown)} for {email!r}")
        base = raw.get("base", "none")
        if base not in _BASES:
            raise ValueError(f"MCP_ROLE_MAP: unknown base {base!r} for {email!r}")
        allow = raw.get("allow", [])
        deny = raw.get("deny", [])
        for name, val in (("allow", allow), ("deny", deny)):
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                raise ValueError(f"MCP_ROLE_MAP: {name!r} for {email!r} must be a list of strings")
        return _Grant(base=base, allow=tuple(allow), deny=tuple(deny))
    raise ValueError(f"MCP_ROLE_MAP: grant for {email!r} must be a string or object")


def _load_role_map() -> dict[str, _Grant]:
    raw = os.environ.get("MCP_ROLE_MAP", "")
    if not raw:
        return {}
    parsed = json.loads(raw)
    return {
        email.strip().lower(): _parse_grant(email, grant)
        for email, grant in parsed.items()
    }


def _load_admin_only() -> tuple:
    raw = os.environ.get("MCP_ADMIN_ONLY_TOOLS", "")
    return tuple(p.strip() for p in raw.split(",") if p.strip())


_ROLE_MAP = _load_role_map()
_ADMIN_ONLY = _load_admin_only()


# ── Rate limiting and per-tool daily caps ────────────────────────────────────
#
# Both are per-authenticated-actor (by verified email) and live in process
# memory. The HTTP servers run as a single uvicorn process, so a plain dict is
# a correct, sufficient store — no external cache needed. State resets on
# redeploy, which is acceptable for an abuse/runaway backstop.
#
#   MCP_RATE_LIMIT_PER_MIN  max tool calls per actor per rolling 60s.
#                           Default 120. Set to 0 to disable.
#   MCP_TOOL_DAILY_CAPS     JSON object of tool-name (fnmatch) -> max calls per
#                           actor per UTC day. Empty/unset means no caps. Use it
#                           for cost-bearing tools, e.g. on imagegen:
#                             {"generate_image": 300, "edit_image": 300}


def _per_min_limit() -> int:
    try:
        return int(os.environ.get("MCP_RATE_LIMIT_PER_MIN", "120") or "0")
    except ValueError:
        return 120


def _load_daily_caps() -> list[tuple[str, int]]:
    raw = os.environ.get("MCP_TOOL_DAILY_CAPS", "")
    if not raw:
        return []
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return []
    caps: list[tuple[str, int]] = []
    for pattern, cap in obj.items():
        try:
            caps.append((pattern, int(cap)))
        except (ValueError, TypeError):
            continue
    return caps


_RATE_PER_MIN = _per_min_limit()
_DAILY_CAPS = _load_daily_caps()

_call_times: dict[str, deque] = defaultdict(deque)
_daily_day: str | None = None
_daily_counts: dict[tuple[str, str], int] = {}


def _daily_cap_for(tool_name: str) -> int | None:
    matching = [cap for pattern, cap in _DAILY_CAPS if fnmatch(tool_name, pattern)]
    return min(matching) if matching else None


def _roll_day() -> None:
    global _daily_day
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if today != _daily_day:
        _daily_day = today
        _daily_counts.clear()


def _throttle_reason(email: str | None, tool_name: str) -> str | None:
    """Check per-day cap and per-minute rate for this actor+tool.

    Returns a human-readable reason when the call must be rejected, else None.
    On None it also consumes one unit from each active budget (check-and-commit
    in a single synchronous pass — safe in this single-process server)."""
    actor = (email or "?").lower()

    cap = _daily_cap_for(tool_name)
    if cap is not None:
        _roll_day()
        if _daily_counts.get((actor, tool_name), 0) >= cap:
            return f"daily cap of {cap} call(s) for {tool_name} reached for this identity"

    if _RATE_PER_MIN > 0:
        now = time.monotonic()
        window = _call_times[actor]
        cutoff = now - 60
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= _RATE_PER_MIN:
            return f"rate limit of {_RATE_PER_MIN} calls/min exceeded for this identity"
        window.append(now)

    if cap is not None:
        _daily_counts[(actor, tool_name)] = _daily_counts.get((actor, tool_name), 0) + 1

    return None


def _matches(name: str, patterns: tuple) -> bool:
    return any(fnmatch(name, p) for p in patterns)


def _grant_allows(grant: _Grant | None, tool_name: str, tool_is_read_only: bool) -> bool:
    if grant is None:
        return False
    if _matches(tool_name, grant.deny):
        return False
    if grant.base == "admin":
        return True
    # Admin-only tools cannot be reached below a base=admin grant — not via
    # viewer read-only inheritance and not via an allow list.
    if _matches(tool_name, _ADMIN_ONLY):
        return False
    if grant.base == "viewer" and tool_is_read_only:
        return True
    return _matches(tool_name, grant.allow)


def _actor() -> tuple[str | None, _Grant | None]:
    """Return (email, grant) for the current request; (None, None) if unmapped."""
    token = get_access_token()
    if token is None:
        return None, None
    claims = token.claims or {}
    email = claims.get("email")
    if not email or not claims.get("email_verified"):
        return None, None
    email = email.strip().lower()
    return email, _ROLE_MAP.get(email)


def _tool_is_read_only(tool) -> bool:
    annotations = getattr(tool, "annotations", None)
    return bool(annotations and getattr(annotations, "readOnlyHint", False))


def _audit(record: dict) -> None:
    line = json.dumps(record, separators=(",", ":"))
    print(line, file=sys.stdout, flush=True)
    path = os.environ.get("MCP_HTTP_AUDIT_PATH")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class RoleAuthzMiddleware(Middleware):
    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        _, grant = _actor()
        return [
            t for t in tools
            if _grant_allows(grant, t.name, _tool_is_read_only(t))
        ]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        email, grant = _actor()
        tool_name = context.message.name
        allowed = _grant_allows(
            grant, tool_name, await _is_read_only_tool_name(context, tool_name)
        )
        # Only charge the rate/quota budgets for calls that authorization would
        # otherwise permit — a denied call must not consume an actor's quota.
        throttle = _throttle_reason(email, tool_name) if allowed else None
        _audit(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "actor": email,
                "role": grant.base if grant else None,
                "tool": tool_name,
                "allowed": allowed and throttle is None,
                "throttled": throttle,
            }
        )
        if not allowed:
            raise ToolError(
                f"Not authorized: identity {email or 'unknown'} may not call {tool_name}."
            )
        if throttle:
            raise ToolError(f"Throttled: {throttle}. Try again later.")
        return await call_next(context)


async def _is_read_only_tool_name(context: MiddlewareContext, tool_name: str) -> bool:
    server = context.fastmcp_context.fastmcp if context.fastmcp_context else None
    if server is None:
        return False
    try:
        tool = await server.get_tool(tool_name)
    except Exception:
        return False
    return _tool_is_read_only(tool)
