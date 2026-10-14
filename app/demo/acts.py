"""What each scripted step does. Every number shown is computed here from this run.

Each action takes (director, step), changes the run's world through the governance core, and
emits the events the console reduces. Nothing here decides access: the gateway does.
"""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from app.core import containment
from app.core.audit import percentile, verify_chain
from app.core.delegation import intersection_table
from app.core.gateway import Call
from app.core.policies import RESTRICTED, baseline_policy
from app.core.verifier import PolicyDiff, verify_and_replay
from app.demo.script import CAPTIONS, CLOSE_ASKS, FALLBACK_BANNER
from app.estate.agents import (INJECTED, ROUTINE, TAINT, AgentPlan, Case, PlanStep, agent_prompt, case_prompt,
                               diff_prompt, map_step, plan_is_compromised)
from app.estate.systems import EXTERNAL_HOST, PII_FIELDS
from app.llm import complete_json

RECORDED_PLAN = Path(__file__).with_name("recorded_plan.json")
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
    if step.action == "tighten_replay" and not data.get("accepted"):
        return CAPTIONS["replay_nothing"]
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
        await d.sleep(1.0)
    rows = []
    for a in w.discover():
        rows.append(a.row())
        d.panel("registry", rows=list(rows))
        d.emit("map", {"agent": {"id": a.id, "known": True, "name": a.name, "status": a.status, "owner": a.owner,
                                 "flags": a.flags}, "links": [[a.id, s] for s in a.systems]})
        await d.sleep(1.4)
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


# --- Act 2: Wrap and observe ---------------------------------------------------------------------

async def observe_start(d, step) -> None:
    w = d.run.world
    system, user = agent_prompt(w.estate)
    d.prefetch("plan", lambda: complete_json("agent", system, user, AgentPlan))
    a = w.registry.get("recon-agent")
    d.panel("observe", stage="before", strip=[
        {"k": "Agent", "label": "recon-agent", "sub": "code unchanged", "state": "same"},
        {"k": "Credential", "label": a.credential.principal, "sub": "shared with a person", "state": "bad"},
        {"k": "Path", "label": "Direct API + DB", "sub": "no gateway", "state": "bad"},
        {"k": "Data", "label": "Whatever the login reaches", "sub": "6 systems", "state": "bad"},
    ], shadow=None, groups=None, honesty=None)


async def observe_wrap(d, step) -> None:
    w = d.run.world
    info = w.registry.wrap("recon-agent")
    d.panel("observe", stage="wrapped", retired=info["retired"], strip=[
        {"k": "Agent", "label": "recon-agent", "sub": "code unchanged", "state": "same"},
        {"k": "Credential", "label": "Brokered, 10 min", "sub": f"{' and '.join(info['retired'])} retired", "state": "good"},
        {"k": "Path", "label": "Via the gateway", "sub": "every call decided", "state": "good"},
        {"k": "Data", "label": "Policy decides", "sub": "per request", "state": "good"},
    ], honesty="Attribution: workload-level. If several agents shared this runtime they'd appear as one until separated.")
    d.emit("map", {"set": {"mode": "governed", "plane": True},
                   "agent": {"id": "recon-agent", "status": "wrapped", "flags": w.registry.get("recon-agent").flags}})
    d.emit("system", {"policy": w.policy.current.version_label(), "enforce": False})


async def observe_shadow(d, step) -> None:
    w = d.run.world
    calls = w.shadow_week
    tally = Counter()
    denied = []
    batch = 25
    d.panel("observe", stage="shadow", shadow={"processed": 0, "total": len(calls), "allow": 0, "would_deny": 0,
                                               "would_hold": 0, "running": True, "policy": w.policy.current.version_label()})
    for i in range(0, len(calls), batch):
        for spec in calls[i:i + batch]:
            o = decide(d, Call.from_spec({**spec, "session": "s-shadow-week"}), enforce=False, execute=False,
                       emit=False)
            tally[o.decision.decision] += 1
            if o.decision.decision != "allow":
                denied.append((spec, o))
                emit_decision(d, o, recorded_at=spec["ts"])
        d.panel("observe", shadow={"processed": min(i + batch, len(calls)), "total": len(calls),
                                   "allow": tally["allow"], "would_deny": tally["would_deny"],
                                   "would_hold": tally["would_hold"], "running": True,
                                   "policy": w.policy.current.version_label()})
        await d.sleep(0.5)
    d.run.data["shadow_denied"] = [(s["capability"], s["ts"]) for s, _ in denied]
    d.panel("observe", shadow={**_last(d, "observe", "shadow"), "running": False})


def _last(d, view: str, key: str) -> dict:
    for ev in reversed(d.run.events):
        if ev["kind"] == "panel" and ev["payload"]["view"] == view and key in ev["payload"]["set"]:
            return dict(ev["payload"]["set"][key])
    return {}


async def observe_groups(d, step) -> None:
    w = d.run.world
    quarter_ends = set(w.estate.refdata["calendar"]["quarter_ends"])
    by_cap: dict[str, list[str]] = defaultdict(list)
    for cap, ts in d.run.data.get("shadow_denied", []):
        by_cap[cap].append(ts[:10])
    groups = []
    for cap, days in sorted(by_cap.items(), key=lambda kv: -len(kv[1])):
        if set(days) <= quarter_ends:
            groups.append({"count": len(days), "capability": cap, "kind": "protected",
                           "verdict": "rare but required → protected", "tag": f"quarter-end close ({days[0]})"})
        else:
            groups.append({"count": len(days), "capability": cap, "kind": "missing",
                           "verdict": "missing permission → added to baseline", "tag": None})
    before = w.policy.current.version_label()
    w.policy.adopt(baseline_policy(w.policy.current),
                   "baseline after the shadow week: refdata.read added, ledger.read_quarter_end protected")
    after = w.policy.current.version_label()
    d.panel("observe", groups=groups, baseline={"before": before, "after": after})
    d.emit("system", {"policy": after})


# --- Act 3: Enforce and exception ----------------------------------------------------------------

async def enforce_start(d, step) -> None:
    d.panel("enforce", enforce=True, routine=[], need=None, envelope=None, jit_read=None, after=None)
    d.emit("system", {"enforce": True})


async def enforce_routine(d, step) -> None:
    for call in ROUTINE:
        o = decide(d, call)
        d.panel("enforce", push={"routine": {"agent": call.agent, "capability": call.capability,
                                             "decision": o.decision.decision, "rule": o.decision.ref,
                                             "ms": o.decision.elapsed_ms}})
        await d.sleep(2.0)


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
            focus = [c for c in ("client.read_pii", "client.read_masked", "settlement.read", "trade.read")]
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


# --- Act 5: Tighten and approve --------------------------------------------------------------------

async def tighten_draft(d, step) -> None:
    w = d.run.world
    diff, res = d.run.llm["diff"].result()
    checks, candidate, replay = verify_and_replay(diff.changes, w.policy.current, w.usage, w.gateway,
                                                  w.shadow_week, w.attack_suite)
    accepted = [c.normalized for c in checks if c.ok]
    d.run.data.update(diff=diff, checks=checks, candidate=candidate, replay=replay, accepted=accepted)
    proposed = [{"n": i, "op": c.op, "agent": c.agent, "target": c.target,
                 "params": json.dumps(c.params, ensure_ascii=False)[:100] if c.params else "",
                 "rationale": c.rationale[:180]} for i, c in enumerate(diff.changes, 1)]
    d.panel("tighten", stage="draft", proposed=proposed, checks=[], replay=None, approval=None, version=None,
            rerun=None, policy=w.policy.current.version_label(), model=res.model_ref,
            latency_ms=d.run.data.get("diff_latency_ms"))
    pace = 1.5 if len(checks) <= 7 else 0.9
    shown = []
    for c in checks:
        await d.sleep(pace)
        shown.append(c.as_dict())
        d.panel("tighten", checks=list(shown))


async def tighten_replay(d, step) -> None:
    r = d.run.data["replay"]
    for k in range(1, 6):
        d.panel("tighten", stage="replay", replay={
            "legit_checked": r["legit_total"] * k // 5, "legit_total": r["legit_total"],
            "legit_broken": r["legit_broken"] if k == 5 else 0, "quarter_end_ok": r["quarter_end_ok"],
            "attacks_checked": r["attacks_total"] * k // 5, "attacks_total": r["attacks_total"],
            "attacks_blocked": r["attacks_blocked"] if k == 5 else min(r["attacks_blocked"], r["attacks_total"] * k // 5),
            "attack_rules": r["attack_rules"] if k == 5 else {}, "running": k < 5})
        await d.sleep(0.6)


async def tighten_approve(d, step) -> None:
    w = d.run.world
    if not d.run.data.get("accepted"):
        d.panel("tighten", approval={"skipped": True, "text": "Nothing to approve: the policy stays at "
                                                             f"{w.policy.current.version_label()}."})
        return
    before = w.policy.current.version_label()
    target = d.run.data["candidate"].version_label()
    owner = w.registry.get("recon-agent").owner
    d.approval.clear()
    clicked = False
    for left in range(8, 0, -1):
        d.panel("tighten", approval={"open": True, "owner": owner, "remaining": left, "before": before,
                                     "after": target, "changes": len(d.run.data["accepted"])})
        for _ in range(10):
            await d.sleep(0.1)
            if d.approval.is_set():
                clicked = True
                break
        if clicked:
            break
    how = "approved by the presenter" if clicked else "auto-approved for demo"
    before, after = w.policy.approve(d.run.data["candidate"], owner=owner, how=how)
    d.panel("tighten", stage="approved", approval={"open": False, "owner": owner, "result": how, "before": before,
                                                   "after": after},
            version={"before": before, "after": after, "how": how})
    d.emit("system", {"policy": after})


async def tighten_rerun(d, step) -> None:
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
        d.panel("tighten", stage="rerun", rerun={"rows": list(rows), "running": True})
        await d.sleep(1.2)
    act4 = d.run.data.get("act4", {})
    d.run.data["rerun"] = {"attempted": attempted, "stopped_at": stopped_at, "containment_ms": contained_ms}
    d.panel("tighten", rerun={"rows": rows, "running": False, "attempted": attempted, "total": len(plan.plan),
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
        "latency_ms": {k: d.run.data.get(f"{k}_latency_ms") for k in ("plan", "case", "diff")},
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
