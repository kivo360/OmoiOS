# 4 Approvals Completion

**Part of**: [User Journey Documentation](./README.md)

---
### Phase 4: Approval Gates & Phase Transitions

#### 4.1 Phase Gate Approvals

```
Agent completes all tasks in PHASE_IMPLEMENTATION:
   ↓
1. System checks done_definitions:
   - Component code files created ✓
   - Minimum 3 test cases passing ✓
   - Phase 3 validation task created ✓
   ↓
2. System validates expected_outputs:
   - Files match patterns ✓
   - Tests pass ✓
   ↓
3. System requests user approval for phase transition
   ↓
4. Notification appears:
   - In-app notification
   - Email (if configured)
   - Dashboard shows approval pending badge
   ↓
5. User reviews:
   - Code changes (commit diff viewer)
   - Test results
   - Agent reasoning summaries
   ↓
6. User approves or rejects:
   - Approve → Ticket moves to PHASE_INTEGRATION
   - Reject → Ticket regresses, agent receives feedback
   ↓
7. Workflow continues autonomously
```

**Approval Points:**
- Phase transitions (INITIAL → IMPLEMENTATION → INTEGRATION → REFACTORING)
- PR reviews (before merge)
- Budget threshold exceeded
- High-risk changes

#### 4.2 PR Review & Merge

```
Agent completes feature implementation:
   ↓
1. Agent creates PR automatically
   ↓
2. System generates PR summary:
   - Code changes summary
   - Test coverage report
   - Risk assessment
   ↓
3. User receives notification: "PR ready for review"
   ↓
4. User reviews:
   - Commit diff viewer (side-by-side, syntax highlighted)
   - See exactly which code each agent modified
   - Test results
   - Agent reasoning
   ↓
5. User approves PR:
   - Merge PR
   - Ticket moves to DONE
   - Feature complete!
   ↓
OR
5. User requests changes:
   - Agent receives feedback
   - Agent makes changes
   - PR updated
   - Cycle repeats
```

#### 4.3 Completion Summary & Export

```
All tasks completed and PRs merged:
   ↓
1. System shows Completion Summary checklist:
   ✅ All requirements met
   ✅ All tests passing (50/50)
   ✅ All PRs merged
   ✅ Code deployed to staging (if configured)
   ✅ Documentation updated
   ↓
2. User reviews completion summary
   ↓
3. User clicks "Mark as Complete"
   ↓
4. Spec status changes to "Completed"
   ↓
5. Spec moves to "Completed" section in dashboard
   ↓
6. User can export spec:
   - Click "Export Spec" button
   - Select format: Markdown | YAML | PDF
   - Download file with complete spec (Requirements + Design + Tasks + Execution history)
   ↓
7. Toast notification: "Spec completed and exported ✓"
```

**Completion Summary Checklist:**
- All requirements met (verified against EARS requirements)
- All tests passing (with coverage percentage)
- All PRs merged (with commit SHAs)
- Code deployed (if deployment configured)
- Documentation updated (if documentation tasks exist)
- All agent learnings saved to memory system

**Export Options:**
- **Markdown**: Complete spec in markdown format
- **YAML**: Structured YAML export for version control
- **PDF**: Formatted PDF report for documentation

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
