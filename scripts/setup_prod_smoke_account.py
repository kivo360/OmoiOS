#!/usr/bin/env python3
"""Bootstrap a fresh production smoke-test account end-to-end.

Idempotent: re-running picks up existing user/org/key by email and tops up
whatever is missing.

Steps:
    1. Generate (or reuse) a strong password for `--email`.
    2. POST /api/v1/auth/register; if 409, fall through and try to log in.
    3. If login still fails (email verification pending in prod), promote
       the user to is_verified=true via direct DB write.
    4. Login → JWT.
    5. Pick or create an organization (single-owner, smoke-only).
    6. Mint a platform API key with scopes=["*"].
    7. Create two workspaces (smoke-a, smoke-b) for isolation tests.
    8. Write the resulting state to backend/.env.smoke-test (gitignored).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import string
import sys
import urllib.parse
from pathlib import Path

import httpx
import psycopg


REPO = Path(__file__).resolve().parent.parent
ENV_OUT = REPO / "backend" / ".env.smoke-test"
ENV_PROD = REPO / "backend" / ".env.production"


def parse_db_url(env_file: Path) -> dict:
    text = env_file.read_text()
    m = re.search(r"^DATABASE_URL=([^\s]+)", text, re.MULTILINE)
    if not m:
        sys.exit(f"DATABASE_URL not found in {env_file}")
    raw = m.group(1)
    raw = raw.replace("postgresql+psycopg://", "postgresql://")
    parsed = urllib.parse.urlparse(raw)
    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip("/"),
    }


def gen_password() -> str:
    alphabet = string.ascii_letters + string.digits + "-_!@#"
    return "".join(secrets.choice(alphabet) for _ in range(28))


def post(client: httpx.Client, path: str, json_body: dict, token: str | None = None) -> httpx.Response:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return client.post(path, json=json_body, headers=headers)


def get(client: httpx.Client, path: str, token: str | None = None) -> httpx.Response:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return client.get(path, headers=headers)


def login(client: httpx.Client, email: str, password: str) -> str | None:
    r = post(client, "/api/v1/auth/login", {"email": email, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None


def ensure_verified(db: dict, email: str) -> None:
    with psycopg.connect(**db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_verified = TRUE, is_active = TRUE WHERE email = %s",
                (email,),
            )
            conn.commit()
            print(f"  ✔ promoted {email} to is_verified=true is_active=true")


def pick_or_create_org(client: httpx.Client, token: str, name: str) -> str | None:
    r = get(client, "/api/v1/organizations", token)
    if r.status_code == 200:
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        if items:
            org = items[0]
            print(f"  ✔ found {len(items)} org(s); using '{org.get('name')}' ({org.get('id')})")
            return org.get("id")
    r = post(client, "/api/v1/organizations", {"name": name, "slug": "smoke-test"}, token=token)
    if r.status_code in (200, 201):
        org_id = r.json().get("id")
        print(f"  ✔ created org '{name}' ({org_id})")
        return org_id
    print(f"  ⚠ create org failed: {r.status_code} {r.text[:300]}")
    return None


def mint_key(client: httpx.Client, token: str, name: str, org_id: str | None) -> str:
    body: dict = {"name": name, "scopes": ["*"]}
    if org_id:
        body["organization_id"] = org_id
    r = post(client, "/api/v1/auth/api-keys", body, token=token)
    if r.status_code not in (200, 201):
        sys.exit(f"mint api-key failed: {r.status_code} {r.text[:400]}")
    full_key = r.json().get("key")
    if not full_key or not (full_key.startswith("sk_live_") or full_key.startswith("rpk_live_")):
        sys.exit(f"unexpected api-key response shape: {r.text[:300]}")
    return full_key


def ensure_workspace(client: httpx.Client, token: str, org_id: str, name: str) -> str | None:
    r = get(client, "/api/v1/workspaces", token)
    if r.status_code == 200:
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        for ws in items:
            if ws.get("name") == name:
                print(f"  ✔ workspace '{name}' exists ({ws['id']})")
                return ws["id"]
    body = {"name": name, "slug": name, "organization_id": org_id}
    r = post(client, "/api/v1/workspaces", body, token=token)
    if r.status_code in (200, 201):
        ws_id = r.json().get("id")
        print(f"  ✔ created workspace '{name}' ({ws_id})")
        return ws_id
    print(f"  ⚠ create workspace '{name}' failed: {r.status_code} {r.text[:300]}")
    return None


def write_env(
    api_base: str,
    email: str,
    password: str,
    api_key: str,
    org_id: str,
    ws_a: str,
    ws_b: str,
    user_jwt: str | None = None,
) -> None:
    lines = [
        "# Auto-generated by setup_prod_smoke_account.py — do not commit.",
        f"OMOIOS_API_BASE_URL={api_base}",
        f"OMOIOS_TEST_EMAIL={email}",
        f"OMOIOS_TEST_PASSWORD={password}",  # pragma: allowlist secret
        f"OMOIOS_PLATFORM_API_KEY={api_key}",  # pragma: allowlist secret
        f"OMOIOS_TEST_ORG_ID={org_id}",
        f"OMOIOS_TEST_WORKSPACE_A={ws_a}",
        f"OMOIOS_TEST_WORKSPACE_B={ws_b}",
    ]
    if user_jwt:
        lines.append(f"OMOIOS_USER_JWT={user_jwt}")  # pragma: allowlist secret
    ENV_OUT.write_text("\n".join(lines) + "\n")
    os.chmod(ENV_OUT, 0o600)
    print(f"  ✔ wrote credentials to {ENV_OUT} (mode 0600)")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-base-url", default="https://api.omoios.dev")
    p.add_argument("--email", default="omoi-smoke@autoworkz.org")
    p.add_argument("--full-name", default="OmoiOS Smoke")
    p.add_argument("--org-name", default="OmoiOS Smoke Org")
    args = p.parse_args()

    password = gen_password()
    db = parse_db_url(ENV_PROD)
    print(f"▸ API: {args.api_base_url}")
    print(f"▸ user: {args.email}")
    print(f"▸ db: {db['host']}:{db['port']}/{db['dbname']}")

    # Pre-flight: does the user already exist? If so, skip register entirely and
    # reset password directly. Avoids 500s from register endpoints that don't
    # cleanly express "already exists".
    user_exists = False
    with psycopg.connect(**db) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE email = %s", (args.email,))
        user_exists = cur.fetchone() is not None

    with httpx.Client(base_url=args.api_base_url, timeout=30.0) as client:
        if user_exists:
            r = httpx.Response(409, content=b"user exists (pre-checked)")
        else:
            r = post(client, "/api/v1/auth/register",
                     {"email": args.email, "password": password, "full_name": args.full_name})
        if r.status_code in (200, 201):
            print(f"  ✔ registered {args.email}")
        elif user_exists or (r.status_code in (400, 409) and "already" in r.text.lower()):
            # User exists — for an existing user we don't know the password.
            # Reset it via DB so we have control going forward.
            print(f"  ⚠ user exists; resetting password via direct DB write")
            from passlib.context import CryptContext  # type: ignore
            pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)
            with psycopg.connect(**db) as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET hashed_password = %s, is_verified = TRUE, is_active = TRUE WHERE email = %s",
                    (pwd, args.email),
                )
                conn.commit()
                print(f"  ✔ reset password + verified for {args.email}")
        else:
            sys.exit(f"register failed: {r.status_code} {r.text[:400]}")

        # Try login. If verification gates it, promote in DB and retry.
        token = login(client, args.email, password)
        if token is None:
            print(f"  ⚠ login failed — promoting is_verified=true and retrying")
            ensure_verified(db, args.email)
            token = login(client, args.email, password)
            if token is None:
                sys.exit(f"login still failing after DB-level verification")
        print(f"  ✔ logged in")

        org_id = pick_or_create_org(client, token, args.org_name)
        if not org_id:
            sys.exit("no org_id, cannot continue")

        api_key = mint_key(client, token, name=f"smoke-{args.email}", org_id=org_id)
        print(f"  ✔ minted api key {api_key[:14]}…")

        ws_a = ensure_workspace(client, token, org_id, "smoke-a")
        ws_b = ensure_workspace(client, token, org_id, "smoke-b")
        if not ws_a or not ws_b:
            sys.exit("failed to ensure both workspaces")

    write_env(args.api_base_url, args.email, password, api_key, org_id, ws_a, ws_b, user_jwt=token)
    print()
    print("─" * 72)
    print(f"smoke-test credentials saved to {ENV_OUT}")
    print(f"  email: {args.email}")
    print(f"  password: <stored in env file>")
    print(f"  api key: {api_key[:14]}…")
    print(f"  org: {org_id}")
    print(f"  ws_a: {ws_a}")
    print(f"  ws_b: {ws_b}")
    print("─" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
