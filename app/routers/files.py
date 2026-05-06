from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Transcription

router = APIRouter()


@router.get("/descargar/pdf/{record_id}")
async def download_pdf(record_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(Transcription, record_id)
    if record is None or not record.pdf_path:
        from fastapi import HTTPException
        raise HTTPException(404, "PDF no encontrado")

    pdf_path = Path(record.pdf_path)
    if not pdf_path.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "Archivo PDF no encontrado en disco")

    safe_name = f"transcripcion_{record.discipline}_{record.subject[:30]}.pdf"
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in safe_name)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=safe_name,
    )


@router.get("/descargar/audio/{record_id}")
async def download_audio(record_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(Transcription, record_id)
    if record is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Registro no encontrado")

    audio_path = Path(record.audio_path)
    if not audio_path.exists():
        from fastapi import HTTPException
        raise HTTPException(404, "Archivo de audio no encontrado")

    return FileResponse(
        path=str(audio_path),
        filename=record.original_filename,
    )
