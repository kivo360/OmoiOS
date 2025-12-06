# 8 User Personas

**Part of**: [User Journey Documentation](./README.md)

---
## User Personas & Use Cases

### Engineering Manager
**Primary Use Case**: Monitor multiple projects, approve phase transitions, review PRs, manage organizations

**Typical Flow:**
1. Logs in → Sees dashboard overview with Guardian status indicator
2. Switches organization context (if member of multiple orgs)
3. Checks System Health dashboard → Views overall monitoring status
4. Reviews pending approvals → Approves phase transitions
5. Monitors agent activity → Sees Guardian interventions and alignment scores
6. Reviews intervention history → Checks success rates and recovery times
7. Reviews PRs → Approves merges
8. Checks statistics → Views project health and monitoring insights
9. Manages organization settings → Updates resource limits
10. Generates API keys → For CI/CD integration

**Time Investment**: 10-15 minutes per day for strategic oversight

**Monitoring Touchpoints:**
- Header Guardian indicator for quick system health check
- System Health dashboard for detailed monitoring status
- Intervention alerts in notification center
- Alignment scores in agent list view

**Organization Management:**
- View organization members and roles
- Configure resource limits (max agents, runtime hours)
- Manage organization settings
- View organization-level statistics
- Generate organization-scoped API keys

### Senior IC Engineer
**Primary Use Case**: Create feature requests, review code changes, provide technical guidance

**Typical Flow:**
1. Creates feature request → "Add payment processing"
2. Reviews generated spec → Edits requirements/design
3. Approves plan → System executes autonomously
4. Reviews code changes → Approves PRs
5. Provides feedback → Agents adjust

**Time Investment**: 30-60 minutes per feature (mostly review time)

### CTO/Technical Lead
**Primary Use Case**: Set up projects, configure workflows, monitor system health, manage organizations

**Typical Flow:**
1. Creates organization → Sets up multi-tenant workspace
2. Sets up new project → AI-assisted exploration
3. Configures approval gates → Sets phase gate requirements
4. Configures workspace isolation → Sets workspace types and policies
5. Configures Guardian thresholds → Sets alignment score thresholds and intervention timing
6. Configures monitoring policies → Sets notification preferences and escalation rules
7. Monitors system health → Views System Health dashboard with real-time trajectory analyses
8. Reviews monitoring insights → Analyzes intervention effectiveness and pattern learning
9. Reviews cost tracking → Optimizes agent usage
10. Reviews cross-project patterns → Views organization-wide learning insights
11. Manages API keys → For programmatic access
12. Reviews workspace isolation → Checks agent workspace health

**Time Investment**: Initial setup (1-2 hours), ongoing monitoring (15 min/day)

**Monitoring Configuration:**
- Set alignment score thresholds (default: 70%)
- Configure intervention timing (default: 60s cycles)
- Set notification preferences for monitoring alerts
- Define escalation rules for critical alignment drops
- Review and adjust adaptive learning thresholds

**Organization Setup:**
- Create organization with unique slug
- Set resource limits (max concurrent agents, max runtime hours)
- Configure organization settings (JSONB)
- Set billing email
- Manage organization members (future)
- Configure RBAC roles and permissions (future)

---


---

**Next**: See [README.md](./README.md) for complete documentation index.
