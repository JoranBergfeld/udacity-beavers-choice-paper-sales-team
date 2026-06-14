from backend.munder.schemas import (
    DelegationPlan, InventoryAssessment, InventoryLine,
    Quote, QuoteLine, SaleResult, AdvisorNote, CustomerReply, RunResult,
)


def test_models_construct_and_roundtrip():
    plan = DelegationPlan(needs_inventory=True, needs_quote=True,
                          needs_sale=False, reasoning="r")
    inv = InventoryAssessment(
        lines=[InventoryLine(item_name="A4 paper", requested=500, available=412,
                             sufficient=False, reorder_recommended=True,
                             reorder_qty=200, delivery_date="2025-04-16")],
        all_available=False,
    )
    quote = Quote(line_items=[QuoteLine(item_name="A4 paper", qty=412,
                  unit_price=0.05, line_total=20.6)],
                  subtotal=20.6, discount_pct=0.05, discount_amount=1.03,
                  total=19.57, rationale="bulk")
    sale = SaleResult(fulfilled=True, transaction_ids=[1], total_charged=19.57)
    advisor = AdvisorNote(observations=["low A4"], recommendations=["reorder"])
    reply = CustomerReply(text="Here is your quote...", fulfilled=True)
    result = RunResult(request_date="2025-04-01", delegation=plan, inventory=inv,
                       quote=quote, sale=sale, advisor=advisor, reply=reply)
    assert result.model_dump()["reply"]["fulfilled"] is True
