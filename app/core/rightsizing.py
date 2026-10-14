"""Right-sizing: 90-day usage plus calendar tags -> which grants could go, which must stay.

Used twice: to brief the investigator before it drafts a diff, and by the verifier to refuse
removing anything in use or anything rare-but-required.
"""
from __future__ import annotations

from app.core.policies import PolicySet


def review(policy: PolicySet, usage: dict, agent: str = "recon-agent") -> list[dict]:
    window = usage.get("window_days", 90)
    agent_usage = usage["agents"].get(agent, {})
    rows = []
    for cap, grant in policy.grants_of(agent).items():
        u = agent_usage.get(cap, {"uses": 0, "last_used": None, "calendar_tags": []})
        if grant.protected_reason:
            verdict = f"keep: protected, {grant.protected_reason}"
        elif u["uses"] == 0:
            verdict = f"candidate for removal: unused in {window} days"
        else:
            verdict = "keep: in use"
        rows.append({"capability": cap, "uses_90d": u["uses"], "last_used": u["last_used"],
                     "calendar_tags": u.get("calendar_tags", []), "tags": list(grant.tags), "verdict": verdict})
    return rows


def uses(usage: dict, agent: str, cap: str) -> int:
    return usage["agents"].get(agent, {}).get(cap, {}).get("uses", 0)
