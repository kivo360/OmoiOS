# AI Coding Agent Development Container

Extended container images for AI coding agents (Claude Code, Cursor, Copilot, Codex, etc.) optimized for Daytona Sandboxes with snapshot support.

## Quick Start

```bash
# Build full version
./build.sh --full --push

# Build light version
./build.sh --light --push

# Then create Daytona snapshots
daytona snapshot push ghcr.io/kivo360/ai-agent-dev:1.0.0 --name ai-agent-dev --cpu 4 --memory 8 --disk 20
daytona snapshot push ghcr.io/kivo360/ai-agent-dev-light:1.0.0 --name ai-agent-dev-light --cpu 2 --memory 4 --disk 10
```

## Container Variants

### Full Version (`Dockerfile`)
- All major programming languages (Python, Node.js, Go, Rust, .NET, Java, Ruby, PHP)
- Complete CLI toolset (ripgrep, fd, bat, eza, delta, zoxide, etc.)
- Cloud tools (AWS CLI, Terraform, kubectl)
- Database clients (PostgreSQL, MySQL, SQLite, Redis)
- Document processing (pandoc, imagemagick)
- ~4-6 GB image size
- Build time: ~15-20 minutes

### Light Version (`Dockerfile.light`)
- Python + Node.js/TypeScript only
- Essential CLI tools (ripgrep, fd, jq, tree, gh)
- Minimal dependencies
- ~1.5-2 GB image size
- Build time: ~3-5 minutes

## What's Included

### Languages (Full Version)
| Language | Version | Tools |
|----------|---------|-------|
| Python | 3.12 | uv, poetry, black, ruff, pytest |
| Node.js | 22.x | npm, yarn, pnpm, typescript, tsx |
| Go | 1.23 | gopls, delve, golangci-lint |
| Rust | stable | cargo, cargo-watch, cargo-edit |
| .NET/C# | 8.0 | dotnet CLI |
| Java | 21 | OpenJDK |
| Ruby | system | gem, bundler |
| PHP | 8.x | composer |

### CLI Tools
- **ripgrep (rg)** - Fast code search (required by Claude Code)
- **fd** - Fast file finder
- **gh** - GitHub CLI for PR workflows
- **jq/yq** - JSON/YAML processing
- **bat** - Better cat with syntax highlighting
- **eza** - Modern ls replacement
- **delta** - Better git diffs
- **zoxide** - Smart directory navigation

## Build Options

```bash
./build.sh [options]

Options:
  --full          Build full variant (default)
  --light         Build light variant
  --push          Push to registry after build
  --registry URL  Container registry (default: ghcr.io/kivo360)
  --version VER   Image version tag (default: 1.0.0)
```

## Resource Recommendations

| Workload | CPU | Memory | Disk |
|----------|-----|--------|------|
| Light (scripting) | 2 | 4 GB | 10 GB |
| Standard (web dev) | 4 | 8 GB | 20 GB |
| Heavy (ML, builds) | 8 | 16 GB | 50 GB |
