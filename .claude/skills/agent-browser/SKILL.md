---
name: agent-browser
description: |
  Headless browser automation CLI for AI agents. Use for web scraping, testing, form filling,
  screenshots, and any browser interaction. Triggers: "browse", "open website", "click button",
  "fill form", "screenshot", "scrape", "test login flow", "automate browser", "web automation".
---

# agent-browser

CLI browser automation optimized for AI. Use refs from snapshots for reliable element selection.
93% less context than Playwright MCP, 95% first-try success rate.

## Core Workflow

```bash
agent-browser open <url>           # Navigate
agent-browser snapshot -i          # Get interactive elements with refs
agent-browser click @e2            # Click by ref
agent-browser fill @e3 "text"      # Fill by ref
agent-browser snapshot -i          # Re-snapshot after changes
agent-browser close                # Close browser
```

## Snapshot (Most Important)

Get accessibility tree with element refs for deterministic selection:

```bash
agent-browser snapshot              # Full tree
agent-browser snapshot -i           # Interactive only (buttons, inputs, links)
agent-browser snapshot -c           # Compact (no empty elements)
agent-browser snapshot -d 3         # Limit depth
agent-browser snapshot -i -c --json # Combine for AI parsing
```

Output example:
```
- heading "Example Domain" [ref=e1]
- button "Submit" [ref=e2]
- textbox "Email" [ref=e3]
```

Use refs with `@` prefix: `agent-browser click @e2`

## Essential Commands

### Navigation
```bash
agent-browser open <url>            # Go to URL
agent-browser back                  # Go back
agent-browser forward               # Go forward
agent-browser reload                # Reload page
```

### Interaction
```bash
agent-browser click @ref            # Click element
agent-browser fill @ref "text"      # Clear and fill input
agent-browser type @ref "text"      # Type into element
agent-browser press Enter           # Press key
agent-browser select @ref "value"   # Select dropdown option
agent-browser check @ref            # Check checkbox
agent-browser hover @ref            # Hover element
agent-browser scroll down 500       # Scroll (up/down/left/right)
```

### Get Info
```bash
agent-browser get text @ref         # Get text content
agent-browser get value @ref        # Get input value
agent-browser get title             # Page title
agent-browser get url               # Current URL
```

### Check State
```bash
agent-browser is visible @ref       # Check visibility
agent-browser is enabled @ref       # Check if enabled
agent-browser is checked @ref       # Check if checked
```

### Wait
```bash
agent-browser wait @ref             # Wait for element visible
agent-browser wait 2000             # Wait milliseconds
agent-browser wait --text "Welcome" # Wait for text
agent-browser wait --load networkidle  # Wait for network idle
```

### Screenshot/Output
```bash
agent-browser screenshot            # Base64 to stdout
agent-browser screenshot page.png   # Save to file
agent-browser screenshot --full     # Full page
agent-browser pdf output.pdf        # Save as PDF
```

## Testing Patterns

### Login Flow Test
```bash
agent-browser open https://app.example.com/login
agent-browser snapshot -i
# Identify: textbox "Email" [ref=e1], textbox "Password" [ref=e2], button "Sign In" [ref=e3]
agent-browser fill @e1 "test@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3
agent-browser wait --url "**/dashboard"
agent-browser snapshot -i  # Verify dashboard loaded
agent-browser get text @e1  # Verify welcome message
```

### Form Submission Test
```bash
agent-browser open https://app.example.com/contact
agent-browser snapshot -i
agent-browser fill @e1 "John Doe"          # Name field
agent-browser fill @e2 "john@example.com"  # Email field
agent-browser fill @e3 "Hello world"       # Message field
agent-browser click @e4                     # Submit button
agent-browser wait --text "Thank you"       # Verify success message
agent-browser snapshot -i                   # Confirm state
```

### Authentication State (Reuse Login)
```bash
# Save auth after login
agent-browser open https://app.example.com/login
agent-browser snapshot -i && agent-browser fill @e1 "user@test.com"
agent-browser fill @e2 "password" && agent-browser click @e3
agent-browser wait --load networkidle
agent-browser state save auth.json          # Save cookies/storage

# Reuse in later tests
agent-browser state load auth.json          # Load saved state
agent-browser open https://app.example.com/dashboard  # Already logged in
```

### E2E Workflow Test
```bash
# Test complete user journey
agent-browser open https://shop.example.com
agent-browser snapshot -i

# Search for product
agent-browser fill @e1 "laptop"  # Search box
agent-browser click @e2          # Search button
agent-browser wait --load networkidle
agent-browser snapshot -i

# Add to cart
agent-browser click @e5          # First product
agent-browser wait --load networkidle
agent-browser snapshot -i
agent-browser click @e3          # Add to cart button
agent-browser wait --text "Added to cart"

# Checkout
agent-browser click @e4          # Cart icon
agent-browser snapshot -i
agent-browser click @e2          # Checkout button
agent-browser wait --url "**/checkout"
```

### Visual Regression
```bash
agent-browser open https://app.example.com/component
agent-browser wait --load networkidle
agent-browser screenshot baseline.png --full
# Make changes, then compare
agent-browser screenshot current.png --full
```

### Error State Testing
```bash
agent-browser open https://app.example.com/form
agent-browser snapshot -i
agent-browser click @e5  # Submit without filling required fields
agent-browser wait 500
agent-browser snapshot -i  # Capture error states
agent-browser get text @e1  # Verify error message text
```

## Parallel Testing with Sessions

```bash
# Run tests in isolated sessions
agent-browser --session test1 open https://app.example.com/feature-a
agent-browser --session test2 open https://app.example.com/feature-b

# Each session has separate cookies/storage
agent-browser --session test1 snapshot -i
agent-browser --session test2 snapshot -i

# List active sessions
agent-browser session list
```

## Debugging Tests

```bash
agent-browser open url --headed     # See browser window
agent-browser console               # View console messages
agent-browser errors                # View page errors
agent-browser highlight @e3         # Highlight element visually
agent-browser trace start           # Record trace
# ... run test steps ...
agent-browser trace stop trace.zip  # Save for analysis
```

## CSS/Text Selectors (Alternative)

When refs aren't available:

```bash
agent-browser click "#submit"
agent-browser click ".btn-primary"
agent-browser click "text=Sign In"
agent-browser find role button click --name "Submit"
```

## Options

| Flag | Description |
|------|-------------|
| `--session <name>` | Use isolated session |
| `--json` | JSON output (for parsing) |
| `--headed` | Show browser window |
| `--full` | Full page screenshot |

## Best Practices for Testing

1. **Always snapshot first** - Get refs before interacting
2. **Use `wait` after actions** - Ensure page state settles
3. **Re-snapshot after navigation** - Refs change between pages
4. **Use `--json` for assertions** - Parse structured output
5. **Save auth state** - Avoid repeated login flows
6. **Use sessions for parallel tests** - Isolated browser instances
7. **Use `--headed` for debugging** - See what's happening
