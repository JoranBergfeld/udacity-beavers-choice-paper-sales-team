from backend.munder.events import RunEvent, EventCollector


def test_collector_records_events_in_order():
    c = EventCollector()
    c(RunEvent(kind="agent_started", agent="Michael"))
    c(RunEvent(kind="tool_call", agent="Dwight", tool="check_stock",
               helper="get_stock_level", data={"item": "A4 paper"}))
    assert [e.kind for e in c.events] == ["agent_started", "tool_call"]
    assert c.events[1].helper == "get_stock_level"


def test_helpers_used_extracts_unique_helper_names():
    c = EventCollector()
    c(RunEvent(kind="tool_call", helper="get_stock_level"))
    c(RunEvent(kind="tool_call", helper="get_stock_level"))
    c(RunEvent(kind="tool_call", helper="create_transaction"))
    assert c.helpers_used() == {"get_stock_level", "create_transaction"}
