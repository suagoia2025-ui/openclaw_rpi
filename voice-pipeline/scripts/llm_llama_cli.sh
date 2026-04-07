#!/usr/bin/env bash
# Prueba aislada LLM: un prompt en stdin (o primer argumento) → respuesta en stdout.
# Requiere: LLAMA_CLI, PHI3_GGUF, opcional VOICE_LLAMA_CTX, VOICE_LLAMA_MAX_TOKENS
set -euo pipefail
: "${LLAMA_CLI:?}" "${PHI3_GGUF:?}"
CTX="${VOICE_LLAMA_CTX:-2048}"
NTOK="${VOICE_LLAMA_MAX_TOKENS:-128}"
if [[ -n "${1:-}" ]]; then
  PROMPT="$1"
else
  PROMPT="$(cat)"
fi
exec "$LLAMA_CLI" -m "$PHI3_GGUF" -p "$PROMPT" -c "$CTX" -n "$NTOK" --no-display-prompt
