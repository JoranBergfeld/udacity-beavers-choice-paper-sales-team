from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter

from backend.munder import db
from backend.api import session
from backend.api.util import json_safe

router = APIRouter()


@router.get("/financials")
def financials(as_of: Optional[str] = None):
    session.use_live()
    as_of = as_of or datetime.now().strftime("%Y-%m-%d")
    return json_safe(db.generate_financial_report(as_of))
