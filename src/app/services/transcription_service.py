from typing import Any

from fastapi import HTTPException, status
from groq import APIConnectionError, APIStatusError

from src.app.core.config import get_settings
from src.app.services.groq_client import get_groq_client


def transcribe_audio(audio: bytes, filename: str, language: str | None) -> str:
    """Transcribe recorded audio with the configured Groq Whisper model."""
    settings = get_settings()
    try:
        client = get_groq_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq client is not configured.",
        ) from exc

    options: dict[str, Any] = {
        "file": (filename, audio),
        "model": settings.groq_transcription_model,
        "response_format": "json",
        "temperature": 0,
    }
    if language:
        options["language"] = language

    try:
        result = client.audio.transcriptions.create(**options)
    except APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq transcription failed with status {exc.status_code}.",
        ) from exc
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to Groq.",
        ) from exc

    transcription = (result.text or "").strip()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No speech was detected in the audio.",
        )
    return transcription
