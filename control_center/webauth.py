"""Browser authentication + hosted-mode gating for the control center web UI.

Local mode (no PORT env var, launchd on the Mac) is completely untouched: no
auth, no CSRF, binds 127.0.0.1, every route behaves exactly as before.

Hosted mode (PORT set, Railway) is fail-closed:

  - Startup refuses to serve unless the full auth config is present
    (CC_ALLOW_NO_AUTH=1 is the only escape hatch, for a platform-private
    service with no public domain -- never set it on an exposed service).
  - Every route except /health, /static, and the login flow requires a
    signed session cookie obtained via Google OAuth (openid email).
  - Identity is authenticated by Google but authorized here: the email must
    appear in CC_ROLE_MAP or the login is rejected. Default-deny.
  - The dashboard is READ-ONLY: every POST returns 403 except /pull
    (admin role only). Google Ads writes (stage/commit/negatives commit)
    stay local-only until the G5 approval gate and G6 CSRF work is complete.
    This is deliberate: decisions recorded on the hosted DB would be
    invisible to the local instance where commits actually run.
  - CSRF: state-changing requests must echo the session's CSRF token
    (X-CSRF-Token header or csrf form field). htmx picks it up from the
    body hx-headers attribute; plain forms carry a hidden input.
  - Every allowed/denied POST is logged as a JSON line with the actor email
    (G4 actor attribution for the read-only surface).

Required env in hosted mode:
  GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET  Google web-app OAuth
      client (shared with the googleads-mcp service; the CC callback URL must
      be added to its authorized redirect URIs).
  CC_BASE_URL          public https base URL of this service
  CC_SESSION_SECRET    stable random secret; signs sessions and OAuth state
  CC_ROLE_MAP          JSON {email: "admin"|"viewer"}; emails matched
                       case-insensitively; must be non-empty

Sessions are HMAC-SHA256-signed cookies (stdlib only, no new dependencies),
12 hour lifetime, Secure + HttpOnly + SameSite=Lax.
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
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

SESSION_COOKIE = "cc_session"
SESSION_TTL_SECONDS = 12 * 3600
STATE_TTL_SECONDS = 600

_ROLES = ("admin", "viewer")

# Paths that never require a session.
_PUBLIC_PATHS = ("/health", "/login", "/logout", "/auth/start", "/auth/callback")
_PUBLIC_PREFIXES = ("/static/",)

# The only POST the hosted read-only dashboard accepts (admin role).
_HOSTED_ALLOWED_POSTS = ("/pull",)

READ_ONLY_MESSAGE = (
    "The hosted control center is read-only. Google Ads writes and queue "
    "decisions stay on the local instance until the G5 approval gate ships."
)


class WebAuthConfigError(RuntimeError):
    pass


def hosted_mode() -> bool:
    return bool(os.environ.get("PORT"))


def _secret() -> bytes:
    return os.environ["CC_SESSION_SECRET"].encode()


def load_role_map() -> dict[str, str]:
    raw = os.environ.get("CC_ROLE_MAP", "")
    if not raw:
        return {}
    parsed = json.loads(raw)
    out: dict[str, str] = {}
    for email, role in parsed.items():
        if role not in _ROLES:
            raise WebAuthConfigError(
                f"CC_ROLE_MAP: unknown role {role!r} for {email!r} (want admin or viewer)"
            )
        out[email.strip().lower()] = role
    return out


def validate_config() -> None:
    """Fail-closed startup check for hosted mode. No-op locally."""
    if not hosted_mode():
        return
    if os.environ.get("CC_ALLOW_NO_AUTH") == "1":
        print(
            "[control_center.webauth] WARNING: CC_ALLOW_NO_AUTH=1, serving without "
            "authentication. Only acceptable on a platform-private service.",
            file=sys.stderr,
        )
        return
    required = (
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "CC_BASE_URL",
        "CC_SESSION_SECRET",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise WebAuthConfigError(
            f"Hosted mode requires web auth configuration; missing: {missing}. "
            "Set CC_ALLOW_NO_AUTH=1 only for a platform-private service."
        )
    if len(os.environ["CC_SESSION_SECRET"]) < 32:
        raise WebAuthConfigError("CC_SESSION_SECRET must be at least 32 characters.")
    if not load_role_map():
        raise WebAuthConfigError(
            "CC_ROLE_MAP is empty or unset; nobody could log in. Default-deny "
            'requires an explicit allowlist, e.g. {"you@company.com": "admin"}.'
        )


def auth_enabled() -> bool:
    return hosted_mode() and os.environ.get("CC_ALLOW_NO_AUTH") != "1"


# ---------------------------------------------------------------------------
# Signed payloads (sessions and OAuth state) -- stdlib HMAC, no dependencies
# ---------------------------------------------------------------------------

def _sign(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_secret(), body, hashlib.sha256).digest()
    return (body + b"." + base64.urlsafe_b64encode(sig)).decode()


def _verify(token: str) -> dict | None:
    try:
        body_b64, sig_b64 = token.encode().rsplit(b".", 1)
        expected = hmac.new(_secret(), body_b64, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, base64.urlsafe_b64decode(sig_b64)):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _make_session(email: str, role: str) -> str:
    return _sign(
        {
            "email": email,
            "role": role,
            "csrf": secrets.token_hex(16),
            "exp": time.time() + SESSION_TTL_SECONDS,
        }
    )


def read_session(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    session = _verify(token)
    if session is None:
        return None
    # Revocation check on every request: dropping an email from CC_ROLE_MAP
    # (and redeploying) invalidates their live sessions too.
    role = load_role_map().get(session.get("email", ""))
    if role is None or role != session.get("role"):
        return None
    return session


# ---------------------------------------------------------------------------
# OAuth login flow
# ---------------------------------------------------------------------------

_LOGIN_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Ads Control Center</title>
<link rel="stylesheet" href="/static/tabler.min.css"></head>
<body data-bs-theme="dark"><div class="page page-center"><div class="container container-tight py-4">
<div class="card card-md"><div class="card-body text-center">
<h2 class="mb-3">Ads Control Center</h2>
<p class="text-secondary">{message}</p>
<a class="btn btn-primary w-100" href="/auth/start">Sign in with Google</a>
</div></div></div></div></body></html>"""


def login(request: Request):
    if not auth_enabled():
        return RedirectResponse("/", status_code=303)
    message = "Sign in with your work Google account to continue."
    if request.query_params.get("denied"):
        message = "That Google account is not authorized for this dashboard."
    return HTMLResponse(_LOGIN_PAGE.format(message=message), status_code=200)


def auth_start(request: Request):
    state = _sign({"nonce": secrets.token_hex(8), "exp": time.time() + STATE_TTL_SECONDS})
    params = {
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "redirect_uri": _callback_url(),
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}", status_code=302)


def _callback_url() -> str:
    return os.environ["CC_BASE_URL"].rstrip("/") + "/auth/callback"


async def auth_callback(request: Request):
    state = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    if not code or _verify(state) is None:
        return HTMLResponse("Invalid or expired login attempt. <a href='/login'>Retry</a>", 400)

    async with httpx.AsyncClient(timeout=15.0) as http:
        token_resp = await http.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _callback_url(),
            },
        )
    if token_resp.status_code != 200:
        print(
            f"[control_center.webauth] token exchange failed: {token_resp.status_code}",
            file=sys.stderr,
        )
        return HTMLResponse("Login failed at token exchange. <a href='/login'>Retry</a>", 400)

    # The id_token arrives directly from Google's token endpoint over TLS, so
    # its payload is trusted without local signature verification (OIDC core
    # 3.1.3.7 note); audience and issuer are still checked.
    try:
        claims = _decode_jwt_payload(token_resp.json()["id_token"])
    except Exception:
        return HTMLResponse("Login failed: malformed token response.", 400)
    if claims.get("aud") != os.environ["GOOGLE_OAUTH_CLIENT_ID"] or claims.get("iss") not in (
        "https://accounts.google.com",
        "accounts.google.com",
    ):
        return HTMLResponse("Login failed: token audience/issuer mismatch.", 400)

    email = (claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        return RedirectResponse("/login?denied=1", status_code=303)
    role = load_role_map().get(email)
    _audit_line({"event": "login", "actor": email, "allowed": role is not None})
    if role is None:
        return RedirectResponse("/login?denied=1", status_code=303)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        _make_session(email, role),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


def logout(request: Request):
    response = RedirectResponse("/login" if auth_enabled() else "/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


def _decode_jwt_payload(jwt: str) -> dict:
    payload_b64 = jwt.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64))


def _audit_line(record: dict) -> None:
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}
    print(json.dumps(record, separators=(",", ":")), file=sys.stdout, flush=True)


# ---------------------------------------------------------------------------
# Middleware: session requirement + hosted read-only gating + CSRF
# ---------------------------------------------------------------------------

class WebAuthMiddleware:
    """Pure ASGI middleware: session auth, hosted read-only gating, CSRF.

    Local mode (no PORT): passes everything through untouched, full access.
    Hosted mode: session required (unless CC_ALLOW_NO_AUTH=1), and the
    read-only POST gate applies even when auth is disabled -- a platform-
    private deployment still must not expose Google Ads writes.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        if not hosted_mode():
            state.update(actor_email="", actor_role="admin", read_only=False, csrf_token="")
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path
        state.update(actor_email="", actor_role="admin", read_only=True, csrf_token="")

        if auth_enabled():
            if path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
                await self.app(scope, receive, send)
                return
            session = read_session(request)
            if session is None:
                response = (
                    JSONResponse({"error": "authentication required"}, status_code=401)
                    if request.headers.get("hx-request")
                    else RedirectResponse("/login", status_code=303)
                )
                await response(scope, receive, send)
                return
            state.update(
                actor_email=session["email"],
                actor_role=session["role"],
                csrf_token=session["csrf"],
            )
        else:
            session = None

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            receive, supplied_csrf = await _buffer_csrf(request, receive)
            csrf_ok = (
                hmac.compare_digest(supplied_csrf, session["csrf"])
                if session and supplied_csrf
                else session is None
            )
            allowed = (
                path in _HOSTED_ALLOWED_POSTS
                and state["actor_role"] == "admin"
                and csrf_ok
            )
            _audit_line(
                {
                    "event": "mutating_request",
                    "actor": state["actor_email"],
                    "role": state["actor_role"],
                    "method": request.method,
                    "path": path,
                    "allowed": allowed,
                }
            )
            if not allowed:
                response = HTMLResponse(READ_ONLY_MESSAGE, status_code=403)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


async def _buffer_csrf(request: Request, receive: Receive) -> tuple[Receive, str]:
    """Read the CSRF token from header or urlencoded body without losing the body.

    Mutating requests here are tiny htmx/form posts, so buffering is safe. The
    original body is replayed to the downstream app via a wrapped receive.
    """
    supplied = request.headers.get("x-csrf-token", "")

    body = b""
    more = True
    while more:
        message = await receive()
        body += message.get("body", b"")
        more = message.get("more_body", False)

    if not supplied and "application/x-www-form-urlencoded" in request.headers.get(
        "content-type", ""
    ):
        try:
            parsed = urllib.parse.parse_qs(body.decode())
            supplied = (parsed.get("csrf") or [""])[0]
        except Exception:
            supplied = ""

    replayed = False

    async def replay() -> dict:
        nonlocal replayed
        if not replayed:
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return replay, supplied
