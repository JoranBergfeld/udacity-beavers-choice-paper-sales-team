from pathlib import Path

import pandas as pd
import pytest
from pydantic_ai.models.test import TestModel

from backend.munder import db, cli

DATA_DIR = str(Path(__file__).resolve().parent.parent / "backend" / "munder" / "data")


def test_make_run_fn_builds_callable():
    run_fn = cli.make_run_fn(model=TestModel())
    assert callable(run_fn)


def test_cli_main_writes_results(tmp_path, monkeypatch):
    db.configure(str(tmp_path / "cli.db"))
    monkeypatch.setenv("MUNDER_DB_PATH", str(tmp_path / "cli.db"))
    code = cli.main([
        "--sample", f"{DATA_DIR}/quote_requests_sample.csv",
        "--data-dir", DATA_DIR,
        "--out", str(tmp_path),
        "--no-judge",
        "--limit", "5",
        "--test-model",
    ])
    assert code == 0
    assert (tmp_path / "test_results.csv").exists()
    df = pd.read_csv(tmp_path / "test_results.csv")
    assert len(df) == 5
