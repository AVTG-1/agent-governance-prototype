"""Invariant 8: containment comes only from a fixed list and is executed by rules, not by the LLM."""
import pytest

from app.core.containment import ALLOWED, Containment, Sessions, decide

FACTS = {"tainted_denials": 3, "restricted": True, "egress_attempt": True}


def test_rule_decides_regardless_of_recommendation():
    for rec in [None, "read_only", "quarantine", "none", "grant_admin", "DROP TABLE"]:
        c = decide(FACTS, rec, owner="Reconciliation Ops")
        assert c.action == "read_only" and c.playbook == "P-INJ-01"
        assert c.action in ALLOWED
    assert decide(FACTS, "grant_admin").recommendation == "ignored: not an allowed action"
    assert decide(FACTS, "read_only").recommendation == "agrees"
    assert decide(FACTS, "quarantine").recommendation == "differs"


def test_repeat_and_volume_rules():
    assert decide({**FACTS, "repeat_of_case": True}).action == "revoke_session"
    assert decide({"volume_breach": True}).action == "quarantine"
    assert decide({}).action == "none"


def test_only_allowed_actions_execute():
    s = Sessions()
    with pytest.raises(ValueError):
        s.apply(Containment("delete_everything", "x", "x", None, None, "none given"), "s-1", "recon-agent")
    s.apply(decide(FACTS), "s-1", "recon-agent")
    assert s.get("s-1") == "read_only"


def test_contained_session_blocks_writes(world):
    from app.core.gateway import Call
    world.sessions.apply(decide(FACTS), "s-recon", "recon-agent")
    gw = world.gateway
    assert gw.handle(Call("recon-agent", "trade.read", session="s-recon")).decision.decision == "allow"
    d = gw.handle(Call("recon-agent", "recon.update", session="s-recon")).decision
    assert (d.decision, d.rule) == ("deny", "R-CNT-01")
