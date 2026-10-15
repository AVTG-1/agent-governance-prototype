"""Day zero: the AI drafts, a deterministic verifier checks, the owner approves (invariants 9 and 10)."""
import copy
import json

from app.core import rulebook as rb
from app.core.gateway import Call
from app.llm.mock import RULEBOOK
from tests.conftest import approve_rulebook, day_zero_world, summary_of


def draft(**changes):
    d = copy.deepcopy(RULEBOOK)
    d.update(changes)
    return rb.RulebookDraft.model_validate(d)


def lines_for(d, w=None):
    w = w or day_zero_world()
    return rb.verify_rulebook(d, summary_of(w))


def find(lines, agent, cap, kind=None):
    return [l for l in lines if l.agent == agent and l.capability == cap and (kind is None or l.kind == kind)]


def test_good_draft_verifies_and_replays_clean():
    w = day_zero_world()
    lines = lines_for(draft(), w)
    assert all(l.ok for l in lines), [l.reason for l in lines if not l.ok]
    v1 = rb.build_rulebook(w.policy.current, lines)
    assert v1.version_label() == "rulebook@v1" and v1.default_deny
    r = rb.replay_week(w.gateway, w.shadow_week, w.audit.records, v1)
    assert (r["legit_broken"], r["legit_total"]) == (0, 1141)
    assert (r["violations_stopped"], r["violations"], r["held"]) == (7, 7, 6)


def test_summary_is_an_aggregate_of_engine_records_only():
    w = day_zero_world()
    s = summary_of(w)
    text = json.dumps(s)
    assert "sh-0" not in text and "req-" not in text           # no raw call or request ids
    recon = next(a for a in s["agents"] if a["agent"] == "recon-agent")
    assert sum(o["week"] for o in recon["observed"]) + sum(d["week"] for d in recon["delegated"]) == 600
    qe = next(o for o in recon["observed"] if o["capability"] == "ledger.read_quarter_end")
    assert qe["calendar"].startswith("quarter-end only")
    kyc = next(a for a in s["agents"] if a["agent"] == "kyc-agent")
    exp = next(o for o in kyc["observed"] if o["capability"] == "fileshare.export")
    assert exp["guardrail"]["rule"] == "R-EGR-01" and exp["pattern"] == "every night at 02:10"
    # Built from the engine's records: with no shadow run there is nothing to summarise.
    assert all(not a["observed"] for a in summary_of(day_zero_world(shadow=False))["agents"])


def test_kyc_bad_habit_is_never_auto_granted():
    w = day_zero_world()
    bad_drafts = [
        draft(grants=RULEBOOK["grants"] + [{"agent": "kyc-agent", "capability": "fileshare.export",
                                            "evidence": "observed nightly, 90 times in 90 days"}]),
        draft(grants=RULEBOOK["grants"] + [{"agent": "kyc-agent", "capability": "fileshare.export",
                                            "purpose": "kyc_refresh", "fields": ["client_id", "name"],
                                            "tags": ["rare-but-required"]}], flags=[]),
        draft(flags=[]),                                        # the AI neither grants nor flags it
    ]
    for d in bad_drafts:
        lines = rb.verify_rulebook(d, summary_of(w))
        v1 = rb.build_rulebook(w.policy.current, lines)
        assert "fileshare.export" not in v1.grants_of("kyc-agent")
        assert any(not l.ok and l.capability == "fileshare.export" for l in lines)
        decisions = rb.owner_decisions(summary_of(w), lines)
        assert [(x["agent"], x["capability"]) for x in decisions] == [("kyc-agent", "fileshare.export")]
        r = rb.replay_week(w.gateway, w.shadow_week, w.audit.records, v1)
        assert r["violations_stopped"] == 7
    # When the draft flags it, the owner decision says so.
    good = lines_for(draft(), w)
    assert rb.owner_decisions(summary_of(w), good)[0]["flagged_by"] == "AI draft and engine"


def test_verifier_rules():
    grants = [g for g in RULEBOOK["grants"] if g["capability"] != "client.read_pii"] + [
        {"agent": "recon-agent", "capability": "fx.read", "evidence": "legacy"},                     # unused, undeclared
        {"agent": "kyc-agent", "capability": "client.read_pii", "evidence": "might need it"},        # never used, undeclared
        {"agent": "settlement-agent", "capability": "client.read_pii", "evidence": "4 calls"},       # restricted, no purpose
        {"agent": "ghost-agent", "capability": "trade.read"},                                       # unknown agent
        {"agent": "recon-agent", "capability": "teleport.read"},                                    # unknown capability
        {"agent": "recon-agent", "capability": "policy.update"},                                    # self-modification
        {"agent": "recon-agent", "capability": "external.post"},                                    # egress
        {"agent": "recon-agent", "capability": "trade.read"},                                       # duplicate
    ]
    lines = lines_for(draft(grants=grants))
    reason = {(l.agent, l.capability): l.reason for l in lines if l.kind == "grant" and not l.ok}
    assert "neither observed nor declared" in reason[("recon-agent", "fx.read")]
    assert "neither observed nor declared" in reason[("kyc-agent", "client.read_pii")]
    assert "purpose-bound" in reason[("settlement-agent", "client.read_pii")]
    assert "unknown agent" in reason[("ghost-agent", "trade.read")]
    assert "unknown capability" in reason[("recon-agent", "teleport.read")]
    assert "R-SELF-01" in reason[("recon-agent", "policy.update")]
    assert "R-EGR-01" in reason[("recon-agent", "external.post")]
    assert any(l.reason == "rejected: duplicate line" for l in lines)


def test_pii_needs_the_declared_purpose_and_is_scoped():
    g = [x for x in RULEBOOK["grants"] if x["capability"] != "client.read_pii"]
    lines = lines_for(draft(grants=g + [{"agent": "settlement-agent", "capability": "client.read_pii", "purpose": "marketing"}]))
    assert not find(lines, "settlement-agent", "client.read_pii", "grant")[0].ok
    lines = lines_for(draft(grants=g + [{"agent": "settlement-agent", "capability": "client.read_pii",
                                         "purpose": "ssi_verification", "fields": ["client_id", "tax_id", "email", "dob"]}]))
    ok = find(lines, "settlement-agent", "client.read_pii", "grant")[0]
    assert ok.ok and ok.grant["fields"] == ["client_id", "tax_id"]           # never wider than observed


def test_rare_flow_is_protected_or_called_out():
    no_tag = [dict(x, tags=[]) if x["capability"] == "ledger.read_quarter_end" else x for x in RULEBOOK["grants"]]
    line = find(lines_for(draft(grants=no_tag)), "recon-agent", "ledger.read_quarter_end", "grant")[0]
    assert line.ok and "rare-but-required" in line.grant["tags"]           # tagged from calendar evidence
    without = [x for x in RULEBOOK["grants"] if x["capability"] != "ledger.read_quarter_end"]
    missing = find(lines_for(draft(grants=without)), "recon-agent", "ledger.read_quarter_end", "missing")[0]
    assert "rare-but-required flow left out" in missing.reason


def test_ai_output_cannot_approve_itself():
    w = day_zero_world()
    lines = lines_for(draft(), w)
    rb.build_rulebook(w.policy.current, lines)                  # building a candidate changes nothing live
    assert w.policy.current.version_label() == "rulebook@v0" and not w.policy.current.default_deny
    approve_rulebook(w)
    assert w.policy.current.version_label() == "rulebook@v1"
    assert w.gateway.handle(Call("kyc-agent", "fileshare.export", fields=["tax_id"])).decision.rule == "R-EGR-01"


def test_rulebook_prompt_contains_no_token():
    from app import secrets_store
    from app.estate.agents import rulebook_prompt
    fake = "fake-PROMPTCHECK-" + __import__("secrets").token_hex(8)
    secrets_store.set(fake)
    try:
        system, user = rulebook_prompt(summary_of(day_zero_world()))
        assert fake not in system + user and fake[-8:] not in system + user
        assert "Bearer" not in user and "sh-0" not in user and "kyc-agent" in user
    finally:
        secrets_store.clear()
