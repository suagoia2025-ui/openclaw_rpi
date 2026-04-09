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
import time
import tempfile
from pathlib import Path

REPO_VOICE = Path(__file__).resolve().parent.parent
DEFAULT_SYSTEM = REPO_VOICE / "prompts" / "system_general.txt"
FILTER_SCRIPT = REPO_VOICE / "scripts" / "output_filter.py"

# Marcador de fin de secuencia de llama.cpp; a veces queda pegado al texto generado.
_RE_END_OF_TEXT_BRACKET = re.compile(r"\[\s*end\s+of\s+text\s*\]", re.I)


def read_system_prompt() -> str:
    p = os.environ.get("VOICE_SYSTEM_PROMPT", "").strip()
    path = Path(p) if p else DEFAULT_SYSTEM
    if not path.is_file():
        raise FileNotFoundError(f"System prompt no encontrado: {path}")
    return path.read_text(encoding="utf-8").strip()


def compute_llama_output_tokens(llama_timeout_sec: int, ctx_size: int) -> tuple[int, str]:
    """
    Calcula -n (tokens de salida) para no cortar respuestas largas en español: sube el límite si
    el timeout lo permite (tokens/s estimados en ARM), con techo por VOICE_LLAMA_MAX_TOKENS y por
    espacio libre en el contexto (prompt sistema+usuario ocupa parte de -c).
    """
    raw = os.environ.get("VOICE_LLAMA_MAX_TOKENS", "").strip()
    try:
        user_cap = int(raw) if raw else 768
    except ValueError:
        user_cap = 768
    user_cap = max(64, min(user_cap, 4096))

    try:
        floor_out = int(os.environ.get("VOICE_LLAMA_MIN_OUTPUT_TOKENS", "256"))
    except ValueError:
        floor_out = 256
    floor_out = max(64, min(floor_out, user_cap))

    try:
        est_tps = float(os.environ.get("VOICE_LLAMA_EST_TOKENS_PER_SEC", "2.5"))
    except ValueError:
        est_tps = 2.5
    est_tps = max(0.3, min(est_tps, 80.0))

    try:
        margin = float(os.environ.get("VOICE_LLAMA_TIMEOUT_TOKEN_MARGIN", "0.88"))
    except ValueError:
        margin = 0.88
    margin = max(0.5, min(margin, 1.0))

    from_time = int(llama_timeout_sec * est_tps * margin)

    try:
        ctx_reserve = int(os.environ.get("VOICE_LLAMA_CTX_RESERVE", "520"))
    except ValueError:
        ctx_reserve = 520
    ctx_reserve = max(200, min(ctx_reserve, ctx_size - 80))
    ctx_room = max(128, ctx_size - ctx_reserve)

    n = min(user_cap, ctx_room, max(floor_out, from_time))
    n = max(64, n)
    detail = (
        f"cap={user_cap} piso={floor_out} desde_timeout≈{from_time} "
        f"ctx_libre={ctx_room} (est {est_tps} tok/s × {llama_timeout_sec}s × {margin})"
    )
    return n, detail


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
    if re.search(
        r"(?i)(instrucci[oó]n\s*\d|r[úu]brica|evaluaci[oó]n\s*(tipo|de|del)|"
        r"afinemos la respuesta|interferencia lingüística|interferencia linguistica|"
        r"^\*+\s*instrucci)",
        t,
    ):
        return True
    if _RE_END_OF_TEXT_BRACKET.fullmatch(t) or re.match(r"(?i)^\s*end\s+of\s+text\s*$", t):
        return True
    if re.match(
        r"(?i)^\s*\(?\s*translation\s*:",
        t,
    ) or re.match(r"(?i)^\s*\(?\s*traducci[oó]n\s*:", t):
        return True
    if re.match(r"(?i)^\s*\(?\s*in english\s*:", t):
        return True
    return False


def _strip_bilingual_translation_note(s: str) -> str:
    """Quita bloques (Translation: …) / traducción al inglés que el modelo a veces añade."""
    if not s:
        return s
    for pat in (
        r"(?is)\n\s*\(\s*translation\s*:.*",
        r"(?is)\n\s*\(\s*traducci[oó]n\s*:.*",
        r"(?is)\n\s*translation\s*:\s*.*",
        r"(?is)\n\s*\[en inglés\]\s*:?.*",
        r"(?is)\n\s*\(\s*in english\s*:.*",
    ):
        s = re.split(pat, s, maxsplit=1)[0]
    s = re.sub(r"(?is)\s*\(\s*translation\s*:\s*[^)]{1,4000}\)", "", s)
    s = re.sub(r"(?is)\s*\(\s*traducci[oó]n\s*:\s*[^)]{1,4000}\)", "", s)
    return s.strip()


def _strip_end_of_text_markers(s: str) -> str:
    """Quita [end of text] y variantes (espacios, sin cierre de corchete) para que Piper no lo lea."""
    if not s:
        return s
    s = _RE_END_OF_TEXT_BRACKET.sub(" ", s)
    s = re.sub(r"(?i)\[\s*end\s+of\s+text\s*$", " ", s)
    s = re.sub(r"(?i)\bend\s+of\s+text\b", " ", s)
    return re.sub(r"  +", " ", s).strip()


def _strip_special_tokens(s: str) -> str:
    s = re.sub(r"<\|[^|]+\|>", "", s)
    s = _strip_end_of_text_markers(s)
    return s.strip()


def _strip_markdown_fences(s: str) -> str:
    """Quita bloques ``` ... ``` (el modelo a veces inventa código; Piper no debe leerlo)."""
    s = re.sub(r"(?s)```[a-zA-Z0-9_-]*\s*\r?\n.*?```", " ", s)
    return re.sub(r"```+", " ", s).strip()


def _strip_markdown_spans(s: str) -> str:
    """Quita **negrita** y *cursiva* para TTS; los asteriscos suenan raros o leen basura."""
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", s)
    return re.sub(r"\*+", "", s).strip()


def _strip_rubric_leakage(s: str) -> str:
    """Corta texto de rúbrica / datos de entrenamiento que a veces filtra el modelo."""
    if not s:
        return s
    for pat in (
        r"(?is)\n\s*\*+\s*instrucci[oó]n\b",
        r"(?i)[?!…]\s+\*+\s*instrucci[oó]n\b",
        r"(?is)\n\s*instrucci[oó]n\s*\d+\s",
        r"(?is)\n\s*afinemos la respuesta\b",
        r"(?is)\n\s*escucho interferencia lingüística\b",
        r"(?is)\n\s*escucho interferencia linguistica\b",
        r"(?i)\binterferencia lingüística\b",
        r"(?i)\binterferencia linguistica\b",
        r"(?is)\n\s*r[úu]brica\b",
        r"(?is)\n\s*evaluaci[oó]n\s*\(",
    ):
        m = re.search(pat, s)
        if m:
            s = s[: m.start()].strip()
    return s


def _strip_assistant_meta_tail(s: str) -> str:
    """Quita colas meta del modelo (orientación, 'otras respuestas', etc.) tras una respuesta válida."""
    if not s:
        return s
    # Tras punto + espacio: cortar desde la frase meta (conserva "… azul.").
    for pat in (
        r"(?i)\.\s+para mantener la orientación\b",
        r"(?i)\.\s+aquí hay (algunas |varias )?otr[ao]s\b",
        r"(?i)\.\s+aquí tienes (algunas |varias )?",
        r"(?i)\.\s+como has solicitado\b",
        r"(?i)\.\s+siguiendo con tu\b",
        r"(?i)\.\s+en cuanto a la orientación\b",
    ):
        m = re.search(pat, s)
        if m:
            return s[: m.start() + 1].strip()
    # Sin punto antes (menos frecuente): cortar desde espacio + frase meta.
    for pat in (
        r"(?i)\s+para mantener la orientación\b",
        r"(?i)\s+aquí hay (algunas |varias )?otr[ao]s\b",
        r"(?i)\s+como has solicitado\b",
    ):
        m = re.search(pat, s)
        if m:
            return s[: m.start()].strip().rstrip(".,;:")
    return s


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
    if re.search(r"(?i)(instrucci[oó]n\s*\d|afinemos la respuesta|interferencia lingu)", t):
        return False
    if t.lstrip().startswith("*") and re.search(r"(?i)instrucci[oó]n", t):
        return False
    if re.match(r"(?i)^\s*\(?\s*translation\s*:", t) or re.match(
        r"(?i)^\s*\(?\s*traducci[oó]n\s*:",
        t,
    ):
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
    text = _strip_rubric_leakage(text)
    text = _strip_markdown_spans(text)
    text = _prefer_last_prose_paragraph(text)
    text = _strip_assistant_meta_tail(text)
    text = _strip_rubric_leakage(text)
    text = _strip_bilingual_translation_note(text)
    return _strip_end_of_text_markers(text)


def extract_llama_completion_text(raw: str) -> str:
    """Obtiene solo el texto hablado para TTS, sin logs ni métricas de llama-completion."""
    raw = (raw or "").replace("\r\n", "\n").strip()
    if not raw:
        return ""
    # Puede haber ruido antes del primer Answer; el último bloque suele ser la generación actual.
    blocks = re.findall(
        r"(?ms)^#?\s*Answer\s*\n(.*?)(?=\n\s*\[\s*end\s+of\s+text\s*\])",
        raw,
    )
    if blocks:
        return _clean_model_lines(blocks[-1])
    m = re.search(
        r"(?ms)^#?\s*Answer\s*\n(.*?)(?=\n\s*\[\s*end\s+of\s+text\s*\]|\ncommon_perf_print:|\Z)",
        raw,
    )
    if m and m.group(1).strip():
        return _clean_model_lines(m.group(1))
    if "<|assistant|>" in raw:
        tail = re.sub(r"^[\s\S]*?<\|assistant\|>\s*", "", raw, count=1)
        tail = re.sub(
            r"\n\s*\[\s*end\s+of\s+text\s*\].*",
            "",
            tail,
            flags=re.I | re.DOTALL,
        )
        return _clean_model_lines(tail)
    head = re.split(r"\ncommon_perf_print:", raw, maxsplit=1)[0]
    head = _RE_END_OF_TEXT_BRACKET.split(head, maxsplit=1)[0]
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
    tail = _strip_rubric_leakage(tail)
    tail = _strip_markdown_spans(tail)
    tail = _prefer_last_prose_paragraph(tail)
    tail = _strip_assistant_meta_tail(tail)
    tail = _strip_rubric_leakage(tail)
    tail = _strip_bilingual_translation_note(tail)
    return _strip_end_of_text_markers(tail)


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
        max_tokens = 256
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
        help="Guardar stt.txt, llama_stdout.txt, llm_raw.txt, pipeline_timings.txt (segundos por etapa), etc.",
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
        t0 = time.perf_counter()
        print(f"[voice-pipeline] 1/{ntot} STT (Whisper)...", flush=True)
        t_stt0 = time.perf_counter()
        transcript = run_whisper(
            whisper_bin,
            whisper_model,
            args.input_wav,
            work,
            whisper_timeout,
            whisper_lang or None,
        )
        stt_sec = time.perf_counter() - t_stt0
        print(
            f"[voice-pipeline] STT listo ({len(transcript)} chars) en {stt_sec:.1f} s. "
            f"2/{ntot} LLM (Phi-3)…",
            flush=True,
        )
        print(
            "[voice-pipeline]    En RPi puede tardar 10–40+ min; timeout="
            f"{llama_timeout}s. Ctrl+C para cancelar.",
            flush=True,
        )
        full_prompt = build_phi3_prompt(sys_prompt, transcript)
        ntok, ntok_detail = compute_llama_output_tokens(llama_timeout, ctx)
        print(f"[voice-pipeline] LLM -n {ntok} ({ntok_detail}).", flush=True)
        t_llm0 = time.perf_counter()
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
        llm_sec = time.perf_counter() - t_llm0
        print(f"[voice-pipeline] LLM listo en {llm_sec:.1f} s.", flush=True)
        if args.log_dir:
            (work / "llama_stdout.txt").write_text(llama_stdout[-500_000:], encoding="utf-8")
        raw_reply = extracted
        (work / "llm_raw.txt").write_text(raw_reply, encoding="utf-8")
        filter_sec = 0.0
        if use_output_filter:
            print("[voice-pipeline] 3/4 Filtro de salida…", flush=True)
            t_f0 = time.perf_counter()
            tts_text = run_filter(sys.executable, raw_reply)
            filter_sec = time.perf_counter() - t_f0
            print(f"[voice-pipeline] Filtro listo en {filter_sec:.1f} s.", flush=True)
            (work / "llm_filtered.txt").write_text(tts_text, encoding="utf-8")
            print("[voice-pipeline] 4/4 TTS (Piper)…", flush=True)
        else:
            tts_text = raw_reply
            print("[voice-pipeline] 3/3 TTS (Piper), salida directa del LLM…", flush=True)
        if not tts_text.strip():
            tts_text = "No tengo respuesta en este momento."
        t_p0 = time.perf_counter()
        run_piper(piper_bin, Path(piper_onnx), Path(piper_json), tts_text, out_wav)
        piper_sec = time.perf_counter() - t_p0
        print(f"[voice-pipeline] Piper listo en {piper_sec:.1f} s.", flush=True)

        total_sec = time.perf_counter() - t0
        print(
            f"[voice-pipeline] Tiempos: STT {stt_sec:.1f} s · LLM {llm_sec:.1f} s"
            + (f" · filtro {filter_sec:.1f} s" if use_output_filter else "")
            + f" · Piper {piper_sec:.1f} s · total {total_sec:.1f} s",
            flush=True,
        )
        if args.log_dir:
            lines = [
                f"stt_sec={stt_sec:.3f}",
                f"llm_sec={llm_sec:.3f}",
                f"llama_max_tokens={ntok}",
            ]
            if use_output_filter:
                lines.append(f"filter_sec={filter_sec:.3f}")
            lines.extend(
                [
                    f"piper_sec={piper_sec:.3f}",
                    f"total_sec={total_sec:.3f}",
                ]
            )
            (work / "pipeline_timings.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"OK: {out_wav}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
