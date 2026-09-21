"""In-memory task storage.

Tasks live only in this process; nothing is persisted. Each task is a dict:

    {"id": 1, "title": "Comprar leche", "done": False}
"""

from typing import Any

tasks: list[dict[str, Any]] = []
