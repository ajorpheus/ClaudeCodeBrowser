#!/bin/bash
# macOS-adapted installer for ClaudeCodeBrowser.
# The upstream scripts/install.sh is Linux-only: wrong native-messaging path
# (~/.mozilla), no interpreter pinning, and it forgets to copy stdio_wrapper.py.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL="$HOME/.claudecodebrowser"
MANIFEST_DIR="$HOME/Library/Application Support/Mozilla/NativeMessagingHosts"

# 1. Layout + files (upstream install.sh omits stdio_wrapper.py/headless_backend.py)
mkdir -p "$INSTALL"/{native-host,mcp-server,agent,screenshots,logs}
cp "$REPO/native-host/claudecodebrowser_host.py" "$INSTALL/native-host/"
cp "$REPO/mcp-server/"{server.py,stdio_wrapper.py,headless_backend.py,mcp_config.json} "$INSTALL/mcp-server/"
cp "$REPO/agent/browser_agent.py" "$INSTALL/agent/"
chmod +x "$INSTALL/native-host/claudecodebrowser_host.py" \
         "$INSTALL/mcp-server/"{server.py,stdio_wrapper.py} \
         "$INSTALL/agent/browser_agent.py"

# 2. Dedicated venv. Firefox launches the native host with the bare launchd
#    PATH, so `env python3` resolves to /usr/bin/python3 (3.9, no websockets).
/opt/homebrew/bin/python3 -m venv "$INSTALL/venv"
"$INSTALL/venv/bin/pip" -q install websockets

# 3. Pin the host's shebang to the venv; the host and stdio wrapper spawn
#    server.py with sys.executable, so everything inherits this interpreter.
/usr/bin/sed -i '' "1s|.*|#!$INSTALL/venv/bin/python3|" \
    "$INSTALL/native-host/claudecodebrowser_host.py"

# 3b. Default screenshots to the install dir instead of /tmp (wiped on reboot).
/usr/bin/sed -i '' \
    "s|Path('/tmp/claudecodebrowser/screenshots')|Path.home() / '.claudecodebrowser' / 'screenshots'|" \
    "$INSTALL/native-host/claudecodebrowser_host.py" \
    "$INSTALL/mcp-server/server.py"

# 4. Firefox native-messaging manifest (macOS location)
mkdir -p "$MANIFEST_DIR"
cat > "$MANIFEST_DIR/claudecodebrowser.json" <<EOF
{
  "name": "claudecodebrowser",
  "description": "ClaudeCodeBrowser Native Messaging Host",
  "path": "$INSTALL/native-host/claudecodebrowser_host.py",
  "type": "stdio",
  "allowed_extensions": ["claudecodebrowser@ligandal.com"]
}
EOF

# 5. Register the MCP server with Claude Code (user scope). stdio_wrapper
#    auto-starts the HTTP server on 127.0.0.1:8765, so nothing else to launch.
claude mcp add --scope user claudecodebrowser -- \
    "$INSTALL/venv/bin/python3" "$INSTALL/mcp-server/stdio_wrapper.py"

echo
echo "Installed. Final manual step (cannot be scripted):"
echo "  Firefox -> about:debugging -> This Firefox -> Load Temporary Add-on..."
echo "  -> select $REPO/extension/manifest.json"
