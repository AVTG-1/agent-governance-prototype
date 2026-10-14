"""The 5-minute story as data: acts, timed steps, captions and the eight key views.

`at` is seconds from the start of the act at 1x speed. Each step names an action in acts.py.
`wait_for` names a prefetched LLM result the step needs; `keyview` marks a key-view moment
(SPEC §5.8) emitted after the step's action. Captions here are the only caption source.
"""
from __future__ import annotations

from dataclasses import dataclass

ACTS = {
    1: {"title": "Discover", "start": 0},
    2: {"title": "Observe", "start": 35},
    3: {"title": "Enforce", "start": 85},
    4: {"title": "Attack", "start": 125},
    5: {"title": "Tighten", "start": 215},
    6: {"title": "Prove", "start": 270},
}
END = 300
EXTRA_ACT = 7


@dataclass(frozen=True)
class Step:
    act: int
    at: float
    action: str
    caption: str | None = None
    wait_for: str | None = None          # "plan" | "case" | "diff"
    timeout_s: float = 25.0
    keyview: str | None = None

    @property
    def abs_at(self) -> float:
        return ACTS[self.act]["start"] + self.at


STEPS: list[Step] = [
    # Act 1: Discover (0:00-0:35). No LLM.
    Step(1, 0, "discover_start", "We start by finding what already runs."),
    Step(1, 2, "discover_scan"),
    Step(1, 15, "discover_flags", "One agent had no owner. Another shares a login with a person."),
    Step(1, 21, "discover_assign"),
    Step(1, 29, "noop", keyview="estate-found"),
    # Act 2: Wrap and observe (0:35-1:25). Agent plan prefetched at the start.
    Step(2, 0, "observe_start", "We wrap the existing agent without touching its code."),
    Step(2, 5, "observe_wrap"),
    Step(2, 20, "observe_shadow", "Then we watch, not block: a week of real traffic in shadow mode."),
    Step(2, 35, "observe_groups", "Without this, switching on enforcement would have broken quarter-end close."),
    Step(2, 45, "noop", keyview="watch-before-blocking"),
    # Act 3: Enforce and exception (1:25-2:05). No LLM in the decision path.
    Step(3, 0, "enforce_start", "Normal work flows at machine speed, with no AI in the decision."),
    Step(3, 3, "enforce_routine"),
    Step(3, 20, "enforce_jit", "A real cross-domain need gets two minutes of exactly what it needs, then it expires.",
         keyview="two-minutes"),
    Step(3, 24, "enforce_countdown"),
    Step(3, 34, "enforce_expired"),
    # Act 4: Attack (2:05-3:35).
    Step(4, 0, "attack_note", "This settlement note carries a hidden instruction."),
    Step(4, 10, "attack_plan", "The live model reads it and plans to follow it.", wait_for="plan"),
    Step(4, 25, "attack_today", "Today: nothing stands between a fooled agent and client data.", keyview="today"),
    Step(4, 45, "attack_governed", "Same plan, with the control plane.", keyview="system-held"),
    Step(4, 70, "attack_case", "AI explains what happened. Pre-agreed rules decide what happens next.",
         wait_for="case", keyview="ai-explains"),
    Step(4, 85, "attack_close", "The model was fooled. The system held."),
    # Act 5: Tighten and approve (3:35-4:30).
    Step(5, 0, "tighten_draft", "AI drafts a narrower policy. A verifier checks every change.", wait_for="diff"),
    Step(5, 25, "tighten_replay", "Replayed against last week and twenty attacks: nothing legitimate breaks."),
    Step(5, 35, "tighten_approve", "A person approves. AI never grants.", keyview="tighter"),
    Step(5, 45, "tighten_rerun", "Tighter, and nothing rare broke."),
    # Act 6: Prove and close (4:30-5:00).
    Step(6, 0, "prove_evidence", "Every number here was measured in this run.", keyview="measured"),
    Step(6, 20, "prove_close", "Synthetic estate. Here's what we'd need to run this on yours."),
]

# Captions used when the run takes a branch the default caption would misdescribe.
CAPTIONS = {
    "delegation": "Asking another agent never adds authority.",
    "plan_fallback": "The live model declined. A recorded compromised plan now tests the controls.",
    "close_fallback": "The plan was stopped at every harmful step. The system held.",
    "replay_nothing": "Every proposed change was rejected, so nothing changes. The verifier held the line.",
    "extra": "Not every rogue agent is an attacker.",
    "extra_quarantine": "A runaway loop is quarantined by a volume rule. The owner is paged.",
}
FALLBACK_BANNER = ("The model declined the hidden instruction. Good — but models don't always. "
                   "Replaying a recorded compromised plan to test the controls.")

KEY_VIEWS = [
    {"id": "estate-found", "n": 1, "act": 1, "title": "Estate found",
     "caption": "We found four agents: one with no owner, one on a person's login."},
    {"id": "watch-before-blocking", "n": 2, "act": 2, "title": "Watch before blocking",
     "caption": "We watched before blocking, and found the quarter-end flow we'd have broken."},
    {"id": "two-minutes", "n": 3, "act": 3, "title": "Two minutes, then gone",
     "caption": "A real exception got two minutes of exactly what it needed."},
    {"id": "today", "n": 4, "act": 4, "title": "Today: nothing stops it",
     "caption": "A fooled agent, today: nothing stops it."},
    {"id": "system-held", "n": 5, "act": 4, "title": "The system held",
     "caption": "Same plan through the control plane: three denials, each citing its rule."},
    {"id": "ai-explains", "n": 6, "act": 4, "title": "AI explains, rules act",
     "caption": "AI explained it; pre-agreed rules contained it."},
    {"id": "tighter", "n": 7, "act": 5, "title": "Tighter, nothing broke",
     "caption": "AI drafted a tighter policy; a verifier and a replay proved nothing broke; a person approved."},
    {"id": "measured", "n": 8, "act": 6, "title": "Measured, not claimed",
     "caption": "Every number here was measured in that run."},
]
KEY_VIEW_BY_ID = {k["id"]: k for k in KEY_VIEWS}

CLOSE_ASKS = [
    "How agents authenticate today",
    "Where traffic can be routed through a gateway",
    "Data-classification tags for client and payment data",
    "The owner for each agent",
    "Latency budgets in settlement windows",
]


def scripted_duration() -> float:
    return END
