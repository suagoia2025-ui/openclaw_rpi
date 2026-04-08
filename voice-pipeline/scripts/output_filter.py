#!/usr/bin/env python3
"""
Filtro mínimo de salida para dominio infantil (heurístico).
Si detecta términos bloqueados o respuesta vacía, devuelve un mensaje seguro predefinido.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_SAFE = (
    "Ups, no puedo contarte eso. ¿Quieres que hablemos de algo divertido y seguro?"
)


def load_blocklist(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.lower())
    return out


def should_block(text: str, blocklist: set[str]) -> bool:
    """Bloquea solo si aparece el término como palabra completa (evita falsos positivos)."""
    t = text.lower()
    for term in blocklist:
        if not term:
            continue
        # Palabra completa (Unicode); antes "droga" coincidía dentro de "drogas" y bloqueaba demasiado.
        if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", t, re.UNICODE):
            return True
    # URLs o correos en respuesta a niños pequeños → sustituir
    if re.search(r"https?://|@\w+\.\w+", t):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Filtra salida del LLM para uso infantil.")
    ap.add_argument(
        "--blocklist",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "filter" / "blocked_terms.txt",
        help="Lista de términos bloqueados (una por línea)",
    )
    ap.add_argument(
        "--safe",
        default=DEFAULT_SAFE,
        help="Mensaje de reemplazo si se bloquea o está vacío",
    )
    ap.add_argument(
        "text",
        nargs="?",
        help="Texto a filtrar; si se omite, se lee de stdin",
    )
    args = ap.parse_args()
    raw = args.text if args.text is not None else sys.stdin.read()
    text = raw.strip()
    blocklist = load_blocklist(args.blocklist)

    if not text or should_block(text, blocklist):
        print(args.safe)
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
