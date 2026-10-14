"""The demo director: plays script.py on a scripted clock with pause, next, jump, restart and speed.

Scripted time (`t`) advances only while playing, scaled by speed, and never while waiting for a
model. So the story is 300 scripted seconds; real time is 300 / speed plus any model wait that
prefetching didn't hide. LLM calls are prefetched as background tasks. If a needed result isn't
ready the console shows "waiting for model"; after the timeout, or on any error, the director
pauses and says why. It never invents output.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime

from app.core.world import World
from app.demo import acts
from app.core.policies import PLAIN, RULE_PLAIN
from app.demo.script import ACTS, END, EXTRA_ACT, INTRO_S, KEY_VIEW_BY_ID, STEPS, Step
from app.estate.systems import AGENT_NAMES, AREAS
from app.events import Bus
from app.llm import CONNECTION, LLMError
from app.llm.catalog import short_name

SPEEDS = (0.5, 1.0, 2.0)
ROLE_OF = {"rulebook": "investigator", "plan": "agent", "case": "investigator", "diff": "investigator"}
JOB_LABEL = {"rulebook": "rulebook draft", "plan": "agent plan", "case": "incident case", "diff": "hardening"}
NEEDED_AT = {s.wait_for: s.abs_at for s in STEPS if s.wait_for}       # scripted second each result is needed


def mmss(t: float) -> str:
    return f"{int(t) // 60}:{int(t) % 60:02d}"


class Run:
    """Everything about one play-through. Restart makes a new one."""

    def __init__(self, run_id: str) -> None:
        self.id = run_id
        self.started_at = datetime.now().astimezone()
        self.t = 0.0
        self.act = 0
        self.step_index = -1
        self.events: list[dict] = []
        self.world = World(now=lambda: self.t)
        self.llm: dict[str, asyncio.Task] = {}
        self.data: dict = {}               # what acts compute and later acts read (plan, case, metrics...)
        self.closed = False
        self.done = False
        self.extra_running = False
        self.models = dict(CONNECTION.models)
        self.provider = CONNECTION.settings.provider
        self.failed: dict | None = None    # the model call the run is paused on, if any


class Director:
    def __init__(self, bus: Bus, keyviews=None) -> None:
        self.bus = bus
        self.keyviews = keyviews
        self.run: Run | None = None
        self.task: asyncio.Task | None = None
        self.speed = 1.0
        self.instant = False                # tests only: every sleep returns at once
        self.paused = False
        self._resume = asyncio.Event()
        self._resume.set()
        self._skip_to_step: int | None = None
        self._skip_to_act: int | None = None
        self.approval = asyncio.Event()
        self._runs = 0
        self.controller: str | None = None     # the console tab that drives the run (main.py)
        self.started_mono = 0.0

    # --- events ----------------------------------------------------------------------------

    def emit(self, kind: str, payload: dict, *, prev_hash: str | None = None, hash: str | None = None,
             run: Run | None = None) -> dict | None:
        """Append to the current run's log and publish. An emit on behalf of an older run (a late model
        reply after a restart) is dropped: every event belongs to exactly one run."""
        if run is not None and run is not self.run:
            return None
        run = self.run
        ev = {"run": run.id, "seq": len(run.events) + 1, "t": round(run.t, 2), "act": run.act, "kind": kind,
              "payload": payload, "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
              "prev_hash": prev_hash, "hash": hash}
        run.events.append(ev)
        self.bus.publish(ev)
        return ev

    def caption(self, text: str) -> None:
        self.emit("caption", {"text": text})

    def panel(self, view: str, show: bool = True, push: dict | None = None, **set_) -> None:
        self.emit("panel", {"view": view, "show": show, "set": set_, "push": push or {}})

    # --- lifecycle ---------------------------------------------------------------------------

    async def start(self, jump_to_act: int | None = None, fresh: bool = False) -> Run:
        """fresh: a Start from the gate. A live run starts at 1x; a restart keeps the presenter's speed."""
        await self.stop()
        if fresh:
            self.speed = 1.0
        self._runs += 1
        self.run = Run(f"run-{self._runs}-{int(time.time())}")
        self.started_mono = time.monotonic()
        self.paused = False
        self._resume.set()
        self._skip_to_step = None
        self._skip_to_act = jump_to_act if jump_to_act and jump_to_act > 1 else None
        self.approval = asyncio.Event()
        self.emit("run", {"run_id": self.run.id, "started_at": self.run.started_at.isoformat(timespec="seconds"),
                          "provider": self.run.provider,
                          "models": {r: short_name(m) for r, m in self.run.models.items()},
                          "speed": self.speed, "acts": {k: {"title": v["title"], "gist": v["gist"]} for k, v in ACTS.items()},
                          "end": END, "needed_at": NEEDED_AT, "jobs": JOB_LABEL,
                          "labels": {"capabilities": PLAIN, "rules": RULE_PLAIN, "agents": AGENT_NAMES, "areas": AREAS}})
        for job, at in NEEDED_AT.items():
            self.emit("llm", {"job": job, "role": ROLE_OF[job], "status": "pending", "needed_at": at,
                              "model": short_name(self.run.models[ROLE_OF[job]])})
        acts.prefetch_rulebook(self)          # fixtures are deterministic, so the day-zero draft can go out now
        self.task = asyncio.create_task(self._play())
        return self.run

    async def stop(self) -> None:
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 - a cancelled run has nothing to report
                pass
        if self.run:
            for t in self.run.llm.values():
                t.cancel()
            self.run.failed = None
        self.paused = False
        self._resume.set()

    async def _play(self) -> None:
        run = self.run
        try:
            for i, step in enumerate(STEPS):
                if step.act != run.act:
                    await self.sleep_until(ACTS[step.act]["start"])
                    if self._skip_to_act is not None and step.act >= self._skip_to_act:
                        self._skip_to_act = None
                    run.act = step.act
                    meta = ACTS[step.act]
                    self.emit("act", {"act": step.act, "title": meta["title"], "gist": meta["gist"],
                                      "deck": meta["deck"], "sub": meta["sub"], "intro": True})
                    await self.sleep(INTRO_S)
                    self.emit("system", {"intro": False})
                await self.sleep_until(step.abs_at)
                run.step_index = i
                if self._skip_to_step is not None and i >= self._skip_to_step:
                    self._skip_to_step = None
                if self._skip_to_act is not None and step.act >= self._skip_to_act:
                    self._skip_to_act = None
                if step.deck:
                    self.emit("system", {"deck": step.deck})
                if step.wait_for:
                    await self.wait_llm(step.wait_for, step.timeout_s, step.abs_at)
                text = acts.override_caption(self, step) or step.caption
                if text:
                    self.caption(text)
                await getattr(acts, step.action)(self, step)
                if step.keyview:
                    self.emit("keyview", KEY_VIEW_BY_ID[step.keyview])
            await self.sleep_until(END)
            run.done = True
            self.emit("system", {"done": True})
            if self.keyviews:
                self.keyviews.save(run)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - show any failure plainly instead of dying silently
            self.emit("error", {"kind": "internal", "message": f"Demo stopped: {type(e).__name__}: {e}"})
            raise

    # --- the scripted clock ------------------------------------------------------------------

    def _skipping(self) -> bool:
        return self.instant or self._skip_to_step is not None or self._skip_to_act is not None

    async def sleep(self, dt: float) -> None:
        await self.sleep_until(self.run.t + dt)

    async def sleep_until(self, target: float) -> None:
        run = self.run
        loop = asyncio.get_running_loop()
        while run.t < target - 1e-6:
            if self._skipping():
                run.t = target
                return
            if self.paused:
                await self._resume.wait()
                continue
            t0 = loop.time()
            await asyncio.sleep(min(0.05, (target - run.t) / self.speed))
            if not self.paused and not self._skipping():
                run.t = min(target, run.t + (loop.time() - t0) * self.speed)

    # --- controls ----------------------------------------------------------------------------

    def pause(self, reason: str | None = None) -> None:
        if self.run and not self.paused:
            self.paused = True
            self._resume.clear()
            self.emit("system", {"paused": True, "reason": reason})

    def resume(self) -> None:
        if self.run and self.run.failed and not self.run.failed.get("action"):
            self.run.failed["action"] = "retry"          # Space on the pause card re-sends the call
        if self.run and self.paused:
            self.paused = False
            self._resume.set()
            self.emit("system", {"paused": False})

    def next_step(self) -> None:
        if self.run and not self.run.done:
            self._skip_to_step = self.run.step_index + 1
            self.resume()

    async def jump(self, act: int) -> None:
        run = self.run
        if run is None or run.done or act <= run.act:
            await self.start(jump_to_act=act)
        else:
            self._skip_to_act = act
            self.resume()

    def set_speed(self, speed: float) -> None:
        if speed in SPEEDS:
            self.speed = speed
            if self.run:
                self.emit("system", {"speed": speed})

    def approve(self) -> None:
        self.approval.set()

    # --- LLM prefetch and waits --------------------------------------------------------------

    def prefetch(self, key: str, coro_factory, run: Run | None = None) -> None:
        """Start an LLM call in the background (once per run). The task belongs to that run: if the run is
        restarted, the task is cancelled and anything it returns late is dropped."""
        run = run or self.run
        if run is not self.run or (key in run.llm and not run.llm[key].cancelled()):
            return
        run.data[f"{key}_factory"] = coro_factory
        self.emit("llm", {"role": ROLE_OF[key], "job": key, "status": "requested", "needed_at": NEEDED_AT.get(key),
                          "model": short_name(run.models[ROLE_OF[key]])}, run=run)
        run.llm[key] = asyncio.create_task(self._timed(run, key, coro_factory))

    async def _timed(self, run: Run, key: str, coro_factory):
        t0 = time.perf_counter()
        role = ROLE_OF[key]
        try:
            result = await coro_factory()
        except LLMError as e:
            self.emit("llm", {"role": role, "job": key, "status": "failed", "needed_at": NEEDED_AT.get(key),
                              "model": short_name(run.models[role]), "message": e.message}, run=run)
            raise
        if run is not self.run:                 # a late reply for a run that was restarted: dropped
            return result
        run.data[f"{key}_latency_ms"] = round((time.perf_counter() - t0) * 1000)
        self.emit("llm", {"role": role, "job": key, "status": "ready", "needed_at": NEEDED_AT.get(key),
                          "model": short_name(run.models[role]), "latency_ms": run.data[f"{key}_latency_ms"]}, run=run)
        return result

    async def wait_llm(self, key: str, timeout_s: float, needed_at: float | None = None):
        """Wait for a prefetched result while the scripted clock holds. On a timeout or an error the director
        pauses and the console offers Retry (re-send this call), Switch model, or Restart. It never continues
        without a real result."""
        run = self.run
        role = ROLE_OF[key]
        while True:
            task = run.llm.get(key)
            if task is None:
                raise RuntimeError(f"LLM job {key} was never started")
            if not task.done():
                self.emit("system", {"waiting": role, "job": key})
            failure = None
            try:
                result = await asyncio.wait_for(asyncio.shield(task), timeout=timeout_s)
                self.emit("system", {"waiting": None})
                self.emit("llm", {"role": role, "job": key, "status": "used", "needed_at": NEEDED_AT.get(key),
                                  "model": short_name(run.models[role]),
                                  "latency_ms": run.data.get(f"{key}_latency_ms")})
                return result
            except asyncio.TimeoutError:
                failure = {"kind": "timeout", "message": f"No reply from the {role} model in {timeout_s:.0f} s. "
                                                         "Check VPN or proxy, then retry or keep waiting."}
            except LLMError as e:
                failure = {"kind": e.kind, "message": e.message, "need_token": e.kind == "auth"}
            self.emit("system", {"waiting": None})
            run.failed = {**failure, "job": key, "role": role, "label": JOB_LABEL[key],
                          "model": run.models[role], "model_name": short_name(run.models[role]),
                          "needed_at": mmss(needed_at if needed_at is not None else run.t), "action": None}
            self.emit("error", {k: v for k, v in run.failed.items() if k != "action"})
            self.pause(f"{role} model")
            await self._resume.wait()
            action = run.failed.get("action") or "retry"
            run.failed = None
            self.emit("error", {"kind": None, "message": None})
            if action == "wait" and failure["kind"] == "timeout" and not task.done():
                continue
            if not task.done():
                task.cancel()
            self.emit("llm", {"role": role, "job": key, "status": "requested", "needed_at": NEEDED_AT.get(key),
                              "model": short_name(run.models[role])})
            run.llm[key] = asyncio.create_task(self._timed(run, key, run.data[f"{key}_factory"]))

    def retry(self, action: str = "retry") -> bool:
        """The pause card's Retry / Keep waiting: re-send the failed call (or keep waiting) and carry on."""
        run = self.run
        if run is None or run.failed is None:
            return False
        run.failed["action"] = action
        self.resume()
        return True

    def switch_model(self, role: str, model_ref: str) -> bool:
        """The pause card's Switch model: later calls for this role use the new (already tested) model,
        and the failed call is re-sent with it."""
        run = self.run
        if run is None:
            return False
        run.models[role] = model_ref
        self.emit("system", {"models": {r: short_name(m) for r, m in run.models.items()}})
        for job, r in ROLE_OF.items():
            if r == role and run.llm.get(job) is None:
                self.emit("llm", {"job": job, "role": role, "status": "pending", "needed_at": NEEDED_AT.get(job),
                                  "model": short_name(model_ref)})
        return self.retry() if run.failed else True

    # --- extra scenario (after the close) ----------------------------------------------------

    async def extra(self) -> bool:
        run = self.run
        if run is None or not run.done or run.extra_running:
            return False
        run.extra_running = True
        run.act = EXTRA_ACT
        self.emit("act", {"act": EXTRA_ACT, "title": "Extra: malfunction"})
        self.task = asyncio.create_task(acts.extra_malfunction(self))
        return True
