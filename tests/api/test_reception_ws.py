def test_reception_streams_events_and_result(client):
    client.post("/api/seed", json={"reset": True})
    with client.websocket_connect("/ws/reception") as ws:
        ws.send_json(
            {
                "request_text": "I need 100 reams of A4 paper.",
                "request_date": "2025-04-01",
            }
        )
        kinds, result, eval_msg = [], None, None
        while True:
            msg = ws.receive_json()
            if msg["type"] == "event":
                kinds.append(msg["event"]["kind"])
            elif msg["type"] == "eval":
                eval_msg = msg
            elif msg["type"] == "result":
                result = msg["result"]
                break
        assert "agent_started" in kinds
        assert "run_complete" in kinds
        assert result is not None and "reply" in result
        # embedded evaluation arrives before the result
        assert eval_msg is not None
        assert isinstance(eval_msg["checks"], list)
