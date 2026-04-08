# Pipeline de voz offline (STT → LLM → TTS)

Implementación del cambio OpenSpec `offline-voice-pipeline-pi4`: **Whisper tiny** (whisper.cpp) → **Phi-3-mini GGUF** (llama.cpp) → **Piper** `es_CO-female-medium`, con **system prompt** por defecto para público general (`prompts/system_general.txt`). El **filtro infantil** (`output_filter.py`) solo corre si defines **`VOICE_OUTPUT_FILTER=1`** en `.env`.

## Documentación principal

- Guía completa (instalación en Debian 13 trixie / RPi4, pruebas por etapa, licencias, latencia): [`../04-offline-voice-pipeline.md`](../04-offline-voice-pipeline.md)
- Modelos y tamaños: [`MODELS.md`](MODELS.md)
- Variables de entorno de ejemplo: [`env.example`](env.example) → copia a `.env` y ajusta rutas en la Pi.

## Punto de entrada rápido

```bash
cd voice-pipeline
cp env.example .env   # editar rutas a binarios y modelos
set -a && source .env && set +a
python3 scripts/voice_pipeline.py /ruta/entrada.wav -o /ruta/salida.wav --log-dir /tmp/voice-log
```

## Micrófono en vivo (grabar → pipeline → opcional altavoz)

1. Lista dispositivos de captura: `arecord -l` (ReSpeaker suele ser `card 3` → `plughw:3,0`).
2. En `.env` opcional: `VOICE_ALSA_CAPTURE`, `VOICE_RECORD_SECONDS`, y si quieres escuchar al terminar: `VOICE_PLAY_AFTER=1`, `VOICE_ALSA_PLAYBACK` (p. ej. HDMI `plughw:1,0`) y `VOICE_ALSA_PLAYBACK_RATE` según el `.json` de Piper.
3. Ejecuta:

```bash
cd voice-pipeline && set -a && source .env && set +a
./scripts/live_mic_pipeline.sh
```

Salida por defecto: `/tmp/pipeline_reply.wav`. Otro path: `./scripts/live_mic_pipeline.sh /tmp/respuesta.wav`. Logs intermedios (p. ej. `llm_raw.txt`): `./scripts/live_mic_pipeline.sh /tmp/salida.wav --log-dir /tmp/voice-debug` (crea el directorio si hace falta).

### Comprobar que el micrófono capta tu voz

1. **`STT listo (N chars)`** — si **N** es muy bajo o **0**, el audio puede ser silencio o muy bajo.
2. Con **`--log-dir /tmp/voice-debug`**, revisa **`stt.txt`** y **`llm_raw.txt`**. Si usas filtro, también **`llm_filtered.txt`**.
3. En `.env`, **`VOICE_DEBUG_SAVE_RECORDING=/tmp/ultima_pregunta.wav`** — tras grabar, escucha: `aplay -D plughw:2,0 -r 16000 -f S16_LE -c 1 /tmp/ultima_pregunta.wav` (ajusta `-D` y tarjeta).
4. Prueba aislada: `arecord -D plughw:3,0 -f S16_LE -c 1 -r 16000 -d 5 /tmp/test.wav` y luego `aplay` con el mismo dispositivo de salida HDMI.
5. **Volumen de captura:** `alsamixer -c 3` (F4 = Capture en muchas versiones) y sube el mic del ReSpeaker.

Los binarios (`whisper.cpp`, `llama.cpp`, `piper`) deben estar instalados en la Raspberry Pi; esta carpeta solo contiene scripts y documentación.
