# Document Reorganization Plan

**Generated**: 2025-11-20
**Total Documents**: 107

---

## Files to Move

- `KANBAN_AND_YAML_COMPLETE.md` → `implementation/services/kanban_board_yaml_phase_loader_complete.md`
  - Reason: The file details completed code, APIs, DB changes, and test results, matching an implementation log. It focuses on service layer functionality, so category is services. Filename follows snake_case without redundant suffixes, adding _complete to indicate completion. Status is Active as the feature is now live. It resides in docs root, which is appropriate for implementation logs, so not orphaned. No outdated content, so not archived. Related design and architecture docs are suggested for cross‑reference.

- `opnhands-bot-questions.md` → `requirements/agents/bot_discovery_questions.md`
  - Reason: The file lists detailed questions that drive requirement gathering and design alignment, fitting the 'requirements' type. It focuses on agent-related topics, so category 'agents' is appropriate. The current name and location (docs/) are generic and do not reflect its purpose, making it orphaned. It is a draft and should remain active. Related design and guide docs should be cross‑referenced.

- `design/multi_agent_orchestration.md` → `design/agents/multi_agent_orchestration.md`
  - Reason: The document details system architecture, component responsibilities, and implementation patterns, which aligns with a design document. It focuses on agent coordination and monitoring, fitting the 'agents' category. The filename is already concise and appropriate for the design folder. No evidence of completion, so status is Draft. Metadata fields like Created, Status, and Purpose are absent, indicating missing metadata.

- `design/AI_DOCUMENT_ORGANIZATION.md` → `design/guides/ai_powered_document_organization.md`
  - Reason: The content describes how to use an AI script to organize docs, which is a how‑to guide. It does not describe design decisions, architecture, or implementation details, so the document type is 'guide'. The appropriate category is a collection of guides/tools, not 'design'. The current location in docs/design is therefore orphaned; it should reside under a guides directory. Metadata fields are present, and the document is active, not obsolete.

- `phase2_detailed_spec.md` → `design/workflows/phase2_specification.md`
  - Reason: The document provides detailed technical specs (data models, service interfaces, API contracts) for Phase 2, fitting the design category. It focuses on workflow implementation, so category is workflows. Filename should be concise without redundant suffixes. Status field is 'Planning', which maps to Draft in the standardized statuses. It resides in the top-level docs folder, but design specs are usually under docs/design/... hence it's orphaned. No indication it's outdated, so not archived.

- `implementation_questions.md` → `design/agents/implementation_questions.md`
  - Reason: The document lists detailed implementation questions, fitting the 'design' type. It focuses on agent behavior, integration, and configuration, so category 'agents' is appropriate. The current location (docs/) is too generic; it belongs under design/agents/. The filename is already concise and snake_case. The document is a work-in-progress, thus Draft status. No archival needed.

- `design/frontend_pages_scaffold.md` → `design/auth/frontend_auth_scaffold.md`
  - Reason: The file contains ready‑to‑use code snippets and usage instructions, which fits the definition of a guide. It focuses on authentication UI, so the auth category is appropriate. The current location (docs/design) is for design specs, not how‑to guides, making it orphaned. The custom status "Scaffold Document" does not match the allowed status set, so it should be normalized to Draft. The content is current and reusable, so it should not be archived.

- `design/PYTEST_TESTMON_GUIDE.md` → `design/testing/pytest_testmon_guide.md`
  - Reason: The document provides step‑by‑step usage instructions, installation, CI/CD integration and advanced features for pytest-testmon, which matches the definition of a 'Guide' (how‑to documentation). Its content is about testing tooling, so the category is 'testing'. The filename should be concise and snake_case without redundant suffixes, resulting in 'pytest_testmon_guide'. The file resides in docs/design, which is inappropriate for a guide, indicating it is orphaned. Metadata includes Created and Purpose but lacks an explicit Status field, so that is listed as missing. The guide is current and useful, so it should not be archived. Related docs are other testing guides and any ADRs concerning testmon.

- `design/agent_job_prompt.md` → `design/agents/design_job_execution_prompt.md`
  - Reason: The file contains procedural instructions rather than a design spec, making it a guide. It focuses on agent-driven job execution, fitting the 'agents' category. The current location in docs/design is inappropriate for a guide, so it is orphaned. It should be renamed to a concise snake_case name reflecting its purpose and kept active. Metadata fields are absent.

- `design/project_management_dashboard_implementation.md` → `implementation/frontend/project_management_dashboard_implementation.md`
  - Reason: The document contains concrete code snippets, component structures, database schemas, and service implementations, which are characteristic of an implementation document. It focuses on frontend components and related services, fitting the 'frontend' category. The current location in docs/design is inappropriate for an implementation artifact, making it orphaned. The status field in the file is a custom label, so it maps to the standard 'Implemented' status. No required metadata fields are missing.

- `ASYNC_SQLALCHEMY_MIGRATION_PLAN.md` → `design/services/async_sqlalchemy_migration_plan.md`
  - Reason: The file details technical design decisions, refactoring steps, and code changes for async migration, fitting a design document. It focuses on service layer changes, so category is services. Filename should be concise without redundant suffixes. No explicit status metadata, likely still in planning, so Draft. It's placed in top-level docs and named with MIGRATION_PLAN, which is vague; better location under design/services. Hence marked orphaned. Not outdated.

- `PHASE4_PARALLEL_PLAN.md` → `design/monitoring/phase4_parallel_plan.md`
  - Reason: The file details how to build and integrate monitoring, alerting, and observability components, matching a design/specification. It focuses on the monitoring domain. The current filename is acceptable but location at the top-level docs makes it orphaned; it belongs under a design or implementation subfolder. Metadata lacks an explicit Purpose field.

- `DIAGNOSTIC_SYSTEM_ANSWER.md` → `implementation/agents/diagnostic_system_gap_analysis.md`
  - Reason: The document reports current implementation progress and missing pieces, fitting the 'implementation' type. It focuses on the diagnostic agent, so the 'agents' category is appropriate. The filename is not snake_case and the file sits in the top-level docs folder, indicating it is orphaned. It is a current status report, not outdated, thus should not be archived. Related design and requirement docs are suggested for cross‑reference.

- `requirements/agents/lifecycle_management.md` → `requirements/agents/agent_lifecycle.md`
  - Reason: The document defines numerous REQ-AGENT-* codes, outlines acceptance criteria, and focuses on what the system shall do, matching the requirements type. It deals with agent lifecycle, fitting the 'agents' category. The current filename is generic and does not follow snake_case naming conventions; 'agent_lifecycle' is concise and descriptive. No indication of completion, so status is assumed Draft. It resides in the correct requirements/agents folder, so not orphaned. No reason to archive as the content is current. The parent document is referenced and should be linked.

- `agent_assignments_phase1.md` → `design/agents/phase1_agent_assignments_guide.md`
  - Reason: The file outlines step‑by‑step actions, checklists, and coordination points, fitting a guide. It focuses on agents, so category is agents. Filename follows snake_case and adds a _guide suffix for clarity. Status "Ready for Assignment" maps to an active work phase. Being at top‑level docs makes it orphaned; it belongs under a more specific subfolder. No archival needed yet. Related docs are those referenced or logically connected.

- `design/fault_tolerance.md` → `design/monitoring/fault_tolerance.md`
  - Reason: The document details architecture and component responsibilities, matching a design document. It focuses on fault tolerance, a monitoring/resilience concern, fitting the 'monitoring' category. The filename is appropriate without redundant suffixes. No explicit metadata block is present, so missing fields are noted. The status appears to be ready for review rather than final approval.

- `DIAGNOSTIC_SYSTEM_GAP_ANALYSIS.md` → `diagnostic_agent_gap_analysis.md`
  - Reason: The file lists missing components and effort estimates, matching a high‑level gap summary rather than a formal requirements or design spec. It fits the 'summary' type and concerns the Diagnostic Agent, so category 'agents' is appropriate. The current name DIAGNOSTIC_SYSTEM_GAP_ANALYSIS.md is all caps and not snake_case, and it sits in the generic docs folder, making it orphaned. It should be renamed to diagnostic_agent_gap_analysis.md and moved to a summary‑or‑analysis subfolder.

- `task_log.md` → `implementation/services/implementation_log.md`
  - Reason: The file logs implementation progress with timestamps, objectives, and step-by-step plans, fitting the 'implementation' type. Content spans service-level work (phases, agent registry, collaboration, guardian), so category 'services' is appropriate. Filename should be concise and reflect its purpose. Status is active as work continues. Location 'docs' is generic; better placed under an implementation subfolder, thus orphaned. Not ready for archiving yet.

- `phase3_code_review_summary.md` → `code_review_summary.md`
  - Reason: The document provides a high-level overview of test results, coverage, and role implementation status, fitting the definition of a summary. It focuses on agent-related features, so category 'agents' is appropriate. The filename should be concise and reflect its purpose; 'code_review_summary' follows snake_case. The review is complete and approved, but its placement in the top-level docs folder makes it orphaned; it belongs in a dedicated summary or reviews subdirectory. It should remain accessible for reference, so not archived. Related design, requirement, and testing docs are listed for cross-referencing.

- `AUTH_SYSTEM_DEPLOYED.md` → `implementation/auth/auth_system_deployed.md.md`
  - Reason: The document details completed deployment, test outcomes, and live system features, matching an implementation/completion log. It focuses on authentication, so category is auth. Filename should be snake_case without redundant terms. Status is Implemented as the system is production ready. It resides in the top-level docs folder, which is not specific, thus orphaned. No need to archive since it serves as a reference. Missing explicit Created date and Purpose metadata fields.

- `PHASE5_SCHEMA_FIX_NEEDED.md` → `implementation/memory/phase5_schema_fix.md`
  - Reason: The document logs a concrete fix (implementation) with test results, fitting the implementation type. It concerns schema changes for memory-related models, so category 'memory' is appropriate. Filename reflects the phase and fix. Status is Implemented as the change is deployed. It's currently in the generic docs folder, should reside under implementation/memory, thus orphaned. Not archived because it serves as a reference. Related docs are the schema conventions and guardian README.

- `design/frontend_react_query_and_websocket.md` → `design/frontend/react_query_websocket.md`
  - Reason: The document describes technical specifications (how to implement data fetching, caching, and real‑time updates) which aligns with a design document. It focuses on frontend concerns, so the category is 'frontend'. It resides in docs/design, the correct location for design specs, and the current filename is descriptive but can be shortened to a concise snake_case name. The metadata fields are present; status is interpreted as a draft pending review.

- `design/parallel_design_jobs.md` → `design/services/design_jobs.md`
  - Reason: The document outlines how to build design documents (technical specs) for various components, fitting the 'design' type. It lists multiple service and workflow components, so 'services' is the most appropriate category. The filename should be concise without redundant suffixes, e.g., 'design_jobs.md'. It lacks explicit metadata and appears to be a draft, not archived, and correctly placed in docs/design.

- `design/ticket_tracking_postgres.md` → `design/services/ticket_tracking_postgres.md.md`
  - Reason: The document details tables, fields, indexes, and migration considerations, which is a technical design. It pertains to the ticket tracking service, fitting the 'services' category. It resides in docs/design, appropriate for a design spec, and the filename already conveys the PostgreSQL focus without redundant suffixes. Status line indicates readiness for review, mapping to the Review stage. No orphaning or archiving needed. Metadata lacks explicit Created and Purpose fields.

- `design/task_queue_management.md` → `design/services/task_queue.md.md`
  - Reason: The document describes architecture, components, data flows, and implementation patterns, which aligns with a design document. It focuses on the Task Queue Management service, fitting the 'services' category. The filename includes redundant 'management' and could be shortened while remaining clear. No explicit metadata block is present, indicating missing Created, Status, and Purpose fields. The content is current and relevant, so it should not be archived. Related documents are explicitly listed in the text.

- `design/validation_system.md` → `design/workflows/validation_system.md`
  - Reason: The document describes how the Validation System will be built (state machine, components, APIs), which matches a design document. It focuses on workflow validation, so the category is 'workflows'. The filename already follows snake_case and resides in docs/design, the correct location for design docs, so it is not orphaned. The content is current and relevant, so it should remain active. Several related requirement and design docs are referenced and should be cross‑referenced. No metadata block is present, so Created, Status, and Purpose are missing.

- `MIGRATION_CONFLICT_FIX.md` → `design/configuration/migration_conflict_resolution.md`
  - Reason: The document provides step‑by‑step instructions (a guide) for fixing a specific Alembic migration conflict, fitting the 'configuration' domain. The content is complete and intended for ongoing use, so status is Active. It resides in the generic docs folder, which is not the proper location for a guide, making it orphaned. It is still relevant, so not archived. Related docs include other migration guides and ADRs about Alembic.

- `design/mcp_server_integration.md` → `design/integration/mcp_server_integration.md`
  - Reason: The document details architecture, components, and design patterns, matching a design document. It focuses on MCP server integration, fitting the 'integration' category. Filename follows snake_case and is concise. No explicit status metadata is present, so it is treated as Draft. Location under docs/design is appropriate, so not orphaned. The content is current, so no archiving needed.

- `REQUIREMENTS_COMPLIANCE_ANALYSIS.md` → `implementation/agents/requirements_compliance_report.md`
  - Reason: The document summarizes compliance findings against requirement codes (REQ-ALM-001, etc.) and provides evidence from code, fitting the implementation/completion log category. It focuses on agent-related features, so 'agents' is appropriate. The current filename is uppercase and not snake_case, and the file sits in the generic docs folder, making it orphaned. Status is indicated as 'In Progress', mapping to Draft. No archival needed as the analysis is recent. Related requirement and design docs should be cross‑referenced.

- `phase4_parallel_agent_prompt.md` → `archive/phase4_parallel_agent_prompt.md`
  - Reason: The file outlines how to build (design) four agents, their scopes, dependencies, tests, and hand‑offs, fitting the design document type. It belongs to the agents/monitoring domain. The current generic name and top‑level location make it orphaned; it should live under docs/design/agents. As it describes a completed Phase 4 effort, archiving is appropriate. Related docs are those covering metrics, alerts, watchdog policies, observability instrumentation, and the preceding Phase 3 deliverables.

- `design/ticket_human_approval.md` → `design/services/ticket_human_approval.md`
  - Reason: The document details technical design (architecture, components, state machine) thus classified as a design document. It describes a service (approval gate) used in ticket workflows, so category 'services' fits. The current location docs/design is too generic; placing it under docs/design/services improves discoverability, marking it as orphaned. No explicit status metadata is present, so assume Draft. It is current and should remain active. Related docs are referenced in the content.

- `DIAGNOSTIC_FINAL_ANSWER.md` → `implementation/workflows/diagnostic_gap_assessment.md`
  - Reason: The file provides a detailed implementation status report, effort estimates, and recommendations, matching an implementation log. It focuses on workflow diagnostics, so category is workflows. The current filename DIAGNOSTIC_FINAL_ANSWER.md is vague and placed in generic docs, making it orphaned. Suggested snake_case name reflects its purpose. No explicit metadata present, so those fields are missing.

- `design/auth_system_status.md` → `implementation/auth/auth_system_implementation_status.md`
  - Reason: The document lists completed components, pending migrations, and next steps, which matches an implementation status log. It focuses on authentication, so the category is auth. It resides in the design folder, but its content is implementation‑focused, making it orphaned. The status reflects ongoing work (Active). It should be renamed to reflect its purpose without redundant suffixes and moved to an implementation directory. Several related design, service, test, and migration docs should be cross‑referenced. Metadata fields for creation date and explicit purpose are missing.

- `design/CONFIG_MIGRATION_GUIDE.md` → `design/configuration/config_migration_guide.md`
  - Reason: The content provides procedural instructions (a guide) for migrating configuration, fitting the 'guide' type. It focuses on configuration, so the category is 'configuration'. The filename should be snake_case without redundant suffixes. The document is complete and intended for ongoing use, thus 'Active'. It resides in docs/design, which is for design specs, not guides, making it orphaned. No archival need. Status metadata is missing.

- `PHASE5_GUARDIAN_COMPLETE.md` → `implementation/services/phase5_guardian_complete.md`
  - Reason: The file lists completed deliverables, test results, migrations, and next steps, matching an implementation/completion log. It pertains to the Guardian service within Phase 5, so category is services. Naming follows snake_case without redundant suffixes. Status is production-ready/active. It is already in docs root but could stay; not orphaned. Not outdated, so not archived. Related docs include the plan, the feature README, and other squad docs.

- `COMPLETE_ORGANIZATION_SOLUTION.md` → `organization_solution_summary.md.md`
  - Reason: The file provides a final high‑level overview of the organization solution, matching the definition of a SUMMARY document. It does not describe a specific requirement, design, or implementation detail, but rather summarizes decisions and deliverables. The content belongs to the documentation domain. The current filename (COMPLETE_ORGANIZATION_SOLUTION.md) violates the snake_case convention and is placed at the repo root, making it orphaned. The status field uses a custom phrase; mapping it to the standard lifecycle yields 'Implemented'. No explicit 'Created' metadata field is present, so it is listed as missing.

- `design/FRONTEND_UPDATES_SUMMARY.md` → `frontend_updates_summary.md`
  - Reason: The file summarizes multiple design documents and new features, fitting the 'summary' type. It pertains to frontend concerns. The current filename is not snake_case and includes redundant 'SUMMARY' given its location. It should be renamed to snake_case. The document is up‑to‑date and not archived, but its placement in docs/design is suboptimal; a summary folder would be clearer, thus flagged as orphaned.

- `claude_code_agent_prompt_phase2_streams_fgh.md` → `design/agents/phase2_streams_fgh.md`
  - Reason: The content outlines how to build specific features (service interfaces, templates, tests) rather than just stating what to build, fitting a design spec. It focuses on agent‑related streams, so category is agents. The filename is already concise and snake_case. No creation date or explicit status metadata is present, and the file sits in the top‑level docs folder instead of a design subfolder, indicating it is orphaned.

- `foundation_and_smallest_runnable.md` → `design/agents/foundation_architecture.md`
  - Reason: The document outlines architectural decisions and concrete design choices (data models, event bus, task queue) rather than pure requirements, fitting the design category. It focuses on agent orchestration, so the 'agents' sub‑category is appropriate. The current top‑level location is generic; it belongs under a design or architecture folder. No indication of completion, so status remains Draft.

- `implementation/openhands_integration_questions.md` → `implementation/integration/openhands_sdk_integration_questions.md`
  - Reason: The file lists open questions rather than completed code or logs, fitting an implementation‑phase brainstorming document. It concerns integration of the OpenHands SDK, so the category is integration. It resides in docs/implementation but the content is a question list, better suited to a design/requirements discussion, thus it's orphaned. The status appears draft as no answers are provided. Related design and requirements docs about the SDK and orchestration should be cross‑referenced.

- `COMPLETE_SYSTEM_INVENTORY.md` → `system_inventory.md.md`
  - Reason: The file lists what exists and what is missing, acting as a snapshot of implementation status – a classic summary. It spans many services, so the 'services' category fits best. The current name is uppercase and placed at the top‑level docs folder, which deviates from the snake_case naming and expected sub‑folder placement for summaries, marking it as orphaned. The content is current, so it should stay active, not archived.

- `mcp/fastmcp_integration.md` → `design/integration/fastmcp_integration.md`
  - Reason: The file explains how to set up and use FastMCP, includes code examples, testing steps and troubleshooting – typical of a user guide. It fits the integration category. The name fastmcp_integration.md follows snake_case and is concise. The content is current and actionable, so status is Active and it is correctly placed under docs/mcp.

- `phase3_parallel_agent_prompt.md` → `design/agents/phase3_multi_agent_coordination.md`
  - Reason: The file outlines how to build the Phase 3 multi‑agent system (roles, APIs, contracts, tests) which matches a design document. It focuses on agents, so the category is 'agents'. The current name includes 'prompt' and is placed in the top‑level docs folder, making it poorly named and orphaned; a clearer snake_case name without redundant suffix is recommended. The work is upcoming (Weeks 5‑6), so the status is Draft. It is not obsolete, thus should not be archived. Related design and requirement docs for Phase 1/2, event bus, scheduler, and testing are natural cross‑references. Metadata fields like Created, Status, and Purpose are missing.

- `PHASE5_CONTEXT2_FINAL_SUMMARY.md` → `PHASE5_CONTEXT2_SUMMARY.md.md`
  - Reason: The document summarizes completed work, lists components, tests, and integration points, matching the definition of a Summary. It spans multiple services (memory, discovery, kanban, yaml loader), so category 'services' fits. The current filename is overly long; a concise uppercase name is appropriate for a summary. Status indicates completion, mapping to 'Implemented'. Being placed in the root docs folder rather than a dedicated summary directory makes it orphaned. No explicit Created or Purpose metadata fields are present, so they are flagged as missing.

- `PHASE3_COMPLETE.md` → `implementation/agents/phase3_multi_agent_coordination_complete.md`
  - Reason: The document details completed implementation work, test coverage, migrations, and APIs, fitting the 'implementation' type. It focuses on agent-related services, so category 'agents' is appropriate. Filename reflects phase, scope, and completion status. Status is 'Implemented'. It resides in a generic docs folder, making it orphaned; it should be moved to docs/implementation/agents. No need to archive as it serves as a reference for the completed phase.

- `requirements/auth_system.md` → `requirements/auth/auth_system.md`
  - Reason: The document lists REQ- codes, acceptance criteria, and API endpoints, matching the definition of a requirements document. Content focuses on authentication/authorization, fitting the 'auth' category. It resides in docs/requirements, which is appropriate, and the filename follows snake_case without redundant suffixes. Status is explicitly marked Draft. No outdated information suggests archiving. Cross‑reference design, architecture, implementation, and guide docs for the same system, as well as related requirement sets for agents and OAuth.

- `ARCHITECTURE_COMPARISON.md` → `architecture/services/architecture_comparison_current_vs_target.md`
  - Reason: The file compares existing implementation with the intended design, includes gap visualizations and a feature completeness matrix, which aligns with an architecture analysis document. It spans multiple service components, so the 'services' category fits best. The current filename is generic and placed at the repository root, making it orphaned; moving it under a dedicated architecture/design folder and renaming it to a concise snake_case name improves organization.

- `coordination_patterns.md` → `design/workflows/coordination_patterns.md`
  - Reason: The document provides detailed how‑to information, examples, and usage instructions, fitting the definition of a guide. It focuses on workflow orchestration patterns, so the category is workflows. The current filename is already snake_case, but the file lives in the generic docs folder; guides are usually under docs/guides/... making it orphaned. Content is complete and up‑to‑date, so status is Active and it should not be archived.

- `design/workspace_isolation_system.md` → `design/agents/workspace_isolation_system.md`
  - Reason: The document details system components, architecture, API, and configuration, which aligns with a design specification. It focuses on workspace isolation for agents, fitting the 'agents' category. The filename follows snake_case and is appropriately placed in docs/design, so it's not orphaned. No metadata headers are present, indicating missing Created/Status/Purpose fields.

- `ANSWERS_TO_ORGANIZATION_QUESTIONS.md` → `design/documentation/documentation_organization_guide.md`
  - Reason: The file gives detailed guidelines (how‑to) on organizing docs, which matches a Guide. It discusses naming conventions, enforcement, and configuration standards, fitting the 'documentation' domain. It resides in the generic docs root, but per the three‑tier system it should be under a guide sub‑folder (e.g., docs/guide or docs/design). The current name includes redundant suffixes and is not snake_case, so a new snake_case name is suggested. The content is current and not obsolete, so it should stay active.

- `implementation_roadmap.md` → `implementation/workflow/roadmap.md`
  - Reason: The document details phased implementation milestones and deliverables, fitting the 'implementation' type. It focuses on workflow progression, so category 'workflow' is appropriate. Current status metadata indicates active planning. Its placement in the top-level docs folder makes it orphaned; it should reside under an implementation subdirectory. No archival needed as work is ongoing.

- `design/project_management_dashboard_api.md` → `design/services/project_management_dashboard_api.md`
  - Reason: The file contains detailed technical specifications of API endpoints, which aligns with a design document. It resides in the docs/design folder, appropriate for design artifacts. The content focuses on service APIs, fitting the 'services' category. The filename is concise and descriptive without redundant suffixes. Metadata fields (Created, Status, Purpose) are present, so no missing metadata. The status label in the file is not one of the standard statuses, so it is interpreted as a draft design pending review.

- `DIAGNOSTIC_SYSTEM_COMPLETE.md` → `implementation/services/diagnostic_system_implementation.md`
  - Reason: The document details the final implementation of the diagnostic system, listing models, services, APIs, monitoring loops, migrations, and test coverage, which aligns with an implementation log. It pertains to the diagnostic service, fitting the 'services' category. The current filename is uppercase and not snake_case, and its location at the docs root makes it orphaned; it should reside under an implementation/services directory. The status reflects production readiness, so 'Active' is appropriate. The content is current and valuable, so archiving is not needed. Metadata fields like creation date and explicit purpose are missing.

- `HEPHAESTUS_ENHANCEMENTS.md` → `implementation/workflows/hephaestus_workflow_enhancements.md`
  - Reason: The file details completed code changes, schema migrations, and usage examples, matching an implementation log. It focuses on workflow enhancements, so category is workflows. The current location (top-level docs) lacks a type-specific subfolder, making it orphaned. The content is still relevant, so not archived. Suggested filename follows snake_case and adds context without redundancy.

- `PHASE6_DIAGNOSTIC_PROPOSAL.md` → `design/workflows/phase6_self_healing.md.md`
  - Reason: The document outlines technical specifications, models, services, and integration points for Phase 6, fitting the design category. It focuses on workflow self‑healing, so the 'workflows' subcategory is appropriate. The current location (docs root) is generic; design docs belong in docs/design/... Hence it is orphaned. The content is a proposal ready for stakeholder review, not yet implemented, so status is Review. It is current work, not archival.

- `SCHEMA_CONVENTIONS.md` → `design/configuration/schema_conventions.md`
  - Reason: The document details technical specifications (PK/FK types, naming, indexes, migrations) describing how the database should be built, which matches a design document. It is a schema design guide, fitting the 'configuration' category. The filename should be snake_case without redundant suffixes. The status is mandatory for phases 4 & 5, indicating it is actively enforced. It is correctly placed in docs and not outdated.

- `phase3_role4_summary.md` → `implementation/services/coordination_patterns_implementation_summary.md`
  - Reason: The file details completed implementation work, lists new files, tests, and next steps, fitting the 'implementation' type. It concerns service-level coordination primitives, so category is services. The current name includes 'summary' but not in uppercase, and it's in docs root, which is acceptable for a summary. Suggested snake_case name reflects its purpose. Status is completed but still active for reference, not archived. Related docs include the API guide and any requirement/design docs.

- `INTELLIGENT_MONITORING_TESTING.md` → `design/testing/intelligent_monitoring_testing_guide.md`
  - Reason: The content is a step‑by‑step how‑to for testing, matching the 'guide' type. It focuses on testing activities, so the category is testing. The filename should be concise, snake_case, and indicate it's a guide. The document is placed in the top‑level docs folder, but testing guides belong under docs/testing or docs/monitoring, making it orphaned. It is up‑to‑date and useful, so not archived. Metadata headers like Created, Status, and Purpose are absent.

- `requirements/multi_agent_orchestration.md` → `requirements/agents/orchestration_index.md`
  - Reason: The document defines functional and non-functional REQ-* codes, making it a requirements document. Its primary focus is on classifying and managing agents, so the 'agents' category fits best. The file serves as an index, so a concise name like 'orchestration_index' follows naming conventions. No evidence of completion or obsolescence, and it resides in the correct requirements folder.

- `design/CONFIGURATION_ARCHITECTURE.md` → `architecture/configuration/configuration_architecture.md`
  - Reason: The content describes architectural standards (why and what) for configuration management, matching the 'architecture' type. It belongs to the 'configuration' domain. The filename is already descriptive but not snake_case; suggest lowercase snake_case. The file lives in docs/design, but architecture standards belong in an architecture folder, so it is orphaned. The status field uses a custom label; mapping to the standard lifecycle suggests it is currently active. No outdated content, so no archiving. Related docs include the actual implementation module, guides on env usage, and any ADRs that reference this standard.

- `ACCURATE_SYSTEM_INVENTORY.md` → `system_inventory_summary.md`
  - Reason: The document is a high-level overview summarizing implemented components, matching the 'summary' type. It focuses on services and database schema, fitting the 'services' category. Filename should be concise snake_case without redundant suffixes. Status reflects that the inventory is current and corrected. It resides in the generic docs folder, making it orphaned; it belongs in a summary or inventory subfolder. No archival needed as it reflects up-to-date system state.

- `design/supabase_auth_integration_plan.md` → `design/auth/supabase_auth_integration.md`
  - Reason: The document details architecture, schema, and component structure, fitting a design spec. It belongs to the auth domain. Filename can be shortened to avoid redundant 'plan' as the directory already indicates design. Status field is non-standard, mapping to Draft. Location is appropriate, no need to archive, and related auth integration docs should be cross-referenced.

- `openhands_sdk_doc_findings.md` → `openhands_sdk_findings.md`
  - Reason: The file aggregates findings and maps to questions, acting as a high-level overview (summary). It fits the 'agents' domain. The current name includes a generic suffix and is placed in docs root, making it orphaned. It should be renamed to a concise snake_case name without redundant suffixes.

- `design/project_management_dashboard.md` → `design/frontend/project_management_dashboard.md`
  - Reason: The document describes how the dashboard will be built, includes UI components, real‑time architecture, and integration points, which matches a design document. It focuses on the user‑facing dashboard, so the primary category is frontend. The filename already follows snake_case and resides in the design folder, so it is not orphaned. Status is set to Review as the document is ready for stakeholder review. No metadata fields are missing.

- `design/agent_lifecycle_management.md` → `design/agents/agent_lifecycle_management.md`
  - Reason: The document details architecture, components, and protocols, matching a design document. It focuses on agent lifecycle, fitting the 'agents' category. Filename follows snake_case and is descriptive, so no rename needed. No explicit metadata block is present, indicating missing Created, Status, and structured Purpose fields. The doc is current and not obsolete, so not archived. Location in docs/design is appropriate.

- `llm_service_usage.md` → `design/services/llm_service_guide.md`
  - Reason: The content is a step‑by‑step usage guide with code examples, configuration notes and best‑practice tips, fitting the 'guide' type. It focuses on the LLM service, so the category is 'services'. The filename should reflect the guide purpose without redundant suffixes; 'llm_service_guide' is concise and clear. The document appears complete and current, so status is Active. It resides in the top‑level docs folder, but guides are typically organized under a guides/services subdirectory, making it orphaned. No indication it is outdated, so it should not be archived. Several related docs (implementation, agent executor, config, schemas) should be cross‑referenced. Metadata fields are missing.

- `design/dependency_graph_implementation.md` → `design/services/dependency_graph_service.md`
  - Reason: The document describes the data model, edge types, and backend service implementation details, which aligns with a design specification. It belongs to the services domain. The current filename includes 'implementation' which mislabels a design doc, making it orphaned. Status 'Implementation Plan' maps to Draft. No outdated content, so not archived.

- `design/TESTING_AND_CONFIG_IMPROVEMENTS_SUMMARY.md` → `testing_and_configuration_summary.md`
  - Reason: The document provides a concise overview of changes, fitting the 'summary' type. Primary focus is on testing improvements, so category 'testing' is appropriate. Filename follows snake_case without redundant suffixes. Status indicates readiness for implementation, mapping to 'Approved'. It's placed in docs/design but summaries belong in a dedicated summary location, making it orphaned. No archival needed as content is current. Missing explicit 'Created' metadata field.

- `design/auth_system_implementation.md` → `design/auth/auth_system_plan.md`
  - Reason: The file contains architecture diagrams, phase‑by‑phase implementation steps and code snippets, which are characteristic of a design/specification document. It focuses on authentication, so the category is 'auth'. It resides in the design folder, matching its type, so it is not orphaned. The status header shows Draft. No explicit 'Purpose' metadata field is present, so that is flagged as missing. The suggested filename removes redundancy while keeping the plan context.

- `CRITICAL_MISSING_FEATURES.md` → `requirements/workflows/workflow_autonomy_requirements.md`
  - Reason: The document lists what must be built (features, components, effort) and prioritizes them, fitting the definition of a requirements document. The focus is on workflow automation and agent-based self‑healing, so the 'workflows' category is appropriate. It resides in the top‑level docs folder and is named in all caps, which violates the snake_case naming convention and location guidelines, making it orphaned. The content is current planning, not completed work, so it should remain active and not archived.

- `requirements/workflows/task_queue_management.md` → `requirements/workflows/task_queue.md`
  - Reason: The document contains REQ‑ prefixed items, a detailed data model, and no implementation details, indicating it is a requirements specification. It focuses on task queue behavior within multi‑agent workflows, matching the 'workflows' category. The current filename includes a redundant suffix; a concise 'task_queue.md' follows naming conventions. No status metadata is present, so status is inferred as Draft. Location aligns with its type, so it is not orphaned, and the content is current, so archiving is unnecessary. The parent multi‑agent orchestration requirements document is the primary related doc.

- `openhands_insights_and_prioritization.md` → `design/agents/openhands_insights_prioritization.md`
  - Reason: The document analyzes SDK behavior and recommends design/implementation priorities, fitting the 'design' type. It focuses on agent-related concerns, so category 'agents' is appropriate. Filename follows snake_case without redundant suffixes. No explicit status metadata, so default to Draft. Located in top-level docs, should reside under design or architecture, thus marked orphaned. Not outdated, so no archiving.

- `PHASE5_KICKOFF.md` → `design/agents/phase5_kickoff.md`
  - Reason: The document outlines actionable steps, ownership, and integration contracts for multiple agents, fitting a developer-facing guide. It belongs to the agents domain. The current filename is uppercase and located in the generic docs folder, making it orphaned. It is still relevant to the ongoing Phase 5 work, so it should remain active and be cross‑referenced with the detailed parallel plan.

- `implementation/ticket_tracking_implementation.md` → `design/services/ticket_tracking_implementation_guide.md`
  - Reason: The file details concrete implementation steps and code interfaces, matching a how‑to guide rather than a status log. It belongs to the services domain. The current location (docs/implementation) is inconsistent with its guide nature, so it is orphaned. The content is current and should remain active. It references the design document, which should be cross‑linked. Metadata fields for creation date and explicit purpose are absent.

- `design/monitoring_architecture.md` → `design/monitoring/monitoring_architecture.md`
  - Reason: The document details the technical design and architecture of the monitoring system, fitting the 'design' type. Its focus on monitoring components places it in the 'monitoring' category. The filename should be concise and snake_case; the current name is appropriate without redundant suffixes. No status metadata is present, so we infer a Draft status. The file resides in the correct 'design' folder, so it is not orphaned, and the content remains current, so no archiving is needed. Related documents are explicitly listed in the content.

- `requirements/workflows/validation_system.md` → `requirements/agents/validation_system.md`
  - Reason: The document lists REQ- codes and normative language, indicating a requirements document. It focuses on the validation agent workflow, fitting the 'agents' category. The filename follows snake_case without redundant suffixes. No status metadata is present, so default to Draft. Location under docs/requirements/workflows is appropriate, so not orphaned. No indication it is outdated, so not archived. Related documents include the parent orchestration requirements and likely design or other requirement docs for related services.

- `PHASE5_MEMORY_COMPLETE.md` → `implementation/memory/phase5_memory_implementation.md`
  - Reason: The file records what was built, tested, and delivered for Phase 5, matching an implementation log. It belongs to the memory domain. The current name PHASE5_MEMORY_COMPLETE.md is not snake_case and includes a phase label, so a snake_case name like phase5_memory_implementation is appropriate. It resides in the top-level docs folder, but implementation logs are usually under docs/implementation or docs/phase5, making it orphaned. The work is recent and still relevant, so it should stay active. Cross‑references include the README created for the memory feature and related design/architecture/requirements documents.

- `design/memory_system.md` → `design/memory/memory_system.md`
  - Reason: The document describes system architecture, component responsibilities, and API definitions, which aligns with a design specification. It focuses on the memory service, fitting the 'memory' category. The filename follows snake_case and is appropriately placed in docs/design. No explicit status or creation metadata is present, indicating missing metadata. The content is current and not obsolete, so archiving is unnecessary.

- `design/frontend_zustand_middleware_reference.md` → `design/frontend/zustand_middleware_reference.md`
  - Reason: The file contains detailed code implementations and usage instructions, fitting the definition of a guide. It belongs to the frontend domain. The current location in docs/design is inappropriate for a guide, making it orphaned. Status is set to Active as it appears ready for consumption.

- `parallel_work_streams.md` → `design/agents/parallel_work_streams.md`
  - Reason: The file outlines how to build parallel work streams, detailing interfaces, database changes, and coordination, which fits a design document. It focuses on agents, so category is agents. Status field shows Active Planning, mapping to Active. It's placed in the top-level docs folder, but design specs belong under docs/design/agents, making it orphaned. No outdated content, so not archived.

- `design/TEST_ORGANIZATION_PLAN.md` → `design/testing/test_organization_testmon.md.md`
  - Reason: The document outlines a detailed directory structure, migration plan, and integration steps, which describes how to build the testing organization – fitting the 'design' type. It focuses on testing concerns, so category is 'testing'. The current filename is uppercase and not snake_case, making it an orphaned/poorly named file. Suggested snake_case name reflects both test organization and testmon integration. Status field says 'Implementation Plan', which aligns with an active effort, thus marked as Active. No outdated content, so not archived. Related docs include configuration, implementation, guide, and architecture references.

- `DIAGNOSTIC_TRUE_GAPS.md` → `design/services/diagnostic_true_gaps.md`
  - Reason: The document lists missing components, effort estimates, and implementation steps, fitting a design specification. It focuses on services within the diagnostic system, but resides in the generic docs folder, making it orphaned. No explicit metadata is present, and the content appears draft-level planning.

- `chats/auth_system.md` → `design/auth/organization_auth.md`
  - Reason: The content describes system components, data models, and SQLAlchemy code, which aligns with a design document. It focuses on authentication and organization management, fitting the 'auth' category. No explicit status or purpose metadata is present, indicating a draft. The file resides in a chats folder, which is unrelated to design docs, making it orphaned.

- `agent_assignments_phase2.md` → `design/workflows/phase2_workflow.md`
  - Reason: The document details how the system should be built (state machine, services, DB schema) which aligns with a design document. It focuses on workflow services, fitting the 'workflows' category. The current location 'docs' is too generic; it belongs under design/workflows. The status label 'Ready for Planning' maps to a Draft stage. No indication that the work is completed, so it should not be archived. It lacks explicit Created and Purpose metadata fields.

- `design/result_submission.md` → `design/services/result_submission.md`
  - Reason: The document describes technical specifications, component responsibilities, and integration details, which aligns with a design document. It focuses on a service that supports workflow result handling, fitting the 'services' category. No explicit metadata block is present, and the content appears current, so it is not orphaned or ready for archiving.

- `design/diagnosis_agent.md` → `design/agents/diagnosis_agent.md`
  - Reason: The document details component responsibilities, architecture diagrams, and interfaces, which are characteristic of a design specification. It focuses on the Diagnosis Agent, an autonomous analysis service, fitting the 'agents' category. The file resides in the design folder, matching its type, and the current filename is appropriate. No explicit metadata block is present, indicating missing Created/Status/Purpose fields. The content appears current, so archiving is not needed.

- `design/frontend_architecture_shadcn_nextjs.md` → `design/frontend/frontend_architecture_shadcn_nextjs.md`
  - Reason: The document describes how the frontend should be built (architecture, component mapping, directory layout), fitting the definition of a design document. It belongs to the frontend domain. The filename is descriptive and follows snake_case without redundant suffixes. Status metadata uses a non-standard value, so 'Draft' is inferred. Location in docs/design is appropriate, and the content is current, so no archiving. Related docs are suggested for state management, directory structure, UI component mapping, and ADR for technology choice.

- `TICKETS_VS_TASKS.md` → `ticket_task_hierarchy.md`
  - Reason: The file provides a high‑level overview of concepts rather than detailed specifications, making it a summary. It discusses workflow concepts, fitting the 'workflows' category. The current uppercase filename and placement in the top‑level docs folder violate naming and organization conventions, so a snake_case name and placement under a workflow subdirectory are recommended. No indication it is outdated, and related docs on ticket lifecycle, task execution, and the task queue design should be cross‑referenced. Metadata headers are absent.

- `design/ticket_workflow.md` → `design/workflows/ticket_workflow.md.md`
  - Reason: The content describes technical specifications, component responsibilities, and state machine details, which aligns with a design document. It focuses on workflow orchestration, placing it in the 'workflows' category. The filename is appropriate for a design file, but the file resides directly under docs/design rather than a subfolder like docs/design/workflows, making it orphaned. No explicit metadata headers are present, so Created, Status, and Purpose are missing. The document is current and should remain active, not archived.

- `PHASE5_MEMORY_HANDOFF.md` → `implementation/memory/phase5_memory_handoff.md`
  - Reason: The file details completed work, test results, and handoff details, matching an implementation/completion log. It belongs to the memory domain. The current name PHASE5_MEMORY_HANDOFF.md is acceptable but not snake_case; a better name is phase5_memory_handoff.md. The status is production-ready, so it's active rather than archived. It's located in docs root, which is appropriate for a phase handoff summary, not orphaned.

- `PHASE5_ALL_SQUADS_INTEGRATED.md` → `implementation/integration/phase5_integration_completion.md`
  - Reason: The document records the completion of Phase 5 with test results and integration details, fitting the implementation log category. It focuses on integration of multiple squads, so the integration category is appropriate. The current filename is acceptable but can be more concise; a snake_case name without redundancy is suggested. The status reflects production readiness, mapping to 'Implemented'. It resides in the generic docs folder rather than an implementation subfolder, making it orphaned. The content remains relevant, so archiving is not needed. A purpose field is absent, indicating missing metadata.

- `PHASE5_PARALLEL_PLAN.md` → `design/services/phase5_parallel_plan.md`
  - Reason: The document specifies how to build advanced features (Guardian, Memory, Cost Tracking, Quality Gates) with detailed technical deliverables and migrations, fitting the design category. It focuses on services, so 'services' is appropriate. The current filename is uppercase and location is generic, making it orphaned. Status 'READY TO START' maps to Active. No explicit Purpose metadata is present.

- `design/frontend_components_scaffold.md` → `design/frontend/component_scaffold_guide.md`
  - Reason: The file contains ready‑to‑use component code, which is instructional rather than a specification, fitting the 'guide' type. It belongs to the frontend domain. The current location in docs/design is inappropriate for a guide, so it is orphaned. The status label 'Scaffold Document' maps to an active, usable guide. No required metadata fields are missing.

- `chats/deepgrok.md` → `archive/chat_logs/workflows/workflow_design_understanding.md`
  - Reason: The file is a chat export discussing workflow design, fitting the 'chat_log' type. It relates to workflow domain, so category is 'workflows'. The current location 'docs/chats' is not a standard place for design or summary docs, making it orphaned. The content serves as a high-level overview, so it could be treated as a summary; however, as a raw discussion it's best kept as a draft. No explicit status or purpose fields are present, so they are missing.

- `AUTH_SYSTEM_COMPLETE.md` → `implementation/auth/auth_system_complete.md`
  - Reason: The document details the final implementation state, test outcomes, and migration blockers, matching an implementation log. It focuses on authentication, so category is auth. Filename follows snake_case and conveys completion. Status aligns with 'Implemented'. It's stored at the top-level docs folder rather than an implementation subdirectory, making it orphaned. No need to archive yet as migration is pending. Related requirement and design docs are referenced.

- `requirements/workflows/diagnosis_agent.md` → `requirements/agents/diagnosis_agent.md`
  - Reason: The document defines REQ- prefixed requirements for a specific agent, making it a requirements document. Its focus on agent behavior places it in the 'agents' category. The current location under workflows is inappropriate; agents have their own category. No explicit status metadata is present, and the revision history suggests a draft. It is recent and not obsolete, so should not be archived. Related docs are those referenced in the 'Related Documents' section.

- `DOCUMENTATION_STANDARDS.md` → `design/documentation/documentation_standards.md`
  - Reason: The file provides standards and guidelines, which fits the 'guide' type. It does not describe a specific feature, so the category is documentation. The current filename is uppercase and not snake_case, so a snake_case name like 'documentation_standards.md' is recommended. The metadata includes a non‑standard status value ('Standard') which should be mapped to an allowed status such as 'Active'. The document is correctly placed at the repo root (STANDARDS.md) but the naming violates conventions, marking it as orphaned/potentially misnamed. It is a current standard, not outdated, so it should not be archived. Missing typical metadata fields (Updated, Authors, Reviewers, Related) are noted. Cross‑references to the main README and architecture index are useful for navigation.

- `requirements/integration/mcp_servers.md` → `requirements/integration/mcp_server.md`
  - Reason: The document contains REQ- prefixed items, making it a requirements specification. Its focus is on MCP server integration, fitting the 'integration' category. The filename should be singular and omit redundant suffixes; the directory already conveys the requirements context. The revision history shows an initial draft, so status is Draft. Placement is correct, but the plural filename is suboptimal, marking it as orphaned/poorly named. No archival need as the content is current. Several related requirement documents are referenced and should be cross‑linked. Metadata fields typical for our docs (Created, Status, Purpose) are absent.

- `IMPLEMENTATION_PLAN_REMAINING_ITEMS.md` → `implementation/services/implementation_plan_remaining_items.md`
  - Reason: The document details concrete implementation steps, code snippets, and effort estimates, fitting the 'implementation' type. It spans multiple functional areas but primarily concerns service implementations, so 'services' category is appropriate. The filename should be snake_case without redundant terms. Status 'Planning' maps to a Draft stage. Being placed directly in the docs root makes it orphaned; it belongs in an implementation or plans subdirectory. No creation date or explicit purpose field is present, so those metadata are missing.

- `agent_spawn_prompt_phase2_stream_e.md` → `design/workflows/phase2_stream_e_state_machine.md`
  - Reason: The content specifies how to build (technical spec, test cases, code structure) rather than just what to build, fitting a design document. It focuses on workflow/state‑machine logic, so the 'workflows' category is appropriate. The current filename and location are generic and misplaced; a concise snake_case name under a design folder is recommended. Metadata headers are absent, indicating missing fields.

## Files Needing Metadata

- `opnhands-bot-questions.md`: Missing Created, Status, Purpose

- `multi_agent_orchestration.md`: Missing Created, Status, Purpose

- `frontend_pages_scaffold.md`: Missing Status

- `PYTEST_TESTMON_GUIDE.md`: Missing Status

- `agent_job_prompt.md`: Missing Created, Status, Purpose

- `fault_tolerance.md`: Missing Created, Status, Purpose

- `monitoring_architecture.md`: Missing Created, Status, Purpose

- `PHASE4_PARALLEL_PLAN.md`: Missing Purpose

- `DIAGNOSTIC_SYSTEM_ANSWER.md`: Missing Created, Status, Purpose

- `lifecycle_management.md`: Missing Created, Status, Purpose

- `fault_tolerance.md`: Missing Created, Status, Purpose

- `ticket_human_approval.md`: Missing Created, Status, Purpose

- `DIAGNOSTIC_SYSTEM_GAP_ANALYSIS.md`: Missing Created

- `AUTH_SYSTEM_DEPLOYED.md`: Missing Created, Purpose

- `PHASE5_SCHEMA_FIX_NEEDED.md`: Missing Created, Purpose

- `parallel_design_jobs.md`: Missing Created, Status, Purpose

- `ticket_tracking_postgres.md`: Missing Created, Purpose

- `task_queue_management.md`: Missing Created, Status, Purpose

- `validation_system.md`: Missing Created, Status, Purpose

- `mcp_server_integration.md`: Missing Created, Status, Purpose

- `REQUIREMENTS_COMPLIANCE_ANALYSIS.md`: Missing Created, Purpose

- `ticket_human_approval.md`: Missing Created, Status, Purpose

- `DIAGNOSTIC_FINAL_ANSWER.md`: Missing Created, Status, Purpose

- `auth_system_status.md`: Missing Created, Purpose

- `CONFIG_MIGRATION_GUIDE.md`: Missing Status

- `COMPLETE_ORGANIZATION_SOLUTION.md`: Missing Created

- `claude_code_agent_prompt_phase2_streams_fgh.md`: Missing Created, Status

- `foundation_and_smallest_runnable.md`: Missing Status

- `openhands_integration_questions.md`: Missing Created, Status, Purpose

- `phase3_parallel_agent_prompt.md`: Missing Created, Status, Purpose

- `PHASE5_CONTEXT2_FINAL_SUMMARY.md`: Missing Created, Purpose

- `ARCHITECTURE_COMPARISON.md`: Missing Created, Status, Purpose

- `workspace_isolation_system.md`: Missing Created, Status, Purpose

- `DIAGNOSTIC_SYSTEM_COMPLETE.md`: Missing Created, Purpose

- `HEPHAESTUS_ENHANCEMENTS.md`: Missing Purpose

- `INTELLIGENT_MONITORING_TESTING.md`: Missing Created, Status, Purpose

- `multi_agent_orchestration.md`: Missing Created, Status, Purpose

- `openhands_sdk_doc_findings.md`: Missing Created, Status, Purpose

- `agent_lifecycle_management.md`: Missing Created, Status, Purpose

- `llm_service_usage.md`: Missing Created, Status, Purpose

- `TESTING_AND_CONFIG_IMPROVEMENTS_SUMMARY.md`: Missing Created

- `auth_system_implementation.md`: Missing Purpose

- `CRITICAL_MISSING_FEATURES.md`: Missing Created, Status, Purpose

- `task_queue_management.md`: Missing Created, Status, Purpose

- `PHASE5_KICKOFF.md`: Missing Created, Status, Purpose

- `ticket_tracking_implementation.md`: Missing Created, Purpose

- `monitoring_architecture.md`: Missing Created, Status, Purpose

- `validation_system.md`: Missing Created, Status, Purpose

- `memory_system.md`: Missing Created, Status, Purpose

- `DIAGNOSTIC_TRUE_GAPS.md`: Missing Created, Status, Purpose

- `auth_system.md`: Missing Status, Purpose

- `agent_assignments_phase2.md`: Missing Created, Purpose

- `result_submission.md`: Missing Created, Status, Purpose

- `diagnosis_agent.md`: Missing Created, Status, Purpose

- `TICKETS_VS_TASKS.md`: Missing Created, Status, Purpose

- `ticket_workflow.md`: Missing Created, Status, Purpose

- `PHASE5_ALL_SQUADS_INTEGRATED.md`: Missing Purpose

- `PHASE5_PARALLEL_PLAN.md`: Missing Purpose

- `memory_system.md`: Missing Created, Status, Purpose

- `deepgrok.md`: Missing Status, Purpose

- `AUTH_SYSTEM_COMPLETE.md`: Missing Created, Purpose

- `diagnosis_agent.md`: Missing Created, Status, Purpose

- `DOCUMENTATION_STANDARDS.md`: Missing Updated, Authors, Reviewers, Related, Status (value not in allowed set)

- `result_submission.md`: Missing Created, Status, Purpose

- `mcp_servers.md`: Missing Created, Status, Purpose

- `IMPLEMENTATION_PLAN_REMAINING_ITEMS.md`: Missing Created, Purpose

- `agent_spawn_prompt_phase2_stream_e.md`: Missing Created, Status, Purpose

## Files to Archive

- `phase4_parallel_agent_prompt.md`
  - Reason: The file outlines how to build (design) four agents, their scopes, dependencies, tests, and hand‑offs, fitting the design document type. It belongs to the agents/monitoring domain. The current generic name and top‑level location make it orphaned; it should live under docs/design/agents. As it describes a completed Phase 4 effort, archiving is appropriate. Related docs are those covering metrics, alerts, watchdog policies, observability instrumentation, and the preceding Phase 3 deliverables.
