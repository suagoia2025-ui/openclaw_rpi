#!/usr/bin/env python3
"""
Pipeline offline: WAV → whisper.cpp → llama-completion (Phi-3 GGUF) → filtro infantil → Piper.
Sin HTTP en tiempo de inferencia; solo subprocess y archivos locales.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_VOICE = Path(__file__).resolve().parent.parent
DEFAULT_SYSTEM = REPO_VOICE / "prompts" / "system_child_educational.txt"
FILTER_SCRIPT = REPO_VOICE / "scripts" / "output_filter.py"


def read_system_prompt() -> str:
    p = os.environ.get("VOICE_SYSTEM_PROMPT", "").strip()
    path = Path(p) if p else DEFAULT_SYSTEM
    if not path.is_file():
        raise FileNotFoundError(f"System prompt no encontrado: {path}")
    return path.read_text(encoding="utf-8").strip()


def run_whisper(
    whisper_bin: str,
    model: str,
    wav: Path,
    work: Path,
    timeout_sec: int,
    language: str | None,
) -> str:
    out_txt = work / "stt.txt"
    # whisper.cpp: -nt sin marcas de tiempo si está disponible; si falla, quitar -nt del comando.
    # Sin -l, whisper-cli suele usar inglés por defecto → basura tipo "The K" con voz en español.
    cmd = [whisper_bin, "-m", model, "-f", str(wav), "-nt"]
    if language and language.lower() != "auto":
        cmd.extend(["-l", language])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"whisper falló: {proc.stderr or proc.stdout}")
    text = (proc.stdout or "").strip()
    if not text and proc.stderr:
        text = proc.stderr.strip()
    if not text:
        out_txt.write_text("", encoding="utf-8")
        return ""
    # Líneas tipo [mm:ss] texto
    cleaned: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\[[^\]]+\]\s*", "", line)
        if line:
            cleaned.append(line)
    joined = " ".join(cleaned)
    out_txt.write_text(joined, encoding="utf-8")
    return joined


def build_phi3_prompt(system: str, user_text: str) -> str:
    """Plantilla tipo Phi-3 instruct (marcadores estilo chat)."""
    u = user_text.strip() or "(silencio o audio poco claro)"
    return (
        f"<|system|>\n{system}<|end|>\n<|user|>\n{u}<|end|>\n<|assistant|>\n"
    )


def run_llama(
    llama_bin: str,
    gguf: Path,
    prompt: str,
    ctx: int,
    max_tokens: int,
    timeout_sec: int,
    threads: str | None,
) -> str:
    # Usar llama-completion (herramienta "completion"), no llama-cli: desde ~2025 llama-cli es
    # solo UI de chat; -no-cnv ahí muestra error y sigue en bucle `>` (upstream: usar llama-completion).
    # -n -1 en llama.cpp = generar hasta llenar contexto (parece “infinito”).
    if max_tokens <= 0:
        max_tokens = 128
    # Ref. upstream tools/completion/completion.cpp: con modo conversación activo, si no hay
    # single_turn + prompt no vacío, se fuerza interactive_first y aparece el prompt `>`.
    # -no-cnv / --no-conversation: desactiva conversación (imprescindible con plantilla en el GGUF).
    # -st: con prompt no vacío, desactiva el modo interactivo en el mismo bloque.
    # --log-disable: menos ruido en stderr al capturar salida.
    cmd = [
        llama_bin,
        "-m",
        str(gguf),
        "--no-conversation",
        "-st",
        "-p",
        prompt,
        "-c",
        str(ctx),
        "-n",
        str(max_tokens),
        "--no-display-prompt",
        "--simple-io",
        "--log-disable",
    ]
    if threads:
        cmd.extend(["-t", threads])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"llama-completion falló: {proc.stderr}")
    out = (proc.stdout or "").strip()
    # Quitar posible repetición del prompt
    out = re.sub(r"^[\s\S]*?<\|assistant\|>\s*", "", out, count=1)
    return out.strip()


def run_filter(py: str, text: str) -> str:
    proc = subprocess.run(
        [py, str(FILTER_SCRIPT)],
        input=text,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"output_filter falló: {proc.stderr}")
    return (proc.stdout or "").strip()


def run_piper(piper_bin: str, onnx: Path, json_path: Path, text: str, out_wav: Path) -> None:
    proc = subprocess.run(
        [piper_bin, "--model", str(onnx), "--config", str(json_path), "--output_file", str(out_wav)],
        input=text,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"piper falló: {proc.stderr}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Pipeline STT → LLM → TTS offline")
    ap.add_argument("input_wav", type=Path, help="Entrada 16 kHz mono WAV (recomendado)")
    ap.add_argument("-o", "--output-wav", type=Path, help="Salida WAV Piper")
    ap.add_argument("--log-dir", type=Path, help="Guardar stt.txt / respuesta intermedia")
    args = ap.parse_args()

    whisper_bin = os.environ.get("WHISPER_BIN", "")
    whisper_model = os.environ.get("WHISPER_MODEL", "")
    llama_bin = os.environ.get("LLAMA_COMPLETION", "").strip() or os.environ.get("LLAMA_CLI", "").strip()
    phi3 = os.environ.get("PHI3_GGUF", "")
    piper_bin = os.environ.get("PIPER_BIN", "")
    piper_onnx = os.environ.get("PIPER_VOICE_ONNX", "")
    piper_json = os.environ.get("PIPER_VOICE_JSON", "")
    ctx = int(os.environ.get("VOICE_LLAMA_CTX", "2048"))
    try:
        ntok = int(os.environ.get("VOICE_LLAMA_MAX_TOKENS", "128"))
    except ValueError:
        ntok = 128
    llama_timeout = int(os.environ.get("VOICE_LLAMA_TIMEOUT_SEC", "2400"))
    whisper_timeout = int(os.environ.get("VOICE_WHISPER_TIMEOUT_SEC", "900"))
    whisper_lang = (os.environ.get("VOICE_WHISPER_LANGUAGE") or "es").strip()
    llama_threads = os.environ.get("VOICE_LLAMA_THREADS", "").strip() or None

    if not llama_bin:
        print(
            "Falta LLAMA_COMPLETION (ruta a llama-completion) o LLAMA_CLI como alternativa",
            file=sys.stderr,
        )
        return 2

    for name, val in [
        ("WHISPER_BIN", whisper_bin),
        ("WHISPER_MODEL", whisper_model),
        ("PHI3_GGUF", phi3),
        ("PIPER_BIN", piper_bin),
        ("PIPER_VOICE_ONNX", piper_onnx),
        ("PIPER_VOICE_JSON", piper_json),
    ]:
        if not val:
            print(f"Falta variable de entorno {name}", file=sys.stderr)
            return 2

    if not args.input_wav.is_file():
        print(
            f"No existe el WAV de entrada: {args.input_wav.resolve()}",
            file=sys.stderr,
        )
        return 2

    out_wav = args.output_wav or args.input_wav.with_name("pipeline_reply.wav")

    sys_prompt = read_system_prompt()
    py = sys.executable

    with tempfile.TemporaryDirectory(prefix="voice-pipeline-") as td:
        work = Path(args.log_dir) if args.log_dir else Path(td)
        if args.log_dir:
            work.mkdir(parents=True, exist_ok=True)

        print("[voice-pipeline] 1/4 STT (Whisper)...", flush=True)
        transcript = run_whisper(
            whisper_bin,
            whisper_model,
            args.input_wav,
            work,
            whisper_timeout,
            whisper_lang or None,
        )
        print(f"[voice-pipeline] STT listo ({len(transcript)} chars). 2/4 LLM (Phi-3)…", flush=True)
        print(
            "[voice-pipeline]    En RPi puede tardar 10–40+ min; timeout="
            f"{llama_timeout}s. Ctrl+C para cancelar.",
            flush=True,
        )
        full_prompt = build_phi3_prompt(sys_prompt, transcript)
        raw_reply = run_llama(
            llama_bin, Path(phi3), full_prompt, ctx, ntok, llama_timeout, llama_threads
        )
        (work / "llm_raw.txt").write_text(raw_reply, encoding="utf-8")
        print("[voice-pipeline] 3/4 Filtro de salida…", flush=True)
        filtered = run_filter(py, raw_reply)
        (work / "llm_filtered.txt").write_text(filtered, encoding="utf-8")
        print("[voice-pipeline] 4/4 TTS (Piper)…", flush=True)
        run_piper(piper_bin, Path(piper_onnx), Path(piper_json), filtered, out_wav)

    print(f"OK: {out_wav}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
