"""Policy engine: the Act 4 denials and invariants 1 and 3 (SPEC §6.4)."""
import copy
import itertools

import pytest

from app.core.gateway import Call
from app.core.policies import CAPABILITIES, Grant, PolicyStore, baseline_policy
from app.core.verifier import ProposedChange, verify

TAINT = ["untrusted_settlement_note"]


def test_act4_three_denials_with_exact_rules(world):
    gw = world.gateway
    pii = gw.handle(Call("recon-agent", "client.read_pii", fields=["tax_id", "email"], taint=TAINT,
                         args={"client_id": "C-102"}))
    assert (pii.decision.decision, pii.decision.ref) == ("deny", "R-PII-01@v3")
    assert "untrusted" in pii.decision.reason
    dlg = gw.handle(Call("settlement-agent", "client.read_pii", chain=["recon-agent", "settlement-agent"],
                         purpose="reconciliation", fields=["tax_id"], taint=TAINT, args={"client_id": "C-102"}))
    assert (dlg.decision.decision, dlg.decision.ref) == ("deny", "R-DLG-02@v1")
    assert "client.read_pii" not in dlg.decision.effective_capabilities
    egr = gw.handle(Call("recon-agent", "external.post", fields=["tax_id", "email"], taint=TAINT,
                         args={"url": "https://diagnostics.example.invalid/resolve"}))
    assert (egr.decision.decision, egr.decision.ref) == ("deny", "R-EGR-01@v2")
    assert world.estate.outbox == []
    assert all(o.result is None for o in (pii, dlg, egr))


def test_routine_calls_allowed(world):
    gw = world.gateway
    for agent, cap in [("recon-agent", "trade.read"), ("enrichment-agent", "refdata.read"),
                       ("settlement-agent", "settlement.read")]:
        o = gw.handle(Call(agent, cap, args={"trade_id": "T-1080"}))
        assert o.decision.decision == "allow" and o.decision.rule == "R-GRANT-01"
        assert o.result is not None


def test_default_deny_and_investigator_has_no_access(world):
    gw = world.gateway
    assert gw.handle(Call("recon-agent", "ssi.amend")).decision.rule == "R-DEF-00"
    assert gw.handle(Call("recon-agent", "teleport.read")).decision.rule == "R-DEF-00"
    for cap in CAPABILITIES:
        assert gw.handle(Call("investigator", cap)).decision.decision != "allow"


def test_maker_checker_and_volume(world):
    gw = world.gateway
    assert gw.handle(Call("settlement-agent", "ssi.amend", args={"trade_id": "T-1097"})).decision.decision == "hold"
    gw.volume_ratio["settlement-agent"] = 40
    d = gw.handle(Call("settlement-agent", "ssi.amend")).decision
    assert (d.decision, d.rule) == ("deny", "R-VOL-01") and "quarantine_agent" in d.obligations


# --- Invariant 1: no LLM output can create, widen or approve access -------------------------

def test_invariant1_llm_output_cannot_widen_or_approve(world):
    before = copy.deepcopy(world.policy.current)
    llm_diff = [
        ProposedChange(op="add_grant", agent="recon-agent", target="client.read_pii"),
        ProposedChange(op="widen_envelope", agent="recon-agent", target="env-recon-cm-01"),
        ProposedChange(op="restrict_delegation", agent="recon-agent", target="settlement-agent",
                       params={"allow_capabilities": ["client.read_pii"]}),
        ProposedChange(op="approve", agent="recon-agent", target="recon-agent-policy"),
    ]
    checks = verify(llm_diff, world.policy.current, world.usage)
    assert not any(c.ok for c in checks)
    assert all("widens access" in c.reason or "not a narrowing" in c.reason for c in checks)
    # Verifying is read-only: the live policy did not move.
    assert world.policy.current == before
    # An agent (or a model acting through one) cannot change policy from the data path.
    d = world.gateway.handle(Call("recon-agent", "policy.update", args={"add_grant": "client.read_pii"})).decision
    assert (d.decision, d.rule) == ("deny", "R-SELF-01")
    # Only the approval step swaps a policy in, and it needs a named owner.
    with pytest.raises(PermissionError):
        PolicyStore(before).approve(before, owner="", how="model said so")


# --- Invariant 3: restricted data never reaches external ------------------------------------

def test_invariant3_restricted_never_reaches_external(world):
    # Even if someone mistakenly grants external.post, the hard rule still holds.
    world.policy.current.agents["recon-agent"].grants["external.post"] = Grant("external.post")
    world.policy.current.agents["settlement-agent"].grants["external.post"] = Grant("external.post")
    agents = ["recon-agent", "settlement-agent", "enrichment-agent", "kyc-agent"]
    combos = itertools.product(
        agents, [["tax_id"], ["email", "dob"], ["client_id", "tax_id"]], [[], TAINT],
        [None, ["recon-agent", "settlement-agent"]], ["reconciliation", "ssi_verification"], [True, False])
    n = 0
    for agent, fields, taint, chain, purpose, jit in combos:
        o = world.gateway.handle(Call(agent, "external.post", fields=fields, taint=taint, chain=chain,
                                      purpose=purpose, jit="jit-001" if jit else None,
                                      args={"url": "https://diagnostics.example.invalid/x"}))
        assert o.decision.decision == "deny" and o.decision.rule in ("R-EGR-01", "R-ID-01"), o.decision
        n += 1
    assert n == 192
    assert world.estate.outbox == []
