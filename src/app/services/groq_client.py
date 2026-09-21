from functools import lru_cache

from groq import Groq

from src.app.core.config import get_settings


@lru_cache
def get_groq_client() -> Groq:
    """Build the Groq SDK client from GROQ_API_KEY.

    The client is created lazily on first use, never at application startup,
    and creating it does not perform any request against the Groq API.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file (see .env.example)."
        )
    return Groq(
        api_key=settings.groq_api_key,
        timeout=settings.request_timeout_seconds,
    )
