# 05 · Environments

An environment is everything the agent needs to run, **minus the prompt**. Three build modes, every version immutable, egress declared upfront.

## Build modes

| Mode | Speed | When to use |
|---|---|---|
| `platform` | fastest | Pre-built images: `node-20`, `python-3.12`, `rust-stable`. Zero build, pre-warmed pool. |
| `dockerfile` | flexible | Customer `POST`s a Dockerfile + context. Platform builds, scans, signs, stores as snapshot. |
| `snapshot` | fastest warm | Customer attaches a setup script; platform snapshots the resulting FS. Best for heavy setup (DB seed, repo clone, deps). |

## Egress model

Every sandbox egresses through a per-tenant proxy. The environment declares an allowlist; anything else is denied and logged. This is how you prevent an agent with prompt-injected instructions from exfiltrating to attacker-controlled domains.

```json
"egress": {
  "allowed_hosts": [
    "api.github.com",
    "codeload.github.com",
    "registry.npmjs.org",
    "*.internal.acme.com"
  ],
  "allowed_ports": [443, 5432],
  "dns_over_proxy": true,
  "deny_by_default": true
}
```

## Versioning

- Every mutation produces a new `version`. Old versions remain accessible.
- Sessions pin to `env_Jk2p@v7` at creation time.
- Rolling update requires explicit `environment_id: env_Jk2p` (no version) on create — opt-in, not default.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/organizations/{org}/environments` | Create. |
| `GET` | `/v1/organizations/{org}/environments` | List. |
| `GET` | `/v1/organizations/{org}/environments/{id}` | Current version. |
| `GET` | `/v1/organizations/{org}/environments/{id}/versions/{n}` | Pinned version. |
| `POST` | `/v1/organizations/{org}/environments/{id}/versions` | Build a new version. |
