"""Invariant 7: every decision is logged with rule, version and hash chain; the chain verifies."""
from app.core.audit import verify_chain
from app.core.gateway import Call


def test_chain_verifies_and_detects_tampering(world):
    for s in world.shadow_week[:50]:
        world.gateway.handle(Call.from_spec(s), enforce=False, execute=False)
    world.gateway.handle(Call("recon-agent", "client.read_pii", fields=["tax_id"], taint=["x"]))
    recs = world.audit.records
    assert len(recs) == 51
    assert all(r["rule"] and r["rule_version"] and len(r["hash"]) == 64 for r in recs)
    assert verify_chain(recs) == (True, None)
    recs[10]["decision"] = "allow" if recs[10]["decision"] != "allow" else "deny"
    assert verify_chain(recs) == (False, 10)


def test_reordering_breaks_chain(world):
    for s in world.shadow_week[:5]:
        world.gateway.handle(Call.from_spec(s), enforce=False, execute=False)
    recs = list(world.audit.records)
    recs[1], recs[2] = recs[2], recs[1]
    assert verify_chain(recs)[0] is False
