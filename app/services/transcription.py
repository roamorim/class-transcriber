import asyncio
import time
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.google_api_key)
    return _client


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

    response = client.models.generate_content(
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
    )

    return response.text


async def run_transcription(audio_path: Path) -> str:
    return await asyncio.to_thread(_sync_transcribe, audio_path)
