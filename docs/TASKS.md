# Build plan

Work top to bottom. Tick each box when its acceptance checks pass, then commit. Keep commits small and messages clear.

## M0 — Skeleton (keep it tiny)
- [x] `requirements.txt` installs cleanly; `run.py` starts Uvicorn on `127.0.0.1:8765` and opens the browser.
- [x] `/` serves `web/index.html` with `web/tokens.css` and the fonts from `design/` copied into `web/`.
- [x] `scripts/check_no_secrets.py` exists and passes; `pytest -q` runs (even with one placeholder test).

**Accept:** `python run.py` shows a styled placeholder page; both commands pass.

## M1 — Synthetic estate
- [x] `scripts/gen_fixtures.py` (seed 42) writes the data described in SPEC §3.4 to `app/estate/data/`.
- [x] `app/estate/systems.py` exposes simple read/update functions per system. PII columns are tagged.
- [x] The poisoned note on `T-1097` exists verbatim, and the shadow week reproduces **586 allowed / 14 would-deny** under the initial policy (13 refdata, 1 quarter-end).

**Accept:** tests assert the fixture counts and the shadow outcome.

## M2 — Governance core (the most important milestone)
- [x] Request envelope and decision models (SPEC §6.1–6.2).
- [x] Rules as data with ids and versions (SPEC §6.3). Policy engine with enforce and shadow modes.
- [x] Delegation intersection, JIT envelopes on a demo clock, containment actions, verifier, right-sizing, audit hash chain.
- [x] One test per invariant in SPEC §6.4, plus the three Act 4 denials with the exact rule ids.

**Accept:** `pytest -q` is green. Reading `policy_engine.py` takes under five minutes.

## M3 — LLM client
- [x] `app/llm/catalog.py` from `docs/LLM_PROVIDERS.md`.
- [x] Foundry: azure, openai, bedrock and gemini request builders and parsers, with non-stream first and stream fallback. OpenRouter. Unified `complete()` and `test_model()`.
- [x] `mock.py` for tests only. Tests prove it is not reachable from any route.
- [x] Parser unit tests with captured-style samples for each family, including the streaming variants.
- [x] `scripts/probe_llm.py`, which takes the token via `getpass` only.

**Accept:** parser tests are green. Grep confirms no route imports `mock`.

## M4 — Connection gate
- [x] The screen in SPEC §4.1, with Foundry selected by default and the recommended models preselected.
- [x] `secrets_store` holds the token in memory only; *Forget token* clears it; the UI shows a masked token.
- [x] `POST /api/demo/start` returns 409 until both role tests pass in this process.
- [x] `tests/test_no_token_leak.py` passes.

**Accept:** without a passing test the Start button is disabled and the API refuses; after a mocked pass (in tests) it starts.

## M5 — Director, script and stream
- [x] `app/demo/script.py` holds every step and caption from `docs/DEMO_SCRIPT.md` with SPEC §5 timings.
- [x] The director supports play, pause, next step, jump to act, restart and speed (0.5×, 1×, 2×), plus prefetch and `wait_for` with timeout and a visible pause on error.
- [x] The SSE stream carries events per `docs/ARCHITECTURE.md`.
- [x] `tests/test_director_timing.py` runs the full script with the mock LLM at high speed and asserts the total scripted duration is 300 s ± 20 s and that every act is reached.

**Accept:** the timing test is green; restart fully resets state.

## M6 — Console UI
- [x] Build the UI as a pure reducer of events: `state = events.reduce(apply, initialState)`, then `render(state)`. Keep no state outside it. Key views (M8) depend on this, so get it right here.
- [x] The layout in SPEC §4.2 and `docs/DESIGN.md`: header with act progress and controls, estate map, live timeline, act panel, caption bar.
- [x] Per-act panels: registry, wrap strip plus shadow counters, enforcement plus envelope countdown, poisoned note plus plan plus capability intersection plus case, diff plus verifier plus replay plus approval modal, evidence.
- [x] Light and dark themes (D key); keyboard controls; legible at 1440×900 and 1920×1080 with no page scroll.

**Accept:** manual check against the DESIGN checklist; screenshot both themes into `docs/screens/` if a headless browser is available.

## M7 — Story details that make it credible
- [x] Today mode with dashed bypass edges and the red outcome.
- [x] The agent-resists fallback with the exact banner text from SPEC §5.4.
- [x] The verifier shows a real ✓/✗ per change; replay computes "0 of 600 broken" and "20 of 20 blocked".
- [x] Owner approval modal with an 8 s auto-approve countdown, labelled.
- [x] Evidence numbers computed from the run; downloadable Markdown and JSON pack with a verifiable hash chain.
- [x] The *Extra: malfunction* button (SPEC §5.7).

**Accept:** a full mocked run produces an evidence pack whose chain verifies in a test.

## M8 — Key views (SPEC §5.8)
- [x] `KEY_VIEWS` in `app/demo/script.py`: eight entries with id, title, caption and the step that emits the `keyview` marker event.
- [x] `app/demo/keyviews.py` keeps the last completed run's event log and markers in memory. `GET /api/keyviews` lists them; `GET /api/keyviews/export` returns the self-contained HTML file.
- [x] UI: a **Key views** button (K) after the close card, the filmstrip, key-view mode with the "recorded from this run" badge, ←/→/Esc, animations off and frozen countdowns.
- [x] Export: string-assembled HTML with inlined assets and `window.__REPLAY__`. It opens offline in key-view mode with the recording banner and makes no network requests.
- [x] `tests/test_keyviews.py`: a mocked full run produces exactly eight markers in order. Listing and exporting make no LLM calls and add no decision events. The exported file contains no token (use the fake token from the leak test), no `http://` or `https://` asset URLs, and the "playback only" label. `/api/keyviews` returns 404 before any run reaches Act 6.

**Accept:** after a mocked run, every key view renders the expected panel. Open the exported file from disk in a headless browser if one is available and screenshot views 4, 5 and 7 into `docs/screens/`.

## M9 — Hand-off
- [x] README "Run on the work laptop" steps checked line by line (Windows paths, venv or conda, proxy note).
- [x] `docs/DECISIONS.md` lists any spec interpretations you made.
- [x] A final pass removes dead code, unused files and any abstraction that isn't needed for the demo.

**Accept:** fresh clone, install, `python run.py`: the connection screen appears. All tests and the secrets check pass.

---

# Round 2: day-zero onboarding and the deck-matched console

## M10 — Day-zero core
- [x] Fixtures: a recorded week for all four agents (1,154 calls) including the quarter-end ledger read, recon's delegated reads, settlement's SSI amendments and purpose-bound PII reads, and kyc's nightly PII export to the external shared drive (the planted bad habit). Owner declarations and the old credentials' entitlements in `signals.json`; 90-day usage for all four agents.
- [x] Onboarding swaps for all four agents with the deck's wording; attribution per agent.
- [x] `rulebook@v0`: guardrails only (`R-EGR-01`, `R-SSI-01`, `R-DLG-02`, `R-SELF-01`), default deny off, `R-OBS-00` observe for everything else.
- [x] `app/core/rulebook.py`: aggregated usage summary from the engine's shadow records, the rulebook JSON contract, the deterministic verifier (observed use or declared purpose, no guardrail broken, restricted data purpose-bound, valid references, protected flows and unflagged guardrail habits listed), building `rulebook@v1`, and the week replay.
- [x] Tests: verifier rules for the rulebook; the kyc bad habit is never auto-granted; shadow outcome 1,141 / 7 / 6; invariants still hold under the new rulebook.

**Accept:** `pytest -q` is green; a good draft verifies all ✓ and replays 0 legitimate calls broken with the 7 exports blocked.

## M11 — The new story in the director
- [x] `investigator_rulebook.md` prompt; the rulebook call prefetched at Start (four live calls per run).
- [x] Act 2 "Shadow and learn": onboard, guardrails, shadow week, AI draft, verifier, replay, owner approval (owner rejects the export), default deny on.
- [x] Act 5 hardening only (restrict client-data delegation; human for `env-recon-cm-01` for 7 days). Acts 3, 4 and 6 as before; every evidence number recomputed.
- [x] Eight key views, with "AI drafts the rulebook, a person approves" replacing "Tighter, nothing broke".
- [x] Tests: timing within budget (300 ± 20 s scripted), prefetch order, the rulebook prompt contains no token, key views.

**Accept:** a mocked full run reaches every act in 5:00 and the evidence pack verifies.

## M12 — Console matches the deck
- [x] Deck chrome: deep navy header and caption in both themes, soft glow washes, card styles and shadows, rounded nodes, exact colour semantics (blue control, green allowed, red stopped, amber waits for a person, purple dashed AI advisory, grey dashed simulated); every status is icon plus word plus colour.
- [x] The estate map is the deck's control-plane diagram with the six parts named as in the deck and a moving decision dot.
- [x] Act intro cards and the "Deck: …" chapter chip; one focal point per step; purposeful motion only; `prefers-reduced-motion` honoured.
- [x] Connection screen and close card redesigned to the same standard.
- [x] Screenshots of every step at 1440×900 and 1920×1080 in both themes compared against the deck; overflow sweep clean; final set in `docs/screens/`.

**Accept:** someone who has just seen the deck recognises every screen as the same product.

# Round 3: live-test fixes and a calmer console

## M13 — Live-test fixes, the agent-action map, robustness
- [x] Bug (a): pasted token and suffix cleaned (whitespace, invisible characters); other non-ASCII refused with a plain gate message, never a 500; the masked value is never sent back. Test pastes `·`, `•`, a newline and a trailing space.
- [x] Bug (b): every contract robust: fences and prose stripped, outermost object, trailing commas, cut-off detection (stop reason or unclosed object), larger output budget, compact rulebook contract, JSON mode where it exists, one retry with the parse error, raw reply printed to the terminal. Parser tests for fenced, truncated, prose-wrapped and trailing-comma replies.
- [x] Bug (c): the pause card names the failed call and when it is needed, with Retry (re-send), Switch model (tested live first) and Restart.
- [x] Bug (d): nothing needs scrolling during autoplay; drawers scroll with wheel, trackpad, touch and keyboard, with a visible scrollbar.
- [x] Bug (e): the caption has a fixed height; errors, pauses and signatures float over the act panel and never change the layout.
- [x] Two areas and a ticker: the agent-action map (60%), the act panel (40%), the caption and a one-row decision ticker; the full timeline is a drawer (L). Header: title, stepper, clock, controls only.
- [x] The agent-action map: agents → plane band (six parts) → systems by business area; edges by decision, thickness by shadow-week usage; unknown in Act 1, filled in by Act 2, kyc export red when rejected, the attack path stopping at the plane; click to filter; in key views and the export.
- [x] Acts and deck chips follow the updated deck (Prototype chapter; chapter 4 "Human in the loop"): Discover, Shadow and learn, People sign, Enforce, Attack, Tighten and prove. Still 5:00.
- [x] Robustness: readiness lights per call; the clock holds for a late result; a fresh Start plays at 1×; optional Preflight of the four contracts; late replies from an old run dropped; one controlling tab, others view; a double-clicked Start is one run; SSE reconnect and resync; 429 back-off once; 401 resumes the same step; approvals work at 0.5×, 1× and 2×.
- [x] Sweep: every step at 1280×720, 1366×768, 1536×864 and 1920×1080, at 90/100/110% zoom, in both themes: no overflow, nothing clipped.

**Accept:** `pytest -q` is green; the sweep is clean; a mocked run plays all six acts in 5:00; the key-views export works offline with the map.

# Round 4: captioned replay

## M14 — A self-playing, captioned replay of the run
- [x] Time-warp table: the 300 scripted seconds in at most 90 s, slower for important beats (`app/demo/replay.py`).
- [x] About seventeen callouts anchored to what they describe, templated from this run's facts; branch-aware; nothing stated that didn't happen.
- [x] Player in the console: progress bar with acts and callouts, play/pause, previous/next callout, restart, seek, start and end cards, labelled as a recording.
- [x] Available on the close card and filmstrip (P), and in the offline export (opens on the start card).
- [x] Tests: length ≤ 90 s, contiguous warp, callout spacing, facts match the run's metrics, the resisted-plan branch, export carries it with no token, no model call.

**Accept:** after a mocked run, the replay plays in 86 s with every callout in view at 1280×720, 1366×768, 1440×900 and 1920×1080; the exported file plays it offline with no network requests.
