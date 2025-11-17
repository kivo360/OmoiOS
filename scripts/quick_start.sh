#!/bin/bash
# Quick Start Script - Get OmoiOS running in seconds
# Usage: ./scripts/quick_start.sh [level]
#   level 0: Just databases (default)
#   level 1: Databases + API
#   level 2: Databases + API + Worker (full E2E)

set -e

LEVEL=${1:-0}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 OmoiOS Quick Start - Level $LEVEL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Level 0: Databases
echo ""
echo "📦 Starting databases..."
docker-compose up -d postgres redis

echo "⏳ Waiting for databases to be healthy..."
until docker-compose ps | grep -q "healthy.*postgres"; do
  sleep 1
done
until docker-compose ps | grep -q "healthy.*redis"; do
  sleep 1
done

echo "✅ Databases ready!"
docker-compose ps

if [ "$LEVEL" = "0" ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "✅ LEVEL 0 COMPLETE"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "• PostgreSQL: localhost:15432"
  echo "• Redis: localhost:16379"
  echo ""
  echo "Test it:"
  echo "  uv run python scripts/smoke_test.py"
  exit 0
fi

# Level 1+: Apply migrations
echo ""
echo "🗃️  Running migrations..."
uv run alembic upgrade heads || {
  echo "⚠️  Migration failed - may need manual fix"
  echo "Try: uv run alembic heads"
}

# Check for missing columns (common issue)
echo ""
echo "🔍 Checking schema..."
HAS_PREVIOUS_PHASE=$(docker exec omoi_os_postgres psql -U postgres -d app_db -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='tickets' AND column_name='previous_phase_id';" || echo "")
if [ -z "$HAS_PREVIOUS_PHASE" ]; then
  echo "⚡ Adding missing previous_phase_id column..."
  docker exec omoi_os_postgres psql -U postgres -d app_db -c "ALTER TABLE tickets ADD COLUMN previous_phase_id VARCHAR(50); CREATE INDEX IF NOT EXISTS ix_tickets_previous_phase_id ON tickets(previous_phase_id);"
fi

# Level 1: API Server
if [ "$LEVEL" -ge "1" ]; then
  echo ""
  echo "🌐 Starting API server..."
  uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload &
  API_PID=$!
  
  echo "⏳ Waiting for API to start..."
  sleep 3
  
  until curl -s http://localhost:18000/health > /dev/null 2>&1; do
    sleep 1
  done
  
  echo "✅ API ready!"
  curl -s http://localhost:18000/health | jq .
  
  if [ "$LEVEL" = "1" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ LEVEL 1 COMPLETE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "• API: http://localhost:18000"
    echo "• Docs: http://localhost:18000/docs"
    echo "• API PID: $API_PID"
    echo ""
    echo "Stop API: kill $API_PID"
    echo ""
    echo "Press Ctrl+C to stop..."
    wait $API_PID
    exit 0
  fi
fi

# Level 2: Worker
if [ "$LEVEL" -ge "2" ]; then
  echo ""
  echo "🤖 Starting worker..."
  PHASE_ID=PHASE_IMPLEMENTATION uv run python -m omoi_os.worker &
  WORKER_PID=$!
  
  sleep 3
  
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "✅ LEVEL 2 COMPLETE - FULL E2E RUNNING!"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "• API: http://localhost:18000"
  echo "• Docs: http://localhost:18000/docs"
  echo "• API PID: $API_PID"
  echo "• Worker PID: $WORKER_PID"
  echo ""
  echo "Create a test task:"
  echo '  curl -X POST http://localhost:18000/create_task \'
  echo '    -H "Content-Type: application/json" \'
  echo '    -H "X-Agent-ID: test-cli" \'
  echo '    -d '"'"'{"task_description":"Test","done_definition":"Done","ai_agent_id":"test-cli","priority":"high"}'"'"
  echo ""
  echo "Stop all: kill $API_PID $WORKER_PID"
  echo ""
  echo "Press Ctrl+C to stop..."
  
  # Wait for both processes
  wait $API_PID $WORKER_PID
fi

