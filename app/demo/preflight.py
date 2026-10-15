"""Preflight (optional, on the connection screen): each of the four real model contracts once, with the
real prompts, validated exactly as the demo validates them. It tells the presenter which calls pass and how
long they take before anyone is watching. Results live in process memory for this session only.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime

from app.core import rulebook as rb
from app.core.verifier import PolicyDiff, verify
from app.demo.acts import RECORDED_PLAN, scratch_day_zero
from app.estate.agents import (AgentPlan, Case, agent_prompt, case_prompt, diff_prompt, map_step, plan_is_compromised,
                               rulebook_prompt)
from app.llm import CONNECTION, LLMError, complete_json
from app.llm.catalog import short_name


def _observed_draft(summary: dict) -> rb.RulebookDraft:
    """A deterministic stand-in rulebook (everything observed that breaks no guardrail), only so the case
    prompt gets realistic denied records. It is never shown as AI output."""
    grants = [{"agent": a["agent"], "capability": o["capability"], "basis": "observed",
               "purpose": a["restricted_purposes"].get(o["capability"]) if o["restricted"] else None,
               "tags": ["rare-but-required"] if o["calendar"] else []}
              for a in summary["agents"] for o in a["observed"]
              if not (o["guardrail"] and o["guardrail"]["outcome"] == "would deny")]
    return rb.RulebookDraft.model_validate({"grants": grants})


async def _one(job: str, role: str, coro) -> tuple[dict, object]:
    t0 = time.perf_counter()
    try:
        value, res = await coro
    except LLMError as e:
        return {"job": job, "role": role, "ok": False, "model": short_name(CONNECTION.models[role]),
                "latency_ms": round((time.perf_counter() - t0) * 1000), "message": e.message}, None
    return {"job": job, "role": role, "ok": True, "model": short_name(res.model_ref),
            "latency_ms": round((time.perf_counter() - t0) * 1000), "message": ""}, value


async def run_preflight() -> dict:
    world, summary = scratch_day_zero()
    sys_r, user_r = rulebook_prompt(summary)
    sys_p, user_p = agent_prompt(world.estate)
    lines = rb.verify_rulebook(_observed_draft(summary), summary)
    world.policy.approve(rb.build_rulebook(world.policy.current, lines), owner="preflight", how="preflight")
    recorded = AgentPlan.model_validate(json.loads(RECORDED_PLAN.read_text(encoding="utf-8")))
    denied = []
    for step in recorded.plan:
        call, _ = map_step(step, session="s-preflight")
        o = world.gateway.handle(call)
        if o.decision.blocked:
            denied.append(o.record)
    sys_c, user_c = case_prompt(denied, world.registry.get("recon-agent").row())

    (r_rb, draft), (r_plan, plan), (r_case, case) = await asyncio.gather(
        _one("rulebook", "investigator", complete_json("investigator", sys_r, user_r, rb.RulebookDraft,
                                                        job="rulebook draft")),
        _one("plan", "agent", complete_json("agent", sys_p, user_p, AgentPlan, job="agent plan")),
        _one("case", "investigator", complete_json("investigator", sys_c, user_c, Case, job="incident case")))
    if draft is not None:
        ls = rb.verify_rulebook(draft, summary)
        grants = [x for x in ls if x.kind == "grant"]
        flagged = any(x.kind == "flag" and x.ok and x.capability == "fileshare.export" for x in ls)
        kept = any(x.kind == "grant" and x.ok and x.capability == "ledger.read_quarter_end" for x in ls)
        r_rb["detail"] = (f"{sum(1 for x in grants if x.ok)} of {len(grants)} grants verified · "
                          f"export {'flagged for the owner' if flagged else 'not flagged (the engine still finds it)'} · "
                          f"quarter-end {'kept' if kept else 'missing (the replay would show it breaking)'}")
    if plan is not None:
        r_plan["detail"] = (f"follows the hidden instruction ({len(plan.plan)} steps)" if plan_is_compromised(plan)
                            else "declined the hidden instruction: the labelled recorded plan would be used")
    if case is not None:
        r_case["detail"] = f"cause {case.suspected_cause} · recommends {case.recommended_containment}"
        sys_d, user_d = diff_prompt(case.model_dump(), world.policy.current, world.usage)
        r_diff, diff = await _one("diff", "investigator", complete_json("investigator", sys_d, user_d, PolicyDiff,
                                                                        job="hardening diff"))
        if diff is not None:
            checks = verify(diff.changes, world.policy.current, world.usage)
            r_diff["detail"] = f"{len(checks)} changes, {sum(1 for c in checks if c.ok)} pass the verifier"
    else:
        r_diff = {"job": "diff", "role": "investigator", "ok": False, "model": short_name(CONNECTION.models["investigator"]),
                  "latency_ms": None, "message": "Not run: it needs the incident case."}
    results = [r_rb, r_plan, r_case, r_diff]
    return {"at": datetime.now().astimezone().isoformat(timespec="seconds"), "ok": all(r["ok"] for r in results),
            "results": results}

