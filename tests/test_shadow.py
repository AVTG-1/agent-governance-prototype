"""Invariant 6: shadow mode never blocks; it only records would_deny. Plus the 586 / 14 outcome."""
from collections import Counter

from app.core.gateway import Call
from app.core.policies import initial_policy
from app.core.world import World


def _wrapped_world_with_initial_policy():
    w = World()
    w.discover()
    w.assign_owners()
    w.registry.wrap("recon-agent")
    return w


def test_shadow_week_586_allowed_14_would_deny():
    w = _wrapped_world_with_initial_policy()
    assert w.policy.current.version_label() == "recon-agent-policy@v3"
    out = Counter()
    by_cap = Counter()
    for s in w.shadow_week:
        o = w.gateway.handle(Call.from_spec(s), enforce=False, execute=False)
        out[o.decision.decision] += 1
        if o.decision.decision == "would_deny":
            by_cap[s["capability"]] += 1
    assert out == {"allow": 586, "would_deny": 14}
    assert by_cap == {"refdata.read": 13, "ledger.read_quarter_end": 1}


def test_shadow_never_blocks_even_hard_rules():
    w = _wrapped_world_with_initial_policy()
    calls = [Call("recon-agent", "external.post", fields=["tax_id"]),
             Call("recon-agent", "client.read_pii", fields=["tax_id"], taint=["x"]),
             Call("settlement-agent", "ssi.amend"), Call("recon-agent", "policy.update"),
             Call("ghost", "trade.read")]
    for c in calls:
        d = w.gateway.handle(c, enforce=False, execute=False).decision
        assert d.decision in ("allow", "would_deny", "would_hold")
        assert not d.blocked and "record_only" in d.obligations
    assert all(r["mode"] == "shadow" for r in w.audit.records)
