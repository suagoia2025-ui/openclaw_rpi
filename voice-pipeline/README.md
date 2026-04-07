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

Los binarios (`whisper.cpp`, `llama.cpp`, `piper`) deben estar instalados en la Raspberry Pi; esta carpeta solo contiene scripts y documentación.
