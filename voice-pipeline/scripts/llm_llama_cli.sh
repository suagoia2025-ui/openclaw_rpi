#!/usr/bin/env bash
# Prueba aislada LLM: un prompt en stdin (o primer argumento) → respuesta en stdout.
# Requiere: LLAMA_COMPLETION (o LLAMA_CLI), PHI3_GGUF; opcional VOICE_LLAMA_CTX, VOICE_LLAMA_MAX_TOKENS
set -euo pipefail
: "${PHI3_GGUF:?}"
LLAMA_BIN="${LLAMA_COMPLETION:-${LLAMA_CLI:-}}"
[[ -n "$LLAMA_BIN" ]] || { echo "Define LLAMA_COMPLETION o LLAMA_CLI" >&2; exit 1; }
CTX="${VOICE_LLAMA_CTX:-2048}"
NTOK="${VOICE_LLAMA_MAX_TOKENS:-128}"
if [[ -n "${1:-}" ]]; then
  PROMPT="$1"
else
  PROMPT="$(cat)"
fi
exec "$LLAMA_BIN" -m "$PHI3_GGUF" --no-conversation -st -p "$PROMPT" -c "$CTX" -n "$NTOK" --no-display-prompt --simple-io < /dev/null
