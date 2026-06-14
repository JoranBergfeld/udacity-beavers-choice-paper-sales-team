import pytest


@pytest.fixture(autouse=True)
def _seed(client):
    client.post("/api/seed", json={"reset": True})


def test_catalog_lists_items_with_stock(client):
    items = client.get("/api/catalog").json()["items"]
    assert len(items) >= 1
    assert {"item_name", "category", "unit_price", "stock"} <= set(items[0])


def test_policies_roundtrip(client):
    p = client.get("/api/policies").json()
    assert "discount_tiers" in p and "cash_floor" in p
    p["cash_floor"] = 1234.0
    assert client.put("/api/policies", json=p).status_code == 200
    assert client.get("/api/policies").json()["cash_floor"] == 1234.0


def test_quotes_history(client):
    assert isinstance(client.get("/api/quotes").json()["quotes"], list)


def test_restock_increases_stock(client):
    item = client.get("/api/catalog").json()["items"][0]
    before = item["stock"]
    r = client.post(
        "/api/restock", json={"item_name": item["item_name"], "quantity": 50}
    )
    assert r.status_code == 200
    after = next(
        i
        for i in client.get("/api/catalog").json()["items"]
        if i["item_name"] == item["item_name"]
    )["stock"]
    assert after == before + 50
