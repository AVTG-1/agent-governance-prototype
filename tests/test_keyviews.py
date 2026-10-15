"""Key views (SPEC §5.8): eight markers, instant replay with no model calls, an offline token-free export."""
import json
import re

from app.demo.script import KEY_VIEWS
from tests.conftest import pass_gate, wait_done

FAKE = "fake-KVCHECK-" + __import__("secrets").token_hex(10)

EXPECTED_VIEW = {   # key view id -> (act, panel view, stage or None)
    "estate-found": (1, "registry", None), "watch-before-blocking": (2, "shadow", None),
    "rulebook": (2, "rulebook", "approved"), "two-minutes": (3, "enforce", None), "today": (4, "attack", "today"),
    "system-held": (4, "attack", "governed"), "ai-explains": (4, "attack", "case"), "measured": (6, "evidence", None),
}


def run_once(client):
    pass_gate(client, fake=FAKE)
    client.post("/api/demo/start")
    wait_done(client)
    import app.main as main
    return main.director.run


def test_404_before_any_run_reaches_act6(client):
    assert client.get("/api/keyviews").status_code == 404
    assert client.get("/api/keyviews/export").status_code == 404


def test_eight_markers_in_order_and_each_shows_its_panel(client):
    run_once(client)
    data = client.get("/api/keyviews").json()
    views = data["views"]
    assert [v["id"] for v in views] == [k["id"] for k in KEY_VIEWS]
    assert [v["n"] for v in views] == list(range(1, 9))
    assert all(len(v["ts"]) >= 16 for v in views)
    # Fold panel state up to each marker, as the console does, and check what it would show.
    for v in views:
        upto = [e for e in data["events"] if e["seq"] <= v["seq"]]
        view, panels, act = None, {}, 0
        for e in upto:
            if e["kind"] == "act":
                act = e["payload"]["act"]
            if e["kind"] == "panel":
                p = e["payload"]
                panels.setdefault(p["view"], {}).update(p["set"])
                if p.get("show", True):
                    view = p["view"]
        want_act, want_view, want_stage = EXPECTED_VIEW[v["id"]]
        assert (act, view) == (want_act, want_view), v["id"]
        if want_stage:
            assert panels[view].get("stage") == want_stage, v["id"]
    # View 4 holds the envelope with its time remaining at that moment.
    four = [e for e in data["events"] if e["seq"] <= views[3]["seq"] and e["kind"] == "panel"
            and e["payload"]["set"].get("envelope")]
    assert four[-1]["payload"]["set"]["envelope"]["remaining"] == 120
    # View 3 carries the verified rulebook lines, the replay, the owner's rejection and the version bump.
    three = [e["payload"] for e in data["events"] if e["seq"] <= views[2]["seq"] and e["kind"] == "panel"
             and e["payload"]["view"] == "rulebook"]
    assert sum(1 for p in three if p["push"].get("lines")) == 22
    assert any(p["set"].get("version", {}) and p["set"]["version"]["after"] == "rulebook@v1" for p in three)
    assert any(p["set"].get("replay") and p["set"]["replay"]["legit_broken"] == 0
               and p["set"]["replay"]["violations_stopped"] == 7 for p in three)
    assert any(p["set"].get("decisions") and p["set"]["decisions"][0]["capability"] == "fileshare.export" for p in three)


def test_listing_and_export_make_no_model_calls_and_no_decisions(client):
    run = run_once(client)
    calls, events, records = len(client.mock.calls), len(run.events), len(run.world.audit.records)
    for _ in range(3):
        assert client.get("/api/keyviews").status_code == 200
        assert client.get("/api/keyviews/export").status_code == 200
    assert len(client.mock.calls) == calls
    assert len(run.events) == events and len(run.world.audit.records) == records


def test_export_is_offline_token_free_and_labelled(client):
    run_once(client)
    r = client.get("/api/keyviews/export")
    html = r.text
    assert re.match(r'attachment; filename="key-views-\d{8}-\d{4}\.html"', r.headers["content-disposition"])
    assert FAKE not in html and FAKE[-10:] not in html
    assert "playback only" in html and "Recorded from a live run" in html
    assert "window.__REPLAY__" in html and "data:font/woff;base64," in html
    # No network assets of any kind.
    assert not re.search(r'(src|href)\s*=\s*["\']?https?://', html, re.I)
    assert not re.search(r"url\(\s*['\"]?https?://", html, re.I)
    assert "@import" not in html and 'src="app.js"' not in html and 'href="styles.css"' not in html
    # No gate, provider settings, prompts or auth material.
    assert 'id="g-token"' not in html and "llmfoundry" not in html and "llmproxy-playground" not in html
    assert "ReconBot" not in html and "Bearer" not in html and "EventSource('/api" in html   # code present, never run
    replay = json.loads(re.search(r"window.__REPLAY__ = (\{.*?\});</script>", html, re.S).group(1).replace("<\\/", "</"))
    assert replay["meta"]["agent_model"] == "azure:gpt-4.1-mini"
    assert sum(1 for e in replay["events"] if e["kind"] == "keyview") == 8


def test_key_views_survive_restart_until_next_completed_run(client):
    first = run_once(client)
    import app.main as main
    assert client.get("/api/keyviews").json()["meta"]["run_id"] == first.id
    main.director.instant = False
    client.post("/api/demo/control", json={"cmd": "restart"})
    assert client.get("/api/keyviews").json()["meta"]["run_id"] == first.id    # old recording still there
    main.director.instant = True
    client.post("/api/demo/control", json={"cmd": "restart"})
    wait_done(client)
    assert client.get("/api/keyviews").json()["meta"]["run_id"] == main.director.run.id
