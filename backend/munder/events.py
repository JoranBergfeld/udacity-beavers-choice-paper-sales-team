from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

EventKind = str  # "agent_started" | "agent_message" | "tool_call" | "tool_result"
#               | "handoff" | "financials_update" | "final_quote" | "run_complete" | "error"


class RunEvent(BaseModel):
    kind: EventKind
    agent: Optional[str] = None
    message: Optional[str] = None
    tool: Optional[str] = None
    helper: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=lambda: datetime.now().isoformat())


class EventCollector:
    """Callable sink that records events; used by the orchestrator and tests."""

    def __init__(self) -> None:
        self.events: List[RunEvent] = []

    def __call__(self, event: RunEvent) -> None:
        self.events.append(event)

    def helpers_used(self) -> Set[str]:
        return {e.helper for e in self.events if e.helper}
