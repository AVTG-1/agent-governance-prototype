"""Day zero inside a full mocked run: four live calls, the habit rejected by its owner, prompts token-free."""
import json

from tests.conftest import pass_gate, wait_done

FAKE = "fake-DAYZERO-" + __import__("secrets").token_hex(10)


def test_day_zero_in_a_full_run(client):
    pass_gate(client, fake=FAKE)
    client.post("/api/demo/start")
    wait_done(client)
    import app.main as main
    run = main.director.run
    # Four live calls per run, in order; every prompt that went to a model is token-free.
    roles = [c["role"] for c in client.mock.calls if c["role"] != "test"]
    assert roles == ["rulebook", "agent", "case", "diff"]
    for prompt in client.mock.prompts:
        assert FAKE not in prompt and FAKE[-10:] not in prompt
    rulebook_prompt = next(p for p in client.mock.prompts if "Draft the day-zero rulebook" in p)
    assert "every night at 02:10" in rulebook_prompt and "sh-0" not in rulebook_prompt
    # The prefetched summary was identical to the one computed from this run's own shadow records.
    import hashlib
    live = hashlib.sha256(json.dumps(run.data["summary"], sort_keys=True).encode()).hexdigest()
    assert run.data["summary_prefetched"] == live
    # The habit was flagged by the AI, never granted, and rejected by its owner (not by the AI).
    w = run.world
    assert "fileshare.export" not in w.policy.current.grants_of("kyc-agent")
    [rej] = run.data["owner_rejected"]
    assert (rej["agent"], rej["capability"], rej["by"]) == ("kyc-agent", "fileshare.export", "Client Onboarding")
    # Default deny came on only after the owners approved v1.
    hist = [h["label"] for h in w.policy.history]
    assert hist == ["rulebook@v0", "rulebook@v1", "rulebook@v2"]
    enforce_on = next(e["seq"] for e in run.events if e["kind"] == "system" and e["payload"].get("enforce") is True)
    approved = next(e["seq"] for e in run.events if e["kind"] == "system" and e["payload"].get("policy") == "rulebook@v1")
    assert approved < enforce_on
    # Shadow decisions came from the engine only: no allow in shadow cites a grant.
    shadow = [r for r in w.audit.records if r["mode"] == "shadow"]
    assert len(shadow) == 1154 and {r["rule"] for r in shadow} == {"R-OBS-00", "R-EGR-01", "R-SSI-01"}
    # All four agents were onboarded with their own swap and no code change.
    onboarded = [e["payload"]["set"]["rows"] for e in run.events if e["kind"] == "panel"
                 and e["payload"]["view"] == "onboard" and "rows" in e["payload"]["set"]][-1]
    assert {r["swap"] for r in onboarded} == {
        "One identity per agent; the shared account is retired", "Key swapped for a short-lived token from the broker",
        "Role federated to a registered agent identity", "Credential unchanged"}
    assert all(r["done"] for r in onboarded)


def test_a_different_draft_is_shown_honestly(client):
    """Model variability: the draft tries to grant the kyc export and misses the quarter-end grant. The verifier
    shows ✗, the replay counts what breaks, captions say so, and the owner still rejects the habit."""
    import copy

    from app.llm.mock import RULEBOOK
    import app.main as main
    bad = copy.deepcopy(RULEBOOK)
    bad["grants"] = [g for g in bad["grants"] if g["capability"] != "ledger.read_quarter_end"]
    bad["grants"].append({"agent": "kyc-agent", "capability": "fileshare.export", "basis": "observed"})
    bad["flags"] = []
    client.mock.rulebook = bad
    pass_gate(client)
    client.post("/api/demo/start")
    wait_done(client)
    run = main.director.run
    lines = run.data["rulebook_lines"]
    export = [l for l in lines if l.kind == "grant" and l.capability == "fileshare.export"]
    assert export and not export[0].ok and "R-EGR-01" in export[0].reason
    assert any(l.kind == "missing" and l.capability == "ledger.read_quarter_end" for l in lines)
    caps = [e["payload"]["text"] for e in run.events if e["kind"] == "caption"]
    assert "A verifier checks every line the AI drafted, and rejects what it cannot back up." in caps
    assert "Replayed against the week: the exports stop, and the replay shows exactly what else would." in caps
    assert run.data["rulebook_replay"]["legit_broken"] == 1           # the quarter-end read, measured
    assert run.data["rulebook_ok"] == 15 and run.data["rulebook_total"] == 16      # shown as "15 of 16 verified"
    assert [d["by"] for d in run.data["owner_rejected"]] == ["Client Onboarding"]
    assert run.data["owner_decisions"][0]["flagged_by"] == "engine"     # the AI did not flag it; the engine did
