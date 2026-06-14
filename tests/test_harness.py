import json
from pathlib import Path

import pandas as pd
import pytest

from backend.munder import db
from backend.munder.eval import harness
from backend.munder.events import EventCollector, RunEvent
from backend.munder.schemas import (
    RunResult, CustomerReply, Quote, QuoteLine, SaleResult, DelegationPlan,
)

DATA_DIR = str(Path(__file__).resolve().parent.parent / "backend" / "munder" / "data")


def _fake_run_factory():
    """Returns a run_fn that fulfills odd request ids and declines even ones,
    recording a real sale so cash changes, and emitting all 7 helper events."""
    async def run_fn(request_text, request_date, emit):
        rid = run_fn.counter = getattr(run_fn, "counter", 0) + 1
        for helper in ("get_all_inventory", "get_stock_level",
                       "get_supplier_delivery_date", "get_cash_balance",
                       "generate_financial_report", "search_quote_history"):
            emit(RunEvent(kind="tool_call", helper=helper))
        fulfilled = rid % 2 == 1
        if fulfilled:
            # record a real sale so cash balance moves
            db.create_transaction("A4 paper", "sales", 1, 5.0, request_date)
            emit(RunEvent(kind="tool_call", helper="create_transaction"))
            sale = SaleResult(fulfilled=True, transaction_ids=[rid], total_charged=5.0)
            reply = CustomerReply(text="Fulfilled with a 10% bulk discount.",
                                  fulfilled=True)
        else:
            sale = SaleResult(fulfilled=False, decline_reason="insufficient stock")
            reply = CustomerReply(text="We cannot fulfill: insufficient stock.",
                                  fulfilled=False)
        quote = Quote(line_items=[QuoteLine(item_name="A4 paper", qty=500,
                      unit_price=0.05, line_total=25.0)], subtotal=25.0,
                      discount_pct=0.10, discount_amount=2.5, total=22.5,
                      rationale="bulk")
        return RunResult(request_date=request_date,
                         delegation=DelegationPlan(needs_inventory=True,
                            needs_quote=True, needs_sale=fulfilled, reasoning="r"),
                         quote=quote, sale=sale, reply=reply)
    return run_fn


@pytest.fixture()
def env(tmp_path):
    db.configure(str(tmp_path / "harness.db"))
    return tmp_path


def test_harness_writes_results_and_meets_rubric(env, tmp_path):
    report = harness.run_eval(
        sample_csv=f"{DATA_DIR}/quote_requests_sample.csv",
        data_dir=DATA_DIR,
        run_fn=_fake_run_factory(),
        out_dir=str(tmp_path),
        judge=None,            # Layer 2 off for the fast test
        limit=10,
    )
    csv_path = Path(tmp_path) / "test_results.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert list(df.columns) == ["request_id", "request_date",
                                "cash_balance", "inventory_value", "response"]
    assert len(df) == 10
    # rubric thresholds
    assert report["rubric"]["fulfilled_count"] >= 3
    assert report["rubric"]["declined_count"] >= 1
    assert report["rubric"]["cash_change_count"] >= 3
    assert set(report["rubric"]["helpers_used"]) >= {
        "create_transaction", "get_all_inventory", "get_stock_level",
        "get_supplier_delivery_date", "get_cash_balance",
        "generate_financial_report", "search_quote_history"}
    assert report["rubric"]["all_helpers_used"] is True
    # eval report json present
    assert (Path(tmp_path) / "eval_report.json").exists()
