#!/usr/bin/env python3
"""Build the OmO+VNC Daytona snapshot used by OmoiOS sandboxes.

Produces a Daytona snapshot whose image layers the following on top of
`daytonaio/sandbox:0.6.0` (the default Daytona base, per `/api/snapshots`
listing):

  - curl, jq, ca-certificates (for the broker bootstrap script)
  - Xvfb, fluxbox, x11vnc, websockify + noVNC (for VNC access)
  - Node.js 20 (for opencode / oh-my-openagent npm tooling)
  - sst/opencode installed via the official installer
  - oh-my-openagent installed via npm
  - /usr/local/bin/omoios-init  (our bootstrap, from sandbox/bootstrap.sh)

The snapshot uses `/usr/local/bin/omoios-init` as entrypoint so every sandbox
allocated from it goes through the broker-fetch → auth.json → VNC-startup
sequence automatically.

Build runs server-side inside Daytona — no local Docker daemon required.

Usage:
    uv run python scripts/build_omo_snapshot.py
    uv run python scripts/build_omo_snapshot.py --name omoios-omo-vnc-v2
    uv run python scripts/build_omo_snapshot.py --dry-run   # print Dockerfile-equivalent
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Load DAYTONA_API_KEY from backend/.env without requiring a python-dotenv dep.
REPO = Path(__file__).resolve().parent.parent
BACKEND_ENV = REPO / "backend" / ".env"
SANDBOX_BOOTSTRAP = REPO / "sandbox" / "bootstrap.sh"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)


load_env_file(BACKEND_ENV)

try:
    from daytona import Daytona, DaytonaConfig, Image
    from daytona.common.snapshot import CreateSnapshotParams
    from daytona.common.sandbox import Resources
except ImportError:
    sys.exit("daytona SDK not installed. Run: uv sync --group dev (from backend/)")


BASE_IMAGE = os.environ.get("OMOIOS_SANDBOX_BASE", "daytonaio/sandbox:0.6.0")
DEFAULT_SNAPSHOT_NAME = "omoios-omo-vnc"


def build_image() -> Image:
    """Declaratively describe the sandbox image."""
    # daytonaio/sandbox:0.6.0 (upstream Dockerfile:
    # https://github.com/daytonaio/daytona/raw/main/images/sandbox/Dockerfile)
    # already ships:
    #   - VNC stack: xvfb x11vnc novnc xfce4 xfce4-terminal dbus-x11 ffmpeg
    #   - System:    jq, curl, ripgrep, chromium, bind9-dnsutils, ffmpeg
    #   - Runtimes:  Node 25 via nvm, bun@1.3.6, opencode-ai@1.1.35
    #   - Agents:    @anthropic-ai/claude-code, openclaw, claude-agent-sdk
    #   - Python:    uv, pipx, numpy/pandas/torch, anthropic, openai, langchain
    # Runs as non-root `daytona` (uid 1001) with passwordless sudo.
    return (
        Image.base(BASE_IMAGE)
        # Layer 1: upgrade opencode-ai. Base ships 1.1.35; oh-my-opencode
        # requires 1.4.0+. The upstream Dockerfile chowns /usr/local/share/nvm
        # to daytona, but then installs global npm packages as root — so the
        # existing opencode-ai files are root-owned. Re-chown before upgrading
        # so `npm install -g` can rename the old package tree.
        .run_commands(
            "sudo chown -R daytona:daytona /usr/local/share/nvm",
            "npm install -g opencode-ai@latest",
            "opencode --version",
        )
        # Layer 2: oh-my-opencode harness, no subscriptions at build time.
        # Per-tenant provider config is rendered at sandbox boot by the broker
        # into opencode.json + auth.json. --skip-auth avoids interactive prompts.
        # Package name is `oh-my-opencode` (rename to `oh-my-openagent` is
        # transitional per the install guide).
        .run_commands(
            "bunx oh-my-opencode install --no-tui --skip-auth "
            "--claude=no --openai=no --gemini=no --copilot=no "
            "--opencode-zen=no --zai-coding-plan=no --opencode-go=no "
            "--kimi-for-coding=no --vercel-ai-gateway=no",
        )
        # Layer 3: symlink nvm-managed binaries into /usr/local/bin so they
        # are on PATH for non-interactive `/bin/sh -c` exec (e.g. when agents
        # or smoke tests run commands without sourcing nvm). The Node version
        # dir is detected at build time so a future base image bump doesn't
        # silently break things.
        .run_commands(
            "NODE_BIN=$(ls -d /usr/local/share/nvm/versions/node/v*/bin 2>/dev/null | tail -1) && "
            "echo \"symlinking from $NODE_BIN\" && "
            "for b in opencode bun bunx node npm npx; do "
            "  [ -x \"$NODE_BIN/$b\" ] && sudo ln -sf \"$NODE_BIN/$b\" \"/usr/local/bin/$b\"; "
            "done && "
            "/usr/local/bin/opencode --version && /usr/local/bin/bun --version",
        )
        # Layer 4: bootstrap script.
        .add_local_file(str(SANDBOX_BOOTSTRAP), "/usr/local/bin/omoios-init")
        .run_commands("sudo chmod +x /usr/local/bin/omoios-init")
        .add_local_file(str(REPO / "egress-proxy" / "egress-proxy"), "/usr/local/bin/omoios-egress-proxy")
        .run_commands("sudo chmod +x /usr/local/bin/omoios-egress-proxy")
        # Environment + ports. Leave PATH to the base image's default so nvm
        # scripts in /etc/profile.d still work for interactive shells; our
        # symlinks cover non-interactive exec.
        .env(
            {
                "DISPLAY": ":0",
                "VNC_PORT": "5900",
                "NOVNC_PORT": "6080",
                "VNC_RESOLUTION": "1920x1080x24",
            }
        )
    )


def dry_run(image: Image) -> None:
    """Print a Dockerfile-equivalent view of the image for inspection."""
    print(f"# Equivalent Dockerfile for OmoiOS OmO+VNC sandbox")
    print(f"FROM {BASE_IMAGE}")
    # The Image builder stores its layer ops as an internal list; print the
    # repr to give the caller something to eyeball.
    print()
    print(repr(image))


def main() -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    p.add_argument("--name", default=DEFAULT_SNAPSHOT_NAME,
                   help=f"snapshot name (default: {DEFAULT_SNAPSHOT_NAME})")
    p.add_argument("--dry-run", action="store_true",
                   help="print the image spec without building")
    p.add_argument("--timeout", type=float, default=1800,
                   help="snapshot build timeout in seconds (default: 1800)")
    p.add_argument("--cpu", type=int, default=4)
    p.add_argument("--memory-gb", type=int, default=8)
    p.add_argument("--disk-gb", type=int, default=8,
                   help="disk size in GB (max 10 per Daytona account limit)")
    args = p.parse_args()

    api_key = os.environ.get("DAYTONA_API_KEY")
    api_url = os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api")
    target = os.environ.get("DAYTONA_TARGET", "us")
    if not api_key:
        sys.exit("DAYTONA_API_KEY not set (looked in env + backend/.env)")

    image = build_image()

    if args.dry_run:
        dry_run(image)
        return 0

    print(f"▸ building snapshot '{args.name}' from {BASE_IMAGE}")
    print(f"  resources: cpu={args.cpu} memory={args.memory_gb}GB disk={args.disk_gb}GB")
    print(f"  timeout:   {args.timeout}s")
    print(f"  target:    {target}")
    print()

    client = Daytona(DaytonaConfig(api_key=api_key, api_url=api_url, target=target))

    def on_log(line: str) -> None:
        print(f"  │ {line.rstrip()}")

    params = CreateSnapshotParams(
        name=args.name,
        image=image,
        resources=Resources(cpu=args.cpu, memory=args.memory_gb, disk=args.disk_gb),
        entrypoint=["/usr/local/bin/omoios-init"],
    )

    try:
        snap = client.snapshot.create(params, on_logs=on_log, timeout=args.timeout)
    except Exception as e:
        print(f"✖ snapshot create failed: {e}", file=sys.stderr)
        return 1

    print()
    print(f"✔ snapshot ready: name={snap.name} state={getattr(snap, 'state', '?')}")
    print(f"  reference this in the smoke test via:")
    print(f"    export OMOIOS_SMOKE_SANDBOX_SNAPSHOT={snap.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
