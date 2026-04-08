# Pipeline de voz offline (STT → LLM → TTS)

Implementación del cambio OpenSpec `offline-voice-pipeline-pi4`: **Whisper tiny** (whisper.cpp) → **Phi-3-mini GGUF** (llama.cpp) → **Piper** `es_CO-female-medium`, con **system prompt** y **filtro de salida** para uso infantil.

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

Los binarios (`whisper.cpp`, `llama.cpp`, `piper`) deben estar instalados en la Raspberry Pi; esta carpeta solo contiene scripts y documentación.
