"""The connection gate: no live test, no demo. No other way in."""
import os

from tests.conftest import pass_gate


def test_start_refused_until_both_roles_pass(client):
    assert client.post("/api/demo/start").status_code == 409
    assert client.post("/api/demo/control", json={"cmd": "restart"}).status_code == 409
    assert client.post("/api/demo/control", json={"cmd": "jump", "value": 4}).status_code == 409
    pass_gate(client)
    assert client.post("/api/demo/start").status_code == 200


def test_failed_role_keeps_gate_closed(client):
    client.mock.fail_role = "test"
    r = client.post("/api/connection/test", json={"provider": "foundry", "token": "fake-gate-token-0002",
                                                    "models": {"agent": "azure:gpt-4.1-mini",
                                                               "investigator": "bedrock:claude-sonnet-4.5"}})
    body = r.json()
    assert not body["ready"]
    assert not body["tests"]["agent"]["ok"] and "Paste a fresh token" in body["tests"]["agent"]["message"]
    assert client.post("/api/demo/start").status_code == 409


def test_environment_variable_cannot_supply_token(client, monkeypatch):
    for name in ("FOUNDRY_TOKEN", "LLM_TOKEN", "OPENROUTER_API_KEY", "TOKEN"):
        monkeypatch.setenv(name, "fake-env-token-should-be-ignored")
    status = client.get("/api/connection/status").json()
    assert status["token"] is None and not status["ready"]
    assert client.post("/api/demo/start").status_code == 409
    assert os.environ["FOUNDRY_TOKEN"]          # set, and still ignored


def test_forget_token_closes_gate_and_masking(client):
    body = pass_gate(client, fake="fake-gate-token-abcd").json()
    assert body["token"] == "••••abcd"
    assert client.post("/api/connection/forget").json()["token"] is None
    assert client.post("/api/demo/start").status_code == 409


def test_changing_models_requires_a_new_test(client):
    import app.llm as llm
    pass_gate(client)
    llm.CONNECTION.models["agent"] = "azure:gpt-4o-mini"
    assert client.post("/api/demo/start").status_code == 409


def test_mock_cannot_be_chosen_from_the_gate(client):
    r = client.post("/api/connection/test", json={"provider": "mock", "token": "x" * 20,
                                                    "models": {"agent": "mock", "investigator": "mock"}})
    assert r.status_code == 400
