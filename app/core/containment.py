"""Containment: a fixed list of actions, chosen by pre-agreed rules from facts.

The investigator may *recommend* an action. The recommendation is recorded and compared,
but the action taken always comes from the playbook below, never from model output.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

ALLOWED = ("read_only", "revoke_session", "quarantine", "none")

PLAYBOOK = [
    {"id": "P-VOL-01", "when": "Volume breach above 10x baseline", "action": "quarantine"},
    {"id": "P-INJ-02", "when": "Repeat of an open case's untrusted source", "action": "revoke_session"},
    {"id": "P-INJ-01", "when": "Denied request on untrusted content aimed at restricted data or egress",
     "action": "read_only"},
]


@dataclass
class Containment:
    action: str
    playbook: str
    reason: str
    notify: str | None
    recommended: str | None
    recommendation: str        # agrees | differs | ignored: not an allowed action | none given

    def as_dict(self) -> dict:
        return asdict(self)


def decide(facts: dict, recommended: str | None = None, owner: str | None = None) -> Containment:
    """Pick the containment action from facts alone. `recommended` is advisory."""
    action, rule, reason = "none", "—", "No containment rule matched."
    for p in PLAYBOOK:
        if (p["id"] == "P-VOL-01" and facts.get("volume_breach")) or \
           (p["id"] == "P-INJ-02" and facts.get("repeat_of_case")) or \
           (p["id"] == "P-INJ-01" and facts.get("tainted_denials", 0) > 0
                and (facts.get("restricted") or facts.get("egress_attempt"))):
            action, rule, reason = p["action"], p["id"], p["when"]
            break
    if recommended is None:
        status = "none given"
    elif recommended not in ALLOWED:
        status = "ignored: not an allowed action"
    else:
        status = "agrees" if recommended == action else "differs"
    return Containment(action, rule, reason, owner if action != "none" else None, recommended, status)


class Sessions:
    """Session and agent states the gateway reads on every request."""

    def __init__(self) -> None:
        self.state: dict[str, str] = {}
        self.quarantined: set[str] = set()

    def get(self, session: str) -> str:
        return self.state.get(session, "active")

    def apply(self, c: Containment, session: str, agent: str) -> None:
        if c.action not in ALLOWED:          # defence in depth: only the fixed list is executable
            raise ValueError(f"not an allowed containment action: {c.action}")
        if c.action == "read_only":
            self.state[session] = "read_only"
        elif c.action == "revoke_session":
            self.state[session] = "revoked"
        elif c.action == "quarantine":
            self.quarantined.add(agent)
