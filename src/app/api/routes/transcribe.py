from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from src.app.schemas.voice import InstructionRequest, TranscribeFlowResponse
from src.app.services.instruction_service import interpret_instruction
from src.app.services.task_executor import execute_instruction
from src.app.services.transcription_service import transcribe_audio
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    """Full voice flow: audio (or manual text) -> transcription -> instruction -> /tasks."""
    transcription = await read_transcription(request)
    try:
        instruction = await run_in_threadpool(interpret_instruction, transcription)
        result = execute_instruction(instruction)
    except HTTPException as exc:
        raise with_transcription(exc, transcription) from exc
    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )


def with_transcription(exc: HTTPException, transcription: str) -> HTTPException:
    """Re-raise a routing/execution error keeping the transcription the backend heard."""
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": exc.detail}
    return HTTPException(
        status_code=exc.status_code,
        detail={**detail, "transcription": transcription},
        headers=exc.headers,
    )


async def read_transcription(request: Request) -> str:
    """Accept the two shapes the frontend sends: multipart audio or JSON text."""
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing audio file in field 'file'.",
            )
        language = normalize_transcription_language(form.get("language"))
        audio = await upload.read()
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded audio file is empty.",
            )
        filename = upload.filename or "command.webm"
        return await run_in_threadpool(transcribe_audio, audio, filename, language)

    if content_type.startswith("application/json"):
        try:
            body = InstructionRequest.model_validate(await request.json())
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Expected a JSON body with a non-empty 'transcription'.",
            ) from exc
        return body.transcription.strip()

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Send multipart/form-data with an audio 'file' or JSON with 'transcription'.",
    )
