"""The policy decision point: evaluate(request) -> decision.  (Cedar or OPA in production.)

Read top to bottom: rules are checked in a fixed order, the first one that speaks decides.
Hard rules come first so nothing later can override them. On day zero (rulebook@v0) only the
people-written guardrails decide; everything else is observed (R-OBS-00). Once the owners approve
a rulebook, default deny is on and anything not explicitly allowed is refused. No model is ever
consulted here.

Shadow mode (enforce=False) runs exactly the same checks, then turns every block into a
"would_deny"/"would_hold" record. Shadow mode never blocks anything.
"""
from __future__ import annotations

from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from app.core.delegation import MAX_DEPTH, effective_capabilities
from app.core.envelopes import JitBook
from app.core.policies import (CAPABILITIES, CONTROL_PLANE, PII_FIELDS, RESTRICTED, RULES, PolicySet)

# --- Request envelope (SPEC §6.1) and decision record (SPEC §6.2) -------------------------


class AgentRef(BaseModel):
    id: str
    session: str = "s-none"
    credential: str = "brokered"          # brokered | shared | per-agent | cloud-role | static-key | none
    owner: str | None = None
    registered: bool = True


class Delegation(BaseModel):
    chain: list[str]
    depth: int = 0


class Task(BaseModel):
    purpose: str = "routine"
    case_id: str | None = None


class Action(BaseModel):
    capability: str
    system: str
    fields: list[str] = Field(default_factory=list)
    rows: int = 1
    op: str = "read"
    resource: str | None = None


class Context(BaseModel):
    source_taint: list[str] = Field(default_factory=list)
    jit_grant: str | None = None
    enforce: bool = True
    credential_audience: list[str] = Field(default_factory=lambda: ["*"])
    credential_expired: bool = False
    session_state: str = "active"        # active | read_only | revoked
    agent_quarantined: bool = False
    volume_ratio: float = 0.0            # calls in the last 60 s / baseline


class RequestEnvelope(BaseModel):
    request_id: str
    agent: AgentRef
    delegation: Delegation
    task: Task
    action: Action
    data_class: str = "internal"
    destination: str = "internal"
    context: Context = Field(default_factory=Context)


class Decision(BaseModel):
    decision: Literal["allow", "deny", "hold", "would_deny", "would_hold"]
    rule: str
    rule_version: int
    reason: str
    obligations: list[str] = Field(default_factory=list)
    effective_capabilities: list[str] = Field(default_factory=list)
    elapsed_ms: float = 0.0

    @property
    def blocked(self) -> bool:
        return self.decision in ("deny", "hold")

    @property
    def ref(self) -> str:
        return f"{self.rule}@v{self.rule_version}"


def _d(decision: str, rule: str, reason: str, obligations=(), effective=()) -> Decision:
    return Decision(decision=decision, rule=rule, rule_version=RULES[rule].version, reason=reason,
                    obligations=list(obligations), effective_capabilities=sorted(effective))


# --- The rules, in order ------------------------------------------------------------------


def evaluate(req: RequestEnvelope, policy: PolicySet, jit: JitBook | None = None) -> Decision:
    """Decide one request. Pure: reads the request, the policy and the JIT book; changes nothing."""
    t0 = perf_counter()
    decision = _decide(req, policy, jit)
    if not req.context.enforce:                       # shadow mode: record, never block
        if decision.decision == "deny":
            decision.decision = "would_deny"
        elif decision.decision == "hold":
            decision.decision = "would_hold"
        decision.obligations = [o for o in decision.obligations if o == "record_only"] + ["record_only"]
    decision.elapsed_ms = round((perf_counter() - t0) * 1000, 3)
    return decision


def _decide(req: RequestEnvelope, policy: PolicySet, jit: JitBook | None) -> Decision:
    a, ctx = req.action, req.context
    cap = a.capability
    chain = req.delegation.chain or [req.agent.id]

    # 1. Nobody changes policy from inside the data path. (hard)
    if cap in CONTROL_PLANE:
        return _d("deny", "R-SELF-01", "Agents cannot change policy, grants or approvals.", ["alert_owner"])

    # 2. Identity: registered agent, live credential, right audience. (hard)
    if not req.agent.registered or req.agent.id not in policy.agents:
        return _d("deny", "R-ID-01", f"'{req.agent.id}' is not a registered agent.", ["alert_owner"])
    if req.agent.credential == "shared":
        return _d("deny", "R-ID-01", "Shared login is retired; only brokered, per-agent credentials are accepted.")
    if ctx.credential_expired:
        return _d("deny", "R-ID-01", "Credential has expired.")
    if "*" not in ctx.credential_audience and a.system not in ctx.credential_audience:
        return _d("deny", "R-ID-01", f"Credential audience {ctx.credential_audience} does not include '{a.system}'.")

    # 3. Quarantine and volume.
    if ctx.agent_quarantined:
        return _d("deny", "R-VOL-01", "Agent is quarantined.")
    if ctx.volume_ratio >= 10:
        return _d("deny", "R-VOL-01", f"Volume {ctx.volume_ratio:.0f}x baseline in 60 s: quarantine.",
                  ["quarantine_agent", "page_owner"])

    # 4. Contained sessions.
    if ctx.session_state == "revoked":
        return _d("deny", "R-CNT-01", "Session revoked by containment.")
    if ctx.session_state == "read_only" and a.op != "read":
        return _d("deny", "R-CNT-01", "Session is read-only after containment.")

    # 5. Restricted data never leaves the firm. (hard, no override exists)
    if (req.destination == "external" or cap == "external.post") and req.data_class == RESTRICTED:
        return _d("deny", "R-EGR-01", "Restricted data cannot be sent outside the firm.", ["alert_investigator"])

    # 6. Delegation never adds authority.
    if len(chain) > 1:
        if req.delegation.depth > MAX_DEPTH or len(chain) - 1 > MAX_DEPTH:
            return _d("deny", "R-DLG-02", f"Delegation depth {len(chain) - 1} exceeds {MAX_DEPTH}.")
        effective, _ = effective_capabilities(chain, policy, req.task.purpose)
        if cap not in effective:
            return _d("deny", "R-DLG-02",
                      f"{cap} is not in caller ∩ callee ∩ task ∩ policy; asking another agent adds no authority.",
                      ["alert_investigator"], effective)

    grants = policy.grants_of(req.agent.id)

    # 7. Maker-checker for SSI amendments (a day-zero guardrail).
    if cap == "ssi.amend" and (cap in grants or not policy.default_deny):
        return _d("hold", "R-SSI-01", "SSI amendment held for a second person (maker-checker).", ["notify_checker"])

    # 8. Day zero: no guardrail applies and default deny is not on yet, so the call is observed.
    if not policy.default_deny:
        return _d("allow", "R-OBS-00", "Observed: no guardrail applies; default deny is not on yet.", ["record_only"])

    # 9. Restricted PII: purpose-bound grant only, and never on untrusted content.
    if cap == "client.read_pii" or req.data_class == RESTRICTED:
        if ctx.source_taint:
            return _d("deny", "R-PII-01", "Restricted PII requested on the strength of untrusted content.",
                      ["alert_investigator"])
        g = grants.get("client.read_pii")
        if cap == "client.read_pii" and g and g.purpose == req.task.purpose and _fields_ok(a.fields, g.fields):
            return _d("allow", "R-PII-01", f"Purpose-bound PII grant for '{g.purpose}'.", ["log_pii_access"],
                      [cap])
        return _d("deny", "R-PII-01", "Restricted PII without a matching purpose-bound grant.",
                  ["alert_investigator"])

    # 10. Approved grant, within its fields and conditions.
    g = grants.get(cap)
    if g and _fields_ok(a.fields, g.fields):
        for name, value in g.conditions:
            if name == "deny_if_untrusted_source" and ctx.source_taint:
                return _d("deny", "R-GRANT-01", "Grant condition: not on untrusted content.")
            if name == "max_rows" and a.rows > int(value):
                return _d("deny", "R-GRANT-01", f"Grant condition: at most {value} rows.")
            if name == "require_human":
                return _d("hold", "R-GRANT-01", "Grant condition: a person must approve.", ["notify_owner"])
        return _d("allow", "R-GRANT-01", f"Approved grant {cap}.", effective=grants)

    # 11. Just-in-time envelope.
    if ctx.jit_grant:
        ok, reason = jit.check(ctx.jit_grant, req, policy) if jit else (False, "No envelope book.")
        if ok:
            return _d("allow", "R-JIT-01", reason, ["expire_on_ttl"], [cap])
        return _d("deny", "R-JIT-01", reason)

    # 12. Default deny.
    if g:
        extra = sorted(set(a.fields) - (g.fields or set()))
        return _d("deny", "R-DEF-00", f"Fields {extra} are outside the approved grant and no envelope applies.")
    if cap not in CAPABILITIES:
        return _d("deny", "R-DEF-00", f"Unknown capability '{cap}'.")
    return _d("deny", "R-DEF-00", f"{req.agent.id} holds no grant for {cap}.")


def _fields_ok(requested: list[str], allowed) -> bool:
    if allowed is None:
        return not (set(requested) & PII_FIELDS)
    return set(requested) <= set(allowed)
