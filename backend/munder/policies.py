from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class DiscountTier:
    min_units: int
    pct: float


def _default_tiers() -> List[DiscountTier]:
    return [
        DiscountTier(0, 0.0),
        DiscountTier(100, 0.05),
        DiscountTier(500, 0.10),
        DiscountTier(1000, 0.15),
    ]


@dataclass
class BusinessPolicy:
    """Decision rules the agents read instead of hardcoding logic."""

    discount_tiers: List[DiscountTier] = field(default_factory=_default_tiers)
    cash_floor: float = 5000.0

    def bulk_discount_pct(self, total_units: int) -> float:
        pct = 0.0
        for tier in sorted(self.discount_tiers, key=lambda t: t.min_units):
            if total_units >= tier.min_units:
                pct = tier.pct
        return pct

    def should_reorder(self, current_stock: int, min_level: int) -> bool:
        return current_stock < min_level

    def can_afford(self, cash: float, cost: float) -> bool:
        return (cash - cost) >= self.cash_floor


def load_policy(path: Optional[str] = None) -> BusinessPolicy:
    if path and Path(path).exists():
        raw = json.loads(Path(path).read_text())
        tiers = [DiscountTier(**t) for t in raw.get("discount_tiers", [])]
        return BusinessPolicy(
            discount_tiers=tiers or _default_tiers(),
            cash_floor=raw.get("cash_floor", 5000.0),
        )
    return BusinessPolicy()
