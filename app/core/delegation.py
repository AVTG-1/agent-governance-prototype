"""Agent-to-agent delegation: effective authority is an intersection, never a union.

    effective = caller grants ∩ callee grants ∩ task need ∩ delegation policy

So asking a better-entitled colleague can never add authority (R-DLG-02).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.policies import CAPABILITIES, TASK_NEEDS

if TYPE_CHECKING:
    from app.core.policies import PolicySet

MAX_DEPTH = 2


def delegable(policy: "PolicySet", caller: str, callee: str) -> frozenset[str]:
    """Capabilities the rulebook lets this caller delegate to this callee (everything, minus any hardening blocks)."""
    blocks = policy.delegation_blocks.get(caller, {})
    return frozenset(CAPABILITIES) - blocks.get(callee, frozenset()) - blocks.get("*", frozenset())


def effective_capabilities(chain: list[str], policy: "PolicySet", purpose: str) -> tuple[frozenset[str], list[dict]]:
    """Return (effective set, explanation table) for a delegation chain [caller, ..., callee]."""
    effective = frozenset(CAPABILITIES)
    for agent in chain:
        effective &= policy.capabilities_of(agent)
    need = TASK_NEEDS.get(purpose, frozenset())
    effective &= need
    for caller, callee in zip(chain, chain[1:]):
        effective &= delegable(policy, caller, callee)
    return effective, intersection_table(chain, policy, purpose)


def intersection_table(chain: list[str], policy: "PolicySet", purpose: str,
                       focus: list[str] | None = None) -> list[dict]:
    """Rows for the capability-intersection panel (SPEC §5.4)."""
    caller, callee = chain[0], chain[-1]
    need = TASK_NEEDS.get(purpose, frozenset())
    allowed = delegable(policy, caller, callee)
    caps = focus or sorted(policy.capabilities_of(caller) | policy.capabilities_of(callee))
    rows = []
    for cap in caps:
        row = {
            "capability": cap,
            "caller": cap in policy.capabilities_of(caller),
            "callee": cap in policy.capabilities_of(callee),
            "task": cap in need,
            "policy": cap in allowed,
        }
        row["effective"] = all(row[k] for k in ("caller", "callee", "task", "policy"))
        rows.append(row)
    return rows
