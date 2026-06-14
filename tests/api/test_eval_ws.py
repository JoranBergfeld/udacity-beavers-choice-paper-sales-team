def test_eval_streams_progress_and_report(client):
    with client.websocket_connect("/ws/eval") as ws:
        ws.send_json({"limit": 3, "judge": False})
        progress, report = 0, None
        while True:
            msg = ws.receive_json()
            if msg["type"] == "progress":
                progress += 1
            elif msg["type"] == "report":
                report = msg["report"]
                break
        assert progress >= 1
        assert "rubric" in report
        rub = report["rubric"]
        assert rub["fulfilled_count"] + rub["declined_count"] == 3
