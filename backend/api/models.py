from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ConfigUpdate(BaseModel):
    model: Optional[str] = None
    base_url: Optional[str] = None


class SeedRequest(BaseModel):
    reset: bool = True


class PolicyDTO(BaseModel):
    discount_tiers: List[dict]
    cash_floor: float


class RestockRequest(BaseModel):
    item_name: str
    quantity: int


class ReceptionRequest(BaseModel):
    request_text: str
    request_date: str  # YYYY-MM-DD


class EvalRequest(BaseModel):
    limit: Optional[int] = None
    judge: bool = False
