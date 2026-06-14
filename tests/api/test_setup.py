def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_config_reports_demo_mode_when_no_key(client):
    body = client.get("/api/config").json()
    assert body["api_key_set"] is False
    assert body["demo_mode"] is True
    assert "model" in body and "base_url" in body


def test_put_config_updates_model(client):
    r = client.put("/api/config", json={"model": "gpt-4.1", "base_url": "https://x/v1"})
    assert r.status_code == 200
    assert client.get("/api/config").json()["model"] == "gpt-4.1"


def test_status_reports_db_seeded_after_seed(client):
    assert client.get("/api/status").json()["db_seeded"] in (True, False)
    client.post("/api/seed", json={"reset": True})
    assert client.get("/api/status").json()["db_seeded"] is True


def test_test_connection_demo_mode(client):
    body = client.post("/api/test-connection").json()
    assert body["ok"] is True
    assert body["demo_mode"] is True
