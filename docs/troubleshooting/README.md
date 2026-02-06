# Troubleshooting

Operational guides for diagnosing and fixing issues encountered during development.

## Contents

| Document | Description |
|----------|-------------|
| [macOS Memory Audit (2026-02-05)](macos_memory_audit_2026-02-05.md) | System memory analysis — identified Next.js dev server (2.8 GB idle), Brave extensions (640 MB for 6 extension processes), and 32 GB swap usage. Before/after cleanup metrics and prevention strategies. |
| [Memory Management Strategy](memory_management_strategy.md) | Strategies for managing macOS memory pressure with background tooling, process policies, and a Rust daemon design. |
| [SQLAlchemy DetachedInstanceError Fixes](detached_instance_fixes.md) | Fixes for `DetachedInstanceError` issues where SQLAlchemy model instances were used outside session context. |
| [OAuth Redirect URI Fix](oauth_redirect_uri_fix.md) | Troubleshooting guide for `redirect_uri is not associated with this application` errors. |
| [OAuth Redirect URI Quick Fix](oauth_redirect_uri_quick_fix.md) | 5-step quick fix for OAuth redirect URI configuration issues. |
