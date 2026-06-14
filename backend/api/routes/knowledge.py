from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter

from backend.munder import db
from backend.munder.catalog import paper_supplies
from backend.munder.policies import load_policy
from backend.api import session
from backend.api.models import PolicyDTO, RestockRequest
from backend.api.util import json_safe

router = APIRouter()


def _policy_path() -> str:
    return str(Path(session.live_db_path()).with_name("policies.json"))


@router.get("/catalog")
def catalog():
    session.use_live()
    today = datetime.now().strftime("%Y-%m-%d")
    stock = db.get_all_inventory(today)
    items = [
        {**item, "stock": int(stock.get(item["item_name"], 0))}
        for item in paper_supplies
    ]
    return {"items": items}


@router.get("/policies")
def get_policies():
    p = load_policy(_policy_path())
    return {
        "discount_tiers": [vars(t) for t in p.discount_tiers],
        "cash_floor": p.cash_floor,
    }


@router.put("/policies")
def put_policies(p: PolicyDTO):
    Path(_policy_path()).write_text(json.dumps(p.model_dump()))
    return {"ok": True}


@router.get("/quotes")
def quotes():
    session.use_live()
    try:
        df = pd.read_sql(
            "SELECT * FROM quotes ORDER BY order_date DESC LIMIT 50", db.db_engine
        )
        return {"quotes": json_safe(df.to_dict(orient="records"))}
    except Exception:
        return {"quotes": []}


@router.post("/restock")
def restock(req: RestockRequest):
    session.use_live()
    unit = next(
        (i["unit_price"] for i in paper_supplies if i["item_name"] == req.item_name),
        0.0,
    )
    today = datetime.now().strftime("%Y-%m-%d")
    db.create_transaction(
        req.item_name, "stock_orders", req.quantity, req.quantity * unit, today
    )
    return {"ok": True}
