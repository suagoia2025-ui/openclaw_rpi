# Instalación desde cero: voz offline en la Raspberry Pi (Debian 13 / trixie)

Guía **ordenada** para pasar de “nada instalado” a poder ejecutar el pipeline en la Pi. Necesitas **internet solo durante esta instalación** (descargas y compilación). Usuario de ejemplo: el tuyo (p. ej. `serv_openclaw`); rutas bajo **`$HOME`**.

**Tiempo aproximado:** 1–3 horas según red y si compilas en la Pi (compilar en la Pi es lento pero normal).

---

## 0. Antes de empezar

- **Espacio:** al menos **~5 GB libres** en la tarjeta (modelos + compilaciones).
- **RAM:** 4 GB; si ves cortes de memoria al cargar el LLM, configura **swap** (apartado 8).
- **Repo del proyecto:** clona o copia `openclaw_rpi` en la Pi (o sincroniza con `git pull`) para tener la carpeta `voice-pipeline/`.

Conéctate por SSH y actualiza paquetes:

```bash
sudo apt update
sudo apt install -y build-essential cmake git wget curl ffmpeg python3 python3-pip pkg-config
```

---

## 1. Carpetas para modelos

```bash
mkdir -p "$HOME/voice-models/whisper" "$HOME/voice-models/llm" "$HOME/voice-models/piper"
```

---

## 2. whisper.cpp (transcripción / STT)

```bash
cd ~
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build -j "$(nproc)"
```

Descarga el modelo **tiny** (script oficial):

```bash
cd ~/whisper.cpp
bash ./models/download-ggml-model.sh tiny
```

Copia el `.bin` a tu árbol de modelos (el nombre suele ser `ggml-tiny.bin`; confirma con `ls models/`):

```bash
cp models/ggml-tiny.bin "$HOME/voice-models/whisper/"
```

Anota la ruta del binario de whisper (según versión puede ser `whisper-cli` o `main`):

```bash
ls ~/whisper.cpp/build/bin/
```

Ejemplo si existe `whisper-cli`:

- `WHISPER_BIN=$HOME/whisper.cpp/build/bin/whisper-cli`
- `WHISPER_MODEL=$HOME/voice-models/whisper/ggml-tiny.bin`

**Prueba rápida** (genera un WAV de prueba y transcribe):

```bash
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=2" -ac 1 -ar 16000 /tmp/test16k.wav
~/whisper.cpp/build/bin/whisper-cli -m "$HOME/voice-models/whisper/ggml-tiny.bin" -f /tmp/test16k.wav -nt
```

Si tu binario no acepta `-nt`, quita esa opción.

---

## 3. llama.cpp (Phi-3 en GGUF)

```bash
cd ~
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build -j "$(nproc)"
```

Descarga **un** archivo GGUF **Q4_K_M** de Phi-3-mini-4k-instruct (ejemplo vía Hugging Face; la descarga pesa ~2,2–2,4 GB):

```bash
cd "$HOME/voice-models/llm"
wget --continue -O Phi-3-mini-4k-instruct-Q4_K_M.gguf \
  "https://huggingface.co/bartowski/Phi-3-mini-4k-instruct-GGUF/resolve/main/Phi-3-mini-4k-instruct-Q4_K_M.gguf"
```

Si el enlace falla, abre en el navegador el repositorio [bartowski/Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/bartowski/Phi-3-mini-4k-instruct-GGUF) y descarga manualmente el `.gguf` Q4 a esa carpeta.

Prueba mínima:

```bash
~/llama.cpp/build/bin/llama-cli -m "$HOME/voice-models/llm/Phi-3-mini-4k-instruct-Q4_K_M.gguf" \
  -p "Hola." -c 2048 -n 64 --no-display-prompt
```

- `LLAMA_CLI=$HOME/llama.cpp/build/bin/llama-cli`
- `PHI3_GGUF=$HOME/voice-models/llm/Phi-3-mini-4k-instruct-Q4_K_M.gguf`

---

## 4. Piper (TTS) y voz en español

### 4.1 Binario `piper`

En [releases de Piper](https://github.com/rhasspy/piper/releases) busca un paquete para **Linux ARM64** (a veces `aarch64`). Descárgalo y descomprime; sitúa el ejecutable `piper` en un directorio del `PATH`, por ejemplo:

```bash
mkdir -p ~/.local/bin
# tras descomprimir el release, copia el binario:
# cp ruta/al/piper ~/.local/bin/piper
chmod +x ~/.local/bin/piper
```

Comprueba que arranca: `piper --help`

### 4.2 Descargar una voz (español)

**Importante:** en el repositorio oficial [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) las variantes de español suelen ser **`es_ES`**, **`es_MX`** y **`es_AR`**. **No hay** una carpeta `es_CO` en ese índice; si en el proyecto aparece el nombre `es_CO-female-medium`, es una voz **objetivo** que tendrás que conseguir por otro canal o entrenar. **Para instalar algo que funcione hoy**, usa una voz publicada en `piper-voices`, por ejemplo **mexicana** `es_MX-ald-medium`:

```bash
cd "$HOME/voice-models/piper"
wget --continue -O es_MX-ald-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx"
wget --continue -O es_MX-ald-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json"
```

Luego en tu **`.env`** pon `PIPER_VOICE_ONNX` y `PIPER_VOICE_JSON` apuntando a **esos** archivos (nombres reales), no a `es_CO-*` hasta que existan en disco.

Prueba:

```bash
echo "Hola, prueba de voz." | ~/.local/bin/piper \
  --model "$HOME/voice-models/piper/es_MX-ald-medium.onnx" \
  --config "$HOME/voice-models/piper/es_MX-ald-medium.onnx.json" \
  --output_file /tmp/piper-test.wav
```

Otras voces: navega `es/es_ES/...` o `es/es_MX/...` en el árbol del mismo repositorio y descarga el `.onnx` + `.json` del mismo directorio.

---

## 5. Archivo `.env` del proyecto

En la Pi, dentro del clon del repo:

```bash
cd ~/ruta/al/openclaw_rpi/voice-pipeline   # ajusta la ruta
cp env.example .env
nano .env
```

Debes dejar **rutas reales** coherentes con lo anterior, por ejemplo:

- `WHISPER_BIN=$HOME/whisper.cpp/build/bin/whisper-cli` (o `main`)
- `WHISPER_MODEL=$HOME/voice-models/whisper/ggml-tiny.bin`
- `LLAMA_CLI=$HOME/llama.cpp/build/bin/llama-cli`
- `PHI3_GGUF=$HOME/voice-models/llm/Phi-3-mini-4k-instruct-Q4_K_M.gguf`
- `PIPER_BIN=$HOME/.local/bin/piper`
- `PIPER_VOICE_ONNX` y `PIPER_VOICE_JSON` apuntando a los dos archivos de la voz (p. ej. `es_MX-ald-medium.onnx` y `es_MX-ald-medium.onnx.json` si seguiste el apartado 4.2).

Guarda el archivo.

---

## 6. Pipeline completo

```bash
cd ~/ruta/al/openclaw_rpi/voice-pipeline
set -a && source .env && set +a
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" -ac 1 -ar 16000 /tmp/test16k.wav
python3 scripts/voice_pipeline.py /tmp/test16k.wav -o /tmp/reply.wav --log-dir /tmp/voice-run
```

Si termina bien, deberías tener `/tmp/reply.wav`. Para escuchar (si tienes salida de audio):

```bash
aplay /tmp/reply.wav
```

*(La frecuencia de muestreo la define Piper; si `aplay` falla, prueba con `ffplay` o revisa el `.json` de la voz.)*

---

## 7. Si algo falla

| Síntoma | Qué revisar |
|--------|-------------|
| `command not found` en whisper/llama | Rutas en `.env` y que existan los binarios en `build/bin/` |
| Error al descargar GGUF | Conexión, espacio en disco, o descarga manual desde Hugging Face |
| Proceso muere por memoria | Swap (apartado 8), bajar `VOICE_LLAMA_CTX` y `VOICE_LLAMA_MAX_TOKENS` en `.env` |
| Piper no encuentra la voz | Nombres y rutas de `.onnx` y `.onnx.json` |

Documentación adicional: [`04-offline-voice-pipeline.md`](04-offline-voice-pipeline.md), [`voice-pipeline/MODELS.md`](voice-pipeline/MODELS.md), [`voice-pipeline/CHECKLIST.md`](voice-pipeline/CHECKLIST.md).

---

## 8. (Opcional) Swap de 2 GB en la Pi

Si el LLM cierra el proceso o la Pi se queda sin memoria:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

*Instalación probada conceptualmente en Debian 13 (trixie) ARM64; ajusta nombres de binarios si tu versión de whisper.cpp/llama.cpp difiere.*
