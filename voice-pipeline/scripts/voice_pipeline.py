#!/usr/bin/env python3
"""
Pipeline offline: WAV → whisper.cpp → llama-completion (Phi-3 GGUF) → Piper.
Filtro infantil opcional (VOICE_OUTPUT_FILTER=1 → output_filter.py).
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


def _line_is_llama_noise(s: str) -> bool:
    """True si la línea parece log/métrica/código de llama.cpp (no debe ir a Piper)."""
    t = s.strip()
    if not t:
        return False
    if re.match(
        r"^(main:|llama_|load:|print_info:|sched_|sampler |encoding|gguf|common_init|"
        r"llama_context|llama_kv|llama_model|llama_memory|whisper|Running|==|generate:|"
        r"system_info:|ggml_|print_timings|common_perf|common_|sched_reserve|load_tensors|"
        r"print_info:|llama_params|llama_sampler|token to piece|^\s*\.+\s*$)",
        t,
        re.I,
    ):
        return True
    if re.match(r"^\s*#(include|define|pragma|if|ifdef|ifndef|endif|else|elif)\b", t, re.I):
        return True
    if re.match(r"^\s*(def |async def |class |import |from |public:|private:|protected:)", t):
        return True
    if re.search(
        r"(^common_perf_print:|\b(t/s|tokens per|ms per|eval time|sampling time|load time|prompt eval|"
        r"unaccounted|graphs reused|memory breakdown|MiB|KV buffer|Flash.?Attn|"
        r"n_ctx|n_batch|n_predict|n_keep|threadpool|backend init)\b)",
        t,
        re.I,
    ):
        return True
    if re.search(
        r"\b(void|int|char|bool|size_t|uint\d*_t|std::|template|namespace|nullptr|"
        r"static_cast|reinterpret_cast|constexpr|typedef|struct |enum )\b",
        t,
    ):
        return True
    if "::" in t and re.search(r"\b[a-z_][a-z0-9_]*::", t, re.I):
        return True
    sym = sum(1 for c in t if c in "()[]{}<>;=&|!+-*/%")
    if sym >= 6 and sym * 3 > len(t):
        return True
    if ("{" in t or "}" in t) and sym >= 3:
        return True
    if t.rstrip().endswith(";") and "(" in t and ")" in t:
        return True
    if re.match(r"^[\d\s\.\,\-\:\/\|\%\+\=\(\)x\*]+$", t) and len(t) > 5:
        return True
    if re.search(r"=\s*\d", t) and re.search(r"\d{3,}", t) and len(t) < 120:
        return True
    if len(t) > 160 and t.count(" ") < 4:
        return True
    return False


def _strip_special_tokens(s: str) -> str:
    return re.sub(r"<\|[^|]+\|>", "", s).strip()


def _strip_markdown_fences(s: str) -> str:
    """Quita bloques ``` ... ``` (el modelo a veces inventa código; Piper no debe leerlo)."""
    s = re.sub(r"(?s)```[a-zA-Z0-9_-]*\s*\r?\n.*?```", " ", s)
    return re.sub(r"```+", " ", s).strip()


def _line_looks_like_speech_line(line: str) -> bool:
    """True si la línea parece frase hablada (español), no basura numérica ni pseudo-código."""
    t = line.strip()
    if not t:
        return False
    if "```" in t or t.startswith("`") or t.endswith("`"):
        return False
    if "{" in t or "}" in t:
        return False
    if "::" in t:
        return False
    if t.rstrip().endswith(";") and "(" in t:
        return False
    letters = sum(1 for c in t if c.isalpha())
    digits = sum(1 for c in t if c.isdigit())
    if letters + digits == 0:
        return False
    if digits > max(2, letters * 0.35):
        return False
    if letters < 6 and len(t) < 28:
        return letters >= 2 and any(c in t.lower() for c in "aeiouáéíóú")
    low = t.lower()
    vowels = sum(1 for c in low if c in "aeiouáéíóú")
    return vowels >= 2 and vowels >= max(2, letters // 6)


def _prefer_last_prose_paragraph(s: str) -> str:
    """Si hay basura delante y la respuesta buena al final, quedarse con el último bloque con sentido."""
    s = s.strip()
    if not s:
        return s
    lines = [ln.strip() for ln in s.split("\n") if ln.strip()]
    runs: list[list[str]] = []
    cur: list[str] = []
    for ln in lines:
        if _line_looks_like_speech_line(ln):
            cur.append(ln)
        else:
            if cur:
                runs.append(cur)
                cur = []
    if cur:
        runs.append(cur)
    if len(runs) >= 2:
        return "\n".join(runs[-1]).strip()
    if len(runs) == 1 and len(lines) >= 2:
        return "\n".join(runs[0]).strip()
    parts = [p.strip() for p in re.split(r"\n\s*\n+", s) if p.strip()]
    if len(parts) >= 2:
        for p in reversed(parts):
            if len(p) < 20:
                continue
            low = p.lower()
            if sum(1 for c in low if c in "aeiouáéíóú") >= max(3, len(p) // 25):
                return p
    return s


def _clean_model_lines(body: str) -> str:
    lines_out: list[str] = []
    for li in body.splitlines():
        if _line_is_llama_noise(li):
            continue
        lines_out.append(li)
    text = "\n".join(lines_out).strip()
    text = _strip_special_tokens(text)
    text = _strip_markdown_fences(text)
    return _prefer_last_prose_paragraph(text)


def extract_llama_completion_text(raw: str) -> str:
    """Obtiene solo el texto hablado para TTS, sin logs ni métricas de llama-completion."""
    raw = (raw or "").replace("\r\n", "\n").strip()
    if not raw:
        return ""
    # Puede haber ruido antes del primer Answer; el último bloque suele ser la generación actual.
    blocks = re.findall(
        r"(?ms)^#?\s*Answer\s*\n(.*?)(?=\n\s*\[end of text\])",
        raw,
    )
    if blocks:
        return _clean_model_lines(blocks[-1])
    m = re.search(
        r"(?ms)^#?\s*Answer\s*\n(.*?)(?=\n\s*\[end of text\]|\ncommon_perf_print:|\Z)",
        raw,
    )
    if m and m.group(1).strip():
        return _clean_model_lines(m.group(1))
    if "<|assistant|>" in raw:
        tail = re.sub(r"^[\s\S]*?<\|assistant\|>\s*", "", raw, count=1)
        tail = re.sub(r"\n\s*\[end of text\].*", "", tail, flags=re.I | re.DOTALL)
        return _clean_model_lines(tail)
    head = re.split(r"\ncommon_perf_print:", raw, maxsplit=1)[0]
    head = re.split(r"\n\s*\[end of text\]", head, maxsplit=1, flags=re.I)[0]
    lines_kept: list[str] = []
    for li in head.split("\n"):
        s = li.strip()
        if not s:
            if lines_kept:
                lines_kept.append("")
            continue
        if _line_is_llama_noise(li):
            continue
        lines_kept.append(li)
    tail = _strip_markdown_fences(_strip_special_tokens("\n".join(lines_kept).strip()))
    return _prefer_last_prose_paragraph(tail)


def run_llama(
    llama_bin: str,
    gguf: Path,
    prompt: str,
    ctx: int,
    max_tokens: int,
    timeout_sec: int,
    threads: str | None,
    work_debug: Path | None = None,
) -> tuple[str, str]:
    # Usar llama-completion (herramienta "completion"), no llama-cli: desde ~2025 llama-cli es
    # solo UI de chat; -no-cnv ahí muestra error y sigue en bucle `>` (upstream: usar llama-completion).
    # -n -1 en llama.cpp = generar hasta llenar contexto (parece “infinito”).
    if max_tokens <= 0:
        max_tokens = 128
    # Ref. upstream tools/completion/completion.cpp: con modo conversación activo, si no hay
    # single_turn + prompt no vacío, se fuerza interactive_first y aparece el prompt `>`.
    # -no-cnv / --no-conversation: desactiva conversación (imprescindible con plantilla en el GGUF).
    # -st: con prompt no vacío, desactiva el modo interactivo en el mismo bloque.
    # No usar --log-disable aquí: en varias builds oculta el bloque "# Answer" y la extracción queda vacía.
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
    ]
    if threads:
        cmd.extend(["-t", threads])
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        tail = (proc.stdout or "")[-6000:]
        raise RuntimeError(f"llama-completion falló: {tail}")
    # Unificar flujo como en terminal: la respuesta suele ir con logs; # Answer es lo habitual.
    combined = (proc.stdout or "").replace("\r\n", "\n")
    text = extract_llama_completion_text(combined)
    return text, combined


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
    ap.add_argument(
        "--log-dir",
        type=Path,
        help="Guardar stt.txt, llama_stdout.txt (salida cruda), llm_raw.txt (texto ya extraído para TTS), etc.",
    )
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
    use_output_filter = os.environ.get("VOICE_OUTPUT_FILTER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )

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

    with tempfile.TemporaryDirectory(prefix="voice-pipeline-") as td:
        work = Path(args.log_dir) if args.log_dir else Path(td)
        if args.log_dir:
            work.mkdir(parents=True, exist_ok=True)

        ntot = 4 if use_output_filter else 3
        print(f"[voice-pipeline] 1/{ntot} STT (Whisper)...", flush=True)
        transcript = run_whisper(
            whisper_bin,
            whisper_model,
            args.input_wav,
            work,
            whisper_timeout,
            whisper_lang or None,
        )
        print(f"[voice-pipeline] STT listo ({len(transcript)} chars). 2/{ntot} LLM (Phi-3)…", flush=True)
        print(
            "[voice-pipeline]    En RPi puede tardar 10–40+ min; timeout="
            f"{llama_timeout}s. Ctrl+C para cancelar.",
            flush=True,
        )
        full_prompt = build_phi3_prompt(sys_prompt, transcript)
        extracted, llama_stdout = run_llama(
            llama_bin,
            Path(phi3),
            full_prompt,
            ctx,
            ntok,
            llama_timeout,
            llama_threads,
            work,
        )
        if args.log_dir:
            (work / "llama_stdout.txt").write_text(llama_stdout[-500_000:], encoding="utf-8")
        raw_reply = extracted
        (work / "llm_raw.txt").write_text(raw_reply, encoding="utf-8")
        if use_output_filter:
            print("[voice-pipeline] 3/4 Filtro de salida…", flush=True)
            tts_text = run_filter(sys.executable, raw_reply)
            (work / "llm_filtered.txt").write_text(tts_text, encoding="utf-8")
            print("[voice-pipeline] 4/4 TTS (Piper)…", flush=True)
        else:
            tts_text = raw_reply
            print("[voice-pipeline] 3/3 TTS (Piper), salida directa del LLM…", flush=True)
        if not tts_text.strip():
            tts_text = "No tengo respuesta en este momento."
        run_piper(piper_bin, Path(piper_onnx), Path(piper_json), tts_text, out_wav)

    print(f"OK: {out_wav}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
