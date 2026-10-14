"""HTTP routes. One process: API, SSE stream and the static console. Binds to 127.0.0.1 only (run.py)."""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import app.llm as llm
from app import secrets_store
from app.core.audit import build_pack
from app.demo import acts
from app.demo.director import SPEEDS, Director
from app.demo.keyviews import KeyViews
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


def connection_status() -> dict:
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
    }


@app.get("/api/catalog")
def catalog() -> dict:
    return {"foundry": FOUNDRY_MODELS, "openrouter": OPENROUTER_MODELS, "recommended": RECOMMENDED,
            "defaults": {"provider": "foundry", "project": FOUNDRY_DEFAULT_PROJECT, "base_url": FOUNDRY_BASE_URL},
            "speeds": SPEEDS}


@app.get("/api/connection/status")
def status() -> dict:
    return connection_status()


@app.post("/api/connection/test")
async def test_connection(req: TestRequest) -> dict:
    if req.provider not in ("foundry", "openrouter"):
        raise HTTPException(400, "Provider must be foundry or openrouter.")
    if any(r not in req.models or not req.models[r].strip() for r in llm.ROLES):
        raise HTTPException(400, "Pick a model for both roles.")
    if req.token and req.token.strip():
        secrets_store.set(req.token)
    token = secrets_store.get()
    if not token:
        raise HTTPException(400, "Paste a token first.")
    c = llm.CONNECTION
    c.settings = llm.Settings(provider=req.provider,
                              project=(req.project or FOUNDRY_DEFAULT_PROJECT).strip(),
                              base_url=(req.base_url or FOUNDRY_BASE_URL).strip(),
                              ca_bundle=(req.ca_bundle or "").strip() or None)
    c.models = {r: req.models[r].strip() for r in llm.ROLES}
    c.tests = {}
    results = await asyncio.gather(*(llm.test_model(req.provider, c.models[r], token, c.settings)
                                     for r in llm.ROLES))
    c.tests = dict(zip(llm.ROLES, results))
    return connection_status()


@app.post("/api/connection/token")
def refresh_token(req: TokenRequest) -> dict:
    """Mid-demo: a fresh token after a 401/403. The paused call is retried on resume."""
    if not req.token.strip():
        raise HTTPException(400, "Paste a token.")
    secrets_store.set(req.token)
    return connection_status()


@app.post("/api/connection/forget")
def forget() -> dict:
    secrets_store.clear()
    llm.CONNECTION.tests = {}
    return connection_status()


# --- Demo control ------------------------------------------------------------------------------------

class Control(BaseModel):
    cmd: str
    value: float | None = None


def _require_gate() -> None:
    if not llm.CONNECTION.ready:
        raise HTTPException(409, "Test the connection for both roles first. The demo needs a live model.")


@app.post("/api/demo/start")
async def start() -> dict:
    _require_gate()
    run = await director.start()
    return {"run_id": run.id}


@app.post("/api/demo/control")
async def control(c: Control) -> dict:
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
        await director.start()
    elif c.cmd == "jump" and c.value and 1 <= int(c.value) <= 6:
        await director.jump(int(c.value))
    elif c.cmd == "speed" and c.value in SPEEDS:
        director.set_speed(float(c.value))
    else:
        raise HTTPException(400, f"Unknown command {c.cmd}.")
    return {"ok": True}


@app.post("/api/demo/approve")
def approve() -> dict:
    director.approve()
    return {"ok": True}


@app.post("/api/demo/extra")
async def extra() -> dict:
    if not await director.extra():
        raise HTTPException(409, "The extra scenario runs once, after the close card.")
    return {"ok": True}


@app.get("/api/stream")
async def stream(request: Request) -> StreamingResponse:
    async def gen():
        q = bus.subscribe()
        try:
            yield "retry: 1500\n\n"
            run = director.run
            sent = {}
            if run:
                for ev in list(run.events):
                    sent[ev["run"]] = ev["seq"]
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            while not await request.is_disconnected():
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=10)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if ev["seq"] <= sent.get(ev["run"], 0):
                    continue
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
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
    checks = [c.as_dict() for c in run.data.get("checks", [])]
    verifier = [{"op": c["op"], "target": c["target"], "ok": c["ok"], "reason": c["reason"]} for c in checks]
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
