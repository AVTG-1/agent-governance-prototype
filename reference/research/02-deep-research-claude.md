# Governing Nomura's Agent Estate: Research Brief for a Capability Response (October 2026)

Nomura is not really asking for an agent-security product. It is asking for proof that a partner can put a single control plane (identity, entitlement, oversight and intervention) over a varied set of "glue" agents it already runs. Most of those agents cannot be rewritten, and the plane must be defensible to regulators in Tokyo, London, New York and Singapore. A credible response treats existing agents as untrusted workloads to be discovered, given an identity and mediated from outside. It makes "optimised" permissions a human-approved, evidence-driven right-sizing loop rather than an autonomous AI that grants access. And it demonstrates rogue-agent containment with deterministic controls, using detectors only as signals.

## TL;DR

- **The real problem is non-human identity and authority, not AI.** Nomura's 160+ unconnected systems are bridged by agents whose credentials, scopes and delegation paths are probably invisible to central governance. The publicly visible owner of data, Cloud and AI governance is the Chief Data Office. No public record of a "Chief Data Innovation Officer" was found, so the sponsor's title should be confirmed before submission.
- **The standards are mostly unfinished, so architecture judgement is the differentiator.** NIST's agent identity work is a February 2026 draft concept paper, and the IETF agent-auth work is individual drafts. MAS finalised AI risk guidelines on 7 October 2026 and will consult on agent-specific guidance in 2027. The mature building blocks are OAuth token exchange, workload identity, policy engines and gateways. Agent-specific protocols are still emerging.
- **Win with a demo built on deterministic enforcement, honest detection and an observe-first rollout.** Published evidence shows prompt-injection detectors cut attacks a lot under static tests, but adaptive attacks get past them more than 90% of the time. Containment therefore has to rest on scoped, short-lived credentials, policy at choke points and kill-switches. "AI watching AI" should be sold only as a signal layer.

## Executive Summary: What Nomura Is Really Trying to Achieve

**Verified context.** Nomura publicly describes AI as strategic. It set up a Japan AI Centre of Excellence in April 2024 and an International AI CoE in April 2025, and it rolled out the internal "NomuChat" tool in May 2023. Its AI governance framework involves legal, compliance and risk management in a "dual-line supervisory approach".\[1\] Its April 2026 governance presentation says a governance framework will be established across the whole AI lifecycle, with primary oversight of AI risk held by the Group CIO Risk Management Committee under the Group Risk Management Committee.\[2\] Nomura's careers pages describe a Chief Data Office (skill category "Group Data Office") as "the central authority" for "data, Cloud and AI governance".\[3\] One of its VP roles is explicitly about evaluating governance tooling for "Agentic AI, Agents / Multi-Agent systems".\[4\]

**Inference: what the sponsor actually needs.** The four gaps listed (manage access, verify identity at action time, oversee behaviour, catch improper access early) are the classic identity governance and privileged access problems, now applied to a new kind of non-human actor. These actors behave less predictably than service accounts and can be steered by the content they read. The sponsor almost certainly needs:
1. a defensible inventory and ownership model;
2. a way to impose identity and least privilege on agents without rewriting them;
3. evidence for supervisors that this oversight is continuous.

The fact that this sits with a data organisation rather than the CISO suggests the framing is data entitlement and lineage ("which agent touched which client or trade data, on whose authority"), not only cyber.

**What a credible response looks like (our position):**
- **Architecture strategy:** a "mediate, don't modify" control plane. This means discovery, then an agent registry with accountable human owners, then brokered short-lived credentials, then policy enforcement at the gateway, data and API layers, then telemetry. It should run in observe-only mode before enforcement.
- **Entitlements POV:** a layered model. The base is static, role-based least privilege. On top of that sit attribute- and relationship-based policy (policy-as-code) for context, and just-in-time elevation for rare actions. Usage-driven right-sizing is proposed by analytics but approved by humans. LLM-generated policy is confined to drafting and explaining, never granting.
- **Talent:** profiles that combine IAM/PAM and workload identity engineering, capital-markets operations knowledge (settlement, reconciliation, reference data), agent security and red-teaming, and model risk and regulatory mapping.
- **Demo:** one synthetic post-trade estate (trade capture, settlement, reconciliation, reference and client data), with agents onboarded, entitlements right-sized from observed usage, and a prompt-injected reconciliation agent contained in real time with a full audit trail.

## Q1. Nomura: Technology, AI Operating Model, Governance, Leadership, Regulators

### Verified facts

**AI operating model and programmes**
- **Japan AI CoE** (April 2024) and **International AI CoE** (April 2025). The 2025 Nomura Report says Japan and overseas offices "will collaborate to promote both the utilization and governance of generative AI."\[1\]
- **NomuChat**, an internal generative AI chat tool for all employees, launched May 2023.\[1\]
- **AI governance structure:** a framework involving legal, compliance and risk management (a "dual-line supervisory approach"), with "ongoing assessments of model transparency, data management, and deviations" (Nomura Report 2025).\[1\]
- **Risk oversight:** according to the April 2026 governance presentation, the Group CIO Risk Management Committee has primary oversight of AI risk and reports to the Board and Risk Committee as needed. The same deck references an "AI Governance Forum", says a CISO was hired and a Cybersecurity Department set up in April 2024, and commits to an AI lifecycle governance framework "covering evaluation, development, implementation, and oversight".\[2\]
- **Investor Day (May 2026):** management committed to "accelerate the use of data and AI tools across the Group" and cited "robust risk management and governance" as a source of competitive advantage.\[5\]

**Data organisation and leadership (as of October 2026)**
- **Chief Data Office / Group Data Office.** Nomura job postings describe the CDO function as defining and overseeing "data, Cloud and AI governance" and as "the central authority overseeing the Business and Corporate functions in complying with data, Cloud and AI governance requirements."\[3\] A Mumbai VP AI Governance role covers evaluating and implementing governance tooling for "Generative AI, Agentic AI, Agents / Multi-Agent systems".\[4\] A LinkedIn profile shows an "AI Governance Japan Lead" in the Chief Data Office (Tokyo).\[6\]
- **Former Group CDO.** Deep Thomas was publicly described as "Nomura Group's Chief Data Officer" (CDO Magazine, August 2023). He has since joined JPMorganChase as APAC Chief Data & Analytics Officer, with press describing his Nomura role as "Group Chief Data and Analytics Officer".\[7\]\[8\] **A current named successor could not be verified.**
- **Other named data/AI leaders (secondary sources):**
  - Ling Ling Lo, "global head of data strategy and transformation and EMEA head of Nomura's chief data office" (Raconteur).\[9\]
  - Santanu Sengupta, "Global Head of Data & AI Products and Solutions" (B Capital, September 2024).\[10\]
  - Tahir Zafar, Nomura's international head of AI strategy. Bloomberg reported on 8 June 2026 that he was leaving for JPMorgan.\[11\]
- **Senior management lineup (effective 1 April 2026):** Akio Hori is CIO and Takumi Kitamura is Chief Transformation Officer (CTO). Nobuyuki Taguchi covers Group IT and Digital Company, and Munehiro Itani is Joint Head of Global Operations.\[12\] **No Chief Data or Chief Data & Innovation Officer appears among the Senior Managing Directors**, which suggests the data head sits below SMD level or under one of these executives.

**Title verification.** No public source was found for the title "Chief Data Innovation Officer". The publicly evidenced unit is the Chief Data Office / Group Data Office. Treat the title as **unverified**, and ask directly whether the sponsor heads the Group Data Office, which division it reports into (IT, Transformation or Corporate), and whether the role was recently re-scoped after the leadership departures.

**Cloud and vendor relationships**
- **AWS:** digital transformation on AWS since 2017. "Core AI", a generative AI platform built with the AWS Generative AI Innovation Center on Amazon Bedrock and Anthropic Claude, is used for compliance and ad-review automation. Llama models on Bedrock were used to open up generative AI to employees (2024).\[13\]\[14\] Both are AWS case studies, so vendor-published.
- **OpenAI:** strategic collaboration to adopt OpenAI Deep Research, focused on asset management and investment advice.\[15\]
- **Nomura Research Institute (NRI)** is a separate listed affiliate that runs Japanese financial-market utility platforms.\[16\] It is not evidence of Nomura Holdings' own estate.

**Hiring signals.** A New York Global Markets posting seeks a VP to "build the AI operating model for Global Markets, balancing traditional AI/ML with Generative AI and Agentic AI", including "post-trade automation".\[17\] This supports the client's statement that agents are in operational use.

### Inference (not verified)
- With two prominent data/AI leaders gone to JPMorgan in 2025–26, the sponsor may be under pressure to show a governance capability quickly and to institutionalise knowledge. Reliable partner bench depth will matter.
- AI risk sits under the Group CIO Risk Management Committee, while AI governance sits in the Chief Data Office. That means any entitlement architecture must satisfy both, and probably the CISO's identity and access management (IAM) team as well. Expect an approval chain of three or more stakeholders.
- The AWS/Bedrock footprint suggests some agents use AWS IAM roles, which helps credential brokering. The 160+ heterogeneous systems imply many agents also use service accounts, API keys or screen-level access.

### Regulators and current expectations (dated)

| Jurisdiction / entity | Regulator(s) | Current position on AI agents, machine identity, access (as of Oct 2026) |
|---|---|---|
| Japan (Nomura Holdings, Nomura Securities) | FSA; BoJ | FSA AI Discussion Paper v1.0 (4 March 2025), updated to **v1.1 on 3 March 2026** after the FSA AI Public-Private Forum (June–December 2025). Discussion points, not binding rules.\[18\] BoJ published a report on generative AI use and risk management by Japanese financial institutions in October 2024.\[19\]\[20\] No agent-specific identity rule was found. |
| Singapore (Nomura Singapore entities) | MAS | **Guidelines on AI Risk Management issued 7 October 2026, effective 7 October 2027.** They cover all AI, including agents. They require inventories, materiality assessment and lifecycle controls (data governance, testing, human oversight, cybersecurity, monitoring, change management), and explicitly anticipate "agentic AI systems that can operate autonomously and access tools."\[21\]\[22\] MAS intends to consult in 2027 on further agentic guidance.\[23\]\[24\] Supported by Project MindForge handbooks (2026) and IMDA's Model AI Governance Framework for Agentic AI (January 2026).\[25\]\[26\]\[27\] |
| UK (Nomura International plc etc.) | FCA; PRA | No dedicated AI rulebook. Existing regimes apply: SM&CR accountability, Consumer Duty, PRA SS1/23 model risk management, operational resilience.\[28\] FCA CEO speech (24 June 2026) called agentic systems a "profound step change" and said accountability "must remain clear".\[29\] The **Mills Review (6 July 2026)** recommended the FCA lead a trusted framework clarifying how AI agents "can be authorised, identified and held accountable".\[30\] The PRA lists AI adoption among its 2026 supervisory priorities.\[31\] |
| EU (Nomura Financial Products Europe GmbH etc.) | BaFin/ECB, ESMA/EBA; EU AI Act; DORA | AI Act in force since 1 August 2024. GPAI obligations applied from August 2025, transparency rules from August 2026, and high-risk rules on a revised timetable. DORA governs ICT risk, including access management and third-party risk.\[32\] No agent-specific EU identity rule was found. |
| US (Nomura Securities International, NHA) | SEC, FINRA, Fed | **FINRA 2026 Regulatory Oversight Report (9 December 2025)** discusses AI agents for the first time. It flags autonomy, agents acting "beyond the user's actual or intended scope and authority", and sensitive-data misuse. It suggests agent-specific supervision: monitoring system access and data handling, human-in-the-loop placement, action tracking and guardrails.\[33\]\[34\]\[35\] Fed/OCC SR 11-7 model risk management remains the bank-side anchor. |
| Global | FSB | 2026 consultation on responsible AI adoption asks whether practices address GenAI and agentic AI.\[32\] |
| Hong Kong, India | HKMA/SFC; SEBI/RBI | **Not researched in this cycle**. A gap to close before submission. |

**Implication.** No regulator yet mandates a specific agent-identity standard. Across the regimes, though, supervisors converge on four expectations: an inventory, an accountable human for every agent, access limited to scope, and a reconstructable action record. These are exactly the sponsor's four gaps, so the response can frame its architecture as "regulator-ready by construction".

**Incidents and enforcement.** No public enforcement action or incident involving Nomura's AI agents was found. Nomura has had unrelated conduct issues reported in the press ("Trading Scandal, Attempted Murder Arrest Haunt Nomura" appears in MarketScreener headlines).\[36\] These are not AI-related and should not feature in a pitch.

## Q2. State of the Art in Governing Agent Entitlements (2026)

### Named real-world deployments (evidence quality noted)
- **BNY "Digital Employees"** is the strongest public bank example. Agents have their own login credentials, an employee number in the corporate directory and a human manager, and they work in narrow team-specific instances "so no digital employee has broad access to information across the company" (CIO Leigh-Ann Russell, via WSJ, July 2025).\[37\]\[38\] Microsoft WorkLab's BNY case study puts the count at "nearly 140" digital employees, described as "super agents" built from multiple agents. BNY CEO Robin Vince told Business Insider that "All digital employees report to a human manager", with about 100 managers across the firm overseeing them. PYMNTS reports live manager dashboards (volume, cycle times, missed transactions, approval outcomes) and a "Digital Employee Agency", led by head of talent Michelle O'Reilly, covering onboarding, scorecards and offboarding. The payments-validation agent replaced brittle scripted bots. Validations "that took up to six minutes now clear in under 30 seconds" and open investigations fell "nearly 80%", per BNY's Rachel Lewis in a Microsoft case study, so a vendor-published channel.
  - Lesson: BNY treats agents like **workforce identities with joiner-mover-leaver lifecycle**, a model Nomura's identity governance tooling may already support.
- **JPMorgan Chase:** chief analytics officer Derek Waldron told CNBC (9 June 2026) that the bank plans long-running autonomous agents in 2026. CNBC characterised this as suggesting the security and governance hurdles are close to cleared.\[39\] That is a press inference, not a disclosed architecture.
- **Goldman Sachs:** CNBC (6 February 2026) quoted CIO Marco Argenti as saying that for "the past six months" the bank has worked "with embedded Anthropic engineers to co-develop autonomous agents" for "accounting for trades and transactions, and client vetting and onboarding", with launch expected "soon" and no date given. No governance architecture has been disclosed.
- **Survey signal:** JumpCloud's Q4 2026 report "Enterprise AI Access Is Outpacing Control" (250 US and UK IT leaders, reported 8 October 2026) found that among organisations using AI agents "only 41% have fully integrated them into human IAM policies", so 59% have not. It also found 72% see a gap between what agents can access and what they can prove the agents accessed. JumpCloud is a vendor, so treat this as vendor-sourced and indicative.

### Standards, protocols and frameworks: maturity map

| Item | Status (Oct 2026) | Maturity |
|---|---|---|
| OAuth 2.0 (RFC 6749), Token Exchange (RFC 8693), DPoP (RFC 9449), mTLS-bound tokens (RFC 8705), Resource Indicators (RFC 8707), Protected Resource Metadata (RFC 9728) | Ratified RFCs | **Mature**; the backbone for delegation and audience restriction |
| OAuth 2.1 | IETF WG draft (-15, March 2026); IESG submission milestone December 2026\[40\] | Near-final, not an RFC |
| SPIFFE/SPIRE workload identity; IETF WIMSE | SPIFFE is a CNCF project in wide use; WIMSE WG drafts in progress\[40\] | Mature for workloads; agent profiles emerging |
| MCP authorization | Project spec; revision 2026-07-28 mandates resource indicators, protected-resource metadata, issuer validation, step-up authorization.\[40\] MCP donated to Linux Foundation's Agentic AI Foundation in December 2025\[41\] | **Emerging but fast-hardening**; versioned by revision date |
| IETF "AI Agent Authentication and Authorization" (draft-klrc-aiagent-auth) | Individual draft (-00 2 March 2026; -03 6 July 2026); discussed at WIMSE interim; no WG adoption\[40\]\[42\]\[43\] | Emerging; deliberately reuses existing standards\[42\] |
| OAuth on-behalf-of for AI agents (draft-oauth-ai-agents-on-behalf-of-user) | Expired individual draft\[44\] | Unproven |
| OAuth Profile for Delegated AI Agent Authorization (draft-mishra-oauth-agent-grants-02) | Individual draft, 30 August 2026\[45\] | Unproven |
| OAuth Transaction Tokens (and agent extensions) | WG draft / individual drafts | Emerging; useful for propagating context through call chains\[46\] |
| NIST CAISI AI Agent Standards Initiative | Launched 17 February 2026\[47\] | Programme, not a standard |
| NIST NCCoE "Accelerating the Adoption of Software and AI Agent Identity and Authorization" | Draft concept paper, February 2026; comments closed 2 April 2026\[47\]\[48\] | Concept stage. Focus areas: identification, authorization, access delegation, logging/transparency, data-flow tracking\[47\] |
| NIST AI RMF; SP 800-207 zero trust | Published | Mature frameworks, not agent-specific |
| OWASP Top 10 for Agentic Applications (2026) | Published | Mature as a risk taxonomy. ASI03 Identity & Privilege Abuse, ASI07 Insecure Inter-Agent Communication, ASI10 Rogue Agents\[49\] |
| ISO/IEC 42001 | Published 2023 | Mature management-system standard; not an access-control spec |
| Policy engines: OPA/Rego, Cedar, Zanzibar-style ReBAC | Production-proven in large enterprises | **Mature**, but agent-specific policy patterns are new |
| IMDA Model AI Governance Framework for Agentic AI | Published January 2026\[27\] | Governance guidance |

**Bottom line.** Mature plumbing (OAuth, token exchange, workload identity, policy-as-code, API gateways, PAM vaults) can deliver most of Nomura's four requirements today. The genuinely immature layers are agent-native protocols for multi-hop delegation and standardised agent identity claims. A partner should design so these can be adopted later without re-plumbing.

## Q3. "Optimised" Permissions: Approaches and Trade-offs

Evidence on agent-specific performance of these approaches is **thin**. Most evidence comes from human/workload IAM and is extrapolated. Ratings below are qualitative judgements from that evidence, not measured benchmarks.

| Approach | How it "optimises" | Reliability | Security | Latency | Cost | Auditability | Regulatory acceptability |
|---|---|---|---|---|---|---|---|
| **Static RBAC / scoped service accounts** | Only via periodic recertification | High, deterministic | Prone to drift and over-provisioning; agents' broad tasks invite wide roles | Negligible | Low build, high review burden | High | High; familiar to examiners |
| **Rule/attribute-based (ABAC) policy-as-code** (OPA, Cedar) | Context such as data classification, time, trade status or entity narrows access per request | High if policies are tested | Strong least privilege; policy errors are the main risk | Low (in-process evaluation is typically sub-millisecond to low ms) | Moderate (policy engineering) | High; policies are versioned code | High |
| **Relationship-based (ReBAC, Zanzibar-style)** | Access derives from graph relations (agent→desk→book→client) | High at scale when well-modelled | Good for delegation chains; graph complexity can hide paths | Low to moderate | Moderate to high | High, but path explanations needed | High if explainable |
| **Just-in-time / ephemeral credentials** (token exchange, PAM brokering) | Standing privilege tends toward zero; elevation per task | High, but brokers become critical dependencies | Very strong; limits the blast radius of compromised agents | Adds token issuance latency per task | Moderate | High; every grant logged | High; matches PAM expectations |
| **Usage-driven right-sizing** (mine logs, propose removals) | Shrinks entitlements to observed need | Depends on observation window; rare legitimate actions (quarter-end, fails management) get wrongly removed | Strong if human-approved | None at runtime | Low to moderate | High if proposals and approvals are logged | High as a recommender; low if auto-applied |
| **ML anomaly-driven adaptive access** (risk scores trigger step-up/deny) | Tightens access dynamically on deviation | Moderate; false positives disrupt operations | Adds detection; models can be evaded | Moderate (scoring inline) | Moderate to high | Medium; model decisions need explanation | Medium; falls under model risk management (SS1/23, SR 11-7) |
| **LLM-generated or LLM-adjudicated policy** | Natural-language intent becomes policy; LLM approves requests | Low to moderate; non-deterministic | Weak as an enforcer, since it is itself injectable (see Q6) | High (LLM calls) | Higher per decision | Low unless outputs are fixed as code | Low as a decision-maker today; acceptable as a drafting aid |
| **Hybrid** (deterministic enforcement + analytics/LLM recommendation + human approval) | Continuous improvement with deterministic runtime | High | Strong | Low at runtime | Moderate | High | **Highest** |

**Even-handed reading.** Each approach wins on different axes. Fully adaptive ML/LLM approaches promise the most "optimisation" but carry the weakest auditability and regulatory acceptability today. Static models are most acceptable but least optimised. Every regulator reviewed emphasises human accountability and lifecycle controls, and that favours designs where optimisation is *recommended by analytics and committed by an accountable owner*. The partner should present this as a spectrum and let Nomura choose its position per risk tier, rather than presuppose one winner.

## Q4. Governing Agents You Cannot See Inside

Since the internals are unknown, the control points must sit **outside** the agent:

1. **Discovery and inventory.** Mine identity provider and directory records, cloud IAM (e.g. AWS roles used with Bedrock), secrets vaults, API gateway logs, egress/proxy logs, scheduler and RPA consoles, and LLM-provider billing/API keys to find non-human principals behaving like agents. MAS's final guidelines explicitly extend identification to AI embedded in providers' services and to "shadow AI".\[50\] Output: a registry with an accountable owner, purpose, systems touched and data classes per agent.\[51\]
2. **Identity layer (credential substitution).** Replace shared or static secrets with per-agent identities: vault-brokered, short-lived credentials, or workload identity (SPIFFE) where agents run in controllable runtimes.\[51\] This can usually be done by changing configuration or environment injection, not code. BNY's one-login-per-digital-employee model is the organisational equivalent.\[52\]
3. **API / tool layer (gateway mediation).** Route agent calls to systems through a policy-enforcing gateway or MCP proxy that authenticates the agent, applies ABAC/ReBAC policy, strips over-broad scopes (token exchange to narrower audiences) and logs every call.
4. **Data layer.** Enforce row/column-level security, data masking and purpose tags in data platforms. This catches improper access even when the agent and gateway are bypassed.
5. **Network layer.** Egress allow-listing and segmentation as a backstop. Notably, EchoLeak-class exfiltration used outbound URL fetches.\[53\]
6. **Observe-only rollout.** Run policy in "shadow" mode: decisions are logged, not enforced. That builds a baseline, measures would-be denials, tunes policy, and then enforces by risk tier. This is standard practice from zero-trust and PAM programmes. We found no published agent-specific case study quantifying it, so present it as transferred practice.

**What has worked in practice (evidence-qualified).** BNY's narrow scoping, named identities and manager dashboards (above).\[38\]\[54\] FINRA's suggested practices of monitoring system access and data handling, tracking actions, and guardrails.\[35\] The rest is extrapolated from non-human-identity and PAM programmes, which the OWASP Agentic Top 10 explicitly links (ASI03).

## Q5. Agent-to-Agent Risk: Delegation, Impersonation, Confused Deputy, Escalation

**How it arises:**
- **Confused deputy / scope violation:** an agent uses authority it legitimately holds to serve an attacker's instruction embedded in content. EchoLeak (CVE-2025-32711, CVSS 9.3, Microsoft 365 Copilot, disclosed June 2025) is the canonical production example: a crafted email caused zero-click data exfiltration, and it evaded Microsoft's prompt-injection classifier.\[53\]\[55\]\[56\]
- **Identity and privilege abuse (OWASP ASI03):** inherited or cached credentials, a privileged agent passing credentials to a lower-privilege agent, transitive privilege inheritance across chains.\[57\]\[58\]
- **Insecure inter-agent communication (ASI07):** spoofed or tampered messages. A low-privilege agent "instructs" a high-privilege one, which trusts it implicitly.\[59\]\[60\]
- **Cascading failures (ASI08):** errors propagate through planning and execution chains.\[60\] In post-trade, a bad reference-data update can feed settlement instructions.

**How it is being addressed:**
- **Delegation with attenuation:** RFC 8693 token exchange (actor and subject claims) lets each hop carry *who acts for whom* with narrower scope. The draft-mishra profile and transaction-token drafts extend this.\[45\]\[46\] Multi-hop delegation across trust domains is **only partially solved**. Commentators note the on-behalf-of draft covers a single hop.\[46\]
- **Mutual authentication between agents** (mTLS/SPIFFE), signed messages, and per-hop policy checks at gateways.
- **Re-authorisation for escalation** and detection of transitive privilege (OWASP guidance).\[57\]

**Maturity.** Single-hop delegation is mature (OAuth). Multi-hop, cross-protocol (MCP ↔ A2A) delegation with verifiable provenance is at research and draft stage, with several competing proposals on arXiv and at the IETF.\[61\] A credible response should say so plainly and design a chain-of-custody record (a delegation-chain ID propagated through every call) that does not depend on any one draft winning.

## Q6. Detecting and Correcting Rogue Agents

### What the evidence says about detection (all academic / lab benchmarks; none capital-markets-specific)

| Source | Finding |
|---|---|
| AgentDojo (Debenedetti et al., NeurIPS 2024, arXiv 2406.13352) | 97 tasks, 629 security cases. "Current LLMs solve less than 66% of AgentDojo tasks in the absence of any attack… our attacks succeed against the best performing agents in less than 25% of cases." A secondary detector drops attack success to 8%, but "has too many false positives… and significantly degrades utility". "All defenses lose 15-20% of utility under attack."\[62\] |
| Meta LlamaFirewall (arXiv 2505.03574, April/May 2025; "utilized in production at Meta") | PromptGuard 2 86M: 97.5% recall at 1% FPR on jailbreak detection. On AgentDojo replay, attack success fell from 17.6% to 7.5% (utility 47.7% to 47.0%). Combined with AlignmentCheck: 1.75%. AlignmentCheck detected "over 83% of goal hijacking attempts while maintaining a very low FPR of 2.5%" (Llama 4 Maverick). Authors note narrow attack coverage and that the checker itself can be targeted.\[63\] |
| "The Attacker Moves Second" (Nasr, Carlini, Tramèr et al., arXiv 2510.09023, October 2025, preprint) | Bypassed 12 recent defenses "with attack success rate above 90% for most… the majority of defenses originally reported near-zero attack success rates." Adaptive attack exceeded 90% success against Protect AI, PromptGuard and Model Armor; PIGuard 71%. Combining multiple guardrails did not stop the attacks.\[64\] |
| CaMeL (Google DeepMind et al., arXiv 2503.18813, v2 June 2025) | Design-level defence separating control and data flow, with capability tracking: "solving 77% of tasks with provable security (compared to 84% with an undefended system)". Successful attacks on Gemini 2.5 Pro fell "from 300 without to 0 with CaMeL" (of 949). Costs: about 2.8× input and 2.7× output tokens. Authors: "prompt injection attacks are not fully solved."\[65\] |
| Microsoft Prompt Shields | Described qualitatively by MSRC (July 2025); **no published detection/FPR figures found**.\[66\] |

**Interpretation.** Classifier detectors give real but brittle protection. Their static-benchmark numbers overstate robustness against adaptive adversaries, and their false positives are operationally costly. The most robust approaches are **architectural**: constrain what an agent *can* do (capabilities, least privilege, data/control separation, egress limits) so a hijacked agent can do little harm. Detection then becomes an early-warning signal. Misaligned or malfunctioning (non-adversarial) agents are best caught by **behavioural baselines against declared purpose**: volume, systems touched, data classes, time-of-day, and deviation from the entitlement set. Those methods come from user and entity behaviour analytics; no agent-specific false-positive benchmarks were found.

### Containment and correction mechanisms
- **Graduated response:** alert → step-up (require human approval) → scope reduction (revoke specific tokens) → quarantine (suspend identity, block at gateway) → kill-switch (revoke all credentials) → rollback/compensating transactions.
- **Human-in-the-loop at value thresholds** (FINRA; MAS human oversight).\[21\]\[67\]
- **Immutable action logs** to support reconstruction. FINRA suggests storing prompt and output logs.\[68\]

### Capital-markets scenarios for the demo (illustrative, synthetic)
- **Reconciliation agent prompt-injected** through a counterparty break comment, tries to pull the full client static-data table → gateway denies (purpose/data-class mismatch) → anomaly raised → token revoked → owner notified.
- **Settlement agent malfunction:** loops generating duplicate SSI amendment requests → rate/volume baseline breach → step-up to human → quarantine.
- **Agent-to-agent escalation:** a low-privilege trade-capture enrichment agent asks the privileged settlement agent to amend a standing settlement instruction → delegation-chain check fails (originating authority insufficient) → blocked and logged.
- **Reference-data drift:** an agent with legitimate write access updates an LEI mapping outside its normal pattern → held for four-eyes approval.

## Q7. Competitive Landscape

**Categories (vendor names are those surfaced in this research; capability claims are vendor-sourced unless stated):**
- **Platform and identity incumbents:** Microsoft (Copilot Studio governance mapped to OWASP Agentic Top 10), Okta/Auth0, CyberArk, SailPoint and Teleport (ephemeral certificates, JIT for agents).\[57\]\[69\] Agent-identity features from these incumbents are rapidly becoming **bundled**. Microsoft Learn lists Microsoft Entra Agent ID as generally available as of April 2026 ("Microsoft Entra Agent ID is now generally available"), and Microsoft Agent 365, the control plane that includes Agent ID, went GA on 1 May 2026 at USD15 per user per month (Microsoft Security blog).
- **Non-human identity and agent-security specialists:** Astrix, Keycard (agent credentialing), Noma Security (disclosed ForcedLeak in Salesforce Agentforce), Aim Security (EchoLeak), Invariant Labs (GitHub MCP exploit research), WorkOS (MCP auth), Sentra (data security), Containment.ai.\[53\]\[58\]\[70\]\[71\]\[72\] CB Insights frames a "Know Your Agent" category that has raised $278M over three years.\[72\] That figure comes via secondary commentary, not checked against CB Insights directly.
- **Guardrail/detection tooling:** Meta LlamaFirewall/PromptGuard (open source), Protect AI, Google Model Armor. The adaptive-attack evidence applies to these.
- **Consultancies/SIs:** large firms publish agentic governance thought leadership (e.g. KPMG Japan on AI governance in Japanese financial institutions).\[73\] This research did not verify named bank deployments delivered by specific SIs, so claims of SI track records should be tested in references.

**What is commoditising:** agent registries, per-agent credentials, OAuth-for-MCP, prompt/response logging, off-the-shelf injection classifiers, OWASP mapping dashboards.

**What remains hard and differentiating for a services firm:**
1. Discovering and mediating **legacy, un-rewritable agents** across 160+ heterogeneous systems without breaking STP-substitute flows.
2. **Domain-correct entitlement models** for post-trade data (client static, SSIs, books, legal entities), so policies match how operations actually work, including quarter-end and fails-management exceptions.
3. **Multi-hop delegation and chain-of-custody** design that survives standards churn.
4. Mapping controls to **four-plus regulatory regimes** at once, with evidence packs.
5. **Operating model:** ownership, joiner-mover-leaver for agents, recertification cadence, incident playbooks. BNY's "Digital Employee Agency" shows this is where leaders are investing.\[54\]

## Q8. What Would Convince This Buyer

**Evidence from the sponsor's own organisation (Raconteur interview with Ling Ling Lo, Nomura Chief Data Office):**
- Data gaps that appear mid-project are "the easiest way to kill off an AI use case".\[9\] The demo must show it handles messy, incomplete data and entitlement metadata.
- Governance should "evolve in parallel with an AI initiative"; "sometimes innovation has to live in a fairly unstructured space before you then put in the guardrails."\[9\] So pitch observe-first, incremental governance, not a big-bang control regime that freezes working agents.
- Technical skill must be "coupled with very strong commerciality" ("purple people").\[9\] Talent profiles should show business-facing operations expertise, not only engineering.

**Our inferences on credibility (not evidenced by buyer surveys; general practice):**
- **Show, don't tell.** One end-to-end demo on realistic synthetic post-trade data beats architecture slides. Include a live red-team moment and the audit trail a regulator would ask for.
- **Be honest about limits.** Citing the adaptive-attack evidence and positioning detectors as signals builds trust with a sophisticated buyer. Overclaiming "AI catches rogue AI" is a likely failure mode.
- **Design for unknown internals explicitly.** Present a decision tree: if the agent uses AWS IAM roles → X; static API keys → Y; RPA/UI access → Z; MCP → W. This shows capability without pretending to know Nomura's estate.
- **Common failure reasons:** vendor-locked product pitches; demos that assume agents can be rewritten; ignoring Japan/FSA alongside Western regulators; no operating model; unconvincing staffing (generic AI profiles without IAM and post-trade depth).

### Recommended response shape
1. **Architecture strategy:** a six-layer "mediate, don't modify" reference architecture (discovery → registry → identity broker → policy gateway → data controls → telemetry and response), with phased observe → enforce rollout and explicit standards-adoption hooks (token exchange now; MCP auth and IETF agent drafts later).
2. **Entitlements POV:** the hybrid model from Q3, with risk-tiered positions and a governance cadence. Analytics propose; owners approve; policy-as-code enforces.
3. **Talent profiles (sample roles):** Agent Identity Architect (OAuth/SPIFFE/PAM); Post-Trade Domain Lead (settlement and reconciliation, reference data); Policy-as-Code Engineer (OPA/Cedar/ReBAC); Agent Security & Red Team Lead; AI Model Risk & Regulatory Lead (SS1/23, SR 11-7, MAS AIRG, FSA DP, EU AI Act/DORA); Detection & Telemetry Engineer; Operating Model / Change Lead with Japanese-language capability.
4. **Unified demo:** synthetic estate of about 8–12 systems and about 10 agents. Covers onboarding with discovery, shadow-mode baseline, usage-based right-sizing proposal with approval, live enforcement, and three rogue scenarios (prompt-injection, malfunction, A2A escalation), each with containment and a regulator-ready evidence pack.

## Open Questions Only Nomura Can Answer

1. **Sponsor's exact title, reporting line and mandate boundary with the CIO, CISO and Group CIO Risk Management Committee.** This determines who signs off and whether identity enforcement is in scope or advisory.
2. **How do existing agents authenticate today** (service accounts, API keys, AWS IAM roles, RPA credentials, human credentials reused)? This decides the feasibility and sequencing of credential substitution.
3. **What runtimes and frameworks host agents** (Bedrock, OpenAI, in-house, vendor-embedded)? This determines where gateways and telemetry can attach.
4. **Do agents call each other, and how?** It sets the priority of delegation-chain controls.
5. **Which systems among the 160+ are in which jurisdiction and legal entity?** This determines which regulatory regime (FSA, MAS, FCA/PRA, EU, FINRA) applies to each control.
6. **Existing IGA/PAM/IdP and policy tooling.** Reuse vs. new build, and the vendor-neutrality expectation.
7. **Risk appetite for automated enforcement:** may the platform revoke an agent's access without human approval during market hours? This defines containment design.
8. **Tolerance for latency and outage in post-trade flows.** It decides inline vs. out-of-band enforcement per flow.
9. **Has Nomura experienced agent-related incidents or near misses?** These would anchor the demo scenarios in real pain.
10. **Data classification and entitlement metadata maturity.** ABAC is only as good as tags.
11. **What does "optimised" mean to the sponsor:** fewer standing privileges, lower review burden, faster onboarding, or cost?
12. **Hong Kong and India entity footprint and regulator interactions**, which were not researched here.

## Caveats

- **Time sensitivity:** MAS guidelines (7 October 2026) are a week old. IETF drafts expire every six months and MCP spec revisions are frequent. Recheck all standard statuses before submission.
- **Leadership data:** the current Group CDO identity is unverified. Several leadership facts come from press, LinkedIn or aggregator sources, and departures in 2025–26 mean the organisation may have changed.
- **Vendor-sourced material:** AWS and Microsoft case studies and security-vendor blogs are marketing-adjacent. BNY's payments metrics come via a Microsoft case study. The CB Insights funding figure is secondary, and the 59% IAM statistic comes from vendor JumpCloud's own survey.
- **Benchmarks are not production evidence:** detection figures come from AgentDojo-style lab environments with different baselines that are not directly comparable. None are capital-markets-specific.
- **Q3 ratings** are qualitative judgements extrapolated from human/workload IAM. No rigorous agent-specific comparative study was found.
- **Gaps:** HKMA/SFC and SEBI/RBI expectations, Bank of Japan detail, ESMA/EBA AI statements, and named SI deployments were not researched in depth in this cycle.
- **Client statements** (160+ systems, numerous agents in production) are taken as the client's position and were not independently verified.
- Sources are provided through the accompanying citation layer rather than as a separate list in this document.

## Sources

1. <https://www.nomuraholdings.com/doc/en/investor/library/ar/report/2025_47_58.pdf>
2. [© Nomura April 2026 Nomura Group's Governance Initiatives Nomura Holdings, Inc.](https://www.nomuraholdings.com/en/investor/presentation/main/02/teaserItems1/010/tableContents/00/multiFileUpload10/link/2025_0331_prem.pdf)
3. [Analyst - Data Governance Job Details](https://careers.nomura.com/Nomura/job/Mumbai-Analyst-Data-Governance/1321388000/)
4. [VP - AI Governance Job Details](https://careers.nomura.com/Nomura/job/Mumbai-VP-AI-Governance/1389676100/)
5. [Investor Day 2026 - Reaching for Sustainable Growth](https://www.nomuraholdings.com/en/investor/presentation/main/017/teaserItems1/00/tableContents/00/multiFileUpload30/link/2025_0530_01_prem.pdf)
6. [Shinya Murakami - Vice President at Nomura](https://www.linkedin.com/in/shinya-murakami-198005249/)
7. [Deep Thomas, Nomura Group Chief Data Officer, Joins CDO Magazine Global Editorial Board](https://www.cdomagazine.tech/editorial-board-announcements/deep-thomas-nomura-group-chief-data-officer-joins-cdo-magazine-global-editorial-board)
8. [JPMorganChase Appoints Deep Thomas as APAC Chief Data & Analytics Officer - CDO Magazine](https://www.cdomagazine.tech/leadership-moves/jpmorganchase-appoints-deep-thomas-as-apac-chief-data-analytics-officer)
9. [Nomura’s chief data office managing director on getting data ready for AI - Raconteur](https://www.raconteur.net/technology/nomuras-chief-data-office-managing-director-on-getting-data-ready-for-ai)
10. [The Unsung Heroes of the Innovation Economy? Forward-Thinking Corporate Executives - B Capital](https://b.capital/insights/the-unsung-heroes-of-the-innovation-economy-forward-thinking-corporate-executives/)
11. [JPMorgan Hires Nomura's International Head of AI Strategy - Bloomberg](https://www.bloomberg.com/news/articles/2026-06-08/jpmorgan-hiring-nomura-s-international-ai-strategy-chief)
12. <https://www.nomuraholdings.com/en/news/nr/nhi20260227a/main/0/link/20260227_nhi_a.pdf>
13. [bedrock nomura](https://aws.amazon.com/solutions/case-studies/bedrock-nomura)
14. [Nomura on AWS: Case Studies, Videos, Innovator Stories](https://aws.amazon.com/solutions/case-studies/innovators/nomura/)
15. [Nomura, OpenAI partner on asset management](https://www.privatebankerinternational.com/news/nomura-openai-asset-management-partnership/)
16. [Nomura Research Institute's Medium-Term Plan Shows Margin Upside From AI Consulting](https://www.morningstar.com/company-reports/1476888-nomura-research-institutes-medium-term-plan-shows-margin-upside-from-ai-consulting)
17. [AI & Innovation Program Manager, Global Markets Job Details](https://careers.nomura.com/Nomura/job/New-York-AI-&-Innovation-Program-Manager,-Global-Markets-NY-10019/1416167500/)
18. [Japan AI Regulation News: How the World's Third-Largest Economy Governs AI Without Binding Rules - Tech Jacks Solutions](https://techjacksolutions.com/ai-brief/japan-ai-regulation-news-how-the-worlds-third-largest-econom/)
19. [Publication of AI Discussion Paper (Version 1.1) : FSA](https://www.fsa.go.jp/en/news/2026/20260303/aidp.html)
20. [Understanding Japan’s AI Shift in Finance: Challenges and Priorities (Basic Version)](https://www.abeam.com/jp/en/insights/089/)
21. [MAS Sets Out Supervisory Expectations on Responsible AI Adoption by Financial Institutions](https://www.mas.gov.sg/news/media-releases/2026/mas-sets-out-supervisory-expectations-on-responsible-ai-adoption-by-financial-institutions)
22. [Guidelines on Artificial Intelligence Risk Management for Financial Institutions](https://www.mas.gov.sg/regulation/guidelines/guidelines-on-artificial-intelligence-risk-management-for-financial-institutions)
23. [MAS Issues AI Risk Management Guidelines for Financial Institutions - OpenGov Asia](https://opengovasia.com/mas-issues-ai-risk-management-guidelines-for-financial-institutions/?c=us)
24. [MAS Finalises AI Risk Guidelines for Financial Firms](https://www.leaprate.com/regulation/mas-finalises-ai-risk-guidelines-for-financial-firms/)
25. [Best Practices for AI Governance and Risk Management Published for Singapore Financial Sector](https://www.rajahtannasia.com/viewpoints/best-practices-for-ai-governance-and-risk-management-published-for-singapore-financial-sector/)
26. [AI Risk Management: Operationalisation Handbook January 2026](https://www.mas.gov.sg/-/media/mas-media-library/schemes-and-initiatives/ftig/project-mindforge/mindforge-ai-risk-management-operationalisation-handbook.pdf)
27. [Governance by Design: A Parsonian Institutional Architecture for Internet-Wide Agent Societies](https://arxiv.org/pdf/2604.11337)
28. [AI Governance for Financial Services: FCA & PRA 2026 - SureCloud](https://www.surecloud.com/blog-hub/ai-governance-financial-services-fca-pra)
29. [Keeping an eye on AI in financial services: recent regulator messaging on the agentic "step change" - Burges Salmon](https://www.burges-salmon.com/articles/102n7kt/keeping-an-eye-on-ai-in-financial-services-recent-regulator-messaging-on-the-age/)
30. [Agentic Finance, the FCA, and a Brave New World: The Mills Review 2026](https://www.stephensonharwood.com/post/102n942/agentic-finance-the-fca-and-a-brave-new-world-the-mills-review-2026/)
31. [AI in financial services: Responses to the Committee’s First report](https://publications.parliament.uk/pa/cm5901/cmselect/cmtreasy/1791/report.html)
32. [Agent-to-Agent Finance: Blockchain Payments and Trust Infrastructure for Autonomous AI Agents](https://arxiv.org/pdf/2607.00245)
33. [FINRA Publishes 2026 Regulatory Oversight Report to Empower Member Firm Compliance](https://www.finra.org/media-center/newsreleases/2025/finra-publishes-2026-regulatory-oversight-report-empower-member-firm)
34. [FINRA’s 2026 Regulatory Oversight Report: Continued Focus on Generative AI and Emerging Agent-Based Risks](https://www.debevoisedatablog.com/2025/12/11/finras-2026-regulatory-oversight-report-continued-focus-on-generative-ai-and-emerging-agent-based-risks/)
35. [FINRA 2026 Oversight Report: GenAI and AI Agent Expectations](https://www.meilynx.com/reference/finra-2026-oversight-report-genai)
36. [news insiders](https://www.marketscreener.com/quote/stock/NOMURA-HOLDINGS-INC-6492527/news-insiders/)
37. [BNY Mellon gives agentic AI 'staff' logins & human managers](https://www.hrgrapevine.com/us/content/article/2025-07-17-bny-mellon-gives-ai-staff-logins-human-managers)
38. [BNY to give AI-powered 'digital employees' their own emails](https://www.finextra.com/newsarticle/46243/bny-to-give-ai-powered-digital-employees-their-own-emails)
39. [JPMorgan Chase AI: Bank to deploy more powerful agents this year](https://www.cnbc.com/2026/06/09/jpmorgan-chase-ai-agents.html)
40. [Authorization Architectures for Tool-Using AI Agents](https://arxiv.org/pdf/2609.15906)
41. [Ethical Hyper-Velocity (EHV): A Hardware-Rooted Zero-Trust Runtime Enforcement Architecture for Agentic AI Systems](https://arxiv.org/pdf/2605.17909)
42. [AI Agent Authentication and Authorization](https://www.ietf.org/archive/id/draft-klrc-aiagent-auth-00.html)
43. [agenda-interim-2026-wimse-01-wimse-01](https://datatracker.ietf.org/doc/agenda-interim-2026-wimse-01-wimse-01/)
44. [OAuth 2.0 Extension: On-Behalf-Of User Authorization for AI Agents](https://datatracker.ietf.org/doc/html/draft-oauth-ai-agents-on-behalf-of-user-02)
45. [OAuth Profile for Delegated AI Agent Authorization](https://www.ietf.org/archive/id/draft-mishra-oauth-agent-grants-02.html)
46. [OAuth's On-Behalf-Of flow for AI agents — WorkOS](https://workos.com/blog/oauth-on-behalf-of-ai-agents)
47. [NIST AI Agent Authorization: Five Asks Mapped to Kubernetes - ARMO](https://www.armosec.io/blog/nist-ai-agent-identity-authorization/)
48. [NIST's AI Agent Standards Initiative: What CISOs Need to Know and How to Prepare](https://www.metricstream.com/blog/nists-ai-agent-standards-initiative.html)
49. [OWASP Top 10 for Agentic Applications 2026](https://cycode.com/blog/owasp-top-10-agentic-applications/)
50. [MAS Finalises AI Risk Guidelines: What Actually Changed](https://genesishumanexperience.com/2026/10/07/mas-ai-risk-management-guidelines-final-2026/)
51. [AI Agent Governance Starts With Identity - BankInfoSecurity](https://www.bankinfosecurity.com/ai-agent-governance-starts-identity-a-33063)
52. [Digital Employees: How BNY Scaled to 100+ AI Agents When Others Can't Get Past 10](https://www.thehelixloop.com/digital-employees-how-bny-scaled-to-100-ai-agents-when-others-cant-get-past-10/)
53. [EchoLeak (CVE-2025-32711): What the Microsoft Copilot Prompt Injection Vulnerability Means for Your Data](https://sentra.io/blog/copilot-echoleak-prompt-injection)
54. [Banks Put AI Agents Through Performance Reviews](https://www.pymnts.com/news/artificial-intelligence/2026/banks-put-ai-agents-through-performance-reviews/)
55. [The Comprehensive Guide to Prompt Injection Attacks in 2026](https://www.sysdig.com/learn-cloud-native/prompt-injection)
56. [Prompt injection: types, real-world CVEs, and enterprise defenses](https://www.vectra.ai/topics/prompt-injection)
57. [OWASP Top 10 for Agentic Applications 2026: Key Takeaways & How to Take Action](https://goteleport.com/blog/owasp-top-10-agentic-applications/)
58. [OWASP Agentic Top 10 Released: AI Risks](https://astrix.security/learn/blog/the-owasp-agentic-top-10-just-dropped-heres-what-you-need-to-know/)
59. [Lessons from OWASP Top 10 for Agentic Applications](https://auth0.com/blog/owasp-top-10-agentic-applications-lessons/)
60. [OWASP Top 10 for Agentic Applications](https://www.promptfoo.dev/docs/red-team/owasp-agentic-ai/)
61. [AIP: Agent Identity Protocol for Verifiable Delegation Across MCP and A2A](https://arxiv.org/pdf/2603.24775)
62. <https://arxiv.org/pdf/2406.13352v3>
63. <https://arxiv.org/pdf/2505.03574v1>
64. <https://arxiv.org/pdf/2510.09023>
65. <https://arxiv.org/pdf/2503.18813v2>
66. [how-microsoft-defends-against-indirect-prompt-injection-attacks](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks)
67. [FINRA 2026 Oversight Report: GenAI is key compliance risk](https://www.globalrelay.com/resources/thought-leadership/finra-2026-oversight-report-flags-genai-recordkeeping-and-cybersecurity-risks/)
68. [What FINRA's 2026 Oversight Report Means for AI and Recordkeeping](https://archiveintel.com/blog/finra-2026-ai-recordkeeping)
69. [Addressing the OWASP Top 10 Risks in Agentic AI with Microsoft Copilot Studio](https://www.microsoft.com/en-us/security/blog/2026/03/30/addressing-the-owasp-top-10-risks-in-agentic-ai-with-microsoft-copilot-studio/)
70. [Everything you should know about NIST's AI Agent Standards Initiative — WorkOS](https://workos.com/blog/nist-ai-agent-standards-initiative-explained)
71. [The Promptware Kill Chain: How Prompt Injections Gradually Evolved Into a Multistep Malware Delivery Mechanism](https://arxiv.org/pdf/2601.09625)
72. [AI in Banking Just Got Real](https://www.ccgcatalyst.com/thought-leadership/commentary/ai-in-banking-just-got-real/)
73. [The approach to AI governance in Japanese financial ...](https://assets.kpmg.com/content/dam/kpmg/jp/pdf/2025/jp-ai-governance-en.pdf)
