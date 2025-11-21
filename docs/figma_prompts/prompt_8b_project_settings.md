# Figma Make Prompt 8B: Project Settings Pages

Build this following engineering best practices:
- Write all code to WCAG AA accessibility standards
- Create and use reusable components throughout
- Use semantic HTML and proper component architecture
- Avoid absolute positioning; use flexbox/grid layouts
- Build actual code components, not static image SVGs
- Keep code clean, maintainable, and well-structured

You are Figma Make. Continue building the OmoiOS application. Foundation through User Settings (Prompt 8A) are already built. Now build the Project Settings Pages section (final section).

**PROJECT CONTEXT:**
OmoiOS is a spec-driven autonomous engineering platform. Use existing design system components and layout structure.

**PAGES TO BUILD:**

**1. Project Settings (`/projects/:id/settings`)**
- Layout: Settings header, left sidebar with tabs, main content (shows selected tab or redirects to General)
- Components: Header (project name, "Settings" title), Sidebar (General, Board, Phases, GitHub, Integrations tabs), Main content (shows selected tab)
- Content: Settings navigation menu, Tab content (varies by tab)
- States: Default (show General or redirect)
- Navigation: Switch settings tabs

**2. Board Configuration (`/projects/:id/settings/board`)**
- Layout: Settings header, form sections, save button
- Components: Board columns editor (add/edit/delete, drag to reorder), Column config (name, phase mapping, WIP limit), Ticket types config (add/edit/delete), Default ticket type selector, Initial status selector, Auto-transition settings, Save button
- Content: Board Columns (list with drag reorder, Column editor: Name, Phase Mapping dropdown, WIP Limit input, "+ Add Column"), Ticket Types (type list, Type editor: Name, Color, Icon, "+ Add Type"), Defaults (Default Ticket Type [component ▼], Initial Status [backlog ▼]), Auto-Transitions ([ ] Auto-transition when phase completes, [ ] Auto-unblock when blocker resolves)
- States: Loading, Editing, Saving, Saved, Error
- Navigation: Save → board page, Cancel → project settings

**3. Phase Configuration (`/projects/:id/settings/phases`)**
- Layout: Settings header, default phases list, custom phases list, "Create Custom Phase" button
- Components: Default phases list (read-only, "View Details" links), Custom phases list (editable, edit/delete buttons), Phase cards (phase ID, name, description, sequence order), "Create Custom Phase" button, Phase detail links
- Content: Default Phases (list of 8, each shows Phase ID, Name, Description, Sequence Order, [View Details] read-only), Custom Phases (list, each shows Phase ID, Name, [Edit] [Delete]), "+ Create Custom Phase" button, "Import from YAML" button
- States: Loading, Loaded, Empty Custom ("No custom phases"), Error
- Navigation: View default details, Edit/Delete custom, Create custom, Import from YAML

**4. GitHub Integration (`/projects/:id/settings/github`)**
- Layout: Settings header, GitHub connection status, repository selector, webhook config, auto-sync settings
- Components: Connection status card (connected/disconnected), "Authorize GitHub" button (if not connected), Repository selector dropdown (if connected), Webhook config section, Auto-sync settings (checkboxes: issues, commits, PRs, workflows), Connection test button, Disconnect/reauthorize buttons
- Content: Connection Status ("Connected" badge or "Not Connected", GitHub username/org), Repository Selection (dropdown [Select Repository ▼], Selected repo name/URL), Webhook Config (URL read-only, Status "Active"/"Inactive", [Test Webhook]), Auto-Sync ([ ] Sync Issues, [ ] Sync Commits, [ ] Sync Pull Requests, [ ] Sync Workflow Runs), Actions ([Disconnect GitHub] [Reauthorize GitHub])
- States: Not Connected (show "Authorize GitHub" CTA), Connected (show selector and settings), Testing, Error
- Navigation: Authorize GitHub (OAuth), Select repository, Configure webhook, Toggle auto-sync, Test connection, Disconnect/reauthorize

**Requirements:**
- Use existing settings layout structure (sidebar navigation)
- Create reusable form components
- Implement board columns editor (drag-and-drop for reordering)
- Add ticket types configuration UI
- Create phase configuration lists (default vs custom)
- Implement GitHub integration UI (connection status, repository selector)
- Add webhook configuration section
- Include auto-sync checkboxes
- Add connection test functionality
- Implement OAuth flow initiation
- Include loading skeletons, empty states, error handling
- Make all pages responsive
- Include toast notifications
- Implement confirmation modals for destructive actions
- Add form validation
- Create reusable settings sidebar component

Generate all 4 pages as separate React components with full functionality, proper state management, and navigation. This completes the entire OmoiOS application UI.

