---
id: TSK-007
title: Implement Slack Message Formatter
status: pending
parent_ticket: TKT-002
estimate: M
created: 2025-12-29
assignee: null
dependencies:
  depends_on: []
  blocks: [TSK-008]
---

# TSK-007: Implement Slack Message Formatter

## Objective

Create a Slack-specific message formatter that converts webhook payloads into Slack Block Kit format.

## Implementation Details

- Create `SlackFormatter` class in `services/webhook_formatters.py`
- Convert task events to Slack blocks with proper formatting
- Include action buttons for task links
- Support rich text and code blocks for error messages

## Acceptance Criteria

- [ ] SlackFormatter produces valid Block Kit JSON
- [ ] Messages include task status, title, description
- [ ] Error messages display in code blocks
- [ ] Unit tests cover all event types
