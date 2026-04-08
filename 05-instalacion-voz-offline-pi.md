# Instalación desde cero: voz offline en la Raspberry Pi (Debian 13 / trixie)

Guía **ordenada** para pasar de “nada instalado” a poder ejecutar el pipeline en la Pi. Necesitas **internet solo durante esta instalación** (descargas y compilación). Usuario de ejemplo: el tuyo (p. ej. `serv_openclaw`); rutas bajo **`$HOME`**.

**Tiempo aproximado:** 1–3 horas según red y si compilas en la Pi (compilar en la Pi es lento pero normal).

---

## 0. Antes de empezar

- **Espacio:** al menos **~5 GB libres** en la tarjeta (modelos + compilaciones).
- **RAM:** 4 GB; si ves cortes de memoria al cargar el LLM, configura **swap** (apartado 8).
- **Repo del proyecto:** en la Pi debe existir el clon **`openclaw_rpi`** (ruta típica **`~/openclaw_rpi`**) con la carpeta **`voice-pipeline/`**, [`env.example`](voice-pipeline/env.example) y los scripts. El archivo **`.env` no se sube a Git** (está en `.gitignore`); cada máquina lo crea a partir de `env.example`.

### 0.1 Clonar o actualizar el repositorio en la Pi

```bash
cd ~
git clone https://github.com/suagoia2025-ui/openclaw_rpi.git
cd ~/openclaw_rpi
git pull origin main
```

Si ya tenías el clon, basta con `cd ~/openclaw_rpi && git pull origin main`. Ajusta la URL si usas otro remoto o SSH.

Conéctate por SSH y actualiza paquetes (incluye dependencias para compilar y para **Piper** / `espeak-ng`):

```bash
sudo apt update
sudo apt install -y build-essential cmake git wget curl ffmpeg python3 python3-pip pkg-config \
  espeak-ng libespeak-ng1
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
~/llama.cpp/build/bin/llama-completion -m "$HOME/voice-models/llm/Phi-3-mini-4k-instruct-Q4_K_M.gguf" \
  --no-conversation -st -p "Hola." -c 2048 -n 64 --no-display-prompt --simple-io < /dev/null
```

- `LLAMA_COMPLETION=$HOME/llama.cpp/build/bin/llama-completion` (inferencia batch; **no** uses `llama-cli` para el pipeline: es solo chat y queda en `>`)
- `PHI3_GGUF=$HOME/voice-models/llm/Phi-3-mini-4k-instruct-Q4_K_M.gguf`

---

## 4. Piper (TTS) y voz en español

### 4.1 Binario `piper` (Linux ARM64, solo en la Pi)

Descarga el paquete **`piper_linux_aarch64.tar.gz`** desde [releases de Piper](https://github.com/rhasspy/piper/releases). **Debe instalarse en la Raspberry Pi:** el binario es para **Linux ARM64**; si lo ejecutas en un Mac verás `exec format error`.

Después de descomprimir, el ejecutable suele estar en `piper/piper` junto a librerías (p. ej. `libpiper_phonemize.so.1`). **No basta con copiar solo el binario** a `~/.local/bin`: faltarán las `.so`. Instalación recomendada:

```bash
mkdir -p ~/piper-extract
cd ~/piper-extract
tar -xzf /ruta/al/piper_linux_aarch64.tar.gz
mkdir -p ~/.local/opt/piper
cp -a ~/piper-extract/piper/* ~/.local/opt/piper/
```

*(Sustituye `/ruta/al/piper_linux_aarch64.tar.gz` por donde esté el archivo en la Pi, p. ej. `~/Descargas/piper_linux_aarch64.tar.gz`.)*

Crea un **wrapper** que fije `LD_LIBRARY_PATH` y un enlace en el `PATH`:

```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/piper <<'EOF'
#!/usr/bin/env bash
PIPER_HOME="$HOME/.local/opt/piper"
export LD_LIBRARY_PATH="$PIPER_HOME:${LD_LIBRARY_PATH:-}"
exec "$PIPER_HOME/piper" "$@"
EOF
chmod +x ~/.local/bin/piper ~/.local/opt/piper/piper
```

Añade `~/.local/bin` al `PATH` (sesión actual y futuras):

```bash
grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Comprueba:

```bash
which piper
piper --help
```

Si aparece error de `libespeak-ng.so.1`, instala los paquetes del apartado 0 (`espeak-ng`, `libespeak-ng1`).

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
echo "Hola, prueba de voz." | piper \
  -m "$HOME/voice-models/piper/es_MX-ald-medium.onnx" \
  -c "$HOME/voice-models/piper/es_MX-ald-medium.onnx.json" \
  -f /tmp/piper-test.wav
```

Equivalente con nombres largos: `--model`, `--config`, `--output_file`.

Otras voces: navega `es/es_ES/...` o `es/es_MX/...` en el árbol del mismo repositorio y descarga el `.onnx` + `.json` del mismo directorio.

---

## 5. Archivo `.env` del proyecto

Plantilla en el repo: [`voice-pipeline/env.example`](voice-pipeline/env.example) (rutas **`$HOME/whisper.cpp`** y **`$HOME/llama.cpp`**, voz **`es_MX-ald-medium`**). En la Pi:

```bash
cd ~/openclaw_rpi/voice-pipeline
cp -n env.example .env
nano .env
```

(`cp -n` no sobrescribe si `.env` ya existe.)

Comprueba que coincidan con lo instalado, sobre todo:

- `PHI3_GGUF` → el nombre real del `.gguf` en `~/voice-models/llm/` (`ls ~/voice-models/llm/*.gguf`).
- `WHISPER_BIN` → `whisper-cli` o `main` según `ls ~/whisper.cpp/build/bin/`.

Referencia rápida:

- `WHISPER_BIN=$HOME/whisper.cpp/build/bin/whisper-cli` (o `main`)
- `WHISPER_MODEL=$HOME/voice-models/whisper/ggml-tiny.bin`
- `LLAMA_COMPLETION=$HOME/llama.cpp/build/bin/llama-completion` (inferencia batch; **no** uses `llama-cli` para el pipeline: es solo chat y queda en `>`)
- `PHI3_GGUF=$HOME/voice-models/llm/Phi-3-mini-4k-instruct-Q4_K_M.gguf`
- `PIPER_BIN=$HOME/.local/bin/piper`
- `PIPER_VOICE_ONNX` / `PIPER_VOICE_JSON` → archivos `es_MX-ald-medium` en `~/voice-models/piper/`

Tras editar:

```bash
set -a && source ~/openclaw_rpi/voice-pipeline/.env && set +a
echo "$WHISPER_BIN" "$PHI3_GGUF"
```

---

## 6. Pipeline completo

```bash
cd ~/openclaw_rpi/voice-pipeline
set -a && source .env && set +a
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=3" -ac 1 -ar 16000 /tmp/test16k.wav
python3 scripts/voice_pipeline.py /tmp/test16k.wav -o /tmp/reply.wav --log-dir /tmp/voice-run
```

Si termina bien, deberías ver `OK: /tmp/reply.wav`. Para escuchar (si tienes salida de audio):

```bash
aplay /tmp/reply.wav
```

Si el tono o la velocidad no cuadran, la voz suele ser **22050 Hz** mono; prueba:

```bash
aplay -r 22050 -f S16_LE -c 1 /tmp/reply.wav
```

*(La frecuencia exacta está en el `.json` de la voz.)*

---

## 7. Si algo falla

### 7.1 Prompt `>` “infinito” con llama.cpp (qué dice el código upstream)

En **`llama-completion`** (herramienta correcta para un prompt y salir), el carácter **`>`** solo se imprime cuando el **modo conversación** sigue activo: en ese caso el programa puede quedar **esperando entrada por teclado** (`readline`), lo que en una terminal parece un bucle infinito. Referencia: [tools/completion/completion.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/completion/completion.cpp) (bloque que fija `interactive_first` si hay conversación sin “single turn” + prompt, y el `LOG("\n> ")` en modo conversación).

**Reglas prácticas:**

1. **No uses `llama-cli` para el pipeline** — en versiones recientes es la **UI de chat**; para texto “una vez y terminar” usa **`llama-completion`** (variable **`LLAMA_COMPLETION`** en `.env`).
2. **Desactiva conversación explícitamente:** `--no-conversation` (o `-no-cnv`) para que no se active el modo chat aunque el GGUF traiga plantilla.
3. **Un turno:** `-st` con **`-p` no vacío** evita el camino que fuerza modo interactivo cuando la conversación estaría activa (mismo archivo fuente, ~líneas 414–426).
4. **Prueba en terminal:** si ejecutas el binario **a mano** sin **`< /dev/null`**, con stdin conectado al teclado el programa puede **bloquearse en `>` esperando que escribas**: es comportamiento esperado, no un fallo del modelo. El pipeline usa `stdin` cerrado (`subprocess`); las pruebas manuales deben incluir **`< /dev/null`** o `echo | …`.
5. **Comprueba qué binario es:** `basename "$(readlink -f "$LLAMA_COMPLETION")"` debe ser **`llama-completion`**, no `llama-cli`.

Ejemplo de prueba mínima (termina sola; sin teclado):

```bash
"$LLAMA_COMPLETION" -m "$PHI3_GGUF" --no-conversation -st -p "hola" -n 32 --no-display-prompt --simple-io < /dev/null
```

*(El pipeline no usa `--log-disable`: en algunas builds oculta el bloque de respuesta legible.)*

| Síntoma | Qué revisar |
|--------|-------------|
| `command not found` en whisper/llama | Rutas en `.env` y que existan los binarios en `build/bin/` |
| `command not found` para `piper` | `echo $PATH` debe incluir `~/.local/bin`; `source ~/.bashrc` o ruta completa `~/.local/bin/piper` |
| `libespeak-ng.so.1` | `sudo apt install -y espeak-ng libespeak-ng1` |
| `libpiper_phonemize.so.1` | Instalación completa en `~/.local/opt/piper` + wrapper con `LD_LIBRARY_PATH` (apartado 4.1) |
| Error al descargar GGUF | Conexión, espacio en disco, o descarga manual desde Hugging Face |
| Proceso muere por memoria | Swap (apartado 8), bajar `VOICE_LLAMA_CTX` y `VOICE_LLAMA_MAX_TOKENS` en `.env` |
| `TimeoutExpired` en `llama-completion` | En la Pi Phi-3 puede tardar **>10 min**; sube `VOICE_LLAMA_TIMEOUT_SEC` (p. ej. `3600`) o baja `VOICE_LLAMA_MAX_TOKENS` / `VOICE_LLAMA_CTX`. Opcional: `VOICE_LLAMA_THREADS=4`. Actualiza `voice-pipeline` con `git pull`. |
| Pipeline no termina y el proceso queda en `>` (chat) | Lee **§7.1**. Usa **`llama-completion`** (no `llama-cli`), **`--no-conversation`**, **`-st`**, prueba con **`< /dev/null`**. Asegura **`LLAMA_COMPLETION`** en `.env`. No pongas **`VOICE_LLAMA_MAX_TOKENS=-1`**. |
| Piper no encuentra la voz | Nombres y rutas de `.onnx` y `.onnx.json` en `.env` |

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

*Instalación alineada con el repositorio actual (`env.example`, scripts en `voice-pipeline/`). Debian 13 (trixie) ARM64; ajusta nombres de binarios si tu versión de whisper.cpp/llama.cpp difiere.*
