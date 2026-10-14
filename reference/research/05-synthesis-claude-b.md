# Governing the Agent Mesh at Nomura: Entitlement Architecture, Hybrid Governance Framework and Capability-Demo Blueprint (Straive Proposal Synthesis, October 2026)

Straive should pitch Nomura a **deterministic-first, AI-assisted** agent governance framework. Every agent gets a cryptographic identity and a named human owner. Every call an agent makes to a system or tool is authorised by a deterministic policy engine with default-deny. Cross-domain "need-to-know" access is granted only as short-lived, task-scoped, attenuated tokens. LLMs are kept *out* of the inline allow/deny path and used for justification, exception triage, investigation and permission right-sizing recommendations that a human signs off. This resolves the internal debate: Eswar and Dharmendra are right about the enforcement plane, Aryan is right that rigid static roles will break reconciliation pipelines, and Anand's adversarial loop becomes the continuous-assurance engine rather than an autonomous policy author.

## TL;DR

- **The problem is an identity problem before it is an AI problem.** Rubrik Zero Labs puts the non-human-to-human identity ratio at 45:1, Entro Labs' H1 2025 report found the average grew from 92:1 to 144:1, most of these identities are over-privileged, and regulators (FINRA's 2026 Oversight Report, DORA's RTS 2024/1774, Japan FSA's AI Discussion Paper v1.1, MAS's final AI Risk Management Guidelines) now expect agents to be uniquely identified, least-privileged, logged and supervised. Nomura's 160+ systems bridged by ungoverned agents is a textbook DORA/FINRA gap.
- **Recommended architecture: five tiers.** Tier 0 agent identity and registry; Tier 1 deterministic PDP/PEP gateway (RBAC/ABAC/ReBAC plus row/column security); Tier 2 just-in-time, task-bound elevation (AI may recommend, policy plus human grants); Tier 3 behavioural monitoring with AI triage off the hot path; Tier 4 audit, kill-switch and a human-approved permission-optimisation loop. This keeps authorisation latency in the low-millisecond range, auditable and explainable to regulators, while still enabling Aryan's dynamic cross-domain access.
- **Deliverable: one 12-minute demo, not four options.** Baseline entitlements first (Aditi), then three rogue-agent scenarios (prompt-injected reconciliation agent reaching for KYC PII, delegation-chain privilege escalation, over-broad tool exfiltration) caught, contained, explained and remediated, with a control-mapped audit trail (DORA RTS Art. 12/20/21, SOC 2, OWASP ASI). Build in ~6 weeks with a 5–6 person pod; position it as Phase 0 of a phased, vendor-neutral engagement.

## Key Findings

1. **Agent governance is now a supervisory expectation, not a nice-to-have.** FINRA's 2026 Annual Regulatory Oversight Report (9 December 2025) for the first time addresses AI agents, flagging risks of agents "acting autonomously without human validation and approval" and acting "beyond the user's actual or intended scope and authority," and suggests agent-specific supervisory processes covering monitoring of system access and data handling, human-in-the-loop placement, tracking of agent actions, and guardrails.\[1\]\[2\]\[3\] Japan's FSA published AI Discussion Paper v1.1 on 3 March 2026 after a public-private forum.\[4\] MAS finalised its Guidelines on AI Risk Management on 7 October 2026, applying them to all forms of AI including agentic AI.\[5\]\[6\]
2. **The US model-risk safe harbour has disappeared for agents.** SR 26-2 (17 April 2026), which replaced SR 11-7, explicitly places generative and agentic AI outside its scope and tells banks to use their existing risk management and governance practices instead.\[7\]\[8\]\[9\] In practice, this means agent governance at Nomura's US broker-dealer will be judged against operational, cyber and supervisory controls (FINRA Rule 3110, access control, logging), which is exactly the entitlement layer Nomura lacks.
3. **DORA already contains the entitlement requirements in black and white.** The RTS on ICT risk management (Delegated Regulation 2024/1774) requires "unique identification and authentication of natural persons and systems" (Art. 20), access "based on need-to-know, need-to-use and least privilege principles" (Art. 21(a)), limiting "generic and shared user accounts" (Art. 21(c)), access reviews at least every 6 months for systems supporting critical or important functions (Art. 21(e)(iv)), and logging of access-control and identity-management events, protected against tampering (Art. 12).\[10\]\[11\]\[12\] Shared service accounts used by agents are a direct finding against Art. 21(c).
4. **The tooling and standards market has matured fast in 2025–2026.** Microsoft Entra Agent ID reached general availability in April 2026 and Agent 365 on 1 May 2026;\[13\]\[14\] Okta for AI Agents shipped 30 April 2026 with an Agent Gateway and agent-to-agent connections; CyberArk's Secure AI Agents Solution became generally available (announced 4 November 2025).\[15\]\[16\]\[17\] NIST's NCCoE published a concept paper on AI agent identity and authorization (5 February 2026) that proposes applying OAuth 2.0, SPIFFE/SPIRE and MCP rather than inventing a new stack.\[18\]\[19\] MCP's authorization spec now mandates OAuth 2.1 with RFC 8707 resource indicators.\[20\]\[21\] This means Straive should position as a **vendor-neutral integrator and governance-design partner**, not as a product vendor.
5. **Peer banks are putting agents directly into Nomura's problem domain.** Goldman Sachs CIO Marco Argenti told CNBC (6 February 2026) that embedded Anthropic engineers have been co-developing Claude-based agents "in at least two specific areas: accounting for trades and transactions, and client vetting and onboarding," and that the firm is "in the early stages." JPMorgan's chief analytics officer Derek Waldron told CNBC (9 June 2026) that agents "don't just run for two or three minutes… they can run for an hour or two" and "we will have those in 2026." Nomura itself has built "Core AI," a multi-LLM orchestration platform on Amazon Bedrock and Anthropic Claude, developed with the AWS Generative AI Innovation Center "over 12 months" using "multi-LLM orchestration and AI-based compliance checks" (AWS case study). Agents with hours of autonomy touching reconciliation and KYC raise the stakes on entitlement.
6. **Inline LLM-over-LLM gatekeeping is the wrong design for the enforcement plane.** It is non-deterministic, slow relative to STP budgets, vulnerable to the same prompt injection it is meant to catch, and hard to explain to an examiner. LLMs belong in Tier 2 (justification) and Tier 3/4 (triage, investigation, right-sizing proposals), never as the sole authority on allow/deny.

## 1. Problem Statement Expansion and Enterprise Context

### 1.1 The core friction at Nomura

Nomura runs more than 160 systems across heterogeneous stacks (trade capture, booking, confirmation/affirmation, settlement, nostro/depot reconciliation, client reference data, regulatory reporting). Because these systems do not natively interoperate, STP breaks at every seam, and Nomura has filled the seams with AI agents. That has created an **agent mesh with no control plane**: agents are effectively privileged integration middleware, yet they are governed, if at all, as generic service accounts.

**Stakeholder title discrepancy (action item):** the internal notes refer to Nomura's sponsor as the "Chief **Data** Innovation Officer," while the request brief says "Chief **Digital** Innovation Officer." The team must confirm the exact title before any material is sent; getting a sponsor's title wrong in a governance pitch undermines credibility.

### 1.2 How agents bridging trade, settlement and reconciliation create risk

| Risk vector | How it manifests in Nomura's agent mesh | Why it matters |
|---|---|---|
| Credential sprawl | Each agent holds API keys, DB credentials and SaaS tokens for multiple systems, often in config files or prompts | Entro's separate 2025 State of NHIs report found 97% of NHIs carry excessive privileges, and its H1 2025 report found 5.5% of AWS machine identities had full admin access; leaked secrets give persistent, MFA-free access |
| Shared service accounts | Several agents (and sometimes humans) use one integration account per system | Actions cannot be attributed to a specific agent; direct conflict with DORA RTS Art. 21(c) and OWASP NHI9 (NHI Reuse) / NHI10 (Human Use of NHI)\[22\] |
| Over-privileged API keys | Reconciliation agent given read-all on the client master "to be safe" | OWASP NHI5 (Overprivileged NHI); blast radius of any compromise equals the union of all grants\[22\] |
| Prompt injection / goal hijack | A malicious string in a SWIFT MT/ISO 20022 free-text field, a counterparty email or a PDF confirmation instructs the agent to fetch and forward data | OWASP ASI01 Agent Goal Hijack;\[23\] indirect injection travels through ordinary data feeds |
| Confused deputy | A low-privilege agent asks a high-privilege agent to fetch data on its behalf; the high-privilege agent uses its *own* rights | Classic authorisation bypass; OWASP ASI03 Identity and Privilege Abuse\[23\] |
| Agent-to-agent delegation chains | Booking → Settlement → Reconciliation → Reporting agents pass tasks and context without carrying the originating principal or scope | Privileges amplify along the chain instead of attenuating; OWASP ASI07 Insecure Inter-Agent Communication\[23\] |
| Information barriers / Chinese walls | A research or deal-team agent with MNPI-flagged data shares a vector store or tool with a sales/trading agent | Market-abuse and insider-dealing exposure; barrier breaches are regulatory events, not just security incidents |
| PII / KYC leakage | Agents pull client KYC fields into prompts sent to an external LLM endpoint or log them | Privacy law (APPI in Japan, GDPR in the EU), data residency, and FINRA's flagged risk that agents may "unintentionally store, explore, disclose, or misuse sensitive or proprietary information"\[2\] |
| T+1 settlement pressure | The US moved to T+1 in May 2024; the EU, UK and Switzerland move on 11 October 2027\[24\]\[25\]\[26\] | Compressed windows push teams to grant broad standing access "so the breaks get fixed tonight," and make any governance layer that adds seconds of latency or false-positive blocks commercially unacceptable |
| Third-party / supply-chain NHI | Vendor-hosted agents or SaaS integrations hold OAuth refresh tokens into Nomura systems | The August 2025 Salesloft Drift incident saw stolen OAuth tokens used to access Salesforce data at more than 700 organisations, bypassing MFA entirely (FINRA issued a cybersecurity alert)\[27\]\[28\] |

### 1.3 Benchmarks: the NHI and agent-identity landscape (2025–2026)

**Scale of the problem.** Estimates vary by methodology, but every credible source points the same way:

| Source | Finding |
|---|---|
| Entro Labs, NHI & Secrets Risk Report H1 2025 | Analysing 27M+ NHIs, found "the average growing from 92:1 to 144:1"; NHIs grew 44% year on year; 5.5% of AWS machine identities had full admin access and 62% of AWS NHIs showed no activity in the past 90 days (the widely cited 97% over-privilege figure comes from Entro's separate 2025 State of NHIs report) |
| CyberArk 2025 Identity Security Landscape (Vanson Bourne; 2,600 decision-makers, 20 countries) | "82 machine identities for every human"; 88% define a privileged user as human-only |
| Rubrik Zero Labs (The Hacker News, May 2026); CSA NHI research | 45:1 NHI-to-human ratio in the modern enterprise (Rubrik); CSA reports 51% of organisations have no clear ownership of AI identities (citing WEF) |
| Gravitee State of AI Agent Security 2026 survey (cited by Okta at Showcase 2026) | Only 22% (21.9%) of organisations treat AI agents as independent, identity-bearing entities; 88% reported confirmed or suspected AI agent security incidents |
| MCP ecosystem research (vendor-reported, via NHIMG) | Only 18% of MCP server deployments implement any access scoping for tool permissions; 53% expose credentials through hard-coded configuration values\[29\] |

*Interpretation:* the ratio numbers are vendor-sourced and not directly comparable, so they should be quoted as a range in client materials. The consistent signals that matter for Nomura are (a) agents are being bolted onto an NHI estate that is already ungoverned, and (b) most organisations still classify privilege as a human concept, which is exactly the gap the CDIO identified.

### 1.4 Regulatory and standards benchmark

| Framework | Status (as of Oct 2026) | What it implies for agent entitlement at Nomura |
|---|---|---|
| **EU DORA** (Reg. 2022/2554) + RTS 2024/1774 | Applicable since 17 Jan 2025 | Art. 9(4)(c): limit logical access "to what is required for legitimate and approved functions"; RTS Art. 20: unique identification of "natural persons and systems," identity lifecycle; Art. 21: least privilege, segregation of duties, no generic/shared accounts, 6-monthly reviews for critical systems, PAM automation; Art. 12: log access-control and identity events, tamper-protected.\[10\]\[11\]\[12\]\[30\] Third-party risk rules apply to LLM/agent vendors. Relevant to Nomura's EU entities |
| **EU AI Act** | Digital Omnibus agreed 7 May 2026; Annex III high-risk obligations now apply 2 Dec 2027, Annex I-embedded 2 Aug 2028\[31\]\[32\] | Most back-office reconciliation agents are unlikely to be Annex III high-risk (credit scoring and some insurance underwriting are), but transparency and AI-literacy duties apply, and logging/human oversight design should anticipate high-risk-style controls |
| **US: SR 26-2** (Fed/OCC/FDIC, 17 Apr 2026) | Replaces SR 11-7 and SR 21-8\[33\] | Explicitly excludes GenAI and agentic AI; banks must govern them via existing risk and governance practices.\[7\] Entitlement and supervision controls carry the load |
| **FINRA 2026 Oversight Report** | Published 9 Dec 2025 | First dedicated treatment of AI agents: autonomy, scope/authority, data sensitivity risks; recommends monitoring agent access and data handling, human-in-the-loop, action tracking, guardrails; prompt/output logs for accountability\[2\]\[3\]\[34\] |
| **SEC** | No agent-specific rule identified in this research | Reg S-P (customer data safeguards) and books-and-records obligations still apply to agent actions and outputs |
| **Japan FSA** AI Discussion Paper v1.0 (Mar 2025) → v1.1 (3 Mar 2026) | Non-binding; dialogue-based | Encourages adoption ("risk of inaction") while emphasising governance, explainability and internal audit of AI;\[35\]\[36\]\[37\] home-regulator signal for Nomura Holdings |
| **MAS** Guidelines on AI Risk Management | Final, 7 Oct 2026 (phased deadlines reported as Oct 2027 and Oct 2028)\[5\] | Applies to all AI including agentic; board oversight, AI inventory, materiality assessment, lifecycle controls; relevant to Nomura Singapore\[5\]\[6\]\[38\] |
| **UK FCA / PRA** | PRA SS1/23 model risk principles in force; FCA principles-based approach\[39\] | Model risk and operational resilience regimes apply; T+1 on 11 Oct 2027\[40\]\[41\] |
| **BCBS 239** | Ongoing supervisory focus | Data lineage, accuracy and completeness: agents that transform risk/finance data must be traceable in lineage |
| **NIST AI RMF / AI 600-1 GenAI Profile** | Voluntary | Govern-Map-Measure-Manage structure for the AI risk programme; useful as the umbrella taxonomy |
| **NIST NCCoE agent identity concept paper** (5 Feb 2026) + CAISI AI Agent Standards Initiative (17 Feb 2026) | Draft; comments closed 2 Apr 2026\[42\] | Direction of travel: apply OAuth 2.0, SPIFFE/SPIRE and MCP to agents; authorisation evaluated at action time; not yet a testable standard\[19\]\[42\] |
| **ISO/IEC 42001** | Certifiable AI management system standard | Gives Nomura an auditable AIMS wrapper; the entitlement framework becomes one of its operational controls |
| **SOC 2** (Trust Services Criteria) | Attestation standard | Logical access (CC6.x) and monitoring (CC7.x) criteria map directly to Tiers 1, 3 and 4; relevant if Straive operates any managed component |
| **OWASP Top 10 for LLM Applications (2025)** | Published | Prompt injection, sensitive information disclosure, excessive agency |
| **OWASP Top 10 for Agentic Applications 2026** (9 Dec 2025) | Published, 100+ contributors\[43\] | ASI01 Goal Hijack, ASI02 Tool Misuse, ASI03 Identity & Privilege Abuse, ASI04 Supply Chain, ASI07 Insecure Inter-Agent Communication, ASI10 Rogue Agents; promotes "least agency"\[23\] |
| **OWASP Non-Human Identities Top 10 (2025)** | Published | NHI1 Improper Offboarding through NHI10 Human Use of NHI; the checklist for Tier 0\[44\]\[45\] |

### 1.5 Standards and vendor building blocks

- **Workload identity:** SPIFFE/SPIRE issues short-lived, cryptographically verifiable identities (SVIDs) to workloads; the NCCoE concept paper names it as a candidate for agent identity.\[19\]
- **Delegation:** OAuth 2.0 Token Exchange (RFC 8693) supports on-behalf-of and actor claims. IETF drafts extend it for agents, including *draft-oauth-ai-agents-on-behalf-of-user* (requested_actor / actor_token), *draft-mishra-oauth-agent-grants-02* (August 2026, attenuating authority through token exchange and sender-constrained tokens), *draft-klrc-aiagent-auth-00* (applying existing standards rather than new protocols, including CIBA step-up for user confirmation), and *draft-mcguinness-oauth-ai-agent-instance-00* (per-instance agent identity, because platforms otherwise collapse "every agent session into one identity").\[46\]\[47\]\[48\]\[49\] These are drafts, not standards; design for them, but do not depend on them.
- **MCP authorization:** MCP servers act as OAuth 2.1 resource servers; clients must use RFC 9728 protected-resource metadata and send RFC 8707 resource indicators so tokens are audience-bound to one MCP server. Current revision is 2026-07-28.\[21\]\[50\]
- **A2A:** Google announced Agent2Agent in April 2025 and donated it to the Linux Foundation on 23 June 2025 (founding members included AWS, Cisco, Google, Microsoft, Salesforce, SAP and ServiceNow);\[51\] in 2026 it joined the Linux Foundation's Agentic AI Foundation alongside MCP.\[52\] Agents publish an Agent Card at `/.well-known/agent-card.json` declaring OpenAPI-style security schemes (OAuth2, OIDC, mTLS, bearer); the spec states servers must authenticate every request and recommends against static secrets in cards.\[53\]\[54\] A2A handles *how* agents present credentials, not *what* they are allowed to do; that remains Nomura's job.
- **Policy engines:** OPA/Rego (CNCF-graduated, general purpose), AWS Cedar / Amazon Verified Permissions (analysable policy language), and Zanzibar-style ReBAC (OpenFGA, SpiceDB) for relationship-based rules such as "agent may read trades for books it is assigned to."
- **Agent identity products:** Microsoft Entra Agent ID (GA April 2026; Conditional Access, ID Protection, lifecycle workflows for agents);\[14\]\[55\] Okta for AI Agents (GA 30 April 2026; shadow agent discovery, Agent Gateway, Universal Logout to revoke all tokens if an agent deviates; July 2026 added Agent-to-Agent Connections and resource access certifications); CyberArk Secure AI Agents (zero standing privileges, session monitoring); AWS Bedrock AgentCore Identity.\[15\]\[16\]\[17\]\[56\]\[57\]

### 1.6 What peer banks are publicly doing

| Firm | Public signal | Implication for Nomura |
|---|---|---|
| Goldman Sachs | Embedded Anthropic engineers co-developing Claude-based agents "in at least two specific areas: accounting for trades and transactions, and client vetting and onboarding"; firm is "in the early stages" (CIO Marco Argenti, CNBC, 6 Feb 2026) | Agents are moving into exactly the reconciliation/KYC flows where Nomura's entitlement gap bites |
| JPMorgan Chase | Agents that "don't just run for two or three minutes… they can run for an hour or two"; "We will have those in 2026" (Derek Waldron, CNBC, 9 June 2026); public messaging that autonomy and controls should "grow in tandem" | Long-running agents make standing privileges more dangerous; continuous authorisation becomes mandatory |
| Morgan Stanley and others | No specific public agent-entitlement architecture identified in this research | Do not claim peer practices we cannot cite; frame Nomura as an opportunity to lead |
| Nomura | "Core AI" multi-LLM orchestration platform built with AWS GenAI Innovation Center on Amazon Bedrock and Anthropic Claude "over 12 months," using "multi-LLM orchestration and AI-based compliance checks" to resolve ad-review bottlenecks (AWS case study) | Strong hint that agents are Bedrock/Claude-centric with orchestration (LangChain / Semantic Kernel appear in Nomura's AWS Summit materials);\[58\] confirm in discovery |

## 2. Architectural Evaluation and Hybrid Governance Framework

### 2.1 The tension: deterministic rules vs dynamic AI enforcement

| Dimension | Deterministic policy (RBAC/ABAC/ReBAC, Cedar/Rego, SQL views with RLS/CLS) | LLM-over-LLM "super/mother agent" as gatekeeper |
|---|---|---|
| Security | Default-deny, formally analysable (Cedar), immune to prompt injection because it does not read natural language | Inherits the attack surface it polices; a crafted justification can talk the governor into granting access |
| Latency | Sub-millisecond to low-millisecond in-process evaluation; cacheable | Hundreds of ms to seconds per decision; multiplies across chained calls; threatens STP/T+1 windows |
| Cost | Near-zero marginal cost per decision | Token cost on every tool call; agentic call volumes multiply this |
| Auditability | Same input → same decision; policy-as-code in Git with reviews | Non-reproducible decisions; model/version drift changes outcomes |
| Regulatory explainability | "Denied by policy P-117: reconciliation agents may not read KYC.PII outside task scope" | "The model judged it inappropriate"; weak evidence for DORA/FINRA examiners |
| Failure modes | Too rigid: false denials break pipelines; role explosion | Compounding probabilistic error: if each of three chained LLM judgments is 98% correct, the chain is only ~94% correct; silent false allows |
| Adaptability | Poor for novel, context-dependent needs (Aryan's point) | Excellent at understanding context and intent |
| Best use | **Enforcement** (the allow/deny decision) | **Advisory**: justification, risk scoring, triage, investigation, policy-change proposals |

**Verdict:** Eswar's warning about compounding uncertainty is correct for the enforcement plane, and Aryan's concern about rigidity is correct for the access-request plane. The design answer is to separate *who decides* (deterministic policy plus accountable humans) from *who reasons* (AI), and to make dynamic access a *governed workflow* rather than an AI judgment.

### 2.2 Proposed five-tier hybrid governance framework

**Tier 0 — Agent Identity, Registry and Accountability**
- Every agent gets a unique, cryptographic workload identity (SPIFFE SVID or Entra Agent ID / Okta agent identity, depending on Nomura's IdP), with per-instance identity for concurrent runs.
- Agent registry/manifest ("agent card"): purpose, owner (named human plus business sponsor), model/provider and version, frameworks, tools and systems it may touch, data classifications, max autonomy level, environment, review date.
- Lifecycle: registration → approval → certification (6-monthly for critical systems, per DORA RTS Art. 21) → decommissioning (OWASP NHI1).\[10\]
- Secrets eliminated where possible (workload identity federation); otherwise vaulted, short-lived and rotated.

**Tier 1 — Deterministic Policy Decision and Enforcement (PDP/PEP)**
- An **Agent Gateway** (PEP) fronts every system API, database proxy and MCP server. No agent reaches a system directly; network policy enforces this.
- A centralised PDP evaluates policy-as-code (Cedar or OPA/Rego) combining RBAC (agent role), ABAC (data classification, desk, region, time, task ID, environment) and ReBAC (OpenFGA/SpiceDB: agent → assigned book/portfolio/client relationships).
- Data-layer enforcement: row-level and column-level security and masked views in the data platform (Dharmendra's layer), so even an allowed query returns only permitted rows and columns.
- Information-barrier rules encoded as hard denies (e.g., any principal tagged `side=private` cannot share tools, memory or vector stores with `side=public`).
- Default-deny and **fail-closed** for writes, PII, MNPI and payment/settlement instructions; a narrowly defined **fail-open-to-read-only-with-alert** mode for non-sensitive reads during PDP outage is a business decision Nomura must make explicitly.

**Tier 2 — Just-in-Time, Task-Bound Elevation and Delegation (reconciling Aryan and Eswar)**
- When an agent needs out-of-domain data (e.g., a reconciliation agent needing a counterparty's SSI or a limited client attribute to clear a break), it raises an **elevation request** tied to a task/break ID.
- A **Broker agent** (Aryan's "mother agent," with constrained powers) may assemble the justification, check that the break exists, and recommend the minimum scope; it *cannot* grant.
- Grant decision: deterministic pre-approved elevation policies auto-approve low-risk patterns (e.g., read one SSI record for a break that exists, 15 minutes); higher-risk requests go to a human approver (desk supervisor / data owner) via Slack/Teams/ServiceNow with step-up confirmation (CIBA-style).
- The issued credential is a short-lived, audience-bound, sender-constrained token (OAuth token exchange with actor claims; RFC 8707 resource binding), scoped to specific records/columns, expiring on task completion or TTL.
- **Delegation attenuation:** when Agent A delegates to Agent B, B's token is derived from A's and can only narrow scope (never widen), carries the full actor chain (`act` claims) and the originating principal, and has a maximum chain depth. This kills the confused-deputy and delegation-escalation patterns.

**Tier 3 — Behavioural Monitoring and Detection (deterministic plus ML, AI for triage)**
- Every PEP decision, token issuance and tool call streams to the SIEM (Splunk/Sentinel or Nomura's equivalent) with OpenTelemetry traces linking agent → task → tool → system → data classification.
- Deterministic detections: denied-call bursts, attempts on barrier-crossing resources, out-of-hours access, new tool use, token reuse from an unexpected workload.
- ML/statistical baselines: per-agent volume, entity-access and sequence anomalies (e.g., a reconciliation agent suddenly enumerating client records).
- Content guardrails at the gateway: prompt-injection classifiers on inbound data, DLP on outbound payloads (PII/MNPI patterns).
- **AI is used here for triage and investigation**, summarising an incident, reconstructing the chain and drafting the analyst note, *not* for inline blocking.
- Automated containment is deterministic: risk score above threshold → quarantine agent (revoke tokens, move to read-only or suspended state).

**Tier 4 — Audit, Lineage, Attestation, Kill-Switch and Continuous Optimisation**
- Tamper-evident decision log (append-only/WORM; hash-chained), satisfying DORA RTS Art. 12(2)(d) protection against "tampering, deletion, and unauthorised access."\[12\]
- Lineage: which agent touched which data element under which policy version, feeding BCBS 239 lineage.
- Kill-switch hierarchy: per-agent, per-agent-class, per-system, and global "agents read-only" mode, with tested runbooks.
- **Permission optimisation loop:** observed-usage analytics compare granted vs used entitlements; an AI assistant drafts right-sizing pull requests (remove unused scopes, tighten row filters, propose new pre-approved elevation patterns); Anand's red-team agent tests the proposed policy in a shadow environment; a **human policy owner approves** the PR; policy deploys via CI/CD with automated regression tests. No autonomous tightening or loosening in production.
- Control mapping: each log event and policy is tagged to DORA RTS articles, SOC 2 CC6/CC7, OWASP ASI/NHI IDs and FINRA supervisory expectations, so evidence packs are generated, not compiled.

### 2.3 Latency budget and failure posture

| Hop | Target budget (design recommendation) | How |
|---|---|---|
| PEP + PDP decision | ≤5 ms p99 | In-process or sidecar evaluation (Cedar/OPA), cached entity data, local policy bundles |
| ReBAC check | ≤10 ms p99 | OpenFGA/SpiceDB with consistency tokens and caching |
| Token exchange (Tier 2 auto-approved) | ≤100 ms | Pre-approved patterns; no human or LLM in path |
| Human-approved elevation | Minutes (SLA by desk) | Only for non-routine requests; measured and reported |
| Tier 3 detection | Seconds to minutes (async) | Streaming analytics; never on the hot path |

These figures are Straive design targets for the demo and should be validated in Nomura's environment, not presented as vendor benchmarks. The principle is that the governance layer should add milliseconds, not seconds, to an STP hop; under T+1 compression that is the difference between adoption and bypass.

### 2.4 Reference technology stack (vendor-neutral, with alternatives)

| Layer | Primary (demo) | Enterprise alternatives |
|---|---|---|
| Agent identity | SPIFFE/SPIRE | Microsoft Entra Agent ID, Okta for AI Agents, AWS AgentCore Identity |
| Authorisation server / token exchange | Keycloak (supports MCP authorisation profile) | Entra ID, Okta, Ping |
| Policy engine (PDP) | AWS Cedar (open source) or OPA/Rego | Amazon Verified Permissions, Styra |
| ReBAC | OpenFGA | SpiceDB/AuthZed |
| Gateway (PEP) | Envoy with ext_authz + custom MCP proxy | Okta Agent Gateway, Kong, Apigee, Azure API Management |
| Data-level security | PostgreSQL RLS + masked views (synthetic data) | Snowflake/Databricks row access and masking policies |
| Secrets/PAM | HashiCorp Vault | CyberArk (likely Nomura incumbent) |
| Agents and orchestration | LangGraph or Semantic Kernel agents on Bedrock/Claude (mirrors Nomura Core AI) | Nomura's actual frameworks |
| Agent protocols | MCP (tools), A2A (agent-to-agent) | — |
| Observability | OpenTelemetry → OpenSearch/Grafana | Splunk, Microsoft Sentinel |
| Guardrails | Prompt-injection classifier + DLP regex/NER at gateway | Bedrock Guardrails, Microsoft Purview, Lakera-class tools |
| Audit store | Append-only, hash-chained log (e.g., immutable object storage) | WORM storage under existing books-and-records |

### 2.5 Architecture diagram description (for the design team)

- **Left column, "Agent Plane":** four boxes — Trade Booking Agent, Settlement Agent, Reconciliation Agent, Client Reporting Agent — plus a red-outlined "Rogue/Red-Team Agent." Each box shows a small key icon labelled "SPIFFE ID / Agent ID" and an owner tag.
- **Top band, "Tier 0: Identity & Registry":** Agent Registry (manifests, owners, autonomy level), Identity Provider (workload identity + token service), Vault/PAM. Dotted lines from each agent to the registry.
- **Centre, "Tier 1: Agent Gateway (PEP)":** a single wide bar every agent arrow must cross. Attached above it, the "Policy Decision Point" (Cedar/OPA) and "ReBAC graph" (OpenFGA); attached below, "Guardrails (injection filter, DLP)."
- **Right column, "System Plane":** Trade Capture, Settlement/SSI store, Nostro Recon, Client KYC/PII store (lock icon), Research/MNPI store (separated by a thick vertical "Information Barrier" line), Regulatory Reporting. A "Row/Column Security" shim sits in front of the data stores.
- **Below the gateway, "Tier 2: JIT Elevation":** Broker Agent (recommend only) → Elevation Policy → Human Approver (Teams/ServiceNow) → Token Service issuing a "15-min, task-bound, attenuated token" back to the requesting agent.
- **Bottom band, "Tier 3: Monitoring":** event stream from gateway → SIEM/analytics → Risk Scoring → AI Triage Analyst (LLM) → Quarantine action (red arrow back to the gateway).
- **Far bottom, "Tier 4: Assurance":** Tamper-evident Audit Log, Control Mapping (DORA/SOC 2/OWASP), Kill-Switch panel, and a loop arrow "Usage Analytics → AI Right-sizing Proposal → Red-Team Test → Human Approval → Policy CI/CD → PDP."
- **Legend:** solid arrows = runtime calls; dashed = control/telemetry; red = containment; green = approved policy change.

## 3. Deliverables Execution Blueprint

### 3.1 Deconstructing the ask

| Deliverable | What "good" looks like | Owner (suggested) |
|---|---|---|
| AI Architecture Strategy | 5–7 slides: Straive's approach to heterogeneous stacks (gateway-first, identity-first, policy-as-code, observability-by-default), with the five-tier diagram | Solution architect |
| POV on Entitlement | 6–8 page paper: principles (least agency, default-deny, attenuation, JIT, human accountability), the five tiers, regulatory mapping table, maturity model (Level 0 shared accounts → Level 4 continuous, usage-optimised entitlement) | Architect + risk/compliance SME |
| Talent Profiles | 5–6 anonymised profiles: IAM/zero-trust architect, policy-as-code engineer, agent engineer (LangGraph/Bedrock), data platform security engineer, AI red-teamer, BFSI ops/reconciliation SME; include certifications and BFSI case references | Delivery lead |
| Capability Demo | One unified, scripted, reproducible demo on synthetic data (below) | Demo pod |

### 3.2 Synthetic banking data scenario

- **Firm:** "Kaiyo Securities" (fictional), desks in Tokyo, London and New York.
- **Datasets (all synthetic):** 50k trades (equities, JGBs, FX forwards) with book, trader, counterparty; settlement instructions/SSIs; nostro statements (camt.053-style) with seeded breaks; client master with KYC/PII fields (name, DOB, tax ID, address) tagged `PII`; research notes and deal pipeline tagged `MNPI`, `side=private`; regulatory-report extracts.
- **Agents:** Trade Booking Agent, Settlement Agent, Reconciliation Agent, Client Reporting Agent, Broker ("mother") Agent, Governance Triage Agent, and a Red-Team Agent (Anand).

### 3.3 Demo user journey and script (~12–15 minutes)

| Min | Act | What the audience sees | Key point |
|---|---|---|---|
| 0–1 | Framing | Kaiyo's 12-system landscape with agents bridging gaps, "today: shared service accounts" | Mirrors Nomura's problem without assuming internals |
| 1–3 | **Act 1: Baseline entitlements (Aditi)** | Agent registry: each agent's identity, owner, purpose, allowed systems/tools, data classes; entitlement matrix heatmap; Cedar policy snippet in plain English | Governance starts with an explicit, reviewable baseline |
| 3–4 | Happy path | Booking → Settlement → Recon chain runs; trace view shows each call allowed with policy ID and <5 ms decision time | Governance does not slow STP |
| 4–6 | **Act 2: Dynamic need-to-know (Aryan)** | Recon agent hits a break needing a counterparty SSI outside its domain; Broker agent drafts justification; policy auto-approves a 15-minute token for one record; token TTL counts down; access auto-expires | Flexibility without standing privilege |
| 6–8 | **Act 3a: Prompt-injected recon agent** | A seeded nostro statement narrative field contains an injected instruction to pull client DOB/tax IDs and post them to an external endpoint; gateway denies KYC.PII read (policy P-21), DLP blocks egress, risk score spikes, agent auto-quarantined to read-only | Deterministic layer stops it even though the agent "wanted" to comply |
| 8–9 | **Act 3b: Delegation escalation** | Client Reporting Agent asks Settlement Agent to "fetch the full client file"; token exchange shows attenuation (requested scope > delegator scope → denied), actor chain displayed | Confused deputy neutralised |
| 9–10 | **Act 3c: Information-barrier breach** | Red-team agent attempts to query MNPI research via a shared tool; ReBAC barrier deny; compliance alert with barrier ID | Chinese-wall enforcement by construction |
| 10–12 | **Act 4: Explain and remediate (Anand + Dharmendra)** | Governance Triage Agent produces an incident narrative (who, what, which policy, which control); usage analytics show Recon agent uses 3 of 9 granted scopes; AI drafts a right-sizing policy PR; red-team replays attacks against the proposed policy in shadow; human approver clicks approve; least-privilege score rises | AI optimises, humans authorise |
| 12–13 | Evidence | One-click evidence pack: decision log excerpts mapped to DORA RTS Art. 12/20/21, SOC 2 CC6/CC7, OWASP ASI01/ASI03/ASI07 | Speaks to the CDIO's audit and regulatory audience |
| 13–15 | Path to production | Phased roadmap, integration with Nomura IAM/PAM, open questions | Bridges demo-to-production credibility gap |

### 3.4 Dashboards and metrics that will land with an innovation officer

- **Agent inventory and ownership coverage:** % of agents with unique identity, named owner, current certification.
- **Least-privilege score:** used ÷ granted entitlements per agent, trended over time.
- **Permission drift:** entitlements added outside the policy pipeline (should be zero).
- **Blocked attempts by OWASP category:** ASI01/02/03/07/10 counts with drill-down.
- **Mean time to detect / contain (MTTD/MTTC):** for the seeded attacks (targets: seconds to detect, under one minute to quarantine).
- **JIT elevation stats:** requests, auto-approved vs human-approved, median approval time, standing-privilege hours avoided.
- **Policy decision latency:** p50/p99 per hop, shown alongside STP throughput.
- **False-positive rate:** denied calls later confirmed legitimate (key to operations buy-in).
- **Control coverage heatmap:** DORA RTS articles / SOC 2 criteria / OWASP IDs vs implemented controls, with evidence links.

### 3.5 Build plan (~6 weeks, 5–6 people)

| Week | Workstream outputs |
|---|---|
| 1 | Synthetic data generation; agent and system mocks; registry schema; Cedar/OPA policy model and information-barrier model |
| 2 | Identity (SPIRE/Keycloak), gateway (Envoy + MCP proxy), PDP integration, RLS/CLS views; happy-path chain |
| 3 | Tier 2 JIT elevation with token exchange, attenuation and TTL; human-approval stub in Teams/Slack |
| 4 | Tier 3 telemetry, detections, quarantine automation; red-team agent with the three scenarios |
| 5 | Tier 4 audit log, control mapping, usage analytics, AI right-sizing PR and shadow replay; dashboards |
| 6 | Hardening, scripted run-throughs, failure rehearsal (PDP outage → fail-closed demo), recorded backup video, POV paper and talent profiles finalised |

Team: solution architect (lead), IAM/policy engineer, agent engineer, data/platform engineer, front-end/dashboard developer, and a part-time BFSI ops SME and AI red-teamer. Aryan's data-analyst role fits naturally on synthetic data design and the metrics/dashboard layer.

## 4. Team Input Synthesis and Gap Analysis

### 4.1 Where the team converges and how each idea maps

| Team member | Core input | Where it lands in the architecture | Refinement |
|---|---|---|---|
| Aditi Gupta | One solid demo; baseline entitlements first | Demo Act 1; Tier 0 registry and Tier 1 baseline policy | Adopted as the demo spine |
| Anand Subramanian | Adversarial agent exposes gaps; primary agent iteratively optimises | Tier 3 red-team scenarios; Tier 4 optimisation loop | The optimiser *proposes*; humans approve. Red-team runs continuously in shadow, not against production |
| Dharmendra Singh | Deterministic human-style RBAC with row/column security; AI only for exceptions | Tier 1 PDP + data-layer RLS/CLS; AI in Tier 3 triage | Adopted as the enforcement foundation; extend RBAC with ABAC/ReBAC for agent context |
| Pothuri Sai Eswar | Conservative rule-based classifier first; no LLM-over-LLM | Tier 1 default-deny; LLMs off the inline path | Adopted as a design principle and stated explicitly to the client |
| Aryan Verma | Static rules too rigid; a super/mother agent grants need-to-know cross-domain access | Tier 2 Broker agent and JIT elevation | Mother agent becomes a *recommender and justifier*; grants come from policy + human, as short-lived attenuated tokens |

**Convergence:** all five agree on (a) agent-centric (not human-centric) governance, (b) a strong baseline, and (c) a visible catch-and-fix story. The only real disagreement, who holds grant authority, is resolved by Tier 2's separation of recommend vs grant.

### 4.2 Gap analysis: blind spots to close before presenting

| # | Gap / edge case | Severity | Mitigation |
|---|---|---|---|
| 1 | **Authentication, not just authorisation:** the team discussed permissions but not how an agent proves who it is | Critical | Tier 0 cryptographic workload identity; per-instance IDs; no shared accounts |
| 2 | **Integration with Nomura's IAM/PAM** (likely AD/Entra, SailPoint, CyberArk — unconfirmed) | Critical | Position the framework as an overlay: registry syncs to IGA for certifications; PAM vaults residual secrets; IdP issues agent identities |
| 3 | **Legacy systems without fine-grained APIs** (mainframe, batch file drops, screen-scraping) | High | Enforce at a proxy/data-virtualisation layer or file-drop broker; coarse system-level gating plus compensating monitoring; tier roadmap by system criticality |
| 4 | **Who governs the governor** (Broker/Triage agents and PDP as attack surface) | Critical | Governance agents have no write access to policy; policy changes only via signed CI/CD with human approval; PDP isolated, separately monitored; four-eyes on policy admin |
| 5 | **Prompt injection through business data** (SWIFT/ISO 20022 free text, PDFs, emails) | High | Treat all inbound content as untrusted; injection classifiers; tool-call authorisation independent of model intent; reduce autonomy when untrusted data is in context (a point NIST commenters raised)\[59\] |
| 6 | **Latency impact on STP/T+1** | High | Millisecond PDP budget; async monitoring; pre-approved elevation patterns; measure and publish p99 |
| 7 | **False positives disrupting operations** (blocked recon at 6pm on T+1 eve) | High | Shadow/monitor-only mode before enforce; break-glass with post-hoc review; FP rate as a KPI owned with operations |
| 8 | **Optimisation loop over-tightens or loosens without sign-off** | High | Policy changes are PRs with human approval, shadow replay, regression tests and rollback; rate-limit changes |
| 9 | **Human-in-the-loop design and approval fatigue** | Medium | Risk-tiered approvals; auto-approve low-risk patterns; batch reviews; measure approval latency |
| 10 | **Data residency** (Japan APPI, EU GDPR, US) and LLM endpoints | High | Region-pinned model endpoints; residency attributes in ABAC; PII never in prompts to out-of-region models |
| 11 | **Regulatory explainability** (DORA, FINRA 3110, FSA) | High | Deterministic policy IDs on every decision; control-mapped evidence packs |
| 12 | **Ownership and accountability of agents** | High | Mandatory named owner and sponsor in the registry; orphaned-agent auto-suspension |
| 13 | **Third-party / vendor agents and SaaS tokens** (Drift-style risk) | High | Inventory third-party OAuth grants; short-lived, scoped tokens; DORA third-party register\[60\]\[61\] |
| 14 | **Change management** (developers, ops, desk supervisors) | Medium | Self-service agent onboarding with policy templates; training; phased enforcement |
| 15 | **Cost model** (token cost of AI triage, platform licences) | Medium | AI only off the hot path; small models for classification; show cost per 1k decisions |
| 16 | **Demo-to-production credibility gap** | High | Show failure modes (PDP outage, false positive and override), name integration assumptions, and offer a scoped pilot on 2–3 real agents |
| 17 | **Vendor neutrality** | Medium | Demo on open-source components with documented mappings to Entra/Okta/CyberArk equivalents |
| 18 | **Commercial framing** | Medium | Phased offer (below) |
| 19 | **Model/version change governance** (agent behaviour shifts when the model updates) | Medium | Registry pins model version; re-certification triggered on model change; MAS/FSA lifecycle expectations |
| 20 | **Memory and vector-store contamination across barriers** | High | Per-barrier, per-agent memory stores with ReBAC; no shared embeddings across `side=private/public` |

### 4.3 Recommended commercial framing

- **Phase 0 (now, 6 weeks, Straive-funded or low-cost):** capability demo, POV and talent profiles.
- **Phase 1 (8–10 weeks):** discovery and agent inventory across a defined slice (e.g., settlement and reconciliation), entitlement baseline, risk assessment mapped to DORA/FINRA/FSA.
- **Phase 2 (3–4 months):** pilot gateway, PDP and JIT on 2–3 production agents in monitor-only then enforce mode.
- **Phase 3 (ongoing):** scale across the agent estate; managed red-teaming and policy-optimisation service; quarterly evidence packs.

## 5. Client Engagement and Probing Questions

Ask these in the next Nomura sync, ideally with the CDIO, the IAM/security lead and an operations owner in the room:

1. **Agent inventory and ownership:** "How many agents are in production or pilot today, which teams built them, and is there a named business owner for each? Are they all on Core AI/Bedrock, or are other frameworks and LLM providers in use?"
2. **Authentication today:** "How do agents authenticate to the 160+ systems today: shared service accounts, per-agent service principals, API keys, OAuth clients? Where are those credentials stored, and how often are they rotated?"
3. **IAM/PAM/IGA stack:** "Which identity provider, privileged access and identity governance tools are strategic (e.g., Entra ID, Okta, CyberArk, SailPoint), and is there appetite to extend them to agents rather than add a new platform?"
4. **Interfaces and the hardest systems:** "Which systems do agents touch via APIs, which via database connections, file drops or UI automation, and which 5–10 systems are highest-risk (PII, MNPI, payments/settlement instructions)? Do agents use MCP or agent-to-agent calls today?"
5. **Telemetry and incident handling:** "What do you log about agent actions today, and does it reach your SIEM? Has there been an incident or near-miss involving an agent accessing data it should not have?"
6. **Regulatory drivers and jurisdictions:** "Which regulators are the primary audience (FSA, FINRA/SEC, FCA/PRA, ECB/DORA, MAS), and are there open audit findings on service accounts, access reviews or information barriers? Any data-residency constraints on model endpoints?"
7. **Demo success criteria:** "What would make you say 'yes' after the demo: a specific scenario (e.g., reconciliation agent and client data), latency proof, integration with your IdP, or a control-mapping view for audit? And who else needs to see it?"

## Recommendations

1. **Lead with the principle "AI recommends, policy decides, humans approve, and everything is logged."** It resolves the internal debate and is the message most likely to satisfy Nomura's risk, audit and regulatory stakeholders.
2. **Build the single demo with the five-tier architecture, open-source components and explicit mappings to Entra/Okta/CyberArk**, so Straive is seen as a vendor-neutral architect.
3. **Make DORA RTS Art. 20/21/12 and FINRA's agent expectations the evidence spine** of the POV; they are the most concrete, citable requirements available.
4. **Show failure modes deliberately** (PDP outage → fail-closed; false positive → break-glass), since this closes the demo-to-production credibility gap.
5. **Confirm the sponsor's exact title** and use the probing questions to replace assumptions with facts before Phase 1 is scoped.

## Caveats

- NHI ratio statistics are largely vendor-sourced (Entro, CyberArk, Okta, CSA) with different methodologies; quote ranges, not a single number.
- IETF agent-auth documents are Internet-Drafts and NIST's NCCoE paper is a draft concept paper; neither is a finalised standard.\[62\]
- MAS final-guideline deadlines and some EU AI Act Omnibus implementation details were taken from secondary reporting; verify against primary texts before client use. DORA RTS quotes were checked against consolidated reproductions; verify against the EUR-Lex PDF before publication.
- Peer-bank information reflects public statements and press coverage, not disclosed architectures. No public agent-entitlement architecture was found for Morgan Stanley.
- Latency targets in Section 2.3 are Straive design objectives, not measured benchmarks.
- Nomura's internal stack (IdP, PAM, IGA, agent frameworks) is unconfirmed; references to Entra, CyberArk or SailPoint are hypotheses to test in discovery.

## Sources

1. [FINRA’s 2026 Regulatory Oversight Report: Continued Focus on Generative AI and Emerging Agent-Based Risks](https://www.debevoise.com/insights/publications/2025/12/finras-2026-regulatory-oversight-report-continued)
2. [FINRA Publishes 2026 Regulatory Oversight Report to Empower Member Firm Compliance](https://www.finra.org/media-center/newsreleases/2025/finra-publishes-2026-regulatory-oversight-report-empower-member-firm)
3. [FINRA 2026 Oversight Report: GenAI and AI Agent Expectations](https://www.meilynx.com/reference/finra-2026-oversight-report-genai)
4. [Publication of AI Discussion Paper (Version 1.1) : FSA](https://www.fsa.go.jp/en/news/2026/20260303/aidp.html)
5. [MAS Finalises AI Risk Guidelines for Financial Firms](https://www.leaprate.com/regulation/mas-finalises-ai-risk-guidelines-for-financial-firms/)
6. [MAS Guidelines on Artificial Intelligence Risk Management](https://aigovernance.com/policy/mas-ai-risk-management-guidelines-singapore)
7. [SR 26-2: Model Risk Management Guidance Explained](https://domino.ai/data-science-dictionary/sr-26-2)
8. [Model risk management: What SR 26-2 means for financial institutions](https://www.abrigo.com/blog/model-risk-management-what-sr-26-2-means-for-financial-institutions/)
9. [SR 26-2 Regulates Your Models, Not Your AI Agents: What Banks Need to Know - CIMCON Software](https://cimcon.com/sr-26-2-regulates-your-models-not-your-ai-agents-what-banks-need-to-know/)
10. [Article 21: Access control \[CDR 2024-1774\]](https://advisera.com/cdr-2024-1774/access-control-human-resources/)
11. [Article 20: Identity management \[CDR 2024-1774\]](https://advisera.com/cdr-2024-1774/identity-management/)
12. [Article 12: Logging \[CDR 2024-1774\]](https://advisera.com/cdr-2024-1774/logging/)
13. [Microsoft Agent 365 & Entra Agent ID: A Technical Deep Dive](https://www.candede.com/articles/microsoft-agent-365-and-entra-agent-id/)
14. [Microsoft Entra Agent ID GA: Deep Dive for IT and Security](https://www.bighatgroup.com/blog/entra-agent-id-ga-deep-dive/)
15. [Okta announces new blueprint for the secure agentic enterprise](https://www.okta.com/newsroom/press-releases/showcase-2026/)
16. [Okta announces new innovations to secure AI agents at runtime and automate ongoing agent governance](https://www.okta.com/newsroom/articles/okta-july-2026-product-innovations/)
17. [CyberArk Introduces First Identity Security Solution Purpose-Built to Protect AI Agents with Privilege Controls](https://www.cyberark.com/press/cyberark-introduces-first-identity-security-solution-purpose-built-to-protect-ai-agents-with-privilege-controls/)
18. [NIST AI Agent Standards: What It Means for Enterprise Security](https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-initiative-2026040/)
19. [NIST AI Agent Standards Initiative: What It Means](https://mind-core.com/blogs/nist-ai-agent-standards-initiative/)
20. [MCP Authentication: OAuth 2.1 in MCP Explained](https://www.authgear.com/post/mcp-authentication/)
21. [Diving Into the MCP Authorization Specification](https://www.descope.com/blog/post/mcp-auth-spec)
22. [OWASP Non-Human Identities Top 10 - 2025 - OWASP Non-Human Identities Top 10](https://owasp.org/www-project-non-human-identities-top-10/2025/top-10-2025/)
23. [Lessons from OWASP Top 10 for Agentic Applications](https://auth0.com/blog/owasp-top-10-agentic-applications-lessons/)
24. [T+1 Settlement in Europe: October 2027 Is Closer Than You Think](https://collateralmanagementforum.com/t1-in-europe/)
25. [Streamlinefeed](https://streamlinefeed.co.ke/news/financial-firms-one-year-automate-operations-uk-october-2027-t1-settlement-deadline)
26. [About T+1 settlement](https://www.fca.org.uk/markets/about-t1-settlement)
27. [Cybersecurity Alert](https://www.finra.org/rules-guidance/guidance/salesloft-drift-AI-supply-chain-attack)
28. [Salesloft Drift Supply Chain Attack Exposes Data of Hundreds of Organizations via Compromised OAuth Tokens](https://mallory.ai/stories/43ce3e37-2fbe-49fb-807b-5055553582e7)
29. [MCP server authentication in 2026: what practitioners need to know](https://nhimg.org/articles/mcp-server-authentication-in-2026-what-practitioners-need-to-know/)
30. [Digital Operational Resilience Act (DORA), Article 9](https://www.digital-operational-resilience-act.com/Article_9.html)
31. [Artificial Intelligence: Council and Parliament agree to simplify and streamline rules - Consilium](https://www.consilium.europa.eu/en/press/press-releases/2026/05/07/artificial-intelligence-council-and-parliament-agree-to-simplify-and-streamline-rules/)
32. [EU AI Act omnibus: the new high-risk deadlines explained](https://verifywise.ai/blog/eu-ai-act-omnibus-what-changed)
33. [SR 26-2 model risk management: What changed for banks](https://www.cicrim.com/insights/sr-26-2-model-risk-management.html)
34. [What FINRA's 2026 Oversight Report Means for AI and Recordkeeping](https://archiveintel.com/blog/finra-2026-ai-recordkeeping)
35. [Japan Financial Services Agency: Publication Of AI Discussion Paper](https://mondovisione.com/media-and-resources/news/japan-financial-services-agency-publication-of-ai-discussion-paper-2025410/)
36. [How Is Japan's Banking and Financial Services Landscape Evolving With AI, and What Challenges Must Be Overcome?](https://fptsoftware.com/resource-center/blogs/banking-and-financial-services-landscape-in-japan-current-ai-applications-and-challenges-to-overcome)
37. [Financial Services Regulation 2025 - Japan](https://practiceguides.chambers.com/practice-guides/financial-services-regulation-2025/japan/trends-and-developments)
38. [Consultation Paper on Guidelines on Artificial Intelligence Risk Management (AIRG)](https://www.aigl.blog/consultation-paper-on-guidelines-on-artificial-intelligence-risk-management-airg/)
39. [Compliant with Local Controls, Collectively Discriminatory. A Governance Architecture for Multi-Agent AI in Regulated Finance](https://arxiv.org/pdf/2609.27994)
40. [T+1 Accelerated Settlement - Operations - Operations - PIMFA](https://operations.sites.pimfa.uk/t-1/)
41. [T+1 settlement cycle in the UK, EU & Switzerland](https://www.business.hsbc.com/en-gb/financial-regulations/tplus1-settlement-cycle/uk-eu-switzerland)
42. [NIST AI Agent Authorization: Five Asks Mapped to Kubernetes - ARMO](https://www.armosec.io/blog/nist-ai-agent-identity-authorization/)
43. [OWASP Top 10 for Agentic Applications 2026](https://cycode.com/blog/owasp-top-10-agentic-applications/)
44. [OWASP Non-Human Identities Top 10](https://owasp.org/www-project-non-human-identities-top-10/2025/)
45. [Introduction - OWASP Non-Human Identities Top 10](https://owasp.org/www-project-non-human-identities-top-10/2025/introduction/)
46. [AI Agent Authentication and Authorization](https://www.ietf.org/archive/id/draft-klrc-aiagent-auth-00.html)
47. [OAuth Profile for Delegated AI Agent Authorization](https://www.ietf.org/archive/id/draft-mishra-oauth-agent-grants-02.html)
48. [OAuth 2.0 Extension: On-Behalf-Of User Authorization for AI Agents](https://www.ietf.org/archive/id/draft-oauth-ai-agents-on-behalf-of-user-01.html)
49. [draft-mcguinness-oauth-ai-agent-instance-00](https://datatracker.ietf.org/doc/html/draft-mcguinness-oauth-ai-agent-instance-00)
50. [MCP OAuth: How MCP Authentication Works (2026) — Scalar](https://scalar.com/learn/mcp/mcp-oauth)
51. [Agent2Agent (A2A): Spec v1.0, Linux Foundation](https://agenticcommerceprotocol.info/standards/a2a)
52. [A2A Joins MCP at the Agentic AI Foundation](https://blog.pebblous.ai/blog/a2a-mcp-agentic-ai-foundation-authorization/en/)
53. [Specification - Agent2Agent Protocol (A2A)](https://a2a-protocol.org/v0.2.5/specification/)
54. [A2A security: The developer's complete guide](https://tyk.io/learning-center/a2a-security-the-developers-complete-guide/)
55. [Secure Agent Access with Microsoft Entra](https://www.microsoft.com/en-us/security/business/identity-access/microsoft-entra-agent-id)
56. [Okta launches platform to secure AI agents - Techzine Global](https://www.techzine.eu/news/security/139633/okta-launches-platform-to-secure-ai-agents/)
57. [Microsoft Entra Agent ID Is the Best Agent Identity System That Only Works Inside Microsoft](https://aethyrresearch.com/blog/microsoft-entra-agent-id)
58. [© 2024, Amazon Web Services, Inc. or its affiliates. All rights reserved.](https://pages.awscloud.com/rs/112-TZM-766/images/CUS-22_AWS-Summit-2024_Nomura%20Holdings.pdf)
59. [Summary of Comments on the Concept Paper — NCCoE Agentic AI Identity and Authorization Project Resource Hub documentation](https://pages.nist.gov/nccoe-ai-identity/summary-of-comments.html)
60. [The Salesloft Drift breach: A cross-vendor attack](https://www.silverfort.com/blog/the-salesloft-drift-breach-a-cross-vendor-lateral-movement-attack-that-requires-a-new-shared-security-model/)
61. [Salesloft Drift token misuse exposes Salesforce NHI governance gaps](https://nhimg.org/articles/salesloft-drift-token-misuse-exposes-salesforce-nhi-governance-gaps/)
62. [NIST's AI Agent Standards Initiative, Explained — CASRAI](https://casrai.org/guides/nist-ai-agent-standards-initiative)
