"""The token appears in no response, event, log line, export or file. It lives only in process memory."""
import json
import logging
from pathlib import Path

from tests.conftest import pass_gate, wait_done

FAKE = "fake-LEAKCHECK-" + __import__("secrets").token_hex(10)   # generated per run, so no file holds it
ROOT = Path(__file__).resolve().parents[1]


def test_token_never_leaves_memory(client, caplog):
    caplog.set_level(logging.DEBUG)
    bodies = []
    bodies.append(pass_gate(client, token=FAKE).text)
    bodies.append(client.get("/api/connection/status").text)
    bodies.append(client.get("/api/catalog").text)
    bodies.append(client.post("/api/demo/start").text)
    wait_done(client)
    import app.main as main
    events = json.dumps(main.director.run.events)
    bodies += [events, client.get("/api/evidence.md").text, client.get("/api/evidence.json").text,
               client.get("/api/keyviews").text, client.get("/api/keyviews/export").text]
    bodies.append(sse_snapshot(main))
    for b in bodies:
        assert FAKE not in b
        assert FAKE[-12:] not in b
    assert "••••" in bodies[1] and FAKE[-4:] in bodies[1]        # masked: last 4 at most
    assert FAKE not in caplog.text
    # Nothing on disk: no file in the repository contains the token.
    for p in ROOT.rglob("*"):
        if p.is_file() and ".git" not in p.parts and ".venv" not in p.parts and p.stat().st_size < 5_000_000:
            assert FAKE.encode() not in p.read_bytes(), p


def sse_snapshot(main) -> str:
    """Everything the SSE stream sends a newly connected browser (the run so far), without a live socket."""
    import asyncio

    class FakeRequest:
        async def is_disconnected(self):
            return True

    async def collect():
        resp = await main.stream(FakeRequest())
        return "".join([chunk async for chunk in resp.body_iterator])
    text = asyncio.run(collect())
    assert text.count("data: ") == len(main.director.run.events)
    return text


def test_errors_are_redacted(client):
    from app import secrets_store
    from app.llm import LLMError
    secrets_store.set(FAKE)
    e = LLMError("http", f"500: upstream echoed {FAKE}")
    assert FAKE not in e.message and FAKE not in str(e)


def test_401_mid_demo_pauses_and_asks_for_a_fresh_token(client):
    pass_gate(client, token=FAKE)
    client.mock.fail_role = "case"
    client.mock.fail_kind = "once"
    client.post("/api/demo/start")
    import time
    import app.main as main
    d = main.director
    t0 = time.time()
    while not d.paused and time.time() - t0 < 10:
        time.sleep(0.05)
    assert d.paused
    errors = [e["payload"] for e in d.run.events if e["kind"] == "error" and e["payload"].get("message")]
    assert errors[-1]["need_token"] is True and "Paste a fresh token" in errors[-1]["message"]
    assert client.post("/api/connection/token", json={"token": FAKE + "-new"}).status_code == 200
    client.post("/api/demo/control", json={"cmd": "resume"})
    wait_done(client)
    assert d.run.data["case"].suspected_cause == "prompt_injection"
    assert FAKE not in json.dumps(d.run.events)
