"""The director plays the whole script in 300 ± 20 scripted seconds and reaches every act."""
import asyncio
import time

import pytest

from app.demo.director import Director
from app.demo.keyviews import KeyViews
from app.demo.script import ACTS, END, KEY_VIEWS, STEPS
from app.events import Bus


@pytest.fixture
def token():
    from app import secrets_store
    secrets_store.set("fake-director-token-0001")
    yield
    secrets_store.clear()


def play(speed=None, instant=True, mock_plan="compromised"):
    async def go():
        d = Director(Bus(), KeyViews())
        d.instant = instant
        if speed:
            d.speed = speed
        t0 = time.perf_counter()
        await d.start()
        await d.task
        return d, time.perf_counter() - t0
    return asyncio.run(go())


def test_script_shape():
    assert sum(1 for s in STEPS if s.keyview) == 8
    assert [s.act for s in STEPS] == sorted(s.act for s in STEPS)
    assert END == 300
    assert [ACTS[a]["start"] for a in range(1, 7)] == [0, 25, 80, 110, 140, 225]
    assert [ACTS[a]["title"] for a in range(1, 7)] == ["Discover", "Shadow and learn", "People sign", "Enforce",
                                                      "Attack", "Tighten and prove"]       # the deck's Prototype chapter
    for s in STEPS:
        nxt = [x for x in STEPS if x.act == s.act + 1]
        if nxt:
            assert s.abs_at < ACTS[s.act + 1]["start"]


def test_full_run_is_300s_and_reaches_every_act(mock_llm, token):
    d, _ = play()
    run = d.run
    assert abs(run.t - 300) <= 20
    acts = [e["payload"]["act"] for e in run.events if e["kind"] == "act"]
    assert acts == [1, 2, 3, 4, 5, 6]
    for e in run.events:
        if e["kind"] == "act":
            assert e["t"] == ACTS[e["payload"]["act"]]["start"]
    markers = [e["payload"]["id"] for e in run.events if e["kind"] == "keyview"]
    assert markers == [k["id"] for k in KEY_VIEWS]
    assert run.done and run.closed
    assert run.data["metrics"]["attacks_blocked"] == 20 and run.data["metrics"]["legit_broken"] == 0


def test_real_clock_path_at_high_speed(mock_llm, token):
    d, wall = play(speed=150, instant=False)
    assert abs(d.run.t - 300) <= 20
    assert 1.0 < wall < 10


def test_prefetch_order(mock_llm, token):
    d, _ = play()
    jobs = [(e["t"], e["payload"]["job"]) for e in d.run.events if e["kind"] == "llm" and e["payload"]["status"] == "requested"]
    assert [j for _, j in jobs] == ["rulebook", "plan", "case", "diff"]     # four live calls per run
    assert jobs[0][0] == 0                                     # the rulebook draft goes out at Start
    assert ACTS[2]["start"] <= jobs[1][0] < ACTS[2]["start"] + 5   # the plan at the start of Act 2
    assert ACTS[5]["start"] < jobs[2][0] < ACTS[6]["start"]   # case at the first Act 5 denial
    assert ACTS[5]["start"] < jobs[3][0] < ACTS[6]["start"]   # diff as soon as the case is ready
    roles = [e["payload"]["role"] for e in d.run.events if e["kind"] == "llm" and e["payload"]["status"] == "used"]
    assert roles == ["investigator", "agent", "investigator", "investigator"]


def test_controls_pause_next_jump_restart_speed(mock_llm, token):
    async def go():
        d = Director(Bus(), KeyViews())
        d.speed = 20
        await d.start()
        await asyncio.sleep(0.2)
        d.pause("presenter")
        t_paused = d.run.t
        await asyncio.sleep(0.3)
        assert d.run.t == t_paused                     # scripted clock stops while paused
        d.resume()
        d.next_step()
        await asyncio.sleep(0.2)
        assert d.run.step_index >= 1
        await d.jump(4)                                # forward jump fast-forwards earlier acts
        for _ in range(100):
            if d.run.act >= 4:
                break
            await asyncio.sleep(0.05)
        assert d.run.act >= 4
        first = d.run
        await d.jump(2)                                # backward jump restarts and fast-forwards
        assert d.run is not first and d.run.world.audit.records == [] or d.run.act <= 2
        d.set_speed(2.0)
        assert d.speed == 2.0
        d.set_speed(7.0)
        assert d.speed == 2.0                          # only 0.5x, 1x, 2x
        await d.stop()
    asyncio.run(go())


def test_restart_fully_resets(mock_llm, token):
    async def go():
        d = Director(Bus(), KeyViews())
        d.instant = True
        await d.start()
        await d.task
        old = d.run
        assert old.world.policy.current.version_label() == "rulebook@v2"
        d.instant = False
        await d.start()
        new = d.run
        assert new is not old and new.t == 0 and new.world.audit.records == []
        assert new.world.policy.current.version_label() == "rulebook@v0"
        assert new.world.estate.outbox == [] and new.events[0]["kind"] == "run"
        await d.stop()
    asyncio.run(go())


def test_llm_timeout_pauses_with_a_plain_message(mock_llm, token):
    mock_llm.delay = 0.3

    async def go():
        import app.demo.script as script
        d = Director(Bus(), KeyViews())
        d.instant = True
        await d.start()
        # Shrink the timeout for the plan step to force the timeout path.
        for _ in range(200):
            if d.paused:
                break
            await asyncio.sleep(0.01)
        return d
    # Temporarily give the plan step a tiny timeout.
    import dataclasses
    import app.demo.director as director_mod
    orig = list(director_mod.STEPS)
    director_mod.STEPS[:] = [dataclasses.replace(s, timeout_s=0.05) if s.wait_for == "rulebook" else s for s in orig]
    try:
        d = asyncio.run(go())
        errs = [e["payload"] for e in d.run.events if e["kind"] == "error" and e["payload"].get("message")]
        assert d.paused and errs and errs[-1]["kind"] == "timeout" and "No reply" in errs[-1]["message"]
    finally:
        director_mod.STEPS[:] = orig


def test_agent_resists_uses_labelled_recorded_plan(mock_llm, token):
    mock_llm.plan = "resistant"
    d, _ = play()
    assert d.run.data["plan_source"] == "recorded"
    panels = [e["payload"]["set"] for e in d.run.events if e["kind"] == "panel" and e["payload"]["view"] == "attack"]
    banner = [p["fallback"] for p in panels if p.get("fallback")]
    assert banner == ["The model declined the hidden instruction. Good — but models don't always. "
                      "Replaying a recorded compromised plan to test the controls."]
    assert any(p.get("plan_source") == "recorded" for p in panels)
    rules = [e["payload"]["rule"] for e in d.run.events if e["kind"] == "decision" and e["act"] == 5]
    assert rules == ["R-PII-01", "R-DLG-02", "R-EGR-01"]


def test_next_goes_exactly_one_step(mock_llm, token):
    async def go():
        d = Director(Bus(), KeyViews())
        await d.start()
        await asyncio.sleep(0.1)
        assert d.run.step_index == -1                  # the Act 1 intro card is showing
        for expected in (0, 1, 2, 3):
            d.next_step()
            await asyncio.sleep(0.15)
            assert d.run.step_index == expected
        await d.stop()
    asyncio.run(go())


def test_sse_events_follow_the_schema(mock_llm, token):
    d, _ = play()
    keys = {"run", "seq", "t", "act", "kind", "payload", "ts", "prev_hash", "hash"}
    for i, e in enumerate(d.run.events, 1):
        assert set(e) == keys and e["seq"] == i
        assert (e["hash"] is not None) == (e["kind"] == "decision")
    decisions = [e for e in d.run.events if e["kind"] == "decision"]
    by_n = {r["hash"]: r for r in d.run.world.audit.records}
    assert all(by_n[e["hash"]]["prev_hash"] == e["prev_hash"] for e in decisions)
