#!/usr/bin/env python3
"""Smoke test: send an error and a trace to BetterStack via the Sentry SDK.

BetterStack Error Monitoring is Sentry-protocol compatible — point a stock
sentry-sdk at a BetterStack DSN and both exceptions and performance
transactions are accepted.

Run:
    pip install 'sentry-sdk>=2.0'

    # Either pass DSN explicitly...
    python -m scripts.betterstack.sentry_demo \\
        --dsn "https://<application-token>@<ingesting-host>/1"

    # ...or set SENTRY_DSN, then:
    python -m scripts.betterstack.sentry_demo

    # ...or auto-bootstrap a fresh app via the API and use its DSN:
    python -m scripts.betterstack.sentry_demo --auto-create my-test-app

After the script exits, check BetterStack → Errors → your app for:
  • The captured `division by zero` exception
  • The captured `caught manually` exception
  • A performance transaction named "demo-transaction" with two child spans
"""

from __future__ import annotations

import argparse
import os
import sys
import time

try:
    import sentry_sdk
except ImportError:
    print(
        "sentry-sdk is not installed.\n"
        "Install with: pip install 'sentry-sdk>=2.0'",
        file=sys.stderr,
    )
    sys.exit(1)


def fake_db_query(seconds: float) -> int:
    """A fake child operation we'll wrap in a span to demo tracing."""
    time.sleep(seconds)
    return 42


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsn",
        default=os.environ.get("SENTRY_DSN"),
        help="BetterStack-issued Sentry DSN. Falls back to $SENTRY_DSN.",
    )
    parser.add_argument(
        "--auto-create",
        metavar="NAME",
        help="Create a fresh BetterStack error app via API and use its DSN.",
    )
    parser.add_argument(
        "--environment", default="local-smoke", help="Sentry environment tag"
    )
    parser.add_argument(
        "--release", default="betterstack-demo@0.1.0", help="Sentry release"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable sentry-sdk debug logging (shows HTTP requests).",
    )
    args = parser.parse_args()

    dsn = args.dsn
    if args.auto_create:
        from .api import BetterStack

        with BetterStack() as bs:
            print(f"[setup] creating error tracking app '{args.auto_create}'...")
            app = bs.create_app(args.auto_create, platform="python")
            dsn = bs.app_dsn(app)
            if not dsn:
                print(
                    f"[setup] app created but no DSN returned: {app}",
                    file=sys.stderr,
                )
                return 1
            print(f"[setup] DSN: {dsn}")

    if not dsn:
        print(
            "No DSN. Pass --dsn, set SENTRY_DSN, or use --auto-create.",
            file=sys.stderr,
        )
        return 1

    # --- Initialize the Sentry SDK ----------------------------------------
    sentry_sdk.init(
        dsn=dsn,
        debug=args.debug,
        # Errors
        send_default_pii=False,
        # Performance / tracing — 1.0 means "send every transaction"
        traces_sample_rate=1.0,
        # Profiling adds CPU sampling on top of traces
        profiles_sample_rate=1.0,
        # Tags
        environment=args.environment,
        release=args.release,
        # Useful for the BetterStack UI
        before_send=lambda event, hint: event,
    )
    print("[sentry] initialized")

    # --- 1. Capture an unhandled exception (caught for the demo) ----------
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        event_id = sentry_sdk.capture_exception()
        print(f"[error] sent ZeroDivisionError -> event_id={event_id}")

    # --- 2. Capture a manually constructed message ------------------------
    msg_id = sentry_sdk.capture_message("hello from betterstack-demo", level="info")
    print(f"[message] sent info message -> event_id={msg_id}")

    # --- 3. A captured exception with extra context ----------------------
    try:
        raise RuntimeError("caught manually")
    except RuntimeError:
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("component", "betterstack-demo")
            scope.set_user({"id": "demo-user-123", "email": "demo@example.com"})
            scope.set_extra("custom_field", {"foo": "bar"})
            event_id = sentry_sdk.capture_exception()
            print(f"[error] sent RuntimeError with context -> event_id={event_id}")

    # --- 4. A performance transaction with nested spans -------------------
    with sentry_sdk.start_transaction(
        op="demo", name="demo-transaction"
    ) as transaction:
        transaction.set_tag("demo.kind", "smoke")

        with sentry_sdk.start_span(op="db.query", name="select_users"):
            fake_db_query(0.05)

        with sentry_sdk.start_span(op="http.client", name="external-api-call"):
            fake_db_query(0.10)

        print(f"[trace] sent transaction -> trace_id={transaction.trace_id}")

    # --- 5. Make sure everything flushes before we exit -------------------
    print("[sentry] flushing buffered events...")
    sentry_sdk.flush(timeout=10)
    print("[done] check BetterStack -> Errors for 3 events + 1 transaction")
    return 0


if __name__ == "__main__":
    sys.exit(main())
