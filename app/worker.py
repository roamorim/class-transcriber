import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Transcription
from app.services.transcription import run_transcription
from app.services.pdf import generate_pdf
from app.services.repetition import analyze_repetition

logger = logging.getLogger(__name__)

transcription_queue: asyncio.Queue[int] = asyncio.Queue()


async def transcription_worker() -> None:
    while True:
        record_id = await transcription_queue.get()
        async with AsyncSessionLocal() as db:
            record = await db.get(Transcription, record_id)
            if record is None:
                transcription_queue.task_done()
                continue

            record.status = "processing"
            await db.commit()

            try:
                from pathlib import Path
                audio_path = Path(record.audio_path)
                text = await run_transcription(audio_path)

                report = analyze_repetition(text)
                if report is not None:
                    logger.warning(
                        "Possible repetition loop in transcription id=%s: "
                        "%.0f%% of the text is repeated blocks, top block repeats %s times. Sample: %r",
                        record.id,
                        report.fraction * 100,
                        report.top_count,
                        report.sample,
                    )

                pdf_path = await generate_pdf(record, text)

                record.transcript_text = text
                record.pdf_path = str(pdf_path)
                record.status = "done"
                record.completed_at = datetime.now(timezone.utc)
            except Exception as exc:
                record.status = "error"
                record.error_message = str(exc)

            await db.commit()
        transcription_queue.task_done()
