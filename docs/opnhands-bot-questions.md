## Bot Discovery Questions Aligned with DeepWiki

This question set draws directly from the DeepWiki structure for [OpenHands/software-agent-sdk](https://deepwiki.com/OpenHands/software-agent-sdk). Each question references the relevant section so we can keep requirements and design decisions grounded in the existing documentation.

### 1. Overview (Sections 1.1–1.2)
1. Section 1.1 outlines getting started—what minimum platform and dependency checklist should we confirm before beginning bot development?
2. Based on Section 1.1, what are the recommended first experiences or tutorials we should run to familiarize the team with the SDK?
3. Section 1.2 describes deployment modes—what mode(s) should our bot support initially (e.g., standalone, server) and why?

### 2. Core Architecture (Section 2)
4. The Core Architecture section splits functionality across four packages—how should we map our bot’s responsibilities to `openhands-sdk`, `openhands-tools`, `openhands-workspace`, and `openhands-agent-server`?
5. Section 2.1 describes the SDK package—what agent lifecycle APIs from `openhands-sdk` will our bot need to call, and what custom logic should wrap them?
6. From Section 2.2–2.4, what existing tooling, workspace orchestration, or server features can we reuse versus needing new extensions?

### 3. Agent System (Section 3)
7. Section 3.1 covers agent configuration—what parameters must be configurable (e.g., persona, memory limits, max tokens) for our bot to support?
8. With Section 3.2’s security policies in mind, what authorization boundaries and credential management must we enforce to keep the bot compliant?
9. Section 3.3 details agent reconciliation—how will we reconcile state between bot runs, and what triggers should prompt reconciliation?

### 4. LLM Integration (Section 4)
10. Section 4.1 describes LLM configuration—what model selection strategy (e.g., temperature, versioning) suits our use case, and where does the configuration reside?
11. In Section 4.2, what model routing rules or feature flags must the bot support to divert traffic between inference endpoints?
12. From Section 4.3 on metrics, what telemetry should we surface (latency, cost, hallucination rate) and how will we collect it?
13. Section 4.4 discusses function calling—what functions must our bot expose to the LLM, and how should we design their signatures?

### 5. Conversation Management (Section 5)
14. Section 5.1 talking about local conversations—how should we model conversation buffers, history pruning, and local context for responsiveness?
15. Based on Section 5.2, which remote conversation backends (if any) need to be supported, and how will we sync them with local state?
16. Section 5.3’s event system hints at extensibility—what events (user message received, tool invoked, error) should our implementation expose?
17. Section 5.4 covers context condensation—what condensation algorithm or heuristics will keep the bot’s context window manageable?
18. Section 5.5 mentions state persistence—where will we store conversation state (DB, filesystem, etc.), and how do we ensure durability?
19. For Section 5.6’s secret management, what secrets (API keys, credentials) must the bot protect, and what storage/rotation policies apply?

### 6. Tools and Capabilities (Section 6)
20. Section 6.1 outlines the tool system architecture—how will we register and expose our bot’s tools to the agent runtime?
21. From Section 6.2’s built-in tools, which ones can immediately fulfill our requirements (e.g., web search, file access), and where do we need custom tooling?
22. Section 6.3 shows browser automation—does our use case demand controlling browsers, and if so, what automation scripts or selectors are required?
23. Section 6.4 explains creating custom tools—what extensions should we author (name, purpose, inputs/outputs) to cover missing capabilities?
24. How should the bot handle tool failures or timeouts per the architectural guidance in Section 6?

### 7. Workspace Environments (Section 7)
25. Section 7.1 describes local workspaces—what development workflow (OS, dependencies, local servers) must we document for contributors?
26. From Section 7.2 on Docker workspaces, what image/tag should we base on, and what files or mounts does the bot require?
27. Section 7.3 mentions remote workspaces—do we need a remote execution environment, and how will it connect to our agent server?
28. How do we keep workspace environment parity and reproducibility as suggested across Sections 7.1–7.3?

### 8. Agent Server (Section 8)
29. Section 8.1’s server architecture—do we run our own `openhands-agent-server`, or rely on managed hosting, and what sizing/scaling considerations apply?
30. From Section 8.2, which REST API endpoints must the bot expose or consume for orchestration and monitoring?
31. Section 8.3 details WebSocket streaming—do we need streaming interactions, and what protocols/payloads must we support?
32. Section 8.4 discusses deployment options—what environments (K8s, VM, serverless) should we target for the server portion of the bot?
33. Based on Section 8.5, what server configuration files or flags (logging, TLS, retries) need to be templated for our bot’s deployment?

### 9. CI/CD and Automation (Section 9)
34. Section 9.1 describes testing infrastructure—what automated tests must we create (unit, sanity, regression) to validate bot behavior?
35. From Section 9.2’s build pipeline, what steps (lint, compile, package) should the bot follow before deployment?
36. Section 9.3 emphasizes code quality gates—what metrics (coverage threshold, lint pass rate) gate merges for the bot?
37. Section 9.4’s automation workflows—what scheduled jobs (lint, dependency updates, retraining) or GitOps flows should we configure?

### 10. Examples and Development Guide (Sections 10–11)
38. Section 10.1 lists standalone SDK examples—what existing sample corresponds closest to our bot’s goal, and what can we reuse?
39. Section 10.2 covers server mode examples—what patterns or configs should we borrow for scaling the bot in production?
40. From Section 11.1–11.3, what development, testing, and style guidelines must the team follow to stay aligned with the SDK ecosystem?


