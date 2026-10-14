"""Just-in-time envelopes: exactly the fields, rows and operation a task needs, for a short TTL.

TTL runs on a demo clock so a 120 s grant can be shown expiring in about 8 real seconds.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.policies import PolicySet
    from app.core.policy_engine import RequestEnvelope


class DemoClock:
    """Seconds on the envelope clock. The director advances it; tests set it directly."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


@dataclass
class JitGrant:
    grant_id: str
    envelope_id: str
    agent: str
    counterparty: str
    issued_at: float
    ttl_s: int
    human_approved: bool = False

    def remaining(self, now: float) -> float:
        return max(0.0, self.issued_at + self.ttl_s - now)


class JitBook:
    def __init__(self, clock: DemoClock | None = None) -> None:
        self.clock = clock or DemoClock()
        self.grants: dict[str, JitGrant] = {}

    def issue(self, policy: "PolicySet", envelope_id: str, agent: str, counterparty: str,
              human_approved: bool = False) -> tuple[JitGrant | None, str]:
        env = policy.envelopes.get(envelope_id)
        if env is None:
            return None, f"No envelope {envelope_id}."
        if env.agent != agent:
            return None, f"Envelope {envelope_id} is not for {agent}."
        days = policy.envelope_human_days.get(envelope_id)
        if days and not human_approved:
            return None, f"Envelope {envelope_id} needs a person to approve for {days} days after an incident."
        grant = JitGrant(f"jit-{len(self.grants) + 1:03d}", envelope_id, agent, counterparty,
                         self.clock.now(), env.ttl_s, human_approved)
        self.grants[grant.grant_id] = grant
        return grant, "issued"

    def check(self, grant_id: str, req: "RequestEnvelope", policy: "PolicySet") -> tuple[bool, str]:
        """Is this request inside the grant's envelope right now? Returns (ok, reason)."""
        grant = self.grants.get(grant_id)
        if grant is None:
            return False, f"No such grant {grant_id}."
        env = policy.envelopes.get(grant.envelope_id)
        if env is None:
            return False, f"Envelope {grant.envelope_id} no longer exists."
        a = req.action
        if req.agent.id != grant.agent:
            return False, "Grant belongs to another agent."
        if a.capability != env.capability or a.system != env.system:
            return False, f"Envelope covers {env.capability} only."
        if a.op != env.op:
            return False, "Envelope is read-only."
        extra = set(a.fields) - env.fields
        if extra:
            return False, f"Fields {sorted(extra)} are outside the envelope."
        if a.rows > env.max_rows:
            return False, f"{a.rows} rows exceeds the envelope's {env.max_rows}."
        if a.resource and a.resource != grant.counterparty:
            return False, f"Envelope is for counterparty {grant.counterparty} only."
        if policy.envelope_human_days.get(env.id) and not grant.human_approved:
            return False, "Envelope now needs a person to approve."
        if grant.remaining(self.clock.now()) <= 0:
            return False, f"Envelope {env.id} expired (TTL {env.ttl_s} s)."
        left = grant.remaining(self.clock.now())
        return True, f"Within {env.id}: {len(a.fields)} fields, {a.rows} row, read-only, {left:.0f} s left."
