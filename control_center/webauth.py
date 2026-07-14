"""Web UI authentication for hosted (Railway) mode: Google OAuth + signed session.

Local mode (no PORT env var) never activates any of this; the app serves on
127.0.0.1 exactly as before. Hosted mode is fail-closed: if PORT is set and the
auth configuration is incomplete, startup raises. The only escape hatch is
ADS_CC_ALLOW_NO_AUTH=1, for a platform-private service with no public domain.

This mirrors the connector auth model (mcp_server/authn.py + authz.py) for a
browser instead of an MCP client: the same Google OAuth client authenticates,
and a default-deny email role map authorizes. No new dependencies; the OAuth
code flow is a confidential server flow done with httpx, and the session is an
HMAC-signed cookie (stdlib hmac).

Required env in hosted mode:
  GOOGLE_OAUTH_CLIENT_ID      shared Google OAuth client (same as connectors)
  GOOGLE_OAUTH_CLIENT_SECRET  its secret
  ADS_CC_BASE_URL             public https base URL of this service
  ADS_CC_SESSION_SECRET       fresh random secret per service (openssl rand -hex 32)
  ADS_CC_ROLE_MAP             JSON email -> "admin" | "viewer"; unmapped = no access

The Google client needs https://<domain>/auth/callback added to its
authorized redirect URIs.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.parse

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

SESSION_COOKIE = "cc_session"
SESSION_TTL_SECONDS = 24 * 3600
STATE_TTL_SECONDS = 600

_REQUIRED = (
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "ADS_CC_BASE_URL",
    "ADS_CC_SESSION_SECRET",
    "ADS_CC_ROLE_MAP",
)

# Paths that never require a session. /health is the Railway healthcheck;
# /static is css/js only.
_PUBLIC_PREFIXES = ("/health", "/auth/", "/static/")


class AuthConfigError(RuntimeError):
    pass


class WebAuthConfig:
    def __init__(self) -> None:
        self.client_id = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
        self.client_secret = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
        self.base_url = os.environ["ADS_CC_BASE_URL"].rstrip("/")
        self.session_secret = os.environ["ADS_CC_SESSION_SECRET"].encode()
        try:
            role_map = json.loads(os.environ["ADS_CC_ROLE_MAP"])
        except json.JSONDecodeError as exc:
            raise AuthConfigError(f"ADS_CC_ROLE_MAP is not valid JSON: {exc}") from exc
        if not isinstance(role_map, dict) or not role_map:
            raise AuthConfigError("ADS_CC_ROLE_MAP must be a non-empty JSON object")
        bad = {r for r in role_map.values() if r not in ("admin", "viewer")}
        if bad:
            raise AuthConfigError(f"ADS_CC_ROLE_MAP has unknown roles: {sorted(bad)}")
        self.role_map = {email.strip().lower(): role for email, role in role_map.items()}

    @property
    def redirect_uri(self) -> str:
        return f"{self.base_url}/auth/callback"

    def role_for(self, email: str) -> str | None:
        return self.role_map.get(email.strip().lower())


def build_web_auth() -> WebAuthConfig | None:
    """Build the auth config for hosted mode, or None if explicitly disabled.

    Fail-closed: raises AuthConfigError unless configuration is complete or
    ADS_CC_ALLOW_NO_AUTH=1 is set (platform-private services only).
    """
    values = {name: os.environ.get(name) for name in _REQUIRED}

    if not any(values.values()):
        if os.environ.get("ADS_CC_ALLOW_NO_AUTH") == "1":
            print(
                "[control_center.webauth] AUTH DISABLED (ADS_CC_ALLOW_NO_AUTH=1). "
                "Only acceptable on a platform-private service with no domain.",
                file=sys.stderr,
            )
            return None
        raise AuthConfigError(
            "Hosted mode requires web auth configuration "
            f"({', '.join(_REQUIRED)}). ADS_CC_ALLOW_NO_AUTH=1 may only be set "
            "on a platform-private service with no public domain."
        )

    missing = [name for name, value in values.items() if not value]
    if missing:
        raise AuthConfigError(f"Incomplete web auth configuration, missing: {missing}")
    return WebAuthConfig()


# ---------------------------------------------------------------------------
# Signed tokens (session cookie + OAuth state), stdlib only
# ---------------------------------------------------------------------------

def _sign(secret: bytes, payload: bytes) -> str:
    mac = hmac.new(secret, payload, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(payload).decode().rstrip("=")
        + "."
        + base64.urlsafe_b64encode(mac).decode().rstrip("=")
    )


def _verify(secret: bytes, token: str) -> bytes | None:
    try:
        payload_b64, mac_b64 = token.split(".", 1)
        payload = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4))
        mac = base64.urlsafe_b64decode(mac_b64 + "=" * (-len(mac_b64) % 4))
    except Exception:
        return None
    expected = hmac.new(secret, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        return None
    return payload


def make_session_token(config: WebAuthConfig, email: str, role: str) -> str:
    payload = json.dumps(
        {"email": email, "role": role, "exp": int(time.time()) + SESSION_TTL_SECONDS}
    ).encode()
    return _sign(config.session_secret, payload)


def read_session(config: WebAuthConfig, request: Request) -> dict | None:
    """Return {email, role} for a valid, unexpired, still-authorized session."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    payload = _verify(config.session_secret, token)
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if data.get("exp", 0) < time.time():
        return None
    email = data.get("email", "")
    # Re-check the role map on every request so removing an email from
    # ADS_CC_ROLE_MAP revokes access at the next request, not at cookie expiry.
    role = config.role_for(email)
    if role is None:
        return None
    return {"email": email, "role": role}


# ---------------------------------------------------------------------------
# OAuth routes
# ---------------------------------------------------------------------------

def make_auth_routes(config: WebAuthConfig):
    """Return the /auth/* route handlers bound to this config."""

    def login(request: Request) -> Response:
        state_payload = json.dumps(
            {"nonce": secrets.token_urlsafe(16), "exp": int(time.time()) + STATE_TTL_SECONDS}
        ).encode()
        state = _sign(config.session_secret, state_payload)
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": "openid email",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}")

    def callback(request: Request) -> Response:
        state = request.query_params.get("state", "")
        code = request.query_params.get("code", "")
        payload = _verify(config.session_secret, state)
        if payload is None or json.loads(payload).get("exp", 0) < time.time():
            return PlainTextResponse("Invalid or expired login state. Try again.", 400)
        if not code:
            return PlainTextResponse("Google login was cancelled or failed.", 400)

        token_resp = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "redirect_uri": config.redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        if token_resp.status_code != 200:
            print(
                f"[control_center.webauth] token exchange failed: "
                f"{token_resp.status_code} {token_resp.text[:200]}",
                file=sys.stderr,
            )
            return PlainTextResponse("Google token exchange failed.", 502)
        access_token = token_resp.json().get("access_token", "")

        userinfo_resp = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if userinfo_resp.status_code != 200:
            return PlainTextResponse("Could not fetch Google account info.", 502)
        info = userinfo_resp.json()
        email = (info.get("email") or "").strip().lower()
        if not email or not info.get("email_verified"):
            return PlainTextResponse("Google account has no verified email.", 403)

        role = config.role_for(email)
        if role is None:
            # Default-deny: authenticated but not authorized.
            print(
                f"[control_center.webauth] denied unmapped email: {email}",
                file=sys.stderr,
            )
            return PlainTextResponse(
                f"{email} is not authorized for the Ads Control Center. "
                "Ask Adam to add you to the role map.",
                403,
            )

        print(
            "[control_center.webauth] "
            + json.dumps({"event": "login", "email": email, "role": role}),
            file=sys.stderr,
        )
        response = RedirectResponse("/", status_code=302)
        response.set_cookie(
            SESSION_COOKIE,
            make_session_token(config, email, role),
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            secure=config.base_url.startswith("https://"),
            samesite="lax",
        )
        return response

    def logout(request: Request) -> Response:
        response = RedirectResponse("/auth/login", status_code=302)
        response.delete_cookie(SESSION_COOKIE)
        return response

    return login, callback, logout


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def is_public_path(path: str) -> bool:
    return path == "/health" or any(
        path.startswith(p) for p in _PUBLIC_PREFIXES if p != "/health"
    )


class SessionAuthMiddleware:
    """Pure ASGI middleware: every non-public request needs a valid session."""

    def __init__(self, app, config: WebAuthConfig) -> None:
        self.app = app
        self.config = config

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or is_public_path(scope["path"]):
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        session = read_session(self.config, request)
        if session is None:
            if scope["method"] in ("GET", "HEAD"):
                response: Response = RedirectResponse("/auth/login", status_code=302)
            else:
                response = JSONResponse({"error": "not authenticated"}, status_code=401)
            await response(scope, receive, send)
            return
        scope.setdefault("state", {})
        scope["state"]["user_email"] = session["email"]
        scope["state"]["user_role"] = session["role"]
        await self.app(scope, receive, send)


class ReadOnlyMiddleware:
    """Reject every mutating request. Hosted mode is read-only until the real
    approval gate (G5) and CSRF protection (G6) exist; see
    HOSTING_MIGRATION_PLAN.md Section 3. Runs before auth so a leaked session
    still cannot mutate anything."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] == "http"
            and scope["method"] not in ("GET", "HEAD", "OPTIONS")
            and not scope["path"].startswith("/auth/")
        ):
            response = PlainTextResponse(
                "This hosted Control Center is view-only. Commits, staging, "
                "snoozes, and manual pulls run on the local instance until the "
                "approval gate (G5) and CSRF protection (G6) ship.",
                status_code=403,
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
