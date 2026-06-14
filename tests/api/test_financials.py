def test_financials_report(client):
    client.post("/api/seed", json={"reset": True})
    body = client.get("/api/financials").json()
    for k in (
        "cash_balance",
        "inventory_value",
        "total_assets",
        "inventory_summary",
        "top_selling_products",
    ):
        assert k in body


def test_financials_serializes_with_real_sales(client):
    """A real sale mixed with the NULL opening-balance row makes top_selling_products
    a float column containing NaN; the endpoint must still serialize (NaN -> null)."""
    client.post("/api/seed", json={"reset": True})
    from backend.api import session
    from backend.munder import db

    session.use_live()
    db.create_transaction("A4 paper", "sales", 100, 25.0, "2025-04-01")

    r = client.get("/api/financials")
    assert r.status_code == 200
    assert "top_selling_products" in r.json()
