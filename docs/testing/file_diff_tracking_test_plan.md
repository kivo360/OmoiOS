# File Diff Tracking - Frontend Testing Plan

**Created**: 2025-12-17  
**Status**: Ready for Testing  
**Related**: [09_rich_activity_feed_architecture.md](../design/sandbox-agents/09_rich_activity_feed_architecture.md)

---

## Overview

This document outlines the testing strategy for the file diff tracking feature, from backend worker to frontend display.

## Implementation Status

### Backend ✅
- [x] FileChangeTracker class implemented
- [x] PreToolUse hook for file caching
- [x] PostToolUse hook for diff generation
- [x] `agent.file_edited` event emission
- [x] Event persistence to database
- [x] Event broadcasting via EventBus

### Frontend ✅
- [x] FileChangeCard component created
- [x] Activity page integration
- [x] Event type configuration
- [x] Event transformer updated
- [x] Filter option added

---

## Event Flow

```
┌─────────────────┐
│ Sandbox Worker  │
│ (claude_sandbox │
│  _worker.py)    │
└────────┬────────┘
         │
         │ POST /api/v1/sandboxes/{id}/events
         │ {
         │   "event_type": "agent.file_edited",
         │   "event_data": { ... }
         │ }
         ▼
┌─────────────────┐
│  API Endpoint   │
│ (sandbox.py)    │
└────────┬────────┘
         │
         │ 1. Persist to database
         │ 2. Broadcast via EventBus
         │    (event_type: "SANDBOX_agent.file_edited")
         ▼
┌─────────────────┐
│   EventBus      │
│   (Redis)       │
└────────┬────────┘
         │
         │ WebSocket broadcast
         ▼
┌─────────────────┐
│   Frontend      │
│ (useEvents hook)│
└────────┬────────┘
         │
         │ Transform & Display
         ▼
┌─────────────────┐
│ Activity Page   │
│ FileChangeCard  │
└─────────────────┘
```

---

## Test Scenarios

### 1. End-to-End Integration Test

**Objective**: Verify complete event flow from worker to frontend

**Steps**:
1. Start backend API server
2. Start frontend dev server
3. Navigate to `/activity` page
4. Spawn a sandbox with a task that creates/modifies files
5. Verify events appear in real-time

**Expected Results**:
- ✅ `agent.file_edited` events appear in activity feed
- ✅ FileChangeCard displays file path, change type, line counts
- ✅ Diff preview is visible when expanded
- ✅ Events are filterable by "File Edits" type

**Test Command**:
```bash
# Terminal 1: Start backend
cd backend
python -m uvicorn omoi_os.api.main:app --reload --port 18000

# Terminal 2: Start frontend
cd frontend
npm run dev

# Terminal 3: Spawn test sandbox
python backend/scripts/test_api_sandbox_spawn.py
```

---

### 2. File Creation Event Test

**Objective**: Verify new file creation is tracked correctly

**Test Task**:
```
Create a new file called test.py with:
def hello():
    print("Hello, World!")
```

**Expected Results**:
- ✅ Event shows `change_type: "created"`
- ✅ `lines_added` equals file line count
- ✅ `lines_removed` equals 0
- ✅ Diff shows all lines as additions (`+`)

---

### 3. File Modification Event Test

**Objective**: Verify file modification tracking

**Test Task**:
```
Modify test.py to add:
def goodbye():
    print("Goodbye!")
```

**Expected Results**:
- ✅ Event shows `change_type: "modified"`
- ✅ `lines_added` and `lines_removed` are accurate
- ✅ Diff shows unified diff format with `-` and `+` lines
- ✅ File path is correct

---

### 4. Large File Diff Test

**Objective**: Verify truncation and full diff handling

**Test Task**:
```
Create a large file (> 5KB diff preview, > 50KB full diff)
```

**Expected Results**:
- ✅ Diff preview is truncated to 5KB
- ✅ `full_diff_available: true` flag is set
- ✅ Full diff size is reported
- ✅ Expand button loads full diff (when API endpoint is implemented)

---

### 5. Multiple File Edits Test

**Objective**: Verify multiple file edits in sequence

**Test Task**:
```
Create file1.py, modify file2.py, create file3.py
```

**Expected Results**:
- ✅ All three events appear in activity feed
- ✅ Each event shows correct file path
- ✅ Events are ordered chronologically (newest first)
- ✅ Filtering by "File Edits" shows all three

---

### 6. WebSocket Connection Test

**Objective**: Verify real-time event delivery

**Steps**:
1. Open browser DevTools → Network → WS
2. Verify WebSocket connection to `/api/v1/events/ws/events`
3. Trigger file edit in sandbox
4. Verify event arrives via WebSocket (not polling)

**Expected Results**:
- ✅ WebSocket connection established
- ✅ Event arrives within 1 second of file edit
- ✅ No HTTP polling requests

---

### 7. Event Persistence Test

**Objective**: Verify events are stored in database

**Steps**:
1. Trigger file edit event
2. Query database: `SELECT * FROM sandbox_events WHERE event_type = 'agent.file_edited'`
3. Verify event data is complete

**Expected Results**:
- ✅ Event persisted with correct `sandbox_id`
- ✅ `event_data` contains all diff fields
- ✅ `source` field is "agent" or "worker"

---

### 8. Frontend Component Test

**Objective**: Verify FileChangeCard UI behavior

**Steps**:
1. View activity page with file edit events
2. Test expand/collapse functionality
3. Test diff rendering

**Expected Results**:
- ✅ Card displays file path, change type, line counts
- ✅ Expand button toggles diff view
- ✅ Diff is syntax-highlighted (if implemented)
- ✅ ScrollArea works for long diffs
- ✅ LineChanges component shows correct +/- counts

---

## Manual Testing Checklist

### Backend Verification
- [ ] Worker emits `agent.file_edited` events
- [ ] API endpoint receives events correctly
- [ ] Events are persisted to database
- [ ] Events are broadcast via EventBus
- [ ] Event structure matches schema

### Frontend Verification
- [ ] WebSocket connection established
- [ ] Events appear in activity feed
- [ ] FileChangeCard renders correctly
- [ ] Expand/collapse works
- [ ] Diff preview displays correctly
- [ ] Filter by "File Edits" works
- [ ] Line counts are accurate
- [ ] File paths are displayed correctly

### Edge Cases
- [ ] Very large files (> 50KB diff)
- [ ] Binary files (should not break)
- [ ] Concurrent file edits
- [ ] Network disconnection/reconnection
- [ ] Multiple sandboxes editing files simultaneously

---

## API Endpoint Testing

### Test Event Creation

```bash
# Create a test file edit event
curl -X POST http://localhost:18000/api/v1/sandboxes/test-sandbox-123/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "agent.file_edited",
    "event_data": {
      "file_path": "/workspace/test.py",
      "change_type": "modified",
      "lines_added": 5,
      "lines_removed": 2,
      "diff_preview": "--- a/test.py\n+++ b/test.py\n@@ -1,3 +1,6 @@\n def hello():\n     print(\"Hello\")\n+def goodbye():\n+    print(\"Goodbye\")\n",
      "full_diff_available": false
    },
    "source": "agent"
  }'
```

### Query Events

```bash
# Get all file edit events for a sandbox
curl "http://localhost:18000/api/v1/sandboxes/test-sandbox-123/events?event_type=agent.file_edited&limit=10"
```

---

## Debugging Tips

### Events Not Appearing

1. **Check WebSocket connection**:
   - Browser DevTools → Network → WS tab
   - Verify connection to `/api/v1/events/ws/events`
   - Check for connection errors

2. **Check EventBus**:
   - Verify Redis is running
   - Check EventBus logs for publish errors

3. **Check API logs**:
   - Verify POST endpoint receives events
   - Check for validation errors
   - Verify event persistence

4. **Check Frontend**:
   - Verify `useEvents` hook is enabled
   - Check browser console for errors
   - Verify event filters are correct

### Diff Not Displaying

1. **Check event structure**:
   - Verify `event_data` contains all required fields
   - Check `diff_preview` is not empty
   - Verify `file_path` is present

2. **Check component rendering**:
   - Verify FileChangeCard is imported
   - Check for React errors in console
   - Verify event type matching logic

---

## Next Steps

### Immediate
- [ ] Run end-to-end test with real sandbox
- [ ] Verify all test scenarios pass
- [ ] Fix any discovered issues

### Future Enhancements
- [ ] Implement full diff fetch API endpoint
- [ ] Add syntax highlighting for diffs
- [ ] Add file type icons
- [ ] Add click-to-open-file functionality
- [ ] Add diff line-by-line highlighting
- [ ] Add copy diff button

---

## Related Files

- **Backend**: `backend/omoi_os/workers/claude_sandbox_worker.py`
- **API**: `backend/omoi_os/api/routes/sandbox.py`
- **Frontend Component**: `frontend/components/custom/FileChangeCard.tsx`
- **Activity Page**: `frontend/app/(app)/activity/page.tsx`
- **Event Hook**: `frontend/hooks/useEvents.ts`

---

**Status**: Ready for testing. All components implemented and integrated.
