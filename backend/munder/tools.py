from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from backend.munder import db, decisions
from backend.munder.catalog import canonical_item_name
from backend.munder.events import RunEvent
from backend.munder.policies import BusinessPolicy
from backend.munder.schemas import ParsedOrder


@dataclass
class Deps:
    """Per-request dependencies injected into every tool call."""
    as_of_date: str
    emit: Callable[[RunEvent], None]
    order: Optional[ParsedOrder] = None


def _emit(ctx, tool: str, helper: str, data: Dict[str, Any]) -> None:
    ctx.deps.emit(RunEvent(kind="tool_call", tool=tool, helper=helper, data=data))


def check_all_inventory(ctx) -> Dict[str, int]:
    """Snapshot of all in-stock items as of the request date."""
    _emit(ctx, "check_all_inventory", "get_all_inventory", {})
    return db.get_all_inventory(ctx.deps.as_of_date)


def check_stock(ctx, item_name: str) -> int:
    """Net stock for a single item as of the request date."""
    item_name = canonical_item_name(item_name)
    _emit(ctx, "check_stock", "get_stock_level", {"item_name": item_name})
    row = db.get_stock_level(item_name, ctx.deps.as_of_date)
    return int(row["current_stock"].iloc[0])


def delivery_estimate(ctx, quantity: int) -> str:
    """Supplier delivery date for a quantity, based on the request date."""
    _emit(ctx, "delivery_estimate", "get_supplier_delivery_date",
          {"quantity": quantity})
    return db.get_supplier_delivery_date(ctx.deps.as_of_date, quantity)


def restock_item(ctx, item_name: str, quantity: int, unit_price: float) -> int:
    """Place a stock order (reorder) for an item; returns the transaction id."""
    item_name = canonical_item_name(item_name)
    _emit(ctx, "restock_item", "create_transaction",
          {"item_name": item_name, "quantity": quantity, "type": "stock_orders"})
    return db.create_transaction(item_name, "stock_orders", quantity,
                                 quantity * unit_price, ctx.deps.as_of_date)


def record_sale(ctx, item_name: str, quantity: int, total_price: float) -> int:
    """Record a sale for an item; returns the transaction id."""
    item_name = canonical_item_name(item_name)
    _emit(ctx, "record_sale", "create_transaction",
          {"item_name": item_name, "quantity": quantity, "type": "sales"})
    return db.create_transaction(item_name, "sales", quantity, total_price,
                                 ctx.deps.as_of_date)


def cash_balance(ctx) -> float:
    """Current cash balance as of the request date."""
    _emit(ctx, "cash_balance", "get_cash_balance", {})
    return db.get_cash_balance(ctx.deps.as_of_date)


def financial_report(ctx) -> Dict[str, Any]:
    """Full financial report as of the request date."""
    _emit(ctx, "financial_report", "generate_financial_report", {})
    return db.generate_financial_report(ctx.deps.as_of_date)


def search_quotes(ctx, search_terms: List[str]) -> List[Dict[str, Any]]:
    """Search historical quotes for pricing precedent."""
    _emit(ctx, "search_quotes", "search_quote_history", {"terms": search_terms})
    return db.search_quote_history(search_terms, limit=5)


# --- Deterministic decision tools (operate on the shared, parsed order in deps) ---

def order_inventory(ctx) -> Dict[str, Any]:
    """Authoritative availability for the whole parsed order: per-line stock, whether
    it's sufficient, reorder recommendation, and delivery date. Computed from the DB."""
    ctx.deps.emit(RunEvent(kind="tool_call", tool="order_inventory"))
    order = ctx.deps.order or ParsedOrder()
    return decisions.assess_inventory(order, ctx.deps.as_of_date).model_dump()


def order_quote(ctx) -> Dict[str, Any]:
    """Authoritative quote for the parsed order: catalog pricing + the bulk-discount tier
    for the total quantity. Use this for the numbers; add your own rationale."""
    ctx.deps.emit(RunEvent(kind="tool_call", tool="order_quote"))
    order = ctx.deps.order or ParsedOrder()
    return decisions.price_order(order, BusinessPolicy()).model_dump()


def order_fulfillment(ctx) -> Dict[str, Any]:
    """Authoritative fulfill-or-decline decision for the parsed order, based on stock and
    delivery feasibility against any requested deadline."""
    ctx.deps.emit(RunEvent(kind="tool_call", tool="order_fulfillment"))
    order = ctx.deps.order or ParsedOrder()
    inv = decisions.assess_inventory(order, ctx.deps.as_of_date)
    quote = decisions.price_order(order, BusinessPolicy())
    return decisions.decide_fulfillment(
        order, inv, quote, ctx.deps.as_of_date
    ).model_dump()
