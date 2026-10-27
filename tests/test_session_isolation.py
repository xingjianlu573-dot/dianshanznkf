from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def setup_function():
    api._conversations.clear()
    api._session_order.clear()


def test_requests_without_session_id_get_distinct_histories(monkeypatch):
    observed_histories = []

    def fake_answer_message(message, platform, history):
        observed_histories.append(list(history))
        return {"intent": "TEST", "answer": f"answer:{message}", "sources": []}

    monkeypatch.setattr(api, "answer_message", fake_answer_message)

    first = client.post("/chat", json={"message": "private marker ALPHA"})
    second = client.post("/chat", json={"message": "what was the prior marker?"})

    assert first.status_code == 200
    assert second.status_code == 200
    first_sid = first.json()["session_id"]
    second_sid = second.json()["session_id"]
    assert first_sid != second_sid
    assert first_sid != "default"
    assert second_sid != "default"
    assert observed_histories == [[], []]


def test_explicit_session_id_preserves_multiturn_context(monkeypatch):
    observed_histories = []

    def fake_answer_message(message, platform, history):
        observed_histories.append(list(history))
        return {"intent": "TEST", "answer": f"answer:{message}", "sources": []}

    monkeypatch.setattr(api, "answer_message", fake_answer_message)

    first = client.post("/chat", json={"message": "hello", "session_id": "same-session"})
    second = client.post("/chat", json={"message": "follow-up", "session_id": "same-session"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["session_id"] == second.json()["session_id"] == "same-session"
    assert observed_histories[0] == []
    assert observed_histories[1] == [
        {"role": "user", "content": "hello"},
        {"role": "agent", "content": "answer:hello"},
    ]
