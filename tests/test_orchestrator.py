from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from backend.munder import db, agents, orchestrator
from backend.munder.events import EventCollector
from backend.munder.schemas import RunResult

DATA_DIR = str(Path(__file__).resolve().parent.parent / "backend" / "munder" / "data")


@pytest.fixture()
def built(tmp_path):
    db.configure(str(tmp_path / "orch.db"))
    db.init_database(data_dir=DATA_DIR, seed=137)
    return agents.build_agents(model=TestModel())


@pytest.mark.asyncio
async def test_run_request_returns_runresult_and_reply(built):
    collector = EventCollector()
    result = await orchestrator.run_request(
        request_text="I need 100 reams of A4 paper.",
        request_date="2025-03-15",
        built=built,
        model=TestModel(),
        emit=collector,
    )
    assert isinstance(result, RunResult)
    assert result.request_date == "2025-03-15"
    assert result.reply.text
    # events were emitted, including agent lifecycle
    kinds = {e.kind for e in collector.events}
    assert "agent_started" in kinds
    assert "run_complete" in kinds
