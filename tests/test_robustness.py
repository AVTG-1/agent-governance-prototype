"""Bug (c) and section 4: the pause card's Retry / Switch model / Restart, late replies from an old run,
one controlling tab, an idempotent Start, a 429 back-off, preflight, approvals at every speed."""
import asyncio
import time

import httpx
import pytest

import app.llm as llm
from app.demo import acts
from app.demo.director import Director
from app.demo.keyviews import KeyViews
from app.events import Bus
from tests.conftest import pass_gate, wait_done


@pytest.fixture
def token():
    from app import secrets_store
    secrets_store.set("fake-robust-token-0001")
    yield
    secrets_store.clear()


def _wait(pred, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred():
            return
        time.sleep(0.02)
    raise AssertionError("condition not reached")


# --- (c) the pause card -------------------------------------------------------------------------

def _fail_rulebook_once(mock_llm, kind="parse"):
    """The first rulebook call fails; later ones succeed."""
    orig = mock_llm.__call__

    async def call(provider, model_ref, token, settings, system, user, json_mode=True):
        if mock_llm.role_of(system) == "rulebook":
            mock_llm.rulebook_sent = getattr(mock_llm, "rulebook_sent", 0) + 1
        if mock_llm.role_of(system) == "rulebook" and not getattr(mock_llm, "_failed_once", False):
            mock_llm._failed_once = True
            raise llm.LLMError(kind, "The investigator model returned unusable JSON twice for the rulebook draft.")
        return await orig(provider, model_ref, token, settings, system, user, json_mode)
    return call


def test_failed_call_pauses_with_job_and_time_needed_then_retry_resends_it(client, monkeypatch):
    import app.main as main
    monkeypatch.setattr(llm, "_call_model", _fail_rulebook_once(client.mock))
    pass_gate(client)
    client.post("/api/demo/start")
    _wait(lambda: main.director.run.failed is not None)
    run = main.director.run
    errs = [e["payload"] for e in run.events if e["kind"] == "error" and e["payload"].get("message")]
    assert errs[-1]["job"] == "rulebook" and errs[-1]["label"] == "rulebook draft"
    assert errs[-1]["needed_at"] == "1:09" and errs[-1]["model_name"] == "claude-sonnet-4.5"
    lights = [e["payload"]["status"] for e in run.events if e["kind"] == "llm" and e["payload"]["job"] == "rulebook"]
    assert lights[:3] == ["pending", "requested", "failed"]
    assert client.post("/api/demo/control", json={"cmd": "retry"}).json() == {"ok": True}
    wait_done(client)
    assert client.mock.rulebook_sent == 2                # re-sent exactly once
    assert run.data["rulebook_ok"] == 16


def test_switch_investigator_model_tests_it_live_then_retries_with_it(client, monkeypatch):
    import app.main as main
    monkeypatch.setattr(llm, "_call_model", _fail_rulebook_once(client.mock))
    pass_gate(client)
    status = client.get("/api/connection/status").json()
    assert any(o["ref"] == "azure:gpt-4.1" for o in status["switch"]["investigator"])   # a JSON-mode model offered
    client.post("/api/demo/start")
    _wait(lambda: main.director.run.failed is not None)
    r = client.post("/api/demo/switch_model", json={"role": "investigator", "model": "azure:gpt-4.1"})
    assert r.status_code == 200 and r.json()["models"]["investigator"] == "azure:gpt-4.1"
    wait_done(client)
    used = [c for c in client.mock.calls if c["role"] in ("test", "rulebook", "case", "diff")]
    assert {"role": "test", "model_ref": "azure:gpt-4.1", "provider": "foundry"} in used    # tested live first
    assert [c["model_ref"] for c in used if c["role"] == "rulebook"][-1] == "azure:gpt-4.1"
    assert main.director.run.models["investigator"] == "azure:gpt-4.1"


def test_switch_to_a_model_that_fails_its_test_is_refused(client, monkeypatch):
    pass_gate(client)
    client.mock.fail_role = "test"
    r = client.post("/api/demo/switch_model", json={"role": "investigator", "model": "azure:gpt-4o"})
    assert r.status_code == 400 and "failed its live test" in r.json()["detail"]


def test_restart_from_the_pause_card_starts_clean(client, monkeypatch):
    import app.main as main
    monkeypatch.setattr(llm, "_call_model", _fail_rulebook_once(client.mock))
    pass_gate(client)
    client.post("/api/demo/start")
    _wait(lambda: main.director.run.failed is not None)
    old = main.director.run
    client.post("/api/demo/control", json={"cmd": "restart"})
    new = main.director.run
    assert new is not old and new.failed is None and not main.director.paused
    wait_done(client)


def test_401_asks_for_a_token_and_the_same_step_resumes(client):
    import app.main as main
    pass_gate(client)
    client.mock.fail_role, client.mock.fail_kind = "rulebook", "once"
    client.post("/api/demo/start")
    _wait(lambda: main.director.run.failed is not None)
    assert main.director.run.failed["need_token"]
    step = main.director.run.step_index
    assert client.post("/api/connection/token", json={"token": "fake-fresh-token-0002"}).status_code == 200
    client.post("/api/demo/control", json={"cmd": "retry"})
    wait_done(client)
    assert main.director.run.step_index > step and main.director.run.data["rulebook_ok"] == 16


# --- late replies, one director, double start ---------------------------------------------------------

def test_late_reply_from_an_old_run_is_dropped(mock_llm, token):
    mock_llm.delay = 0.3

    async def go():
        d = Director(Bus(), KeyViews())
        d.instant = True
        await d.start()
        old = d.run
        await asyncio.sleep(0.05)
        await d.start()                       # restart while the rulebook call is in flight
        new = d.run
        await asyncio.sleep(0.5)
        await d.stop()
        return old, new
    old, new = asyncio.run(go())
    assert all(e["run"] == new.id for e in new.events)
    assert "rulebook_latency_ms" not in old.data           # the old task was cancelled, not merged
    assert sum(1 for e in new.events if e["kind"] == "run") == 1


def test_late_prefetch_for_an_old_run_cannot_start_in_the_new_one(mock_llm, token):
    async def go():
        d = Director(Bus(), KeyViews())
        await d.start()
        old = d.run
        await d.start()
        d.prefetch("diff", lambda: asyncio.sleep(0), run=old)
        assert "diff" not in d.run.llm
        await d.stop()
    asyncio.run(go())


def test_second_tab_is_a_viewer_and_cannot_start_a_second_run(client):
    pass_gate(client)
    a, b = {"X-Console-Id": "tab-a"}, {"X-Console-Id": "tab-b"}
    import app.main as main
    main.director.instant = False
    main.director.speed = 0.5
    try:
        assert client.post("/api/demo/start", headers=a).status_code == 200
        r = client.post("/api/demo/start", headers=b)
        assert r.status_code == 409 and "viewer" in r.json()["detail"]
        assert client.post("/api/demo/control", json={"cmd": "pause"}, headers=b).status_code == 403
        assert client.get("/api/connection/status", headers=b).json()["controller"] == {"set": True, "you": False}
        assert client.post("/api/demo/take_control", headers=b).json()["controller"]["you"]
        assert client.post("/api/demo/control", json={"cmd": "pause"}, headers=b).status_code == 200
        assert client.post("/api/demo/control", json={"cmd": "pause"}, headers=a).status_code == 403
    finally:
        main.director.instant = True


def test_double_click_start_is_one_run(client):
    import app.main as main
    pass_gate(client)
    main.director.instant = False
    h = {"X-Console-Id": "tab-a"}
    first = client.post("/api/demo/start", headers=h).json()["run_id"]
    second = client.post("/api/demo/start", headers=h).json()["run_id"]
    assert first == second and main.director._runs == 1


def test_a_fresh_start_plays_at_1x(client):
    import app.main as main
    pass_gate(client)
    main.director.speed = 2.0
    client.post("/api/demo/start")
    assert main.director.speed == 1.0
    wait_done(client)
    main.director.speed = 2.0
    client.post("/api/demo/control", json={"cmd": "restart"})
    assert main.director.speed == 2.0                     # a restart keeps the presenter's speed
    wait_done(client)


# --- 429 back-off -----------------------------------------------------------------------------------

def _seam(responses):
    class Client:
        calls = 0

        async def post(self, *a, **k):
            Client.calls += 1
            return responses.pop(0)
    return Client()


def test_429_backs_off_once_then_succeeds(monkeypatch):
    monkeypatch.setattr(llm, "_retry_after", lambda v: 0.01)
    ok = httpx.Response(200, json={"choices": [{"message": {"content": "{\"ok\": true}"}, "finish_reason": "stop"}]})
    c = _seam([httpx.Response(429, headers={"retry-after": "1"}), ok])
    r = asyncio.run(llm._try_variants(c, "foundry", "azure", "https://x.invalid", {}, [{"name": "non-stream", "stream": False}],
                                      lambda v: ("/p", {}), "k429", "azure:gpt-4.1-mini"))
    assert r.text == '{"ok": true}' and c.calls == 2


def test_429_twice_pauses_with_the_reason(monkeypatch):
    assert llm._retry_after("120") == 8.0 and llm._retry_after(None) == 2.0 and llm._retry_after("1") == 1.0
    monkeypatch.setattr(llm, "_retry_after", lambda v: 0.01)
    c = _seam([httpx.Response(429), httpx.Response(429)])
    with pytest.raises(llm.LLMError) as e:
        asyncio.run(llm._try_variants(c, "foundry", "azure", "https://x.invalid", {}, [{"name": "v", "stream": False}],
                                      lambda v: ("/p", {}), "k", "azure:gpt-4.1-mini"))
    assert e.value.kind == "rate_limit" and "429" in e.value.message and c.calls == 2


# --- preflight ------------------------------------------------------------------------------------------

def test_preflight_runs_the_four_real_contracts_and_keeps_results_in_memory(client, tmp_path):
    pass_gate(client)
    assert client.post("/api/connection/preflight").status_code == 200
    pf = client.get("/api/connection/status").json()["preflight"]
    assert [r["job"] for r in pf["results"]] == ["rulebook", "plan", "case", "diff"] and pf["ok"]
    assert "16 of 16 grants verified" in pf["results"][0]["detail"] and "flagged" in pf["results"][0]["detail"]
    assert "follows the hidden instruction" in pf["results"][1]["detail"]
    assert pf["results"][3]["detail"] == "2 changes, 2 pass the verifier"
    roles = [c["role"] for c in client.mock.calls]
    assert sorted(roles[-4:]) == ["agent", "case", "diff", "rulebook"]
    assert any("Draft the day-zero rulebook" in p for p in client.mock.prompts)          # the real prompts
    assert client.post("/api/connection/forget").json()["preflight"] is None


def test_preflight_reports_a_failing_contract(client):
    pass_gate(client)
    client.mock.fail_role = "rulebook"
    pf = client.post("/api/connection/preflight").json()["preflight"]
    assert not pf["ok"] and not pf["results"][0]["ok"] and pf["results"][1]["ok"]


def test_preflight_needs_the_gate(client):
    assert client.post("/api/connection/preflight").status_code == 409


# --- approvals at every speed ----------------------------------------------------------------------

@pytest.mark.parametrize("speed", [0.5, 1.0, 2.0])
def test_approval_click_works_at_every_speed(mock_llm, token, speed):
    async def go():
        d = Director(Bus(), KeyViews())
        await d.start()
        await d.stop()
        d.speed = speed
        task = asyncio.create_task(acts.owner_approval(d, {"kind": "harden", "title": "t"}))
        await asyncio.sleep(0.25)
        d.approve()
        clicked = await asyncio.wait_for(task, 1.0)
        shown = [e["payload"]["approval"] for e in d.run.events if e["kind"] == "system" and "approval" in e["payload"]]
        return clicked, shown
    clicked, shown = asyncio.run(go())
    assert clicked and shown[0]["remaining"] == 8 and shown[-1] is None


def test_approval_auto_signs_and_is_labelled(client):
    import app.main as main
    pass_gate(client)
    client.post("/api/demo/start")
    wait_done(client)
    notes = [h["note"] for h in main.director.run.world.policy.history[1:]]
    assert len(notes) == 2 and all(n.endswith("(auto-signed for demo)") and "signed by" in n for n in notes)


def test_stream_events_carry_ids_for_resync(client):
    import app.main as main
    from tests.test_no_token_leak import sse_snapshot
    pass_gate(client)
    client.post("/api/demo/start")
    wait_done(client)
    text = sse_snapshot(main)
    assert text.startswith("retry: ") and "\nid: 1\ndata: " in text
    assert text.count("\nid: ") == len(main.director.run.events)
