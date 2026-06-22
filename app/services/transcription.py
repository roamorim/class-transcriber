import asyncio
import logging
import time
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings
from app.services.repetition import analyze_repetition

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

MAX_ATTEMPTS = 3


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


def _generate(client: genai.Client, audio_bytes: bytes, mime_type: str) -> types.GenerateContentResponse:
    return client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            (
                "Transcribe el audio completo de esta clase de forma literal y precisa. "
                "Incluye todo lo que se dice, respetando el idioma original. "
                "No agregues comentarios, resúmenes ni anotaciones. "
                "Solo entrega el texto transcrito."
            ),
        ],
        config=types.GenerateContentConfig(
            # On long audio Gemini sometimes gets stuck repeating the same
            # phrase until it hits the output limit. frequency_penalty /
            # presence_penalty would be the direct fix but this model rejects
            # them ("Penalty is not enabled for models/gemini-2.5-flash"), so
            # max_output_tokens just caps the damage, and _sync_transcribe
            # retries below when repetition is detected -- output is
            # non-deterministic call to call on the same audio.
            max_output_tokens=32768,
        ),
    )


def _sync_transcribe(audio_path: Path) -> str:
    client = _get_client()

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    # Determine MIME type from extension
    ext = audio_path.suffix.lower().lstrip(".")
    mime_map = {
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "mp4": "audio/mp4",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "aiff": "audio/aiff",
        "flac": "audio/flac",
    }
    mime_type = mime_map.get(ext, "audio/mpeg")
    audio_size_mb = len(audio_bytes) / (1024 * 1024)

    best_text = ""
    best_fraction = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = _generate(client, audio_bytes, mime_type)

        finish_reason = None
        if response.candidates:
            finish_reason = response.candidates[0].finish_reason
        usage = response.usage_metadata
        text = response.text or ""

        log_fn = logger.info if finish_reason in (None, "STOP") else logger.warning
        log_fn(
            "Transcription attempt %s/%s of %s (%.1f MB): finish_reason=%s "
            "prompt_tokens=%s response_tokens=%s total_tokens=%s text_len=%s",
            attempt,
            MAX_ATTEMPTS,
            audio_path.name,
            audio_size_mb,
            finish_reason,
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
            getattr(usage, "total_token_count", None),
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
