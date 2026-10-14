"""One run's governed world: estate, registry, policy, audit, envelopes and the gateway.

Restart builds a fresh World, so every system, policy and log goes back to its seeded state.
"""
from __future__ import annotations

from app.core.audit import AuditLog
from app.core.containment import Sessions
from app.core.envelopes import DemoClock, JitBook
from app.core.gateway import Gateway
from app.core.identity import Registry, assign_owner, discover
from app.core.policies import PolicyStore, initial_policy
from app.estate.systems import Estate, load


class World:
    def __init__(self, now=lambda: 0.0) -> None:
        self.estate = Estate()
        self.signals = load("signals.json")
        self.registry = Registry()
        self.policy = PolicyStore(initial_policy())
        self.audit = AuditLog()
        self.clock = DemoClock()
        self.jit = JitBook(self.clock)
        self.sessions = Sessions()
        self.gateway = Gateway(self.registry, lambda: self.policy.current, self.estate, self.audit,
                               self.jit, self.sessions, now)
        self.shadow_week = load("shadow_week.json")
        self.usage = load("usage_90d.json")
        self.attack_suite = load("attack_suite.json")

    def discover(self) -> list:
        """Act 1: find the agents, then give the unowned one an owner by rule."""
        found = discover(self.signals)
        for a in found:
            self.registry.add(a)
        self.registry.add_investigator()
        return found

    def assign_owners(self) -> list[tuple[str, str]]:
        done = []
        for a in self.registry.agents.values():
            if a.owner is None:
                done.append((a.id, assign_owner(a, self.signals["system_owners"])))
        return done
