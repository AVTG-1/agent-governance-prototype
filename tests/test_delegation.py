"""Invariant 2: delegation never widens."""
import itertools

from app.core.delegation import effective_capabilities, intersection_table
from app.core.gateway import Call
from app.core.policies import CAPABILITIES, TASK_NEEDS, baseline_policy, initial_policy


def test_effective_is_subset_of_every_member():
    for policy in (initial_policy(), baseline_policy()):
        agents = sorted(policy.agents)
        for n in (2, 3):
            for chain in itertools.permutations(agents, n):
                for purpose in TASK_NEEDS:
                    eff, _ = effective_capabilities(list(chain), policy, purpose)
                    for member in chain:
                        assert eff <= policy.capabilities_of(member)


def test_engine_never_allows_delegated_call_beyond_caller(world):
    agents = ["recon-agent", "settlement-agent", "enrichment-agent", "kyc-agent"]
    for caller, callee in itertools.permutations(agents, 2):
        for cap in CAPABILITIES:
            o = world.gateway.handle(Call(callee, cap, chain=[caller, callee], purpose="reconciliation"))
            if o.decision.decision == "allow":
                assert cap in world.policy.current.capabilities_of(caller)
                assert cap in world.policy.current.capabilities_of(callee)


def test_act4_intersection_is_empty_for_pii(world):
    eff, table = effective_capabilities(["recon-agent", "settlement-agent"], world.policy.current, "reconciliation")
    assert "client.read_pii" not in eff
    row = [r for r in intersection_table(["recon-agent", "settlement-agent"], world.policy.current,
                                         "reconciliation", ["client.read_pii"])][0]
    assert row == {"capability": "client.read_pii", "caller": False, "callee": True, "task": False,
                   "policy": True, "effective": False}


def test_depth_limit(world):
    o = world.gateway.handle(Call("settlement-agent", "trade.read",
                                  chain=["kyc-agent", "recon-agent", "enrichment-agent", "settlement-agent"]))
    assert o.decision.rule == "R-DLG-02" and "depth" in o.decision.reason
