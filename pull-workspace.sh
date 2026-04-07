#!/bin/bash
# Trae el workspace de OpenClaw desde la Pi a esta carpeta (openclaw_rpi/workspace/)
set -e
HOST="${1:-serv_openclaw@hostopclaw.local}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/workspace"
echo "Pulling workspace from $HOST ..."
scp -r "$HOST:~/.openclaw/workspace/"* "$SCRIPT_DIR/workspace/" 2>/dev/null || scp -r "$HOST:~/.openclaw/workspace/." "$SCRIPT_DIR/workspace/"
echo "Done. Edit the .md files in workspace/ then run ./push-workspace.sh to send back to the Pi."
