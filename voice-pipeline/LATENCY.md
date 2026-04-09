# Latencia del pipeline de voz (fluidez conversacional)

En una **Raspberry Pi 4** con **Phi-3-mini** en CPU, la inferencia del LLM es el cuello de botella: varios **segundos a minutos** por respuesta es normal. “Instantáneo” como un asistente en la nube **no es realista** con el mismo modelo local; sí puedes **acercarte** con los métodos siguientes.

## 1. Mayor impacto: `llama-server` (modelo caliente)

Cada ejecución de `voice_pipeline.py` con **`llama-completion` por subprocess** suele **volver a cargar el GGUF** desde disco a RAM. Eso añade muchísimo tiempo antes del primer token.

**Solución:** mantener **`llama-server`** en marcha con el modelo ya cargado y en el `.env`:

```bash
export VOICE_LLAMA_SERVER_URL="http://127.0.0.1:8080"
```

Arranque del servidor (ajusta rutas):

```bash
cd voice-pipeline
chmod +x scripts/llama_server_voice.sh
set -a && source .env && set +a
./scripts/llama_server_voice.sh
```

El pipeline hará **HTTP solo a localhost** (sigue siendo inferencia local). El script `llama_server_voice.sh` necesita **`PHI3_GGUF`** en `.env` para cargar el modelo; el proceso Python no usa el GGUF cuando solo defines `VOICE_LLAMA_SERVER_URL` (puedes dejar `PHI3_GGUF` solo para arrancar el servidor).

## 2. Respuestas más cortas: `VOICE_FAST_CONVERSATION`

Menos tokens de salida ⇒ menos tiempo de generación (y suele encajar con respuestas breves del system prompt).

En `.env`:

```bash
export VOICE_FAST_CONVERSATION=1
# opcional: techo/piso de tokens en modo rápido
# export VOICE_FAST_MAX_TOKENS=192
# export VOICE_FAST_MIN_OUTPUT_TOKENS=96
```

## 3. Grabación más corta

Menos segundos de audio ⇒ menos trabajo en Whisper (y a veces menos texto en el prompt).

```bash
export VOICE_RECORD_SECONDS=5
```

## 4. Modelo o cuantización más pequeña

Un GGUF **más pequeño** (p. ej. Q4_0 frente a Q4_K_M, o un modelo con menos parámetros compatible con tu plantilla) suele **reducir tokens/s** en tiempo absoluto en CPU. Es un compromiso calidad/velocidad.

## 5. Hilos y contexto

- **`VOICE_LLAMA_THREADS`**: en Pi4 suele ayudar subir hasta el número de núcleos (p. ej. 4).
- **`VOICE_LLAMA_CTX`**: contexto **más bajo** puede acelerar un poco y bajar RAM, pero si es demasiado pequeño verás `prompt is too long`.

## 6. Piper y Whisper

Suelen ser **mucho más rápidos** que el LLM en Pi; optimizarlos tiene efecto menor que los puntos 1–2.

## Resumen práctico

| Prioridad | Acción |
|-----------|--------|
| Alta | `llama-server` + `VOICE_LLAMA_SERVER_URL` |
| Media | `VOICE_FAST_CONVERSATION=1`, menos `VOICE_RECORD_SECONDS` |
| Media | Modelo/cuantización más ligero |
| Baja | Ajuste fino de hilos / contexto |

Para medir etapas, usa `--log-dir` y revisa `pipeline_timings.txt`.
