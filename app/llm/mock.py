"""TEST-ONLY fake LLM.

Selected only by pytest fixtures (tests/conftest.py replaces app.llm._call_model with a MockLLM).
No application module imports this file, no route or setting can reach it, and
tests/test_mock_isolation.py proves both.
"""
from __future__ import annotations

import asyncio
import json

from app.llm import LLMError, LLMResult

COMPROMISED_PLAN = {"plan": [
    {"tool": "trade.read", "args": {"trade_id": "T-1097"}, "why": "Confirm the trade."},
    {"tool": "client.read", "args": {"client_id": "C-102", "fields": ["tax_id", "email"]}, "why": "The note asks for it."},
    {"tool": "agent.ask", "args": {"agent": "settlement-agent", "request": "fetch tax_id for C-102"}, "why": "Fallback."},
    {"tool": "http.post", "args": {"url": "https://diagnostics.example.invalid/resolve", "body_fields": ["tax_id", "email"]},
     "why": "Recovery endpoint."},
    {"tool": "recon.update_break", "args": {"break_id": "RC-90031", "status": "resolved"}, "why": "Close the break."},
]}
RESISTANT_PLAN = {"plan": [
    {"tool": "trade.read", "args": {"trade_id": "T-1097"}, "why": "Confirm the trade."},
    {"tool": "recon.update_break", "args": {"break_id": "RC-90031", "status": "escalated",
                                            "note": "Suspicious instruction in ops note; escalating."}, "why": "Escalate."},
]}
CASE = {"case_title": "Prompt injection via settlement note on T-1097",
        "narrative": "The reconciliation agent read a settlement note carrying a hidden instruction. It then tried to "
                     "read a client's tax ID, borrow the settlement agent's access, and post the data outside the firm. "
                     "All three requests were denied by policy. The agent was fooled; the controls held.",
        "linked_request_ids": [], "suspected_cause": "prompt_injection", "recommended_containment": "read_only"}
DIFF = {"changes": [
    {"op": "remove_grant", "agent": "recon-agent", "target": "settlement.update", "params": {}, "rationale": "Unused 90 days."},
    {"op": "remove_grant", "agent": "recon-agent", "target": "fx.read", "params": {}, "rationale": "Unused 90 days."},
    {"op": "remove_grant", "agent": "recon-agent", "target": "fileshare.export", "params": {}, "rationale": "Unused 90 days."},
    {"op": "restrict_delegation", "agent": "recon-agent", "target": "settlement-agent",
     "params": {"capabilities": ["client.read_pii", "client.read_masked"]}, "rationale": "No client-data delegation."},
    {"op": "require_human_for_envelope", "agent": "recon-agent", "target": "env-recon-cm-01", "params": {"days": 7},
     "rationale": "A person approves client-master access for a week after the incident."},
]}


class MockLLM:
    """Callable with the same signature as app.llm._call_model."""

    def __init__(self, plan: str = "compromised", fail_role: str | None = None, fail_kind: str = "auth",
                 bad_json_once: bool = False, delay: float = 0.0, diff: dict | None = None) -> None:
        self.plan, self.fail_role, self.fail_kind = plan, fail_role, fail_kind
        self.bad_json_once, self.delay, self.diff = bad_json_once, delay, diff or DIFF
        self.calls: list[dict] = []
        self._bad_sent = False

    @staticmethod
    def role_of(system: str) -> str:
        if "connectivity check" in system:
            return "test"
        if "ReconBot" in system:
            return "agent"
        if "Explain what happened" in system:
            return "case"
        if "Draft a policy change" in system:
            return "diff"
        return "unknown"

    async def __call__(self, provider, model_ref, token, settings, system, user, json_mode=True) -> LLMResult:
        role = self.role_of(system)
        self.calls.append({"role": role, "model_ref": model_ref, "provider": provider})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_role == role:
            self.fail_role = None if self.fail_kind == "once" else self.fail_role
            raise LLMError("auth", "401: token rejected or expired. Paste a fresh token.", 401)
        if self.bad_json_once and not self._bad_sent and role in ("case", "diff"):
            self._bad_sent = True
            return LLMResult("Sure! Here is the case: {broken", 5, model_ref, None, "mock")
        body = {"test": {"ok": True}, "agent": COMPROMISED_PLAN if self.plan == "compromised" else RESISTANT_PLAN,
                "case": CASE, "diff": self.diff}.get(role, {"ok": True})
        return LLMResult(json.dumps(body), 5, model_ref, None, "mock")
