> **Spec canónico (fuente de verdad actual):** [`openspec/specs/offline-voice-pipeline/spec.md`](../../../specs/offline-voice-pipeline/spec.md) — esta carpeta y estas tareas son **histórico** del cambio archivado.

## 1. Estructura y modelos locales

- [x] 1.1 Definir y documentar directorio de modelos (p. ej. `~/voice-models/` o `/opt/voice-models/`) y variables de entorno para rutas
- [x] 1.2 Documentar nombres exactos: Whisper tiny, Phi-3-mini GGUF (cuantización recomendada Q4_K_M o Q4_0), voz Piper español (`es-ES`/`es-MX` según modelo publicado) y tamaños aproximados en MB
- [x] 1.3 Añadir en documentación requisitos RPi4 ARM64, SO de referencia Debian GNU/Linux 13 (trixie), RAM 4 GB, disco, uso de swap y límites de contexto/tokens para evitar OOM

## 2. STT (Whisper tiny)

- [x] 2.1 Elegir e instalar implementación (whisper.cpp o faster-whisper en CPU) y obtener binario/wheel funcional en ARM64
- [x] 2.2 Colocar peso Whisper **tiny** en el directorio de modelos y verificar transcripción de un WAV de prueba (16 kHz mono)
- [x] 2.3 Documentar comando de prueba STT aislado (entrada WAV → texto en stdout o archivo)

## 3. LLM (Phi-3-mini GGUF)

- [x] 3.1 Instalar llama.cpp (o runtime elegido) y colocar Phi-3-mini **GGUF** con cuantización documentada
- [x] 3.2 Verificar inferencia por CLI con prompt corto y límites de `--ctx-size` / tokens de salida acordes a 4 GB RAM
- [x] 3.3 Documentar comando de prueba LLM aislado (texto → texto) y estrategia de liberación de memoria entre etapas

## 4. TTS (Piper español)

- [x] 4.1 Instalar Piper y descargar voz **`es_CO-female-medium`** (archivos `es_CO-female-medium.onnx` y `es_CO-female-medium.onnx.json`) desde el repositorio oficial de Piper
- [x] 4.2 Verificar síntesis de un texto corto a WAV (o formato soportado) y documentar frecuencia de salida
- [x] 4.3 Documentar comando de prueba TTS aislado

## 5. Orquestación y pipeline offline

- [x] 5.1 Implementar script shell o Python mínimo que encadene: audio → STT → texto a LLM → texto a Piper → archivo de audio (sin HTTP/HTTPS en el camino de inferencia)
- [x] 5.2 Asegurar formato de audio entre etapas (p. ej. WAV 16 kHz mono hacia STT; conversión si hace falta entre pasos)
- [x] 5.3 Incluir audio de prueba versionado o instrucciones para generar uno, y salida verificable (WAV/log)
- [x] 5.4 Definir system prompt de Phi-3-mini con restricciones de contenido infantil (niños 2-7 años: lenguaje simple, dominio educativo, sin contenido adulto) e implementar filtro de salida que reemplace respuestas fuera de dominio por respuesta segura predefinida

## 6. Documentación y verificación final

- [x] 6.1 Escribir guía de instalación reproducible (orden: modelos → binarios → pruebas por etapa → pipeline completo)
- [x] 6.2 Documentar estimación de orden de magnitud de latencia o tiempo por turno en RPi4 y referencias de licencia de modelos
- [x] 6.3 Validar en instalación limpia (o checklist) el comando de prueba end-to-end del Requirement “Punto de entrada reproducible”
