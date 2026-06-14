from backend.munder.eval.deterministic import (
    check_price_math, check_discount_rule, check_no_oversell,
    check_valid_item_names, check_leakage, CheckResult,
)
from backend.munder.policies import BusinessPolicy
from backend.munder.schemas import Quote, QuoteLine, CustomerReply


def _quote(discount_pct):
    line = QuoteLine(item_name="A4 paper", qty=500, unit_price=0.05, line_total=25.0)
    subtotal = 25.0
    disc = round(subtotal * discount_pct, 2)
    return Quote(line_items=[line], subtotal=subtotal, discount_pct=discount_pct,
                 discount_amount=disc, total=round(subtotal - disc, 2),
                 rationale="bulk")


def test_price_math_passes_for_consistent_quote():
    assert check_price_math(_quote(0.10)).passed is True


def test_price_math_fails_when_total_wrong():
    q = _quote(0.10)
    q.total = 999.0
    assert check_price_math(q).passed is False


def test_discount_rule_matches_policy():
    p = BusinessPolicy()
    # 500 units -> 10% per default tiers
    assert check_discount_rule(_quote(0.10), p).passed is True
    assert check_discount_rule(_quote(0.0), p).passed is False


def test_no_oversell():
    assert check_no_oversell(sold=400, available=412).passed is True
    assert check_no_oversell(sold=500, available=412).passed is False


def test_valid_item_names():
    assert check_valid_item_names(["A4 paper"]).passed is True
    assert check_valid_item_names(["Nonexistent paper"]).passed is False


def test_leakage_flags_margin_and_pii():
    clean = CustomerReply(text="Your total is $24.50 after a 10% bulk discount.",
                          fulfilled=True)
    leaky = CustomerReply(text="Our profit margin on this is 60%. SSN 123-45-6789.",
                          fulfilled=True)
    assert check_leakage(clean).passed is True
    assert check_leakage(leaky).passed is False
