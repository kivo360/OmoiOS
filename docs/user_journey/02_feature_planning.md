# 2 Feature Planning

**Part of**: [User Journey Documentation](./README.md)

---
### Phase 2: Feature Request & Planning

#### 2.1 Creating a Feature Request

**Method 1: Natural Language Feature Request**
```
1. User navigates to project dashboard
   ↓
2. Clicks "New Feature" or uses Command Palette (Cmd+K)
   ↓
3. Spec Creation Modal appears with fields:
   - Spec Title: [________________]
   - Description (natural language): [Add payment processing with Stripe]
   - Repository Selection: [Select Repository ▼]
   - Priority: [Low] [Medium] [High] (default: Medium)
   ↓
4. User clicks "Create Spec"
   ↓
5. System validates inputs:
   - Title required
   - Description minimum length check
   - Repository must be connected
   ↓
6. System analyzes:
   - Current codebase structure
   - Existing dependencies
   - Similar features in codebase
   ↓
7. System generates spec-driven workflow:
   - Requirements Phase (EARS-style requirements)
   - Design Phase (architecture, sequence diagrams)
   - Planning Phase (task breakdown with dependencies)
   - Execution Phase (autonomous code generation)
   ↓
8. Spec appears in Spec Workspace (multi-tab view)
   ↓
9. Toast notification: "Spec created successfully"
```

**Method 2: GitHub Issue Integration**
```
1. GitHub issue created
   ↓
2. Webhook → OmoiOS receives issue
   ↓
3. System creates ticket automatically
   ↓
4. Ticket appears in Kanban board (Backlog column)
   ↓
5. User can trigger spec generation from ticket
```

#### 2.2 Spec Review & Approval

```
1. User navigates to Spec Workspace
   ↓
2. Views multi-tab interface:
   - Requirements tab: EARS-style requirements with WHEN/THE SYSTEM SHALL patterns
   - Design tab: Architecture diagrams, sequence diagrams, data models
   - Tasks tab: Discrete tasks with dependencies
   - Execution tab: (empty until execution starts)
   ↓
3. User reviews Requirements tab:
   - Views EARS format examples:
     ```
     REQ-001
     WHEN: User enables 2FA in account settings
     THE SYSTEM SHALL: Display QR code for authenticator app setup
     ACCEPTANCE CRITERIA:
     ✓ QR code generates valid TOTP secret
     ✓ User can scan with Google Authenticator
     ✓ Backup codes generated automatically
     ```
   - Can edit requirements inline (structured blocks)
   - Can add new requirements
   - Can delete or reorder requirements
   ↓
4. User clicks "Approve Requirements" button
   ↓
5. Toast notification: "Requirements approved ✓"
   ↓
6. User reviews Design tab:
   - Views architecture components with names:
     - Authentication Service
       ├─ OAuth2 Handler
       ├─ JWT Generator
       └─ Token Validator
   - Views data model examples (JavaScript/Python)
   - Views sequence diagrams
   - Can edit design components inline
   ↓
7. User clicks "Approve Design" button
   ↓
8. Toast notification: "Design approved ✓"
   ↓
9. User reviews Tasks tab:
   - Views discrete tasks with dependencies
   - Can edit task descriptions
   - Can adjust dependencies
   ↓
10. User clicks "Approve Plan" when satisfied
    ↓
11. System transitions to Execution Phase
    ↓
12. Toast notification: "Plan approved. Execution starting..."
    ↓
13. Tickets move from Backlog → Initial phase in Kanban board
```

**Spec Workspace Features:**
- **Structured blocks** (Notion-style) for requirements/design content
- **Spec switcher** to switch between multiple specs within each tab
- **Collapsible sidebar** for spec navigation (Obsidian-style)
- **Export options**: Markdown, YAML, PDF
- **Version history**: Track spec changes over time

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
