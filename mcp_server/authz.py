"""Role-based authorization + actor-attributed audit for hosted (HTTP) mode.

Default-deny: an identity not present in the role map sees zero tools and
cannot call any. Roles:
  admin   every tool
  viewer  only tools annotated readOnlyHint=True

MCP_ROLE_MAP is a JSON object of email -> role, e.g.
  {"adam.paquette@pcstools.com": "admin", "someone@pcstools.com": "viewer"}
Emails are matched case-insensitively and must be verified by Google
(email_verified claim) to count.

Every tool call is audited as a JSON line to stdout (captured by Railway
logs) and, when MCP_HTTP_AUDIT_PATH is set, appended to that file.
"""

import json
import os
import sys
import time

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext

_READ_ONLY_ROLES = {"viewer"}
_ALL_TOOL_ROLES = {"admin"}
_VALID_ROLES = _READ_ONLY_ROLES | _ALL_TOOL_ROLES


def _load_role_map() -> dict[str, str]:
    raw = os.environ.get("MCP_ROLE_MAP", "")
    if not raw:
        return {}
    parsed = json.loads(raw)
    role_map = {}
    for email, role in parsed.items():
        if role not in _VALID_ROLES:
            raise ValueError(f"MCP_ROLE_MAP: unknown role {role!r} for {email!r}")
        role_map[email.strip().lower()] = role
    return role_map


def _actor() -> tuple[str | None, str | None]:
    """Return (email, role) for the current request; (None, None) if unmapped."""
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


_ROLE_MAP = _load_role_map()


class RoleAuthzMiddleware(Middleware):
    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        _, role = _actor()
        if role in _ALL_TOOL_ROLES:
            return tools
        if role in _READ_ONLY_ROLES:
            return [t for t in tools if _tool_is_read_only(t)]
        return []

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        email, role = _actor()
        tool_name = context.message.name
        allowed = role in _ALL_TOOL_ROLES or (
            role in _READ_ONLY_ROLES
            and await _is_read_only_tool_name(context, tool_name)
        )
        _audit(
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "actor": email,
                "role": role,
                "tool": tool_name,
                "allowed": allowed,
            }
        )
        if not allowed:
            raise ToolError(
                f"Not authorized: identity {email or 'unknown'} may not call {tool_name}."
            )
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
