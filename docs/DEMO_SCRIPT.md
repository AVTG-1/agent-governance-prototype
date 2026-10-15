# Demo script: 5 minutes, self-playing

These captions are the default text in `app/demo/script.py`. The presenter can stay silent and let the captions carry the story, or speak over them. Times are at 1× speed.

## Before the meeting (work laptop)

1. `python run.py`. The browser opens on the connection screen.
2. LLM Foundry is selected by default. Paste a fresh token; the project suffix is `llmproxy-playground`.
3. Keep the recommended models: **Agent** `azure:gpt-4.1-mini`, **Investigator** `bedrock:claude-sonnet-4.5`.
4. Click **Test connection**. Wait for two green ticks.
5. Optional, recommended before the audience arrives: click **Preflight**. It runs the four real model calls once (rulebook, plan, case, hardening) and shows pass or fail, latency and what came back. If the rulebook fails or is slow, switch the investigator (for example to `azure:gpt-4.1`, which has a JSON mode), test again and re-run Preflight. Nothing is saved.
6. Click **Start demo** when you're ready to present. It always starts at 1×. Press F11 for full screen. Use only one browser tab to drive it; another tab opens as a viewer.

## The run

Each act opens with a 1.5 s title card ("Act 3 of 6 · Nothing enforced unsigned · People sign") naming the deck chapter it proves; the chapter also sits in the act panel's header. The six acts are the ones on the deck's *Prototype* page, in the same words.

The map on the left is the thing to point at: agents on the left, the control plane in the middle, the systems by business area on the right. Every call draws a line; thicker means used more in the recorded week.

| Time | Act | Caption on screen | Say this if you speak |
|---|---|---|---|
| 0:01 | 1 Discover | We start by finding what already runs. | "Four agents connect these systems today. The dotted lines are reach nobody checks." |
| 0:12 | | One agent had no owner. Another shares a login with a person. | "No owner means no one answers for it. A shared login means no one can say who did what." |
| 0:26 | 2 Shadow and learn | We take over all four agents without changing a line of their code. | "Each one gets a different swap, the same four you saw in 'Mediate, don't modify'." |
| 0:43 | | Day zero: only four guardrails, written by people. Everything else is observed. | "No rulebook yet. We don't guess one." |
| 0:50 | | A recorded week replays with enforcement off: watched, not blocked. | "Watch the map fill in: that's who reaches what, measured." |
| 1:02 | | One habit breaks a guardrail every night: client data copied to an outside drive. | "Learning from usage alone would have made that a permission." |
| 1:09 | | AI drafts a rulebook from what was recorded. It cannot grant anything. | "That's a real model call. It sees a summary, never the raw traffic." |
| 1:21 | 3 People sign | A verifier checks every line the AI drafted. | "Deterministic code, not another model." |
| 1:28 | | Replayed against the week: the exports stop, and nothing legitimate breaks. | |
| 1:33 | | The owners sign the rulebook and reject the export. AI never approves. | (Click **Sign**, or let the countdown do it.) "The kyc line turns red: the owner said no, not the AI." |
| 1:43 | | Signed, so enforced: default deny is on. Only what the rulebook allows now runs. | |
| 1:51 | 4 Enforce | Normal work flows at machine speed, with no AI in the decision. | "Each decision takes well under a millisecond and cites its rule." |
| 2:02 | | A real cross-domain need gets two minutes of exactly what it needs, then it expires. | "Flexibility without standing privilege." |
| 2:21 | 5 Attack | This settlement note carries a hidden instruction. | |
| 2:28 | | The live model reads it and plans to follow it. | "That's a real model call, and it's been fooled." |
| 2:40 | | Today: nothing stands between a fooled agent and client data. | "The red dashed lines go straight through: nothing in the path." |
| 2:56 | | Same plan, with the control plane. | "Now the lines stop at the plane." |
| 2:58 | | Asking another agent never adds authority. | "Its colleague has broader rights, but borrowing them is impossible." |
| 3:20 | | AI explains what happened. Pre-agreed rules decide what happens next. | |
| 3:37 | | The model was fooled. The system held. | |
| 3:46 | 6 Tighten and prove | After the incident, AI suggests tighter rules. A verifier checks every change. | "Unused access was already gone on day zero. This is only about the incident." |
| 3:59 | | Replayed against the week and twenty attacks: nothing legitimate breaks. | |
| 4:06 | | The owner signs. AI never approves. | (Click **Sign**, or let the countdown do it.) |
| 4:16 | | Tighter, and nothing legitimate broke. | |
| 4:31 | | Every number here was measured in this run. | "This is what your second line and your examiners will ask for." |
| 4:50 | | Synthetic estate. Here's what we'd need to run this on yours. | "Five answers, and we can run Acts 1 to 3 on a real slice." |

Captions describe what actually happened. If the live model drafts something different (for example it tries to grant the export, or misses the quarter-end grant), the verifier shows ✗ on that line, the replay counts what would break, and the caption changes to say so. Don't read the expected script over a different result.

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
3. "AI drafted the rulebook from what was recorded; a verifier and a replay checked it; the owners signed it and rejected the habit."
4. "A real exception got two minutes of exactly what it needed."
5. "A fooled agent, today: nothing stops it."
6. "Same plan through the control plane: three denials, each citing its rule."
7. "AI explained it; pre-agreed rules contained it."
8. "Every number here was measured in that run."

If you only have two minutes in the meeting, run the live demo beforehand on the work laptop, export the key views and present from the file. Say it's a recording of a live run; the banner says so too.

## If something goes wrong

- **A model call failed or was cut off.** The run pauses with a card over the act panel that names the call and when it's needed. **Retry** re-sends it. **Switch model** picks another model that passed a live test (an untested one is tested first). **Restart** starts over. The terminal shows the raw reply for diagnosis. Say: "The model misbehaved; the demo won't invent a result."
- **The model declined the injection.** The demo says so and replays a labelled recorded plan. Say: "Good model behaviour, but we can't rely on it. Here's what happens when one doesn't refuse."
- **Token expired mid-run.** The same card asks for a fresh token; paste it and the run continues from the same step.
- **Rate-limited (429).** The demo waits a few seconds and tries once more, then pauses with the reason. Wait, then Retry.
- **Slow model.** The readiness lights on the right of the ticker show each call (not sent, in flight, ready). If a result is late, the clock holds and a "waiting for model" card appears; nothing skips ahead. Prefetching hides most latency: the rulebook request goes out the moment you click Start. At 2× there is half the time to hide it.
- **Laptop slept or Wi-Fi dropped.** The console reconnects by itself and catches up from the run's log; a "reconnecting…" note shows meanwhile.
- **Need to repeat a moment.** Click an act in the header to jump, or press R to restart from 0:00. L opens every decision so far; click a line or an agent on the map to filter them.
