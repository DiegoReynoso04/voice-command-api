import re
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from src.app.api.routes import tasks as task_routes
from src.app.schemas.voice import InstructionPayload, TaskCreate, TaskReplace, TaskUpdate

_TASK_ID_ENDPOINT = re.compile(r"^/tasks/(\d+)$")


def execute_instruction(instruction: InstructionPayload) -> Any:
    """Run the /tasks operation described by an /instruction payload.

    The decision of what to do comes exclusively from the structured
    ``method`` and ``endpoint`` returned by the model; the existing /tasks
    handlers are reused so the CRUD logic lives in one place.
    """
    match = _TASK_ID_ENDPOINT.fullmatch(instruction.endpoint)
    task_id = int(match.group(1)) if match else None
    method, params = instruction.method, instruction.params

    try:
        if method == "GET" and task_id is None:
            return task_routes.get_tasks()
        if method == "POST" and task_id is None:
            return task_routes.create_task(TaskCreate.model_validate(params))
        if method == "PUT" and task_id is not None:
            return task_routes.replace_task(task_id, TaskReplace.model_validate(params))
        if method == "PATCH" and task_id is not None:
            return task_routes.update_task(task_id, TaskUpdate.model_validate(params))
        if method == "DELETE" and task_id is not None:
            return task_routes.delete_task(task_id)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Invalid params for {method} {instruction.endpoint}.",
                "errors": exc.errors(include_url=False),
            },
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported instruction: {method} {instruction.endpoint}.",
    )
