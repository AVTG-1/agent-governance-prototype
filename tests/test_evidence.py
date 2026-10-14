"""M7: a full mocked run produces an evidence pack whose hash chain verifies, with numbers from the run."""
import json

from app.core.audit import verify_chain
from tests.conftest import pass_gate, wait_done


def test_evidence_pack_from_a_full_run(client):
    pass_gate(client)
    client.post("/api/demo/start")
    wait_done(client)
    md = client.get("/api/evidence.md")
    js = client.get("/api/evidence.json")
    assert md.status_code == 200 and js.status_code == 200
    data = json.loads(js.text)
    records = data["decision_records"]
    assert data["chain"]["verified"] is True and verify_chain(records) == (True, None)
    assert "Tamper-evident: altering any record breaks the chain." in md.text
    m = data["metrics"]
    assert (m["attacks_blocked"], m["attacks_total"], m["legit_broken"], m["legit_total"]) == (20, 20, 0, 1141)
    assert (m["shadow_calls"], m["guardrail_violations"], m["rulebook_ok"], m["rulebook_total"]) == (1154, 7, 16, 16)
    assert m["owner_rejected"] == 1
    assert m["through_plane"] == m["consequential"] > 0
    assert m["agents_owned"] == m["agents_total"] == 4 and m["workload_only"] == 1
    assert m["p95_ms"] >= m["p50_ms"] > 0
    assert [v["label"] for v in data["policy_versions"]] == ["rulebook@v0", "rulebook@v1", "rulebook@v2"]
    assert all(v["ok"] for v in data["verifier"])
    assert [v["stage"] for v in data["verifier"]].count("day-zero rulebook") == 22
    assert [v["stage"] for v in data["verifier"]].count("hardening") == 2
    assert any(r["capability"] == "client.read_pii" and not r["effective"] for r in data["delegation_chain"])
    # Tampering with the downloaded pack is detectable.
    records[3]["decision"] = "allow" if records[3]["decision"] != "allow" else "deny"
    assert verify_chain(records) == (False, 3)


def test_evidence_not_available_before_act6(client):
    assert client.get("/api/evidence.json").status_code == 404


def test_extra_malfunction(client):
    pass_gate(client)
    assert client.post("/api/demo/extra").status_code == 409          # not before the run ends
    client.post("/api/demo/start")
    wait_done(client)
    import time
    import app.main as main
    assert client.post("/api/demo/extra").status_code == 200
    d = main.director
    t0 = time.time()
    while not any(e["kind"] == "system" and e["payload"].get("extra_done") for e in d.run.events) and time.time() - t0 < 10:
        time.sleep(0.05)
    extra = [e["payload"] for e in d.run.events if e["kind"] == "decision" and e["act"] == 7]
    held = [p for p in extra if p["decision"] == "hold"]
    assert len(held) == 40 and all(p["rule"] == "R-SSI-01" for p in held)
    vol = [p for p in extra if p["rule"] == "R-VOL-01"]
    assert vol and "quarantine_agent" in vol[0]["obligations"]
    assert "settlement-agent" in d.run.world.sessions.quarantined
    assert client.post("/api/demo/extra").status_code == 409          # runs once
