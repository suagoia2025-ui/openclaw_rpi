# Pipeline de voz offline en Raspberry Pi 4 (STT → LLM → TTS)

Asistente de voz local para **público general** (prompt por defecto en español): **Whisper tiny** → **Phi-3-mini GGUF** → **Piper** voz **`es_CO-female-medium`**, sin llamadas HTTP en inferencia. **Filtro infantil** opcional con **`VOICE_OUTPUT_FILTER=1`**. **SO de referencia:** Debian GNU/Linux **13 (trixie)** ARM64 (véase [`README.md`](README.md)).

Código y scripts: carpeta [`voice-pipeline/`](voice-pipeline/).

## 1. Requisitos de hardware y sistema

| Recurso | Orientación |
|---------|-------------|
| Placa | Raspberry Pi 4, **ARM64** |
| RAM | **4 GB** (típico); si hay OOM, activar **swap** (p. ej. 1–2 GB) y bajar `VOICE_LLAMA_CTX` / `VOICE_LLAMA_MAX_TOKENS` |
| Disco | Varios **GB** libres para GGUF Q4 (~2,4 GB) + Whisper tiny (~75 MB) + Piper (~tens MB) + compilaciones |
| Audio entrada | WAV **16 kHz**, **mono**, PCM (formato estándar para Whisper) |
| Red | Solo hace falta **en la fase de instalación** para descargar modelos y compilar; la **inferencia** no usa internet si todo está local |

## 2. Orden recomendado de instalación

1. **Directorio de modelos** (p. ej. `~/voice-models/`) con subcarpetas `whisper/`, `llm/`, `piper/`.
2. **Descargar pesos** (véase [`voice-pipeline/MODELS.md`](voice-pipeline/MODELS.md)).
3. **Compilar o instalar binarios** en la Pi: `whisper.cpp`, `llama.cpp`, `piper` (ver secciones siguientes).
4. **Copiar** [`voice-pipeline/env.example`](voice-pipeline/env.example) a `voice-pipeline/.env` y rellenar rutas.
5. **Probar cada etapa** con los scripts en `voice-pipeline/scripts/` (`stt_*.sh`, `llm_*.sh`, `tts_*.sh`).
6. **Pipeline completo:** `python3 voice-pipeline/scripts/voice_pipeline.py` o [`voice-pipeline/scripts/run_pipeline.sh`](voice-pipeline/scripts/run_pipeline.sh).

## 3. whisper.cpp (STT, Whisper tiny)

En la Pi (dependencias típicas: `build-essential`, `cmake`, `git`):

```bash
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build -j "$(nproc)"
```

El binario puede llamarse `whisper-cli` o `main` según versión; exporta **`WHISPER_BIN`** a ese ejecutable.

Descarga del modelo **tiny** multilingüe (scripts del repo `models/download-ggml-model.sh` o equivalente) y guarda **`ggml-tiny.bin`** en `~/voice-models/whisper/`. Exporta **`WHISPER_MODEL`**.

**Prueba aislada** (con variables cargadas):

```bash
bash voice-pipeline/scripts/stt_whisper_cpp.sh /ruta/prueba_16k_mono.wav
```

Si tu build no soporta `-nt`, edita el comando o el script para quitar esa bandera.

## 4. llama.cpp (LLM, Phi-3-mini GGUF)

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build -j "$(nproc)"
```

Exporta **`LLAMA_COMPLETION`** al binario **`llama-completion`** (inferencia batch; no uses `llama-cli` para scripts: es la UI de chat). Descarga **un** archivo **Phi-3-mini-4k-instruct** en **GGUF** con cuantización **Q4_K_M** o **Q4_0** y colócalo en `~/voice-models/llm/`. Exporta **`PHI3_GGUF`**. Si solo tienes **`LLAMA_CLI`**, el pipeline lo acepta si apunta al mismo binario `llama-completion`.

**Prueba aislada:**

```bash
bash voice-pipeline/scripts/llm_llama_cli.sh "Hola, responde en una sola frase."
```

Ajusta **`VOICE_LLAMA_CTX`** (p. ej. 2048) y **`VOICE_LLAMA_MAX_TOKENS`** (techo; p. ej. 768) en `.env` si la Pi se queda sin memoria. El pipeline calcula **`-n`** también según **`VOICE_LLAMA_TIMEOUT_SEC`** y **`VOICE_LLAMA_EST_TOKENS_PER_SEC`** para reducir respuestas cortadas a medias.

**Memoria entre etapas:** el pipeline ejecuta **procesos secuenciales** (Whisper termina antes de cargar el LLM); no mantengas ambos binarios corriendo a la vez en scripts personalizados.

## 5. Piper (TTS, es_CO-female-medium)

Instala el binario `piper` según [rhasspy/piper](https://github.com/rhasspy/piper) (release para ARM64 o build desde fuente). Descarga **`es_CO-female-medium.onnx`** y **`es_CO-female-medium.onnx.json`** y colócalos en `~/voice-models/piper/`.

**Frecuencia de salida:** suele constar en el JSON (habitualmente **22050 Hz** mono para muchas voces Piper; confirma en tu `.json`).

**Prueba aislada:**

```bash
echo "Hola, esto es una prueba." | bash voice-pipeline/scripts/tts_piper.sh /tmp/piper-test.wav
```

## 6. Pipeline completo y filtro infantil (opcional)

- **System prompt:** [`voice-pipeline/prompts/system_general.txt`](voice-pipeline/prompts/system_general.txt) (sobreescribible con **`VOICE_SYSTEM_PROMPT`**).
- Por defecto la salida del **LLM va directo a Piper**. Filtro: **`VOICE_OUTPUT_FILTER=1`** en `.env` → [`voice-pipeline/scripts/output_filter.py`](voice-pipeline/scripts/output_filter.py) + [`voice-pipeline/filter/blocked_terms.txt`](voice-pipeline/filter/blocked_terms.txt).

**Ejecución:**

```bash
cd voice-pipeline
cp env.example .env   # y editar
set -a && source .env && set +a
python3 scripts/voice_pipeline.py /ruta/entrada.wav -o /ruta/pipeline_reply.wav --log-dir /tmp/voice-run
```

No se realizan peticiones HTTP en esta cadena; solo subprocess locales.

## 7. Audio de prueba

No se versiona un WAV binario en el repo. Genera uno **16 kHz mono** en la Pi, por ejemplo:

```bash
# 3 s de silencio o tono (requiere ffmpeg)
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" -ac 1 -ar 16000 /tmp/test16k.wav
```

O graba con el micrófono (p. ej. ReSpeaker) usando `arecord -f S16_LE -c 1 -r 16000 -d 5 /tmp/mi_voz.wav`.

**Flujo en vivo (grabar + pipeline + opcional reproducción):** script [`voice-pipeline/scripts/live_mic_pipeline.sh`](voice-pipeline/scripts/live_mic_pipeline.sh). Variables en `env.example` (`VOICE_ALSA_CAPTURE`, `VOICE_RECORD_SECONDS`, `VOICE_PLAY_AFTER`, `VOICE_ALSA_PLAYBACK`). Ver [`voice-pipeline/README.md`](voice-pipeline/README.md).

## 8. Latencia (orden de magnitud)

En RPi4 4 GB con **tiny**, **Q4** y respuestas cortas, un turno completo suele estar en el orden de **decenas de segundos** (STT + LLM + TTS en CPU); depende de longitud de audio, tokens y swap. Mide con `time` en tu instalación.

## 9. Licencias y atribución (resumen)

- **Whisper:** términos OpenAI del modelo original; uso vía whisper.cpp.
- **Phi-3:** licencia Microsoft para modelos Phi-3; revisa la ficha del GGUF en Hugging Face.
- **Piper / voz:** proyecto Piper y licencia de la voz concreta en el paquete descargado.

Detalle y enlaces oficiales: amplía según los archivos que descargues (`LICENSE` en cada repositorio).

## 10. Checklist de verificación (E2E)

Lista reproducible: [`voice-pipeline/CHECKLIST.md`](voice-pipeline/CHECKLIST.md).
