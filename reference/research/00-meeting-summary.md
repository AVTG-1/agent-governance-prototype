# Nomura Project: Alignment and Strategy Summary

This document consolidates the details from the Innovation Team and Nomura NY meetings regarding the upcoming Nomura client engagement. 

## (a) Problem Statement & Client Context

**The Core Problem:**
Nomura operates a highly complex environment with over 160 distinct systems across various technology stacks (handling trade data, settlements, reconciliations, etc.). Because these systems do not naturally communicate with one another (preventing Straight-Through Processing), Nomura utilizes numerous AI agents to bridge the gaps and facilitate inter-system communication. 

**The Missing Piece (Client Need):**
While the agents exist, Nomura's Chief Data Innovation Officer has identified a critical lack of centralized governance and entitlement architecture. 
*   There is no overarching framework to manage which agents have access to which systems and data.
*   The client lacks the ability to oversee agent actions, verify identity and permissions, or proactively catch improper data access before it causes operational harm.

**Known Constraints & Information:**
*   The solution must address *agent-to-system* and *agent-to-agent* governance, rather than solely focusing on human access.
*   The exact internal implementation details of Nomura's existing agents are currently opaque to the Strive team.

---

## (b) Expected Deliverable

The immediate goal is not to deliver a fully tailored, production-ready implementation, but rather to **prove Strive's capabilities** in solving agent entitlement and governance challenges.

**The Expected Outputs:**
1.  **AI Architecture Strategy:** A high-level overview of how Strive approaches architecture across complex tech stacks.
2.  **Point of View (POV) on Entitlement:** A structured approach on how to build entitlements for existing and future agents.
3.  **Talent Profiles:** Sample profiles of Strive's AI talent to showcase staffing capabilities.
4.  **The Capability Demo (Primary Technical Deliverable):** A single, unified proof-of-concept demo utilizing synthetic banking data. The demo will illustrate an overarching governance framework handling agent entitlements, demonstrating how permissions are established, monitored, and optimized (specifically showcasing a scenario where a rogue/adversarial agent is caught or corrected).

---

## (c) Team Inputs and Perspectives

The following ideas and strategies were presented by the team to shape the demo and overall approach:

*   **Aditi Gupta**
    *   **Input:** Emphasized the need to build a single, solid demo approach rather than presenting 3-4 different architectural options. She also suggested that the demo workflow should begin by explicitly establishing the baseline agent entitlements before initiating any attack-and-fix scenarios.
    *   **Reasoning:** Providing one strong demo keeps the focus on showcasing Strive's core capability without overcomplicating the presentation or guessing too much about Nomura's exact internal setup. Establishing baselines first provides necessary context for the client.

*   **Anand Subramanian**
    *   **Input:** Proposed an adversarial agent workflow for the demo. A primary agent establishes entitlements, an adversarial agent attacks to expose vulnerabilities (e.g., unauthorized data access), and the primary agent iteratively optimizes permissions to fix the gaps. 
    *   **Reasoning:** Argued that while human Role-Based Access Control (RBAC) is a solved problem with decades of history, *agent* RBAC is a novel challenge. The demo must focus squarely on agent behavior to directly address the client's specific governance gap.

*   **Dharmendra Singh**
    *   **Input:** Suggested incorporating a deterministic, foundational layer of Human Role-Based Access Control (RBAC) into the architecture (e.g., column/row-level security via config files or databases). AI should strictly handle the exceptions that bypass these static checks, aligning with the idea of a governance agent catching a rogue agent.
    *   **Reasoning:** Grounding the solution in established enterprise permission structures (similar to how Google Drive handles access) ensures baseline security, allowing the AI to focus on complex correlations and exceptions rather than basic routing.

*   **Pothuri Sai Eswar**
    *   **Input:** Advocated for a conservative, deterministic rule-based classifier as the initial step (e.g., explicitly restricting a sales agent to sales files). Strongly cautioned against using a "super-arching" LLM to manage other LLMs.
    *   **Reasoning:** Layering probabilistic models (LLMs) on top of one another compounds uncertainty, increases behavioral risk, and adds unnecessary processing costs. A deterministic baseline is safer and more predictable.

*   **Aryan Verma**
    *   **Input:** Argued that static rules might be too restrictive. Proposed a hierarchical structure where a higher-level "super agent" (or mother agent) can dynamically evaluate requests and expose necessary, cross-domain data to lower-level agents on a need-to-know basis. 
    *   **Reasoning:** In real-world scenarios (like reconciliation), agents often need temporary access to out-of-domain data to complete complex tasks. A rigid deterministic rule set might break existing data pipelines, requiring dynamic oversight.