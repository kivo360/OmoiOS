#!/usr/bin/env bash
# Idempotent local-Postgres bring-up via pg0 (no Docker required).
#
# Listens on :15432 (the +10000 dev offset that tests use), creates
# omoi_os_dev (default) and app_db (test target). Safe to re-run.
set -euo pipefail

PG0="${HOME}/.local/bin/pg0"

if ! [ -x "$PG0" ]; then
  echo "Installing pg0..."
  curl -fsSL https://raw.githubusercontent.com/vectorize-io/pg0/main/install.sh | bash
fi

if "$PG0" list 2>/dev/null | grep -E '^\s*omoi-os' | grep -q running; then
  echo "pg0 instance 'omoi-os' already running"
else
  "$PG0" start --name omoi-os --port 15432 --database omoi_os_dev
fi

# Tests expect a database called app_db; create it if missing.
EXISTS=$(PGPASSWORD=postgres psql -h 127.0.0.1 -p 15432 -U postgres -d postgres \
  -tAc "SELECT 1 FROM pg_database WHERE datname='app_db'" 2>/dev/null || true)
if [ "$EXISTS" != "1" ]; then
  PGPASSWORD=postgres psql -h 127.0.0.1 -p 15432 -U postgres -d postgres \
    -c "CREATE DATABASE app_db;"
fi

echo "Connection (dev):  postgresql://postgres:postgres@127.0.0.1:15432/omoi_os_dev"
echo "Connection (test): postgresql://postgres:postgres@127.0.0.1:15432/app_db"
