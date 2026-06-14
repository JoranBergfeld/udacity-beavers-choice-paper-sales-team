from backend.munder.catalog import canonical_item_name
from backend.munder.decisions import price_order
from backend.munder.policies import BusinessPolicy
from backend.munder.schemas import OrderLine, ParsedOrder
from backend.munder.eval.deterministic import (
    check_price_math,
    check_discount_rule,
    check_valid_item_names,
)


def test_canonical_item_matches_catalog():
    assert canonical_item_name("Glossy paper") == "Glossy paper"      # exact
    assert canonical_item_name("glossy paper") == "Glossy paper"      # case-insensitive
    assert canonical_item_name("A4 PAPER") == "A4 paper"              # case-insensitive
    assert canonical_item_name("glossy papers") == "Glossy paper"     # fuzzy


def test_price_order_prices_from_catalog_and_applies_policy():
    order = ParsedOrder(lines=[OrderLine(item_name="Glossy paper", qty=600)])
    q = price_order(order, BusinessPolicy())

    li = q.line_items[0]
    assert li.unit_price == 0.20                    # catalog price
    assert li.line_total == 120.0                   # 600 * 0.20
    assert q.subtotal == 120.0
    assert q.discount_pct == 0.10                    # 600 units -> 500+ tier = 10%
    assert q.discount_amount == 12.0
    assert q.total == 108.0


def test_priced_order_passes_deterministic_checks():
    order = ParsedOrder(lines=[OrderLine(item_name="A4 paper", qty=1200)])
    policy = BusinessPolicy()
    q = price_order(order, policy)

    assert check_price_math(q).passed is True
    assert check_discount_rule(q, policy).passed is True
    assert check_valid_item_names([li.item_name for li in q.line_items]).passed is True
