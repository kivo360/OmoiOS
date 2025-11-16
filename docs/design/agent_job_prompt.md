# Agent Job Execution Prompt

## Instructions

You are tasked with generating a design document from requirements. Follow these steps:

### Step 1: Read the Job Specification File

Read the file: `docs/design/parallel_design_jobs.md`

This file contains 11 independent job specifications. Each job:
- Reads ONE requirements file
- Produces ONE design document
- Is completely independent (can run in parallel)

### Step 2: Select Your Job

Choose ONE job by its number (1-11):

1. Memory System Design
2. Validation System Design
3. Diagnosis Agent Design
4. Enhanced Result Submission Design
5. Monitoring Architecture Design
6. Task Queue Management Design
7. Ticket Human Approval Design
8. Ticket Workflow Design
9. Agent Lifecycle Management Design
10. Fault Tolerance Design
11. MCP Server Integration Design

**If no job number is specified, start with Job 1 (Memory System Design).**

### Step 3: Read the Requirements File

Read the source requirements file specified in your chosen job's contract:
- Path will be something like `docs/requirements/[category]/[filename].md`
- This is your SOLE SOURCE OF TRUTH for what to design

### Step 4: Read Existing Design Documents (for Style Reference)

Read these files to understand the expected format and style:
- `docs/design/multi_agent_orchestration.md` (main reference for style)
- `docs/design/workspace_isolation_system.md` (if relevant to your job)

**DO NOT modify these files** - they are read-only references.

### Step 5: Generate the Design Document

Create the target design document at the path specified in your job contract.

**Required Sections** (adapt based on your job's contract):

1. **Document Overview**
   - Purpose and scope
   - Target audience
   - Related documents (link to requirements and other design docs)

2. **Architecture Overview**
   - High-level architecture diagram (Mermaid or ASCII)
   - Component responsibilities table
   - System boundaries

3. **Component Details**
   - Detailed description of each component
   - Interfaces and contracts
   - Key methods/functions
   - Data flows between components

4. **Data Models**
   - Database schemas (SQL CREATE TABLE statements)
   - Pydantic models (if applicable)
   - Relationships and constraints

5. **API Specifications**
   - Endpoint tables (method, path, purpose, request/response)
   - Request/response models
   - Error handling and status codes
   - Authentication/authorization requirements

6. **Integration Points**
   - How this system integrates with others
   - Memory System integration (if specified in requirements)
   - Other cross-system integrations
   - Event/WebSocket contracts

7. **Implementation Details**
   - Algorithms and pseudocode
   - Performance considerations
   - Configuration parameters
   - Error handling strategies

8. **Related Documents**
   - Links back to requirements document
   - Links to related design documents
   - Cross-references

### Step 6: Quality Checklist

Before completing, verify:

- [ ] All requirements from source file are addressed
- [ ] Architecture diagrams included (Mermaid or ASCII)
- [ ] API specifications match requirements exactly
- [ ] Database schemas match requirements exactly
- [ ] Integration points clearly documented
- [ ] Configuration parameters documented
- [ ] Code examples provided where appropriate
- [ ] Cross-references to related design docs included
- [ ] Formatting consistent with existing design docs
- [ ] Memory System integration included (if specified in requirements)

### Step 7: Output Format

Use Markdown with:
- Code blocks for SQL, Python, JSON, YAML
- Tables for API endpoints, configuration, comparisons
- Mermaid diagrams for state machines, sequence diagrams, architecture
- Clear headings and subheadings
- Consistent formatting with existing design docs

---

## Example Execution

If you're assigned **Job 1 (Memory System Design)**:

1. Read `docs/design/parallel_design_jobs.md` → Find Job 1 contract
2. Read `docs/requirements/memory/memory_system.md` → Your source of truth
3. Read `docs/design/multi_agent_orchestration.md` → Style reference
4. Create `docs/design/memory_system.md` → Your output
5. Follow the contract exactly:
   - Cover ACE workflow (Executor → Reflector → Curator)
   - Include PostgreSQL schema with pgvector
   - Document all API endpoints
   - Include hybrid search implementation (RRF)
   - Add integration patterns

---

## Important Notes

- **Stay within scope**: Only address what's in your assigned requirements file
- **Don't invent**: If something isn't in requirements, don't add it unless it's a necessary implementation detail
- **Be consistent**: Match the style and depth of existing design documents
- **Include diagrams**: Visual representations help understanding
- **Link everything**: Cross-reference requirements, related design docs, and integration points
- **Memory integration**: If your requirements file mentions Memory System integration (REQ-*-MEM-*), include those sections

---

## Job Selection

**To select a job, respond with:**

```
I will execute Job [NUMBER]: [JOB NAME]
```

Then proceed with Steps 3-7 above.

---

**Ready to begin?** Select your job number and start reading the requirements file!

