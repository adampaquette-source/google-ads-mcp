# toolup googleads-mcp — remote MCP server for Claude custom connectors.
# Build context is the repo root (Railway root directory = /).
FROM python:3.11-slim

# Pinned uv, copied from the official distroless image (no pip supply chain).
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /usr/local/bin/uv

RUN useradd --create-home --shell /usr/sbin/nologin app
WORKDIR /app

# Deps first for layer caching; --frozen enforces uv.lock hashes (no resolution
# at build time — the lockfile reviewed in git is exactly what ships).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Runtime code + committed config only. Credentials/, .env, and local state
# are excluded via .dockerignore and must never enter the image.
COPY ads_mcp/ ads_mcp/
COPY mcp_server/ mcp_server/
COPY control_center/ control_center/
COPY stores_mapping.json waste_audit_config.json ./

# /data is the Railway volume mount (audit.db, control_center.db, proposals,
# DCR client store). Railway mounts it root-owned, so the entrypoint chowns it
# and drops to the app user — the server process itself never runs as root.
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && mkdir -p /data && chown -R app:app /data

ENV PYTHONUNBUFFERED=1
# PORT is injected by Railway; server.py selects HTTP transport when it is set.
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "--frozen", "--no-sync", "python", "-m", "mcp_server.server"]
