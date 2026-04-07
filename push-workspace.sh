#!/bin/bash
# Envía los archivos del workspace local a la Pi (sobrescribe ~/.openclaw/workspace/ en la Pi)
set -e
HOST="${1:-serv_openclaw@hostopclaw.local}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$SCRIPT_DIR/workspace" ]; then
  echo "No workspace/ folder found. Run ./pull-workspace.sh first."
  exit 1
fi
echo "Pushing workspace to $HOST ..."
scp "$SCRIPT_DIR/workspace"/*.md "$HOST:~/.openclaw/workspace/"
# Si existe la carpeta memory/, subir también (memoria a corto plazo por día)
if [ -d "$SCRIPT_DIR/workspace/memory" ]; then
  ssh "$HOST" "mkdir -p ~/.openclaw/workspace/memory"
  scp "$SCRIPT_DIR/workspace/memory"/*.md "$HOST:~/.openclaw/workspace/memory/" 2>/dev/null || true
fi
echo "Done. Optionally restart the gateway on the Pi: ssh $HOST 'systemctl --user restart openclaw-gateway'"
