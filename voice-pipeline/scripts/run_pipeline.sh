#!/usr/bin/env bash
# Uso: ./run_pipeline.sh entrada.wav [-o salida.wav] [--log-dir DIR]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi
exec python3 "$ROOT/scripts/voice_pipeline.py" "$@"
