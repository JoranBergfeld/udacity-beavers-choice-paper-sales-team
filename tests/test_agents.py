from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from backend.munder import db, agents, tools
from backend.munder.events import EventCollector
from backend.munder.schemas import InventoryAssessment

DATA_DIR = str(Path(__file__).resolve().parent.parent / "backend" / "munder" / "data")


@pytest.fixture()
def built(tmp_path):
    db.configure(str(tmp_path / "agents.db"))
    db.init_database(data_dir=DATA_DIR, seed=137)
    return agents.build_agents(model=TestModel())


def test_build_agents_returns_all_five(built):
    for key in ("michael", "dwight", "jim", "stanley", "david"):
        assert key in built


@pytest.mark.asyncio
async def test_dwight_runs_with_testmodel_and_calls_tools(built):
    collector = EventCollector()
    deps = tools.Deps(as_of_date="2025-03-01", emit=collector)
    result = await built["dwight"].run("Check stock for A4 paper", deps=deps)
    assert isinstance(result.output, InventoryAssessment)
    # TestModel exercises the agent's registered tools -> helper events recorded
    assert "get_all_inventory" in collector.helpers_used() or \
           "get_stock_level" in collector.helpers_used()
