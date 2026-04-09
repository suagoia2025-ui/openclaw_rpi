> **Spec canónico (fuente de verdad actual):** [`openspec/specs/offline-voice-pipeline/spec.md`](../../../specs/offline-voice-pipeline/spec.md) — este proposal y la carpeta del archive son **histórico** del cambio archivado.

## Why

Un asistente de voz que funcione **sin internet** en Raspberry Pi 4 permite demos, privacidad y uso en redes restringidas. Hoy el stack OpenClaw en esta Pi depende de APIs en la nube para el modelo; este cambio define un **núcleo conversacional offline**: voz → texto (**Whisper tiny**), razonamiento local (**Phi-3-mini GGUF** vía `llama.cpp` o similar), texto → voz (**Piper TTS** español), encadenado de forma reproducible en hardware limitado.

## What Changes

- Definir e implementar un **pipeline STT → LLM → TTS** ejecutable en **RPi4 4 GB** (u orientación clara si hace falta swap o modelo más pequeño).
- Integración **offline** documentada: sin llamadas HTTP a proveedores externos en tiempo de inferencia (modelos y voces locales en disco).
- Selección concreta de artefactos: **Whisper** (variante *tiny*), **Phi-3-mini** en **GGUF**, **Piper** con voz **español**.
- Scripts o servicio mínimo (CLI o loop) que lea audio de entrada, transcriba, genere respuesta y sintetice audio de salida.
- Documentación de instalación, rutas de modelos, uso de RAM y limitaciones conocidas.

## Capabilities

### New Capabilities

- `offline-voice-pipeline`: Pipeline conversacional local STT (Whisper tiny) → LLM (Phi-3-mini GGUF) → TTS (Piper ES) en Raspberry Pi 4, sin dependencia de red en inferencia.

### Modified Capabilities

- *(ninguna — no hay specs previas en `openspec/specs/`)*

## Impact

- **Hardware:** CPU/RAM de la Pi, almacenamiento para modelos (varios cientos de MB–GB según cuantización).
- **Software:** dependencias nativas (ej. `whisper.cpp` / `faster-whisper`, `llama.cpp` o bindings, `piper`), posible compilación ARM64.
- **Proyecto:** nuevo código y/o scripts fuera del flujo OpenClaw cloud; opcionalmente un puente futuro con OpenClaw (fuera del alcance mínimo de esta propuesta).
- **Operación:** mantenimiento de versiones de modelos GGUF y voz Piper; actualizaciones manuales sin gestor de paquetes central para los pesos.
