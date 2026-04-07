# Checklist: verificación end-to-end (instalación limpia)

Marca cada paso en la Raspberry Pi (Debian 13 trixie ARM64) tras copiar el repo y preparar modelos.

- [ ] `cat /etc/os-release` coincide con el SO de referencia del [`README.md`](../README.md).
- [ ] Existe `~/voice-models/` (o ruta elegida) con `ggml-tiny.bin`, un único `.gguf` Phi-3-mini Q4 y `es_CO-female-medium.onnx` + `.json`.
- [ ] `WHISPER_BIN`, `WHISPER_MODEL`, `LLAMA_CLI`, `PHI3_GGUF`, `PIPER_BIN`, `PIPER_VOICE_ONNX`, `PIPER_VOICE_JSON` están definidos (p. ej. en `voice-pipeline/.env`).
- [ ] Prueba STT: `bash scripts/stt_whisper_cpp.sh /ruta/prueba_16k_mono.wav` devuelve texto razonable.
- [ ] Prueba LLM: `bash scripts/llm_llama_cli.sh` con un prompt corto devuelve texto.
- [ ] Prueba TTS: `echo "Hola" | bash scripts/tts_piper.sh /tmp/t.wav` crea WAV válido.
- [ ] `python3 scripts/output_filter.py <<< "texto limpio"` imprime el texto; con un término de `filter/blocked_terms.txt` imprime el mensaje seguro.
- [ ] Pipeline: `python3 scripts/voice_pipeline.py /ruta/prueba_16k_mono.wav -o /tmp/reply.wav --log-dir /tmp/voice-e2e` termina sin error y genera `/tmp/reply.wav` (y logs en `/tmp/voice-e2e` si se usó `--log-dir`).
