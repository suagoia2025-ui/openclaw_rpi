# Modelos y tamaños aproximados

Valores orientativos; comprueba el tamaño real en disco tras descargar.

| Componente | Artefacto recomendado | Tamaño (~) | Notas |
|------------|----------------------|------------|--------|
| STT | **Whisper tiny** → `ggml-tiny.bin` (whisper.cpp) | ~75 MB | Multilingüe; suficiente para español en RPi4. |
| LLM | **Phi-3-mini-4k-instruct** GGUF **Q4_K_M** (o Q4_0) | ~2.2–2.4 GB | Menor RAM que FP16; ajustar `--ctx-size` y `-n` si hay OOM. |
| TTS | Piper **`es_CO-female-medium`** | ~20–40 MB | `es_CO-female-medium.onnx` + `es_CO-female-medium.onnx.json` |

## Enlaces de descarga (requieren red solo en la fase de preparación)

- **Whisper GGML:** [ggerganov/whisper.cpp releases](https://github.com/ggerganov/whisper.cpp) — scripts `models/download-ggml-model.sh` o equivalente para `tiny`.
- **Phi-3-mini GGUF:** Hugging Face — por ejemplo repositorios comunitarios tipo `bartowski/Phi-3-mini-4k-instruct-GGUF` o publicaciones oficiales Microsoft; elige un único archivo `*-Q4_K_M.gguf` (o `Q4_0`).
- **Piper voz:** [rhasspy/piper releases](https://github.com/rhasspy/piper/releases) o índice de voces del proyecto; busca `es_CO-female-medium`.

## Cuantización GGUF

- **Q4_K_M:** equilibrio calidad/tamaño (recomendado como punto de partida).
- **Q4_0:** algo más pequeño; si la Pi queda justa de RAM, probar antes de bajar a Q3.
