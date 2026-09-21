import json

from fastapi import HTTPException, status
from groq import APIConnectionError, APIStatusError
from pydantic import ValidationError

from src.app.core.config import get_settings
from src.app.schemas.voice import InstructionPayload
from src.app.services.groq_client import get_groq_client

SYSTEM_PROMPT = """\
You translate a spoken instruction (usually in Spanish, sometimes English) into \
a single call to a task-management REST API.

Available operations:
- Create a task:            POST   /tasks          params: {"title": str, "done": bool (optional, default false)}
- List all tasks:           GET    /tasks          params: {}
- Replace a task entirely:  PUT    /tasks/{id}     params: {"title": str, "done": bool}
- Partially update a task:  PATCH  /tasks/{id}     params: only the fields to change ("title" and/or "done")
- Delete a task:            DELETE /tasks/{id}     params: {}

Rules:
- Reply with ONLY a JSON object, no markdown, no explanations.
- Shape: {"endpoint": string, "method": string, "params": object}
- The endpoint must contain the concrete numeric id, e.g. "/tasks/3", never a placeholder.
- "Mark task N as done/completed" -> PATCH /tasks/N with {"done": true}; "as pending/not done" -> {"done": false}.
- "Change/rename the title of task N to X" -> PATCH /tasks/N with {"title": "X"}.
- Use PUT only when the user clearly wants to replace the whole task; if "done" is not mentioned, use false.
- Keep the title text exactly as the user said it, without the surrounding command words.
- If the instruction cannot be mapped to one of these operations, reply with {"error": "<short reason>"}.
"""


def interpret_instruction(transcription: str) -> InstructionPayload:
    """Ask the configured Groq model to turn a transcription into an API call."""
    settings = get_settings()
    try:
        client = get_groq_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq client is not configured.",
        ) from exc

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcription},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=512,
            reasoning_effort="low",
        )
    except APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq request failed with status {exc.status_code}.",
        ) from exc
    except APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to Groq.",
        ) from exc

    content = completion.choices[0].message.content or ""
    return parse_instruction(content)


def parse_instruction(content: str) -> InstructionPayload:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq returned a response that is not valid JSON.",
        ) from exc

    if isinstance(data, dict) and "error" in data and "endpoint" not in data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not interpret the instruction: {data['error']}",
        )

    try:
        return InstructionPayload.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq returned an instruction that does not match the expected schema.",
        ) from exc
