## ADDED Requirements

### Requirement: Pipeline offline STT → LLM → TTS

El sistema SHALL ejecutar una cadena de procesamiento de voz en el orden: **entrada de audio** → **transcripción (STT)** → **generación de texto (LLM)** → **síntesis de voz (TTS)** → **salida de audio**, sin utilizar servicios de red para inferencia en esa cadena.

#### Scenario: Inferencia sin red

- **WHEN** el pipeline se ejecuta en modo offline documentado
- **THEN** no SHALL realizarse peticiones HTTP/HTTPS a APIs de terceros para STT, LLM o TTS durante el procesamiento de un turno

### Requirement: Componentes concretos

El sistema SHALL usar **Whisper tiny** (o equivalente documentado como “tiny”) para STT, **Phi-3-mini** en formato **GGUF** para el LLM, y **Piper TTS** con voz en **español** para la salida hablada, salvo documentación explícita de sustituto compatible.

#### Scenario: Versiones documentadas

- **WHEN** un operador instala el sistema siguiendo la documentación del cambio
- **THEN** la documentación SHALL indicar nombres de modelos, cuantización GGUF recomendada y nombre o ruta de la voz Piper en español

### Requirement: Ejecución en Raspberry Pi 4

El sistema SHALL poder ejecutarse en **Raspberry Pi 4** con arquitectura **ARM64** y memoria típica de **4 GB** de RAM, documentando uso de swap y límites de tamaño de contexto o longitud de respuesta si son necesarios para evitar fallos por memoria. La documentación del cambio SHALL alinear el SO de referencia con el repositorio principal: **Debian GNU/Linux 13 (trixie)** ARM64 (coherente con `README.md` del proyecto).

#### Scenario: Documentación de recursos

- **WHEN** se publica la guía de instalación
- **THEN** la guía SHALL incluir requisitos mínimos de RAM/disco, SO de referencia (Debian 13 trixie ARM64) y una estimación de orden de magnitud de latencia o tiempo por turno

### Requirement: Punto de entrada reproducible

El sistema SHALL exponer al menos un **comando o script** documentado que invoque el pipeline completo (por ejemplo: entrada de audio de prueba → salida de audio o texto de registro), de forma que la verificación sea repetible en una instalación limpia.

#### Scenario: Prueba de extremo a extremo

- **WHEN** el operador ejecuta el comando de prueba documentado tras instalar modelos locales
- **THEN** el sistema SHALL completar el pipeline sin error fatal y producir una salida de audio o un archivo de salida verificable

### Requirement: Voz Piper específica
El sistema SHALL usar la voz **`es_CO-female-medium`** de Piper TTS como voz por defecto,
descargando el modelo `.onnx` y su `.json` correspondiente desde el repositorio oficial de Piper.
#### Scenario: Voz colombiana configurada
- **WHEN** el pipeline ejecuta TTS
- **THEN** la voz de salida SHALL corresponder al modelo `es_CO-female-medium` salvo
  sustitución explícitamente documentada

### Requirement: Contexto de uso infantil y filtros de seguridad
El sistema SHALL operar como asistente educativo para **niños de 2 a 7 años**, lo que implica:
- El system prompt de Phi-3-mini SHALL incluir restricciones de contenido apropiado para
  la edad (lenguaje simple, temas seguros, sin contenido adulto).
- El pipeline SHALL incluir un filtro mínimo de salida que rechace o reformule respuestas
  fuera del dominio educativo definido (valores familiares, límites corporales, pensamiento crítico).
- El procesamiento SHALL ser **100% local**: ningún dato de voz o texto del niño SHALL
  salir del dispositivo durante la inferencia.
#### Scenario: Respuesta fuera de dominio
- **WHEN** Phi-3-mini genera una respuesta que no corresponde al dominio educativo infantil
- **THEN** el sistema SHALL reemplazarla por una respuesta segura predefinida antes de
  pasarla a Piper TTS