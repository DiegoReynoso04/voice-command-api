from fastapi import APIRouter

from src.app.schemas.voice import InstructionPayload, InstructionRequest
from src.app.services.instruction_service import interpret_instruction

router = APIRouter(tags=["instruction"])


@router.post("/instruction", response_model=InstructionPayload)
def route_instruction(
    payload: InstructionRequest,
) -> InstructionPayload:
    return interpret_instruction(payload.transcription)
