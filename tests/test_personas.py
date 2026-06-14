from backend.munder.personas import PERSONAS, GUARDRAIL

EXPECTED = {"michael", "dwight", "jim", "stanley", "david"}


def test_all_five_personas_present():
    assert set(PERSONAS.keys()) == EXPECTED


def test_each_persona_has_name_and_prompt():
    for key, p in PERSONAS.items():
        assert p["name"]
        assert len(p["prompt"]) > 50


def test_customer_facing_personas_include_leakage_guardrail():
    # Michael writes the customer reply; guardrail must be in his prompt.
    assert GUARDRAIL in PERSONAS["michael"]["prompt"]
