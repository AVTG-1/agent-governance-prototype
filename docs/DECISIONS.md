# Decisions and spec interpretations

Where `SPEC.md` was ambiguous, these are the choices made, each picked to keep the 5-minute demo clear and the story true.

## Policy model

1. **Two extra rules.** `R-ID-01@v1` (registered agent, live, audience-bound credential, shared login retired) covers the attack-suite cases "token reuse with the wrong audience" and "unregistered agent", which no listed rule covered. `R-CNT-01@v1` (a contained session may only do what its containment allows) makes containment visible as a decision with a rule, like everything else.
2. **One extra capability, `recon.update`.** The agent plan tool `recon.update_break` needs a capability, and the reconciliation agent obviously updates breaks in its own system. It is a standing grant of the recon agent from the start, so it never affects the 586 / 14 shadow outcome.
3. **Policy versions.** `recon-agent-policy@v3` is the policy as first observed (before baselining), `@v4` the baseline adopted after the shadow week (adds `refdata.read` and the protected `ledger.read_quarter_end`), and `@v5` the tightened policy approved in Act 5. Rule versions (`R-PII-01@v3`, `R-EGR-01@v2`, …) are separate and fixed.
4. **Field-scoped grants and the JIT envelope.** The recon agent's standing `client.read_masked` grant covers the masked profile (`client_id`, `name`, `country`, `client_type`). `legal_entity_id` is outside it, which is why break `RC-90031` needs envelope `env-recon-cm-01`. Standing grants are checked before the envelope; a request outside both is default-denied with the reason naming the extra fields.
5. **R-PII-01 applies to any request carrying restricted data**, not only `client.read_pii`, so bulk export of PII to the file share is denied by the PII rule. `R-EGR-01` is checked before it, so external egress of PII always cites the hard egress rule.
6. **Rule order** (first match decides): R-SELF-01, R-ID-01, R-VOL-01, R-CNT-01, R-EGR-01, R-DLG-02, R-PII-01, R-SSI-01, R-GRANT-01, R-JIT-01, R-DEF-00. Hard rules come first so nothing later can override them. Delegation is checked before PII so the Act 4 delegated request cites `R-DLG-02`, as the spec requires.
7. **"Effective capabilities = caller ∩ callee ∩ task need ∩ policy; deny if empty"** is applied to the requested capability: the call is denied when the requested capability is not in the intersection. The panel shows the full intersection table.
8. **Shadow mode** records `would_deny` for denials and `would_hold` for holds (the spec's shadow counter has a "would hold" column).
9. **Shadow-week decisions are recorded in the audit chain** (600 records, mode `shadow`), so the evidence pack includes them. Only the 14 would-denies are streamed to the timeline as rows; the 586 allows drive the counters. The Act 5 replay test is a simulation against a candidate policy and is not recorded as live decisions.

## Verifier

10. **Four narrowing operations only:** `remove_grant`, `restrict_delegation`, `require_human_for_envelope`, `add_condition` (conditions limited to ones the engine enforces: `deny_if_untrusted_source`, `max_rows`, `require_human`). Anything else is "rejected: widens access" when its name or parameters suggest widening, otherwise "rejected: not a narrowing operation".
11. **Two checks beyond the spec's three.** (a) A grant used in the last 90 days cannot be removed ("rejected: in use (N calls in 90 days)"). (b) Defence in depth: each change, applied alone, must permit nothing the current policy doesn't, checked on ~600 probe requests (every agent × capability, direct and delegated, tainted and clean).
12. **Replay drops breaking changes.** If an accepted change breaks any legitimate call in the replay, it is turned into ✗ "rejected: breaks N legitimate calls in replay". So the replay figure shown is always computed, and approval only ever applies changes that keep it at 0.
13. **Lenient reading of model output, strict effect.** The verifier accepts reasonable variations in how a model writes a change (for example `target: "recon-agent:fx.read"`, or `params.scope: "client data"`), normalises them to one precise change, and shows the reason. It never invents a change.

## Containment

14. **The rule picks the action; the AI only recommends.** Playbook: `P-INJ-01` (a denied request on untrusted content aimed at restricted data or egress → session read-only, owner notified), `P-INJ-02` (repeat of an open case's untrusted source → revoke session at once), `P-VOL-01` (volume breach → quarantine). The investigator's recommendation is shown as "agrees", "differs" or "ignored: not an allowed action".
15. **"Re-run the attack: blocked at the first step, with fewer calls attempted."** In the Act 5 re-run, the first tainted denial matches the open case's source, so `P-INJ-02` revokes the session immediately and the agent's remaining steps never run. The panel shows calls attempted (1 vs 3) and time to containment for both runs.

## Director and timing

16. **Scripted clock.** The director's clock advances only while playing, scaled by speed, and never while waiting for a model. The story is exactly 300 scripted seconds (Act 6 ends at 5:00); real time is that divided by speed plus any model wait that prefetching didn't hide. Countdowns (the JIT envelope and the approval) run on the same clock, so they also scale with speed.
17. **Next, jump, restart.** *Next* finishes the current step instantly and starts the next one. *Jump forward* fast-forwards through the steps in between (model calls still happen for real and are waited for). *Jump back* restarts the run and fast-forwards to the chosen act, so state is always what the story produced, never patched.
18. **The agent fires its calls at machine speed; the console reveals them one by one.** In Act 4 (governed), all of the plan's calls go through the gateway at once, as a real agent would. The investigator call starts immediately after (within milliseconds of the first denial), so it sees every denial. The timeline then shows the decisions 2.5 s apart so the audience can follow.
19. **Containment is applied at the "case" step,** after the investigator answers, by rule. "First malicious call to containment" is measured on the wall clock and so includes demo pacing; the screen says so. The Act 5 re-run shows the same measure for a repeat attempt (sub-millisecond, rule `P-INJ-02`).
20. **Captions that would misdescribe a branch are swapped,** with the alternatives kept in `script.py`: when the model declines the injection, "The live model reads it and plans to follow it." becomes "The live model declined. A recorded compromised plan now tests the controls.", and "The model was fooled. The system held." becomes "The plan was stopped at every harmful step. The system held."
21. **The investigator gets no hint of the expected answer.** It sees the denied records, the injected text, the registry entry, grants with 90-day usage and tags, the delegation rule and the envelope. If it proposes something different from the "expected" changes, the verifier and replay judge whatever it did propose.

## Console

22. **Pure reducer.** `state = events.reduce(apply, initialState())`. The only view state outside the log is presentation: theme, which overlay is open, the selected timeline row and the key-view position. Countdowns and counters are events, so key views show them frozen at their value.
23. **Timeline.** Newest at the top, as many rows as fit. Shadow-week rows show "rec." and their recorded date instead of a run time. Today-mode calls appear as dashed "unchecked · no control" rows: they have no decision, which is the point.
24. **Act panels compact as the act moves on** (for example the plan collapses to numbered chips once today mode starts), so each act's current content fits at 1440×900 without scrolling.
25. **The close card is an overlay over the map and timeline** (dismissible), so the evidence panel stays fully visible beside it. *Key views* and *Extra: malfunction* are on the card.
26. **"Consequential calls through the plane"** counts governed agent calls in this run (decided ÷ attempted at the gateway). The today-mode illustration bypasses the plane by design and is excluded; the tile says so.
27. **Theme preference** is kept in `localStorage` (wrapped in try/catch, defaults to dark). Nothing else is stored in the browser.

## Extra and key views

28. **Malfunction extra.** The settlement agent loops on one SSI amendment 40 times (each held by `R-SSI-01`); a volume monitor then measures 40 amendments in 60 s against a baseline of 1 (40×, above the 10× threshold), so the next call is denied by `R-VOL-01` and playbook `P-VOL-01` quarantines the agent and pages its owner. It runs once, after the run ends, and is not part of key views.
29. **Key views are saved when the close card appears** (and again at 5:00), from the run's own event log. A restart keeps them until another run reaches the close card.
