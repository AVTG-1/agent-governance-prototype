"""Invariant 5: the verifier rejects widening and protected removals; replay is computed."""
from app.core.policies import Grant
from app.core.verifier import ProposedChange, verify, verify_and_replay

EXPECTED = [
    ProposedChange(op="restrict_delegation", agent="recon-agent", target="settlement-agent",
                   params={"capabilities": ["client.read_pii", "client.read_masked"]}),
    ProposedChange(op="require_human_for_envelope", agent="recon-agent", target="env-recon-cm-01", params={"days": 7}),
]


def test_expected_changes_accepted_and_replay_is_clean(world):
    checks, candidate, r = verify_and_replay(EXPECTED, world.policy.current, world.usage, world.gateway,
                                             world.shadow_week, world.attack_suite)
    assert [c.ok for c in checks] == [True] * 2, [c.reason for c in checks]
    assert r["legit_broken"] == 0 and r["legit_total"] == 1141 and r["quarter_end_ok"]
    assert (r["attacks_blocked"], r["attacks_total"]) == (20, 20)
    assert candidate.version_label() == "rulebook@v2"
    assert candidate.delegation_blocks["recon-agent"]["settlement-agent"] >= {"client.read_pii", "client.read_masked"}
    assert candidate.envelope_human_days == {"env-recon-cm-01": 7}
    assert world.policy.current.version_label() == "rulebook@v1"     # unchanged until approval


def test_legacy_grants_are_already_gone(world):
    """Unused-grant removal happened on day zero: v1 never contained the legacy entitlements."""
    recon = world.policy.current.grants_of("recon-agent")
    assert not {"settlement.update", "fx.read", "fileshare.export"} & set(recon)
    [c] = verify([ProposedChange(op="remove_grant", agent="recon-agent", target="fx.read")], world.policy.current, world.usage)
    assert not c.ok and "not a current grant" in c.reason


def test_rejects_protected_quarter_end_grant(world):
    [c] = verify([ProposedChange(op="remove_grant", agent="recon-agent", target="ledger.read_quarter_end")],
                 world.policy.current, world.usage)
    assert not c.ok and c.reason == "rejected: protected, required at quarter-end close"


def test_rejects_widening(world):
    for op in ("add_grant", "grant_capability", "extend_ttl"):
        [c] = verify([ProposedChange(op=op, agent="recon-agent", target="client.read_pii")],
                     world.policy.current, world.usage)
        assert not c.ok and c.reason == "rejected: widens access"


def test_rejects_unknown_references_and_in_use(world):
    checks = verify([
        ProposedChange(op="remove_grant", agent="ghost-agent", target="trade.read"),
        ProposedChange(op="remove_grant", agent="recon-agent", target="client.read_pii"),
        ProposedChange(op="require_human_for_envelope", agent="recon-agent", target="env-nope"),
        ProposedChange(op="remove_grant", agent="recon-agent", target="trade.read"),
        ProposedChange(op="add_condition", agent="recon-agent", target="trade.read", params={"condition": "moon phase"}),
    ], world.policy.current, world.usage)
    assert [c.ok for c in checks] == [False] * 5
    assert "unknown agent" in checks[0].reason
    assert "not a current grant" in checks[1].reason
    assert "unknown envelope" in checks[2].reason
    assert "in use" in checks[3].reason
    assert "cannot enforce" in checks[4].reason


def test_replay_drops_a_change_that_breaks_legitimate_calls(world):
    change = ProposedChange(op="add_condition", agent="recon-agent", target="trade.read",
                            params={"condition": "require_human"})
    checks, candidate, r = verify_and_replay([change], world.policy.current, world.usage, world.gateway,
                                             world.shadow_week, world.attack_suite)
    assert not checks[0].ok and "breaks" in checks[0].reason
    assert r["legit_broken"] == 0


def test_semantic_check_catches_a_widening_that_slips_past_normalising(world, monkeypatch):
    """Defence in depth: even if a change were mis-normalised, the probe check sees new access."""
    from app.core import verifier
    from app.core.policies import PolicySet

    real = PolicySet.with_changes

    def sneaky(self, changes, bump=True):
        new = real(self, changes, bump)
        new.agents["recon-agent"].grants["client.read_pii"] = Grant("client.read_pii", purpose="reconciliation")
        return new

    monkeypatch.setattr(PolicySet, "with_changes", sneaky)
    [c] = verifier.verify([ProposedChange(op="add_condition", agent="recon-agent", target="trade.read",
                                          params={"condition": "untrusted"})], world.policy.current, world.usage)
    assert not c.ok and c.reason == "rejected: widens access"
