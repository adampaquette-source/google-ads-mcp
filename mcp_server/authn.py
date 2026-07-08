"""Authentication for hosted (HTTP) mode — Google OAuth via FastMCP's provider.

stdio mode never imports this module; local Claude Code runs exactly as before.

Fail-closed: when the server is started in HTTP mode (PORT set), authentication
must be fully configured or the process refuses to start. The only escape hatch
is MCP_ALLOW_NO_AUTH=1, for a service that is private at the platform layer
(no public domain, no TCP proxy). Never set it on an exposed service.

Required env (all four, or startup fails):
  GOOGLE_OAUTH_CLIENT_ID      Google Cloud OAuth web-app client ID
  GOOGLE_OAUTH_CLIENT_SECRET  its secret (set in Railway variables, never in git)
  MCP_BASE_URL                public https base URL of this service
  MCP_JWT_SIGNING_KEY         stable random secret; also keys the encrypted
                              DCR client-registration store (FASTMCP_HOME)
"""

import os

from fastmcp.server.auth.providers.google import GoogleProvider


class AuthConfigError(RuntimeError):
    pass


_REQUIRED = (
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "MCP_BASE_URL",
    "MCP_JWT_SIGNING_KEY",
)


def build_auth() -> GoogleProvider | None:
    """Build the auth provider for HTTP mode, or None if explicitly disabled."""
    values = {name: os.environ.get(name) for name in _REQUIRED}

    if not any(values.values()):
        if os.environ.get("MCP_ALLOW_NO_AUTH") == "1":
            return None
        raise AuthConfigError(
            "HTTP mode requires Google OAuth configuration "
            f"({', '.join(_REQUIRED)}). MCP_ALLOW_NO_AUTH=1 may only be set "
            "on a platform-private service with no public domain."
        )

    missing = [name for name, value in values.items() if not value]
    if missing:
        raise AuthConfigError(f"Incomplete auth configuration, missing: {missing}")

    return GoogleProvider(
        client_id=values["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=values["GOOGLE_OAUTH_CLIENT_SECRET"],
        base_url=values["MCP_BASE_URL"],
        jwt_signing_key=values["MCP_JWT_SIGNING_KEY"],
        required_scopes=["openid", "email"],
    )
