---
id: TKT-002
title: External Webhook Integrations (Slack, Discord)
status: backlog
priority: MEDIUM
estimate: L
created: 2025-12-29
updated: 2025-12-29
feature: webhook-integrations
requirements:
  - REQ-WEBHOOK-SLACK-001
  - REQ-WEBHOOK-DISCORD-001
design_ref: designs/webhook-integrations.md
tasks:
  - TSK-007
  - TSK-008
dependencies:
  blocked_by: [TKT-001]
  blocks: []
  related: []
---

# TKT-002: External Webhook Integrations (Slack, Discord)

## Description

Add support for external integrations like Slack and Discord notifications. This builds on the webhook infrastructure from TKT-001 to add formatted messages for popular platforms.

### Context
After implementing basic webhook notifications (TKT-001), users want native integrations with common platforms. This requires message formatting specific to each platform's API.

### Goals
- Slack-formatted webhook payloads
- Discord-formatted webhook payloads
- Platform detection from webhook URL

### Non-Goals
- OAuth-based integrations (use incoming webhooks only)

---

## Acceptance Criteria

- [ ] Slack message formatting with blocks
- [ ] Discord embed formatting
- [ ] Auto-detect platform from URL pattern
- [ ] Fallback to generic JSON for unknown platforms
