import asyncio
from pathlib import Path
from uuid import uuid4

from fpdf import FPDF

from app.config import settings

FONT_PATH = Path(__file__).parent.parent / "fonts" / "DejaVuSans.ttf"
FONT_BOLD_PATH = Path(__file__).parent.parent / "fonts" / "DejaVuSans-Bold.ttf"


def _sync_generate_pdf(
    record_id: int,
    discipline: str,
    subject: str,
    created_at_str: str,
    text: str,
) -> Path:
    pdf = FPDF()
    pdf.set_margins(left=20, top=20, right=20)
    pdf.add_page()

    # Register DejaVu font (Unicode support for Spanish characters)
    pdf.add_font("DejaVu", style="", fname=str(FONT_PATH))
    bold_path = FONT_BOLD_PATH if FONT_BOLD_PATH.exists() else FONT_PATH
    pdf.add_font("DejaVu", style="B", fname=str(bold_path))

    # ── Title ──
    pdf.set_font("DejaVu", style="B", size=16)
    pdf.cell(0, 12, "Transcripción de Clase", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    # ── Metadata table ──
    label_w = 45
    pdf.set_font("DejaVu", style="B", size=10)
    pdf.cell(label_w, 7, "Disciplina:", new_x="RIGHT", new_y="TOP")
    pdf.set_font("DejaVu", size=10)
    pdf.cell(0, 7, discipline, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", style="B", size=10)
    pdf.cell(label_w, 7, "Tema:", new_x="RIGHT", new_y="TOP")
    pdf.set_font("DejaVu", size=10)
    pdf.cell(0, 7, subject, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", style="B", size=10)
    pdf.cell(label_w, 7, "Fecha:", new_x="RIGHT", new_y="TOP")
    pdf.set_font("DejaVu", size=10)
    pdf.cell(0, 7, created_at_str, new_x="LMARGIN", new_y="NEXT")

    # ── Divider ──
    pdf.ln(4)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(20, pdf.get_y(), pdf.w - 20, pdf.get_y())
    pdf.ln(8)

    # ── Transcription body ──
    pdf.set_font("DejaVu", size=11)
    pdf.multi_cell(0, 8, text, align="J")

    # Save PDF
    filename = f"transcripcion_{record_id}_{uuid4().hex[:8]}.pdf"
    out_path = settings.pdf_dir / filename
    pdf.output(str(out_path))
    return out_path


async def generate_pdf(record, text: str) -> Path:
    created_str = record.created_at.strftime("%d/%m/%Y %H:%M")
    return await asyncio.to_thread(
        _sync_generate_pdf,
        record.id,
        record.discipline,
        record.subject,
        created_str,
        text,
    )
