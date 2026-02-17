# OmoiOS User Journey Documentation

**Created**: 2025-01-30
**Status**: User Journey Documentation
**Purpose**: Complete user flow from onboarding to feature completion

This documentation has been split into focused sections for easier navigation and maintenance.

---

## The Core Promise

> **Start a feature before bed. Wake up to a PR.**

Let AI run overnight and finish your software for you. Describe what you want, approve a plan, go to sleep. Wake up to a completed PR ready for review.

**See [00a_demo_flow.md](./00a_demo_flow.md) for the video demo script.**

---

## Document Structure

### Demo & Overview
- **[00_overview.md](./00_overview.md)** - The 60-Second Story, Core Promise, Dashboard Layout, Key User Interactions
- **[00a_demo_flow.md](./00a_demo_flow.md)** - Video Demo Script (90 seconds), Scene Breakdowns, Talking Points

### Core Journey
- **[01_onboarding.md](./01_onboarding.md)** - Phase 1: Onboarding & First Project Setup
- **[02_feature_planning.md](./02_feature_planning.md)** - Phase 2: Feature Request & Planning
- **[03_execution_monitoring.md](./03_execution_monitoring.md)** - Phase 3: Autonomous Execution & Monitoring (Sandbox List, Sandbox Detail, Event Deduplication)
- **[04_approvals_completion.md](./04_approvals_completion.md)** - Phase 4: Approval Gates & Phase Transitions
- **[05_optimization.md](./05_optimization.md)** - Phase 5: Ongoing Monitoring & Optimization

### System Documentation
- **[06_key_interactions.md](./06_key_interactions.md)** - Key User Interactions (Command Palette, Real-Time Updates, Intervention Tools, Spec Management)
- **[06a_monitoring_system.md](./06a_monitoring_system.md)** - Guardian & Monitoring System (System Health, Trajectory Analysis, Interventions, Pattern Learning)
- **[07_phase_system.md](./07_phase_system.md)** - Phase System Overview (Default Phases, Custom Phases, Discovery-Based Branching)
- **[08_user_personas.md](./08_user_personas.md)** - User Personas & Use Cases (Engineering Manager, Senior IC Engineer, CTO/Technical Lead)
- **[09_design_principles.md](./09_design_principles.md)** - Visual Design Principles & Success Metrics

### Cost & Resource Management
- **[11_cost_memory_management.md](./11_cost_memory_management.md)** - Cost & Memory Management:
  - Cost Dashboard & Monitoring
  - Budget Management & Alerts
  - Cost Forecasting
  - Agent Memory Search & Patterns
  - Pattern Extraction & Learning
  - Memory Insights Dashboard

### Billing & Subscriptions
- **[12_billing_subscription.md](./12_billing_subscription.md)** - Billing & Subscription Management:
  - Subscription Tiers (Free, Pro, Team, BYO Keys, Lifetime, Enterprise)
  - Credit Purchases via Stripe Checkout
  - Payment Method Management
  - Invoice History & Usage Tracking

### Public & Marketing Pages
- **[13_public_marketing_pages.md](./13_public_marketing_pages.md)** - Public Pages & Conversion Funnel:
  - Landing Page Conversion
  - Pricing Evaluation
  - Blog Discovery
  - Documentation Exploration
  - Showcase Sharing
  - OAuth Callback Flow

### Settings & Personalization
- **[14_settings_personalization.md](./14_settings_personalization.md)** - Settings, Personalization & Activity:
  - Appearance Customization (theme, colors, fonts, layout)
  - Notification Configuration (per-event channels, digest, quiet hours)
  - Security Management (password, 2FA, account deletion)
  - Integration Management (GitHub OAuth)
  - Activity Timeline (real-time system event feed)

### Prototype & Diagnostic
- **[15_prototype_diagnostic.md](./15_prototype_diagnostic.md)** - Prototype Workspace & Diagnostic Reasoning:
  - Prototype Workspace (/prototype) — framework selection, split-view prompt + live preview
  - Diagnostic Reasoning (/diagnostic/[entityType]/[entityId]) — decision timeline, evidence, alternatives

### Additional Information
- **[10_additional_flows.md](./10_additional_flows.md)** - Additional Flows & Edge Cases:
  - Error Handling & Failure Recovery
  - Notification & Alert Flows
  - Settings & Configuration
  - Multi-User Collaboration
  - Organization Management (create, members, settings)
  - Agent Spawning & Workspaces
  - Keyboard Shortcuts & Accessibility
  - Mobile & Responsive Design
  - Troubleshooting & Support
  - Export & Import Flows

## Quick Navigation

**Getting Started:**
1. Read [00_overview.md](./00_overview.md) for dashboard layout and key interactions
2. Follow [01_onboarding.md](./01_onboarding.md) for first-time setup
3. Review [02_feature_planning.md](./02_feature_planning.md) to understand feature creation

**Understanding the System:**
- [06a_monitoring_system.md](./06a_monitoring_system.md) - How the Guardian & monitoring system works
- [07_phase_system.md](./07_phase_system.md) - How phases work
- [08_user_personas.md](./08_user_personas.md) - Who uses OmoiOS and how

**Daily Operations:**
- [03_execution_monitoring.md](./03_execution_monitoring.md) - Monitoring agent work
- [04_approvals_completion.md](./04_approvals_completion.md) - Approving work and completing features
- [05_optimization.md](./05_optimization.md) - Ongoing monitoring and optimization

**Cost & Billing:**
- [11_cost_memory_management.md](./11_cost_memory_management.md) - Cost tracking, budgets, and agent learning
- [12_billing_subscription.md](./12_billing_subscription.md) - Subscription management, credit purchases, invoices

**Public & Settings:**
- [13_public_marketing_pages.md](./13_public_marketing_pages.md) - Landing page, pricing, blog, docs, showcase
- [14_settings_personalization.md](./14_settings_personalization.md) - Appearance, notifications, security, activity timeline

**Advanced Topics:**
- [15_prototype_diagnostic.md](./15_prototype_diagnostic.md) - Prototype workspace, diagnostic reasoning chain
- [10_additional_flows.md](./10_additional_flows.md) - Edge cases, error handling, collaboration, org management
- [09_design_principles.md](./09_design_principles.md) - Design system and success metrics

## Related Documentation

- [Page Flows Documentation](../page_flows/README.md) - Detailed page-by-page navigation flows
- [Page Architecture](../page_architecture.md) - Complete page architecture specifications
- [Design System](../design_system.md) - UI/UX design system guide
- [App Overview](../app_overview.md) - High-level application overview
