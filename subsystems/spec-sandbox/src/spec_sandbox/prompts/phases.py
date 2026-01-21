"""Phase-specific prompts for spec-driven development.

Each phase has a detailed prompt that guides the Claude Agent to produce
high-quality structured output with YAML frontmatter and proper formatting.

Phases:
- EXPLORE: Analyze codebase AND gather feature requirements through discovery
- PRD: Create Product Requirements Document with goals, user stories, success metrics
- REQUIREMENTS: Generate EARS-format requirements with YAML frontmatter
- DESIGN: Create architecture design with API specs and data models
- TASKS: Break down into tickets (TKT-NNN) and tasks (TSK-NNN)
- SYNC: Validate traceability and generate coverage matrix

Output Directory: All artifacts go in `.omoi_os/`
"""

from spec_sandbox.schemas.spec import SpecPhase

# =============================================================================
# EXPLORE PHASE - Codebase Analysis + Discovery Questions
# =============================================================================

EXPLORE_PROMPT = """You are analyzing a codebase and gathering requirements for a new feature.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Your Task

This phase has TWO parts:

### Part 1: Codebase Exploration

Explore the codebase to understand:
1. **Project Structure**: Directory layout, main entry points, configuration files
2. **Architecture Patterns**: How code is organized (MVC, microservices, monolith, etc.)
3. **Key Dependencies**: Major libraries and frameworks used
4. **Relevant Files**: Files most relevant to the spec requirements
5. **Existing Patterns**: Coding patterns, naming conventions, test structure

Use the Read, Glob, and Grep tools to explore the codebase thoroughly.

### Part 2: Discovery Questions (Critical!)

Based on the spec description, formulate 5-15 discovery questions in these categories:

**Problem & Value (2-3 questions)**
- What specific problem does this solve? What pain exists today?
- What happens if we DON'T build this?
- How will we measure success? What metrics matter?

**Users & Journeys (2-3 questions)**
- Who are the primary users? Secondary?
- What's the happy path user journey?
- What are the edge cases and error scenarios?

**Scope & Boundaries (2-3 questions)**
- What is explicitly IN scope?
- What is explicitly OUT of scope? (Very important!)
- Are there existing features this overlaps with?

**Technical Context (3-5 questions)**
- What existing systems/services will this integrate with?
- What data does this need? Where does it come from?
- Are there performance requirements (latency, throughput, scale)?
- What security/privacy considerations apply?
- Are there any hard technical constraints?

**Trade-offs & Risks (2-3 questions)**
- Are there multiple valid approaches? Which should we explore?
- What could go wrong? What are the risks?
- What's the timeline/priority?

## Required Output Format

When complete, you MUST write a JSON file with this structure:

```json
{{
    "codebase_summary": "Brief overview of the codebase architecture (2-3 sentences)",
    "project_type": "Type of project (e.g., 'Next.js 15 + FastAPI backend', 'Python CLI tool')",
    "tech_stack": ["Python 3.11", "FastAPI", "PostgreSQL", "Redis", "etc."],
    "structure": {{
        "frontend": "frontend/src/",
        "backend": "backend/omoi_os/",
        "api_routes": "backend/omoi_os/api/routes/",
        "models": "backend/omoi_os/models/",
        "services": "backend/omoi_os/services/"
    }},
    "key_files": [
        {{"path": "relative/path/to/file.py", "purpose": "Why this file matters for the feature"}},
        {{"path": "another/important/file.ts", "purpose": "Component that will need modification"}}
    ],
    "relevant_patterns": [
        {{
            "pattern": "Repository Pattern",
            "description": "Data access through repository classes",
            "files": ["services/user_repository.py", "services/task_repository.py"]
        }},
        {{
            "pattern": "Service Layer",
            "description": "Business logic in service classes",
            "files": ["services/user_service.py"]
        }}
    ],
    "existing_models": [
        {{"name": "User", "file": "models/user.py", "fields": ["id", "email", "name"]}},
        {{"name": "Task", "file": "models/task.py", "fields": ["id", "title", "status"]}}
    ],
    "conventions": {{
        "naming": "snake_case for backend, camelCase for frontend",
        "testing": "pytest for backend, vitest for frontend",
        "patterns": ["Repository pattern", "Service layer", "Pydantic schemas"]
    }},
    "entry_points": ["main.py", "api/main.py"],
    "test_structure": "Tests in tests/ directory, pytest fixtures in conftest.py",
    "discovery_questions": [
        {{
            "category": "Problem & Value",
            "questions": [
                "What specific problem does this feature solve?",
                "What happens if we don't build this?"
            ]
        }},
        {{
            "category": "Users & Journeys",
            "questions": [
                "Who are the primary users of this feature?",
                "What's the expected user journey?"
            ]
        }},
        {{
            "category": "Scope & Boundaries",
            "questions": [
                "What is explicitly IN scope for this feature?",
                "What is explicitly OUT of scope?"
            ]
        }},
        {{
            "category": "Technical Context",
            "questions": [
                "What existing services will this integrate with?",
                "Are there performance requirements?"
            ]
        }},
        {{
            "category": "Trade-offs & Risks",
            "questions": [
                "What are the main risks?",
                "Are there multiple valid implementation approaches?"
            ]
        }}
    ],
    "feature_summary": {{
        "name": "feature-name-kebab-case",
        "one_liner": "Brief description of what this feature does",
        "problem_statement": "2-3 sentences about the pain point this solves",
        "scope_in": ["Feature A", "Feature B", "Integration with X"],
        "scope_out": ["Future enhancement Y", "Out of scope Z"],
        "technical_constraints": ["Must use existing auth system", "PostgreSQL only"],
        "risks_identified": ["Risk 1", "Risk 2"],
        "success_metrics": ["Metric 1", "Metric 2"]
    }},
    "related_to_feature": [
        {{
            "name": "EventBusService",
            "file": "services/event_bus.py",
            "relevance": "Will need to publish events for this feature"
        }}
    ],
    "notes": "Any important observations for implementation"
}}
```

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# PRD PHASE - Product Requirements Document
# =============================================================================

PRD_PROMPT = """You are creating a Product Requirements Document (PRD) for a feature.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Codebase Context (from Explore phase)
{explore_context}

## Your Task

Create a comprehensive Product Requirements Document that:
1. Defines the product vision and goals
2. Identifies users and their needs
3. Documents user stories with acceptance criteria
4. Establishes success metrics
5. Outlines scope and boundaries

This PRD will be used to generate formal EARS-format requirements in the next phase.

### PRD Sections

#### 1. Overview
- **Feature Name**: Clear, concise name
- **One-Liner**: Single sentence describing the feature
- **Problem Statement**: What pain point does this solve?
- **Solution Summary**: How does this feature solve the problem?

#### 2. Goals & Success Metrics
Define measurable outcomes:
- **Primary Goal**: The main thing this feature achieves
- **Secondary Goals**: Additional benefits
- **Success Metrics**: How we'll know if this is successful
  - Example: "Reduce manual intervention by 50%"
  - Example: "Support 1000 webhook deliveries/minute"
  - Example: "< 500ms p95 latency"

#### 3. Users & Personas
Who uses this feature?
- **Primary Users**: Who benefits most?
- **Secondary Users**: Who else uses it?
- **Persona Details**: Brief persona descriptions with needs

#### 4. User Stories
Use this format:
```
US-NNN: As a [role], I want [capability] so that [benefit].

Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

Include 5-15 user stories covering:
- Happy path scenarios
- Error handling scenarios
- Edge cases
- Administrative/config scenarios

#### 5. Scope Definition
Be explicit about boundaries:

**In Scope**:
- Feature A
- Integration with X
- Basic UI for Y

**Out of Scope** (Critical!):
- Feature B (future phase)
- Integration with Z (not needed)
- Mobile support (later)

**Dependencies**:
- Existing service X must be available
- Database Y must support feature Z

#### 6. Assumptions & Constraints
- **Assumptions**: Things we believe to be true
- **Technical Constraints**: Platform, language, infrastructure limits
- **Business Constraints**: Timeline, budget, regulatory

#### 7. Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Risk 1 | High | Medium | Mitigation strategy |

#### 8. Open Questions
List questions that need answers before implementation:
- [ ] Question 1?
- [ ] Question 2?

## Required Output Format

When complete, you MUST write a JSON file with this structure:

```json
{{
    "prd_version": "1.0",
    "feature_name": "webhook-notifications",
    "overview": {{
        "one_liner": "Enable external systems to receive real-time event notifications via webhooks",
        "problem_statement": "Currently, external systems must poll our API to detect changes, causing delays and unnecessary load. Teams need real-time notifications when events occur.",
        "solution_summary": "Implement a webhook delivery system that pushes events to registered endpoints in real-time with retry logic and delivery tracking."
    }},
    "goals": {{
        "primary": "Enable real-time event delivery to external systems",
        "secondary": [
            "Reduce API polling load by 80%",
            "Provide webhook management UI for end users"
        ],
        "success_metrics": [
            {{
                "metric": "Webhook delivery success rate",
                "target": ">= 99.5%",
                "measurement": "Successful deliveries / Total attempts"
            }},
            {{
                "metric": "P95 delivery latency",
                "target": "< 500ms",
                "measurement": "Time from event to webhook delivery"
            }},
            {{
                "metric": "API polling reduction",
                "target": ">= 80% reduction",
                "measurement": "Compare polling before/after launch"
            }}
        ]
    }},
    "users": {{
        "primary": {{
            "role": "Integration Developer",
            "description": "Developers building integrations with our platform",
            "needs": ["Real-time event notifications", "Reliable delivery", "Easy webhook management"]
        }},
        "secondary": [
            {{
                "role": "Platform Admin",
                "description": "Internal team managing webhook configurations",
                "needs": ["Monitor delivery health", "Debug failed deliveries"]
            }}
        ]
    }},
    "user_stories": [
        {{
            "id": "US-001",
            "role": "Integration Developer",
            "want": "register a webhook endpoint for specific event types",
            "benefit": "I only receive events I care about",
            "priority": "must",
            "acceptance_criteria": [
                "Can specify endpoint URL",
                "Can select which event types to subscribe to",
                "Webhook is validated before activation"
            ]
        }},
        {{
            "id": "US-002",
            "role": "Integration Developer",
            "want": "receive events in a consistent JSON format",
            "benefit": "I can parse all events with the same code",
            "priority": "must",
            "acceptance_criteria": [
                "All events have timestamp, event_type, payload",
                "Payload structure is documented",
                "Events include idempotency key"
            ]
        }},
        {{
            "id": "US-003",
            "role": "Integration Developer",
            "want": "automatic retries for failed deliveries",
            "benefit": "temporary outages don't cause data loss",
            "priority": "must",
            "acceptance_criteria": [
                "Retries with exponential backoff",
                "Maximum 5 retry attempts",
                "Failed deliveries are logged"
            ]
        }},
        {{
            "id": "US-004",
            "role": "Platform Admin",
            "want": "view webhook delivery history and status",
            "benefit": "I can debug integration issues",
            "priority": "should",
            "acceptance_criteria": [
                "Shows recent delivery attempts",
                "Shows success/failure status",
                "Shows response codes and latency"
            ]
        }},
        {{
            "id": "US-005",
            "role": "Integration Developer",
            "want": "verify webhook authenticity",
            "benefit": "I know events are from the real source",
            "priority": "must",
            "acceptance_criteria": [
                "Webhooks include signature header",
                "Documentation for signature verification",
                "Shared secret per webhook endpoint"
            ]
        }}
    ],
    "scope": {{
        "in_scope": [
            "Webhook registration and management API",
            "Event delivery with retry logic",
            "Signature-based authentication",
            "Delivery history and monitoring",
            "Support for task.*, workflow.* events"
        ],
        "out_of_scope": [
            "Webhook UI in frontend (future phase)",
            "Fan-out to multiple endpoints per event",
            "Webhook transformation/filtering rules",
            "OAuth2 authentication for webhooks"
        ],
        "dependencies": [
            "EventBusService must emit events",
            "Async task queue (Taskiq) for delivery",
            "PostgreSQL for webhook storage"
        ]
    }},
    "assumptions": [
        "External endpoints will respond within 30 seconds",
        "Event volume will not exceed 10,000/minute initially",
        "Users can manage their own webhook secrets"
    ],
    "constraints": {{
        "technical": [
            "Must integrate with existing EventBusService",
            "Must use PostgreSQL for storage",
            "Must support async delivery via Taskiq"
        ],
        "business": [
            "Must launch within Q1",
            "Cannot break existing API contracts"
        ]
    }},
    "risks": [
        {{
            "risk": "Webhook endpoints are slow or unreliable",
            "impact": "high",
            "likelihood": "medium",
            "mitigation": "Implement aggressive timeouts and circuit breaker"
        }},
        {{
            "risk": "Event volume exceeds capacity",
            "impact": "high",
            "likelihood": "low",
            "mitigation": "Design for horizontal scaling, add rate limiting"
        }},
        {{
            "risk": "Security: webhook secret leak",
            "impact": "high",
            "likelihood": "low",
            "mitigation": "Secrets encrypted at rest, rotation API"
        }}
    ],
    "open_questions": [
        "Should we support webhook batching (multiple events per request)?",
        "What's the maximum payload size we should support?",
        "Do we need webhook versioning for breaking changes?"
    ],
    "related_features": [
        {{
            "name": "EventBusService",
            "relationship": "depends_on",
            "notes": "PRD relies on events being published"
        }},
        {{
            "name": "Task Management",
            "relationship": "event_source",
            "notes": "Will emit task.created, task.completed events"
        }}
    ],
    "revision_history": [
        {{
            "version": "1.0",
            "date": "2024-01-15",
            "author": "spec-sandbox",
            "changes": "Initial PRD"
        }}
    ]
}}
```

### Quality Checklist

Before submitting, verify:
- [ ] Problem statement is clear and compelling
- [ ] Goals are measurable with specific targets
- [ ] User stories cover happy path AND edge cases
- [ ] Scope clearly defines what's IN and OUT
- [ ] All open questions are documented
- [ ] Risks have mitigations identified

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# REQUIREMENTS PHASE - EARS Format with YAML Frontmatter
# =============================================================================

REQUIREMENTS_PROMPT = """You are generating structured requirements from a spec description and PRD.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Codebase Context (from Explore phase)
{explore_context}

## PRD Context (from PRD phase)
{prd_context}

## Your Task

Translate the PRD user stories and goals into formal EARS-format requirements.
Each user story should map to one or more requirements.

Generate structured requirements using the **EARS (Easy Approach to Requirements Syntax)** format.

### EARS Format Patterns

Use these patterns for requirements:

1. **Ubiquitous (always active)**:
   `THE SYSTEM SHALL [action/behavior].`

2. **Event-driven (triggered by event)**:
   `WHEN [trigger/event], THE SYSTEM SHALL [action/behavior].`

3. **State-driven (while in state)**:
   `WHILE [state/condition], THE SYSTEM SHALL [action/behavior].`

4. **Optional (if condition)**:
   `IF [condition], THEN THE SYSTEM SHALL [action/behavior].`

5. **Complex (combination)**:
   `WHILE [state], WHEN [trigger], THE SYSTEM SHALL [action/behavior].`

### Normative Language

Use these keywords consistently:
- **SHALL** / **MUST**: Mandatory requirement (use for all core functionality)
- **SHOULD**: Recommended but not mandatory
- **MAY**: Optional feature
- **SHALL NOT** / **MUST NOT**: Prohibited behavior

### Requirement Categories

Organize requirements into:
- **Functional (FUNC)**: What the system does
- **Performance (PERF)**: Speed, throughput, scalability
- **Security (SEC)**: Authentication, authorization, data protection
- **Usability (USE)**: User experience requirements
- **Reliability (REL)**: Availability, fault tolerance
- **Constraint (CON)**: Technical or business constraints

### ID Convention

Use this format: `REQ-{{FEATURE}}-{{CATEGORY}}-{{NNN}}`

Examples:
- `REQ-WEBHOOK-FUNC-001` - First functional requirement for webhook feature
- `REQ-WEBHOOK-SEC-001` - First security requirement
- `REQ-WEBHOOK-PERF-001` - First performance requirement

## Required Output Format

When complete, you MUST write a JSON file with this structure:

```json
{{
    "feature_name": "webhook-notifications",
    "requirements": [
        {{
            "id": "REQ-WEBHOOK-FUNC-001",
            "title": "Webhook Subscription Creation",
            "type": "functional",
            "category": "API",
            "priority": "HIGH",
            "text": "WHEN a user submits a valid webhook subscription request, THE SYSTEM SHALL create a new subscription record and return the subscription ID within 500ms.",
            "acceptance_criteria": [
                "Subscription is persisted to database",
                "Response includes subscription ID",
                "Response time is under 500ms for P99",
                "Invalid requests return 400 with descriptive error"
            ],
            "dependencies": [],
            "notes": "Integrates with existing EventBusService"
        }},
        {{
            "id": "REQ-WEBHOOK-FUNC-002",
            "title": "Webhook Event Delivery",
            "type": "functional",
            "category": "Integration",
            "priority": "HIGH",
            "text": "WHEN an event occurs that matches a subscription's event filter, THE SYSTEM SHALL deliver a webhook payload to the subscription URL within 30 seconds.",
            "acceptance_criteria": [
                "Payload is delivered via HTTP POST",
                "Delivery includes HMAC signature header",
                "Failed deliveries are retried up to 3 times",
                "Delivery attempts are logged"
            ],
            "dependencies": ["REQ-WEBHOOK-FUNC-001"],
            "notes": "Uses exponential backoff for retries"
        }},
        {{
            "id": "REQ-WEBHOOK-SEC-001",
            "title": "Webhook Payload Signing",
            "type": "security",
            "category": "Security",
            "priority": "HIGH",
            "text": "THE SYSTEM SHALL sign all webhook payloads using HMAC-SHA256 with the subscription's secret key.",
            "acceptance_criteria": [
                "X-Signature header is included in all deliveries",
                "Signature uses HMAC-SHA256 algorithm",
                "Secret is stored encrypted at rest",
                "Signature can be verified by recipient"
            ],
            "dependencies": ["REQ-WEBHOOK-FUNC-002"],
            "notes": "Standard webhook security practice"
        }},
        {{
            "id": "REQ-WEBHOOK-PERF-001",
            "title": "Webhook Throughput",
            "type": "performance",
            "category": "Performance",
            "priority": "MEDIUM",
            "text": "THE SYSTEM SHALL support delivery of at least 1000 webhook events per minute without degradation.",
            "acceptance_criteria": [
                "P99 delivery latency under 5 seconds at 1000 events/min",
                "No message loss under load",
                "Graceful degradation if limits exceeded"
            ],
            "dependencies": [],
            "notes": "Initial capacity target, can scale later"
        }}
    ],
    "assumptions": [
        "External webhook endpoints are HTTP/HTTPS accessible",
        "Subscribers are responsible for idempotent handling",
        "Event payload size is under 1MB"
    ],
    "out_of_scope": [
        "Webhook management UI (API only for now)",
        "GraphQL subscription support",
        "Real-time websocket delivery"
    ],
    "open_questions": [
        "Should we support custom headers in webhook requests?",
        "What's the retention period for delivery logs?"
    ],
    "traceability": {{
        "prd_sections": ["User Stories #1", "User Stories #2"],
        "design_components": ["WebhookService", "DeliveryService"]
    }}
}}
```

### Quality Checklist

Before finalizing, verify:
- [ ] Every requirement uses EARS format (WHEN/SHALL pattern)
- [ ] Every requirement has 2+ acceptance criteria
- [ ] Every requirement has a unique ID following the convention
- [ ] Requirements use normative language (SHALL, SHOULD, MAY)
- [ ] Dependencies between requirements are documented
- [ ] Assumptions and out-of-scope items are listed

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# DESIGN PHASE - Architecture with API Specs and Data Models
# =============================================================================

DESIGN_PROMPT = """You are creating an architecture design based on requirements.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Codebase Context (from Explore phase)
{explore_context}

## Requirements (from Requirements phase)
{requirements_context}

## Your Task

Design the architecture to satisfy all requirements while:
- Following existing codebase patterns
- Minimizing changes to existing code
- Maintaining separation of concerns
- Ensuring testability

## Design Components

### 1. Architecture Overview
Provide a high-level description and component diagram showing how pieces fit together.

### 2. API Endpoints (Critical!)
Define complete API specifications with:
- HTTP method and path
- Request/response schemas
- Authentication requirements
- Error responses

### 3. Data Models (Critical!)
Define database models with:
- Table name
- All fields with types
- Constraints (primary key, foreign key, unique, not null)
- Indexes
- Relationships

### 4. Component Responsibilities
Define each component's:
- Name and type (service, repository, controller, etc.)
- Single responsibility
- Dependencies
- Interface methods

## Required Output Format

When complete, you MUST write a JSON file with this structure:

```json
{{
    "feature_name": "webhook-notifications",
    "architecture_overview": "The webhook system integrates with the existing EventBusService to capture events and deliver them to external HTTP endpoints. It consists of three main components: WebhookSubscriptionService (manages subscriptions), WebhookDeliveryService (handles HTTP delivery with retries), and WebhookNotificationService (bridges EventBus to delivery).",
    "architecture_diagram": "EventBus -> WebhookNotificationService -> WebhookDeliveryService -> External URL\\n                                    |                          |\\n                              SubscriptionService          DeliveryLog",
    "components": [
        {{
            "name": "WebhookSubscriptionService",
            "type": "service",
            "file_path": "omoi_os/services/webhook_subscription.py",
            "responsibility": "Manages webhook subscription CRUD operations and validation",
            "interfaces": [
                {{
                    "method": "create_subscription",
                    "inputs": {{"url": "str", "events": "list[str]", "secret": "str"}},
                    "outputs": {{"subscription": "WebhookSubscription"}},
                    "description": "Creates a new webhook subscription"
                }},
                {{
                    "method": "get_subscriptions_for_event",
                    "inputs": {{"event_type": "str"}},
                    "outputs": {{"subscriptions": "list[WebhookSubscription]"}},
                    "description": "Returns all active subscriptions for an event type"
                }},
                {{
                    "method": "delete_subscription",
                    "inputs": {{"subscription_id": "UUID"}},
                    "outputs": {{"success": "bool"}},
                    "description": "Soft-deletes a subscription"
                }}
            ],
            "dependencies": ["WebhookSubscriptionRepository", "DatabaseService"]
        }},
        {{
            "name": "WebhookDeliveryService",
            "type": "service",
            "file_path": "omoi_os/services/webhook_delivery.py",
            "responsibility": "Handles HTTP delivery of webhook payloads with retry logic",
            "interfaces": [
                {{
                    "method": "deliver",
                    "inputs": {{"subscription": "WebhookSubscription", "event_type": "str", "payload": "dict"}},
                    "outputs": {{"delivery": "WebhookDelivery"}},
                    "description": "Delivers webhook with retry logic and signature"
                }},
                {{
                    "method": "_generate_signature",
                    "inputs": {{"payload": "bytes", "secret": "str"}},
                    "outputs": {{"signature": "str"}},
                    "description": "Generates HMAC-SHA256 signature for payload"
                }}
            ],
            "dependencies": ["httpx", "WebhookDeliveryRepository"]
        }},
        {{
            "name": "WebhookNotificationService",
            "type": "service",
            "file_path": "omoi_os/services/webhook_notification.py",
            "responsibility": "Bridges EventBusService to webhook delivery",
            "interfaces": [
                {{
                    "method": "handle_event",
                    "inputs": {{"event": "Event"}},
                    "outputs": {{"deliveries": "list[WebhookDelivery]"}},
                    "description": "Handles an event and triggers webhook deliveries"
                }}
            ],
            "dependencies": ["EventBusService", "WebhookSubscriptionService", "WebhookDeliveryService"]
        }}
    ],
    "data_models": [
        {{
            "name": "WebhookSubscription",
            "table_name": "webhook_subscriptions",
            "description": "Stores webhook subscription configurations",
            "fields": {{
                "id": "UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "project_id": "UUID NOT NULL REFERENCES projects(id)",
                "url": "VARCHAR(2048) NOT NULL",
                "secret": "VARCHAR(256) NOT NULL",
                "events": "TEXT[] NOT NULL",
                "is_active": "BOOLEAN DEFAULT true",
                "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
                "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
                "deleted_at": "TIMESTAMP WITH TIME ZONE"
            }},
            "indexes": [
                "CREATE INDEX idx_webhook_sub_project ON webhook_subscriptions(project_id)",
                "CREATE INDEX idx_webhook_sub_events ON webhook_subscriptions USING GIN(events)",
                "CREATE INDEX idx_webhook_sub_active ON webhook_subscriptions(is_active) WHERE is_active = true"
            ],
            "relationships": [
                "belongs_to Project (project_id)",
                "has_many WebhookDelivery"
            ]
        }},
        {{
            "name": "WebhookDelivery",
            "table_name": "webhook_deliveries",
            "description": "Tracks individual webhook delivery attempts",
            "fields": {{
                "id": "UUID PRIMARY KEY DEFAULT gen_random_uuid()",
                "subscription_id": "UUID NOT NULL REFERENCES webhook_subscriptions(id)",
                "event_type": "VARCHAR(100) NOT NULL",
                "payload": "JSONB NOT NULL",
                "status": "VARCHAR(20) NOT NULL DEFAULT 'pending'",
                "attempts": "INTEGER DEFAULT 0",
                "last_attempt_at": "TIMESTAMP WITH TIME ZONE",
                "response_status": "INTEGER",
                "response_body": "TEXT",
                "error_message": "TEXT",
                "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"
            }},
            "indexes": [
                "CREATE INDEX idx_webhook_del_sub ON webhook_deliveries(subscription_id)",
                "CREATE INDEX idx_webhook_del_status ON webhook_deliveries(status)",
                "CREATE INDEX idx_webhook_del_created ON webhook_deliveries(created_at)"
            ],
            "relationships": [
                "belongs_to WebhookSubscription (subscription_id)"
            ]
        }}
    ],
    "api_endpoints": [
        {{
            "method": "POST",
            "path": "/api/v1/webhooks",
            "description": "Create a new webhook subscription",
            "auth_required": true,
            "request_schema": {{
                "url": "string (required, valid URL)",
                "events": "array of strings (required, event types to subscribe to)",
                "secret": "string (optional, auto-generated if not provided)"
            }},
            "response_schema": {{
                "id": "uuid",
                "url": "string",
                "events": "array",
                "is_active": "boolean",
                "created_at": "timestamp"
            }},
            "error_responses": {{
                "400": "Validation error (invalid URL, empty events)",
                "401": "Unauthorized",
                "409": "Subscription already exists for this URL"
            }}
        }},
        {{
            "method": "GET",
            "path": "/api/v1/webhooks",
            "description": "List all webhook subscriptions for the project",
            "auth_required": true,
            "query_params": {{
                "is_active": "boolean (optional, filter by active status)",
                "limit": "integer (optional, default 50)",
                "offset": "integer (optional, default 0)"
            }},
            "response_schema": {{
                "items": "array of WebhookSubscription",
                "total": "integer",
                "limit": "integer",
                "offset": "integer"
            }},
            "error_responses": {{
                "401": "Unauthorized"
            }}
        }},
        {{
            "method": "GET",
            "path": "/api/v1/webhooks/{{id}}",
            "description": "Get a specific webhook subscription",
            "auth_required": true,
            "path_params": ["id"],
            "response_schema": {{
                "id": "uuid",
                "url": "string",
                "events": "array",
                "is_active": "boolean",
                "created_at": "timestamp",
                "updated_at": "timestamp"
            }},
            "error_responses": {{
                "401": "Unauthorized",
                "404": "Subscription not found"
            }}
        }},
        {{
            "method": "DELETE",
            "path": "/api/v1/webhooks/{{id}}",
            "description": "Delete a webhook subscription",
            "auth_required": true,
            "path_params": ["id"],
            "response_schema": {{
                "success": "boolean"
            }},
            "error_responses": {{
                "401": "Unauthorized",
                "404": "Subscription not found"
            }}
        }},
        {{
            "method": "GET",
            "path": "/api/v1/webhooks/{{id}}/deliveries",
            "description": "Get delivery history for a subscription",
            "auth_required": true,
            "path_params": ["id"],
            "query_params": {{
                "status": "string (optional, filter by status)",
                "limit": "integer (optional, default 50)"
            }},
            "response_schema": {{
                "items": "array of WebhookDelivery",
                "total": "integer"
            }},
            "error_responses": {{
                "401": "Unauthorized",
                "404": "Subscription not found"
            }}
        }}
    ],
    "integration_points": [
        {{
            "system": "EventBusService",
            "type": "internal",
            "description": "Subscribe to events for webhook triggering"
        }},
        {{
            "system": "External Webhook URLs",
            "type": "external",
            "description": "HTTP POST to customer-provided endpoints"
        }}
    ],
    "error_handling": {{
        "strategy": "Retry with exponential backoff",
        "max_retries": 3,
        "backoff_base": 2,
        "backoff_delays": ["2s", "4s", "8s"],
        "dead_letter": "Mark as failed after max retries, log for manual review"
    }},
    "testing_strategy": {{
        "unit_tests": [
            "WebhookSubscriptionService - CRUD operations",
            "WebhookDeliveryService - signature generation",
            "WebhookDeliveryService - retry logic"
        ],
        "integration_tests": [
            "End-to-end webhook delivery",
            "EventBus integration",
            "API endpoint tests"
        ],
        "load_tests": [
            "1000 events/minute throughput test"
        ]
    }},
    "security_considerations": [
        "HMAC-SHA256 signing for payload verification",
        "Secret stored encrypted at rest",
        "Rate limiting on webhook creation",
        "URL validation (no internal IPs, valid scheme)"
    ],
    "migration_plan": {{
        "steps": [
            "Create webhook_subscriptions table",
            "Create webhook_deliveries table",
            "Add indexes",
            "Deploy services",
            "Enable EventBus integration"
        ],
        "rollback": "Drop tables, disable EventBus handler"
    }}
}}
```

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# TASKS PHASE - Tickets and Tasks with ID Conventions
# =============================================================================

TASKS_PROMPT = """You are breaking down a design into tickets (work groupings) and tasks (atomic work units).

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Codebase Context (from Explore phase)
{explore_context}

## Requirements (from Requirements phase)
{requirements_context}

## Design (from Design phase)
{design_context}

## Your Task

Create **tickets** that represent logical groupings of work, then break each ticket into small, discrete **tasks**.

## Ticket Guidelines

Tickets are parent work items that appear on the project board:
- **One ticket per major component** or capability from the design
- **Clear acceptance criteria** mapped from requirements
- **Dependencies explicitly listed** - what blocks this, what this blocks
- **Reasonable scope** - if > 5 tasks, consider splitting the ticket

### Ticket ID Convention: `TKT-NNN`
- TKT-001, TKT-002, TKT-003, etc.
- Sequential numbering

### Ticket Priorities
- **CRITICAL**: Blocks other work, security issue, or deadline-critical
- **HIGH**: Core functionality, should be done first
- **MEDIUM**: Important but not blocking
- **LOW**: Nice to have, can be deferred

### Ticket Estimates
- **S**: 1-2 days
- **M**: 3-5 days
- **L**: 1-2 weeks
- **XL**: 2+ weeks (consider splitting)

## Task Guidelines

Tasks are atomic units of work that an AI agent can complete in a single session:
- **1-4 hours** of focused work (ideal)
- **Self-contained** - all context needed is in the task
- **Clear deliverables** - specific files to create/modify
- **Testable** - clear acceptance criteria

### Task ID Convention: `TSK-NNN`
- TSK-001, TSK-002, TSK-003, etc.
- Sequential numbering across all tickets

### Task Types
- `implementation`: Write new code
- `refactor`: Improve existing code
- `test`: Write tests
- `documentation`: Write docs
- `configuration`: Config changes
- `research`: Investigation/spike

### Task Estimates
- **S**: < 2 hours
- **M**: 2-4 hours
- **L**: 4-8 hours (consider splitting if > 4h)

## Required Output Format

When complete, you MUST write a JSON file with this structure:

```json
{{
    "feature_name": "webhook-notifications",
    "tickets": [
        {{
            "id": "TKT-001",
            "title": "Webhook Infrastructure Setup",
            "description": "Set up the core webhook infrastructure including database models, delivery service with retry logic, and API endpoints for webhook management.",
            "priority": "HIGH",
            "estimate": "M",
            "requirements": ["REQ-WEBHOOK-FUNC-001", "REQ-WEBHOOK-FUNC-002", "REQ-WEBHOOK-SEC-001"],
            "tasks": ["TSK-001", "TSK-002", "TSK-003", "TSK-004", "TSK-005", "TSK-006"],
            "acceptance_criteria": [
                "WebhookSubscription and WebhookDelivery models created",
                "Database migrations applied successfully",
                "WebhookDeliveryService delivers with retry logic",
                "All API endpoints functional",
                "Unit tests pass with 80%+ coverage"
            ],
            "dependencies": {{
                "blocked_by": [],
                "blocks": ["TKT-002"]
            }}
        }},
        {{
            "id": "TKT-002",
            "title": "EventBus Integration",
            "description": "Integrate webhook delivery with the existing EventBusService to automatically trigger webhooks when events occur.",
            "priority": "HIGH",
            "estimate": "S",
            "requirements": ["REQ-WEBHOOK-FUNC-002"],
            "tasks": ["TSK-007", "TSK-008"],
            "acceptance_criteria": [
                "WebhookNotificationService bridges EventBus to delivery",
                "Events trigger webhook deliveries automatically",
                "Integration tests pass"
            ],
            "dependencies": {{
                "blocked_by": ["TKT-001"],
                "blocks": []
            }}
        }}
    ],
    "tasks": [
        {{
            "id": "TSK-001",
            "title": "Create WebhookSubscription and WebhookDelivery Models",
            "description": "Create SQLAlchemy models for webhook subscriptions and delivery tracking with all fields from the design.",
            "parent_ticket": "TKT-001",
            "type": "implementation",
            "priority": "HIGH",
            "estimate": "M",
            "estimated_hours": 3,
            "files_to_create": [
                "omoi_os/models/webhook.py"
            ],
            "files_to_modify": [
                "omoi_os/models/__init__.py"
            ],
            "implementation_notes": "Follow existing model patterns. Use UUID for IDs, include created_at/updated_at timestamps. Store secret encrypted.",
            "acceptance_criteria": [
                "WebhookSubscription model with all fields from design",
                "WebhookDelivery model with all fields from design",
                "Models registered in __init__.py",
                "Pydantic schemas created for API"
            ],
            "dependencies": {{
                "depends_on": [],
                "blocks": ["TSK-002", "TSK-003"]
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-001"]
        }},
        {{
            "id": "TSK-002",
            "title": "Create Database Migration for Webhook Tables",
            "description": "Create Alembic migration to add webhook_subscriptions and webhook_deliveries tables with indexes.",
            "parent_ticket": "TKT-001",
            "type": "implementation",
            "priority": "HIGH",
            "estimate": "S",
            "estimated_hours": 1,
            "files_to_create": [
                "omoi_os/migrations/versions/xxx_add_webhook_tables.py"
            ],
            "files_to_modify": [],
            "implementation_notes": "Use alembic revision --autogenerate. Verify indexes are created. Test upgrade and downgrade.",
            "acceptance_criteria": [
                "Migration creates both tables",
                "All indexes from design are created",
                "Migration is reversible (downgrade works)",
                "Migration passes on test database"
            ],
            "dependencies": {{
                "depends_on": ["TSK-001"],
                "blocks": ["TSK-003", "TSK-004"]
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-001"]
        }},
        {{
            "id": "TSK-003",
            "title": "Implement WebhookDeliveryService",
            "description": "Create the delivery service with HTTP client, HMAC signature generation, and retry logic with exponential backoff.",
            "parent_ticket": "TKT-001",
            "type": "implementation",
            "priority": "HIGH",
            "estimate": "M",
            "estimated_hours": 4,
            "files_to_create": [
                "omoi_os/services/webhook_delivery.py"
            ],
            "files_to_modify": [
                "omoi_os/services/__init__.py"
            ],
            "implementation_notes": "Use httpx for async HTTP. Implement HMAC-SHA256 signing. Retry with delays: 2s, 4s, 8s. Log all attempts to WebhookDelivery table.",
            "acceptance_criteria": [
                "deliver() method sends HTTP POST with payload",
                "X-Signature header includes HMAC-SHA256 signature",
                "Failed deliveries retry up to 3 times",
                "Exponential backoff between retries",
                "All attempts logged to database"
            ],
            "dependencies": {{
                "depends_on": ["TSK-001", "TSK-002"],
                "blocks": ["TSK-004", "TSK-007"]
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-002", "REQ-WEBHOOK-SEC-001"]
        }},
        {{
            "id": "TSK-004",
            "title": "Implement WebhookSubscriptionService",
            "description": "Create the subscription service with CRUD operations and subscription lookup by event type.",
            "parent_ticket": "TKT-001",
            "type": "implementation",
            "priority": "HIGH",
            "estimate": "M",
            "estimated_hours": 2,
            "files_to_create": [
                "omoi_os/services/webhook_subscription.py"
            ],
            "files_to_modify": [
                "omoi_os/services/__init__.py"
            ],
            "implementation_notes": "Follow existing service patterns. Auto-generate secret if not provided. Validate URL format.",
            "acceptance_criteria": [
                "create_subscription() creates and returns subscription",
                "get_subscriptions_for_event() returns matching subscriptions",
                "delete_subscription() soft-deletes",
                "URL validation rejects invalid URLs"
            ],
            "dependencies": {{
                "depends_on": ["TSK-001", "TSK-002"],
                "blocks": ["TSK-005", "TSK-007"]
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-001"]
        }},
        {{
            "id": "TSK-005",
            "title": "Create Webhook API Endpoints",
            "description": "Add FastAPI routes for webhook subscription management (CRUD) and delivery history.",
            "parent_ticket": "TKT-001",
            "type": "implementation",
            "priority": "HIGH",
            "estimate": "M",
            "estimated_hours": 3,
            "files_to_create": [
                "omoi_os/api/routes/webhooks.py"
            ],
            "files_to_modify": [
                "omoi_os/api/main.py"
            ],
            "implementation_notes": "Follow existing route patterns. Use dependency injection for services. Add OpenAPI documentation.",
            "acceptance_criteria": [
                "POST /api/v1/webhooks creates subscription",
                "GET /api/v1/webhooks lists subscriptions",
                "GET /api/v1/webhooks/{{id}} gets single subscription",
                "DELETE /api/v1/webhooks/{{id}} deletes subscription",
                "GET /api/v1/webhooks/{{id}}/deliveries lists delivery history",
                "All endpoints require authentication"
            ],
            "dependencies": {{
                "depends_on": ["TSK-003", "TSK-004"],
                "blocks": ["TSK-006"]
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-001"]
        }},
        {{
            "id": "TSK-006",
            "title": "Write Unit Tests for Webhook Services",
            "description": "Create comprehensive unit tests for WebhookDeliveryService and WebhookSubscriptionService.",
            "parent_ticket": "TKT-001",
            "type": "test",
            "priority": "HIGH",
            "estimate": "M",
            "estimated_hours": 3,
            "files_to_create": [
                "tests/unit/services/test_webhook_delivery.py",
                "tests/unit/services/test_webhook_subscription.py"
            ],
            "files_to_modify": [],
            "implementation_notes": "Mock HTTP client for delivery tests. Test retry logic, signature generation, CRUD operations.",
            "acceptance_criteria": [
                "Tests cover happy path for all service methods",
                "Tests cover error cases (network failure, invalid input)",
                "Tests verify retry logic with mocked delays",
                "Tests verify HMAC signature generation",
                "80%+ code coverage"
            ],
            "dependencies": {{
                "depends_on": ["TSK-003", "TSK-004", "TSK-005"],
                "blocks": []
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-001", "REQ-WEBHOOK-FUNC-002", "REQ-WEBHOOK-SEC-001"]
        }},
        {{
            "id": "TSK-007",
            "title": "Implement WebhookNotificationService",
            "description": "Create the notification service that bridges EventBusService to webhook delivery.",
            "parent_ticket": "TKT-002",
            "type": "implementation",
            "priority": "HIGH",
            "estimate": "M",
            "estimated_hours": 2,
            "files_to_create": [
                "omoi_os/services/webhook_notification.py"
            ],
            "files_to_modify": [
                "omoi_os/services/__init__.py"
            ],
            "implementation_notes": "Subscribe to EventBus events. For each event, look up matching subscriptions and trigger delivery.",
            "acceptance_criteria": [
                "handle_event() processes events from EventBus",
                "Looks up subscriptions by event type",
                "Triggers delivery for each matching subscription",
                "Handles delivery failures gracefully"
            ],
            "dependencies": {{
                "depends_on": ["TSK-003", "TSK-004"],
                "blocks": ["TSK-008"]
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-002"]
        }},
        {{
            "id": "TSK-008",
            "title": "Write Integration Tests for EventBus Integration",
            "description": "Create integration tests verifying end-to-end flow from EventBus event to webhook delivery.",
            "parent_ticket": "TKT-002",
            "type": "test",
            "priority": "MEDIUM",
            "estimate": "M",
            "estimated_hours": 2,
            "files_to_create": [
                "tests/integration/test_webhook_integration.py"
            ],
            "files_to_modify": [],
            "implementation_notes": "Use test database. Mock external HTTP endpoints. Verify complete flow.",
            "acceptance_criteria": [
                "Test creates subscription, triggers event, verifies delivery",
                "Test verifies retry behavior on failure",
                "Test verifies signature in delivered payload",
                "All tests use isolated test database"
            ],
            "dependencies": {{
                "depends_on": ["TSK-007"],
                "blocks": []
            }},
            "requirements_addressed": ["REQ-WEBHOOK-FUNC-002"]
        }}
    ],
    "total_estimated_hours": 20,
    "critical_path": ["TSK-001", "TSK-002", "TSK-003", "TSK-005", "TSK-007"],
    "parallel_tracks": [
        {{
            "name": "Core Infrastructure",
            "tasks": ["TSK-001", "TSK-002", "TSK-003", "TSK-004", "TSK-005"]
        }},
        {{
            "name": "Integration",
            "tasks": ["TSK-007", "TSK-008"],
            "starts_after": "TSK-004"
        }}
    ]
}}
```

### Quality Checklist

Before finalizing, verify:
- [ ] Every ticket has TKT-NNN format ID
- [ ] Every task has TSK-NNN format ID
- [ ] Every task has a parent_ticket reference
- [ ] Every task is 1-4 hours (atomic)
- [ ] No circular dependencies
- [ ] All requirements are addressed by at least one task
- [ ] Critical path is defined
- [ ] Files to create/modify are specified for each task

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# SYNC PHASE - Validation and Traceability
# =============================================================================

SYNC_PROMPT = """You are synchronizing and validating all generated artifacts.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Generated Artifacts
- Requirements: {requirements_context}
- Design: {design_context}
- Tasks: {tasks_context}

## Your Task

Verify and finalize all generated artifacts:

1. **Validate Consistency**
   - Requirements → Design: Every requirement has a design component
   - Design → Tasks: Every design component has tasks
   - Requirements → Tasks: Every requirement is addressed by tasks

2. **Check Dependencies**
   - No circular dependencies in task graph
   - All dependency references are valid (exist)
   - Critical path is achievable

3. **Calculate Traceability Statistics**
   - Requirements coverage percentage
   - Orphan detection (unlinked items)
   - Task status breakdown

4. **Generate Coverage Matrix**
   - Map each requirement to covering tasks
   - Identify gaps in coverage

5. **Final Validation**
   - All IDs follow conventions
   - All required fields present
   - Estimates are reasonable

## Required Output Format

When complete, you MUST write a JSON file with this structure:

```json
{{
    "validation_results": {{
        "all_requirements_covered": true,
        "all_design_components_have_tasks": true,
        "dependency_order_valid": true,
        "no_circular_dependencies": true,
        "all_ids_valid": true,
        "issues_found": [],
        "warnings": [
            "REQ-WEBHOOK-PERF-001 has no dedicated task (covered by integration tests)"
        ]
    }},
    "coverage_matrix": [
        {{
            "requirement_id": "REQ-WEBHOOK-FUNC-001",
            "requirement_title": "Webhook Subscription Creation",
            "covered_by_tasks": ["TSK-001", "TSK-002", "TSK-004", "TSK-005"],
            "covered_by_tickets": ["TKT-001"],
            "status": "fully_covered",
            "coverage_notes": "CRUD operations and API fully implemented"
        }},
        {{
            "requirement_id": "REQ-WEBHOOK-FUNC-002",
            "requirement_title": "Webhook Event Delivery",
            "covered_by_tasks": ["TSK-003", "TSK-007", "TSK-008"],
            "covered_by_tickets": ["TKT-001", "TKT-002"],
            "status": "fully_covered",
            "coverage_notes": "Delivery service and EventBus integration"
        }},
        {{
            "requirement_id": "REQ-WEBHOOK-SEC-001",
            "requirement_title": "Webhook Payload Signing",
            "covered_by_tasks": ["TSK-003", "TSK-006"],
            "covered_by_tickets": ["TKT-001"],
            "status": "fully_covered",
            "coverage_notes": "HMAC signing in delivery service"
        }},
        {{
            "requirement_id": "REQ-WEBHOOK-PERF-001",
            "requirement_title": "Webhook Throughput",
            "covered_by_tasks": ["TSK-008"],
            "covered_by_tickets": ["TKT-002"],
            "status": "partially_covered",
            "coverage_notes": "Verified in integration tests, no dedicated load test task"
        }}
    ],
    "traceability_stats": {{
        "requirements": {{
            "total": 4,
            "fully_covered": 3,
            "partially_covered": 1,
            "not_covered": 0,
            "coverage_percent": 87.5
        }},
        "tickets": {{
            "total": 2,
            "with_requirements": 2,
            "orphans": 0
        }},
        "tasks": {{
            "total": 8,
            "with_parent_ticket": 8,
            "with_requirements": 8,
            "orphans": 0,
            "by_status": {{
                "pending": 8,
                "in_progress": 0,
                "completed": 0
            }},
            "by_type": {{
                "implementation": 6,
                "test": 2
            }}
        }},
        "dependencies": {{
            "total_edges": 12,
            "circular_detected": 0,
            "invalid_references": 0
        }}
    }},
    "dependency_analysis": {{
        "task_dependency_graph": {{
            "TSK-001": [],
            "TSK-002": ["TSK-001"],
            "TSK-003": ["TSK-001", "TSK-002"],
            "TSK-004": ["TSK-001", "TSK-002"],
            "TSK-005": ["TSK-003", "TSK-004"],
            "TSK-006": ["TSK-003", "TSK-004", "TSK-005"],
            "TSK-007": ["TSK-003", "TSK-004"],
            "TSK-008": ["TSK-007"]
        }},
        "ticket_dependency_graph": {{
            "TKT-001": [],
            "TKT-002": ["TKT-001"]
        }},
        "critical_path": ["TSK-001", "TSK-002", "TSK-003", "TSK-005", "TSK-007", "TSK-008"],
        "critical_path_hours": 15,
        "parallel_opportunities": [
            "TSK-003 and TSK-004 can run in parallel after TSK-002"
        ]
    }},
    "spec_summary": {{
        "feature_name": "webhook-notifications",
        "total_requirements": 4,
        "total_tickets": 2,
        "total_tasks": 8,
        "total_estimated_hours": 20,
        "files_to_create": 8,
        "files_to_modify": 4,
        "requirement_coverage_percent": 87.5,
        "estimated_duration": "1-2 weeks with one developer"
    }},
    "ready_for_execution": true,
    "blockers": [],
    "recommendations": [
        "Consider adding a dedicated load test task for REQ-WEBHOOK-PERF-001",
        "TSK-001 is on critical path - prioritize first"
    ]
}}
```

### Validation Checklist

Verify these before marking ready_for_execution = true:

- [ ] All requirements have at least one task covering them
- [ ] No circular dependencies in task graph
- [ ] All task dependencies reference valid task IDs
- [ ] All tickets have at least one task
- [ ] All tasks have parent_ticket set
- [ ] Critical path is defined and achievable
- [ ] Total estimated hours is reasonable (< 80 for a feature)
- [ ] No orphan tasks or tickets

Use the Write tool to create this JSON file at the path specified in your instructions.
"""


def get_phase_prompt(phase: SpecPhase) -> str:
    """Get the prompt template for a specific phase.

    Args:
        phase: The spec phase to get prompt for

    Returns:
        The prompt template string with placeholders

    Raises:
        ValueError: If phase is not recognized
    """
    prompts = {
        SpecPhase.EXPLORE: EXPLORE_PROMPT,
        SpecPhase.PRD: PRD_PROMPT,
        SpecPhase.REQUIREMENTS: REQUIREMENTS_PROMPT,
        SpecPhase.DESIGN: DESIGN_PROMPT,
        SpecPhase.TASKS: TASKS_PROMPT,
        SpecPhase.SYNC: SYNC_PROMPT,
    }

    if phase not in prompts:
        raise ValueError(f"Unknown phase: {phase}")

    return prompts[phase]
