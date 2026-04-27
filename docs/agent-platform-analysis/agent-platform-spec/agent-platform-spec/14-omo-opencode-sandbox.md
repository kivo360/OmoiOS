# 14 · OmO + OpenCode — Sandbox Configuration

Research notes on how **oh-my-openagent** (OmO — formerly `oh-my-opencode`, `code-yeongyu/oh-my-openagent`) and its underlying OpenCode runtime configure themselves, and how to wire that cleanly into the platform's `Environment` resource.

> Sources: DeepWiki on `code-yeongyu/oh-my-openagent` and `sst/opencode`, April 2026. Some provider env vars are inferred from the `PROVIDER_API_KEY` convention; always verify against the specific provider at sandbox bootstrap time.

## 1 · What OmO is, and what sits under it

- **OpenCode** (`sst/opencode`) is the base terminal-based AI coding agent. Single-agent, one model at a time. Reads config from `opencode.json` and auth from `~/.local/share/opencode/auth.json`.
- **OmO** is a harness on top of OpenCode. Adds:
  - 11 specialised agents (Sisyphus, Hephaestus, Oracle, Librarian, Explore, Multimodal-Looker, Prometheus, Metis, Momus, Atlas, Sisyphus-Junior) — each with its own role, default model, and fallback chain.
  - Model resolution with per-agent fallback chains — if Claude Opus is rate-limited, the agent transparently drops to Kimi K2.5 or GPT-5.4.
  - Categories (`quick`, `deep`, `visual-engineering`, `writing`, `git`) — task-level routing instead of per-agent.
  - Parallel background task execution with per-provider and per-model concurrency caps.
  - Its own config file `oh-my-openagent.jsonc` layered on top of `opencode.json`.

**Two config files, layered:**
- `~/.config/opencode/opencode.json` — provider/model surface (OpenCode's)
- `~/.config/opencode/oh-my-openagent.jsonc` — agent/category routing (OmO's, sits on top)

Project-level override: `.opencode/*.json[c]` in the working dir beats the user-level file.

## 2 · Provider authentication in a sandbox

Two ways to authenticate without running `opencode auth login` interactively.

### Option A — environment variables (simplest)

Set these in the sandbox at boot. OpenCode reads them directly, or `opencode.json` can reference them via `{env:VAR_NAME}` substitution.

| Provider | ID | API key env var | Extra |
|---|---|---|---|
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `baseURL` via `opencode.json` |
| OpenAI | `openai` | `OPENAI_API_KEY` | `baseURL` via `opencode.json` |
| Google Vertex | `google` | `GOOGLE_APPLICATION_CREDENTIALS` (path to JSON key) | `GOOGLE_CLOUD_PROJECT`, `VERTEX_LOCATION` |
| OpenCode Go | `opencode` | `OPENCODE_API_KEY` | — |
| Groq | `groq` | `GROQ_API_KEY` | — |
| xAI | `xai` | `XAI_API_KEY` | — |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | sets `HTTP-Referer`, `X-Title` headers |
| Vercel AI Gateway | `vercel` | `VERCEL_API_KEY` | sets `http-referer`, `x-title` headers |
| GitHub Copilot | `github-copilot` | — (OAuth; pre-populate `auth.json`) | — |
| Z.ai Coding Plan | `zai-coding-plan` | use `auth.json` or `{env:ZAI_API_KEY}` in `opencode.json` | — |
| Kimi for Coding | `kimi-for-coding` | use `auth.json` or `{env:KIMI_API_KEY}` in `opencode.json` | — |
| Venice | `venice` | use `auth.json` or `{env:VENICE_API_KEY}` in `opencode.json` | — |
| Moonshot AI | `moonshotai` | use `auth.json` or `{env:MOONSHOT_API_KEY}` in `opencode.json` | — |
| Ollama (local) | `ollama` | none (unauthenticated local) | `baseURL` via `opencode.json` |

### Option B — pre-populated `auth.json`

OpenCode persists post-login credentials to `~/.local/share/opencode/auth.json`. Shape:

```json
{
  "anthropic":       { "type": "api",   "key": "sk-ant-…" },
  "openai":          { "type": "api",   "key": "sk-…" },
  "opencode":        { "type": "api",   "key": "oc_…" },
  "zai-coding-plan": { "type": "api",   "key": "zai_…" },
  "github-copilot":  { "type": "oauth", "refresh": "…",  "access": "…", "expires": 1713… }
}
```

Write this file into the sandbox at boot instead of — or alongside — env vars. Cleaner for GitHub Copilot (OAuth) and for providers not keyed on standard env var names. Permissions must be `0600`.

### Recommended hybrid

- **API-key providers (Anthropic, OpenAI, OpenCode Go, Groq, xAI, OpenRouter, Vercel, Z.ai, Kimi, Venice, Moonshot):** env vars. Inject from the platform's Credential Broker at boot.
- **OAuth providers (GitHub Copilot):** pre-populated `auth.json` (short-lived access token minted by the Broker).
- **Google Vertex:** pre-populated service-account JSON file at `$GOOGLE_APPLICATION_CREDENTIALS`.

## 3 · Model resolution order

Every time an agent needs a model, OmO resolves it in this exact order. **First hit wins.**

1. **Per-agent user override** — `agents.<name>.model` in `oh-my-openagent.jsonc`
2. **Category default** — if the task was delegated via a category, the category's `model`
3. **User `fallback_models`** — tried before any built-in chain
4. **Built-in fallback chain** — hard-coded per agent in `src/shared/model-requirements.ts`
5. **OpenCode's system default**

When a model in the chain fails with rate-limit / quota / 5xx, OmO advances to the next entry and retries. Per-agent, not per-task.

## 4 · Fallback format — `fallback_models`

Accepts a mixed array of plain strings and objects. Object entries let you override generation settings *only when that fallback is selected*.

```jsonc
{
  "agents": {
    "sisyphus": {
      "model": "anthropic/claude-opus-4-7",
      "fallback_models": [
        "openai/gpt-5.4",
        {
          "model": "anthropic/claude-sonnet-4-6",
          "variant": "high",
          "thinking": { "type": "enabled", "budgetTokens": 12000 }
        },
        {
          "model": "openai/gpt-5.3-codex",
          "reasoningEffort": "high",
          "temperature": 0.2,
          "top_p": 0.95,
          "maxTokens": 8192
        }
      ]
    }
  }
}
```

Per-fallback object fields: `variant`, `reasoningEffort`, `temperature`, `top_p`, `maxTokens`, `thinking`.

## 5 · Default fallback chains (from `src/shared/model-requirements.ts`)

Each entry is `model (providers in preference order)`. OmO tries providers left to right for a given model before advancing to the next model.

- **Sisyphus** — main orchestrator
  `claude-opus-4-7 (anthropic, github-copilot, opencode, vercel)` → `kimi-k2.5 (opencode-go, vercel)` → `k2p5 (kimi-for-coding)` → `kimi-k2.5 (opencode, moonshotai, moonshotai-cn, firmware, ollama-cloud, aihubmix, vercel)` → `gpt-5.4 (openai, github-copilot, opencode, vercel)` → `glm-5 (zai-coding-plan, opencode, vercel)` → `big-pickle (opencode)`

- **Hephaestus** — deep worker, code-heavy
  `gpt-5.4 (openai, github-copilot, venice, opencode, vercel)`
  *(single-family — do not substitute Claude; prompt is GPT-specific)*

- **Oracle** — architecture consultant, read-only
  `gpt-5.4 (openai, …)` → `gemini-3.1-pro (google, …)` → `claude-opus-4-7 (anthropic, …)` → `glm-5 (opencode-go, vercel)`

- **Librarian** — docs/reference search
  `minimax-m2.7 (opencode-go, vercel)` → `minimax-m2.7-highspeed (opencode, vercel)` → `claude-haiku-4-5 (anthropic, opencode, vercel)` → `gpt-5-nano (opencode, vercel)`

- **Explore** — fast codebase grep
  `grok-code-fast-1 (github-copilot, xai, vercel)` → `minimax-m2.7-highspeed (opencode-go, vercel)` → `minimax-m2.7 (opencode, vercel)` → `claude-haiku-4-5 (anthropic, opencode, vercel)` → `gpt-5-nano (opencode, vercel)`

- **Multimodal-Looker** — vision
  `gpt-5.4 (openai, opencode, vercel)` → `kimi-k2.5 (opencode-go, vercel)` → `glm-4.6v (zai-coding-plan, vercel)` → `gpt-5-nano (openai, github-copilot, opencode, vercel)`

- **Prometheus** — planner
  `claude-opus-4-7 (anthropic, …)` → `gpt-5.4 (openai, …)` → `glm-5 (opencode-go, vercel)` → `gemini-3.1-pro (google, …)`

- **Metis** — plan consultant
  `claude-opus-4-7 (anthropic, …)` → `gpt-5.4 (openai, …)` → `glm-5 (opencode-go, vercel)` → `k2p5 (kimi-for-coding)`

- **Momus** — plan reviewer
  `gpt-5.4 (openai, …)` → `claude-opus-4-7 (anthropic, …)` → `gemini-3.1-pro (google, …)` → `glm-5 (opencode-go, vercel)`

- **Atlas** — todo orchestrator
  `claude-sonnet-4-6 (anthropic, …)` → `kimi-k2.5 (opencode-go, vercel)` → `gpt-5.4 (openai, …)` → `minimax-m2.7 (opencode-go, vercel)`

- **Sisyphus-Junior** — delegated worker (category-dependent, below is the task fallback)
  `claude-sonnet-4-6 (anthropic, …)` → `kimi-k2.5 (opencode-go, vercel)` → `gpt-5.4 (openai, …)` → `minimax-m2.7 (opencode-go, vercel)` → `big-pickle (opencode)`

**Family-sensitive agents:** Sisyphus and Hephaestus have prompts tuned to one family. Sisyphus expects Claude-class instruction-following; Hephaestus expects GPT-class codex behavior. Cross-family override degrades output. Prometheus, Atlas, Oracle, Momus self-detect via `isGptModel()` and swap prompts.

## 6 · Categories

Instead of binding a task to an agent, you can delegate by category via `task()`. The category's `model` is used for whatever sub-agent runs the task.

Defaults worth knowing (from the config example):

```jsonc
"categories": {
  "quick":               { "model": "opencode/gpt-5-nano" },
  "unspecified-low":     { "model": "anthropic/claude-sonnet-4-6" },
  "unspecified-high":    { "model": "anthropic/claude-opus-4-7", "variant": "max" },
  "writing":             { "model": "google/gemini-3-flash" },
  "visual-engineering":  { "model": "google/gemini-3.1-pro", "variant": "high" },
  "git":                 { "model": "opencode/gpt-5-nano",
                           "description": "All git operations",
                           "prompt_append": "Focus on atomic commits, clear messages, and safe operations." },
  "deep":                { "model": "anthropic/claude-opus-4-7" }
}
```

For self-hosted setups, map a category to a local model and every task routed to that category uses it:

```jsonc
"categories": {
  "quick": { "model": "ollama/qwen2.5-coder:7b" },
  "deep":  { "model": "ollama/qwen2.5-coder:32b" }
}
```

## 7 · Self-hosted / OpenAI-compatible providers

Define in `opencode.json` (OpenCode's file, not OmO's):

```json
{
  "provider": {
    "local-llama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "http://localhost:11434/v1",
        "apiKey": "{env:OLLAMA_API_KEY}"
      },
      "models": {
        "qwen2.5-coder:32b": {},
        "qwen2.5-coder:7b":  {}
      }
    }
  }
}
```

Then reference as `local-llama/qwen2.5-coder:32b` in OmO config. `@ai-sdk/openai-compatible` targets `/v1/chat/completions`; use `@ai-sdk/openai` for `/v1/responses` endpoints.

## 8 · Concurrency

OmO caps parallel background tasks per provider and per model — matters a lot in a sandbox to avoid hammering one provider and tripping rate limits.

```jsonc
"background_task": {
  "providerConcurrency": {
    "anthropic":       3,
    "openai":          3,
    "opencode":        10,
    "zai-coding-plan": 10
  },
  "modelConcurrency": {
    "anthropic/claude-opus-4-7": 2,
    "opencode/gpt-5-nano":       20
  }
}
```

## 9 · Mapping into the platform's `Environment` resource

The `Environment` object from [`02 §Environment`](./02-resources.md) already has an `env` block and an `image`. Here's how OmO-flavored environments populate both:

```json
{
  "id": "env_omo_default",
  "version": 1,
  "image": {
    "kind": "platform",
    "ref": "omo-runtime:2026-04"
  },
  "env": {
    "ANTHROPIC_API_KEY":  { "$broker": "anthropic" },
    "OPENAI_API_KEY":     { "$broker": "openai" },
    "OPENCODE_API_KEY":   { "$broker": "opencode-go" },
    "ZAI_API_KEY":        { "$broker": "zai-coding-plan" },
    "KIMI_API_KEY":       { "$broker": "kimi-for-coding" },
    "XAI_API_KEY":        { "$broker": "xai" },
    "GOOGLE_APPLICATION_CREDENTIALS": "/secrets/google-sa.json"
  },
  "files": [
    {
      "path": "/root/.config/opencode/opencode.json",
      "content_ref": "blob_opencode_config_v3"
    },
    {
      "path": "/root/.config/opencode/oh-my-openagent.jsonc",
      "content_ref": "blob_omo_config_v3"
    },
    {
      "path": "/secrets/google-sa.json",
      "content_ref": { "$broker": "google-vertex-sa" },
      "mode": "0600"
    }
  ],
  "tools": ["bash", "editor", "git", "browser"],
  "egress": {
    "allowed_hosts": [
      "api.anthropic.com",
      "api.openai.com",
      "api.opencode.ai",
      "api.z.ai",
      "api.moonshot.cn",
      "api.x.ai",
      "api.groq.com",
      "openrouter.ai",
      "ai-gateway.vercel.sh",
      "api.github.com"
    ]
  },
  "resources": { "cpu": 4, "memory_gb": 8, "timeout_sec": 3600 }
}
```

**Three new primitives this introduces on top of the spec in `02`:**

1. **`{ "$broker": "<provider>" }`** — the value is resolved at sandbox boot by calling the Credential Broker (§8 of [`13`](./13-better-auth-integration.md)). The plaintext key exists only inside the sandbox, for the session's lifetime.

2. **`files[]`** — alongside `env`, environments can ship pre-populated config files. Same `$broker` / `$secret` resolution. `content_ref` is a blob ID stored on the platform (customer-editable via `PUT /environments/{id}/files`).

3. **`egress.allowed_hosts`** — already in the spec, but now filled with the complete OmO provider surface. Missing a host = the agent silently falls back to the next provider in the chain, which is *desirable* behavior.

## 10 · Starter platform default environment

A sensible default `Environment` that new tenants get out of the box:

**Provider strategy:**
- **Tier 1 (native)** — Anthropic, OpenAI, Google. If the tenant's connection is present, use these.
- **Tier 2 (aggregator)** — OpenCode Go subscription ($10/mo) covers GLM-5, Kimi K2.5, MiniMax M2.7 via one key. Big leverage for fallback.
- **Tier 3 (backup)** — Vercel AI Gateway or OpenRouter, so every model has at least one fallback even if the tenant hasn't connected a specific provider.

**OmO config that assumes this tiering:**

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/assets/oh-my-opencode.schema.json",
  "agents": {
    "sisyphus": {
      "model": "anthropic/claude-opus-4-7",
      "fallback_models": [
        "opencode-go/kimi-k2.5",
        "openai/gpt-5.4",
        "vercel/claude-opus-4-7"
      ]
    },
    "explore":    { "model": "github-copilot/grok-code-fast-1" },
    "librarian":  { "model": "opencode-go/minimax-m2.7" },
    "oracle":     { "model": "openai/gpt-5.4", "variant": "high" },
    "prometheus": { "prompt_append": "Leverage deep & quick agents heavily, always in parallel." }
  },
  "categories": {
    "quick":              { "model": "opencode/gpt-5-nano" },
    "deep":               { "model": "anthropic/claude-opus-4-7" },
    "visual-engineering": { "model": "google/gemini-3.1-pro", "variant": "high" }
  },
  "background_task": {
    "providerConcurrency": { "anthropic": 3, "openai": 3, "opencode": 10 }
  }
}
```

## 11 · What this changes about the platform

Four design implications for the platform, not the spec rewrites themselves:

1. **The `Environment` schema needs a `files[]` field** (not just `env`). Without it you can't configure OmO + OpenCode without baking configs into the image — which kills per-tenant customization.

2. **The Credential Broker needs to handle more than GitHub-style OAuth.** Most OmO providers are plain bearer keys, not OAuth. Easier than GitHub — the Broker just pulls the tenant's stored secret (via the `secret` resource or the `connection_org` table) and injects it at boot. Faster to ship than the GitHub App flow.

3. **Egress allowlists are ~10 entries minimum** per typical OmO-powered tenant. Worth shipping a "model provider bundle" — an allowlist preset that covers all Tier 1/2/3 providers so customers don't have to list them manually.

4. **Per-provider concurrency caps belong at two layers.** OmO's `providerConcurrency` caps a single sandbox's parallelism. The platform also needs tenant-level caps (across all their concurrent sessions) to prevent one tenant from exhausting the tenant's own Anthropic quota across 20 parallel sessions and bricking every session at once.

## 12 · Three next steps

1. **Build the default `Environment` above as an immutable platform image** — `omo-runtime:2026-04`. Every new tenant starts with this as their workspace default. Customers override via `POST /environments` later.

2. **Extend the `Environment` schema in [`02`](./02-resources.md) to include `files[]`.** One-line migration; unblocks everything else.

3. **In the Credential Broker ([`13 §8`](./13-better-auth-integration.md)), add a `mintBearer` code path** — for providers like Anthropic/OpenAI/OpenCode Go where "minting" is just "fetch the stored secret, return it" rather than an OAuth exchange. That path serves 90% of the OmO provider surface.

## Reflective question

**OmO's fallback chains are optimized for a user with personal accounts on 3–5 providers.** In a multi-tenant platform, a tenant may have exactly one provider key — say, just Anthropic. When Claude rate-limits their session, should the platform fall back to the *platform's* aggregator keys (OpenCode Go, Vercel Gateway) and bill the tenant a markup? Or fail the session and let the tenant decide?

That's not a technical question. It's a pricing and positioning question that affects how you build the whole Broker — and it's worth answering before Phase 3 of [`12`](./12-next-steps.md).
