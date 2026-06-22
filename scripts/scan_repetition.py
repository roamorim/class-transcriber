#!/usr/bin/env python3
"""Scan existing transcriptions for the repetition-loop pattern.

Usage: uv run python scripts/scan_repetition.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.repetition import analyze_repetition


def main() -> None:
    if not settings.db_path.exists():
        print(f"No se encontro la base de datos en {settings.db_path}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT id, discipline, subject, transcript_text FROM transcriptions "
        "WHERE status = 'done' AND transcript_text IS NOT NULL"
    ).fetchall()
    conn.close()

    flagged = []
    for record_id, discipline, subject, text in rows:
        report = analyze_repetition(text)
        if report is not None:
            flagged.append((record_id, discipline, subject, len(text), report))

    print(f"Revisadas {len(rows)} transcripciones completas en {settings.db_path}.")
    if not flagged:
        print("No se detecto repeticion en ninguna.")
        return

    flagged.sort(key=lambda item: item[4].fraction, reverse=True)
    print(f"\n{len(flagged)} transcripcion(es) con posible repeticion:\n")
    print(f"{'id':>4}  {'%rep':>5}  {'veces':>6}  {'chars':>7}  materia")
    for record_id, discipline, subject, length, report in flagged:
        print(
            f"{record_id:>4}  {report.fraction * 100:>4.0f}%  {report.top_count:>6}  "
            f"{length:>7}  {discipline} / {subject}"
        )
        print(f"      muestra: {report.sample!r}\n")


if __name__ == "__main__":
    main()
