# Agent governance control plane: demo prototype

A self-playing, 5-minute demo showing how a control plane governs the AI agents that bridge a bank's post-trade systems. It finds the agents, onboards all four without changing their code, watches a recorded week before enforcing anything, has an AI draft the rulebook that a verifier checks and a person approves, stops a fooled agent, hardens access after the incident and produces measured evidence. Policy decides. AI advises. People approve. Everything is synthetic.

**Status:** built (milestones M0–M12 in `docs/TASKS.md`). Four live model calls per run. Screenshots are in `docs/screens/`. Interpretations of the spec are in `docs/DECISIONS.md`.

## Repository map

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Rules for Claude Code: core not plumbing, no secrets, live-token gate |
| `SPEC.md` | What to build: story, screens, 5-minute timeline, policy model, LLM contracts |
| `docs/ARCHITECTURE.md` | Small single-process design and folder layout |
| `docs/LLM_PROVIDERS.md` | Foundry and OpenRouter request shapes, model catalogue, **model recommendations** |
| `docs/DEMO_SCRIPT.md` | Captions and presenter notes, minute by minute |
| `docs/TASKS.md` | Milestones M0–M12 with acceptance checks |
| `docs/DESIGN.md` | Visual rules (shared with the proposal deck) |
| `design/` | Colour tokens and fonts from the deck |
| `reference/` | The proposal deck and background research (read-only) |
| `scripts/check_no_secrets.py` | Fails if anything that looks like a credential is committed |
| `app/core/` | The governance core: policy engine, delegation, envelopes, verifier, containment, audit chain |
| `app/demo/` | The 5-minute script, the director and key views |
| `app/llm/` | Foundry and OpenRouter client (`mock.py` is for tests only) |
| `web/` | The console: plain HTML, CSS and one ES module, no build step |
| `tests/` | Invariant tests and the rest (`python -m pytest -q`, offline) |

## Run on the work laptop

Python 3.11 or newer. Use PowerShell or Anaconda Prompt, from the repository folder:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

With conda instead: `conda create -n agentgov python=3.11 -y`, then `conda activate agentgov`, then `pip install -r requirements.txt` and `python run.py`.

If PowerShell refuses to run `activate` (execution policy), either run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip activation and call the venv's Python directly: `.venv\Scripts\python -m pip install -r requirements.txt`, then `.venv\Scripts\python run.py`.

`run.py` serves on `http://127.0.0.1:8765` (this machine only) and opens the browser. Stop it with Ctrl+C. If the browser doesn't open, browse to that address yourself.

The browser opens on the **connection screen**:
1. Keep **LLM Foundry** selected (recommended). Paste a **fresh** token; the project suffix defaults to `llmproxy-playground`.
2. Keep the recommended models (Agent `azure:gpt-4.1-mini`, Investigator `bedrock:claude-sonnet-4.5`), or pick others.
3. Click **Test connection**. When both show ✓, **Start demo** unlocks.

After the run, press **K** (or click **Key views**) to jump back to the eight key moments with no model calls. *Download key views* saves an offline HTML recording you can present later without a token.

The token is held in memory only. It is never saved, logged or shown again. If it expires mid-run, the demo pauses and asks for a new one.

**Behind a corporate proxy:** the app honours `HTTPS_PROXY` and `NO_PROXY`. In PowerShell: `$env:HTTPS_PROXY = "http://proxy.example:8080"` before `python run.py`. If TLS fails, set `$env:LLM_CA_BUNDLE = "C:\path\to\corporate-ca.pem"` (or paste the path in the connection screen's *Advanced* section). Never disable verification.

**Controls during the run:** Space pause/resume · → next step · R restart · click an act to jump · 0.5×/1×/2× speed · D theme · K key views · click a timeline row for its full decision record. The owner approvals (the rulebook in Act 2, the hardening in Act 5) auto-approve after 8 s, or click *Approve*.

**Tests (offline, no token):** `python -m pytest -q` and `python scripts/check_no_secrets.py`.

**Check connectivity before the meeting:**

```powershell
python scripts\probe_llm.py --provider foundry --model azure:gpt-4.1-mini
python scripts\probe_llm.py --provider foundry --model bedrock:claude-sonnet-4.5
python scripts\probe_llm.py --provider foundry --model bedrock:claude-sonnet-4.5 --each-variant
python scripts\probe_llm.py --provider foundry --model gemini:gemini-3-flash-preview --each-variant
```

The script asks for the token interactively (input hidden) and reports which endpoint variant worked (for example `converse (non-stream)` or `converse_stream`). `--each-variant` tries every variant separately. `--list` prints the catalogue.

## Rules for this repository

- **Never commit a token.** Old tokens in notes are expired; don't paste them anywhere in the repo. Run `python scripts/check_no_secrets.py` before committing.
- Demo prototype, not a product. See "core, not plumbing" in `CLAUDE.md`.
