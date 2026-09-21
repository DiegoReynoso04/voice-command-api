from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services.task_store import tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[dict[str, Any]]:
    return tasks


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> dict[str, Any]:
    task = {"id": next_task_id(), "title": payload.title, "done": payload.done}
    tasks.append(task)
    return task


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> dict[str, Any]:
    task = get_task_or_404(task_id)
    task["title"] = payload.title
    task["done"] = payload.done
    return task


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> dict[str, Any]:
    task = get_task_or_404(task_id)
    task.update(payload.model_dump(exclude_unset=True, exclude_none=True))
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    task = get_task_or_404(task_id)
    tasks.remove(task)
    return {"message": f"Task {task_id} deleted"}


def next_task_id() -> int:
    return max((t["id"] for t in tasks), default=0) + 1


def get_task_or_404(task_id: int) -> dict[str, Any]:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )
