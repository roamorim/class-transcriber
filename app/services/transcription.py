import asyncio
import logging
import warnings
from pathlib import Path

from google import genai

from app.config import settings
from app.services.repetition import analyze_repetition

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

MAX_ATTEMPTS = 3

_SYSTEM_INSTRUCTION = (
    "Transcribe el audio completo de esta clase de forma literal y precisa. "
    "Incluye todo lo que se dice, respetando el idioma original. "
    "No agregues comentarios, resúmenes ni anotaciones. "
    "Solo entrega el texto transcrito."
)

_MIME_MAP = {
    "mp3": "audio/mp3",
    "m4a": "audio/m4a",
    "mp4": "audio/mp4",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "aiff": "audio/aiff",
    "flac": "audio/flac",
}


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def _generate(client: genai.Client, audio_path: Path, mime_type: str):
    audio_content = {"type": "audio", "data": audio_path, "mime_type": mime_type}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return client.interactions.create(
            model="gemini-3.5-transcribe",
            input=[audio_content],
            system_instruction=_SYSTEM_INSTRUCTION,
        )


def _sync_transcribe(audio_path: Path) -> str:
    client = _get_client()

    ext = audio_path.suffix.lower().lstrip(".")
    mime_type = _MIME_MAP.get(ext, "audio/mpeg")
    audio_size_mb = audio_path.stat().st_size / (1024 * 1024)

    best_text = ""
    best_fraction = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = _generate(client, audio_path, mime_type)

        usage = response.usage
        text = response.output_text or ""

        logger.info(
            "Transcription attempt %s/%s of %s (%.1f MB): "
            "input_tokens=%s output_tokens=%s total_tokens=%s text_len=%s",
            attempt,
            MAX_ATTEMPTS,
            audio_path.name,
            audio_size_mb,
            getattr(usage, "total_input_tokens", None),
            getattr(usage, "total_output_tokens", None),
            getattr(usage, "total_tokens", None),
            len(text),
        )

        report = analyze_repetition(text)
        if report is None:
            return text

        logger.warning(
            "Repetition detected on attempt %s/%s for %s: %.0f%% of the text repeats, "
            "top block repeats %s times. Sample: %r",
            attempt,
            MAX_ATTEMPTS,
            audio_path.name,
            report.fraction * 100,
            report.top_count,
            report.sample,
        )
        if best_fraction is None or report.fraction < best_fraction:
            best_text, best_fraction = text, report.fraction

    logger.warning(
        "All %s attempts for %s showed repetition; returning the least-repetitive one (%.0f%%).",
        MAX_ATTEMPTS,
        audio_path.name,
        best_fraction * 100,
    )
    return best_text


async def run_transcription(audio_path: Path) -> str:
    return await asyncio.to_thread(_sync_transcribe, audio_path)
