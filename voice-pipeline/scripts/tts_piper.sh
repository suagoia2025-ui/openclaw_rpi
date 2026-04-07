#!/usr/bin/env bash
# Prueba aislada TTS: texto por stdin → WAV.
# Ejemplo: echo "Hola" | ./tts_piper.sh /tmp/out.wav
# Requiere: PIPER_BIN, PIPER_VOICE_ONNX, PIPER_VOICE_JSON
set -euo pipefail
: "${PIPER_BIN:?}" "${PIPER_VOICE_ONNX:?}" "${PIPER_VOICE_JSON:?}"
OUT="${1:?uso: $0 salida.wav}"
exec "$PIPER_BIN" --model "$PIPER_VOICE_ONNX" --config "$PIPER_VOICE_JSON" --output_file "$OUT"
