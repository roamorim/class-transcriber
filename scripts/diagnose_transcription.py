#!/usr/bin/env python3
"""Reproduce a transcription to confirm the cause of a repetition-loop bug.

Looks up a record by id, reports the audio's size/duration, and calls Gemini
again on the same file so you can see finish_reason / usage_metadata (logged
by app.services.transcription) and whether the repetition reproduces.

Usage: uv run python scripts/diagnose_transcription.py <id>
"""
import asyncio
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.repetition import analyze_repetition
from app.services.transcription import run_transcription

try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None


def _audio_duration_seconds(path: Path) -> float | None:
    if MutagenFile is None:
        return None
    try:
        audio = MutagenFile(path)
    except Exception:
        return None
    if audio is None or audio.info is None:
        return None
    return getattr(audio.info, "length", None)


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: uv run python scripts/diagnose_transcription.py <id>")
        sys.exit(1)

    record_id = int(sys.argv[1])
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not settings.db_path.exists():
        print(f"No se encontro la base de datos en {settings.db_path}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    row = conn.execute(
        "SELECT discipline, subject, audio_path, status, transcript_text "
        "FROM transcriptions WHERE id = ?",
        (record_id,),
    ).fetchone()
    conn.close()

    if row is None:
        print(f"No existe ningun registro con id={record_id} en {settings.db_path}")
        sys.exit(1)

    discipline, subject, audio_path_str, status, existing_text = row
    print(f"Registro #{record_id}: {discipline} / {subject} (status={status})")

    audio_path = Path(audio_path_str)
    if not audio_path.is_absolute():
        audio_path = Path.cwd() / audio_path
    if not audio_path.exists():
        print(f"ATENCION: no se encontro el archivo de audio en {audio_path}")
        sys.exit(1)

    size_mb = audio_path.stat().st_size / (1024 * 1024)
    duration = _audio_duration_seconds(audio_path)
    if duration is not None:
        print(f"Audio: {audio_path} -- {size_mb:.1f} MB, {duration / 60:.1f} minutos")
    else:
        print(f"Audio: {audio_path} -- {size_mb:.1f} MB (no se pudo leer la duracion, instala 'mutagen')")

    if existing_text:
        existing_report = analyze_repetition(existing_text)
        if existing_report:
            print(
                f"Transcripcion ya guardada: {len(existing_text)} caracteres, "
                f"{existing_report.fraction * 100:.0f}% repetido "
                f"(bloque repetido {existing_report.top_count} veces)"
            )
        else:
            print(f"Transcripcion ya guardada: {len(existing_text)} caracteres, sin repeticion detectada")

    print("\nLlamando de nuevo a Gemini para intentar reproducir el problema "
          "(esto consume cuota real de la API)...")
    new_text = asyncio.run(run_transcription(audio_path))

    new_report = analyze_repetition(new_text)
    print(f"\nNueva transcripcion: {len(new_text)} caracteres")
    if new_report:
        print(
            f"-> Repeticion detectada: {new_report.fraction * 100:.0f}% del texto, "
            f"bloque repetido {new_report.top_count} veces"
        )
        print(f"-> Muestra del bloque repetido: {new_report.sample!r}")
    else:
        print("-> No se detecto repeticion en este intento (el problema puede ser intermitente)")


if __name__ == "__main__":
    main()
