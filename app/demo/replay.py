"""Captioned replay (SPEC §5.9): the run just shown, played back in at most 90 seconds with callouts.

Playback only. Nothing re-runs, no model is called and no decision is made: the console folds the run's
own event log on a compressed clock, exactly as key views fold it up to a marker. This module builds the
two pieces of data the player needs, and both travel with key views and the offline export:

- `WARP`: slices of the 300 scripted seconds and how many replay seconds each gets. Important beats
  play slower, dull ones faster.
- callouts: short popups anchored to what they describe, written from templates and filled with this
  run's real numbers. A callout whose facts the run doesn't have (a branch it didn't take) is left out,
  so the replay never states something that didn't happen.
"""
from __future__ import annotations

from app.llm.catalog import short_name

# (from scripted second, to scripted second, replay seconds). Act starts: 0, 25, 80, 110, 140, 225.
WARP: list[tuple[float, float, float]] = [
    (0, 25, 8),       # Act 1 Discover
    (25, 50, 6),      # Act 2 onboarding and guardrails
    (50, 62, 5),      # Act 2 shadow week
    (62, 80, 6),      # Act 2 findings and the AI draft
    (80, 110, 12),    # Act 3 People sign (the heart of the story: slow)
    (110, 140, 7),    # Act 4 Enforce and two-minute access
    (140, 160, 7),    # Act 5 the note and the live plan
    (160, 176, 7),    # Act 5 today mode
    (176, 225, 14),   # Act 5 the same plan through the plane, the case
    (225, 265, 7),    # Act 6 tighten
    (265, 300, 7),    # Act 6 evidence and close
]
MAX_S = 90.0
SHOW_S = 4.2           # how long a callout stays, unless the next one comes sooner


def replay_seconds(t: float) -> float:
    """Scripted second → replay second (piecewise linear over WARP)."""
    r = 0.0
    for a, b, s in WARP:
        if t >= b:
            r += s
        elif t > a:
            return r + (t - a) / (b - a) * s
        else:
            break
    return r


def total_seconds() -> float:
    return sum(s for _, _, s in WARP)


def _last_panel(run, view: str, key: str):
    for ev in reversed(run.events):
        if ev["kind"] == "panel" and ev["payload"]["view"] == view and key in (ev["payload"]["set"] or {}):
            return ev["payload"]["set"][key]
    return None


def _n(x) -> str:
    return f"{x:,}" if isinstance(x, int) else str(x)


def build_callouts(run) -> list[dict]:
    """Each callout: {at (scripted s), anchor (CSS selectors, first found wins), title, text}. Facts come
    only from this run's data; a callout is dropped when its facts are missing."""
    d, w = run.data, run.world
    m = d.get("metrics") or {}
    owner = lambda a: w.registry.get(a).owner if a in w.registry.agents else None  # noqa: E731
    out: list[dict | None] = []

    def add(at, anchor, title, text, need=True):
        out.append({"at": at, "anchor": anchor, "title": title, "text": text} if need else None)

    add(3, [".col-agents"], "Discover",
        "The plane scans vault entries, gateway logs, database sessions, cloud roles and config files. No AI is involved.")
    add(14, ['[data-agent="kyc-agent"]', ".col-agents"], "Who answers for it?",
        f"KYC refresh had no owner, so a rule assigned it to {owner('kyc-agent')}. "
        "Reconciliation shares its login with a person.", need=bool(owner("kyc-agent")))
    add(27, [".band"], "Mediate, don't modify",
        "All four agents now reach their systems through the control plane, each with a new credential. "
        "Not one line of their code changed.")
    add(52, ["#amap-body"], "Watch, don't block",
        f"A recorded week replays with enforcement off: {_n(m.get('shadow_calls'))} calls. Each line is one agent "
        "reaching one system; thicker means used more.", need=m.get("shadow_calls") is not None)
    habit = (d.get("owner_decisions") or [None])[0]
    add(63, ['[data-sys="fileshare"]', ".panel .card"], "A bad habit",
        f"KYC refresh copied client data to the shared drive {habit and habit.get('pattern') or ''} "
        f"({habit and habit['observed']} times). That breaks a firm-wide guardrail.",
        need=bool(habit))
    add(74, [".panel .card.ai", ".panel"], "AI drafts, it doesn't grant",
        f"The AI investigator read a summary, never raw traffic, and drafted {d.get('rulebook_total')} grants. "
        "On its own it can grant nothing.", need=d.get("rulebook_total") is not None)
    lines = d.get("rulebook_lines") or []
    bad = sum(1 for x in lines if not x.ok)
    add(83, [".panel .card.ai", ".panel"], "A verifier checks every line",
        f"Deterministic code, not another model: {d.get('rulebook_ok')} of {d.get('rulebook_total')} grants accepted"
        + (f", {bad} line{'s' if bad != 1 else ''} rejected." if bad else ", nothing rejected."),
        need=d.get("rulebook_ok") is not None)
    rej = (d.get("owner_rejected") or [None])[0]
    add(93, [".panel-over .over", ".panel"], "People sign",
        "The owners sign the rulebook. " + (f"The KYC export is rejected by {rej['by']}, a person, not the AI."
                                            if rej else "AI never approves anything."))
    rr = d.get("rulebook_replay") or {}
    add(104, [".band", ".panel"], "Signed, so enforced",
        f"Default deny is on. Replayed against the week first: {_n(rr.get('legit_broken'))} of "
        f"{_n(rr.get('legit_total'))} legitimate calls broken, {rr.get('violations_stopped')} of "
        f"{rr.get('violations')} breaches stopped.", need="legit_total" in rr)
    add(122, [".panel .env", ".panel"], "Two minutes, then gone",
        "A real one-off need gets read-only access to three fields of one client for two minutes. "
        "Then the same read is refused.", need=d.get("jit_grant") is not None)
    if d.get("plan_source") == "recorded":
        add(148, [".panel .card.sim", ".panel"], "The model declined",
            f"The live model ({short_name(run.models.get('agent', ''))}) refused the hidden instruction. "
            "A labelled recorded plan tests the controls instead.")
    else:
        add(148, [".panel .card.ai", ".panel"], "The model is fooled",
            f"A settlement note hides an instruction. The live model ({short_name(run.models.get('agent', ''))}) "
            "plans to read a client's tax ID and send it outside.", need=d.get("plan_source") == "live")
    today = _last_panel(run, "attack", "today") or {}
    add(171, ['[data-sys="external"]', ".panel .card.deny", ".panel"], "Today: nothing in the path",
        f"Simulated, without the plane: {today.get('outcome')}.", need=bool(today.get("outcome")))
    a4 = d.get("act4") or {}
    add(184, [".band", ".panel"], "The system held",
        f"Same plan through the plane: {a4.get('denied')} of {a4.get('attempted')} calls stopped, each citing its rule. "
        "Asking another agent never adds authority.", need=bool(a4))
    case, c = d.get("case"), d.get("containment")
    add(201, [".panel .card.ai", ".panel"], "AI explains, rules act",
        f"The AI writes the case (suspected cause: {case and case.suspected_cause.replace('_', ' ')}). "
        f"A pre-agreed rule, not the AI, makes the session {c and c.action.replace('_', '-')}.",
        need=bool(case and c))
    acc = d.get("accepted") or []
    add(230, [".panel .card.ai", ".panel"], "Tighter after the incident",
        f"The AI suggests {len(d.get('checks') or [])} narrowing changes; the verifier accepts {len(acc)} and the owner signs."
        if acc else "The AI's suggestions were all rejected by the verifier, so nothing changes.",
        need=d.get("checks") is not None)
    rerun = d.get("rerun") or {}
    add(262, [".panel .card.focus", ".panel"], "The same attack, again",
        f"It now stops at step {rerun.get('stopped_at')}, with {rerun.get('attempted')} call"
        f"{'s' if rerun.get('attempted') != 1 else ''} attempted.", need=bool(rerun.get("stopped_at")))
    add(276, [".panel .evgrid", ".panel"], "Measured, not claimed",
        f"Every number comes from this run: {m.get('attacks_blocked')} of {m.get('attacks_total')} attacks blocked, "
        f"{_n(m.get('legit_broken'))} of {_n(m.get('legit_total'))} legitimate calls broken, hash chain "
        f"{'verified' if m.get('chain_ok') else 'BROKEN'}.", need=bool(m))
    return [x for x in out if x]


def build_replay(run) -> dict:
    """What the player needs: the warp, the callouts (with their replay times) and the total length."""
    callouts = build_callouts(run)
    for i, c in enumerate(callouts):
        c["at_r"] = round(replay_seconds(c["at"]), 2)
        nxt = replay_seconds(callouts[i + 1]["at"]) if i + 1 < len(callouts) else total_seconds()
        c["show_r"] = round(max(1.5, min(SHOW_S, nxt - c["at_r"] - 0.15)), 2)
    return {"warp": [list(x) for x in WARP], "total": total_seconds(), "callouts": callouts}
