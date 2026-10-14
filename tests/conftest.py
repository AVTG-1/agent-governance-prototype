import pytest

from app.core.policies import baseline_policy
from app.core.world import World


@pytest.fixture
def world():
    """A world after Acts 1–2: agents discovered, recon wrapped, baseline policy adopted."""
    w = World()
    w.discover()
    w.assign_owners()
    w.registry.wrap("recon-agent")
    w.policy.adopt(baseline_policy(w.policy.current), "baseline")
    return w


@pytest.fixture
def mock_llm(monkeypatch):
    """Install the test-only mock as the provider seam. This is the only way the mock is ever selected."""
    import app.llm as llm
    from app.llm.mock import MockLLM

    mock = MockLLM()
    monkeypatch.setattr(llm, "_call_model", mock)
    return mock


@pytest.fixture
def client(mock_llm):
    """A fresh app state (connection, token, director, key views) and a TestClient bound to it."""
    from fastapi.testclient import TestClient

    import app.llm as llm
    import app.main as main
    from app import secrets_store
    from app.demo.director import Director
    from app.demo.keyviews import KeyViews

    secrets_store.clear()
    llm.CONNECTION = llm.Connection()
    main.keyviews = KeyViews()
    main.director = Director(main.bus, main.keyviews)
    main.director.instant = True
    with TestClient(main.app) as c:
        c.mock = mock_llm
        yield c
    secrets_store.clear()
    llm.CONNECTION = llm.Connection()


def pass_gate(client, fake="fake-gate-token-0001"):
    r = client.post("/api/connection/test", json={
        "provider": "foundry", "token": fake, "project": "llmproxy-playground",
        "models": {"agent": "azure:gpt-4.1-mini", "investigator": "bedrock:claude-sonnet-4.5"}})
    assert r.status_code == 200 and r.json()["ready"], r.text
    return r


def wait_done(client, timeout=20.0, key="done"):
    import time
    t0 = time.time()
    while time.time() - t0 < timeout:
        if client.get("/api/connection/status").json()["run"][key]:
            return
        time.sleep(0.05)
    raise AssertionError("run did not finish")
