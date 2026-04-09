# offline-voice-pipeline Specification

## Purpose

Proporcionar un **asistente de voz totalmente local** en **Raspberry Pi 4 (ARM64)**: el usuario habla (o aporta audio), el sistema transcribe (**STT**), genera una respuesta en texto (**LLM** Phi-3-mini en GGUF) y la reproduce en voz sintética (**TTS** Piper en español), **sin dependencia de APIs en la nube** en el camino crítico. El LLM puede ejecutarse vía **`llama-completion`** (subprocess) o vía **`llama-server` en localhost** (HTTP al propio dispositivo, modelo en RAM) según documentación de latencia. Por defecto el **system prompt** está orientado a **público general** en español; un **filtro de salida** infantil es **opcional**.

## Requirements

### Requirement: Pipeline offline STT → LLM → TTS

El sistema SHALL ejecutar una cadena en el orden: **entrada de audio (WAV 16 kHz mono hacia STT)** → **transcripción** → **generación de texto (LLM)** → **síntesis de voz (TTS)** → **archivo de audio de salida** (y opcionalmente reproducción por ALSA), sin utilizar servicios de red para STT, LLM ni TTS en ese camino.

#### Scenario: Inferencia sin red

- **WHEN** el operador ejecuta el pipeline documentado con modelos y binarios locales
- **THEN** no SHALL realizarse peticiones HTTP/HTTPS a **servicios remotos** de terceros para STT, LLM o TTS durante el procesamiento de un turno
- **AND** si el LLM usa **`llama-server` en localhost**, las peticiones HTTP SHALL limitarse a ese proceso en el mismo dispositivo (documentado en `LATENCY.md`)

### Requirement: Componentes concretos

El sistema SHALL usar **Whisper tiny** (whisper.cpp o equivalente documentado) para STT, **Phi-3-mini** en **GGUF** para el LLM mediante **`llama-completion`** (subprocess; no la UI de chat como sustituto del batch documentado) **o** mediante **`llama-server`** con la misma familia de modelo cargada localmente, y **Piper** con voz en **español** para TTS, salvo sustitución documentada compatible.

#### Scenario: Versiones documentadas

- **WHEN** un operador instala según la guía del repositorio
- **THEN** la documentación SHALL indicar nombres de modelos (p. ej. `ggml-tiny.bin`, Phi-3-mini GGUF **Q4_K_M** o **Q4_0**), rutas de binarios (`WHISPER_BIN`, `LLAMA_COMPLETION` o `VOICE_LLAMA_SERVER_URL`, `PIPER_BIN`) y pares **`.onnx` + `.json`** de Piper

### Requirement: Latencia y documentación operativa

El repositorio SHALL documentar cómo **reducir latencia** en hardware limitado (p. ej. **mantener el modelo en RAM** con `llama-server`, **menos tokens de salida** con modo conversación rápida, **grabaciones más cortas**, ajuste de hilos), sin prometer tiempos “instantáneos” irreales para Phi-3 en CPU en Pi.

#### Scenario: Guía de latencia

- **WHEN** un operador busca mejorar la fluidez entre turnos
- **THEN** la documentación SHALL incluir `voice-pipeline/LATENCY.md` (o equivalente enlazado desde el README del pipeline) con el orden de impacto de las optimizaciones

### Requirement: Contexto LLM y tamaño de prompt

El pipeline SHALL usar un **tamaño de contexto (`-c`)** en cliente o servidor acorde al prompt completo (plantilla Phi-3 + system + transcripción) cuando aplica a `llama-completion` o `llama-server`. **VOICE_LLAMA_CTX** SHALL ser **al menos 1024** en configuraciones soportadas por defecto; **2048** es el valor documentado por defecto. Contextos del orden de **512** SHALL considerarse insuficientes para el prompt típico y SHALL estar desaconsejados salvo excepción explícita documentada (`VOICE_LLAMA_ALLOW_SMALL_CTX`).

#### Scenario: Prompt demasiado largo

- **WHEN** el prompt tokenizado excede el contexto configurado
- **THEN** la documentación SHALL explicar el error tipo `prompt is too long` y la corrección (subir `VOICE_LLAMA_CTX`, acortar system prompt o grabación)

### Requirement: System prompt y audiencia por defecto

El **system prompt** por defecto SHALL cargarse desde **`voice-pipeline/prompts/system_general.txt`** (español, público general, respuestas breves, una contrapregunta como máximo cuando aplique). El operador SHALL poder sustituirlo con **`VOICE_SYSTEM_PROMPT`** apuntando a un archivo `.txt`.

#### Scenario: Prompt personalizado

- **WHEN** `VOICE_SYSTEM_PROMPT` apunta a un archivo existente
- **THEN** el pipeline SHALL usar ese contenido como system en la plantilla Phi-3

### Requirement: Filtro de salida opcional (uso infantil)

Un **filtro de salida** (`output_filter.py` + lista de términos) SHALL existir para entornos que requieran sustitución de respuestas fuera de un dominio seguro. Por defecto el filtro **no** SHALL ejecutarse; SHALL activarse solo si **`VOICE_OUTPUT_FILTER=1`** (o equivalente documentado).

#### Scenario: Filtro desactivado

- **WHEN** `VOICE_OUTPUT_FILTER` no está activado
- **THEN** el texto enviado a Piper SHALL ser el producido por el LLM tras la capa de saneado de salida del propio pipeline (extracción de respuesta, no TTS de logs crudos)

#### Scenario: Filtro activado

- **WHEN** `VOICE_OUTPUT_FILTER=1`
- **THEN** el texto SHALL pasar por `output_filter.py` antes de Piper y, si aplica, sustituirse por una respuesta segura predefinida según la política del script

### Requirement: Voz Piper en español

La voz Piper SHALL configurarse mediante **`PIPER_VOICE_ONNX`** y **`PIPER_VOICE_JSON`**. El repositorio SHALL documentar al menos un par de voz español reproducible (p. ej. **`es_MX-ald-medium`** en `env.example`) y referencias a otras voces (p. ej. **`es_CO-female-medium`**) en documentación de modelos cuando estén disponibles en el índice de Piper.

#### Scenario: Voz sustituible

- **WHEN** el operador instala otro modelo Piper en español coherente con Piper
- **THEN** SHALL poder enlazarlo solo cambiando variables de entorno, sin modificar el código del orquestador

### Requirement: Ejecución en Raspberry Pi 4

El sistema SHALL poder ejecutarse en **Raspberry Pi 4**, **ARM64**, RAM típica **4 GB**, documentando **swap**, **`VOICE_LLAMA_CTX`**, límites de tokens de salida (**`-n`**) y timeouts para evitar OOM o cortes. La documentación SHALL alinear el SO de referencia con **Debian GNU/Linux 13 (trixie)** ARM64 cuando el proyecto lo declare.

#### Scenario: Documentación de recursos

- **WHEN** se publica la guía de instalación
- **THEN** la guía SHALL incluir requisitos de RAM/disco, SO de referencia, estimación de orden de magnitud de tiempo por turno en Pi y opciones de **`VOICE_LLAMA_THREADS`**, timeouts y mediciones (`pipeline_timings.txt` cuando se use `--log-dir`)

### Requirement: Punto de entrada reproducible

El sistema SHALL exponer comandos documentados para: **pipeline Python** (`voice_pipeline.py` con WAV de entrada), **micrófono en vivo** (`live_mic_pipeline.sh`), y **pruebas aisladas** por etapa (scripts STT/LLM/TTS), de forma repetible tras copiar `env.example` a `.env` y ajustar rutas.

#### Scenario: Prueba de extremo a extremo

- **WHEN** el operador ejecuta el flujo documentado con modelos locales
- **THEN** el sistema SHALL completar sin error fatal y producir un WAV de salida o artefactos verificables (`stt.txt`, `llm_raw.txt`, `llama_stdout.txt` con `--log-dir`)

### Requirement: Privacidad local

Durante la inferencia de un turno en modo offline documentado, **ningún audio ni texto del usuario** SHALL enviarse a servicios remotos como parte del pipeline (STT/LLM/TTS). Los binarios y modelos SHALL residir en el dispositivo o medios locales montados.

#### Scenario: Sin exfiltración en el camino crítico

- **WHEN** se ejecuta solo el pipeline documentado sin servicios adicionales
- **THEN** el procesamiento del turno SHALL no depender de APIs externas para STT, LLM o TTS

### Requirement: Salida del LLM apta para TTS

El orquestador SHALL **extraer y limpiar** la salida de `llama-completion` para que Piper no lea logs, métricas, marcadores tipo `[end of text]`, bloques de traducción bilingüe ni párrafos que imiten un system prompt espurio, según la lógica documentada en el script del pipeline (expresiones regulares y reglas de saneado).

#### Scenario: Texto hablable

- **WHEN** el LLM devuelve mezcla de logs y respuesta
- **THEN** el texto pasado al TTS SHALL contener principalmente la respuesta conversacional destinada al usuario, no la basura de consola del runtime
