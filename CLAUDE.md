# CLAUDE.md — instructions for Claude Code

You are building a **5-minute, mostly hands-off demo prototype** of an AI-agent governance control plane for a capital-markets client. Read this file fully, then `SPEC.md`, then `docs/TASKS.md`, and work through the milestones in order.

## The one rule that shapes everything: core, not plumbing

This is a demo prototype, not a commercial product. Spend effort on the things the audience sees and the logic that makes the story true. Spend almost none on infrastructure.

**Core (do this well):**
- The policy decision logic and its invariants (`app/core/`): default deny, delegation can only narrow, restricted data never leaves, AI can never grant access, envelopes are bounded, right-sizing protects rare-but-required grants.
- The demo director: a deterministic, timed state machine that plays the 5-minute story with almost no presenter input.
- The single-screen console UI: clear, calm, legible on a projector, matching `docs/DESIGN.md`.
- The two live LLM roles (the agent that gets fooled; the investigator that explains and drafts a narrower policy) and their prompts.
- Honest, measured numbers on the final evidence screen (taken from the actual run, not hard-coded).
- Key views after the run (SPEC §5.8): the presenter jumps back to eight key moments of the run just shown, or exports them as one offline HTML file. Build the UI as a pure reducer of the event log and this comes almost free. Don't add snapshots, screenshots or a second renderer.

**Plumbing (keep minimal or skip):**
- No database server. SQLite file or in-memory data is fine. JSON fixtures are fine.
- No auth system, user accounts, RBAC for the app itself, multi-tenancy, Docker, Kubernetes, CI pipelines, message queues, ORMs, migrations or caching layers.
- No frontend build step. Plain HTML, CSS and ES-module JavaScript served by the Python app. No React, no npm.
- No real SPIFFE, OPA, Cedar, Envoy or Keycloak. Implement small, readable Python equivalents of the behaviour and label them on screen with what production would use (for example "policy engine (Cedar in production)").
- No retries/backoff frameworks, no plugin systems, no abstraction layers "for later". One provider module, a few functions.

If you are unsure whether something is core or plumbing: would the client notice it in the 5-minute demo, or would it change whether the story is true? If neither, skip it or do the simplest thing.

## Hard constraints

1. **No secrets in the repo, ever.** No API keys or tokens in code, docs, tests, fixtures, comments, `.env` files or commit messages. Use the placeholder `<YOUR_FOUNDRY_TOKEN>` in docs. Any example token in old notes is expired and must not be copied. Run `python scripts/check_no_secrets.py` before every commit; it must pass.
2. **The demo cannot start without a live, user-pasted key.** On launch the app shows a connection screen. The presenter picks a provider (**LLM Foundry, default and recommended**, or OpenRouter), pastes a token, and clicks *Test connection*. A real call to each selected model must succeed before *Start demo* is enabled. There is no environment-variable or file-based way to supply the token, and no "skip" button. Key views (SPEC §5.8) aren't an exception: they only replay a run that already passed the gate, are always labelled as recorded, and can't start a run.
3. **Tokens live only in server memory** for the life of the process. Never write them to disk, logs, the event stream, error messages or the browser's storage. Mask them in the UI (show last 4 characters at most). If a call returns 401/403 mid-demo, pause the demo and ask for a fresh token.
4. **The mock LLM is for automated tests only.** `app/llm/mock.py` may exist for `pytest`, selected only by test fixtures. It must not be reachable from the UI or from any setting a presenter can change.
5. **Never fake a live result silently.** If an LLM call fails, pause and say so plainly. The one sanctioned fallback is in SPEC §5.5 (the agent resists the injection): it is shown on screen as a recorded plan, clearly labelled.
6. **You cannot reach LLM Foundry from this environment.** Foundry is only reachable from the presenter's work laptop. Do not try to call `llmfoundry.straive.com`. Build against the documented request shapes in `docs/LLM_PROVIDERS.md`, test with the mock, and keep `scripts/probe_llm.py` working so the presenter can verify connectivity on the laptop.
7. **Target machine:** Windows work laptop with Python (conda or venv), possibly behind a corporate proxy. Use `pathlib`, no bash-only scripts, no symlinks. `python run.py` must start everything and open the browser. Respect `HTTPS_PROXY` and an optional CA bundle path (see `docs/LLM_PROVIDERS.md`).
8. **Dependencies:** keep to `requirements.txt` (FastAPI, Uvicorn, httpx, pydantic, pytest). Ask before adding anything else, and never add anything that needs a compiler or Node.
9. **Synthetic data only.** No real client names, people, identifiers or schemas. The fictional firm is "Kaiyo Securities".

## Commands

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
python run.py                         # starts the app on http://127.0.0.1:8765 and opens the browser
python -m pytest -q                   # all tests (use the mock LLM; no network)
python scripts/check_no_secrets.py    # must pass before every commit
python scripts/probe_llm.py --provider foundry --model gpt-4.1-mini   # presenter-only, on the work laptop
```

## How to work

- Follow `docs/TASKS.md` milestone by milestone. Each milestone ends with its acceptance checks passing; commit after each one with a clear message.
- Write tests for the core invariants first (`tests/test_policy.py` etc.). They are the proof that the story is true.
- Keep modules small and readable; a reviewer should understand the policy engine in five minutes.
- When you finish a milestone, update the checklist in `docs/TASKS.md`.
- If the spec is ambiguous, choose the option that makes the 5-minute demo clearer and note the decision in `docs/DECISIONS.md` (create it if needed). Do not stop to ask unless a decision is irreversible.
- Do not edit `reference/`; it is background material. `SPEC.md` wins over anything in `reference/`.

## Definition of done

- `python run.py` on a fresh Windows Python environment opens the connection screen.
- With a valid Foundry token, *Test connection* passes and *Start demo* plays the full story in 5:00 ± 0:20 with at most two optional presenter clicks (the owners' signatures in Acts 3 and 6, each of which auto-signs after an 8-second countdown, labelled "auto-signed for demo").
- After the run, **Key views** shows all eight moments instantly, and *Download key views* produces an offline, token-free HTML file labelled as a recording.
- All tests pass offline. `check_no_secrets.py` passes. No token is stored anywhere but process memory.
- The UI matches `docs/DESIGN.md` in light and dark mode and is legible at 1440×900 and 1920×1080.
