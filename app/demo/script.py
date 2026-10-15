"""The 5-minute story as data: acts, timed steps, captions, deck chapters and the eight key views.

`at` is seconds from the start of the act at 1x speed. Each step names an action in acts.py.
`wait_for` names a prefetched LLM result the step needs; `keyview` marks a key-view moment
(SPEC §5.8) emitted after the step's action; `deck` names the proposal-deck chapter the step
proves (shown as a chip in the header). Captions here are the only caption source.
"""
from __future__ import annotations

from dataclasses import dataclass

# Act names, one-line gists and deck chapters follow the deck's "Prototype" chapter (the five-minute run).
ACTS = {
    1: {"title": "Discover", "gist": "Find every agent", "start": 0, "deck": "The estate today",
        "sub": "The plane scans the bank and finds four agents, and who answers for each."},
    2: {"title": "Shadow and learn", "gist": "Watch, don't block", "start": 25, "deck": "Rolling it out",
        "sub": "All four agents are wrapped without changing their code. A week is watched, nothing is blocked, "
               "and the AI drafts a rulebook from what it saw."},
    3: {"title": "People sign", "gist": "Nothing enforced unsigned", "start": 80, "deck": "Human in the loop",
        "sub": "A verifier checks the draft. The owners sign it, and reject a bad habit an agent had picked up."},
    4: {"title": "Enforce", "gist": "Normal work flows", "start": 110, "deck": "The control plane",
        "sub": "Routine calls go straight through, each citing its rule. A real one-off need gets two minutes."},
    5: {"title": "Attack", "gist": "The model is fooled", "start": 140, "deck": "Catching a rogue agent",
        "sub": "A settlement note hides an instruction and the live model follows it. Today, then with the plane."},
    6: {"title": "Tighten and prove", "gist": "Signed, measured", "start": 225, "deck": "Optimising permissions",
        "sub": "The AI suggests tighter rules after the incident; the owner signs. Every number is measured from this run."},
}
END = 300
INTRO_S = 1.5
EXTRA_ACT = 7


@dataclass(frozen=True)
class Step:
    act: int
    at: float
    action: str
    caption: str | None = None
    wait_for: str | None = None          # "rulebook" | "plan" | "case" | "diff"
    timeout_s: float = 25.0
    keyview: str | None = None
    deck: str | None = None              # deck chapter this step proves (chip in the header)

    @property
    def abs_at(self) -> float:
        return ACTS[self.act]["start"] + self.at


STEPS: list[Step] = [
    # Act 1: Discover (0:00-0:25). No LLM.
    Step(1, 1.5, "discover_start", "We start by finding what already runs."),
    Step(1, 2.5, "discover_scan"),
    Step(1, 12, "discover_flags", "One agent had no owner. Another shares a login with a person."),
    Step(1, 16, "discover_assign"),
    Step(1, 21, "noop", keyview="estate-found"),
    # Act 2: Shadow and learn (0:25-1:20). Day zero. The rulebook draft was prefetched at Start.
    Step(2, 1.5, "onboard_start", "We take over all four agents without changing a line of their code.",
         deck="Agents we can't see inside"),
    Step(2, 3, "onboard_swaps"),
    Step(2, 18, "guardrails", "Day zero: only four guardrails, written by people. Everything else is observed.",
         deck="Who decides"),
    Step(2, 25, "shadow_week", "A recorded week replays with enforcement off: watched, not blocked.", deck="Rolling it out"),
    Step(2, 37, "shadow_findings", "One habit breaks a guardrail every night: client data copied to an outside drive.",
         keyview="watch-before-blocking"),
    Step(2, 44, "rulebook_draft", "AI drafts a rulebook from what was recorded. It cannot grant anything.",
         wait_for="rulebook", deck="Who decides"),
    # Act 3: People sign (1:20-1:50). Nothing is enforced until a person signs.
    Step(3, 1.5, "rulebook_verify", "A verifier checks every line the AI drafted."),
    Step(3, 8, "rulebook_replay", "Replayed against the week: the exports stop, and nothing legitimate breaks."),
    Step(3, 13, "rulebook_approve", "The owners sign the rulebook and reject the export. AI never approves."),
    Step(3, 23, "default_deny_on", "Signed, so enforced: default deny is on. Only what the rulebook allows now runs.",
         keyview="rulebook"),
    # Act 4: Enforce (1:50-2:20). No LLM in the decision path.
    Step(4, 1.5, "enforce_start", "Normal work flows at machine speed, with no AI in the decision."),
    Step(4, 2.5, "enforce_routine"),
    Step(4, 12, "enforce_jit", "A real cross-domain need gets two minutes of exactly what it needs, then it expires.",
         keyview="two-minutes"),
    Step(4, 15, "enforce_countdown"),
    Step(4, 25, "enforce_expired"),
    # Act 5: Attack (2:20-3:45).
    Step(5, 1.5, "attack_note", "This settlement note carries a hidden instruction."),
    Step(5, 8, "attack_plan", "The live model reads it and plans to follow it.", wait_for="plan"),
    Step(5, 20, "attack_today", "Today: nothing stands between a fooled agent and client data.", keyview="today"),
    Step(5, 36, "attack_governed", "Same plan, with the control plane.", keyview="system-held"),
    Step(5, 60, "attack_case", "AI explains what happened. Pre-agreed rules decide what happens next.",
         wait_for="case", keyview="ai-explains", deck="Catching a rogue agent"),
    Step(5, 77, "attack_close", "The model was fooled. The system held."),
    # Act 6: Tighten and prove (3:45-5:00). Post-incident only; unused grants were already left out on day zero.
    Step(6, 1.5, "harden_draft", "After the incident, AI suggests tighter rules. A verifier checks every change.",
         wait_for="diff"),
    Step(6, 14, "harden_replay", "Replayed against the week and twenty attacks: nothing legitimate breaks."),
    Step(6, 21, "harden_approve", "The owner signs. AI never approves.", deck="Human in the loop"),
    Step(6, 31, "harden_rerun", "Tighter, and nothing legitimate broke.", deck="Optimising permissions"),
    Step(6, 46, "prove_evidence", "Every number here was measured in this run.", keyview="measured",
         deck="What's being asked"),
    Step(6, 65, "prove_close", "Synthetic estate. Here's what we'd need to run this on yours."),
]

# Captions used when the run takes a branch the default caption would misdescribe.
CAPTIONS = {
    "delegation": "Asking another agent never adds authority.",
    "plan_fallback": "The live model declined. A recorded compromised plan now tests the controls.",
    "close_fallback": "The plan was stopped at every harmful step. The system held.",
    "harden_nothing": "Every proposed change was rejected, so nothing changes. The verifier held the line.",
    "rulebook_broken": "Replayed against the week: the exports stop, and the replay shows exactly what else would.",
    "rulebook_exports_pass": "Replayed against the week: the replay shows exactly what this draft would let through.",
    "verify_rejects": "A verifier checks every line the AI drafted, and rejects what it cannot back up.",
    "extra": "Not every rogue agent is an attacker.",
    "extra_quarantine": "A runaway loop is quarantined by a volume rule. The owner is paged.",
}
FALLBACK_BANNER = ("The model declined the hidden instruction. Good — but models don't always. "
                   "Replaying a recorded compromised plan to test the controls.")

KEY_VIEWS = [
    {"id": "estate-found", "n": 1, "act": 1, "title": "Estate found",
     "caption": "We found four agents: one with no owner, one on a person's login."},
    {"id": "watch-before-blocking", "n": 2, "act": 2, "title": "Watch before blocking",
     "caption": "All four onboarded with no code change; a week watched, a rare flow to protect and a habit that breaks a guardrail."},
    {"id": "rulebook", "n": 3, "act": 3, "title": "AI drafts the rulebook, a person signs",
     "caption": "AI drafted the rulebook from what was recorded; a verifier and a replay checked it; the owners signed it and rejected the habit."},
    {"id": "two-minutes", "n": 4, "act": 4, "title": "Two minutes, then gone",
     "caption": "A real exception got two minutes of exactly what it needed."},
    {"id": "today", "n": 5, "act": 5, "title": "Today: nothing stops it",
     "caption": "A fooled agent, today: nothing stops it."},
    {"id": "system-held", "n": 6, "act": 5, "title": "The system held",
     "caption": "Same plan through the control plane: three denials, each citing its rule."},
    {"id": "ai-explains", "n": 7, "act": 5, "title": "AI explains, rules act",
     "caption": "AI explained it; pre-agreed rules contained it."},
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
