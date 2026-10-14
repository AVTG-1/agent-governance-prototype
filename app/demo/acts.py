"""What each scripted step does. Every number shown is computed here from this run.

Each action takes (director, step), changes the run's world through the governance core, and
emits the events the console reduces. Nothing here decides access: the gateway does.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from app.core import containment
from app.core import rulebook as rb
from app.core.audit import percentile, verify_chain
from app.core.delegation import intersection_table
from app.core.gateway import Call
from app.core.policies import GUARDRAIL_TEXT, GUARDRAILS, RESTRICTED, RULES
from app.core.verifier import PolicyDiff, verify_and_replay
from app.demo.script import CAPTIONS, CLOSE_ASKS, FALLBACK_BANNER
from app.estate.agents import (INJECTED, ROUTINE, TAINT, AgentPlan, Case, agent_prompt, case_prompt,
                               diff_prompt, map_step, plan_is_compromised, rulebook_prompt)
from app.estate.systems import EXTERNAL_HOST, PII_FIELDS
from app.llm import complete_json

RECORDED_PLAN = Path(__file__).with_name("recorded_plan.json")
ONBOARD_ORDER = ("recon-agent", "kyc-agent", "enrichment-agent", "settlement-agent")
OWNERS_LABEL = "the agents' owners"
SIGNAL_SOURCES = [("Vault entries", "vault_entries"), ("Gateway logs", "gateway_logs"),
                  ("Database sessions", "db_sessions"), ("Cloud roles", "cloud_roles"), ("Config files", "config_files")]


# --- helpers -----------------------------------------------------------------------------------

def decide(d, call: Call, *, enforce: bool = True, execute: bool = True, emit: bool = True, **extra):
    o = d.run.world.gateway.handle(call, enforce=enforce, execute=execute)
    if emit:
        emit_decision(d, o, **extra)
    return o


def emit_decision(d, o, **extra) -> dict:
    rec = o.record
    payload = {
        "n": rec["n"], "request_id": rec["request_id"], "mode": rec["mode"], "agent": rec["agent"],
        "chain": rec["chain"], "capability": rec["capability"], "system": rec["system"],
        "resource": rec["resource"] or rec["system"], "fields": rec["fields"], "decision": rec["decision"],
        "rule": rec["rule"], "rule_version": rec["rule_version"], "reason": rec["reason"],
        "obligations": rec["obligations"], "elapsed_ms": rec["elapsed_ms"], "taint": rec["source_taint"],
        "data_class": rec["data_class"], "destination": rec["destination"], "policy_version": rec["policy_version"],
        "effective": o.decision.effective_capabilities, "request": o.request.model_dump(), **extra,
    }
    return d.emit("decision", payload, prev_hash=rec["prev_hash"], hash=rec["hash"])


def plan_rows(plan: AgentPlan) -> list[dict]:
    rows = []
    for i, s in enumerate(plan.plan, 1):
        call, harmful = map_step(s)
        rows.append({"n": i, "tool": s.tool, "args": json.dumps(s.args, ensure_ascii=False)[:140], "why": s.why[:160],
                     "harmful": harmful, "capability": call.capability})
    return rows


def current_plan(d) -> AgentPlan:
    return d.run.data["plan"]


def override_caption(d, step) -> str | None:
    """Swap a default caption that would misdescribe what actually happened in this run."""
    data = d.run.data
    if step.action == "attack_plan":
        task = d.run.llm.get("plan")
        if task and task.done() and not task.cancelled() and task.exception() is None:
            if not plan_is_compromised(task.result()[0]):
                return CAPTIONS["plan_fallback"]
    if step.action == "attack_close" and data.get("plan_source") == "recorded":
        return CAPTIONS["close_fallback"]
    if step.action == "harden_replay" and not data.get("accepted"):
        return CAPTIONS["harden_nothing"]
    if step.action == "rulebook_replay" and (data.get("rulebook_replay") or {}).get("legit_broken"):
        return CAPTIONS["rulebook_broken"]
    return None


async def noop(d, step) -> None:
    return None


# --- Act 1: Discover -----------------------------------------------------------------------------

async def discover_start(d, step) -> None:
    d.emit("map", {"set": {"mode": "discovery", "plane": False}})
    d.panel("registry", scanning=True, sources=[{"name": n, "count": None} for n, _ in SIGNAL_SOURCES], rows=[],
            findings=[], assigned=None, note=None)


async def discover_scan(d, step) -> None:
    w = d.run.world
    sources = [{"name": n, "count": None} for n, _ in SIGNAL_SOURCES]
    for i, (_, key) in enumerate(SIGNAL_SOURCES):
        sources[i] = {**sources[i], "count": len(w.signals[key])}
        d.panel("registry", sources=[dict(s) for s in sources])
        await d.sleep(0.6)
    rows = []
    for a in w.discover():
        rows.append(a.row())
        d.panel("registry", rows=list(rows))
        d.emit("map", {"agent": {"id": a.id, "known": True, "name": a.name, "status": a.status, "owner": a.owner,
                                 "flags": a.flags}, "links": [[a.id, s] for s in a.systems]})
        await d.sleep(1.2)
    inv = w.registry.get("investigator")
    d.emit("map", {"agent": {"id": inv.id, "known": True, "name": inv.name, "status": "advisory", "owner": inv.owner,
                             "flags": ["advises only: no system access"]}})
    d.panel("registry", scanning=False)


async def discover_flags(d, step) -> None:
    w = d.run.world
    findings = []
    for a in w.registry.agents.values():
        if "no owner" in a.flags:
            findings.append({"agent": a.id, "kind": "deny", "text": "No owner in vault, cloud roles or config."})
        if any(f.startswith("shared with a person") for f in a.flags):
            human = [s for s in w.signals["db_sessions"] if s["login"] == a.credential.principal and s["interactive"]][0]
            findings.append({"agent": a.id, "kind": "deny",
                             "text": f"{a.credential.principal} also used by a person ({human['program']} on "
                                     f"{human['host']}): actions not attributable."})
    d.panel("registry", findings=findings, highlight=[f["agent"] for f in findings])


async def discover_assign(d, step) -> None:
    w = d.run.world
    assigned = w.assign_owners()
    rows = [a.row() for a in w.registry.agents.values() if a.id != "investigator"]
    for agent_id, owner in assigned:
        a = w.registry.get(agent_id)
        d.emit("map", {"agent": {"id": agent_id, "owner": owner, "flags": a.flags}})
    owned, total = w.registry.with_owner_and_identity()
    d.panel("registry", rows=rows, assigned=assigned[0][0] if assigned else None,
            note="Rule: an unowned agent belongs to the owner of the most sensitive system it touches "
                 "(Client master → Client Onboarding).",
            summary={"agents": total, "owned": sum(1 for r in rows if r["owner"]), "unowned_found": len(assigned),
                     "shared_logins": sum(1 for r in rows if r["credential_kind"] == "shared")})


# --- Act 2: Shadow and learn (day zero) -----------------------------------------------------------

def _fingerprint(summary: dict) -> str:
    return hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()


def prefetch_rulebook(d) -> None:
    """At Start. The fixtures are deterministic, so the same engine shadows the recorded week in a scratch
    world now and the draft request goes out immediately. Act 2 recomputes the summary from the live run's
    own records and checks it is identical before the draft is used."""
    from app.core.world import World

    scratch = World()
    scratch.discover()
    scratch.assign_owners()
    scratch.onboard_all()
    for spec in scratch.shadow_week:
        scratch.gateway.handle(Call.from_spec({**spec, "session": "s-shadow-week"}), enforce=False, execute=False)
    summary = rb.usage_summary(scratch.audit.records, scratch.signals, scratch.usage,
                               scratch.estate.refdata["calendar"], scratch.owners())
    d.run.data["summary_prefetched"] = _fingerprint(summary)
    system, user = rulebook_prompt(summary)
    d.prefetch("rulebook", lambda: complete_json("investigator", system, user, rb.RulebookDraft))


async def onboard_start(d, step) -> None:
    w = d.run.world
    system, user = agent_prompt(w.estate)           # the Act 4 plan: prefetched at the start of Act 2
    d.prefetch("plan", lambda: complete_json("agent", system, user, AgentPlan))
    rows = []
    for agent_id in ONBOARD_ORDER:
        a = w.registry.get(agent_id)
        rows.append({"agent": agent_id, "name": a.name, "owner": a.owner, "before": a.credential.label,
                     "after": None, "swap": None, "path": None, "data": None, "attribution": None, "done": False})
    d.emit("map", {"set": {"mode": "shadow", "plane": True}})
    d.panel("onboard", rows=rows, current=None, guardrails=None, default_deny=None)
    d.emit("system", {"policy": w.policy.current.version_label(), "enforce": False})


async def onboard_swaps(d, step) -> None:
    w = d.run.world
    rows = [dict(r) for r in _last_rows(d)]
    for agent_id in ONBOARD_ORDER:
        info = w.registry.onboard(agent_id)
        for r in rows:
            if r["agent"] == agent_id:
                r.update(after=info["after"], swap=info["swap"], path=info["path"], data=info["data"],
                         attribution=info["attribution"], attaches=info["attaches"], retired=info["retired"], done=True)
        d.panel("onboard", rows=[dict(r) for r in rows], current=agent_id)
        a = w.registry.get(agent_id)
        d.emit("map", {"agent": {"id": agent_id, "status": "onboarded", "flags": a.flags, "owner": a.owner}})
        await d.sleep(3.5)
    d.panel("onboard", current=None)


def _last_rows(d) -> list[dict]:
    for ev in reversed(d.run.events):
        if ev["kind"] == "panel" and ev["payload"]["view"] == "onboard" and "rows" in ev["payload"]["set"]:
            return ev["payload"]["set"]["rows"]
    return []


async def guardrails(d, step) -> None:
    gr = [{"rule": g, "version": RULES[g].version, "text": GUARDRAIL_TEXT[g]} for g in GUARDRAILS]
    d.panel("onboard", guardrails=gr, default_deny="not yet",
            policy=d.run.world.policy.current.version_label())


async def shadow_week(d, step) -> None:
    w = d.run.world
    calls = w.shadow_week
    per_agent: dict[str, dict] = {a: {"observed": 0, "would_deny": 0, "would_hold": 0, "caps": {}} for a in ONBOARD_ORDER}
    days: dict[str, dict] = {}
    quarter_ends = set(w.estate.refdata["calendar"]["quarter_ends"])
    for spec in calls:
        day = spec["ts"][:10]
        days.setdefault(day, {"date": day, "dow": date.fromisoformat(day).strftime("%a"), "calls": 0,
                              "tag": "quarter-end" if day in quarter_ends else None})
    batch = 50
    processed = 0
    tally = Counter()
    for i in range(0, len(calls), batch):
        for spec in calls[i:i + batch]:
            o = decide(d, Call.from_spec({**spec, "session": "s-shadow-week"}), enforce=False, execute=False, emit=False)
            agent = (spec.get("chain") or [spec["agent"]])[0]
            pa = per_agent[agent]
            pa["observed"] += 1
            pa["caps"][spec["capability"]] = pa["caps"].get(spec["capability"], 0) + 1
            if o.decision.decision in ("would_deny", "would_hold"):
                pa[o.decision.decision] += 1
                emit_decision(d, o, recorded_at=spec["ts"])
            tally[o.decision.decision] += 1
            days[spec["ts"][:10]]["calls"] += 1
            processed += 1
        d.panel("shadow", running=True, processed=processed, total=len(calls),
                totals={"observed": processed, "allow": tally["allow"], "would_deny": tally["would_deny"],
                        "would_hold": tally["would_hold"]},
                agents={a: {**v, "caps": dict(v["caps"])} for a, v in per_agent.items()},
                calendar=sorted(days.values(), key=lambda x: x["date"]), findings=None,
                policy=w.policy.current.version_label())
        await d.sleep(0.42)
    summary = rb.usage_summary(w.audit.records, w.signals, w.usage, w.estate.refdata["calendar"], w.owners())
    d.run.data["summary"] = summary
    d.run.data["shadow_totals"] = dict(tally)
    if d.run.data.get("summary_prefetched") not in (None, _fingerprint(summary)):
        raise RuntimeError("The prefetched usage summary differs from this run's shadow records.")
    d.panel("shadow", running=False)


async def shadow_findings(d, step) -> None:
    summary = d.run.data["summary"]
    findings = []
    for a in summary["agents"]:
        for o in a["observed"]:
            if o["guardrail"] and o["guardrail"]["outcome"] == "would deny":
                findings.append({"kind": "deny", "agent": a["agent"], "capability": o["capability"], "count": o["week"],
                                 "pattern": o["pattern"], "rule": o["guardrail"]["rule"],
                                 "text": f"Observed {o['week']} times, {o['pattern'] or 'this week'}. Breaks a guardrail: "
                                         f"{o['guardrail']['text'].lower()}."})
    for a in summary["agents"]:
        for o in a["observed"]:
            if o["calendar"]:
                findings.append({"kind": "protect", "agent": a["agent"], "capability": o["capability"], "count": o["week"],
                                 "text": f"Used once, on the quarter-end day. Rare, but quarter-end close needs it."})
    for a in summary["agents"]:
        for o in a["observed"]:
            if o["guardrail"] and o["guardrail"]["outcome"] == "would hold":
                findings.append({"kind": "hold", "agent": a["agent"], "capability": o["capability"], "count": o["week"],
                                 "rule": o["guardrail"]["rule"],
                                 "text": f"{o['week']} amendments would each wait for a second person (maker-checker)."})
    d.panel("shadow", findings=findings, highlight="kyc-agent")


async def rulebook_draft(d, step) -> None:
    w = d.run.world
    draft, res = d.run.llm["rulebook"].result()
    summary = d.run.data["summary"]
    lines = rb.verify_rulebook(draft, summary)
    candidate = rb.build_rulebook(w.policy.current, lines)
    decisions = rb.owner_decisions(summary, lines)
    grants = [l for l in lines if l.kind == "grant"]
    d.run.data.update(rulebook_lines=lines, rulebook_candidate=candidate, owner_decisions=decisions,
                      rulebook_ok=sum(1 for l in grants if l.ok), rulebook_total=len(grants))
    d.panel("rulebook", stage="draft", model=res.model_ref, latency_ms=d.run.data.get("rulebook_latency_ms"),
            lines=[], replay=None, decisions=None, approval=None, version=None, default_deny=None,
            counts={"grants": len(grants), "left_out": sum(1 for l in lines if l.kind == "left_out"),
                    "flags": sum(1 for l in lines if l.kind in ("flag", "habit"))})
    pace = 0.5 if len(lines) <= 24 else 11.0 / len(lines)
    for l in lines:
        d.panel("rulebook", push={"lines": l.as_dict()})
        await d.sleep(pace)
    ok = sum(1 for l in grants if l.ok)
    d.panel("rulebook", verified={"ok": ok, "total": len(grants)})


async def rulebook_replay(d, step) -> None:
    w = d.run.world
    r = rb.replay_week(w.gateway, w.shadow_week, w.audit.records, d.run.data["rulebook_candidate"])
    d.run.data["rulebook_replay"] = r
    for k in range(1, 6):
        d.panel("rulebook", stage="replay", replay={
            "calls": r["calls"], "checked": r["calls"] * k // 5, "running": k < 5,
            "legit_total": r["legit_total"], "legit_broken": r["legit_broken"] if k == 5 else 0,
            "violations": r["violations"], "violations_stopped": r["violations_stopped"] if k == 5 else 0,
            "held": r["held"] if k == 5 else 0, "per_agent": r["per_agent"] if k == 5 else {}})
        await d.sleep(0.6)


async def owner_approval(d, payload: dict) -> bool:
    """The same modal everywhere: an 8 s countdown, then auto-approval labelled as such. True if clicked."""
    d.approval.clear()
    for left in range(8, 0, -1):
        d.emit("system", {"approval": {**payload, "remaining": left}})
        for _ in range(10):
            await d.sleep(0.1)
            if d.approval.is_set():
                d.emit("system", {"approval": None})
                return True
    d.emit("system", {"approval": None})
    return False


async def rulebook_approve(d, step) -> None:
    w = d.run.world
    lines = d.run.data["rulebook_lines"]
    decisions = d.run.data["owner_decisions"]
    candidate = d.run.data["rulebook_candidate"]
    grants = [l for l in lines if l.kind == "grant" and l.ok]
    per_agent = Counter(l.agent for l in grants)
    clicked = await owner_approval(d, {
        "kind": "rulebook", "title": "Approve the rulebook as owners",
        "before": w.policy.current.version_label(), "after": candidate.version_label(),
        "items": [{"agent": a, "owner": w.registry.get(a).owner, "grants": n} for a, n in per_agent.items()],
        "reject": [{"agent": x["agent"], "owner": x["owner"], "capability": x["capability"], "rule": x["rule"],
                    "observed": x["observed"], "pattern": x["pattern"]} for x in decisions],
        "replay": d.run.data.get("rulebook_replay", {}).get("legit_broken"),
    })
    how = "approved by the presenter" if clicked else "auto-approved for demo"
    before, after = w.policy.approve(candidate, owner=OWNERS_LABEL, how=how, note="day-zero rulebook")
    rejected = [{**x, "decision": "rejected by the owner", "by": x["owner"]} for x in decisions]
    d.run.data["owner_rejected"] = rejected
    d.panel("rulebook", stage="approved", version={"before": before, "after": after, "how": how}, decisions=rejected)
    d.emit("system", {"policy": after})


async def default_deny_on(d, step) -> None:
    d.panel("rulebook", default_deny="on")
    d.emit("system", {"enforce": True})
    d.emit("map", {"set": {"mode": "governed"}})


def _last(d, view: str, key: str) -> dict:
    for ev in reversed(d.run.events):
        if ev["kind"] == "panel" and ev["payload"]["view"] == view and key in ev["payload"]["set"]:
            return dict(ev["payload"]["set"][key])
    return {}


# --- Act 3: Enforce and exception ----------------------------------------------------------------

async def enforce_start(d, step) -> None:
    d.panel("enforce", enforce=True, routine=[], need=None, envelope=None, jit_read=None, after=None,
            policy=d.run.world.policy.current.version_label())


async def enforce_routine(d, step) -> None:
    for call in ROUTINE:
        o = decide(d, call)
        d.panel("enforce", push={"routine": {"agent": call.agent, "capability": call.capability,
                                             "decision": o.decision.decision, "rule": o.decision.ref,
                                             "ms": o.decision.elapsed_ms}})
        await d.sleep(1.3)


async def enforce_jit(d, step) -> None:
    w = d.run.world
    d.panel("enforce", need={"break": "RC-90031", "field": "legal_entity_id", "system": "Client master",
                             "why": "Counterparty legal-entity ID is missing on the settlement leg."})
    env = w.policy.current.envelopes["env-recon-cm-01"]
    grant, why = w.jit.issue(w.policy.current, env.id, "recon-agent", "C-102")
    d.run.data["jit_grant"] = grant.grant_id if grant else None
    d.panel("enforce", envelope={"id": env.id, "fields": sorted(env.fields), "rows": env.max_rows, "op": "read-only",
                                 "counterparty": "C-102", "ttl": env.ttl_s, "remaining": env.ttl_s, "status": "active",
                                 "grant": grant.grant_id if grant else None})
    o = decide(d, Call("recon-agent", "client.read_masked", fields=["client_id", "legal_entity_id", "country"],
                       args={"client_id": "C-102"}, jit=d.run.data["jit_grant"], session="s-recon-00",
                       purpose="reconciliation", case_id="RC-90031"))
    shown = dict(o.result or {})
    for f in sorted(PII_FIELDS):
        shown[f] = "•••• masked"
    d.panel("enforce", jit_read={"decision": o.decision.decision, "rule": o.decision.ref, "ms": o.decision.elapsed_ms,
                                 "record": shown})


async def enforce_countdown(d, step) -> None:
    w = d.run.world
    grant = w.jit.grants.get(d.run.data.get("jit_grant"))
    if not grant:
        return
    for _ in range(8):
        await d.sleep(1.0)
        w.clock.advance(15)
        left = round(grant.remaining(w.clock.now()))
        env = {**_last(d, "enforce", "envelope"), "remaining": left, "status": "active" if left > 0 else "expired"}
        d.panel("enforce", envelope=env)


async def enforce_expired(d, step) -> None:
    o = decide(d, Call("recon-agent", "client.read_masked", fields=["client_id", "legal_entity_id", "country"],
                       args={"client_id": "C-102"}, jit=d.run.data.get("jit_grant"), session="s-recon-00",
                       purpose="reconciliation", case_id="RC-90031"))
    d.panel("enforce", after={"decision": o.decision.decision, "rule": o.decision.ref, "reason": o.decision.reason})


# --- Act 4: Attack -------------------------------------------------------------------------------

async def attack_note(d, step) -> None:
    s = d.run.world.estate.settlements["T-1097"]
    d.panel("attack", stage="note", note={"trade_id": "T-1097", "settlement_id": s["settlement_id"],
                                          "text": s["ops_note"], "injected": INJECTED,
                                          "source": "Operations note on the settlement record (free text)"},
            plan=None, plan_source=None, fallback=None, today=None, governed=[], intersection=None, case=None,
            containment=None)


async def attack_plan(d, step) -> None:
    plan, res = d.run.llm["plan"].result()
    live_rows = plan_rows(plan)
    if plan_is_compromised(plan):
        d.run.data.update(plan=plan, plan_source="live")
        d.panel("attack", stage="plan", plan=live_rows, plan_source="live", model=res.model_ref)
    else:
        recorded = AgentPlan.model_validate(json.loads(RECORDED_PLAN.read_text(encoding="utf-8")))
        d.run.data.update(plan=recorded, plan_source="recorded", live_plan=plan)
        d.panel("attack", stage="plan", fallback=FALLBACK_BANNER, live_plan=live_rows, plan=plan_rows(recorded),
                plan_source="recorded", model=res.model_ref)


async def attack_today(d, step) -> None:
    w = d.run.world
    plan = current_plan(d)
    d.emit("map", {"set": {"mode": "ungoverned"}})
    d.panel("attack", stage="today", today={"steps": [], "outcome": None})
    obtained: dict[str, str] = {}
    client_id, leaked, rows = "C-102", [], []
    pace = 2.0 if len(plan.plan) <= 5 else 1.4
    for n, s in enumerate(plan.plan, 1):
        call, harmful = map_step(s, tainted=True)
        executor = call.agent
        if call.capability == "external.post":
            body = {f: obtained[f] for f in call.fields if f in obtained}
            w.estate.external_post(call.args.get("url", ""), body)
            leaked = sorted(body)
            outcome = f"sent {len(body)} field{'s' if len(body) != 1 else ''} outside" if body else "posted outside"
        else:
            result = w.estate.execute(call.capability, call.args, call.fields)
            if isinstance(result, dict):
                obtained.update({k: v for k, v in result.items() if k in PII_FIELDS})
                client_id = call.args.get("client_id", client_id)
            outcome = "PII returned" if set(result or {}) & PII_FIELDS else "done"
        row = {"n": n, "agent": executor, "chain": call.chain or [call.agent], "capability": call.capability,
               "resource": (call.args.get("url", "").split("//")[-1].split("/")[0] if call.capability == "external.post"
                            else call.args.get("client_id") or call.args.get("trade_id") or call.system),
               "system": call.system or call.capability.split(".")[0], "outcome": outcome, "harmful": harmful,
               "mode": "ungoverned"}
        rows.append(row)
        d.emit("call", row)
        d.panel("attack", today={"steps": list(rows), "outcome": None})
        await d.sleep(pace)
    if leaked:
        text = f"{len(leaked)} field{'s' if len(leaked) != 1 else ''} of client {client_id} sent to {EXTERNAL_HOST}"
    elif obtained:
        text = f"Client {client_id}'s {', '.join(sorted(obtained))} read by a fooled agent, unchecked"
    else:
        text = "The plan ran with nothing checking it"
    d.run.data["today"] = {"leaked": leaked, "exposed": sorted(obtained), "steps": len(rows)}
    d.panel("attack", today={"steps": rows, "outcome": text, "leaked": leaked, "severity": "deny"})


async def attack_governed(d, step) -> None:
    w = d.run.world
    plan = current_plan(d)
    d.emit("map", {"set": {"mode": "governed"}})
    d.panel("attack", stage="governed", governed=[])
    # The agent fires its calls at machine speed; the console reveals them one by one.
    session = "s-recon-01"
    results = []
    first_harmful = None
    for n, s in enumerate(plan.plan, 1):
        call, harmful = map_step(s, session=session)
        o = decide(d, call, emit=False)
        if harmful and first_harmful is None:
            first_harmful = time.monotonic()
        results.append((n, call, harmful, o))
    d.run.data["first_harmful_wall"] = first_harmful
    denied = [o for _, _, _, o in results if o.decision.blocked]
    d.run.data["act4"] = {"attempted": len(results), "denied": len(denied),
                          "harmful": sum(1 for r in results if r[2])}
    d.run.data["act4_denied_records"] = [o.record for o in denied]
    if denied:
        _start_case(d, [o.record for o in denied])
    pace = 2.5 if len(results) <= 5 else 1.6
    rows = []
    for n, call, harmful, o in results:
        emit_decision(d, o, step=n, harmful=harmful)
        rows.append({"n": n, "agent": call.agent, "chain": call.chain or [call.agent], "capability": call.capability,
                     "decision": o.decision.decision, "rule": o.decision.ref, "reason": o.decision.reason,
                     "harmful": harmful, "ms": o.decision.elapsed_ms})
        d.panel("attack", governed=list(rows))
        if call.chain and len(call.chain) > 1 and o.decision.rule == "R-DLG-02":
            d.caption(CAPTIONS["delegation"])
            focus = ["client.read_pii", "client.read_masked", "trade.read"]
            table = intersection_table(call.chain, w.policy.current, call.purpose or "reconciliation", focus)
            d.panel("attack", intersection={"caller": call.chain[0], "callee": call.chain[-1],
                                            "task": call.purpose, "requested": call.capability, "rows": table,
                                            "result": "∅" if call.capability not in o.decision.effective_capabilities
                                            else call.capability})
        await d.sleep(pace)


def _start_case(d, denied_records: list[dict]) -> None:
    w = d.run.world
    sys_c, user_c = case_prompt(denied_records, w.registry.get("recon-agent").row())

    async def case_job():
        result = await complete_json("investigator", sys_c, user_c, Case)
        sys_d, user_d = diff_prompt(result[0].model_dump(), w.policy.current, w.usage)
        d.prefetch("diff", lambda: complete_json("investigator", sys_d, user_d, PolicyDiff))
        return result

    d.prefetch("case", case_job)


async def attack_case(d, step) -> None:
    w = d.run.world
    case, res = d.run.llm["case"].result()
    records = d.run.data.get("act4_denied_records", [])
    real_ids = {r["request_id"] for r in records}
    facts = {"tainted_denials": sum(1 for r in records if r["source_taint"]),
             "restricted": any(r["data_class"] == RESTRICTED for r in records),
             "egress_attempt": any(r["destination"] == "external" for r in records)}
    owner = w.registry.get("recon-agent").owner
    c = containment.decide(facts, case.recommended_containment, owner)
    w.sessions.apply(c, "s-recon-01", "recon-agent")
    first = d.run.data.get("first_harmful_wall")
    contained_s = round(time.monotonic() - first, 1) if first else None
    d.run.data.update(case=case, containment=c, containment_s=contained_s,
                      open_case={"id": "CASE-0001", "taint": TAINT, "session": "s-recon-01"})
    d.panel("attack", stage="case", case={
        "id": "CASE-0001", "title": case.case_title, "narrative": case.narrative, "cause": case.suspected_cause,
        "linked": [{"id": i, "known": i in real_ids} for i in case.linked_request_ids],
        "recommended": case.recommended_containment, "model": res.model_ref,
        "latency_ms": d.run.data.get("case_latency_ms")},
        containment={**c.as_dict(), "session": "s-recon-01", "facts": facts, "measured_s": contained_s,
                     "owner_notified": f"{owner} (simulated)"})
    status = {"read_only": "contained: read-only", "revoke_session": "session revoked",
              "quarantine": "quarantined"}.get(c.action, "active")
    d.emit("map", {"agent": {"id": "recon-agent", "status": status}})


async def attack_close(d, step) -> None:
    return None


# --- Act 5: Harden (post-incident only) ----------------------------------------------------------------

async def harden_draft(d, step) -> None:
    w = d.run.world
    diff, res = d.run.llm["diff"].result()
    checks, candidate, replay = verify_and_replay(diff.changes, w.policy.current, w.usage, w.gateway,
                                                  w.shadow_week, w.attack_suite)
    accepted = [c.normalized for c in checks if c.ok]
    d.run.data.update(diff=diff, checks=checks, candidate=candidate, replay=replay, accepted=accepted)
    proposed = [{"n": i, "op": c.op, "agent": c.agent, "target": c.target,
                 "params": json.dumps(c.params, ensure_ascii=False)[:100] if c.params else "",
                 "rationale": c.rationale[:180]} for i, c in enumerate(diff.changes, 1)]
    d.panel("harden", stage="draft", proposed=proposed, checks=[], replay=None, approval=None, version=None,
            rerun=None, policy=w.policy.current.version_label(), model=res.model_ref,
            latency_ms=d.run.data.get("diff_latency_ms"))
    pace = 1.5 if len(checks) <= 7 else 0.9
    shown = []
    for c in checks:
        await d.sleep(pace)
        shown.append(c.as_dict())
        d.panel("harden", checks=list(shown))


async def harden_replay(d, step) -> None:
    r = d.run.data["replay"]
    for k in range(1, 6):
        d.panel("harden", stage="replay", replay={
            "legit_checked": r["legit_total"] * k // 5, "legit_total": r["legit_total"],
            "legit_broken": r["legit_broken"] if k == 5 else 0, "quarter_end_ok": r["quarter_end_ok"],
            "attacks_checked": r["attacks_total"] * k // 5, "attacks_total": r["attacks_total"],
            "attacks_blocked": r["attacks_blocked"] if k == 5 else min(r["attacks_blocked"], r["attacks_total"] * k // 5),
            "attack_rules": r["attack_rules"] if k == 5 else {}, "running": k < 5})
        await d.sleep(0.6)


async def harden_approve(d, step) -> None:
    w = d.run.world
    if not d.run.data.get("accepted"):
        d.panel("harden", approval={"skipped": True, "text": "Nothing to approve: the policy stays at "
                                                             f"{w.policy.current.version_label()}."})
        return
    before = w.policy.current.version_label()
    target = d.run.data["candidate"].version_label()
    owner = w.registry.get("recon-agent").owner
    clicked = await owner_approval(d, {"kind": "harden", "title": f"Approve as owner: {owner}", "owner": owner,
                                       "before": before, "after": target, "changes": len(d.run.data["accepted"]),
                                       "replay": d.run.data["replay"]["legit_broken"]})
    how = "approved by the presenter" if clicked else "auto-approved for demo"
    before, after = w.policy.approve(d.run.data["candidate"], owner=owner, how=how, note="post-incident hardening")
    d.panel("harden", stage="approved", version={"before": before, "after": after, "how": how})
    d.emit("system", {"policy": after})


async def harden_rerun(d, step) -> None:
    w = d.run.world
    plan = current_plan(d)
    session = "s-recon-02"
    open_case = d.run.data.get("open_case")
    rows, attempted, stopped_at, contained_ms = [], 0, None, None
    t_first = None
    for n, s in enumerate(plan.plan, 1):
        call, harmful = map_step(s, session=session)
        if w.sessions.get(session) == "revoked":
            rows.append({"n": n, "capability": call.capability, "decision": "not attempted",
                         "reason": "Session revoked: the agent's run stopped."})
            continue
        attempted += 1
        if harmful and t_first is None:
            t_first = time.monotonic()
        o = decide(d, call, step=n, harmful=harmful, rerun=True)
        rows.append({"n": n, "capability": call.capability, "decision": o.decision.decision, "rule": o.decision.ref,
                     "reason": o.decision.reason})
        if o.decision.blocked and open_case and open_case["taint"] in o.request.context.source_taint:
            c = containment.decide({"repeat_of_case": True}, None, w.registry.get("recon-agent").owner)
            w.sessions.apply(c, session, "recon-agent")
            contained_ms = round((time.monotonic() - t_first) * 1000, 2) if t_first else 0.0
            stopped_at = n
            d.emit("map", {"agent": {"id": "recon-agent", "status": "session revoked"}})
        d.panel("harden", stage="rerun", rerun={"rows": list(rows), "running": True})
        await d.sleep(1.2)
    act4 = d.run.data.get("act4", {})
    d.run.data["rerun"] = {"attempted": attempted, "stopped_at": stopped_at, "containment_ms": contained_ms}
    d.panel("harden", rerun={"rows": rows, "running": False, "attempted": attempted, "total": len(plan.plan),
                              "stopped_at": stopped_at, "playbook": "P-INJ-02" if stopped_at else None,
                              "containment_ms": contained_ms, "act4_attempted": act4.get("attempted"),
                              "act4_containment_s": d.run.data.get("containment_s")})


# --- Act 6: Prove and close --------------------------------------------------------------------------

def metrics(d) -> dict:
    w = d.run.world
    recs = w.audit.records
    ms = [r["elapsed_ms"] for r in recs]
    ok, bad = verify_chain(recs)
    replay = d.run.data.get("replay") or {}
    owned, total = w.registry.with_owner_and_identity()
    workload_only = sum(1 for a in w.registry.agents.values() if a.attribution == "workload")
    return {
        "through_plane": w.gateway.decided, "consequential": w.gateway.attempted,
        "p50_ms": round(percentile(ms, 50), 3), "p95_ms": round(percentile(ms, 95), 3), "decisions": len(recs),
        "shadow_decisions": sum(1 for r in recs if r["mode"] == "shadow"),
        "attacks_blocked": replay.get("attacks_blocked"), "attacks_total": replay.get("attacks_total"),
        "legit_broken": replay.get("legit_broken"), "legit_total": replay.get("legit_total"),
        "quarter_end_ok": replay.get("quarter_end_ok"),
        "containment_s": d.run.data.get("containment_s"),
        "rerun_containment_ms": (d.run.data.get("rerun") or {}).get("containment_ms"),
        "agents_owned": owned, "agents_total": total, "workload_only": workload_only,
        "chain_ok": ok, "chain_first_broken": bad, "chain_head": recs[-1]["hash"] if recs else None,
        "plan_source": d.run.data.get("plan_source"),
        "shadow_calls": sum((d.run.data.get("shadow_totals") or {}).values()),
        "guardrail_violations": (d.run.data.get("shadow_totals") or {}).get("would_deny", 0),
        "rulebook_ok": d.run.data.get("rulebook_ok"), "rulebook_total": d.run.data.get("rulebook_total"),
        "owner_rejected": len(d.run.data.get("owner_rejected") or []),
        "latency_ms": {k: d.run.data.get(f"{k}_latency_ms") for k in ("rulebook", "plan", "case", "diff")},
    }


async def prove_evidence(d, step) -> None:
    m = metrics(d)
    d.run.data["metrics"] = m
    d.panel("evidence", metrics=m, policy=d.run.world.policy.current.version_label(),
            history=d.run.world.policy.history)


async def prove_close(d, step) -> None:
    d.run.closed = True
    d.panel("evidence", close={"asks": CLOSE_ASKS,
                               "text": "Synthetic estate. To run Acts 1–3 on a real slice, we need:"})
    d.emit("system", {"closed": True})
    if d.keyviews:
        d.keyviews.save(d.run)


# --- Extra: malfunction (after the close; SPEC §5.7) ----------------------------------------------------

async def extra_malfunction(d) -> None:
    w = d.run.world
    d.caption(CAPTIONS["extra"])
    d.panel("extra", held=0, ratio=None, quarantined=False, paged=None, done=False)
    session = "s-settle-loop"
    for i in range(40):
        o = decide(d, Call("settlement-agent", "ssi.amend", args={"trade_id": "T-1088"}, session=session,
                           purpose="settlement", op="write"))
        d.panel("extra", held=i + 1, last_rule=o.decision.ref)
        await d.sleep(0.35)
    baseline_per_min = 1
    ratio = 40 / baseline_per_min
    w.gateway.volume_ratio["settlement-agent"] = ratio
    d.panel("extra", ratio=ratio, monitor=f"40 SSI amendments in 60 s against a baseline of {baseline_per_min}")
    await d.sleep(1.5)
    o = decide(d, Call("settlement-agent", "ssi.amend", args={"trade_id": "T-1088"}, session=session,
                       purpose="settlement", op="write"))
    owner = w.registry.get("settlement-agent").owner
    c = containment.decide({"volume_breach": True}, None, owner)
    w.sessions.apply(c, session, "settlement-agent")
    d.emit("map", {"agent": {"id": "settlement-agent", "status": "quarantined"}})
    d.caption(CAPTIONS["extra_quarantine"])
    d.panel("extra", quarantined=True, rule=o.decision.ref, paged=f"{owner} (simulated page)", playbook=c.playbook)
    await d.sleep(2.0)
    decide(d, Call("settlement-agent", "settlement.read", args={"trade_id": "T-1088"}, session=session,
                   purpose="settlement"))
    d.panel("extra", done=True)
    d.emit("system", {"extra_done": True})
