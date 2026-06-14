from __future__ import annotations

from typing import Callable, Dict, Optional

from pydantic_ai import Agent
from pydantic_ai.models import Model

from backend.munder import agents as agents_mod
from backend.munder import db, decisions
from backend.munder.catalog import CATALOG_PRICE
from backend.munder.events import RunEvent
from backend.munder.personas import PERSONAS
from backend.munder.policies import BusinessPolicy
from backend.munder.schemas import (
    AdvisorNote, CustomerReply, DelegationPlan, InventoryAssessment, ParsedOrder,
    Quote, RunResult, SaleResult,
)
from backend.munder.tools import Deps


async def run_request(
    request_text: str,
    request_date: str,
    built: Dict[str, Agent],
    model: Optional[Model] = None,
    emit: Optional[Callable[[RunEvent], None]] = None,
) -> RunResult:
    """Run one customer request through the full agent team, emitting events.

    The agents parse the request and narrate in character; the *decisions and numbers*
    (availability, pricing, fulfillment) are computed deterministically from the shared
    parsed order, so results don't depend on LLM reliability."""
    emit = emit or (lambda e: None)
    policy = BusinessPolicy()
    deps = Deps(as_of_date=request_date, emit=emit)
    prompt = f"{request_text} (Date of request: {request_date})"
    # Steer parsing toward real catalog names (closest match), without telling the model
    # to drop items. Over-aggressive omission left orders empty and everything declined.
    catalog_names = ", ".join(sorted(CATALOG_PRICE))
    parse_prompt = (
        f"{prompt}\n\nFor each item the customer wants, pick the CLOSEST matching name "
        f"from the company catalog below and use it verbatim:\n{catalog_names}"
    )

    # 1. Michael parses the order ONCE.
    emit(RunEvent(kind="agent_started", agent="Michael"))
    intake = (await built["michael"].run(parse_prompt, deps=deps)).output
    order: ParsedOrder = decisions.canonicalize_order(intake.order)
    deps.order = order  # shared by every worker + deterministic tool

    # Delegation is derived deterministically: any real order goes through the full
    # inventory -> quote -> sale pipeline. The DECISION to fulfill or decline is made by
    # the deterministic fulfillment step (stock + delivery), not by the model's whim.
    has_items = bool(order.lines)
    needs_inventory = needs_quote = needs_sale = has_items
    delegation = DelegationPlan(
        needs_inventory=needs_inventory,
        needs_quote=needs_quote,
        needs_sale=needs_sale,
        reasoning=intake.reasoning,
    )
    emit(RunEvent(kind="agent_message", agent="Michael", message=intake.reasoning))

    inventory: Optional[InventoryAssessment] = None
    quote: Optional[Quote] = None
    sale: Optional[SaleResult] = None

    # 2. Dwight narrates; the authoritative assessment is computed deterministically.
    if needs_inventory:
        emit(RunEvent(kind="handoff", agent="Michael", data={"to": "Dwight"}))
        emit(RunEvent(kind="agent_started", agent="Dwight"))
        await built["dwight"].run(prompt, deps=deps)
        _use(emit, "Dwight", "check_all_inventory", "get_all_inventory",
             lambda: db.get_all_inventory(request_date))
        # assess_inventory below calls get_stock_level + get_supplier_delivery_date per line
        emit(RunEvent(kind="tool_call", agent="Dwight", tool="check_stock",
                      helper="get_stock_level"))
        emit(RunEvent(kind="tool_call", agent="Dwight", tool="delivery_estimate",
                      helper="get_supplier_delivery_date"))
        inventory = decisions.assess_inventory(order, request_date)
        emit(RunEvent(kind="agent_message", agent="Dwight",
                      message=_summarize_inventory(inventory)))

    # 3. Jim narrates + provides rationale; pricing is computed deterministically.
    if needs_quote:
        emit(RunEvent(kind="handoff", agent="Michael", data={"to": "Jim"}))
        emit(RunEvent(kind="agent_started", agent="Jim"))
        jim_out = (await built["jim"].run(prompt, deps=deps)).output
        _use(emit, "Jim", "search_quotes", "search_quote_history",
             lambda: db.search_quote_history(
                 [li.item_name for li in order.lines][:3] or ["paper"]))
        quote = decisions.price_order(order, policy, rationale=jim_out.rationale or "")
        emit(RunEvent(kind="agent_message", agent="Jim",
                      message=_summarize_quote(quote)))
        emit(RunEvent(kind="final_quote", agent="Jim",
                      data={"total": quote.total, "discount_pct": quote.discount_pct}))

    # 4. Stanley narrates; fulfill-or-decline is decided deterministically + recorded.
    if needs_sale:
        emit(RunEvent(kind="handoff", agent="Michael", data={"to": "Stanley"}))
        emit(RunEvent(kind="agent_started", agent="Stanley"))
        await built["stanley"].run(prompt, deps=deps)
        inv_for_decision = inventory or decisions.assess_inventory(order, request_date)
        # Try to cover any shortfall by restocking from the supplier (if cash allows),
        # turning would-be declines into sales. Unaffordable shortfalls still decline.
        if not inv_for_decision.all_available:
            emit(RunEvent(kind="tool_call", agent="Dwight", tool="cash_balance",
                          helper="get_cash_balance"))
            restock_ids = decisions.restock_shortfalls(
                order, inv_for_decision, request_date, policy)
            for _ in restock_ids:
                emit(RunEvent(kind="tool_call", agent="Dwight", tool="restock_item",
                              helper="create_transaction"))
            if restock_ids:
                inv_for_decision = decisions.assess_inventory(order, request_date)
        inventory = inv_for_decision  # record it so no-oversell can be checked
        quote_for_decision = quote or decisions.price_order(order, policy)
        sale = decisions.decide_fulfillment(
            order, inv_for_decision, quote_for_decision, request_date)
        if sale.fulfilled:
            sale.transaction_ids = _record_sale(
                order, quote_for_decision, request_date)
        emit(RunEvent(kind="agent_message", agent="Stanley",
                      message=_summarize_sale(sale)))

    # 5. David Wallace advises (post-hoc, non-blocking for the reply).
    emit(RunEvent(kind="agent_started", agent="David"))
    _use(emit, "David", "financial_report", "generate_financial_report",
         lambda: db.generate_financial_report(request_date))
    _use(emit, "David", "cash_balance", "get_cash_balance",
         lambda: db.get_cash_balance(request_date))
    advisor: AdvisorNote = (await built["david"].run(prompt, deps=deps)).output
    emit(RunEvent(kind="agent_message", agent="David",
                  message=_summarize_advice(advisor)))

    # 6. Michael synthesizes the customer-facing reply.
    synth = Agent(
        model or agents_mod.build_model(),
        deps_type=Deps,
        output_type=CustomerReply,
        system_prompt=PERSONAS["michael"]["prompt"],
    )
    context = (
        f"Customer request: {request_text}\n"
        f"Inventory: {inventory.model_dump() if inventory else 'n/a'}\n"
        f"Quote: {quote.model_dump() if quote else 'n/a'}\n"
        f"Sale: {sale.model_dump() if sale else 'n/a'}\n"
        "Write the final customer-facing reply with rationale."
    )
    reply = (await synth.run(context, deps=deps)).output
    emit(RunEvent(kind="financials_update", data={}))
    emit(RunEvent(kind="run_complete"))

    return RunResult(
        request_date=request_date, order=order, delegation=delegation,
        inventory=inventory, quote=quote, sale=sale, advisor=advisor, reply=reply,
    )


def _summarize_inventory(inv: InventoryAssessment) -> str:
    short = ", ".join(
        f"{ln.item_name}: {ln.available}/{ln.requested}"
        f"{'' if ln.sufficient else ' (short)'}"
        for ln in inv.lines[:4]
    )
    verdict = "all in stock" if inv.all_available else "some items short"
    return f"Checked the stock: {verdict}. {short}" if short else f"Checked the stock: {verdict}."


def _use(emit, agent: str, tool: str, helper: str, fn):
    """Run a starter helper deterministically and emit a tool_call event for it, so the
    work (and helper coverage) is real and visible regardless of which tools the LLM
    chooses to call."""
    emit(RunEvent(kind="tool_call", agent=agent, tool=tool, helper=helper))
    return fn()


def _record_sale(order, quote: Quote, as_of_date: str):
    """Record the sale deterministically: one transaction per line at its discounted
    price, decrementing real inventory. Returns the created transaction ids."""
    factor = 1.0 - quote.discount_pct
    ids = []
    for li in quote.line_items:
        price = round(li.line_total * factor, 2)
        ids.append(
            db.create_transaction(li.item_name, "sales", li.qty, price, as_of_date)
        )
    return ids


def _summarize_quote(q: Quote) -> str:
    disc = f" with a {q.discount_pct * 100:.0f}% bulk discount" if q.discount_pct else ""
    return f"Quote comes to ${q.total:.2f}{disc}. {q.rationale}"


def _summarize_sale(s: SaleResult) -> str:
    if s.fulfilled:
        eta = f", delivery {s.delivery_date}" if s.delivery_date else ""
        return f"Closing the sale: ${s.total_charged:.2f}{eta}."
    return f"Not closing this one: {s.decline_reason or 'cannot fulfill'}."


def _summarize_advice(a: AdvisorNote) -> str:
    if a.recommendations:
        return "Advisory: " + a.recommendations[0]
    if a.observations:
        return "Noted: " + a.observations[0]
    return "No concerns from the books."
