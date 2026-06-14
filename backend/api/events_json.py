from __future__ import annotations

from backend.munder.events import RunEvent
from backend.munder.schemas import RunResult


def event_to_json(e: RunEvent) -> dict:
    return {"type": "event", "event": e.model_dump()}


def result_to_json(r: RunResult) -> dict:
    return {"type": "result", "result": r.model_dump()}
