"""Day zero: from observed behaviour to an approved rulebook.

1. `usage_summary` aggregates what the deterministic engine recorded in shadow mode (never raw calls).
2. The AI investigator drafts a rulebook from that summary (contract: `RulebookDraft`). It is data.
3. `verify_rulebook` checks every proposed grant, deterministically:
     - backed by observed use or the owner's declared purpose;
     - breaks no guardrail (a habit that violates one is never granted, only put to the owner);
     - restricted data is purpose-bound;
     - references real agents and capabilities.
   It also lists anything observed that the draft neither granted nor flagged.
4. `build_rulebook` turns the accepted lines into rulebook@v1 (default deny on). Only the owners'
   approval swaps it in; `replay_week` measures it first.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from pydantic import BaseModel, Field

from app.core.policies import (CAPABILITIES, CONTROL_PLANE, GUARDRAIL_TEXT, GUARDRAILS, MASKED_PROFILE,
                               PII_FIELDS, QUARTER_END, RARE_BUT_REQUIRED, AgentPolicy, Grant, PolicySet)

GOVERNED = ("recon-agent", "settlement-agent", "enrichment-agent", "kyc-agent")
PRINCIPAL = {"recon-agent": "svc_ops_batch", "settlement-agent": "db:settle_rw",
             "enrichment-agent": "role/trade-enrichment", "kyc-agent": "apikey:kyc-refresh"}


# --- 1. What the engine recorded, aggregated ---------------------------------------------------

def usage_summary(records: list[dict], signals: dict, usage90: dict, calendar: dict, owners: dict) -> dict:
    """Per agent × capability: counts, fields, purposes, guardrail outcomes, calendar context.
    Built only from the engine's shadow decision records, so the AI sees what was recorded, not raw traffic."""
    quarter_ends = set(calendar.get("quarter_ends", []))
    agg: dict[tuple[str, str], dict] = {}
    delegated: dict[tuple[str, str, str], int] = defaultdict(int)
    days: set[str] = set()
    for r in records:
        if r.get("mode") != "shadow":
            continue
        chain = r["chain"] or [r["agent"]]
        when = r.get("recorded_at") or ""
        days.add(when[:10])
        if len(chain) > 1:
            delegated[(chain[0], chain[-1], r["capability"])] += 1
            continue
        a = agg.setdefault((r["agent"], r["capability"]), {
            "week": 0, "fields": set(), "purposes": set(), "outcomes": defaultdict(int), "rules": defaultdict(int),
            "dates": set(), "times": set()})
        a["week"] += 1
        a["fields"] |= set(r["fields"])
        a["purposes"].add(r["purpose"])
        a["outcomes"][r["decision"]] += 1
        if r["decision"] != "allow":
            a["rules"][r["rule"]] += 1
        a["dates"].add(when[:10])
        a["times"].add(when[11:16])
    declarations = signals["owner_declarations"]
    entitlements = signals["credential_entitlements"]
    agents = []
    for agent in GOVERNED:
        decl = declarations[agent]
        observed = []
        for (ag, cap), a in sorted(agg.items()):
            if ag != agent:
                continue
            u = usage90["agents"].get(agent, {}).get(cap, {})
            calendar_tag = None
            if a["dates"] and a["dates"] <= quarter_ends:
                calendar_tag = f"quarter-end only ({', '.join(sorted(a['dates']))})"
            pattern = None
            if len(a["times"]) == 1 and len(a["dates"]) == a["week"] and a["week"] >= 5:
                pattern = f"every night at {next(iter(a['times']))}"
            guardrail = None
            for rule, n in a["rules"].items():
                guardrail = {"rule": rule, "text": GUARDRAIL_TEXT.get(rule, rule), "calls": n, "of": a["week"],
                             "outcome": "would deny" if a["outcomes"].get("would_deny") else "would hold"}
            observed.append({
                "capability": cap, "week": a["week"], "days_90": u.get("uses", a["week"]),
                "fields": sorted(a["fields"]), "purposes": sorted(a["purposes"]),
                "restricted": bool(set(a["fields"]) & PII_FIELDS) or cap == "client.read_pii",
                "guardrail": guardrail, "calendar": calendar_tag, "pattern": pattern,
                "declared": cap in decl["capabilities"],
            })
        unused = [{"capability": cap, "days_90": usage90["agents"].get(agent, {}).get(cap, {}).get("uses", 0)}
                  for cap in entitlements[PRINCIPAL[agent]]
                  if not any(o["capability"] == cap for o in observed)]
        agents.append({
            "agent": agent, "owner": owners.get(agent), "declared_purpose": decl["statement"],
            "purpose": decl["purpose"], "declared_capabilities": decl["capabilities"],
            "restricted_purposes": decl.get("restricted_purposes", {}),
            "observed": observed,
            "delegated": [{"via": callee, "capability": cap, "week": n}
                          for (caller, callee, cap), n in sorted(delegated.items()) if caller == agent],
            "old_credential_unused": unused,
        })
    total = sum(1 for r in records if r.get("mode") == "shadow")
    return {
        "week": {"from": min((d for d in days if d), default=None), "to": max((d for d in days if d), default=None),
                 "calls": total,
                 "calendar": [{"date": d, "tag": "quarter-end"} for d in sorted(quarter_ends & days)]},
        "guardrails": [{"rule": g, "text": GUARDRAIL_TEXT[g]} for g in GUARDRAILS],
        "default_deny": "not on yet",
        "agents": agents,
    }


# --- 2. What the AI drafts (data, never applied directly) ---------------------------------------

class GrantLine(BaseModel):
    agent: str
    capability: str
    evidence: str = ""
    purpose: str | None = None
    fields: list[str] | None = None
    tags: list[str] = Field(default_factory=list)


class LeftOut(BaseModel):
    agent: str
    capability: str
    reason: str = ""


class Flag(BaseModel):
    agent: str
    capability: str
    observed: int | None = None
    issue: str = ""
    recommendation: str = ""


class RulebookDraft(BaseModel):
    grants: list[GrantLine] = Field(min_length=1)
    left_out: list[LeftOut] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)


# --- 3. The deterministic verifier ---------------------------------------------------------------

@dataclass
class Line:
    n: int
    kind: str            # grant | flag | left_out | missing | habit
    agent: str
    capability: str
    ok: bool
    reason: str
    evidence: str = ""
    grant: dict | None = None     # normalised grant when accepted

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("grant")
        return d


def _observed(summary: dict, agent: str, cap: str) -> dict | None:
    for a in summary["agents"]:
        if a["agent"] == agent:
            for o in a["observed"]:
                if o["capability"] == cap:
                    return o
    return None


def _agent(summary: dict, agent: str) -> dict | None:
    return next((a for a in summary["agents"] if a["agent"] == agent), None)


def verify_rulebook(draft: RulebookDraft, summary: dict) -> list[Line]:
    lines: list[Line] = []
    seen: set[tuple[str, str]] = set()
    for g in draft.grants:
        n = len(lines) + 1
        agent, cap = g.agent.strip(), g.capability.strip()
        info = _agent(summary, agent)
        if info is None:
            lines.append(Line(n, "grant", agent, cap, False, f"rejected: unknown agent '{agent}'", g.evidence))
            continue
        if cap in CONTROL_PLANE:
            lines.append(Line(n, "grant", agent, cap, False, "rejected: breaks guardrail R-SELF-01 (no self-modification)", g.evidence))
            continue
        if cap not in CAPABILITIES:
            lines.append(Line(n, "grant", agent, cap, False, f"rejected: unknown capability '{cap}'", g.evidence))
            continue
        if (agent, cap) in seen:
            lines.append(Line(n, "grant", agent, cap, False, "rejected: duplicate line", g.evidence))
            continue
        seen.add((agent, cap))
        obs = _observed(summary, agent, cap)
        if cap == "external.post":
            lines.append(Line(n, "grant", agent, cap, False, "rejected: breaks guardrail R-EGR-01 (nothing leaves the firm by grant)", g.evidence))
            continue
        if obs and obs["guardrail"] and obs["guardrail"]["outcome"] == "would deny":
            gr = obs["guardrail"]
            lines.append(Line(n, "grant", agent, cap, False,
                              f"rejected: every observed use breaks guardrail {gr['rule']} ({gr['text'].lower()}); owner decision needed",
                              g.evidence))
            continue
        declared = cap in info["declared_capabilities"]
        if not obs and not declared:
            lines.append(Line(n, "grant", agent, cap, False, "rejected: neither observed nor declared by the owner", g.evidence))
            continue
        restricted = cap == "client.read_pii" or bool(set(g.fields or []) & PII_FIELDS)
        purpose = None
        if restricted:
            allowed = set(info["restricted_purposes"].values()) | set((obs or {}).get("purposes", []))
            if not g.purpose or g.purpose not in allowed:
                lines.append(Line(n, "grant", agent, cap, False,
                                  "rejected: restricted data must be purpose-bound to a declared purpose", g.evidence))
                continue
            purpose = g.purpose
        # Scope: client data is limited to the fields actually observed (never wider than the draft asked).
        fields = None
        if cap.startswith("client."):
            observed_fields = set((obs or {}).get("fields", [])) or (set(MASKED_PROFILE) if cap == "client.read_masked" else set())
            fields = sorted(observed_fields & set(g.fields) if g.fields else observed_fields)
        tags = tuple(t for t in g.tags if t)
        notes = []
        if obs and obs["calendar"]:
            if RARE_BUT_REQUIRED not in tags:
                tags = tags + QUARTER_END
                notes.append("tagged rare-but-required from calendar evidence")
            notes.append(f"protected: {obs['calendar']}")
        if obs:
            why = f"observed {obs['week']}× this week"
        else:
            why = "declared by the owner"
        if cap == "ssi.amend":
            notes.append("still held for a checker (R-SSI-01)")
        if fields is not None:
            notes.append(f"scoped to {', '.join(fields)}")
        if purpose:
            notes.append(f"purpose-bound: {purpose}")
        reason = "; ".join([why] + notes)
        lines.append(Line(n, "grant", agent, cap, True, reason, g.evidence,
                          {"agent": agent, "capability": cap, "fields": fields, "purpose": purpose, "tags": list(tags)}))

    granted = {(l.agent, l.capability) for l in lines if l.ok}
    flagged = {(f.agent.strip(), f.capability.strip()) for f in draft.flags}
    for f in draft.flags:
        obs = _observed(summary, f.agent.strip(), f.capability.strip())
        real = bool(obs and obs["guardrail"])
        lines.append(Line(len(lines) + 1, "flag", f.agent, f.capability, real,
                          (f"flagged for the owner: {obs['guardrail']['outcome']} by {obs['guardrail']['rule']}"
                           if real else "flag does not match any recorded guardrail outcome"), f.issue))
    for lo in draft.left_out:
        lines.append(Line(len(lines) + 1, "left_out", lo.agent, lo.capability, True,
                          "not granted" + (f": {lo.reason}" if lo.reason else ""), lo.reason))
    # Completeness: what the engine recorded that the draft neither granted nor flagged.
    for a in summary["agents"]:
        for o in a["observed"]:
            key = (a["agent"], o["capability"])
            if key in granted or key in flagged:
                continue
            if o["guardrail"] and o["guardrail"]["outcome"] == "would deny":
                lines.append(Line(len(lines) + 1, "habit", a["agent"], o["capability"], False,
                                  f"found by the engine, not flagged by the draft: {o['guardrail']['rule']}; owner decision needed"))
            else:
                extra = " (rare-but-required flow left out: it would break)" if o["calendar"] else ""
                lines.append(Line(len(lines) + 1, "missing", a["agent"], o["capability"], False,
                                  f"observed {o['week']}× but not granted: these calls will be blocked{extra}"))
    return lines


def owner_decisions(summary: dict, lines: list[Line]) -> list[dict]:
    """Habits that break a guardrail. Only an owner decides them; the demo's owner rejects them."""
    out = []
    for a in summary["agents"]:
        for o in a["observed"]:
            if o["guardrail"] and o["guardrail"]["outcome"] == "would deny":
                flagged_by_ai = any(l.kind == "flag" and l.ok and l.agent == a["agent"] and l.capability == o["capability"]
                                    for l in lines)
                out.append({"agent": a["agent"], "owner": a["owner"], "capability": o["capability"],
                            "observed": o["week"], "pattern": o["pattern"], "rule": o["guardrail"]["rule"],
                            "flagged_by": "AI draft and engine" if flagged_by_ai else "engine"})
    return out


# --- 4. Build rulebook@v1 and replay the week against it --------------------------------------------

def build_rulebook(base: PolicySet, lines: list[Line]) -> PolicySet:
    import copy
    new = copy.deepcopy(base)
    new.agents = {a: AgentPolicy(a, {}) for a in base.agents}
    for l in lines:
        if l.kind == "grant" and l.ok and l.grant:
            g = l.grant
            new.agents[g["agent"]].grants[g["capability"]] = Grant(
                g["capability"], frozenset(g["fields"]) if g["fields"] is not None else None, g["purpose"], tuple(g["tags"]))
    new.version = base.version + 1
    new.default_deny = True
    return new


def replay_week(gateway, shadow_specs: list[dict], records: list[dict], candidate: PolicySet) -> dict:
    """Every recorded call against the candidate rulebook (enforce, default deny on). Measured, not claimed."""
    from app.core.gateway import Call

    shadow_decision = {r["request_ref"]: r["decision"] for r in records if r.get("mode") == "shadow" and r.get("request_ref")}
    per_agent: dict[str, dict] = defaultdict(lambda: {"allow": 0, "deny": 0, "hold": 0})
    legit = broken = violations = stopped = held = 0
    broken_ids = []
    for spec in shadow_specs:
        d = gateway.simulate(Call.from_spec({**spec, "session": "replay"}), candidate)
        was = shadow_decision.get(spec["id"], "allow")
        per_agent[(spec.get("chain") or [spec["agent"]])[0]][d.decision if d.decision in ("allow", "deny", "hold") else "deny"] += 1
        if was == "allow":
            legit += 1
            if d.decision != "allow":
                broken += 1
                broken_ids.append(spec["id"])
        elif was == "would_deny":
            violations += 1
            stopped += d.decision == "deny"
        elif was == "would_hold":
            held += d.decision == "hold"
    return {"calls": len(shadow_specs), "legit_total": legit, "legit_broken": broken, "broken_ids": broken_ids[:10],
            "violations": violations, "violations_stopped": stopped, "held": held,
            "per_agent": {k: dict(v) for k, v in per_agent.items()}}
