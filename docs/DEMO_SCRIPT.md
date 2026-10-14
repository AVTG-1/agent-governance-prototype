# Demo script: 5 minutes, self-playing

These captions are the default text in `app/demo/script.py`. The presenter can stay silent and let the captions carry the story, or speak over them. Times are at 1× speed.

## Before the meeting (work laptop)

1. `python run.py`. The browser opens on the connection screen.
2. LLM Foundry is selected by default. Paste a fresh token; the project suffix is `llmproxy-playground`.
3. Keep the recommended models: **Agent** `azure:gpt-4.1-mini`, **Investigator** `bedrock:claude-sonnet-4.5`.
4. Click **Test connection**. Wait for two green ticks, then click **Start demo** when you're ready to present. Press F11 for full screen.

## The run

Each act opens with a 1.5 s title card ("Act 2 · Shadow and learn") and a chip naming the deck chapter it proves, which stays in the header.

| Time | Act | Caption on screen | Say this if you speak |
|---|---|---|---|
| 0:00 | 1 Discover | We start by finding what already runs. | "Four agents connect these systems today." |
| 0:12 | | One agent had no owner. Another shares a login with a person. | "No owner means no one answers for it. A shared login means no one can say who did what." |
| 0:27 | 2 Shadow and learn | We take over all four agents without changing a line of their code. | "Each one gets a different swap, the same four you saw in 'Mediate, don't modify'." |
| 0:44 | | Day zero: only four guardrails, written by people. Everything else is observed. | "No rulebook yet. We don't guess one." |
| 0:52 | | A recorded week replays with enforcement off: watched, not blocked. | "The engine records everything. Nothing is stopped." |
| 1:05 | | One habit breaks a guardrail every night: client data copied to an outside drive. | "Learning from usage alone would have made that a permission." |
| 1:12 | | AI drafts a rulebook from what was recorded. A verifier checks every line. | "That's a real model call. It sees a summary, never the raw traffic." |
| 1:25 | | Replayed against the week: the exports stop, and nothing legitimate breaks. | |
| 1:32 | | The owners approve the rulebook and reject the export. AI never grants. | (Click **Approve**, or let the countdown do it.) |
| 1:42 | | Default deny is on. Only what the rulebook allows now runs. | |
| 1:52 | 3 Enforce | Normal work flows at machine speed, with no AI in the decision. | "Each decision takes well under a millisecond and cites its rule." |
| 2:02 | | A real cross-domain need gets two minutes of exactly what it needs, then it expires. | "Flexibility without standing privilege." |
| 2:22 | 4 Attack | This settlement note carries a hidden instruction. | |
| 2:28 | | The live model reads it and plans to follow it. | "That's a real model call, and it's been fooled." |
| 2:40 | | Today: nothing stands between a fooled agent and client data. | |
| 2:56 | | Same plan, with the control plane. | |
| 2:58 | | Asking another agent never adds authority. | "Its colleague has broader rights, but borrowing them is impossible." |
| 3:20 | | AI explains what happened. Pre-agreed rules decide what happens next. | |
| 3:37 | | The model was fooled. The system held. | |
| 3:47 | 5 Harden | After the incident, AI drafts a hardening. A verifier checks every change. | "Unused access was already gone on day zero. This is only about the incident." |
| 3:59 | | Replayed against the week and twenty attacks: nothing legitimate breaks. | |
| 4:06 | | A person approves. AI never grants. | (Click **Approve**, or let the countdown do it.) |
| 4:16 | | Tighter, and nothing legitimate broke. | |
| 4:32 | 6 Prove | Every number here was measured in this run. | "This is what your second line and your examiners will ask for." |
| 4:50 | | Synthetic estate. Here's what we'd need to run this on yours. | "Five answers, and we can run Acts 1 to 3 on a real slice." |

## After the run: key views

The close card shows **Key views** (or press K). Nothing re-runs and no model is called, so it's instant and safe during Q&A.

| Use | How |
|---|---|
| Answer "show me that again" | K, then click the card (for example **6 The system held**) |
| Retell the story in about a minute | K, click **1**, then press → seven times. Each view has its own caption. |
| Show it later or send it on | *Download key views* saves `key-views-….html`. It opens offline on any laptop, with no token, and is labelled "recorded from a live run". |

Short retelling (≈ 60 s, one line per view):
1. "We found four agents: one with no owner, one on a person's login."
2. "We onboarded all four without code changes and watched a week: a quarter-end flow to protect, and a nightly habit that breaks a guardrail."
3. "AI drafted the rulebook from what was recorded; a verifier and a replay checked it; the owners approved it and rejected the habit."
4. "A real exception got two minutes of exactly what it needed."
5. "A fooled agent, today: nothing stops it."
6. "Same plan through the control plane: three denials, each citing its rule."
7. "AI explained it; pre-agreed rules contained it."
8. "Every number here was measured in that run."

If you only have two minutes in the meeting, run the live demo beforehand on the work laptop, export the key views and present from the file. Say it's a recording of a live run; the banner says so too.

## If something goes wrong

- **The model declined the injection.** The demo says so and replays a labelled recorded plan. Say: "Good model behaviour, but we can't rely on it. Here's what happens when one doesn't refuse."
- **Token expired mid-run.** The demo pauses with a prompt. Paste a fresh token, then resume. The run continues from the same step.
- **Slow model.** A small "waiting for model" indicator appears. Prefetching hides most latency: the rulebook request goes out the moment you click Start. If a call times out, the demo pauses with the reason.
- **Need to repeat a moment.** Click an act in the header to jump, or press R to restart from 0:00.
