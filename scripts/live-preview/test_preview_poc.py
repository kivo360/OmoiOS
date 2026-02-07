#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "daytona>=0.112.0",
#     "python-dotenv",
# ]
# ///
"""Phase 0 POC: Prove Daytona preview URLs work with Vite HMR.

Creates a public Daytona sandbox, scaffolds a Vite + React app,
starts the dev server, gets the preview URL, then modifies App.tsx
to verify HMR works (browser hot-updates without full reload).

Usage:
    uv run scripts/live-preview/test_preview_poc.py
    uv run scripts/live-preview/test_preview_poc.py --no-interactive
    uv run scripts/live-preview/test_preview_poc.py --keep-sandbox --skip-hmr
"""

import argparse
import os
import signal
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------

try:
    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(project_root / "backend" / ".env.local")
    load_dotenv(project_root / "backend" / ".env")
    load_dotenv(project_root / ".env.local")
    load_dotenv(project_root / ".env")
except ImportError:
    pass  # dotenv is optional — env vars can be set directly

# ---------------------------------------------------------------------------
# CLI arguments
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Phase 0 POC — Daytona live preview with Vite HMR"
    )
    p.add_argument(
        "--image",
        default="nikolaik/python-nodejs:python3.12-nodejs22",
        help="Docker image for the sandbox (default: nikolaik/python-nodejs)",
    )
    p.add_argument(
        "--template",
        default="react-ts",
        choices=["react-ts", "react", "vue-ts", "vue"],
        help="Vite project template (default: react-ts)",
    )
    p.add_argument("--cpu", type=int, default=2, help="CPU cores (default: 2)")
    p.add_argument("--memory", type=int, default=4, help="Memory GiB (default: 4)")
    p.add_argument("--disk", type=int, default=8, help="Disk GiB (default: 8)")
    p.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Sandbox creation timeout seconds (default: 120)",
    )
    p.add_argument(
        "--port", type=int, default=3000, help="Dev server port (default: 3000)"
    )
    p.add_argument(
        "--no-interactive",
        action="store_true",
        help="Skip interactive pauses (auto-proceed)",
    )
    p.add_argument(
        "--wait",
        type=int,
        default=30,
        help="Seconds to wait in non-interactive mode before proceeding (default: 30)",
    )
    p.add_argument(
        "--skip-hmr", action="store_true", help="Skip the HMR modification test"
    )
    p.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="Don't delete sandbox on exit (for debugging)",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Vite config template
# ---------------------------------------------------------------------------

VITE_CONFIG_TS = """\
import {{ defineConfig }} from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({{
  plugins: [react()],
  server: {{
    host: '0.0.0.0',
    port: {port},
    hmr: {{
      clientPort: 443,
      protocol: 'wss',
    }},
    headers: {{
      'X-Frame-Options': 'ALLOWALL',
    }},
  }},
}})
"""

# ---------------------------------------------------------------------------
# Modified App.tsx for HMR test
# ---------------------------------------------------------------------------

MODIFIED_APP_TSX = """\
import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>OmoiOS Live Preview Works!</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          HMR is working — this text was injected by the POC script
        </p>
      </div>
      <p className="read-the-docs">
        Phase 0 verification complete
      </p>
    </>
  )
}

export default App
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def step(n: int, msg: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  Step {n}: {msg}")
    print(f"{'=' * 60}")


def info(msg: str) -> None:
    print(f"  -> {msg}")


def ok(msg: str) -> None:
    print(f"  OK: {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL: {msg}", file=sys.stderr)


def run_cmd(sandbox, cmd: str, label: str | None = None, check: bool = True) -> str:
    """Execute a command in the sandbox and return stdout."""
    label = label or cmd[:60]
    result = sandbox.process.exec(cmd)
    if check and result.exit_code != 0:
        fail(f"{label} exited with code {result.exit_code}")
        if result.result:
            print(f"  stdout: {result.result.strip()[:500]}")
        raise RuntimeError(f"Command failed: {label}")
    return result.result.strip() if result.result else ""


def wait_for_user(args: argparse.Namespace, prompt: str) -> None:
    """Pause for user verification (or auto-wait in non-interactive mode)."""
    if args.no_interactive:
        info(f"Non-interactive mode: waiting {args.wait}s...")
        time.sleep(args.wait)
    else:
        input(f"\n  >> {prompt} [Press Enter to continue] ")


# ---------------------------------------------------------------------------
# Main POC
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()

    print("=" * 60)
    print("  Phase 0 POC — Daytona Live Preview + Vite HMR")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Validate environment
    # ------------------------------------------------------------------
    step(1, "Validate environment")

    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        fail("DAYTONA_API_KEY not set")
        info("Set it in .env.local or export DAYTONA_API_KEY=dtn_...")
        return 1
    ok(f"DAYTONA_API_KEY: {api_key[:10]}...")

    try:
        from daytona import (
            CreateSandboxFromImageParams,
            Daytona,
            DaytonaConfig,
            Resources,
            SessionExecuteRequest,
        )
    except ImportError:
        fail("Daytona SDK not installed")
        info(
            "Run: uv run scripts/live-preview/test_preview_poc.py  (PEP 723 auto-installs)"
        )
        return 1
    ok("Daytona SDK imported")

    # ------------------------------------------------------------------
    # Step 2: Create Daytona client
    # ------------------------------------------------------------------
    step(2, "Create Daytona client")

    config = DaytonaConfig(
        api_key=api_key,
        api_url="https://app.daytona.io/api",
        target="us",
    )
    daytona = Daytona(config)
    ok("Daytona client configured")

    # ------------------------------------------------------------------
    # Sandbox lifecycle with cleanup
    # ------------------------------------------------------------------
    sandbox = None
    keep = args.keep_sandbox

    def cleanup(sig=None, frame=None):
        nonlocal sandbox
        if sandbox and not keep:
            print("\n  Cleaning up sandbox...")
            try:
                daytona.delete(sandbox)
                print("  Sandbox deleted.")
            except Exception as e:
                print(f"  Cleanup error: {e}")
            sandbox = None
        if sig is not None:
            sys.exit(1)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        # --------------------------------------------------------------
        # Step 3: Create sandbox
        # --------------------------------------------------------------
        step(3, "Create public sandbox")
        info(f"Image: {args.image}")
        info(f"Resources: {args.cpu} CPU, {args.memory} GiB RAM, {args.disk} GiB disk")

        t0 = time.time()
        params = CreateSandboxFromImageParams(
            image=args.image,
            labels={"poc": "live-preview-phase0"},
            ephemeral=True,
            public=True,
            resources=Resources(cpu=args.cpu, memory=args.memory, disk=args.disk),
        )
        sandbox = daytona.create(params=params, timeout=args.timeout)
        elapsed = time.time() - t0
        ok(f"Sandbox created in {elapsed:.1f}s  (ID: {sandbox.id})")

        # --------------------------------------------------------------
        # Step 4: Detect home directory
        # --------------------------------------------------------------
        step(4, "Detect home directory")
        home_dir = run_cmd(sandbox, "echo $HOME", "detect $HOME")
        ok(f"HOME={home_dir}")
        project_dir = f"{home_dir}/preview-app"

        # Verify Node is available
        node_ver = run_cmd(sandbox, "node --version", "node version")
        npm_ver = run_cmd(sandbox, "npm --version", "npm version")
        info(f"Node {node_ver}, npm {npm_ver}")

        # --------------------------------------------------------------
        # Step 5: Scaffold Vite + React app
        # --------------------------------------------------------------
        step(5, f"Scaffold Vite app (template: {args.template})")
        run_cmd(
            sandbox,
            f"cd {home_dir} && npm create vite@latest preview-app -- --template {args.template}",
            "npm create vite",
        )
        # Verify scaffold
        files = run_cmd(sandbox, f"ls {project_dir}/src/", "verify scaffold")
        ok(f"Scaffold created: {files}")

        # --------------------------------------------------------------
        # Step 6: Upload HMR-ready vite.config.ts
        # --------------------------------------------------------------
        step(6, "Upload HMR-ready vite.config.ts")
        vite_config = VITE_CONFIG_TS.format(port=args.port)
        config_filename = "vite.config.ts"
        sandbox.fs.upload_file(
            vite_config.encode("utf-8"),
            f"{project_dir}/{config_filename}",
        )
        # Verify upload
        uploaded = run_cmd(
            sandbox, f"cat {project_dir}/{config_filename}", "verify config"
        )
        if "clientPort: 443" in uploaded and "protocol: 'wss'" in uploaded:
            ok("vite.config.ts uploaded with HMR proxy settings")
        else:
            fail("vite.config.ts content mismatch")
            return 1

        # --------------------------------------------------------------
        # Step 7: Install dependencies
        # --------------------------------------------------------------
        step(7, "Install dependencies (npm install)")
        t0 = time.time()
        run_cmd(sandbox, f"cd {project_dir} && npm install", "npm install")
        elapsed = time.time() - t0
        ok(f"Dependencies installed in {elapsed:.1f}s")

        # --------------------------------------------------------------
        # Step 8: Start dev server via session
        # --------------------------------------------------------------
        step(8, "Start dev server (session-based, async)")
        session_id = "dev-server"
        info("Creating session...")
        sys.stdout.flush()
        sandbox.process.create_session(session_id)
        info("Launching dev server...")
        sys.stdout.flush()
        response = sandbox.process.execute_session_command(
            session_id,
            SessionExecuteRequest(
                command=f"cd {project_dir} && npm run dev",
                runAsync=True,
            ),
        )
        cmd_id = response.cmd_id
        ok(f"Dev server started (session={session_id}, cmd_id={cmd_id})")
        sys.stdout.flush()

        # --------------------------------------------------------------
        # Step 9: Poll for dev server readiness
        # --------------------------------------------------------------
        step(9, "Wait for dev server to be ready")
        max_wait = 60
        poll_interval = 3
        waited = 0
        ready = False

        while waited < max_wait:
            check = sandbox.process.exec(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{args.port}/ 2>/dev/null || echo 'fail'"
            )
            status = check.result.strip() if check.result else "fail"
            if status == "200":
                ready = True
                break
            info(f"Waiting... ({waited}s, status={status})")
            sys.stdout.flush()
            time.sleep(poll_interval)
            waited += poll_interval

        if not ready:
            fail(f"Dev server not ready after {max_wait}s")
            # Print server logs for debugging
            try:
                logs = sandbox.process.get_session_command_logs(session_id, cmd_id)
                if logs.output:
                    info("Server logs:")
                    print(logs.output[:2000])
            except Exception:
                pass
            return 1
        ok(f"Dev server ready after {waited}s")

        # --------------------------------------------------------------
        # Step 10: Get preview URL
        # --------------------------------------------------------------
        step(10, "Get preview URL")
        preview = sandbox.get_preview_link(args.port)
        preview_url = preview.url
        ok(f"Preview URL: {preview_url}")

        # --------------------------------------------------------------
        # Step 11: User verification — app renders
        # --------------------------------------------------------------
        step(11, "Verify app renders in browser")
        print("\n  Open this URL in your browser:\n")
        print(f"    {preview_url}\n")
        print("  You should see the default Vite + React app with spinning logos")
        print("  and a counter button. Click the counter a few times.\n")
        wait_for_user(args, "Verified app renders?")

        if args.skip_hmr:
            info("Skipping HMR test (--skip-hmr)")
            print("\n" + "=" * 60)
            print("  Phase 0 POC PASSED (HMR test skipped)")
            print("=" * 60)
            return 0

        # --------------------------------------------------------------
        # Step 12: Upload modified App.tsx (HMR test)
        # --------------------------------------------------------------
        step(12, "Upload modified App.tsx for HMR test")
        sandbox.fs.upload_file(
            MODIFIED_APP_TSX.encode("utf-8"),
            f"{project_dir}/src/App.tsx",
        )
        ok("Modified App.tsx uploaded")

        # --------------------------------------------------------------
        # Step 13: User verification — HMR works
        # --------------------------------------------------------------
        step(13, "Verify HMR in browser")
        print("\n  Check your browser at:\n")
        print(f"    {preview_url}\n")
        print("  You should see:")
        print("    - Heading: 'OmoiOS Live Preview Works!'")
        print("    - Body: 'HMR is working — this text was injected by the POC script'")
        print("    - Footer: 'Phase 0 verification complete'")
        print("    - Counter should KEEP its value (no full reload = HMR works)\n")
        wait_for_user(args, "Verified HMR works?")

        # --------------------------------------------------------------
        # Done
        # --------------------------------------------------------------
        print("\n" + "=" * 60)
        print("  Phase 0 POC PASSED")
        print("  - Sandbox created with public access")
        print("  - Vite + React app scaffolded and running")
        print(f"  - Preview URL: {preview_url}")
        print("  - HMR verified via App.tsx modification")
        print("=" * 60)
        return 0

    except Exception as e:
        fail(str(e))
        import traceback

        traceback.print_exc()
        return 1

    finally:
        if sandbox and not keep:
            print("\n  Cleaning up sandbox...")
            try:
                daytona.delete(sandbox)
                print("  Sandbox deleted.")
            except Exception as e:
                print(f"  Cleanup error: {e}")
        elif sandbox and keep:
            print(f"\n  --keep-sandbox: sandbox {sandbox.id} left running")
            print("  Delete manually when done.")


if __name__ == "__main__":
    sys.exit(main())
