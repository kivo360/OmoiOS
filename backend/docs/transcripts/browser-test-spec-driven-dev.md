# Browser Test: Spec-Driven Development Feature

## Objective

Test the spec-driven-dev skill enforcement feature by creating a ticket in "Spec Driven" mode and verifying the agent creates properly formatted specs.

## Prerequisites

- Frontend running at `http://localhost:3000` (or production URL)
- Backend running and connected
- User logged in with valid session

## Test Steps

### Step 1: Navigate to Command Center

1. Open the browser
2. Navigate to `/command` (Command Center page)
3. Wait for the page to load completely
4. Verify you see:
   - A text input area for the prompt
   - A mode selector (should show "Quick" and "Spec Driven" options)
   - Project/repo selection dropdowns

### Step 2: Select Spec Driven Mode

1. Find the workflow mode selector (may be labeled "Mode" or show icons)
2. Click to open the dropdown/selector
3. Select "Spec Driven" mode (not "Quick")
4. Verify the mode is selected (UI should indicate selection)
5. Note: The helper text below the input should change to reflect spec-driven mode

### Step 3: Select a Project or Repository

1. Either select an existing project from the project dropdown
2. OR select a GitHub repository from the repo dropdown
3. This determines where the specs will be created

### Step 4: Enter a Prompt

1. Click on the main text input area
2. Enter a test prompt, for example:
   ```
   Create a user authentication system with login, logout, and password reset functionality
   ```
3. The prompt should describe a feature to be specified (not implemented)

### Step 5: Submit and Wait

1. Click the submit button (or press Enter/Cmd+Enter)
2. You should see:
   - "Creating ticket..." or similar loading state
   - Then "Launching sandbox..." message
   - Finally redirect to the board page (`/board/{projectId}`)
3. Wait for the redirect (may take 10-30 seconds)

### Step 6: Monitor the Board

1. On the board page, watch for:
   - Task cards appearing
   - Status updates on the cards
2. The agent should be working on creating specs

### Step 7: Verify Spec Creation (Via Sandbox Page)

1. Find the sandbox ID from the URL or task card
2. Navigate to `/sandbox/{sandboxId}` to see agent activity
3. Watch for:
   - Agent reading/writing to `.omoi_os/` directory
   - Creation of spec files (tickets/*.md, tasks/*.md, etc.)
   - Git commits with spec files

### Step 8: Check the Output

After the agent completes, verify:

1. **Directory Structure Created:**
   ```
   .omoi_os/
   ├── tickets/
   │   └── *.md files
   └── tasks/
       └── *.md files
   ```

2. **Files Have YAML Frontmatter:**
   Each `.md` file should start with:
   ```yaml
   ---
   id: TICKET-001 (or TASK-001)
   title: "Feature title"
   status: draft
   priority: medium (for tickets)
   ticket_id: TICKET-001 (for tasks)
   ---
   ```

3. **Git Commit Made:**
   - Agent should have committed the spec files
   - Commit message should follow convention: `docs(scope): description`

## Expected Results

### Success Criteria

- [ ] Spec Driven mode selected successfully
- [ ] Ticket created with `workflow_mode: "spec_driven"`
- [ ] Sandbox spawned with `REQUIRE_SPEC_SKILL=true`
- [ ] Agent creates `.omoi_os/` directory
- [ ] Spec files have valid YAML frontmatter
- [ ] Agent commits and pushes specs
- [ ] No validation errors in worker logs

### Failure Indicators

- Agent writes implementation code instead of specs
- No `.omoi_os/` directory created
- Spec files missing frontmatter
- Validation errors in logs: "Missing required fields: ..."
- Agent doesn't follow the spec-driven-dev workflow

## Troubleshooting

### If Agent Doesn't Create Specs

1. Check worker logs for `REQUIRE_SPEC_SKILL` value
2. Verify `execution_config` is set on the task in DB
3. Check if skill content is being injected into prompt

### If Validation Fails

1. Check worker logs for specific validation errors
2. Common issues:
   - Missing `id` field in frontmatter
   - Missing `status` field
   - Wrong directory structure

### If Sandbox Doesn't Spawn

1. Check backend logs for spawner errors
2. Verify Daytona API key is configured
3. Check if ticket was created with correct `workflow_mode`

## Browser Console Commands (for debugging)

```javascript
// Check current page state
console.log(window.location.pathname)

// Check localStorage for session
console.log(localStorage.getItem('session'))

// Monitor network requests
// Open DevTools > Network tab > Filter by "Fetch/XHR"
```

## API Verification (optional)

You can verify the ticket was created correctly:

```bash
# Get the ticket (replace {ticketId} with actual ID)
curl -X GET "http://localhost:8000/api/v1/tickets/{ticketId}" \
  -H "Authorization: Bearer {token}"

# Check task execution_config
curl -X GET "http://localhost:8000/api/v1/tasks?ticket_id={ticketId}" \
  -H "Authorization: Bearer {token}"
```

The task should have:
```json
{
  "execution_config": {
    "require_spec_skill": true,
    "selected_skill": "spec-driven-dev"
  }
}
```
