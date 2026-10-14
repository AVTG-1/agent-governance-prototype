# Kickoff prompt for Claude Code (web)

Paste this as the first message after connecting the repository.

---

Build the prototype described in this repository.

1. Read `CLAUDE.md` first and follow it strictly: core, not plumbing; no secrets anywhere; the demo must not start without a live token pasted into the connection screen.
2. Then read `SPEC.md`, `docs/ARCHITECTURE.md`, `docs/LLM_PROVIDERS.md`, `docs/DESIGN.md` and `docs/TASKS.md`.
3. Work through `docs/TASKS.md` from M0 to M9. Finish each milestone with its acceptance checks passing, `python scripts/check_no_secrets.py` passing, a ticked checklist and a commit.
4. You cannot reach LLM Foundry from here, and you must not try. Build to the documented request shapes and test with the mock LLM, which must stay test-only.
5. Don't stop to ask unless a decision is irreversible. Record interpretations in `docs/DECISIONS.md` and keep going.
6. When done, summarise what was built, how to run it on a Windows laptop, and anything the presenter must verify with a live Foundry token, such as which Bedrock or Gemini endpoint variant works.

---

## Follow-up prompts you may need

- **To resume:** "Continue from the first unticked milestone in `docs/TASKS.md`."
- **After a live test on the laptop:** "On the work laptop, `probe_llm.py` reported: <paste output, no token>. Adjust the Foundry adapter accordingly and add a parser test for this response shape."
- **To tighten the run time:** "The rehearsal ran 5:40. Trim captions and act durations in `app/demo/script.py` to land at 5:00, keeping every act."
