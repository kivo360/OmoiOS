# 12 · Next Steps — Better Auth First

Revised incremental path assuming Better Auth is the auth layer from day one. Each step is roughly one day of focused work; none requires a rewrite of the previous.

## Phase 1 — Auth foundation (days 1–3)

**1. Install Better Auth + core plugins.**
```bash
pnpm add better-auth @better-auth/api-key jose
```
Wire `auth.ts` with `organization`, `apiKey` (two configs), `jwt`, `genericOAuth`. Enable `teams: { enabled: true }`. Copy the config from [`13 §3`](./13-better-auth-integration.md).

**2. Define the access control graph.**
Write `permissions.ts` with the five custom resources (`session_exec`, `environment`, `secret`, `connection`, `webhook`) and four roles (`owner`, `admin`, `editor`, `viewer`). Import and pass into `organization()`. See [`13 §4`](./13-better-auth-integration.md).

**3. Generate and run the schema migration.**
```bash
pnpm better-auth generate
pnpm drizzle-kit push          # or prisma migrate dev
```
Confirm `organization`, `member`, `team`, `teamMember`, `apiKey`, `jwks` tables exist.

**4. Ship the `resolveAuth` middleware.**
One function, four token types, one `AuthContext` output. Every future route uses this. See [`13 §9`](./13-better-auth-integration.md).

**✅ Exit criteria for Phase 1:** a dashboard user can sign up, create an org, invite a teammate, mint a platform API key, and call a stub `/v1/organizations/{org}/ping` endpoint with either the platform key *or* their JWT *or* their session cookie and get the same response.

## Phase 2 — Session API, single-tenant shape (days 4–6)

**5. Add our own tables: `session_exec`, `artifact`, `environment`.**
Separate migration, FK to `organization.id`. `workspace_id` is a `team.id`.

**6. Implement the sessions API.**
Routes at `/v1/organizations/{org}/sessions/*`. Every handler calls `resolveAuth` first, then `ac.hasPermission({ role, permissions: { session_exec: ["create"] } })`. See [`03`](./03-sessions-api.md) for endpoints.

**7. Stub the sandbox.**
Don't implement Modal yet. A `POST /sessions` writes a row and returns `status: "pending"`; a background job (or just a `setTimeout`) flips it to `"running"` and streams fake events over SSE. Proves the surface without paying for compute.

**8. Ship the TypeScript SDK against this.**
See [`09 §TypeScript`](./09-sdks.md). Use it from a local script to dogfood the shape before anyone sees it. **The SDK shape is your public contract — lock it now.**

**✅ Exit criteria for Phase 2:** `pnpm test` runs an integration script that creates a session, streams 5 fake events over SSE, cancels it, and asserts the final status. RBAC is enforced (a `viewer` can't call `cancel`).

## Phase 3 — Session tokens + Credential Broker (days 7–10)

**9. Mint session tokens on `POST /sessions`.**
`auth.api.createApiKey({ configId: "session", … })`. Pass the plaintext into the sandbox's env. See [`13 §5c`](./13-better-auth-integration.md).

**10. Configure user-linked OAuth providers (Model A, zero custom code).**
Add `socialProviders: { github, gitlab, linear }` to the top-level Better Auth config. Expose a `/link/github` route in the dashboard that calls `authClient.linkSocial`. Token refresh is automatic via `auth.api.getAccessToken`. See [`13 §7 Model A`](./13-better-auth-integration.md).

**10b. (Optional, ship when first customer asks) GitHub App installation flow.**
For org-wide repo access that survives users leaving. One table (`githubInstallation`), one setup handler, `@octokit/auth-app` for minting. See [`13 §7 Model B`](./13-better-auth-integration.md).

**11. Build `credentialBroker` custom plugin.**
`GET /broker/creds/:provider` route with three binding kinds: `github_app` (Model B, mint installation token), `user_oauth` (Model A, delegate to `auth.api.getAccessToken`), `bearer_secret` (static API keys). Environment declares which kind per provider. See [`13 §8`](./13-better-auth-integration.md).

**12. Real sandbox, minimal.**
Swap the fake event stream for an actual Modal sandbox that calls the Broker for GitHub creds and clones a repo. The first "real" agent run.

**✅ Exit criteria for Phase 3:** an agent session can clone a customer repo through the Broker without your platform code ever touching the customer's raw GitHub refresh token.

## Phase 4 — Multi-tenant hardening (days 11–14)

**13. Egress proxy.**
Per-tenant allowlist enforced at the network layer. See [`05`](./05-environments.md). This is the piece that gates whether you can safely onboard real customers.

**14. Environment versioning + build pipeline.**
`POST /environments/:id/versions` with Dockerfile upload. Snapshots stored in a registry. Sessions pin to `env_…@vN`.

**15. Python SDK.**
Mirror the TS surface. See [`09 §Python`](./09-sdks.md). Ship to PyPI under a scoped name.

**16. Webhook dispatcher.**
Custom plugin with HMAC signing + retry-with-backoff queue. See [`06`](./06-streaming-and-webhooks.md).

**✅ Exit criteria for Phase 4:** a second tenant signs up, authorizes their GitHub, kicks off a session — and there is no code path where their session can read the first tenant's env, secrets, or egress to an un-allowlisted host.

## Phase 5 — Client surfaces (days 15–20)

**17. Slack bot reference implementation.** See [`10 §1`](./10-client-patterns.md).
**18. GitHub Action reference implementation.** See [`10 §2`](./10-client-patterns.md).
**19. Web client + hosted editor iframe.** See [`10 §3`](./10-client-patterns.md).
**20. Plasmo Chrome extension scaffold.** See [`11`](./11-chrome-extension-plasmo.md). This is your demo artifact.

## Phase 6 — Production readiness

**21. Quota enforcement.** Monthly aggregates, soft warn at 80%, hard 429 at 100%. See [`08`](./08-quotas-and-errors.md).
**22. Billing + usage endpoint.** Surface per-org compute seconds + token usage. Wire to Stripe (Better Auth has a Stripe plugin if helpful).
**23. Audit log.** Every `broker.mint`, every `secret.read`, every RBAC denial logged with tenant + subject + time.

---

## Reflective question

**Looking at this path: which phase is the one you'd be tempted to skip in a hackathon demo — and which phase would the customer notice missing in the first week of production?**

Those are usually different phases, and the gap between them is the riskiest part of the build.
