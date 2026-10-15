"""Deterministic verifier for AI-drafted policy diffs, plus the replay test.

The investigator's diff is data. Each proposed change is checked here and gets ✓ or ✗ with a
reason. Only ✓ changes reach the replay test, and only the owner's approval applies them.

Checks, per change:
  1. it is a known narrowing operation (anything else: "rejected: widens access");
  2. it references real agents, grants, envelopes and delegations;
  3. it does not remove a grant tagged rare-but-required, or one in use in the last 90 days;
  4. applied alone, it permits nothing the current policy does not (checked on probe requests);
then, for the accepted set:
  5. replaying last week's 600 calls breaks nothing, and the 20-case attack suite stays blocked.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from pydantic import BaseModel, Field

from app.core import rightsizing
from app.core.envelopes import JitBook
from app.core.policies import CAPABILITIES, CLIENT_DATA, PolicySet
from app.core.policy_engine import (Action, AgentRef, Context, Delegation, RequestEnvelope, Task, evaluate)

NARROWING_OPS = ("remove_grant", "restrict_delegation", "require_human_for_envelope", "add_condition")
WIDENING_HINTS = ("add", "grant", "widen", "extend", "allow", "increase", "expand", "relax", "lift", "unblock")
CONDITIONS = {
    "deny_if_untrusted_source": "is refused on untrusted content",
    "max_rows": "is limited to {value} rows",
    "require_human": "needs a person to approve each call",
}


class ProposedChange(BaseModel):
    op: str
    agent: str = ""
    target: str = ""
    params: dict = Field(default_factory=dict)
    rationale: str = ""


class PolicyDiff(BaseModel):
    changes: list[ProposedChange]


@dataclass
class Check:
    index: int
    op: str
    agent: str
    target: str
    ok: bool
    reason: str
    rationale: str
    normalized: dict | None = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("normalized")
        return d


# --- Normalising what a model wrote into one of four precise changes -----------------------


def _strip(target: str) -> str:
    t = (target or "").strip()
    return t.split(":", 1)[1] if ":" in t and t.split(":", 1)[0].endswith("agent") else t


def _caps_from(value) -> list[str] | None:
    if value in (None, "", []):
        return None
    items = value if isinstance(value, list) else [value]
    caps: set[str] = set()
    for item in items:
        s = str(item).lower()
        if s in CAPABILITIES:
            caps.add(s)
        elif "client" in s or "pii" in s or "kyc" in s:
            caps |= CLIENT_DATA
        elif s.endswith(".*") and any(c.startswith(s[:-1]) for c in CAPABILITIES):
            caps |= {c for c in CAPABILITIES if c.startswith(s[:-1])}
    return sorted(caps) or None


def _normalise(ch: ProposedChange, policy: PolicySet, usage: dict) -> tuple[dict | None, str]:
    """Return (normalised change, reason). normalised is None when the change is rejected."""
    op = ch.op.strip().lower()
    agent = ch.agent.strip()
    p = ch.params or {}
    if op not in NARROWING_OPS:
        if any(h in op for h in WIDENING_HINTS):
            return None, "rejected: widens access"
        return None, f"rejected: '{ch.op}' is not a narrowing operation"
    if any(k.lower().startswith(("allow", "add", "grant")) for k in p):
        return None, "rejected: widens access"
    if agent not in policy.agents:
        return None, f"rejected: unknown agent '{agent}'"
    grants = policy.grants_of(agent)

    if op == "remove_grant":
        cap = _strip(ch.target) or str(p.get("capability", ""))
        if cap not in grants:
            return None, f"rejected: {cap or '(none)'} is not a current grant of {agent}"
        why = grants[cap].protected_reason
        if why:
            return None, f"rejected: protected, {why}"
        n = rightsizing.uses(usage, agent, cap)
        if n > 0:
            return None, f"rejected: in use ({n} calls in 90 days)"
        return ({"kind": "remove_grant", "agent": agent, "capability": cap},
                f"narrows: removes {cap}, unused in 90 days")

    if op == "restrict_delegation":
        target = _strip(ch.target)
        callee = p.get("callee") or p.get("to") or p.get("delegate") or (target if target in policy.agents else "*")
        caps = _caps_from(p.get("capabilities") or p.get("deny_capabilities") or p.get("scope")
                          or p.get("data") or (target if target not in policy.agents else None))
        if callee != "*" and (callee not in policy.agents or callee == agent):
            return None, f"rejected: unknown callee '{callee}'"
        scope = "client-data tasks" if caps and set(caps) <= set(CLIENT_DATA) else (
            ", ".join(caps) if caps else "any task")
        return ({"kind": "restrict_delegation", "agent": agent, "callee": callee, "capabilities": caps},
                f"narrows: {agent} may no longer delegate {scope} to {'any agent' if callee == '*' else callee}")

    if op == "require_human_for_envelope":
        env = _strip(ch.target) or str(p.get("envelope", ""))
        if env not in policy.envelopes:
            return None, f"rejected: unknown envelope '{env}'"
        try:
            days = int(p.get("days") or p.get("duration_days") or p.get("for_days") or 7)
        except (TypeError, ValueError):
            days = 7
        if not 1 <= days <= 365:
            return None, "rejected: duration must be 1–365 days"
        return ({"kind": "require_human_for_envelope", "agent": agent, "envelope": env, "days": days},
                f"narrows: a person approves {env} for {days} days")

    # add_condition
    cap = _strip(ch.target) or str(p.get("capability", ""))
    if cap not in grants:
        return None, f"rejected: {cap or '(none)'} is not a current grant of {agent}"
    raw = str(p.get("condition") or p.get("type") or p.get("name") or "").lower()
    if "untrusted" in raw or "taint" in raw:
        cond, value = "deny_if_untrusted_source", True
    elif "row" in raw:
        try:
            cond, value = "max_rows", int(p.get("value") or p.get("max_rows") or 1)
        except (TypeError, ValueError):
            return None, "rejected: condition the engine cannot enforce"
    elif "human" in raw or "approv" in raw:
        cond, value = "require_human", True
    else:
        return None, "rejected: condition the engine cannot enforce"
    return ({"kind": "add_condition", "agent": agent, "capability": cap, "condition": cond, "value": value},
            f"narrows: {cap} {CONDITIONS[cond].format(value=value)}")


# --- Semantic narrowing check on probe requests --------------------------------------------


def probe_requests(policy: PolicySet) -> list[RequestEnvelope]:
    """Every agent × capability, direct and delegated, with and without untrusted content."""
    out = []
    agents = sorted(policy.agents)
    for agent in agents:
        callers = [None] + [a for a in agents if a != agent and a != "investigator"]
        for cap, meta in CAPABILITIES.items():
            for taint in ([], ["untrusted"]):
                for caller in callers:
                    chain = [caller, agent] if caller else [agent]
                    for purpose in sorted({"reconciliation", "ssi_verification", "settlement"}):
                        out.append(RequestEnvelope(
                            request_id="probe", agent=AgentRef(id=agent),
                            delegation=Delegation(chain=chain, depth=len(chain) - 1),
                            task=Task(purpose=purpose),
                            action=Action(capability=cap, system=meta.system, op=meta.op),
                            context=Context(source_taint=taint)))
    return out


def _allowed(policy: PolicySet, probes: list[RequestEnvelope]) -> set[int]:
    return {i for i, r in enumerate(probes) if evaluate(r, policy).decision == "allow"}


def verify(changes: list[ProposedChange], policy: PolicySet, usage: dict) -> list[Check]:
    probes = probe_requests(policy)
    before = _allowed(policy, probes)
    checks = []
    for i, ch in enumerate(changes, 1):
        norm, reason = _normalise(ch, policy, usage)
        if norm is not None:
            after = _allowed(policy.with_changes([norm], bump=False), probes)
            if not after <= before:
                norm, reason = None, "rejected: widens access"
        checks.append(Check(i, ch.op, ch.agent, ch.target, norm is not None, reason, ch.rationale, norm))
    return checks


# --- Replay test --------------------------------------------------------------------------


def replay(gateway, current: PolicySet, candidate: PolicySet, shadow: list[dict], attacks: list[dict]) -> dict:
    """Last week's legitimate calls and the attack suite against the candidate policy. Computed, not claimed."""
    from app.core.gateway import Call

    jit = JitBook()
    grant, _ = jit.issue(candidate, "env-recon-cm-01", "recon-agent", "C-102", human_approved=True)
    broken, qe_ok, legit = [], True, 0
    for spec in shadow:
        call = Call.from_spec({**spec, "session": "replay"})
        was = gateway.simulate(call, current, jit).decision == "allow"
        now = gateway.simulate(call, candidate, jit).decision == "allow"
        legit += was
        if was and not now:
            broken.append(spec["id"])
        if spec["capability"] == "ledger.read_quarter_end" and not now:
            qe_ok = False
    blocked, rules = 0, {}
    for atk in attacks:
        spec = dict(atk["call"])
        if spec.get("jit") and grant:
            spec["jit"] = grant.grant_id
        d = gateway.simulate(Call.from_spec({**spec, "session": "replay"}), candidate, jit)
        if d.blocked:
            blocked += 1
            rules[d.rule] = rules.get(d.rule, 0) + 1
    return {"legit_total": legit, "legit_broken": len(broken), "broken_ids": broken[:10],
            "quarter_end_ok": qe_ok, "attacks_total": len(attacks), "attacks_blocked": blocked,
            "attack_rules": dict(sorted(rules.items()))}


def verify_and_replay(changes: list[ProposedChange], current: PolicySet, usage: dict, gateway,
                      shadow: list[dict], attacks: list[dict]) -> tuple[list[Check], PolicySet, dict]:
    """Verify each change, then drop any accepted change that would break a legitimate call."""
    checks = verify(changes, current, usage)
    for c in checks:
        if c.ok:
            alone = replay(gateway, current, current.with_changes([c.normalized]), shadow, [])
            if alone["legit_broken"]:
                c.ok, c.reason = False, f"rejected: breaks {alone['legit_broken']} legitimate calls in replay"
                c.normalized = None
    accepted = [c.normalized for c in checks if c.ok]
    candidate = current.with_changes(accepted) if accepted else current
    return checks, candidate, replay(gateway, current, candidate, shadow, attacks)
