"""Captioned replay (SPEC §5.9): at most 90 s, sections at their own speeds, callouts filled only with this
run's facts, carried by key views and the offline export, no token, no model call."""
import json
import re

from app.demo.replay import WARP, build_replay, replay_seconds, total_seconds
from app.demo.script import ACTS, END
from tests.conftest import pass_gate, wait_done

FAKE = "fake-REPLAY-" + __import__("secrets").token_hex(10)


def run_once(client):
    pass_gate(client, fake=FAKE)
    client.post("/api/demo/start")
    wait_done(client)
    import app.main as main
    return main.director.run


def test_warp_covers_the_whole_run_in_at_most_90_seconds():
    assert WARP[0][0] == 0 and WARP[-1][1] == END
    assert all(a[1] == b[0] for a, b in zip(WARP, WARP[1:]))            # contiguous, no gaps
    assert total_seconds() <= 90
    assert all(s > 0 for _, _, s in WARP)
    assert replay_seconds(0) == 0 and replay_seconds(END) == total_seconds()
    # Different speeds by importance: People sign plays slower than the shadow week's onboarding.
    rate = {(a, b): s / (b - a) for a, b, s in WARP}
    assert rate[(80, 110)] > rate[(25, 50)]
    for act in ACTS.values():                                          # act starts are section boundaries
        assert any(a == act["start"] for a, _, _ in WARP)


def test_callouts_tell_this_runs_facts(client):
    run = run_once(client)
    r = build_replay(run)
    cs = r["callouts"]
    assert 12 <= len(cs) <= 20
    ats = [c["at_r"] for c in cs]
    assert ats == sorted(ats) and all(b - a >= 2.5 for a, b in zip(ats, ats[1:]))
    assert all(1.5 <= c["show_r"] <= 4.2 and c["at_r"] + c["show_r"] <= r["total"] for c in cs)
    text = " ".join(c["title"] + " " + c["text"] for c in cs)
    assert "None" not in text and "{" not in text
    m = run.data["metrics"]
    assert f"{m['shadow_calls']:,} calls" in text
    assert f"{m['attacks_blocked']} of {m['attacks_total']} attacks blocked" in text
    assert f"{run.data['rulebook_ok']} of {run.data['rulebook_total']} grants accepted" in text
    assert "rejected by Client Onboarding, a person, not the AI" in text
    assert "The model is fooled" in text and "The model declined" not in text
    assert all(isinstance(c["anchor"], list) and c["anchor"] for c in cs)


def test_a_resisted_plan_gets_its_own_honest_callout(client):
    client.mock.plan = "resistant"
    run = run_once(client)
    titles = [c["title"] for c in build_replay(run)["callouts"]]
    assert "The model declined" in titles and "The model is fooled" not in titles


def test_replay_travels_with_key_views_and_the_export_without_a_token(client):
    run_once(client)
    data = client.get("/api/keyviews").json()
    assert data["replay"]["total"] <= 90 and data["replay"]["callouts"]
    html = client.get("/api/keyviews/export").text
    m = re.search(r"window\.__REPLAY__ = (\{.*?\});</script>", html, re.S)
    payload = json.loads(m.group(1).replace("<\\/", "</"))
    assert payload["replay"]["callouts"] == data["replay"]["callouts"]
    assert FAKE not in html and FAKE not in json.dumps(data)
    assert "openReplay" in html                                       # the player ships inside the file


def test_replay_makes_no_model_call(client):
    run_once(client)
    before = len(client.mock.calls)
    client.get("/api/keyviews")
    client.get("/api/keyviews/export")
    assert len(client.mock.calls) == before
