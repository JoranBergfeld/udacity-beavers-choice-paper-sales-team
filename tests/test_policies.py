from backend.munder.policies import BusinessPolicy, DiscountTier, load_policy


def test_bulk_discount_tiers():
    p = BusinessPolicy()
    assert p.bulk_discount_pct(10) == 0.0
    assert p.bulk_discount_pct(100) == 0.05
    assert p.bulk_discount_pct(500) == 0.10
    assert p.bulk_discount_pct(2000) == 0.15


def test_should_reorder():
    p = BusinessPolicy()
    assert p.should_reorder(40, 50) is True
    assert p.should_reorder(60, 50) is False


def test_can_afford_respects_cash_floor():
    p = BusinessPolicy(cash_floor=5000.0)
    assert p.can_afford(10000, 4000) is True   # leaves 6000
    assert p.can_afford(10000, 6000) is False  # leaves 4000 < floor


def test_load_policy_from_json(tmp_path):
    f = tmp_path / "policies.json"
    f.write_text('{"cash_floor": 1000, "discount_tiers":'
                 ' [{"min_units":0,"pct":0.0},{"min_units":50,"pct":0.2}]}')
    p = load_policy(str(f))
    assert p.cash_floor == 1000
    assert p.bulk_discount_pct(50) == 0.2


def test_load_policy_defaults_when_missing():
    p = load_policy(None)
    assert isinstance(p, BusinessPolicy)
    assert p.cash_floor == 5000.0
