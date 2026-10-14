# Agent governance control plane: demo prototype

A self-playing, 5-minute demo showing how a control plane governs the AI agents that bridge a bank's post-trade systems. It finds the agents, wraps an existing one without changing its code, observes before enforcing, stops a fooled agent, tightens access safely and produces measured evidence. Everything is synthetic.

**Status:** specification kit. Claude Code builds the app from `SPEC.md` and `docs/TASKS.md`; see `docs/KICKOFF_PROMPT.md`.

## Repository map

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Rules for Claude Code: core not plumbing, no secrets, live-token gate |
| `SPEC.md` | What to build: story, screens, 5-minute timeline, policy model, LLM contracts |
| `docs/ARCHITECTURE.md` | Small single-process design and folder layout |
| `docs/LLM_PROVIDERS.md` | Foundry and OpenRouter request shapes, model catalogue, **model recommendations** |
| `docs/DEMO_SCRIPT.md` | Captions and presenter notes, minute by minute |
| `docs/TASKS.md` | Milestones M0–M9 with acceptance checks |
| `docs/DESIGN.md` | Visual rules (shared with the proposal deck) |
| `design/` | Colour tokens and fonts from the deck |
| `reference/` | The proposal deck and background research (read-only) |
| `scripts/check_no_secrets.py` | Fails if anything that looks like a credential is committed |

## Run on the work laptop (once built)

Use PowerShell or Anaconda Prompt, from the repository folder:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

With conda instead: `conda create -n agentgov python=3.11 -y`, then `conda activate agentgov`, then `pip install -r requirements.txt`.

The browser opens on the **connection screen**:
1. Keep **LLM Foundry** selected (recommended). Paste a **fresh** token; the project suffix defaults to `llmproxy-playground`.
2. Keep the recommended models (Agent `azure:gpt-4.1-mini`, Investigator `bedrock:claude-sonnet-4.5`), or pick others.
3. Click **Test connection**. When both show ✓, **Start demo** unlocks.

After the run, press **K** (or click **Key views**) to jump back to the eight key moments with no model calls. *Download key views* saves an offline HTML recording you can present later without a token.

The token is held in memory only. It is never saved, logged or shown again. If it expires mid-run, the demo pauses and asks for a new one.

**Behind a corporate proxy:** the app honours `HTTPS_PROXY`. If TLS fails, set `LLM_CA_BUNDLE` to your corporate CA file path. Never disable verification.

**Check connectivity before the meeting:**

```powershell
python scripts\probe_llm.py --provider foundry --model azure:gpt-4.1-mini
python scripts\probe_llm.py --provider foundry --model bedrock:claude-sonnet-4.5
```

The script asks for the token interactively.

## Rules for this repository

- **Never commit a token.** Old tokens in notes are expired; don't paste them anywhere in the repo. Run `python scripts/check_no_secrets.py` before committing.
- Demo prototype, not a product. See "core, not plumbing" in `CLAUDE.md`.
