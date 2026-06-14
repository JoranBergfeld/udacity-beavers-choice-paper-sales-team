from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class OrderLine(BaseModel):
    item_name: str
    qty: int


class ParsedOrder(BaseModel):
    """The customer's request parsed once into structured form, shared by all workers
    so they never disagree on items/quantities/dates."""
    lines: List[OrderLine] = Field(default_factory=list)
    requested_delivery_date: Optional[str] = Field(
        default=None, description="Requested delivery date as YYYY-MM-DD, or null if none."
    )


class DelegationPlan(BaseModel):
    needs_inventory: bool
    needs_quote: bool
    needs_sale: bool
    reasoning: str


class Intake(BaseModel):
    """Michael's intake output: the parsed order plus which workers to involve."""
    order: ParsedOrder
    needs_inventory: bool
    needs_quote: bool
    needs_sale: bool
    reasoning: str


class InventoryLine(BaseModel):
    item_name: str
    requested: int
    available: int
    sufficient: bool
    reorder_recommended: bool
    reorder_qty: int = 0
    delivery_date: Optional[str] = None


class InventoryAssessment(BaseModel):
    lines: List[InventoryLine] = Field(default_factory=list)
    all_available: bool


class QuoteLine(BaseModel):
    item_name: str
    qty: int
    unit_price: float
    line_total: float


class Quote(BaseModel):
    line_items: List[QuoteLine] = Field(default_factory=list)
    subtotal: float
    discount_pct: float = Field(
        description="Discount as a FRACTION between 0 and 1 (e.g. 0.10 means 10%), "
        "NOT a whole-number percentage."
    )
    discount_amount: float
    total: float
    rationale: str


class SaleResult(BaseModel):
    fulfilled: bool
    transaction_ids: List[int] = Field(default_factory=list)
    total_charged: float = 0.0
    delivery_date: Optional[str] = None
    decline_reason: Optional[str] = None


class AdvisorNote(BaseModel):
    observations: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CustomerReply(BaseModel):
    text: str
    fulfilled: bool


class RunResult(BaseModel):
    request_id: Optional[int] = None
    request_date: str
    order: Optional[ParsedOrder] = None
    delegation: Optional[DelegationPlan] = None
    inventory: Optional[InventoryAssessment] = None
    quote: Optional[Quote] = None
    sale: Optional[SaleResult] = None
    advisor: Optional[AdvisorNote] = None
    reply: CustomerReply
