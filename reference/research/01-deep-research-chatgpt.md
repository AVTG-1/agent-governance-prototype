# Governing AI-Agent Entitlements at Nomura: Deep Research for a Capability Response

## Executive summary

**What Nomura is really trying to achieve.** Based on the discovery notes, Nomura is not primarily asking for another AI-agent framework, IAM product, or model-governance process. It is trying to turn a growing, heterogeneous population of machine actors into a **governable production workforce**: every agent should have a knowable identity, an accountable owner and purpose, an explicitly bounded mandate, independently enforced access to systems and data, traceable delegation to other agents, and controls capable of stopping an impermissible action **before** it reaches a trade, settlement, reconciliation, reference-data, or client-data system. The client-stated facts—160+ heterogeneous systems, production agents bridging systems that do not natively interoperate, and no common agent-entitlement layer—make this principally an **identity, authorization, runtime-control and operational-resilience problem**, with AI-specific complications, rather than a conventional “AI governance” problem.

That interpretation is unusually well aligned with Nomura's public direction. As of August 2026, Ayumi Kato's verified public title is **Co-Chief Data Officer and Head of the Chief Data Office, Nomura Holdings**. Nomura describes the Chief Data Office as responsible for creating an environment in which data and AI can be used safely and effectively; Kato says it has grown from roughly 10 people into a global organization of nearly 100, reviews AI proposals for legal, ethical and cybersecurity concerns, and has deployed more than 80 AI solutions in Japan and more than 200 globally. She has led the establishment of Nomura's AI-governance framework since 2024. citeturn17view1 Nomura's current AI-governance role descriptions additionally call the CDO the **central authority** for data, cloud and AI governance across business and corporate functions. citeturn17view3 The internal note “Chief Data Innovation Officer” therefore appears imprecise: the closest verified role is **Co-Chief Data Officer / Head of the Chief Data Office at Nomura Holdings**. Public evidence does **not**, however, establish that Kato herself was the discovery-meeting sponsor, so that identity should not be assumed.

Nomura is already materially invested in AI and cloud. Its public AI Governance Policy describes a centralized group-wide operating framework; its 2026 reporting describes an AI & Data Strategy Department driving cross-functional initiatives. citeturn16search0turn16search4 AWS says Nomura uses Amazon Bedrock and a “core AI” platform, including automated compliance review, and quotes a Nomura enterprise architect describing AWS as the firm's primary cloud provider. citeturn17view4 Public evidence also shows use of Google Cloud for initiatives such as FINTOS and describes hybrid cloud as part of group-wide technology infrastructure, so the correct architectural presumption is **heterogeneous and multi-environment, not AWS-only**. citeturn2search2turn0search18

The regulatory direction strengthens the case for a runtime control plane without, in most jurisdictions, prescribing one specific implementation. FINRA's 2026 guidance explicitly says existing technology-neutral supervision, recordkeeping, communications and other requirements apply to GenAI, and calls out the potentially novel supervisory and operational issues created by autonomous agents. citeturn18search0 The FCA says it does not currently intend a separate AI rulebook and instead relies on existing accountability and governance frameworks, including the Senior Managers and Certification Regime. citeturn18search5 EU DORA and its technical standards are more concrete on ICT identity and access management, including documented identity-management and access-right controls. citeturn16search3turn16search15 Singapore is furthest ahead in articulating the agent-specific control pattern: MAS's final AI Risk Management Guidelines, issued **7 October 2026**, require proportionate AI inventory, risk assessment, oversight and lifecycle controls; its separate SAFR industry framework proposes agent identity, explicit mandates, pre-execution authorization, deny/escalate/observe/auto-execute dispositions and tamper-evident logging. citeturn18search2turn19view0turn19view1turn18search7 Importantly, MAS expressly says SAFR is an industry framework rather than itself a statement of regulatory requirements. citeturn18search3turn18search13

**A credible response should therefore avoid pretending the architecture is already known.** It should demonstrate a method for discovering the estate and choosing enforcement points, then show that the same policy model can work through more than one integration pattern. A compelling capability demonstration would include one “existing/opaque” agent that cannot be rewritten and one natively governable agent; several synthetic capital-markets systems exposed through different interfaces; a registry binding agents to owners, purposes and identities; deterministic externalized authorization; data/tool/action-level controls; delegation provenance; observe-only deployment followed by enforcement; evidence-based permission right-sizing; and an adversarial scenario stopped before an irreversible action. This approach follows the direction publicly articulated by JPMorgan Chase—that agent security must establish authorization boundaries, constraints, runtime evidence and auditable records at the point of execution—and MAS SAFR's action-level model. citeturn17view6turn19view4

The strongest point of view on **“optimized” permissions** is not that an LLM should continuously rewrite production entitlements. The evidence supports a layered approach in which optimization can be adaptive but execution remains bounded by deterministic hard controls. Static/RBAC, ABAC, relationship-based authorization and policy-as-code are mature; just-in-time privilege and usage-based right-sizing are mature in adjacent IAM/cloud contexts; ML recommendations have meaningful production precedent; LLM-generated or semantic authorization is useful but still comparatively young; and multi-agent delegation protocols remain unsettled. Google, for example, uses actual permission usage plus ML in IAM Recommender, while AWS Access Analyzer can generate or reduce permissions from observed activity. citeturn9search3turn9search15turn9search2 AWS now offers natural-language policy authoring for AgentCore, but its actual authorization policies are represented in an analyzable deterministic policy language. citeturn21search0turn21search11 For a regulated post-trade environment, that distinction is important.

Finally, there is a meaningful services opportunity even though many building blocks are rapidly becoming products. Microsoft, Google, AWS, Okta, SailPoint, CyberArk and others now sell agent identity, inventory, gateways, policy and governance capabilities. citeturn20search0turn21search5turn21search0turn20search1turn20search10turn20search35 What remains hard is **not** minting an agent ID or evaluating an allow/deny rule. It is discovering agents embedded in a messy legacy estate; proving which logical agent is behind an action; converting trading and operations mandates into enforceable machine policy; preserving authority correctly through agent chains; introducing enforcement without breaking critical processing; distinguishing anomalous from legitimate rare behavior; optimizing least privilege without causing an outage; and producing defensible evidence across jurisdictions. Those are exactly the areas a services firm should demonstrate.

## Nomura, its regulatory perimeter, and the control problem

**Research question — Nomura itself**

### What is verified publicly

Nomura's public operating model is already substantially more mature than “an organization experimenting with AI.” In August 2026, Co-Chief Data Officer Ayumi Kato said the Chief Data Office's mission is to enable safe and effective use of data and AI, that the predecessor Data Management Office began around 2014, and that the organization has expanded globally to nearly 100 staff across locations including New York, London, Singapore and India. She described a review process examining ethics, legal soundness and cybersecurity before AI use cases are approved, and stated that Nomura has deployed **80+ AI solutions in Japan and 200+ globally**. citeturn17view1

Nomura's public AI-governance material says it has an **Artificial Intelligence Governance Policy and centralized group-wide operating framework**. citeturn16search4turn16search7 A current AI-governance vacancy describes the Chief Data Office as the central authority defining and overseeing data, cloud and AI governance, and specifically seeks capabilities around automated testing, continuous monitoring, model failure rates, human-intervention frequency, tool-use success, cross-agent conflict detection and guardrail violations. citeturn17view3 That vacancy is particularly relevant because it suggests Nomura is already moving beyond model governance into **operational effectiveness and multi-agent monitoring**.

Nomura's 2026 organizational reporting also identifies an **AI & Data Strategy Department**, while public organizational material includes the Chief Data Office, IT Strategy, CIO functions and Cyber Security. citeturn16search0turn15search1turn15search4 The precise division of responsibilities among the CDO, AI & Data Strategy Department, CIO/security functions and individual businesses is not disclosed publicly and is therefore a key discovery topic.

On infrastructure, AWS states that Nomura uses Amazon Bedrock, Llama-family models and a “core AI” generative-AI platform, and describes AWS as Nomura's **primary cloud provider** in a customer case study. AWS also says it worked with Nomura's Generative AI Innovation Center on compliance and advertising-review automation. citeturn17view4 Nomura has also publicly worked with Google Cloud on FINTOS, while corporate material has referred to group-wide technologies including AI, automation and **hybrid cloud**. citeturn2search2turn0search18 The safe conclusion is that the estate is heterogeneous and probably contains substantial on-premises and multiple-cloud technology; the discovery-meeting statement that there are 160+ systems is client-supplied and has not been independently verified.

The public leadership title most closely matching “Chief Data Innovation Officer” is therefore:

> **Ayumi Kato — Co-Chief Data Officer, Head of the Chief Data Office, Nomura Holdings.**

That title and organization are verified. citeturn17view1 **It remains unverified whether Kato was the individual sponsor in the discovery meeting.**

### What the regulatory perimeter implies

Nomura's own legal notices identify Nomura Holdings as regulated by the Japanese FSA as an ultimate designated parent company and Nomura Securities Co. as JFSA-regulated. They identify Nomura International plc as PRA-authorized and FCA/PRA-regulated in the UK and registered with the CFTC as a swap dealer; Nomura Financial Products Europe GmbH is supervised by BaFin; Nomura International Hong Kong by the SFC; Nomura Singapore by MAS; and additional entities operate under regulators including ASIC, DFSA, OJK and Asian securities authorities. citeturn17view5 Nomura Securities International is a US broker-dealer subject to SEC/FINRA regulation. citeturn5search1

| Jurisdiction / key supervisor | Current AI-agent/access-control direction relevant to the problem | Implication for Nomura |
|---|---|---|
| **Japan — JFSA** | JFSA updated its AI Discussion Paper to version 1.1 on **3 March 2026** and is simultaneously increasing work on AI-related cyber threats. The original paper expressly described itself as discussion material rather than a list of supervisory expectations; JFSA's broader cyber program now includes cybersecurity guidelines and 2026 work on threats posed by frontier AI. citeturn16search5turn16search8turn16search2 | No public JFSA rule identified here dictates a special “AI-agent identity” protocol. Existing governance, IT/cybersecurity, operational-resilience and accountability expectations remain the foundation. |
| **United States — SEC / FINRA; CFTC where applicable** | FINRA's 2026 oversight report states that its rules and securities laws remain technology-neutral and explicitly discusses AI agents. It highlights supervision, testing, prompt/output monitoring and records, and says autonomy can create novel supervisory and operational considerations. citeturn18search0 | A broker-dealer cannot treat an autonomous agent as outside its normal supervisory perimeter. Identity, action attribution, retained evidence and pre-/post-action controls are consequently important even without an “NHI rule.” |
| **United Kingdom — FCA / PRA** | FCA's position, updated **2 October 2026**, is to use existing outcome-focused rules rather than introduce additional AI-specific regulations; it explicitly points to senior-manager accountability. Its CEO's June 2026 speech addresses GenAI and agentic AI as a live financial-services issue. citeturn18search5turn18search1 | Governance should preserve named managerial accountability and operational resilience regardless of whether decisions are executed by people or agents. |
| **EU / EEA — BaFin and other competent authorities, plus DORA** | DORA requires documented, continuously improved ICT-risk controls. Its detailed technical rules address identity and access management and control of access rights. citeturn16search3turn16search15 The EU AI Act separately imposes governance, logging, robustness and cybersecurity requirements where a system falls into an applicable high-risk category; generic post-trade automation should **not** automatically be assumed high-risk under the AI Act. citeturn4search14 | For agent entitlements, DORA is generally the more direct baseline than assuming the AI Act governs every agent. Entity, use-case and role classification are needed. |
| **Singapore — MAS** | MAS issued final AI Risk Management Guidelines on **7 October 2026**. They require proportional governance, an adequate AI inventory and materiality assessment, lifecycle controls, defined board/senior-management responsibilities and incident/escalation processes. citeturn18search2turn19view0turn19view1turn19view2 MAS's SAFR paper additionally proposes runtime identity, mandate checks, action-by-action authorization, dispositions and tamper-evident audit. citeturn18search7turn19view4 | Singapore provides the clearest public articulation of the control pattern Nomura is asking about, although SAFR itself is explicitly an industry framework, not binding supervisory guidance. |
| **Hong Kong, Australia, Dubai, India, Indonesia, Korea and others** | Nomura publicly identifies regulated entities under SFC, ASIC, DFSA, SEBI and other local authorities. citeturn17view5 Comparable agent-specific runtime-entitlement rules were not established from the primary sources reviewed for this report. | The architecture should produce a common evidence base while allowing jurisdiction- and entity-specific policy overlays rather than hard-coding one jurisdiction's model. |

A particularly important recent development is MAS SAFR. It starts from the observation that financial agents can initiate payments, trading orders and other consequential actions and argues that existing control models developed for human decision-making are not always suited to machine-speed autonomous execution. citeturn19view3 Its proposed disposition model distinguishes **deny, escalate, auto-execute and observe**; calibration factors include reversibility, financial materiality, customer impact, regulatory sensitivity and anomaly. It also calls for an independent, tamper-evident audit record. citeturn19view4 This is not a blueprint Nomura must adopt, but it is unusually strong evidence that the requested capability is aligned with an emerging financial-industry control model.

### Relevant incidents and control history

The most obviously relevant public Nomura control event is **Archegos**, not because AI was involved—it was not—but because it illustrates why a global investment bank will scrutinize claims about pre-emptive controls and risk visibility. Nomura reported roughly $2.9 billion of losses from Archegos; UK regulators subsequently imposed additional capital requirements on Nomura International, which were lifted in 2024 after remediation that reportedly included strengthened risk monitoring and governance. citeturn5news27 It would be misleading to present this as an AI-agent incident. Its relevance is cultural and supervisory: a buyer in this environment is likely to prefer controls that produce **independent evidence before and during execution**, rather than reliance on post-event monitoring alone.

No verified public evidence reviewed for this report establishes an AI-agent-related incident at Nomura. That absence should not be interpreted as proof that no such event has occurred internally.

### First-principles inference from the discovery facts

The client-stated architecture creates four distinct risks that conventional “AI model governance” does not solve:

1. **Authority fragmentation.** If each agent receives whatever service account, API key or application privilege happens to make an integration work, the resulting authority is defined by implementation accident rather than business mandate.
2. **Attribution failure.** If multiple logical agents share identities or secrets, downstream systems may know that “an application” changed a record without knowing which agent, task, upstream principal or delegated objective caused it.
3. **Transitive privilege.** An agent with narrow rights may call another agent with broader rights, unintentionally converting a low-privilege request into a high-privilege action.
4. **Execution-before-detection.** Monitoring after an API call or database update may be too late for settlements, reference-data changes, client-data exposure or trade processing.

Those are reasons to treat Nomura's requirement as a **machine authorization architecture spanning identity, policy, enforcement and evidence**, rather than merely a dashboard over agent telemetry.

## Entitlement state of the art and permission optimization

**Research question — state of the art in governing AI-agent entitlements**

The crucial distinction in 2026 is between **mature security primitives being applied to agents** and genuinely new agent-specific mechanisms.

### What is mature enough to build around

**OAuth/OIDC and workload authentication.** OAuth-based authorization, short-lived credentials, audience-restricted tokens and workload identity are established patterns. MCP's current authorization specification deliberately uses OAuth 2.1: a protected MCP server is a resource server, the client acts as an OAuth client and authorization servers issue access tokens. It explicitly warns servers not to accept tokens intended for a different resource. citeturn22search0turn22search3

**Workload identity.** SPIFFE/SPIRE provide strongly attested cryptographic identities across heterogeneous infrastructure and are mature CNCF projects rather than agent-specific inventions. citeturn21search2turn21search6 An enterprise does not necessarily need a novel identity protocol merely because the workload contains an LLM.

**Externalized policy enforcement.** Open Policy Agent is a CNCF graduated project and can be inserted through Envoy's external-authorization filter, giving a policy decision service request context before traffic reaches an application. citeturn21search25turn21search7 This PDP/PEP pattern is particularly valuable when the business wants policy independent of whichever agent framework happens to be in use.

**RBAC, ABAC and relationship-based authorization.** These are mature authorization families. Google's Zanzibar paper is important evidence for relationship-based authorization at hyperscale: it underpins access-control systems across major Google services. citeturn9search0 None is inherently “AI-native,” which is a virtue: the business can express agent purpose, system, data classification, counterparty, legal entity, transaction type or owner as authorization facts without making the model itself the source of authority.

**Policy-as-code and analyzable authorization languages.** AWS Verified Permissions and Cedar exemplify deterministic, machine-evaluable authorization with policy analysis, while current Bedrock AgentCore Policy uses Cedar-family semantics to govern agent actions. citeturn9search25turn9search1turn21search11

### What is new but increasingly productized

Agent-specific identity and governance products have appeared rapidly in 2025–26:

| Product / ecosystem | Publicly documented capability as of October 2026 | Maturity interpretation |
|---|---|---|
| **Microsoft Entra Agent ID** | Purpose-built agent identity constructs for authentication, authorization and governance; Microsoft recommends agent identities rather than ordinary service principals for most AI agents. citeturn20search0turn20search8 | Productized, but agent-specific operating history is short. |
| **Google Gemini Enterprise Agent Platform** | Agent Identity, Registry and Agent Gateway; agent identity is workload-bound and the gateway enforces runtime controls for agent-to-tool and agent-to-agent traffic. Existing agent workloads can be assigned identities. citeturn21search12turn21search15turn21search30 | Strong integrated cloud pattern; still platform-specific and young. |
| **AWS Bedrock AgentCore** | Gateway plus Cedar-based policy evaluation; supports explicit agent/tool authorization and natural-language policy authoring. citeturn21search0turn21search4 | Strong cloud-native capability; should not be confused with a cross-estate entitlement architecture by itself. |
| **Okta** | AI-agent identity, token exchange, agent-to-agent flows and resource-access certification; certifications reached GA during 2026. citeturn20search1turn20search9turn20search21 | Extends established IGA/IAM into agents; still evolving quickly. |
| **SailPoint Agent Identity Security** | Discovery/aggregation, ownership and governance of agent identities alongside human and application identities. citeturn20search10turn20search22 | Strong IGA extension; runtime enforcement depends on integrations. |
| **CyberArk / Idira Secure AI Agents** | Registration, agent identity and a proxy/Identity Broker that can sit between agent and tools as a tracking/enforcement point. citeturn20search35turn20search7 | Natural extension of PAM/machine-identity security; agent features are newer than core PAM. |

Two protocol families deserve special treatment.

**MCP is becoming an interoperability layer, not a complete authorization model.** Its OAuth 2.1-based transport authorization is meaningful, but it does not by itself answer “is this settlement agent allowed to change this SSI for this counterparty under this task?” Tool- and parameter-level business authorization still needs policy above or alongside transport authentication. citeturn22search0turn22search9

**A2A is becoming a practical agent-interoperability protocol**, and version 1.0 has moved toward stable, enterprise-focused specification under Linux Foundation governance. citeturn7search2turn7search5 Yet agent-to-agent communication protocol maturity should not be mistaken for solved multi-hop authorization.

OpenID AuthZEN is notable because **Authorization API 1.0 became a Final Specification in January 2026**, standardizing interaction between policy enforcement and decision points. Agent/MCP-specific COAZ work is newer and remains under active development. citeturn22search5turn22search11 IETF work on AI-agent authentication, on-behalf-of delegation and attenuated authorization is also active, but much of it remains at Internet-Draft stage and therefore should not be sold as settled standards. citeturn22search1turn22search10turn6search16

### What banks and financial firms are actually doing

The strongest public evidence supports **bounded agents plus existing enterprise controls**, rather than completely autonomous machine principals with unconstrained privileges.

JPMorgan Chase's March 2026 security position argues for clear authorization boundaries, constrained service interaction, auditable automated workflows, runtime governance and machine-to-machine authentication; it explicitly warns that one compromised agent can propagate risk across environments. citeturn17view6 This is a bank-authored architectural position, not a disclosure of every implementation detail.

Deutsche Bank publicly announced an agentic Source-of-Wealth/KYC application in Singapore and Hong Kong in September 2026 and emphasized governance, controls and human oversight. citeturn8search0 Goldman Sachs and Anthropic were reported in February 2026 to be developing agents for areas including trade and transaction accounting and onboarding, but the work was described as early-stage. citeturn8news41 Wells Fargo has been publicly named by Google as an early adopter of an enterprise agent platform; because this is a vendor-hosted customer reference, it is evidence of adoption but not independent evidence of control effectiveness. citeturn8search11

MAS SAFR includes concrete industry reference patterns. Its examples describe Visa registering agents and validating consumer mandates at transaction time, Circle coupling an agent identity with transaction caps and per-action checking, and OCBC/Bank of Singapore using narrow scopes, predefined triggers and human review in a wealth-management workflow. citeturn19view5turn13view1 These should be treated as **industry examples documented by MAS**, not proof that one standardized architecture has won.

**Bottom line on maturity:** identity, OAuth, workload credentials, gateways, policy engines, least privilege, JIT privilege, logging and access review are mature foundations. Agent registries, first-class agent identities and agent gateways are becoming standard product features. Parameter-level MCP authorization, semantic policy, verifiable multi-agent delegation and adaptive autonomous entitlements are still emerging.

**Research question — “optimized” permissions**

“Optimized” should be explicitly defined as a multi-objective problem:

> **minimize unnecessary authority and standing privilege while preserving legitimate task completion, availability, predictable latency, operational resilience and auditability.**

A permission set that is smallest but breaks month-end reconciliation is not optimal. A permission set that maximizes STP but lets an agent read every client record is not optimal either.

| Approach | Reliability / security | Latency and cost | Auditability / regulatory posture | Evidence and limitations |
|---|---|---|---|---|
| **Static ACL / RBAC** | Deterministic and predictable; good for stable functions, but roles can become broad and accumulate privilege. | Very low runtime complexity; significant administrative role-engineering cost at scale. | Excellent explainability. Conventional regulators understand it. | Mature foundation, but poorly suited alone to highly contextual or ephemeral agents. |
| **Rule-based ABAC** | Can evaluate agent identity, system, action, data class, legal entity, environment, task and risk context. Strong least-privilege potential if attributes are trustworthy. | Policy lookup and attribute retrieval add runtime dependencies; usually manageable when PDPs/caches are engineered locally. | Deterministic decisions are highly auditable; policy complexity can become the principal governance risk. | OPA and modern cloud IAM demonstrate mature context-aware policy patterns. citeturn21search28turn9search27 |
| **Relationship-based authorization** | Excellent where rights depend on graph relationships—agent→owner, owner→desk, desk→account, agent→approved tool. Can avoid role explosion. | Requires a consistently available authorization graph; large-scale feasibility is well established. | Decision provenance can be explicit, though relationship lifecycle itself must be governed. | Google's Zanzibar provides real hyperscale evidence, albeit not specifically for AI agents. citeturn9search0 |
| **Just-in-time / ephemeral privilege** | Reduces standing credentials and blast radius; particularly useful for exceptional high-risk tasks. Security depends on the grant decision and revocation path. | Credential issuance/token exchange can add latency and creates control-plane availability requirements. | Strong if every grant has reason, owner, expiry and task linkage. | Mature in PAM/workload-access practice; agent-specific integrations are now appearing in identity products. citeturn20search3turn20search21 |
| **Usage-driven right-sizing** | Removes privileges that telemetry shows are unused. Strong against privilege accumulation, but cannot infer that an unobserved disaster-recovery, quarter-end or rare exception permission is unnecessary. | Analysis happens off-path, so runtime latency is unaffected. Cost is telemetry retention and analysis. | Highly explainable when recommendation cites observed actions and a review window. | AWS IAM Access Analyzer can generate policies from observed access; Google similarly bases recommendations partly on usage. citeturn9search2turn9search5 |
| **ML-driven recommendations** | Can predict likely future permission needs and prioritize risky excess privileges; errors can remove a legitimate rare entitlement or retain an unnecessary one. | Usually offline/advisory, making latency low; needs sufficient history and retraining/monitoring. | Acceptable as decision support if a deterministic policy and accountable approval remain the enforcement authority. Harder to defend if the model directly grants privilege. | Google states IAM Recommender uses ML and a 90-day usage horizon, including predictions about likely future permission use. citeturn9search3turn9search15 |
| **LLM-assisted policy authoring** | Useful for turning natural-language business intent into candidate policies; vulnerable to ambiguity and generation errors if trusted directly. | Adds inference cost at authoring time rather than necessarily on every transaction. | Good when generated policy is compiled, tested, analyzed and human-approved; poor if natural language itself is treated as unquestioned authority. | AWS AgentCore can author from plain English while enforcing through formal policy. citeturn21search0turn21search11 |
| **LLM/semantic runtime authorization** | Can reason about intent that static rules cannot express, but decisions are probabilistic and adversarially exposed. | Inference on the critical path raises latency, cost and availability questions. | Evidence for regulator-grade autonomous authorization remains thin. It is more credible as an additional risk signal than as the sole arbiter of a consequential trade/settlement action. | Current products are beginning to expose semantic policy, but long-duration independent production evidence is not yet available. |
| **Hybrid deterministic + adaptive** | Hard policy sets non-negotiable boundaries; analytics/ML recommend right-sizing or change risk; contextual rules choose execute/escalate/observe; humans approve exceptional changes. | More components and engineering complexity, but adaptation can remain off critical path while deterministic authorization stays fast. | Strongest combination of explainability and adaptability if change governance is preserved. | Closely resembles MAS SAFR's risk-calibrated disposition model. citeturn19view4 |

The evidence therefore supports **permission optimization as a governed feedback loop**, not “the AI edits its own privileges”:

**observe → infer candidate least privilege → simulate/back-test → evaluate rare scenarios → approve → version policy → enforce → monitor → roll back if necessary.**

The right demo should deliberately show a permission *recommendation* becoming narrower because observed activity no longer justifies an entitlement, while also showing why the optimization engine is not allowed to remove a rare but mandated quarter-end or exception-handling permission solely because it did not appear in the recent telemetry.

## Governing opaque agents and agent-to-agent chains

**Research question — governing agents you cannot see inside**

The requirement is feasible without rewriting every agent, but only where Nomura can establish **a trustworthy enforcement point somewhere between the agent and the consequential resource**. The internal model, framework and prompt structure can remain unknown.

### Discovery must precede control

The first task is not “give every agent an identity”; it is determining what constitutes an agent and what it touches. A practical discovery process would correlate:

**deployment evidence** such as cloud workloads, containers, virtual machines and job schedulers; **credential evidence** such as service accounts, OAuth clients, API keys, vault check-outs and certificates; **communication evidence** such as API-gateway, proxy, DNS, network-flow, message-bus and database-session logs; and **application evidence** such as tool calls and downstream transaction logs.

Each discovered actor should be mapped to at least: owner, business purpose, hosting location, logical agent, execution runtime, credentials, upstream caller, downstream systems/tools, data classes, read/write capabilities, delegation relationships, legal entity and criticality.

MAS's final 2026 guidelines now explicitly expect financial institutions to maintain adequate AI inventories and risk-materiality assessments. citeturn19view0turn19view2 The discovery phase therefore has regulatory value independently of the eventual architecture.

### Enforcement can be inserted at several layers

| Control point | What can be governed without changing the agent | Principal limitation |
|---|---|---|
| **Network / service-mesh egress** | Workload identity, destination, network protocol, selected L7 request context; block connections to unapproved systems. OPA/Envoy and service-mesh patterns support external authorization before traffic reaches the target. citeturn21search7turn21search3 | Cannot always understand the business meaning of a request; encrypted/proprietary protocols may restrict inspection. |
| **API / agent gateway** | Agent identity, endpoint/tool, HTTP method, parameters, OAuth token, user/delegation context, DLP/content controls. | Requires traffic to be routed through the gateway and APIs to expose enough context. |
| **MCP gateway/server** | Tool discovery and invocation, OAuth identity, fine-grained tool authorization. | Legacy applications that are not exposed through MCP need adapters; MCP transport auth is not sufficient business authorization. citeturn22search0turn22search5 |
| **Credential broker / PAM** | Prevent the agent from seeing raw secrets; mint short-lived credentials only when policy permits. | Downstream system may still see the brokered account rather than the full logical-agent chain unless metadata is preserved. |
| **Data layer / database proxy** | Schema/table/row/column/query controls, client-data classification, read versus write. | Does not govern actions outside that data service. |
| **Message bus / file-transfer layer** | Topic/queue/file permissions and message provenance. | Can miss semantic misuse inside an allowed message. |
| **Legacy UI / RPA boundary** | Session isolation, desktop/bastion controls, privileged credential brokering and downstream transaction monitoring. | Hardest case: human-like GUI automation offers fewer natural policy hooks and may require network or application-side controls. |

Google's current Agent Gateway is useful evidence that the pattern can be applied to pre-existing workloads: its documentation says every governed agent needs a unique workload-bound SPIFFE identity and that an identity can be assigned to an existing agent workload; unidentified traffic is blocked by default when the gateway is enforcing identity-based policy. citeturn21search30 CyberArk likewise documents a proxy-like Identity Broker between an agent and its tools. citeturn20search35 These are vendor implementations of a generic architectural principle, not reasons to choose either product in advance.

A critical caveat is **identity granularity**. Wrapping a Kubernetes pod in a SPIFFE identity proves which workload sent traffic. It does **not** prove which logical agent acted if five agents run inside one process and share that workload identity. Nomura therefore needs a hierarchy such as:

`runtime identity → logical agent identity → invoking principal/agent → task/mandate → action`.

Where a legacy agent cannot emit the finer-grained fields, the architecture may initially be able to guarantee only workload-level attribution. That limitation should be visible rather than concealed.

### Observe-only rollout is essential

A realistic brownfield sequence is:

**inventory → passive observation → identity association → shadow policy decisions → compare decisions with actual operations → narrow pilot enforcement → broader enforcement → right-sizing.**

During shadow mode, the policy engine evaluates “would allow / would deny / would escalate” without blocking the transaction. That creates the evidence needed to find missing dependencies, exceptional month-end behavior and false positives before a control can disrupt production. MAS SAFR's explicit **Observe** outcome provides a useful financial-sector analogue. citeturn19view4

The architectural rule is simple: **an opaque agent can be governed externally only to the extent that its consequential actions can be made to traverse an enforceable boundary.** An agent with unrestricted direct database credentials and an unrestricted network route that bypasses the control plane cannot be made governable by a dashboard.

**Research question — agent-to-agent risk**

Agent chains create a deeper problem than normal service-to-service authentication because there are potentially three distinct concepts on every call:

- **the agent that physically made the call;**
- **the principal or upstream agent on whose behalf it is acting;**
- **the task-specific authority actually delegated for this action.**

Collapsing those into a single bearer token creates the classic **confused-deputy** condition: a downstream agent has broad powers of its own and is persuaded by a weaker upstream principal to use them.

A representative chain might be:

`Reconciliation agent → break-resolution agent → settlement agent → payment service`.

Suppose the reconciliation agent can identify a break but has no authority to alter a settlement instruction. If it can simply ask a settlement agent that *does* have that authority, and the settlement agent authenticates only the immediate caller, the chain has **laundered privilege**.

The failure modes include:

**impersonation**, when agents share service accounts or forwarded bearer tokens; **authority amplification**, when a downstream agent applies its own larger privilege set rather than the delegated subset; **token passthrough**, where a token intended for one audience is accepted by another; **delegation replay**, when a valid delegation survives the task for which it was issued; **chain ambiguity**, where logs preserve only the last hop; and **recursive or collusive escalation**, where agents combine individually legitimate privileges into an impermissible sequence.

JPMorgan Chase explicitly identifies delegated authority, accountable identities and agent-to-agent trust as foundational security issues. citeturn17view6 MCP's security specification specifically rejects accepting tokens meant for another resource, addressing one class of token-confusion problem. citeturn22search3

The defensible design principles are:

**separate actor from delegator; re-authorize each consequential hop; bind authority to audience, action, task and expiry; attenuate authority rather than amplify it; retain the complete actor/delegation chain; and never assume that because action A was authorized, action B downstream is automatically authorized.**

IETF work is moving directly toward those needs. An OAuth AI-agent proposal introduces separate actor information for agents acting on behalf of users; other 2026 drafts address attenuated authorization and delegation chains. citeturn22search10turn6search16 But these remain emerging drafts rather than mature cross-vendor standards. An IETF analysis in 2026 documented dozens of overlapping drafts and unresolved approaches around identity, delegation, discovery and audit—strong evidence that this part of the architecture is **not yet settled**. citeturn22search25

That has a practical consequence for Nomura: the response should not bet its architecture on a brand-new “agent delegation protocol.” It should define the **semantics Nomura needs**—actor chain, non-amplification, task binding, expiry, resource audience, action constraints and audit—and map current or future protocols into that model through adapters.

## Rogue-agent control and the competitive landscape

**Research question — detecting and correcting rogue agents**

“Rogue” should be decomposed into at least four failure classes because they are detected differently:

**compromise** — the agent or its credentials are controlled by an attacker;  
**prompt/data injection** — untrusted data changes the agent's instructions;  
**misalignment** — the agent pursues an objective in a harmful but internally coherent way;  
**malfunction** — bugs, hallucination, stale data or tool failures cause unintended actions.

No single “AI guardrail” reliably detects all four.

### What the empirical evidence says

Prompt-injection detection remains considerably less robust than vendor presentations can imply. An October 2026 study re-evaluating detectors across agent benchmarks found severe transfer problems: the best detector on one benchmark reportedly detected only **2%** of AgentDojo injections at a **1% false-positive rate**, while a detector that caught **72%** of attacks on AgentDojo caught only **15%** on another task distribution. The paper also found false-positive behavior changed sharply across tool-output distributions. citeturn10search0 The lesson is not that detectors are useless; it is that benchmark performance does not generalize automatically to a bank's own messages, files and tool outputs.

Other 2026 work similarly shows material residual risk. Automated prompt-injection research reports non-zero attack success even against stronger models and materially higher success across repeated attempts. citeturn10search1 Research on agent data injection reports that structured data such as JSON and DOM content can carry attacks that bypass defenses designed for conventional prompt injection. citeturn10search5

There are also promising results. PromptArmor reported low false-positive and false-negative rates in its evaluated benchmark settings, while a 2026 agentic detection system reported strong results on its own benchmark and low false alarms on AgentDojo. citeturn10search29turn10search16 These results do **not** contradict the transfer problem: they show that well-designed detectors can be effective on particular distributions while remaining difficult to calibrate universally.

Tool-layer controls offer a different line of defense. ACL 2026 research on tool-invocation safety reported a substantial reduction in harmful tool invocations under prompt injection while maintaining benign-task utility. citeturn10search19 More importantly for a bank, deterministic authorization can prevent a harmful effect even when the security layer fails to correctly classify the prompt as malicious.

That gives a useful hierarchy:

| Control | What it catches best | Main weakness |
|---|---|---|
| **Hard authorization invariant** | Clearly forbidden systems, data, tools, fields, actions, amounts, counterparties or state transitions | Cannot detect harmful behavior that remains technically within the allowed envelope |
| **Transaction/business invariant** | Semantically wrong operational actions, e.g. payment does not match the trade or SSI | Requires capital-markets domain modelling |
| **DLP/data classification** | PII/client/confidential-data exfiltration | May not understand why an otherwise permissible field is being used |
| **Prompt-injection detector** | Known/modeled adversarial instruction patterns | Distribution shift, evasion and false positives |
| **Behavior anomaly / UEBA** | Novel volume, destination, sequence, time, delegation or access pattern | Rare legitimate operations can look anomalous |
| **LLM judge / semantic monitor** | Intent and contextual anomalies that rigid rules miss | Probabilistic and vulnerable to the same model/adversarial problems |
| **Human escalation** | Ambiguous and consequential exceptions | Slow and expensive; can become a bottleneck |

For capital-markets operations, some of the strongest controls are ordinary **business invariants expressed at machine speed**. A settlement agent should not be able to alter standing settlement instructions merely because a text field says to. A payment should be tied to an approved trade/obligation, currency, amount range, counterparty, legal entity and mandate. A reconciliation agent that normally reads breaks should not suddenly retrieve a broad client-data set or write to a golden-source ledger. A reference-data agent should not change a legal-entity identifier or SSI without the required maker/checker or approval condition.

### A credible rogue-agent demo

A stronger scenario than “the chatbot says something toxic” would be:

A synthetic reconciliation agent reads an external counterparty file containing an injected instruction telling it to obtain restricted client information and then ask a settlement agent to replace an SSI with a new beneficiary.

The demo should visibly show:

**first**, the agent has a registered machine identity and declared purpose;  
**second**, the malicious instruction reaches the model—proving the demo is not simply filtering the string at ingress;  
**third**, the resulting client-data call is evaluated against agent/data/purpose policy and denied;  
**fourth**, the attempted delegation to the settlement agent carries the original actor/task context, so the downstream agent cannot inherit the settlement agent's broader authority;  
**fifth**, the SSI update is denied or escalated before execution because it violates the mandate and/or maker-checker policy;  
**sixth**, the event raises a behavioral/security signal;  
**seventh**, the identity or session is quarantined, its short-lived authority revoked, and the immutable audit trail shows the attempted sequence.

The key point is that **the model is allowed to fail while the system remains safe**. That is a much more persuasive demonstration of enterprise capability.

Containment should support graduated actions: deny the individual call; require human approval; force read-only mode; lower transaction limits; stop further delegation; revoke or rotate credentials; terminate the agent session; isolate the workload's egress; or kill/quarantine the workload. MAS SAFR explicitly contemplates action-level deny/escalate/observe/execute decisions and cites kill switches/timeouts among agent controls. citeturn18search11turn19view4

“Correction” should likewise not mean silently instructing a compromised agent to behave better. Depending on the root cause, recovery may require resetting context/memory, removing a poisoned source or tool, rotating credentials, restoring a trusted configuration, reducing privileges, rolling back reversible actions and rerunning evaluation before reinstatement.

There are **no robust, publicly verified bank-production false-positive rates** for this whole control stack. The benchmark evidence above should therefore be presented as experimental evidence, not a performance promise.

**Research question — competitive landscape**

The market is rapidly filling in around Nomura's requirement.

### Identity and entitlement vendors

Microsoft Entra Agent ID now offers explicit agent identities and access governance; Okta offers agent identity, token exchange and access certification; SailPoint offers agent discovery and lifecycle governance; CyberArk/Idira combines discovery, privilege management and an agent/tool identity broker. citeturn20search0turn20search1turn20search10turn20search35 Saviynt, Ping Identity and other identity firms are also integrating agent-aware authorization into gateway ecosystems. Google's current Agent Gateway partner catalog includes Okta, Ping, Saviynt, Silverfort and multiple security vendors. citeturn21search24

### Cloud/platform vendors

Google's integrated stack combines Agent Identity, Registry, Gateway and observability. citeturn21search5turn21search12 AWS combines AgentCore Gateway and analyzable authorization policies. citeturn21search0turn21search4 Microsoft is integrating Entra Agent ID with its broader agent/Foundry ecosystem. citeturn20search28 These vendors increasingly provide enough functionality that a consultancy should not claim that basic agent registration, OAuth or policy evaluation is proprietary differentiation.

### Open infrastructure

SPIFFE/SPIRE, Envoy, Istio and OPA provide credible open building blocks for machine identity, interception and externalized authorization. citeturn21search2turn21search7turn21search25 OpenID AuthZEN is standardizing the PDP/PEP interface, while MCP and A2A are reducing agent-integration friction. citeturn22search5turn22search0turn7search2 This increasingly makes a bespoke “agent gateway” itself less defensible as a services firm's main differentiator.

### AI-security vendors

Google's gateway ecosystem now lists integrations from Palo Alto Networks, Cisco, CrowdStrike, F5, Netskope, Zscaler, Check Point and others for prompt/tool/data inspection and behavioral controls. citeturn21search24 This illustrates how fast generic inspection and guardrails are becoming a marketplace feature.

### Consultancies and systems integrators

Accenture has published an AI-agent Zero Trust/IAM model and identifies authentication, authorization and role-based agent permissions as a 2026 banking priority. citeturn24search0turn24search8 Deloitte has a 2026 banking-specific treatment of agentic risk and governance. citeturn24search1 IBM Consulting markets agentic-AI governance and AI integration services. citeturn24search6turn24search34 Capgemini offers enterprise agentic-AI integration and financial-services agentic programs. citeturn24search3turn24search31 These are genuine competitors for the strategy/integration work even where they do not own the underlying entitlement technology.

### What is becoming commodity and what is not

**Increasingly productized:** unique agent identity; workload credentials; OAuth/OIDC; generic agent/tool registries; API/MCP gateways; allow/deny policy engines; agent access reviews; logging/tracing; prompt/DLP inspection; basic anomaly detection; cloud-native agent observability.

**Still hard and differentiating:**

**Brownfield discovery and identity binding.** Finding a logical agent spread across shared runtimes, service accounts, legacy APIs, databases, message queues and UI automation is materially harder than governing a newly created cloud-native agent.

**Business-semantic authorization.** A generic IAM platform knows “write:database”; it does not inherently know that a reconciliation agent may correct a break but must not modify an SSI, or that a settlement agent may release only a payment corresponding to a validated obligation below a mandate threshold.

**Cross-platform delegation.** Identity products are converging, but consistent non-amplifying authority across multiple clouds, frameworks, MCP, A2A, legacy applications and custom agents remains unsolved at industry level, as the continuing IETF draft activity demonstrates. citeturn22search1turn22search25

**Safe entitlement optimization.** Removing permissions from production automation without breaking rare but critical flows requires business knowledge, scenario simulation, telemetry quality, risk thresholds and governance; the analytics are easier than safely operationalizing the changes.

**Control placement in the legacy estate.** Deciding whether the enforceable chokepoint should be a service mesh, API gateway, credential broker, database proxy, application adapter or downstream transaction control is an architectural and organizational problem, not something one product can determine.

**Regulator-grade evidence.** Correlating agent identity, delegator, task, authorization decision, action, data lineage, policy version, exception/approval and downstream effect into one defensible record is still difficult in heterogeneous environments.

Those are the areas in which a services firm can credibly differentiate.

## What would convince the buyer and the questions only Nomura can answer

**Research question — what would convince this buyer**

Nomura's own public statements provide unusually useful evidence about the likely buying lens. Kato describes her method as envisioning the ideal state, identifying the gap from the current state, then determining what people and support are required. She also emphasizes that governance must evolve with AI and that proposed use cases are examined for ethics, legal soundness and cybersecurity before rollout. citeturn17view1 That suggests a response centered on a shiny framework diagram or one vendor platform would be poorly matched to the stated operating style.

The buyer is likely to find the response credible if it demonstrates **problem-solving method, interoperability and evidence**, rather than merely claiming expertise.

### What the architecture strategy should show

The architecture point of view should begin with **control objectives and decision points**, not a product stack:

`Discover → Identify → Authorize → Enforce → Observe → Attribute → Contain → Review/Optimize`.

It should then show alternative enforcement patterns for API-native agents, opaque legacy agents, data access, agent-to-agent calls and UI/RPA cases, with explicit decision criteria for choosing among them. The target architecture should separate:

**identity plane** — unique agent/workload identities, owners and lifecycle;  
**resource and tool registry** — systems, APIs, datasets, capabilities and sensitivity;  
**policy plane** — roles, attributes, relationships, mandates, risk thresholds and segregation-of-duties rules;  
**enforcement plane** — gateways, proxies, credential brokers, service meshes and application/data adapters;  
**telemetry/evidence plane** — immutable identity, delegation, decision and action records;  
**optimization plane** — access analytics and recommendations that feed controlled policy change.

This does **not** imply that these must be six new products. Existing Nomura IAM, PAM, IGA, API management, service mesh, CMDB, data-governance, SIEM and cloud controls may already fulfill much of each plane.

### What the entitlement point of view should show

A serious POV should distinguish:

**identity** — “which machine actor is this?”  
**authentication** — “how did it prove that?”  
**delegation** — “who authorized it to act, and for what task?”  
**entitlement** — “what resources/actions may it use?”  
**runtime authorization** — “is this specific action allowed now?”  
**behavioral oversight** — “is a nominally allowed sequence becoming suspicious?”  
**optimization** — “does observed use justify narrowing or changing the mandate?”  
**accountability** — “which human/business function ultimately owns this agent and exception?”

The response will lose credibility if those are collapsed into “RBAC for agents.”

### What the unified capability demo should contain

A credible synthetic-banking demo could simulate four systems:

a **trade-capture API**, a **reconciliation database**, a **reference/SSI service**, and a **settlement/payment service**, using deliberately different integration styles. It should include both an agent whose code can be instrumented and an “existing opaque agent” wrapped externally.

The audience should be able to see the entire lifecycle:

**registration and ownership.** A new and existing agent appear in an inventory with owner, purpose, criticality and identity.

**permission establishment.** The reconciliation agent can read assigned breaks and approved reference records but cannot read unrelated client PII or write SSIs; the settlement agent has a different mandate.

**normal STP.** An allowed synthetic trade/reconciliation/settlement flow executes with no human interruption and generates traceable evidence.

**delegation.** Agent A asks Agent B to act; the control plane preserves both identities and task authority, and the downstream permission is no greater than the delegated mandate.

**observe-only mode.** A proposed rule is evaluated without enforcement and exposes a legitimate exceptional workflow that would otherwise have been accidentally blocked.

**optimization.** Historical synthetic telemetry shows an obsolete or consistently unused privilege. The system proposes a narrower policy, simulates it against normal and rare test scenarios, then requires an accountable approval before the change takes effect.

**rogue event.** An injected external file causes an agent to request restricted client data and an SSI modification. The request is denied before the target system changes, the delegation chain is shown, the identity/session is contained, and the audit trail records policy version, reason and disposition.

**measured engineering evidence.** The demo should report added authorization latency, failure behavior when the policy service is unavailable, percentage of consequential actions passing through enforcement, action-attribution coverage and the false-positive/false-negative result on a defined adversarial test set. It should not imply that one successful scripted attack proves universal prompt-injection protection; cross-benchmark research strongly warns against that claim. citeturn10search0

That is more convincing than a polished UI because it demonstrates the exact capability Nomura lacks: **control over actions, including when the agent itself is wrong**. It is also close to the practical path advocated by JPMorgan—reference architectures and implementation examples showing agent-to-system and agent-to-agent control, authorization, monitoring and containment. citeturn17view6

### What credible talent profiles should look like

The requested sample profiles should collectively prove the firm has people spanning the full problem, not merely GenAI developers.

A **Principal AI/Security Architect** should demonstrate heterogeneous enterprise architecture, IAM/zero-trust design, API/data integration and regulated-cloud experience.

An **Identity and Authorization Lead** should have IAM/IGA/PAM, OAuth/OIDC, workload identity, RBAC/ABAC/ReBAC, policy-as-code and machine-identity experience.

An **Agent Runtime / Integration Engineer** should be able to build with more than one agent framework, MCP/A2A, APIs, message systems and gateways and to wrap brownfield workloads rather than requiring rewrites.

An **AI Security and Evaluation Engineer** should understand prompt/data injection, adversarial testing, model/tool monitoring, evaluation calibration and containment.

A **Capital-Markets Operations SME** should understand trade capture, confirmations, reference data, reconciliations, settlements, SSIs, exception handling, maker-checker and operational cut-offs.

A **Data Security/Governance Specialist** should understand data classification, lineage, fine-grained access, DLP and cross-border constraints.

A **Financial-Regulatory AI/Risk Lead** should be capable of mapping control evidence to JFSA, FINRA/SEC, FCA/PRA, DORA, MAS and relevant local requirements without falsely claiming one global rule.

An **SRE/Observability Engineer** should be able to demonstrate production failure modes, telemetry, policy-engine availability, latency, rollout, rollback and tamper-resistant audit.

Nomura's current AI-governance recruitment itself asks for a mix of testing, monitoring, cross-agent conflict detection, guardrail metrics, investment-banking/global-markets knowledge and cloud experience, reinforcing the value of showing similarly multidisciplinary staffing. citeturn17view3

### Open questions that only Nomura can answer

| Question for Nomura | Why it matters |
|---|---|
| **Who exactly is the sponsor, and under which Nomura Holdings / business / regional organization does the mandate sit?** | Confirms whether the public CDO structure identified here is the correct governance owner and who can mandate cross-business controls. |
| **What counts as one of the “160+ systems,” and which are in the initial entitlement scope?** | Determines whether the problem is APIs/databases/messages/UI automation and prevents designing to an inaccurate abstraction. |
| **How many production agents exist today, who owns them, and how are they discovered?** | Sets inventory scope and exposes shadow agents or unowned automation. |
| **What does Nomura call an “agent”? LLM-based autonomous software only, or also RPA, deterministic bots and workflow orchestrators?** | The identity population and control architecture change dramatically depending on definition. |
| **Where are existing agents hosted—AWS, other cloud, Kubernetes, VMs, desktops, SaaS, on-premises?** | Determines which workload-identity and interception mechanisms are technically possible. |
| **Which frameworks/models/orchestrators are currently in use?** | Needed for native integrations, but the architecture should remain viable when this information is unavailable. |
| **How do agents authenticate today: API keys, user accounts, service accounts, OAuth clients, certificates, vault-brokered secrets? Are credentials shared?** | Shared credentials are a direct barrier to reliable attribution and least privilege. |
| **How do agents call systems: REST/gRPC, MCP, database, MQ, file transfer, batch, email or UI/RPA?** | Identifies enforceable chokepoints and areas requiring adapters. |
| **How do agents call each other today, and can a logical delegation chain be reconstructed?** | Central to confused-deputy and privilege-escalation risk. |
| **Can network or API routing be changed so agent traffic must cross an enforcement point?** | External governance cannot prevent actions that can bypass all PEPs. |
| **What IAM, IGA and PAM platforms already exist?** | A credible strategy should reuse established systems of record rather than create a parallel entitlement silo. |
| **What API gateways, service meshes, workload-identity systems, secrets platforms and proxies are already deployed?** | May supply most of the runtime enforcement fabric. |
| **What data catalog, classification, lineage and data-access-control infrastructure exists?** | Data sensitivity and purpose are key attributes for granular authorization. |
| **Which SIEM, observability and transaction-monitoring platforms hold current telemetry?** | Determines whether discovery, behavioral baselines and audit can reuse existing evidence. |
| **Which systems/actions are irreversible or financially consequential?** | Drives fail-closed versus fail-open behavior, escalation thresholds and human approval. |
| **What are the maker-checker, segregation-of-duties and delegated-authority rules for post-trade processes today?** | These business rules should become machine-enforceable invariants rather than be replaced by generic IAM rules. |
| **What legal entities and jurisdictions participate in the target flows?** | Determines applicable supervisory, data-residency and recordkeeping overlays. |
| **What are the latency and availability SLOs for trade, reconciliation and settlement paths?** | Runtime authorization is unacceptable if it violates critical processing windows. |
| **What should happen when the central authorization service is unavailable?** | Fail-open/fail-closed behavior is one of the most important operational-risk decisions. |
| **Does “optimized” mean minimum privilege, lower administrative effort, higher STP, lower exceptions, risk-weighted permissions, or some combination?** | There is no mathematically meaningful optimization until the objective and constraints are explicit. |
| **What rare/month-end/quarter-end/DR flows must remain possible even if telemetry seldom observes them?** | Prevents unsafe right-sizing from removing critical exception authority. |
| **How long must authorization decisions, prompts, tool calls and action logs be retained, and where?** | Affects audit design, cost and privacy. |
| **Can existing agents be wrapped, proxied or re-routed even when they cannot be modified?** | Determines how much of the brownfield estate can be governed non-invasively. |
| **Have there already been agent-related incidents, near misses or excessive-access findings?** | Real failure modes are far more valuable for architecture and demo design than generic threat scenarios. |
| **What stakeholders will judge the proof—CDO, CIO, CISO, operations, risk, compliance, IAM, architecture, internal audit?** | The demo needs to prove different things to each constituency. |
| **What would constitute a successful capability proof?** | Prevents an impressive engineering prototype that fails the buyer's actual evaluation criteria. |

## Caveats and full source list

### Caveats

The discovery-meeting statements—**160+ systems, lack of native STP between them, numerous agents already operating as infrastructure, and absence of centralized agent governance**—are treated as Nomura's stated position. Public research did not independently verify those details. Nothing in this report should be interpreted as evidence that Nomura lacks existing IAM, PAM, cybersecurity, AI-governance or application-specific controls; the narrower client-stated gap is a centralized architecture for agents.

The sponsor's exact identity remains unverified. The public role most closely matching the internal title is **Ayumi Kato, Co-Chief Data Officer and Head of the Chief Data Office at Nomura Holdings**, but the research does not prove she attended or sponsored the discovery engagement. citeturn17view1

Regulation is especially time-sensitive. This report is current to **14 October 2026**, and MAS's final AI Risk Management Guidelines were issued only one week earlier, on **7 October 2026**. citeturn18search2 Legal-entity-specific analysis should therefore be refreshed before a formal regulatory assertion is included in a client proposal.

MAS SAFR is particularly relevant but must not be misrepresented: it is an **industry-developed runtime governance framework**, and MAS materials distinguish it from binding supervisory expectations. citeturn18search3turn18search13 The final MAS AI Risk Management Guidelines, by contrast, do state supervisory expectations. citeturn18search2

Likewise, the EU AI Act should not be cited as though every settlement, reconciliation or trade-support agent is automatically a high-risk AI system. Applicability depends on the system, purpose and legal classification. DORA and ordinary financial-sector ICT/access-control obligations may be more directly relevant to many back-office agent scenarios. citeturn16search3turn4search14

The market is moving rapidly. Features described for Microsoft, Google, AWS, Okta, SailPoint and CyberArk are based on current October 2026 public documentation. Product availability, packaging and GA/preview status can change quickly. Product documentation demonstrates **capability**, not necessarily independent proof of effectiveness in a global investment-bank production estate.

Vendor-hosted customer stories—AWS/Nomura, Google/Wells Fargo and similar examples—have been treated as vendor-sourced evidence and not as independent validation. citeturn17view4turn8search11

Prompt-injection and rogue-agent effectiveness figures are primarily research-benchmark results, including recent preprints and conference work. They should not be generalized into expected Nomura production detection rates. The cross-benchmark evidence specifically cautions against doing so. citeturn10search0

The research found no verified public disclosure of a Nomura AI-agent security incident. That does not establish that none exists internally.

### Full source list used in the analysis

**Nomura primary sources**

- Nomura Plus, **“Encouraging Free Thinking and the Safe Use of AI | Ayumi Kato,” 7 August 2026** — current Co-Chief Data Officer title, CDO mission and size, review process, AI-deployment counts and Kato's role in AI governance. citeturn17view1
- Nomura Holdings, **AI Governance** — Artificial Intelligence Governance Policy and centralized group-wide operating framework. citeturn16search4
- Nomura Holdings, **Nomura Report 2026**, August 2026 — AI Governance Policy and AI & Data Strategy Department. citeturn16search0
- Nomura Holdings, **Sustainability Report 2026** — group AI-governance framework. citeturn16search7
- Nomura Careers, **VP – AI Governance**, current 2026 posting — CDO mandate, testing, monitoring, cross-agent and guardrail metrics. citeturn17view3
- Nomura legal/electronic-communications notice — global regulated-entity mapping across Japan, UK, Europe, Singapore, Hong Kong, US and other jurisdictions. citeturn17view5
- Nomura public organizational material — Chief Data Office, AI & Data Strategy and technology/security functions. citeturn15search1turn15search4
- Nomura public presentation — group-wide AI, automation and hybrid-cloud infrastructure. citeturn0search18
- Nomura / Google Cloud recognition relating to **FINTOS**. citeturn2search2

**Nomura technology relationships**

- AWS, **Nomura on AWS** — Amazon Bedrock/Llama, “core AI,” compliance automation, modernization and AWS described by a Nomura architect as primary cloud provider. citeturn17view4
- AWS customer material on Nomura's use of Meta Llama in Bedrock. citeturn2search24
- AWS Nomura modernization case study covering ECS/Fargate/Aurora/Glue and digital applications. citeturn2search4

**Japan regulation**

- Japan Financial Services Agency, **AI Discussion Paper / version 1.1**, updated 3 March 2026. citeturn16search5turn16search17
- JFSA Access FSA, explanation of the original AI Discussion Paper and its non-prescriptive positioning, 2025. citeturn16search8
- JFSA, **Policy Approaches to Strengthen Cyber Security in the Financial Sector**, including 2026 frontier-AI threat work. citeturn16search2
- JFSA strategic priorities, including the AI Public-Private Forum. citeturn16search11

**United States and United Kingdom regulation**

- FINRA, **2026 Annual Regulatory Oversight Report — GenAI: Continuing and Emerging Trends** — technology-neutral application of rules, supervision, testing, logging/monitoring and AI-agent considerations. citeturn18search0
- FCA, **AI and the FCA: our approach**, updated 2 October 2026 — existing rules and senior-manager accountability rather than a separate AI rulebook. citeturn18search5
- FCA CEO Nikhil Rathi, **Rethinking regulation for the age of AI**, 24 June 2026 — generative and agentic AI in financial services. citeturn18search1
- FCA, **Mills Review: AI and the future of retail financial services**, 6 July 2026 — movement toward delegated AI decision-making. citeturn18search9

**European regulation**

- European Union, **Digital Operational Resilience Act, Regulation (EU) 2022/2554** — ICT-risk governance, continuous monitoring and documented resilience controls. citeturn16search3
- European Union, **Commission Delegated Regulation (EU) 2024/1774** — identity management and access-right controls under DORA. citeturn16search15turn16search24
- European Union, consolidated **AI Act** materials current in 2026 — high-risk-system logging, robustness and cybersecurity where applicable. citeturn4search14

**Singapore regulation and industry frameworks**

- Monetary Authority of Singapore, **Guidelines on Artificial Intelligence Risk Management**, 7 October 2026 — final supervisory expectations. citeturn18search2turn18search6
- MAS guideline pages on proportional application, inventory and materiality assessment. citeturn19view0turn19view2
- MAS guideline page on board/senior-management responsibilities, incidents and escalation. citeturn19view1
- MAS, **Safeguards for Agentic Finance at Runtime (SAFR)**, 3 July 2026 — financial-agent runtime framework. citeturn18search7turn18search11
- MAS SAFR material on deny/escalate/observe/auto-execute and tamper-evident logs. citeturn19view4
- MAS SAFR industry examples for Visa and Circle, plus associated industry use cases. citeturn19view5turn13view1
- MAS, **Project MindForge AI Risk Management Toolkit**, March 2026 — financial-sector operationalization guidance. citeturn18search10turn18search24
- MAS parliamentary response on agentic AI, 5 August 2026 — SAFR as a potential approach to point-of-action authorization and oversight. citeturn18search13

**Bank and financial-enterprise practice**

- JPMorgan Chase, **Securing the next generation of AI agents**, March 2026 — delegated authority, runtime governance, authorization, agent-to-agent trust and auditability. citeturn17view6
- Deutsche Bank Private Bank, September 2026 agentic Source-of-Wealth/KYC deployment in Singapore and Hong Kong. citeturn8search0
- Reuters, February 2026, reporting Goldman Sachs/Anthropic development of agents for trade/transaction accounting and onboarding. citeturn8news41
- Google Cloud / Wells Fargo early enterprise-agent adoption announcement; treated as vendor-sourced customer evidence. citeturn8search11
- Reuters, February 2024, Nomura/Archegos-related UK capital-requirement remediation; contextual control-history evidence, not an AI incident. citeturn5news27

**Identity, authorization and zero-trust foundations**

- NIST, **SP 800-207 Zero Trust Architecture** — resource-focused, no-implicit-trust architecture. citeturn6search10
- SPIFFE/SPIRE official project material — strongly attested cryptographic workload identity across heterogeneous infrastructure. citeturn21search2turn21search6
- Open Policy Agent — CNCF-graduated policy engine and Envoy external-authorization integration. citeturn21search25turn21search7
- Google, **Zanzibar** — relationship-based authorization at large scale. citeturn9search0
- AWS IAM Access Analyzer — unused-access analysis and policy generation from observed activity. citeturn9search2turn9search5
- Google Cloud IAM Recommender — usage- and ML-driven privilege recommendations. citeturn9search3turn9search15
- AWS Verified Permissions / Cedar analysis — deterministic authorization and formal policy analysis. citeturn9search25turn9search1

**Agent protocols and emerging standards**

- Model Context Protocol, **Authorization specification, 28 July 2026** — OAuth 2.1-based authorization model. citeturn22search0
- MCP, **Authorization Security Considerations** — audience validation and separate upstream tokens. citeturn22search3
- OpenID Foundation, **AuthZEN specifications** — Authorization API 1.0 final in January 2026; ongoing agent/MCP profiles. citeturn22search5
- OpenID Foundation, **COAZ / COAZ-MCP**, July 2026 — emerging fine-grained agent/tool authorization drafts. citeturn22search11
- IETF, **AI Agent Authentication and Authorization**, March 2026 Internet-Draft — applying workload identity and OAuth to agents. citeturn22search1
- IETF, **On-Behalf-Of User Authorization for AI Agents** — actor/delegation concepts. citeturn22search10
- IETF emerging work on attenuated authorization/delegation chains. citeturn6search16
- Linux Foundation / A2A official materials — Agent2Agent development and stable 1.0 direction. citeturn7search2turn7search5

**Current product landscape**

- Microsoft, **What is Microsoft Entra Agent ID?**, June 2026. citeturn20search0
- Microsoft, **Plan your agent identity architecture**, August 2026. citeturn20search8
- Google Cloud, **Gemini Enterprise Agent Platform / Agent Identity / Agent Gateway** documentation. citeturn21search5turn21search12turn21search15
- Google Cloud, **Set up Agent Gateway** — unique SPIFFE identity and support for existing workloads. citeturn21search30
- AWS, **Policy in Amazon Bedrock AgentCore** — Cedar policies and natural-language authoring. citeturn21search0turn21search11
- Okta, 2026 Identity Governance release notes and AI-agent token-exchange documentation. citeturn20search1turn20search21
- SailPoint, **Agent Identity Security** documentation. citeturn20search10
- CyberArk/Idira, **Secure AI Agents architecture** — agent identity and Identity Broker enforcement point. citeturn20search35
- Google Cloud, **Agent Gateway ISV partners** — identity, DLP, AI-security and behavioral integrations across multiple vendors. citeturn21search24

**Agent-security research**

- **Re-evaluating Prompt-Injection Detectors for LLM Agents**, October 2026 — cross-benchmark transfer and false-positive limitations. citeturn10search0
- 2026 research on automated prompt-injection attacks and repeated-attempt success. citeturn10search1
- **Agent Data Injection**, July 2026 — attacks embedded in structured tool/data inputs. citeturn10search5
- **Tool Invocation Safety**, ACL 2026 — runtime tool-layer mitigation of harmful invocations. citeturn10search19
- PromptArmor benchmark research — strong results under specific evaluated conditions. citeturn10search29
- 2026 agentic detection research evaluating attack detection and false alarms. citeturn10search16

**Consulting / systems-integration competitive sources**

- Accenture, **Strengthening AI agent security with identity management** — AI-agent Zero Trust and IAM. citeturn24search0
- Accenture, **Banking Trends 2026** — identity, authentication, authorization and agent governance. citeturn24search8
- Deloitte, **Managing the new wave of risks from AI agents in banking**, March 2026. citeturn24search1
- IBM Consulting, **AI Governance Consulting** and AI Integration materials. citeturn24search6turn24search34
- Capgemini, **Reimagining financial services with agentic AI** and **Agentic AI for Enterprise**. citeturn24search3turn24search31