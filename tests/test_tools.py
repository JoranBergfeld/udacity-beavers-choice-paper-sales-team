from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.munder import db, tools
from backend.munder.events import EventCollector

DATA_DIR = str(Path(__file__).resolve().parent.parent / "backend" / "munder" / "data")


class FakeCtx:
    """Stand-in for pydantic_ai RunContext: only `.deps` is used by tools."""
    def __init__(self, deps):
        self.deps = deps


@pytest.fixture()
def ctx(tmp_path):
    db.configure(str(tmp_path / "tools.db"))
    db.init_database(data_dir=DATA_DIR, seed=137)
    collector = EventCollector()
    deps = tools.Deps(as_of_date="2025-03-01", emit=collector)
    return FakeCtx(deps), collector


def test_check_all_inventory_uses_date_and_emits(ctx):
    c, collector = ctx
    inv = tools.check_all_inventory(c)
    assert isinstance(inv, dict) and len(inv) > 0
    assert "get_all_inventory" in collector.helpers_used()


def test_check_stock_returns_int(ctx):
    c, collector = ctx
    item = next(iter(tools.check_all_inventory(c)))
    level = tools.check_stock(c, item)
    assert isinstance(level, int) and level >= 0
    assert "get_stock_level" in collector.helpers_used()


def test_delivery_estimate(ctx):
    c, _ = ctx
    assert tools.delivery_estimate(c, 5) == "2025-03-01"
    assert tools.delivery_estimate(c, 500) == "2025-03-05"


def test_record_sale_changes_stock_and_emits(ctx):
    c, collector = ctx
    item = next(iter(tools.check_all_inventory(c)))
    before = tools.check_stock(c, item)
    tid = tools.record_sale(c, item, 5, 1.0)
    assert isinstance(tid, int)
    assert tools.check_stock(c, item) == before - 5
    assert "create_transaction" in collector.helpers_used()


def test_restock_item_increases_stock(ctx):
    c, _ = ctx
    item = next(iter(tools.check_all_inventory(c)))
    before = tools.check_stock(c, item)
    tools.restock_item(c, item, 100, 0.05)
    assert tools.check_stock(c, item) == before + 100


def test_cash_balance_and_financial_report(ctx):
    c, collector = ctx
    assert isinstance(tools.cash_balance(c), float)
    report = tools.financial_report(c)
    assert "cash_balance" in report
    assert {"get_cash_balance", "generate_financial_report"} <= collector.helpers_used()


def test_search_quotes_emits(ctx):
    c, collector = ctx
    rows = tools.search_quotes(c, ["paper"])
    assert isinstance(rows, list)
    assert "search_quote_history" in collector.helpers_used()
