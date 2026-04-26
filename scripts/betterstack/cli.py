#!/usr/bin/env python3
"""BetterStack CLI — manage Telemetry sources, Errors apps, and Uptime resources.

Authentication: set BETTERSTACK_API_KEY env var or pass --token. A built-in
default key is used if neither is set; rotate it at
https://betterstack.com/settings/global-api-tokens.

Usage examples:

    # First-run bootstrap — creates a telemetry source + error app, prints
    # the OTLP env vars and Sentry DSN ready to copy.
    python -m scripts.betterstack.cli setup --name omoi-os
    python -m scripts.betterstack.cli setup --name omoi-os \\
        --monitor https://api.omoios.dev/health \\
        --heartbeat backend-cron

    # Browse what's there
    python -m scripts.betterstack.cli source list
    python -m scripts.betterstack.cli app list
    python -m scripts.betterstack.cli monitor list
    python -m scripts.betterstack.cli incident list --resolved=false

    # Get a Sentry DSN for an existing error app
    python -m scripts.betterstack.cli app dsn 12345

    # Tear down
    python -m scripts.betterstack.cli source delete 12345
    python -m scripts.betterstack.cli app delete 67890
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .api import BetterStack, BetterStackAPIError, OTLP_PATHS, ResourceNotFound


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _attrs(item: dict) -> dict:
    """JSON:API responses stash payload under .attributes; flatten for printing."""
    a = item.get("attributes") or {}
    return {"id": item.get("id"), **a}


def _print_table(rows: list[dict], columns: list[str]) -> None:
    if not rows:
        print("(none)")
        return
    flat = [_attrs(r) if "attributes" in r else r for r in rows]
    widths = [
        max(len(c), max(len(str(r.get(c, ""))) for r in flat)) for c in columns
    ]
    header = "  ".join(c.ljust(w) for c, w in zip(columns, widths))
    print(header)
    print("  ".join("-" * w for w in widths))
    for r in flat:
        print("  ".join(str(r.get(c, "")).ljust(w) for c, w in zip(columns, widths)))


def _emit(args: argparse.Namespace, value: Any) -> None:
    if args.json:
        json.dump(value, sys.stdout, indent=2, default=str)
        print()


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_setup(bs: BetterStack, args: argparse.Namespace) -> None:
    print(f"Bootstrapping BetterStack project '{args.name}'...")
    result = bs.bootstrap_project(
        args.name,
        monitor_url=args.monitor,
        heartbeat_name=args.heartbeat,
        platform=args.platform,
        data_region=args.data_region,
    )

    src = _attrs(result["source"])
    print(f"\n== Telemetry source ==")
    print(f"  ID:                  {src.get('id')}")
    print(f"  Name:                {src.get('name')}")
    print(f"  Platform:            {src.get('platform')}")
    print(f"  Source token:        {result.get('source_token')}")
    print(f"  Ingesting host:      {result.get('ingesting_host')}")
    print(f"  OTLP traces URL:     {OTLP_PATHS['traces']}")
    print(f"  OTLP logs URL:       {OTLP_PATHS['logs']}")
    print(f"  OTLP metrics URL:    {OTLP_PATHS['metrics']}")

    if "app" in result:
        app = _attrs(result["app"])
        print(f"\n== Error tracking application ==")
        print(f"  ID:                  {app.get('id')}")
        print(f"  Name:                {app.get('name')}")
        print(f"  Sentry DSN:          {result.get('dsn')}")
    elif "app_error" in result:
        print(f"\n== Error tracking application ==")
        print(f"  (skipped) {result['app_error']}")

    if "monitor" in result:
        m = _attrs(result["monitor"])
        print(f"\n== Uptime monitor ==")
        print(f"  ID:                  {m.get('id')}")
        print(f"  URL:                 {m.get('url')}")
        print(f"  Status:              {m.get('status')}")

    if "heartbeat" in result:
        h = _attrs(result["heartbeat"])
        print(f"\n== Heartbeat ==")
        print(f"  ID:                  {h.get('id')}")
        print(f"  Name:                {h.get('name')}")
        print(f"  Period:              {h.get('period')}s")
        print(f"  Ping URL:            {h.get('url')}")

    print("\n== Env vars to export ==")
    if result.get("otlp_endpoint"):
        print(f'  export OTEL_EXPORTER_OTLP_ENDPOINT="{result["otlp_endpoint"]}"')
        print(f'  export OTEL_EXPORTER_OTLP_HEADERS="{result["otlp_headers"]}"')
    if result.get("dsn"):
        print(f'  export SENTRY_DSN="{result["dsn"]}"')

    if args.json:
        _emit(args, result)


def cmd_source(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        items = bs.list_sources()
        _print_table(items, ["id", "name", "platform", "ingesting_host", "token"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_source(args.id)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "create":
        item = bs.create_source(
            args.name,
            platform=args.platform,
            data_region=args.data_region,
        )
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "delete":
        bs.delete_source(args.id)
        print(f"deleted source {args.id}")


def cmd_app(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        items = bs.list_apps()
        _print_table(items, ["id", "name", "platform", "ingesting_host", "token"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_app(args.id)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "create":
        item = bs.create_app(args.name, platform=args.platform)
        print(json.dumps(item, indent=2, default=str))
        dsn = bs.app_dsn(item)
        if dsn:
            print(f"\nSentry DSN: {dsn}")
    elif args.action == "delete":
        bs.delete_app(args.id)
        print(f"deleted app {args.id}")
    elif args.action == "dsn":
        item = bs.get_app(args.id)
        dsn = bs.app_dsn(item)
        print(dsn or "(no token/host on this application — check the dashboard)")


def cmd_monitor(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        items = bs.list_monitors()
        _print_table(items, ["id", "url", "monitor_type", "status", "check_frequency"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_monitor(args.id)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "create":
        item = bs.create_monitor(
            args.url,
            monitor_type=args.type,
            check_frequency=args.frequency,
        )
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "delete":
        bs.delete_monitor(args.id)
        print(f"deleted monitor {args.id}")


def cmd_heartbeat(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        items = bs.list_heartbeats()
        _print_table(items, ["id", "name", "period", "grace", "status", "url"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_heartbeat(args.id)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "create":
        item = bs.create_heartbeat(args.name, period=args.period, grace=args.grace)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "delete":
        bs.delete_heartbeat(args.id)
        print(f"deleted heartbeat {args.id}")


def cmd_incident(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        filters = {}
        if args.resolved is not None:
            filters["resolved"] = "true" if args.resolved else "false"
        items = bs.list_incidents(**filters)
        _print_table(items, ["id", "name", "started_at", "resolved_at", "cause"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_incident(args.id)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "ack":
        bs.acknowledge_incident(args.id)
        print(f"acknowledged incident {args.id}")
    elif args.action == "resolve":
        bs.resolve_incident(args.id)
        print(f"resolved incident {args.id}")


def cmd_policy(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        items = bs.list_policies()
        _print_table(items, ["id", "name", "incident_token"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_policy(args.id)
        print(json.dumps(item, indent=2, default=str))


def cmd_alert(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        items = bs.list_alerts()
        _print_table(items, ["id", "name", "type", "enabled"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_alert(args.id)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "delete":
        bs.delete_alert(args.id)
        print(f"deleted alert {args.id}")


def cmd_status_page(bs: BetterStack, args: argparse.Namespace) -> None:
    if args.action == "list":
        items = bs.list_status_pages()
        _print_table(items, ["id", "company_name", "subdomain", "custom_domain"])
        if args.json:
            _emit(args, items)
    elif args.action == "get":
        item = bs.get_status_page(args.id)
        print(json.dumps(item, indent=2, default=str))
    elif args.action == "create":
        item = bs.create_status_page(
            company_name=args.company,
            subdomain=args.subdomain,
            timezone=args.timezone,
        )
        print(json.dumps(item, indent=2, default=str))


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="betterstack",
        description="Manage BetterStack Telemetry, Errors, and Uptime from the CLI.",
    )
    parser.add_argument(
        "--token",
        help="BetterStack API token. Defaults to $BETTERSTACK_API_KEY or the built-in.",
    )
    parser.add_argument("--json", action="store_true", help="Also dump raw JSON to stdout.")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # setup
    p = sub.add_parser("setup", help="Bootstrap source + error app + optional monitor/heartbeat")
    p.add_argument("--name", required=True, help="Project name (used to derive resource names)")
    p.add_argument("--monitor", help="URL for an HTTP monitor")
    p.add_argument("--heartbeat", help="Name for a cron heartbeat")
    p.add_argument("--platform", default="open_telemetry")
    p.add_argument("--data-region", choices=["us_east", "germany", "singapore"])
    p.set_defaults(func=cmd_setup)

    # source
    p = sub.add_parser("source", help="Telemetry sources (logs/metrics/traces)")
    sp = p.add_subparsers(dest="action", required=True)
    sp.add_parser("list").set_defaults(func=cmd_source)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_source)
    g = sp.add_parser("create")
    g.add_argument("name")
    g.add_argument("--platform", default="open_telemetry")
    g.add_argument("--data-region", choices=["us_east", "germany", "singapore"])
    g.set_defaults(func=cmd_source)
    g = sp.add_parser("delete"); g.add_argument("id"); g.set_defaults(func=cmd_source)

    # app (error tracking)
    p = sub.add_parser("app", help="Error tracking applications (Sentry-compatible)")
    sp = p.add_subparsers(dest="action", required=True)
    sp.add_parser("list").set_defaults(func=cmd_app)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_app)
    g = sp.add_parser("create"); g.add_argument("name"); g.add_argument("--platform", default="python"); g.set_defaults(func=cmd_app)
    g = sp.add_parser("delete"); g.add_argument("id"); g.set_defaults(func=cmd_app)
    g = sp.add_parser("dsn", help="Print the Sentry DSN for an app")
    g.add_argument("id"); g.set_defaults(func=cmd_app)

    # monitor
    p = sub.add_parser("monitor", help="Uptime HTTP/TCP/DNS monitors")
    sp = p.add_subparsers(dest="action", required=True)
    sp.add_parser("list").set_defaults(func=cmd_monitor)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_monitor)
    g = sp.add_parser("create")
    g.add_argument("url")
    g.add_argument("--type", default="status", choices=["status", "keyword", "tcp", "udp", "ping", "smtp", "pop", "imap", "dns"])
    g.add_argument("--frequency", type=int, default=180)
    g.set_defaults(func=cmd_monitor)
    g = sp.add_parser("delete"); g.add_argument("id"); g.set_defaults(func=cmd_monitor)

    # heartbeat
    p = sub.add_parser("heartbeat", help="Cron / scheduled-job heartbeats")
    sp = p.add_subparsers(dest="action", required=True)
    sp.add_parser("list").set_defaults(func=cmd_heartbeat)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_heartbeat)
    g = sp.add_parser("create")
    g.add_argument("name")
    g.add_argument("--period", type=int, default=60)
    g.add_argument("--grace", type=int, default=30)
    g.set_defaults(func=cmd_heartbeat)
    g = sp.add_parser("delete"); g.add_argument("id"); g.set_defaults(func=cmd_heartbeat)

    # incident
    p = sub.add_parser("incident", help="On-call incidents")
    sp = p.add_subparsers(dest="action", required=True)
    g = sp.add_parser("list")
    g.add_argument("--resolved", type=lambda v: v.lower() in ("true", "1", "yes"), default=None)
    g.set_defaults(func=cmd_incident)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_incident)
    g = sp.add_parser("ack"); g.add_argument("id"); g.set_defaults(func=cmd_incident)
    g = sp.add_parser("resolve"); g.add_argument("id"); g.set_defaults(func=cmd_incident)

    # policy
    p = sub.add_parser("policy", help="Escalation policies")
    sp = p.add_subparsers(dest="action", required=True)
    sp.add_parser("list").set_defaults(func=cmd_policy)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_policy)

    # alert
    p = sub.add_parser("alert", help="Telemetry dashboard / exploration alerts")
    sp = p.add_subparsers(dest="action", required=True)
    sp.add_parser("list").set_defaults(func=cmd_alert)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_alert)
    g = sp.add_parser("delete"); g.add_argument("id"); g.set_defaults(func=cmd_alert)

    # status-page
    p = sub.add_parser("status-page", help="Public status pages")
    sp = p.add_subparsers(dest="action", required=True)
    sp.add_parser("list").set_defaults(func=cmd_status_page)
    g = sp.add_parser("get"); g.add_argument("id"); g.set_defaults(func=cmd_status_page)
    g = sp.add_parser("create")
    g.add_argument("--company", required=True)
    g.add_argument("--subdomain", required=True)
    g.add_argument("--timezone", default="UTC")
    g.set_defaults(func=cmd_status_page)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        with BetterStack(token=args.token) as bs:
            args.func(bs, args)
    except ResourceNotFound as e:
        print(f"Not found: {e}", file=sys.stderr)
        return 2
    except BetterStackAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
