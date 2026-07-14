#!/bin/sh
# Shared-image service dispatch. One Docker image serves two Railway services;
# SERVICE_ROLE picks the process:
#   (unset)          googleads-mcp MCP server (stdio locally, HTTP when PORT set)
#   control-center   Ads Control Center web dashboard (control_center/app.py
#                    handles PORT/proxy headers itself)
# Keep the default branch identical to the historical CMD so the googleads-mcp
# service is unaffected by this file existing.
set -e
if [ "$SERVICE_ROLE" = "control-center" ]; then
    exec uv run --frozen --no-sync python -m control_center.app
fi
exec uv run --frozen --no-sync python -m mcp_server.server
