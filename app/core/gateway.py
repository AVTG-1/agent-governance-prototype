"""The gateway: normalise an action into a request envelope, decide, then execute or block, then log.
(Envoy plus an external authoriser in production.)

Every governed call goes through `Gateway.handle`. Today mode skips this module entirely and
calls the estate directly; that is the contrast the demo draws.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.core.audit import AuditLog
from app.core.containment import Sessions
from app.core.envelopes import JitBook
from app.core.identity import Registry
from app.core.policies import CAPABILITIES, PII_FIELDS, RESTRICTED, PolicySet
from app.core.policy_engine import (Action, AgentRef, Context, Decision, Delegation, RequestEnvelope, Task,
                                    evaluate)
from app.estate.systems import Estate


@dataclass
class Call:
    """One intended action, from a scripted agent, an LLM plan step or the attack suite."""
    agent: str
    capability: str
    system: str | None = None
    fields: list[str] = field(default_factory=list)
    rows: int = 1
    chain: list[str] | None = None
    purpose: str | None = None
    case_id: str | None = None
    taint: list[str] = field(default_factory=list)
    destination: str | None = None
    session: str | None = None
    credential: dict | None = None
    jit: str | None = None
    op: str | None = None
    args: dict = field(default_factory=dict)
    resource: str | None = None
    tool: str | None = None

    @classmethod
    def from_spec(cls, spec: dict) -> "Call":
        return cls(**{k: v for k, v in spec.items() if k in cls.__dataclass_fields__})


@dataclass
class Outcome:
    request: RequestEnvelope
    decision: Decision
    result: dict | None
    record: dict | None


def data_class_of(capability: str, fields: list[str], system: str) -> str:
    if capability == "client.read_pii" or set(fields) & PII_FIELDS:
        return RESTRICTED
    return "public" if system == "refdata" else "internal"


def resource_of(call: Call) -> str | None:
    if call.resource:
        return call.resource
    a = call.args or {}
    for key in ("client_id", "trade_id", "break_id", "key"):
        if a.get(key):
            return str(a[key])
    if a.get("url"):
        return str(a["url"]).split("//")[-1].split("/")[0]
    return None


class Gateway:
    def __init__(self, registry: Registry, policy: Callable[[], PolicySet], estate: Estate, audit: AuditLog,
                 jit: JitBook, sessions: Sessions, now: Callable[[], float] = lambda: 0.0) -> None:
        self.registry, self.policy, self.estate, self.audit = registry, policy, estate, audit
        self.jit, self.sessions, self.now = jit, sessions, now
        self.volume_ratio: dict[str, float] = {}
        self._n = 0
        self.attempted = 0          # governed calls that reached the gateway
        self.decided = 0            # ...and got a logged decision

    def normalise(self, call: Call, enforce: bool = True) -> RequestEnvelope:
        self._n += 1
        ident = self.registry.get(call.agent)
        cap = CAPABILITIES.get(call.capability)
        system = call.system or (cap.system if cap else "unknown")
        cred = call.credential
        if cred is None and ident is not None:
            cred = {"kind": ident.credential.kind, "audience": ident.credential.audience,
                    "expired": ident.credential.expired}
        cred = cred or {"kind": "none", "audience": [], "expired": False}
        chain = call.chain or [call.agent]
        session = call.session or f"s-{call.agent}"
        return RequestEnvelope(
            request_id=f"req-{self._n:04d}",
            agent=AgentRef(id=call.agent, session=session, credential=cred["kind"],
                           owner=ident.owner if ident else None, registered=ident is not None),
            delegation=Delegation(chain=chain, depth=len(chain) - 1),
            task=Task(purpose=call.purpose or (ident.purpose if ident else "routine"), case_id=call.case_id),
            action=Action(capability=call.capability, system=system, fields=list(call.fields), rows=call.rows,
                          op=call.op or (cap.op if cap else "read"), resource=resource_of(call)),
            data_class=data_class_of(call.capability, call.fields, system),
            destination=call.destination or ("external" if system == "external" else "internal"),
            context=Context(
                source_taint=list(call.taint), jit_grant=call.jit, enforce=enforce,
                credential_audience=list(cred["audience"]), credential_expired=bool(cred["expired"]),
                session_state=self.sessions.get(session),
                agent_quarantined=call.agent in self.sessions.quarantined,
                volume_ratio=self.volume_ratio.get(call.agent, 0.0),
            ),
        )

    def handle(self, call: Call, *, enforce: bool = True, execute: bool = True) -> Outcome:
        """Decide, then execute only if allowed, then append a hash-chained record."""
        req = self.normalise(call, enforce)
        policy = self.policy()
        if enforce:
            self.attempted += 1
        decision = evaluate(req, policy, self.jit)
        result = None
        if execute and decision.decision == "allow":
            args = dict(call.args)
            if call.capability == "external.post":
                args.setdefault("body", {f: "…" for f in call.fields})
            result = self.estate.execute(call.capability, args, call.fields)
        record = self.audit.record({
            "t": round(self.now(), 2),
            "request_id": req.request_id,
            "mode": "enforce" if enforce else "shadow",
            "agent": req.agent.id,
            "session": req.agent.session,
            "chain": req.delegation.chain,
            "purpose": req.task.purpose,
            "capability": req.action.capability,
            "system": req.action.system,
            "resource": req.action.resource,
            "fields": req.action.fields,
            "rows": req.action.rows,
            "data_class": req.data_class,
            "destination": req.destination,
            "source_taint": req.context.source_taint,
            "decision": decision.decision,
            "rule": decision.rule,
            "rule_version": decision.rule_version,
            "reason": decision.reason,
            "obligations": decision.obligations,
            "elapsed_ms": decision.elapsed_ms,
            "policy_version": policy.version_label(req.agent.id) if req.agent.id in policy.agents else None,
        })
        if enforce:
            self.decided += 1
        return Outcome(req, decision, result, record)

    def simulate(self, call: Call, policy: PolicySet, jit: JitBook | None = None) -> Decision:
        """Decide against a candidate policy: no execution, no audit record (used by the replay test)."""
        n = self._n
        req = self.normalise(call, enforce=True)
        self._n = n                              # replay ids don't consume live request ids
        req.context.session_state = "active"
        req.context.agent_quarantined = False
        req.context.volume_ratio = 0.0
        return evaluate(req, policy, jit or self.jit)
