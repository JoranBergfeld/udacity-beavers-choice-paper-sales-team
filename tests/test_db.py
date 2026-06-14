import os
from datetime import datetime
from pathlib import Path

import pytest

from backend.munder import db

DATA_DIR = str(Path(__file__).resolve().parent.parent / "backend" / "munder" / "data")


@pytest.fixture()
def fresh_db(tmp_path):
    db.configure(str(tmp_path / "test.db"))
    db.init_database(data_dir=DATA_DIR, seed=137)
    return db


def test_initial_cash_balance_is_50k(fresh_db):
    report = fresh_db.generate_financial_report("2025-01-02")
    # 50k seed sale minus the cost of initial stock orders
    expected_cash = 50000.0 - sum(
        i["value"] for i in report["inventory_summary"]
    )
    assert fresh_db.get_cash_balance("2025-01-02") == pytest.approx(expected_cash, abs=1.0)


def test_inventory_and_stock_level_are_consistent(fresh_db):
    inv = fresh_db.get_all_inventory("2025-01-02")
    assert len(inv) > 0
    item = next(iter(inv))
    row = fresh_db.get_stock_level(item, "2025-01-02")
    assert int(row["current_stock"].iloc[0]) == inv[item]


def test_create_transaction_changes_stock_and_cash(fresh_db):
    inv = fresh_db.get_all_inventory("2025-01-05")
    item = next(iter(inv))
    before = inv[item]
    cash_before = fresh_db.get_cash_balance("2025-01-05")
    fresh_db.create_transaction(item, "sales", 10, 5.0, "2025-01-05")
    after = fresh_db.get_all_inventory("2025-01-05")[item]
    assert after == before - 10
    assert fresh_db.get_cash_balance("2025-01-05") == pytest.approx(cash_before + 5.0)


def test_supplier_delivery_date_scales_with_quantity(fresh_db):
    assert fresh_db.get_supplier_delivery_date("2025-01-01", 5) == "2025-01-01"
    assert fresh_db.get_supplier_delivery_date("2025-01-01", 50) == "2025-01-02"
    assert fresh_db.get_supplier_delivery_date("2025-01-01", 500) == "2025-01-05"
    assert fresh_db.get_supplier_delivery_date("2025-01-01", 5000) == "2025-01-08"


def test_search_quote_history_returns_rows(fresh_db):
    results = fresh_db.search_quote_history(["paper"], limit=3)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert "total_amount" in results[0]


def test_financial_report_has_expected_keys(fresh_db):
    report = fresh_db.generate_financial_report("2025-01-10")
    for key in ("cash_balance", "inventory_value", "total_assets",
                "inventory_summary", "top_selling_products"):
        assert key in report
