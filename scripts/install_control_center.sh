#!/bin/zsh
# Deploy and (re)start the Ads Control Center launchd agent.
#
# The service CANNOT run from the Dropbox CloudStorage folder: macOS blocks
# background launchd processes from reading the File Provider mount (python
# hangs during interpreter startup), and cloud sync corrupts SQLite WAL files.
# So this script deploys a runtime copy to ~/Library/Application Support and
# points launchd there. Re-run it after any code change to redeploy.
#
# Usage: ./scripts/install_control_center.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASE_DIR="$HOME/Library/Application Support/ads-control-center"
APP_DIR="$BASE_DIR/app"
PLIST_DST="$HOME/Library/LaunchAgents/com.toolup.ads-control-center.plist"
LABEL="com.toolup.ads-control-center"
LOG="$HOME/Library/Logs/ads-control-center.log"

echo "Deploying code to $APP_DIR"
mkdir -p "$APP_DIR"
rsync -a --delete \
  "$PROJECT_DIR/ads_mcp" \
  "$PROJECT_DIR/control_center" \
  "$PROJECT_DIR/mcp_server" \
  "$APP_DIR/"
rsync -a \
  "$PROJECT_DIR/pyproject.toml" \
  "$PROJECT_DIR/uv.lock" \
  "$PROJECT_DIR/stores_mapping.json" \
  "$PROJECT_DIR/waste_audit_config.json" \
  "$APP_DIR/"
[ -f "$PROJECT_DIR/README.md" ] && rsync -a "$PROJECT_DIR/README.md" "$APP_DIR/" || true

# Secrets: .env, service account key, Shopify MCP credentials
rsync -a "$PROJECT_DIR/.env" "$APP_DIR/.env"
rsync -a --delete "$PROJECT_DIR/credentials" "$APP_DIR/"
rsync -a --delete "$PROJECT_DIR/shopify_mcp" "$APP_DIR/"
chmod -R go-rwx "$APP_DIR/credentials" "$APP_DIR/shopify_mcp" "$APP_DIR/.env"

# The deployed service keeps its own audit.db next to the control center DB
# (writing the project audit.db would hit the same File Provider block).
if ! grep -q "^ADS_MCP_AUDIT_LOG_PATH=$BASE_DIR" "$APP_DIR/.env"; then
  sed -i '' "s|^ADS_MCP_AUDIT_LOG_PATH=.*|ADS_MCP_AUDIT_LOG_PATH=$BASE_DIR/audit.db|" "$APP_DIR/.env"
fi

echo "Building venv"
cd "$APP_DIR"
uv sync --quiet

echo "Installing launchd agent"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST_DST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$APP_DIR/.venv/bin/python</string>
        <string>-m</string>
        <string>control_center.app</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$APP_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG</string>
    <key>StandardErrorPath</key>
    <string>$LOG</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
# bootout is async; bootstrap can hit an I/O error if the old job is still
# unloading. Retry a few times before giving up.
for attempt in 1 2 3 4 5; do
  if launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null; then
    break
  fi
  if [ "$attempt" -eq 5 ]; then
    echo "bootstrap failed after 5 attempts" >&2
    exit 1
  fi
  sleep 2
done
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL"
echo "Dashboard: http://localhost:8770"
echo "Logs: $LOG"
