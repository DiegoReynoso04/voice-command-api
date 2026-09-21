"""In-memory task storage.

Tasks live only in this process; nothing is persisted. Each task is a dict:

    {"id": 1, "title": "Comprar leche", "done": False}
"""

from itertools import count
from typing import Any

tasks: list[dict[str, Any]] = []

# Ids are strictly incremental and never reused after a delete. The counter
# resets together with `tasks` when the server restarts.
_task_ids = count(1)


def next_task_id() -> int:
    return next(_task_ids)
