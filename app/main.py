"""HTTP routes. One process: API, SSE stream and the static console. Binds to 127.0.0.1 only (run.py)."""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import app.llm as llm
from app import secrets_store
from app.core.audit import build_pack
from app.demo import acts
from app.demo.director import SPEEDS, Director
from app.demo.keyviews import KeyViews
from app.demo.preflight import run_preflight
from app.events import Bus
from app.llm.catalog import FOUNDRY_MODELS, OPENROUTER_MODELS, RECOMMENDED, short_name
from app.settings import FOUNDRY_BASE_URL, FOUNDRY_DEFAULT_PROJECT, WEB_DIR, ca_bundle

app = FastAPI(title="Agent governance demo", docs_url=None, redoc_url=None, openapi_url=None)
secrets_store.install_log_filter()
bus = Bus()
keyviews = KeyViews()
director = Director(bus, keyviews)


@app.exception_handler(Exception)
async def plain_errors(_: Request, exc: Exception):
    """Never leak details (or a token) in an unexpected error."""
    return JSONResponse({"error": secrets_store.redact(f"{type(exc).__name__}: {exc}")[:300]}, status_code=500)


# --- Connection gate ---------------------------------------------------------------------------------

class TestRequest(BaseModel):
    provider: str = "foundry"
    token: str | None = None
    project: str | None = None
    models: dict[str, str]
    base_url: str | None = None
    ca_bundle: str | None = None


class TokenRequest(BaseModel):
    token: str


def _test_dict(t) -> dict | None:
    if t is None:
        return None
    return {"ok": t.ok, "model": t.model_ref, "name": short_name(t.model_ref), "latency_ms": t.latency_ms,
            "message": t.message, "variant": t.variant}


def _switch_options(role: str) -> list[dict]:
    """Models the pause card can switch a role to: every model that passed a live test this session first,
    then the catalogue's JSON-mode models (tested live before use)."""
    c = llm.CONNECTION
    out = [{"ref": ref, "name": short_name(ref), "tested": True, "latency_ms": t.latency_ms}
           for ref, t in c.tested.items() if t.ok and ref != c.models.get(role)]
    if c.settings.provider == "foundry":
        for m in FOUNDRY_MODELS:
            if m["family"] in ("azure", "openai") and m["ref"] not in c.tested and m["ref"] != c.models.get(role) \
                    and not m["ref"].split(":")[1].startswith(("o1", "gpt-5")):
                out.append({"ref": m["ref"], "name": short_name(m["ref"]), "tested": False})
    return out[:8]


def connection_status(console: str | None = None) -> dict:
    c = llm.CONNECTION
    run = director.run
    return {
        "provider": c.settings.provider,
        "token": secrets_store.masked(),
        "project": c.settings.project,
        "base_url": c.settings.base_url,
        "ca_bundle": c.settings.ca_bundle or ca_bundle(),
        "models": c.models,
        "tests": {r: _test_dict(c.tests.get(r)) for r in llm.ROLES},
        "ready": c.ready,
        "run": {"active": bool(run and not run.done), "exists": run is not None, "act": run.act if run else 0,
                "done": bool(run and run.done), "closed": bool(run and run.closed)},
        "keyviews": keyviews.available,
        "switch": {r: _switch_options(r) for r in llm.ROLES},
        "preflight": c.preflight,
        "controller": {"set": director.controller is not None,
                       "you": console is not None and director.controller == console},
    }


@app.get("/api/catalog")
def catalog() -> dict:
    return {"foundry": FOUNDRY_MODELS, "openrouter": OPENROUTER_MODELS, "recommended": RECOMMENDED,
            "defaults": {"provider": "foundry", "project": FOUNDRY_DEFAULT_PROJECT, "base_url": FOUNDRY_BASE_URL},
            "speeds": SPEEDS}


@app.get("/api/connection/status")
def status(x_console_id: str | None = Header(default=None)) -> dict:
    return connection_status(_console(x_console_id))


@app.post("/api/connection/test")
async def test_connection(req: TestRequest, x_console_id: str | None = Header(default=None)) -> dict:
    if req.provider not in ("foundry", "openrouter"):
        raise HTTPException(400, "Provider must be foundry or openrouter.")
    if any(r not in req.models or not req.models[r].strip() for r in llm.ROLES):
        raise HTTPException(400, "Pick a model for both roles.")
    c = llm.CONNECTION
    try:
        project = secrets_store.clean(req.project, secrets_store.SUFFIX_NOT_SENDABLE) or FOUNDRY_DEFAULT_PROJECT
        if req.token and not secrets_store.is_masked_echo(req.token) and secrets_store.clean(req.token):
            secrets_store.set(req.token)
            c.tested, c.preflight = {}, None          # earlier tests proved a different token
    except ValueError as e:                  # a stray character pasted: say so plainly, never a 500
        raise HTTPException(400, str(e)) from None
    token = secrets_store.get()
    if not token:
        raise HTTPException(400, "Paste a token first.")
    if c.settings.provider != req.provider:
        c.tested, c.preflight = {}, None
    c.settings = llm.Settings(provider=req.provider,
                              project=project,
                              base_url=(req.base_url or FOUNDRY_BASE_URL).strip(),
                              ca_bundle=(req.ca_bundle or "").strip() or None)
    c.models = {r: req.models[r].strip() for r in llm.ROLES}
    c.tests = {}
    results = await asyncio.gather(*(llm.test_model(req.provider, c.models[r], token, c.settings)
                                     for r in llm.ROLES))
    c.tests = dict(zip(llm.ROLES, results))
    c.tested.update({t.model_ref: t for t in results})
    return connection_status(_console(x_console_id))


@app.post("/api/connection/token")
def refresh_token(req: TokenRequest) -> dict:
    """Mid-demo: a fresh token after a 401/403. The paused call is retried on resume."""
    try:
        if secrets_store.is_masked_echo(req.token) or not secrets_store.clean(req.token):
            raise HTTPException(400, "Paste a fresh token.")
        secrets_store.set(req.token)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return connection_status()


@app.post("/api/connection/forget")
def forget() -> dict:
    secrets_store.clear()
    llm.CONNECTION.tests, llm.CONNECTION.tested, llm.CONNECTION.preflight = {}, {}, None
    return connection_status()


# --- Demo control ------------------------------------------------------------------------------------
#
# One director, one controlling tab. The tab that starts a run controls it; any other tab is a read-only
# viewer until the presenter clicks "Take control" there. A double-clicked Start is one run.

class Control(BaseModel):
    cmd: str
    value: float | None = None


class SwitchRequest(BaseModel):
    role: str
    model: str


_start_lock = asyncio.Lock()


def _console(header: str | None) -> str:
    return (header or "default").strip()[:64] or "default"


def _require_gate() -> None:
    if not llm.CONNECTION.ready:
        raise HTTPException(409, "Test the connection for both roles first. The demo needs a live model.")


def _require_controller(console: str) -> None:
    if director.controller is not None and director.controller != console:
        raise HTTPException(403, "This tab is a viewer. Use Take control to drive the demo from here.")


def _active() -> bool:
    run = director.run
    return bool(run and not run.done and director.task and not director.task.done())


@app.post("/api/demo/start")
async def start(x_console_id: str | None = Header(default=None)) -> dict:
    _require_gate()
    console = _console(x_console_id)
    async with _start_lock:
        run = director.run
        if _active():
            if director.controller != console:
                raise HTTPException(409, "A run is already playing in another tab. This tab is a viewer: "
                                         "use Take control to drive it.")
            if time.monotonic() - director.started_mono < 3:      # a double click: the same run
                return {"run_id": run.id}
        director.controller = console
        run = await director.start(fresh=True)
    return {"run_id": run.id}


@app.post("/api/demo/take_control")
def take_control(x_console_id: str | None = Header(default=None)) -> dict:
    director.controller = _console(x_console_id)
    return connection_status(director.controller)


@app.post("/api/demo/control")
async def control(c: Control, x_console_id: str | None = Header(default=None)) -> dict:
    _require_controller(_console(x_console_id))
    if c.cmd in ("restart", "jump"):
        _require_gate()
    if director.run is None and c.cmd != "speed":
        raise HTTPException(409, "No run yet.")
    if c.cmd == "pause":
        director.pause("presenter")
    elif c.cmd == "resume":
        director.resume()
    elif c.cmd == "next":
        director.next_step()
    elif c.cmd == "restart":
        async with _start_lock:
            await director.start()
    elif c.cmd == "jump" and c.value and 1 <= int(c.value) <= 6:
        await director.jump(int(c.value))
    elif c.cmd == "speed" and c.value in SPEEDS:
        director.set_speed(float(c.value))
    elif c.cmd in ("retry", "wait"):
        if not director.retry(c.cmd):
            raise HTTPException(409, "Nothing to retry.")
    else:
        raise HTTPException(400, f"Unknown command {c.cmd}.")
    return {"ok": True}


@app.post("/api/demo/switch_model")
async def switch_model(req: SwitchRequest, x_console_id: str | None = Header(default=None)) -> dict:
    """Pause card: switch a role's model. A model not yet tested this session gets a live test first."""
    _require_controller(_console(x_console_id))
    if req.role not in llm.ROLES:
        raise HTTPException(400, "Unknown role.")
    c = llm.CONNECTION
    token = secrets_store.get()
    if not token:
        raise HTTPException(400, "Paste a token first.")
    t = c.tested.get(req.model)
    if t is None or not t.ok:
        t = await llm.test_model(c.settings.provider, req.model, token, c.settings)
        c.tested[req.model] = t
    if not t.ok:
        raise HTTPException(400, f"{short_name(req.model)} failed its live test: {t.message}")
    c.models[req.role] = req.model
    c.tests[req.role] = t
    director.switch_model(req.role, req.model)
    return connection_status(_console(x_console_id))


@app.post("/api/demo/approve")
def approve(x_console_id: str | None = Header(default=None)) -> dict:
    _require_controller(_console(x_console_id))
    director.approve()
    return {"ok": True}


@app.post("/api/demo/extra")
async def extra(x_console_id: str | None = Header(default=None)) -> dict:
    _require_controller(_console(x_console_id))
    if not await director.extra():
        raise HTTPException(409, "The extra scenario runs once, after the close card.")
    return {"ok": True}


@app.post("/api/connection/preflight")
async def preflight() -> dict:
    """Optional, on the gate: each of the four real contracts once, with the real prompts. Memory only."""
    _require_gate()
    if _active():
        raise HTTPException(409, "Preflight runs from the connection screen, not during a run.")
    llm.CONNECTION.preflight = await run_preflight()
    return connection_status()


@app.get("/api/stream")
async def stream(request: Request) -> StreamingResponse:
    async def gen():
        q = bus.subscribe()
        try:
            yield "retry: 1500\n\n"
            run = director.run
            sent = {}
            if run:
                for ev in list(run.events):          # a (re)connecting tab resyncs from the run's log
                    sent[ev["run"]] = ev["seq"]
                    yield f"id: {ev['seq']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            while not await request.is_disconnected():
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=10)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if ev["seq"] <= sent.get(ev["run"], 0):
                    continue
                yield f"id: {ev['seq']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --- Evidence pack -------------------------------------------------------------------------------------

def _pack() -> tuple[str, dict]:
    run = director.run
    if run is None or "metrics" not in run.data:
        raise HTTPException(404, "The evidence pack is available once the run reaches Act 6.")
    w = run.world
    meta = {"run_id": run.id, "recorded_at": run.started_at.isoformat(timespec="seconds"),
            "agent_model": run.models["agent"], "investigator_model": run.models["investigator"],
            "plan_source": run.data.get("plan_source"), "estate": "Kaiyo Securities (synthetic)"}
    timeline = [{"seq": e["seq"], "t": e["t"], "act": e["act"], "kind": e["kind"],
                 "summary": e["payload"].get("text") or e["payload"].get("capability") or e["payload"].get("title")}
                for e in run.events if e["kind"] in ("act", "caption", "decision", "call", "keyview")]
    verifier = [{"stage": "day-zero rulebook", "op": l.kind, "target": f"{l.agent} {l.capability}", "ok": l.ok,
                 "reason": l.reason} for l in run.data.get("rulebook_lines", [])]
    verifier += [{"stage": "hardening", "op": c["op"], "target": c["target"], "ok": c["ok"], "reason": c["reason"]}
                 for c in (c.as_dict() for c in run.data.get("checks", []))]
    delegation = []
    for e in run.events:
        if e["kind"] == "panel" and e["payload"]["view"] == "attack" and e["payload"]["set"].get("intersection"):
            delegation = e["payload"]["set"]["intersection"]["rows"]
    return build_pack(meta, acts.metrics(director), w.audit.records, timeline, w.policy.history, verifier, delegation)


@app.get("/api/evidence.md")
def evidence_md() -> PlainTextResponse:
    md, _ = _pack()
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="evidence-pack.md"'})


@app.get("/api/evidence.json")
def evidence_json() -> Response:
    _, data = _pack()
    return Response(json.dumps(data, indent=1, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="evidence-pack.json"'})


# --- Key views -------------------------------------------------------------------------------------------

@app.get("/api/keyviews")
def keyviews_list() -> dict:
    if not keyviews.available:
        raise HTTPException(404, "Key views exist once a live run reaches the close card.")
    return keyviews.listing()


@app.get("/api/keyviews/export")
def keyviews_export() -> Response:
    if not keyviews.available:
        raise HTTPException(404, "Key views exist once a live run reaches the close card.")
    name, html = keyviews.export_html()
    return Response(html, media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
