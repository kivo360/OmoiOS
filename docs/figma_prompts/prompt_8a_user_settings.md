# Figma Make Prompt 8A: User Settings Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation through Agents & Diagnostic are already built. Now build the User Settings Pages section.

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use existing design system components and layout structure.

**PAGES TO BUILD:**

**1. User Settings (`/settings`)**
- Layout: Settings header, left sidebar with sections, main content (redirects to Profile)
- Components: Header ("Settings" title), Sidebar (Profile, API Keys, Sessions, Notifications, Appearance), Main content (redirects to Profile)
- Content: Settings navigation menu, Brief descriptions
- States: Default (redirect to Profile)
- Navigation: Click section → section page

**2. Profile Settings (`/settings/profile`)**
- Layout: Settings header, form sections, save button
- Components: Profile form (display name, email, avatar upload), Email preferences, Timezone selector, Language selector, Theme selector (light/dark/system), Save button
- Content: Display Name input, Email (read-only, change email link), Avatar upload, Email Preferences [ ] In-app [ ] Email [ ] Slack, Timezone [UTC ▼], Language [English ▼], Theme [Light] [Dark] [System]
- States: Loading, Editing, Saving, Saved, Error
- Navigation: Save → `/settings`, Change email → email flow

**3. API Keys (`/settings/api-keys`)**
- Layout: Page header, API keys table, key detail modal
- Components: Header ("API Keys", "Generate Key" button), Keys table (name, scope, created, last used, actions), Key detail modal (full key, scopes, usage), Revoke confirmation
- Content: Table shows Key Name, Scope "Project: auth-system" or "Organization: acme-corp", Created "2 days ago", Last Used "1 hour ago" or "Never", Actions [View] [Revoke], Empty state "No API keys yet"
- States: Loading, Empty, Populated, Revoking, Error
- Navigation: "Generate Key" → `/settings/api-keys/new`, Click row → details, Copy key, Revoke, Filter

**4. Create API Key (`/settings/api-keys/new`)**
- Layout: Centered form layout
- Components: Creation form, Key name input, Scope selector (Project, Organization, Global), Scope target dropdown, Permissions checklist (read, write, admin), Expiration selector, Generate button, Generated key display
- Content: Key Name [My CI/CD Key], Scope [Project ▼] [Organization] [Global], Scope Target [auth-system ▼], Permissions [ ] Read [ ] Write [ ] Admin, Expiration [Never ▼] [30 days] [90 days] [Custom], Generate button, After generation: Key value (masked, copy button), Warning "This key will only be shown once", "Done" button
- States: Empty, Generating, Generated, Error
- Navigation: Generate → show key, Copy, Done → `/settings/api-keys`

**5. API Key Detail (`/settings/api-keys/:id`)**
- Layout: Key header, detail sections, usage stats, actions
- Components: Header (key name, status badge), Details (scope, permissions, created, expires), Usage stats (requests, last used, rate limits), Actions (regenerate, revoke), Revoke confirmation
- Content: Key Name/Status, Scope "Project: auth-system", Permissions "Read, Write", Created "2 days ago", Expires "Never" or date, Total Requests "1,234", Last Used "1 hour ago", Rate Limit "1000/hour", Actions [Regenerate] [Revoke]
- States: Loading, Loaded, Revoked (disabled), Error
- Navigation: View details/stats, Regenerate, Revoke, Copy key

**6. Active Sessions (`/settings/sessions`)**
- Layout: Page header, sessions table, session detail modal
- Components: Header ("Active Sessions"), Sessions table (device, location, IP, last active, actions), Session detail modal, Revoke confirmation
- Content: Table shows Device "Chrome on macOS", Location "San Francisco, CA", IP "192.168.1.1", Last Active "2 hours ago", Current Session indicator, Actions [View] [Revoke], Empty "No active sessions"
- States: Loading, Loaded, Revoking, Error
- Navigation: View details, Revoke session, Revoke all others, Filter

**Requirements:**
- Use settings layout structure (sidebar navigation)
- Create reusable form components
- Implement avatar upload component
- Create timezone/language/theme selectors
- Implement API keys table component
- Add key generation form with scope/permissions
- Create session management table
- Include loading skeletons, empty states, error handling
- Make all pages responsive
- Include toast notifications
- Implement confirmation modals for destructive actions
- Add form validation
- Create reusable settings sidebar component

Generate all 6 pages as separate React components with full functionality, proper state management, and navigation.

