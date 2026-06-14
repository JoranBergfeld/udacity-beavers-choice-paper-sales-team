import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolated DB files per test, and NO provider key for any provider -> demo mode
    # (TestModel, no network). Neutralize every provider key so a developer's real
    # .env (e.g. Azure) can never make the suite hit a live endpoint.
    monkeypatch.setenv("MUNDER_LIVE_DB", str(tmp_path / "live.db"))
    monkeypatch.setenv("MUNDER_EVAL_DB", str(tmp_path / "eval.db"))
    monkeypatch.delenv("UDACITY_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    app = create_app()
    return TestClient(app)
