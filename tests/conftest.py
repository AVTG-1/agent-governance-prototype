import pytest

from app.core import rulebook as rb
from app.core.gateway import Call
from app.core.world import World


def day_zero_world(shadow: bool = True) -> World:
    """Act 1 and the start of Act 2: discovered, owners assigned, all four onboarded, the week shadowed."""
    w = World()
    w.discover()
    w.assign_owners()
    w.onboard_all()
    if shadow:
        for spec in w.shadow_week:
            w.gateway.handle(Call.from_spec({**spec, "session": "s-shadow-week"}), enforce=False, execute=False)
    return w


def summary_of(w: World) -> dict:
    return rb.usage_summary(w.audit.records, w.signals, w.usage, w.estate.refdata["calendar"], w.owners())


def approve_rulebook(w: World, draft: dict | None = None):
    from app.llm.mock import RULEBOOK
    lines = rb.verify_rulebook(rb.RulebookDraft.model_validate(draft or RULEBOOK), summary_of(w))
    w.policy.approve(rb.build_rulebook(w.policy.current, lines), owner="Agent owners", how="test")
    return lines


@pytest.fixture
def world():
    """A world after Act 2: the owners approved the (good) AI-drafted rulebook@v1; default deny is on."""
    w = day_zero_world()
    approve_rulebook(w)
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
