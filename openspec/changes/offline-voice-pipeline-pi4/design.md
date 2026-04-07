## Context

La Raspberry Pi 4 del proyecto ya ejecuta **OpenClaw** con gateway en loopback y canales como Telegram; el modelo por defecto es remoto. Este diseño describe un **camino paralelo**: inferencia 100 % local para voz, sin depender de red en la ruta crítica STT/LLM/TTS. Restricciones típicas: **4 GB RAM** (swap opcional), **ARM64**, almacenamiento en microSD, sin GPU NVIDIA.

## Goals / Non-Goals

**Goals:**

- Pipeline reproducible **STT → LLM → TTS** con **Whisper tiny**, **Phi-3-mini GGUF** y **Piper** (español).
- Ejecución **sin conexión a internet** durante la inferencia (modelos y binarios locales).
- Documentar cuantización recomendada, RAM pico aproximada y tiempos de respuesta esperables.
- Punto de entrada único (script o binario) para una interacción tipo “grabar → responder en audio”.

**Non-Goals:**

- Paridad de calidad con GPT-4o o Whisper large en la misma Pi.
- Integración obligatoria con OpenClaw/Telegram en la primera entrega (puede ser fase 2).
- Reconocimiento de wake-word o always-on mic sin política de privacidad definida.
- Entrenamiento o fine-tuning de modelos.

## Decisions

| Decisión | Elección | Rationale |
|----------|-----------|-----------|
| STT | **Whisper “tiny”** (tiny.en o tiny multilingüe según modelo) | Menor coste computacional en RPi; trade-off de precisión aceptable para demo. |
| Implementación STT | **whisper.cpp** o **faster-whisper** (CPU) | `whisper.cpp` es muy usado en edge; `faster-whisper` + CTranslate2 si hay wheels ARM64 estables. |
| LLM | **Phi-3-mini** en **GGUF** (cuantización **Q4_K_M** o **Q4_0** como punto de partida) | Tamaño razonable; `llama.cpp`/`llamafile`/`llama-cpp-python` son el camino estándar en ARM. |
| Runtime LLM | **llama.cpp** (CLI `llama-cli` o servidor local loopback) | Sin dependencia de PyTorch completo en muchos casos; control explícito de contexto y memoria. |
| TTS | **Piper** + voz **es-ES** (o `es-ES-*`/`es-MX-*` según modelo publicado) | Offline, ligero, buena calidad para voz en español. |
| Formato audio I/O | WAV **16 kHz** mono para STT; salida Piper según modelo (p. ej. 22,05 kHz) | Alineado con Whisper estándar y Piper. |
| Orquestación | Script **shell** o **Python** mínimo que encadena tres pasos | Menor superficie de fallo; fácil de depurar en la Pi. |
| Ubicación de modelos | Directorio fijo, p. ej. `/opt/voice-models/` o `~/voice-models/` con `README` | Evita rutas hardcodeadas dispersas; documentar `ENV`. |

**Alternativas consideradas:**  
- **Ollama:** cómodo pero añade daemon y dependencias; válido si el usuario prefiere UX unificada.  
- **Whisper “base”:** mejor WER pero más RAM/tiempo; reservado para hardware mayor o fase 2.  
- **TTS Coqui / otros:** más pesos; Piper prioriza simplicidad offline.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| **OOM** al cargar Whisper + LLM | Ejecutar etapas secuenciales y liberar procesos antes del siguiente paso; o solo cargar un modelo a la vez; aumentar swap. |
| **Latencia alta** (>10–30 s por turno) | Reducir tokens máximos de salida; cuantización más agresiva (Q3_K); tiny en STT. |
| **Calidad de transcripción** en ruido | Documentar uso de micrófono cercano (p. ej. ReSpeaker ya en el proyecto). |
| **Binarios ARM** no disponibles | Compilar desde fuente en la Pi con `cmake`/`make` (tiempo de build largo). |
| **Licencias de modelos** | Documentar enlaces oficiales Microsoft (Phi-3), OpenAI Whisper, Piper voices. |

## Migration Plan

1. Crear directorio de modelos y descargar pesos (con checksums verificados en doc).  
2. Instalar binarios o compilar STT/LLM/TTS.  
3. Probar cada etapa por separado (audio → texto → texto → audio).  
4. Integrar script único; opcional: `systemd` user service para demo.  
5. **Rollback:** desinstalar paquetes y borrar carpeta de modelos; no afecta OpenClaw existente.

## Open Questions

- ¿Versión exacta del GGUF Phi-3-mini (repositorio Hugging Face recomendado) y tamaño en MB?  
- ¿Entrada de audio: archivo WAV fijo, `arecord`, o stream desde ALSA?  
- ¿Salida: solo WAV a archivo o reproducción directa con `aplay`?
