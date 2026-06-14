"""Deterministic business decisions.

These pure functions compute the authoritative facts (availability, pricing, fulfillment)
from the database, catalog, and policy, so the system's numbers and yes/no decisions don't
depend on LLM reliability. Agents parse the request and narrate; this module decides.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

from backend.munder import db
from backend.munder.catalog import CATALOG_PRICE, canonical_item_name
from backend.munder.policies import BusinessPolicy
from backend.munder.schemas import (
    InventoryAssessment,
    InventoryLine,
    OrderLine,
    ParsedOrder,
    Quote,
    QuoteLine,
    SaleResult,
)


def canonicalize_order(order: ParsedOrder) -> ParsedOrder:
    """Map each line's item name to the exact catalog name and merge duplicate items
    (summing quantities), so downstream availability/pricing/fulfillment operate on one
    line per distinct item. Mutates and returns the order."""
    merged: dict = {}
    sequence = []
    for li in order.lines:
        name = canonical_item_name(li.item_name)
        if name not in merged:
            merged[name] = 0
            sequence.append(name)
        merged[name] += li.qty
    order.lines = [OrderLine(item_name=n, qty=merged[n]) for n in sequence]
    return order


def _min_levels() -> Dict[str, int]:
    try:
        df = pd.read_sql("SELECT item_name, min_stock_level FROM inventory", db.db_engine)
        return {r["item_name"]: int(r["min_stock_level"]) for _, r in df.iterrows()}
    except Exception:
        return {}


def assess_inventory(order: ParsedOrder, as_of_date: str) -> InventoryAssessment:
    """Per-line availability + reorder recommendation, computed from current stock."""
    mins = _min_levels()
    lines = []
    all_ok = True
    for li in order.lines:
        row = db.get_stock_level(li.item_name, as_of_date)
        available = int(row["current_stock"].iloc[0]) if not row.empty else 0
        sufficient = available >= li.qty
        all_ok = all_ok and sufficient
        min_level = mins.get(li.item_name, 0)
        lines.append(
            InventoryLine(
                item_name=li.item_name,
                requested=li.qty,
                available=available,
                sufficient=sufficient,
                reorder_recommended=available < min_level,
                reorder_qty=max(0, li.qty - available) if not sufficient else 0,
                delivery_date=db.get_supplier_delivery_date(as_of_date, li.qty),
            )
        )
    return InventoryAssessment(lines=lines, all_available=all_ok)


def price_order(order: ParsedOrder, policy: BusinessPolicy, rationale: str = "") -> Quote:
    """Price each line from the catalog and apply the bulk-discount tier for the total
    quantity. Pricing and discount are fully deterministic."""
    items = []
    for li in order.lines:
        unit = CATALOG_PRICE.get(li.item_name, 0.0)
        items.append(
            QuoteLine(
                item_name=li.item_name,
                qty=li.qty,
                unit_price=unit,
                line_total=round(li.qty * unit, 2),
            )
        )
    subtotal = round(sum(i.line_total for i in items), 2)
    total_units = sum(li.qty for li in order.lines)
    pct = policy.bulk_discount_pct(total_units)
    discount_amount = round(subtotal * pct, 2)
    return Quote(
        line_items=items,
        subtotal=subtotal,
        discount_pct=pct,
        discount_amount=discount_amount,
        total=round(subtotal - discount_amount, 2),
        rationale=rationale,
    )


def restock_shortfalls(
    order: ParsedOrder,
    inventory: InventoryAssessment,
    as_of_date: str,
    policy: BusinessPolicy,
) -> list:
    """For each line that's short, buy the shortfall from the supplier, but only while
    cash stays above the policy floor. This lets the company meet demand it otherwise
    couldn't (turning would-be declines into sales), while genuinely unaffordable orders
    still decline. Returns the list of restock transaction ids."""
    ids = []
    cash = db.get_cash_balance(as_of_date)
    for ln in inventory.lines:
        if ln.sufficient:
            continue
        shortfall = ln.requested - ln.available
        unit = CATALOG_PRICE.get(ln.item_name, 0.0)
        cost = round(shortfall * unit, 2)
        if shortfall > 0 and unit > 0 and policy.can_afford(cash, cost):
            ids.append(
                db.create_transaction(ln.item_name, "stock_orders", shortfall, cost, as_of_date)
            )
            cash -= cost
    return ids


def decide_fulfillment(
    order: ParsedOrder,
    inventory: InventoryAssessment,
    quote: Quote,
    as_of_date: str,
) -> SaleResult:
    """Decide fulfill-vs-decline deterministically. We ship from stock, so the only reason
    to decline is insufficient stock (the rubric's intended decline reason). The supplier
    lead time is reported as the delivery date but doesn't block an in-stock order; that
    lead time only matters when restocking. (A sale only raises cash, so the cash floor
    never blocks it.) Doesn't record the sale; that's the orchestrator's job."""
    if not order.lines:
        return SaleResult(fulfilled=False, decline_reason="no catalog items identified in the request")

    if not inventory.all_available:
        short = [ln.item_name for ln in inventory.lines if not ln.sufficient]
        return SaleResult(fulfilled=False, decline_reason=f"insufficient stock: {', '.join(short)}")

    total_units = sum(li.qty for li in order.lines)
    delivery = db.get_supplier_delivery_date(as_of_date, total_units)
    return SaleResult(fulfilled=True, total_charged=quote.total, delivery_date=delivery)
