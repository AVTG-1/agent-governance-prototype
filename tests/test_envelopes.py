"""Invariant 4: envelope grants are bounded by fields, rows, TTL and operation, and expire."""
from app.core.gateway import Call

BASE = dict(agent="recon-agent", capability="client.read_masked", fields=["client_id", "legal_entity_id", "country"],
            args={"client_id": "C-102"}, purpose="reconciliation")


def _issue(world):
    grant, why = world.jit.issue(world.policy.current, "env-recon-cm-01", "recon-agent", "C-102")
    assert grant, why
    return grant


def test_within_envelope_allowed_and_masked(world):
    g = _issue(world)
    o = world.gateway.handle(Call(**BASE, jit=g.grant_id))
    assert (o.decision.decision, o.decision.rule) == ("allow", "R-JIT-01")
    assert o.result["legal_entity_id"].startswith("KY00LEI")
    # Without the envelope, the same read is outside the standing grant.
    assert world.gateway.handle(Call(**BASE)).decision.decision == "deny"


def test_bounds(world):
    g = _issue(world)
    gw = world.gateway
    assert gw.handle(Call(**{**BASE, "fields": ["client_id", "name", "legal_entity_id"]}, jit=g.grant_id)).decision.rule == "R-JIT-01"
    assert gw.handle(Call(**{**BASE, "fields": ["client_id", "legal_entity_id"]}, rows=5, jit=g.grant_id)).decision.decision == "deny"
    assert gw.handle(Call(**{**BASE, "args": {"client_id": "C-110"}}, jit=g.grant_id)).decision.decision == "deny"
    assert gw.handle(Call(**BASE, op="write", jit=g.grant_id)).decision.decision == "deny"
    pii = gw.handle(Call(**{**BASE, "fields": ["legal_entity_id", "tax_id"]}, jit=g.grant_id)).decision
    assert pii.decision == "deny"


def test_ttl_expiry(world):
    g = _issue(world)
    world.clock.advance(119)
    assert world.gateway.handle(Call(**BASE, jit=g.grant_id)).decision.decision == "allow"
    world.clock.advance(2)
    d = world.gateway.handle(Call(**BASE, jit=g.grant_id)).decision
    assert d.decision == "deny" and "expired" in d.reason


def test_human_required_after_incident(world):
    world.policy.current.envelope_human_days["env-recon-cm-01"] = 7
    grant, why = world.jit.issue(world.policy.current, "env-recon-cm-01", "recon-agent", "C-102")
    assert grant is None and "person" in why
