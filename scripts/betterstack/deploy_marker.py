#!/usr/bin/env python3
"""Fire a deploy marker into BetterStack + PostHog.

Run from CI/CD on the post-deploy step. Reads release info from
arguments or from the standard env vars set by Railway / GitHub Actions.

Usage:
    uv run python -m scripts.betterstack.deploy_marker \\
        --release v1.42.0 --environment production --actor github-actions

    # Or pull from env (RAILWAY_GIT_COMMIT_SHA / GITHUB_SHA / etc.)
    uv run python -m scripts.betterstack.deploy_marker --environment production
"""

from __future__ import annotations

import argparse
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "backend"))


def _resolve_release() -> str:
    return (
        os.environ.get("OMOIOS_RELEASE")
        or os.environ.get("RAILWAY_GIT_COMMIT_SHA")
        or os.environ.get("GITHUB_SHA")
        or os.environ.get("VERCEL_GIT_COMMIT_SHA")
        or "unknown"
    )


def _resolve_actor() -> str | None:
    return (
        os.environ.get("DEPLOY_ACTOR")
        or os.environ.get("GITHUB_ACTOR")
        or os.environ.get("RAILWAY_DEPLOYMENT_USER")
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release", default=None)
    p.add_argument("--environment", default=os.environ.get("APP_ENV", "production"))
    p.add_argument("--actor", default=None)
    p.add_argument("--git-sha", default=os.environ.get("GIT_SHA"))
    args = p.parse_args()

    release = args.release or _resolve_release()
    actor = args.actor or _resolve_actor()

    from omoi_os.observability.telemetry import deploy_marker, init_telemetry, shutdown

    init_telemetry()
    deploy_marker(
        release=release,
        environment=args.environment,
        git_sha=args.git_sha,
        actor=actor,
    )
    shutdown()
    print(f"deploy_marker fired: release={release} environment={args.environment}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
