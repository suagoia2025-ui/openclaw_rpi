#!/usr/bin/env bash
# Graba desde el micrófono (16 kHz mono) → voice_pipeline.py → opcionalmente reproduce por altavoz.
# Requiere: .env con las mismas variables que el pipeline; opcional VOICE_ALSA_CAPTURE, VOICE_RECORD_SECONDS.
#
# Uso:
#   ./scripts/live_mic_pipeline.sh
#   ./scripts/live_mic_pipeline.sh /tmp/mi_salida.wav
#   ./scripts/live_mic_pipeline.sh /tmp/salida.wav --log-dir /tmp/voice-debug
#   ./scripts/live_mic_pipeline.sh -o /tmp/salida.wav --log-dir /tmp/voice-debug
#   VOICE_RECORD_SECONDS=12 ./scripts/live_mic_pipeline.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi

OUT_WAV="/tmp/pipeline_reply.wav"
PIPE_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output-wav)
      OUT_WAV="$2"
      shift 2
      ;;
    --log-dir)
      PIPE_ARGS+=(--log-dir "$2")
      shift 2
      ;;
    -*)
      echo "Opción desconocida: $1 (usa -o, --output-wav o --log-dir)" >&2
      exit 1
      ;;
    *)
      OUT_WAV="$1"
      shift
      ;;
  esac
done

SEC="${VOICE_RECORD_SECONDS:-8}"
WAV_IN="${VOICE_TMP_WAV:-/tmp/voice_live_$$.wav}"

command -v arecord >/dev/null 2>&1 || {
  echo "arecord no encontrado; instala alsa-utils: sudo apt install -y alsa-utils" >&2
  exit 1
}

cleanup() { rm -f "$WAV_IN"; }
trap cleanup EXIT

echo "[live-mic] Grabando ${SEC}s (16 kHz mono). Habla ahora…" >&2
if [[ -n "${VOICE_ALSA_CAPTURE:-}" ]]; then
  arecord -D "$VOICE_ALSA_CAPTURE" -f S16_LE -c 1 -r 16000 -d "$SEC" "$WAV_IN"
else
  arecord -f S16_LE -c 1 -r 16000 -d "$SEC" "$WAV_IN"
fi

echo "[live-mic] Pipeline STT → LLM → TTS…" >&2
python3 "$ROOT/scripts/voice_pipeline.py" "$WAV_IN" -o "$OUT_WAV" "${PIPE_ARGS[@]}"

if [[ "${VOICE_PLAY_AFTER:-0}" == "1" || "${VOICE_PLAY_AFTER:-}" == "true" ]]; then
  RATE="${VOICE_ALSA_PLAYBACK_RATE:-22050}"
  echo "[live-mic] Reproduciendo → ${VOICE_ALSA_PLAYBACK:-default} @ ${RATE} Hz" >&2
  if [[ -n "${VOICE_ALSA_PLAYBACK:-}" ]]; then
    aplay -D "$VOICE_ALSA_PLAYBACK" -r "$RATE" -f S16_LE -c 1 "$OUT_WAV"
  else
    aplay -r "$RATE" -f S16_LE -c 1 "$OUT_WAV"
  fi
fi

echo "OK: $OUT_WAV" >&2
