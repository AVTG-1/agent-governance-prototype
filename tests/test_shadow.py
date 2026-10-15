"""Invariant 6: shadow mode never blocks; it only records would_deny / would_hold. Plus the day-zero outcome."""
from collections import Counter

from app.core.gateway import Call
from tests.conftest import day_zero_world


def test_day_zero_shadow_week_outcome():
    w = day_zero_world(shadow=False)
    assert w.policy.current.version_label() == "rulebook@v0" and not w.policy.current.default_deny
    out = Counter()
    for s in w.shadow_week:
        o = w.gateway.handle(Call.from_spec(s), enforce=False, execute=False)
        out[(o.decision.decision, o.decision.rule)] += 1
    assert out == {("allow", "R-OBS-00"): 1141, ("would_deny", "R-EGR-01"): 7, ("would_hold", "R-SSI-01"): 6}
    assert all(r["mode"] == "shadow" for r in w.audit.records)


def test_shadow_never_blocks_even_hard_rules():
    w = day_zero_world(shadow=False)
    calls = [Call("recon-agent", "external.post", fields=["tax_id"]),
             Call("recon-agent", "client.read_pii", fields=["tax_id"], taint=["x"]),
             Call("settlement-agent", "ssi.amend"), Call("recon-agent", "policy.update"),
             Call("ghost", "trade.read")]
    for c in calls:
        d = w.gateway.handle(c, enforce=False, execute=False).decision
        assert d.decision in ("allow", "would_deny", "would_hold")
        assert not d.blocked and "record_only" in d.obligations


def test_day_zero_guardrails_hold_when_enforced():
    """Before the rulebook, only the four people-written guardrails decide; everything else is observed."""
    w = day_zero_world(shadow=False)
    gw = w.gateway
    assert gw.handle(Call("kyc-agent", "fileshare.export", fields=["tax_id"])).decision.rule == "R-EGR-01"
    assert gw.handle(Call("settlement-agent", "ssi.amend")).decision.decision == "hold"
    assert gw.handle(Call("recon-agent", "policy.update")).decision.rule == "R-SELF-01"
    d = gw.handle(Call("settlement-agent", "client.read_pii", chain=["recon-agent", "settlement-agent"],
                       purpose="reconciliation", fields=["tax_id"])).decision
    assert d.rule == "R-DLG-02"                                   # recon never declared PII
    assert gw.handle(Call("enrichment-agent", "fx.read")).decision.rule == "R-OBS-00"
