# Architecture (deliberately small)

One Python process serves an API, a Server-Sent Events (SSE) stream and static files. Everything else is in-process.

```
browser (web/)  ──HTTP──▶  FastAPI (app/main.py)
      ▲                        │
      └──── SSE /api/stream ◀──┤  event bus (asyncio queue fan-out)
                               │
            demo director ─────┤  (app/demo/director.py: timed step list, pause/resume/seek)
                │              │
                ▼              ▼
     simulated estate     governance core                LLM client
     (app/estate/)        (app/core/)                    (app/llm/)
     systems, agents,     identity · gateway · policy    foundry · openrouter
     fixtures             delegation · envelopes         (mock for tests only)
                          verifier · rightsizing · audit
```

## Folder layout

```
run.py                     # starts uvicorn on 127.0.0.1:8765 and opens the browser
requirements.txt
app/
  main.py                  # routes: /, /api/connection/*, /api/demo/*, /api/stream, /api/evidence, /api/keyviews*
  settings.py              # non-secret settings only (port, base URL, defaults, CA bundle path)
  secrets_store.py         # in-memory token holder: set / get / clear / masked(); nothing else
  events.py                # Event model, bus, hash chain
  llm/
    __init__.py            # complete(), test_model()
    catalog.py             # model table from docs/LLM_PROVIDERS.md
    foundry.py             # azure / openai / bedrock / gemini request + parse functions
    openrouter.py
    mock.py                # TESTS ONLY, never importable from routes or UI
  core/
    identity.py            # registry, credentials (shared → brokered), sessions, attribution level
    policies.py            # rules as data, with id + version
    policy_engine.py       # evaluate(envelope) -> Decision; shadow vs enforce
    delegation.py          # capability intersection
    envelopes.py           # JIT envelopes, TTL on a demo clock
    gateway.py             # normalise action -> envelope -> decide -> (execute | block) -> log
    containment.py         # fixed allowed actions, applied by rules
    verifier.py            # checks LLM policy diffs: narrow-only, protected grants, references valid
    rulebook.py            # day zero: usage summary from shadow records, rulebook verifier, rulebook@v1
    rightsizing.py         # usage + calendar tags -> candidate removals (used to brief the LLM and to check it)
    audit.py               # decision records, hash chain, evidence pack builder
    world.py               # one run's estate + registry + policy + audit + gateway (restart builds a new one)
  estate/
    systems.py             # tiny functions per system over fixtures
    agents.py              # scripted agents + the LLM-driven recon agent wrapper
    data/                  # generated fixtures (JSON or SQLite)
  demo/
    script.py              # the 5-minute step list: timings, captions, actions
    director.py            # plays script.py; prefetches LLM calls; pause/seek/speed
    acts.py                # what each scripted step does (calls the core, emits events)
    keyviews.py            # last completed run's events + key-view markers; builds the export HTML (SPEC §5.8)
    recorded_plan.json     # the ONLY sanctioned fallback (SPEC §5.4), shown as "recorded plan"
  prompts/
    recon_agent.md
    investigator_case.md
    investigator_diff.md
web/
  index.html  app.js  styles.css  tokens.css  fonts/
scripts/
  gen_fixtures.py  probe_llm.py  check_no_secrets.py
tests/
  test_policy.py  test_delegation.py  test_envelopes.py  test_verifier.py
  test_audit_chain.py  test_shadow.py  test_llm_parsers.py  test_director_timing.py  test_no_token_leak.py  test_keyviews.py
```

## Key flows

**Connection gate**
1. `POST /api/connection/test` with `{provider, token, project, models}`.
2. The server stores the token in `secrets_store`, calls `test_model` for each role, and returns per-model results.
3. `POST /api/demo/start` is refused (HTTP 409) unless the latest tests for both roles passed in this process.

**Every agent action**
1. Agent intent becomes a tool call.
2. `gateway.normalise` builds the request envelope (SPEC §6.1).
3. `policy_engine.evaluate` returns a decision (allow, deny, hold or would-deny).
4. The gateway executes or blocks.
5. `audit.record` hash-chains the record and the bus publishes the event.
6. The UI updates the map, timeline and panel.

**Today mode:** the same tool calls go straight to `estate.systems` with no gateway. The events are tagged `mode: "ungoverned"` so the UI draws dashed bypass edges.

**Director**
- `script.py` is a list of `Step(act, at_s, caption, action, wait_for=None, timeout_s=25)`.
- The director runs on an asyncio loop with a speed factor and supports pause, resume, next step, jump to act and restart.
- Restart resets the estate, policies, audit log and demo clock to their initial state. The token and connection status stay.

**Prefetch**
- The investigator's rulebook draft is requested at Start (the fixtures are deterministic).
- The agent plan is requested at the start of Act 2.
- The investigator's case is requested at the first Act 4 denial.
- The investigator's hardening diff is requested as soon as the case is ready.
- Results are cached per run.

**Key views (SPEC §5.8)**
- The browser keeps the run's events and renders `render(events.reduce(apply, initialState))`. The live console and key views use the same reducer.
- At eight scripted steps the director emits `{"kind": "keyview", "payload": {"id", "n", "title", "caption"}}`.
- When a run reaches Act 6, `keyviews.py` keeps a copy of that run's event list. Restart doesn't clear it; the next completed run replaces it.
- Opening view *k* folds events up to the *k*-th marker with animations off. The server isn't involved.
- The export reads the files in `web/`, inlines them (fonts as base64 `data:` URLs) and injects `window.__REPLAY__ = {meta, events}`. `meta` is `{recorded_at, agent_model, investigator_model}`. No token or provider settings are included.

## Event schema (SSE `data:` JSON)

```json
{"seq": 41, "t": 132.4, "act": 4, "kind": "decision|caption|panel|map|system|llm|error|pause|keyview",
 "payload": {...}, "prev_hash": "…", "hash": "…"}
```

Only `decision` events join the hash chain. `llm` events carry `{role, model_ref, latency_ms, status}`, never prompts containing secrets, and **never the token**.

## Security posture of the prototype itself

- Bind to `127.0.0.1` only.
- The token lives only in the `secrets_store` module (a variable in memory). Redact any string equal to the token from exceptions and logs (a logging filter).
- The key-views export is built only from events, which never carry the token. `tests/test_keyviews.py` checks this.
- `tests/test_no_token_leak.py` starts the app with a fake token through the gate, runs a mocked demo, and asserts the token string appears in no response, event or log line.
