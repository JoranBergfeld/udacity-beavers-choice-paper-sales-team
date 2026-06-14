from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from backend.munder.db import paper_supplies
from backend.munder.policies import BusinessPolicy
from backend.munder.schemas import Quote, CustomerReply

_CATALOG = {item["item_name"] for item in paper_supplies}

_LEAKAGE_PATTERNS = [
    re.compile(r"profit margin", re.I),
    re.compile(r"\bcost basis\b", re.I),
    re.compile(r"traceback", re.I),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),          # SSN-like
    re.compile(r"\bmargin\b.*\d+%", re.I),
]


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def check_price_math(quote: Quote, tol: float = 0.011) -> CheckResult:
    sub = round(sum(li.line_total for li in quote.line_items), 2)
    expected_total = round(quote.subtotal - quote.discount_amount, 2)
    ok = abs(sub - quote.subtotal) <= tol and abs(expected_total - quote.total) <= tol
    return CheckResult("price_math", ok,
                       f"subtotal={sub} total={quote.total}")


def check_discount_rule(quote: Quote, policy: BusinessPolicy) -> CheckResult:
    total_units = sum(li.qty for li in quote.line_items)
    expected = policy.bulk_discount_pct(total_units)
    ok = abs(expected - quote.discount_pct) < 1e-6
    return CheckResult("discount_rule", ok,
                       f"expected={expected} got={quote.discount_pct}")


def check_no_oversell(sold: int, available: int) -> CheckResult:
    return CheckResult("no_oversell", sold <= available,
                       f"sold={sold} available={available}")


def check_valid_item_names(item_names: List[str]) -> CheckResult:
    bad = [n for n in item_names if n not in _CATALOG]
    return CheckResult("valid_item_names", not bad, f"invalid={bad}")


def check_leakage(reply: CustomerReply) -> CheckResult:
    hits = [p.pattern for p in _LEAKAGE_PATTERNS if p.search(reply.text)]
    return CheckResult("no_leakage", not hits, f"hits={hits}")


def run_all_checks(result, policy: BusinessPolicy) -> List[CheckResult]:
    """Run every applicable deterministic check against a single RunResult. Used to embed
    evaluation into the live request flow (and reusable by the batch harness)."""
    checks: List[CheckResult] = []
    if result.quote and result.quote.line_items:
        checks.append(check_price_math(result.quote))
        checks.append(check_discount_rule(result.quote, policy))
        checks.append(
            check_valid_item_names([li.item_name for li in result.quote.line_items])
        )
    if result.reply:
        checks.append(check_leakage(result.reply))
    if result.sale and result.sale.fulfilled and result.inventory:
        for ln in result.inventory.lines:
            checks.append(check_no_oversell(ln.requested, ln.available))
    return checks
