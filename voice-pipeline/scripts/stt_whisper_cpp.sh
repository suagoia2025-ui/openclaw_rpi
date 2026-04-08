#!/usr/bin/env bash
# Prueba aislada STT: WAV → texto por stdout.
# Requiere: WHISPER_BIN, WHISPER_MODEL (ver env.example)
set -euo pipefail
: "${WHISPER_BIN:?definir WHISPER_BIN}" "${WHISPER_MODEL:?definir WHISPER_MODEL}"
WAV="${1:?uso: $0 archivo.wav}"
LANG_OPT=()
[[ -n "${VOICE_WHISPER_LANGUAGE:-}" && "${VOICE_WHISPER_LANGUAGE}" != "auto" ]] && LANG_OPT=(-l "$VOICE_WHISPER_LANGUAGE")
exec "$WHISPER_BIN" -m "$WHISPER_MODEL" -f "$WAV" -nt "${LANG_OPT[@]}"
