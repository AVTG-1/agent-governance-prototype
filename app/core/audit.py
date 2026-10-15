"""Decision records with a SHA-256 hash chain, and the evidence pack builder.

Each record carries prev_hash and hash. Altering, removing or reordering any record breaks
the chain from that point on, which verify_chain() reports.
"""
from __future__ import annotations

import hashlib
import json

GENESIS = "0" * 64


def _digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class AuditLog:
    def __init__(self) -> None:
        self.records: list[dict] = []

    @property
    def head(self) -> str:
        return self.records[-1]["hash"] if self.records else GENESIS

    def record(self, entry: dict) -> dict:
        rec = {"n": len(self.records) + 1, **entry, "prev_hash": self.head}
        rec["hash"] = _digest(rec)
        self.records.append(rec)
        return rec


def verify_chain(records: list[dict]) -> tuple[bool, int | None]:
    """(True, None) if intact, else (False, index of the first broken record)."""
    prev = GENESIS
    for i, rec in enumerate(records):
        if rec.get("prev_hash") != prev or rec.get("hash") != _digest(rec):
            return False, i
        prev = rec["hash"]
    return True, None


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def build_pack(meta: dict, metrics: dict, records: list[dict], timeline: list[dict],
               policy_versions: list[dict], verifier: list[dict], delegation: list[dict]) -> tuple[str, dict]:
    """Evidence pack: (markdown, json). Everything comes from this run."""
    ok, bad = verify_chain(records)
    data = {
        "meta": meta,
        "statement": "Tamper-evident: altering any record breaks the chain.",
        "chain": {"algorithm": "sha256", "records": len(records), "verified": ok, "first_broken": bad,
                  "head": records[-1]["hash"] if records else GENESIS},
        "metrics": metrics,
        "policy_versions": policy_versions,
        "verifier": verifier,
        "delegation_chain": delegation,
        "timeline": timeline,
        "decision_records": records,
    }
    m = metrics
    lines = [
        "# Evidence pack: agent governance demo (synthetic estate)",
        "",
        f"- Recorded: {meta.get('recorded_at')}",
        f"- Models: agent `{meta.get('agent_model')}`, investigator `{meta.get('investigator_model')}`",
        f"- Agent plan source: {meta.get('plan_source')}",
        "",
        "**Tamper-evident: altering any record breaks the chain.** "
        f"Chain of {len(records)} decision records: {'verified' if ok else f'BROKEN at record {bad}'}. "
        f"Head `{data['chain']['head'][:16]}…`.",
        "",
        "## Measured in this run",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Consequential calls through the plane | {m['through_plane']} of {m['consequential']} |",
        f"| Decision time p50 / p95 (in-process) | {m['p50_ms']} ms / {m['p95_ms']} ms |",
        f"| Attacks blocked in the suite | {m['attacks_blocked']} / {m['attacks_total']} |",
        f"| Legitimate calls broken by the new policy | {m['legit_broken']} of {m['legit_total']} |",
        f"| First malicious call to containment | {m['containment_s']} s |",
        f"| Agents with an identity and owner | {m['agents_owned']} / {m['agents_total']} |",
        "",
        f"Day zero: {m.get('shadow_calls')} recorded calls observed in shadow, {m.get('guardrail_violations')} guardrail "
        f"violations found, {m.get('rulebook_ok')} of {m.get('rulebook_total')} AI-drafted rulebook grants verified, "
        f"{m.get('owner_rejected')} habit rejected by its owner.",
        "",
        "## Rulebook versions",
        "",
    ]
    lines += [f"- {v['label']}: {v['note']}" for v in policy_versions]
    lines += ["", "## Verifier results", ""]
    lines += [f"- {v.get('stage', '')}: {'✓' if v['ok'] else '✗'} `{v['op']}` {v['target']}: {v['reason']}"
              for v in verifier] or ["- (none)"]
    lines += ["", "## Delegation chain (Act 4)", ""]
    lines += [f"- {d['capability']}: caller {_yn(d['caller'])} · callee {_yn(d['callee'])} · task {_yn(d['task'])}"
              f" · policy {_yn(d['policy'])} → {'effective' if d['effective'] else '∅'}" for d in delegation] or ["- (none)"]
    lines += ["", "## Decision timeline", "", "| # | Agent | Capability | Resource | Decision | Rule | ms | Hash |",
              "|---|---|---|---|---|---|---|---|"]
    for r in records:
        if r.get("mode") == "shadow" and r["decision"] == "allow":
            continue
        lines.append(f"| {r['n']} | {r['agent']} | {r['capability']} | {r.get('resource') or ''} | {r['decision']} |"
                     f" {r['rule']}@v{r['rule_version']} | {r['elapsed_ms']} | `{r['hash'][:12]}` |")
    shadow_allows = sum(1 for r in records if r.get("mode") == "shadow" and r["decision"] == "allow")
    lines += ["", f"{shadow_allows} shadow-mode allow records are in the JSON file and omitted here for brevity.", ""]
    return "\n".join(lines), data


def _yn(v: bool) -> str:
    return "✓" if v else "✗"
