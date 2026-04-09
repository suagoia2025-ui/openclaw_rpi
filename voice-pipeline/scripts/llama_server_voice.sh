#!/usr/bin/env bash
# Arranca llama-server para usar con VOICE_LLAMA_SERVER_URL (modelo cargado una vez en RAM).
# En otra terminal: source .env && ./scripts/live_mic_pipeline.sh
#
# Requiere: llama-server compilado (make llama-server / cmake target), PHI3_GGUF y .env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi

: "${PHI3_GGUF:?Define PHI3_GGUF en .env (mismo GGUF que usará el servidor)}"
CTX="${VOICE_LLAMA_CTX:-2048}"
THREADS="${VOICE_LLAMA_THREADS:-4}"
PORT="${VOICE_LLAMA_SERVER_PORT:-8080}"
BIN="${LLAMA_SERVER:-${HOME}/llama.cpp/build/bin/llama-server}"

if [[ ! -x "$BIN" && ! -f "$BIN" ]]; then
  echo "No encuentro llama-server en: $BIN" >&2
  echo "Compila llama.cpp con el target llama-server o define LLAMA_SERVER en .env." >&2
  exit 1
fi

echo "[llama-server] $BIN -m \"$PHI3_GGUF\" -c $CTX -t $THREADS --host 127.0.0.1 --port $PORT" >&2
echo "[llama-server] En .env: export VOICE_LLAMA_SERVER_URL=\"http://127.0.0.1:${PORT}\"" >&2
exec "$BIN" -m "$PHI3_GGUF" -c "$CTX" -t "$THREADS" --host 127.0.0.1 --port "$PORT"
