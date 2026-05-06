from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Transcription
from app.worker import transcription_queue

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ALLOWED_EXTENSIONS = {"mp3", "m4a", "wav", "ogg", "mp4", "aiff", "flac"}


@router.get("/subir", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse(request, "index.html", {"errors": [], "form": {}})


@router.post("/subir")
async def upload_audio(
    request: Request,
    discipline: str = Form(...),
    subject: str = Form(...),
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    errors = []
    form_data = {"discipline": discipline, "subject": subject}

    if not discipline.strip():
        errors.append("La disciplina es obligatoria.")
    if not subject.strip():
        errors.append("El tema es obligatorio.")

    filename = audio_file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        errors.append(f"Formato no soportado. Usa: {', '.join(sorted(ALLOWED_EXTENSIONS))}.")

    if errors:
        return templates.TemplateResponse(
            request, "index.html", {"errors": errors, "form": form_data}, status_code=422
        )

    contents = await audio_file.read()
    if len(contents) > settings.max_upload_bytes:
        max_mb = settings.max_upload_bytes // (1024 * 1024)
        errors.append(f"El archivo supera el límite de {max_mb} MB.")
        return templates.TemplateResponse(
            request, "index.html", {"errors": errors, "form": form_data}, status_code=422
        )

    safe_name = f"{uuid4().hex}.{ext}"
    file_path = settings.upload_dir / safe_name
    file_path.write_bytes(contents)

    record = Transcription(
        discipline=discipline.strip(),
        subject=subject.strip(),
        original_filename=filename,
        audio_path=str(file_path),
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await transcription_queue.put(record.id)

    return RedirectResponse("/transcripciones", status_code=303)


@router.get("/transcripciones", response_class=HTMLResponse)
async def list_transcriptions(
    request: Request,
    disciplina: str = "",
    estado: str = "",
    q: str = "",
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Transcription).order_by(Transcription.created_at.desc())
    if disciplina:
        stmt = stmt.where(Transcription.discipline == disciplina)
    if estado:
        stmt = stmt.where(Transcription.status == estado)
    if q:
        stmt = stmt.where(
            or_(
                Transcription.subject.ilike(f"%{q}%"),
                Transcription.discipline.ilike(f"%{q}%"),
            )
        )

    result = await db.execute(stmt)
    records = result.scalars().all()

    disc_result = await db.execute(
        select(Transcription.discipline).distinct().order_by(Transcription.discipline)
    )
    disciplines = [row for row in disc_result.scalars().all()]

    return templates.TemplateResponse(
        request,
        "list.html",
        {
            "records": records,
            "disciplines": disciplines,
            "current_disciplina": disciplina,
            "current_estado": estado,
            "current_q": q,
        },
    )


@router.get("/transcripciones/{record_id}", response_class=HTMLResponse)
async def detail_transcription(
    request: Request,
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Transcription, record_id)
    if record is None:
        return templates.TemplateResponse(request, "404.html", {}, status_code=404)
    return templates.TemplateResponse(request, "detail.html", {"record": record})


@router.get("/transcripciones/{record_id}/estado", response_class=HTMLResponse)
async def record_status_row(
    request: Request,
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Transcription, record_id)
    if record is None:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request, "partials/transcription_row.html", {"record": record}
    )


@router.get("/transcripciones/{record_id}/detalle-estado", response_class=HTMLResponse)
async def record_detail_status(
    request: Request,
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Transcription, record_id)
    if record is None:
        return HTMLResponse("")
    return templates.TemplateResponse(request, "detail.html", {"record": record})


@router.post("/transcripciones/{record_id}")
async def delete_transcription(
    record_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    if form.get("_method") != "DELETE":
        return RedirectResponse(f"/transcripciones/{record_id}", status_code=303)

    record = await db.get(Transcription, record_id)
    if record:
        for path_str in [record.audio_path, record.pdf_path]:
            if path_str:
                p = Path(path_str)
                if p.exists():
                    p.unlink()
        await db.delete(record)
        await db.commit()

    return RedirectResponse("/transcripciones", status_code=303)
