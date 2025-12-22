#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Determine number of workers
if [ -z "$WEB_CONCURRENCY" ]; then
    # Auto-detect: use min(CPU_CORES, 4) to leave headroom
    CPU_CORES=$(nproc 2>/dev/null || echo 2)
    WEB_CONCURRENCY=$((CPU_CORES < 4 ? CPU_CORES : 4))
    echo "Auto-detected $CPU_CORES CPU cores, using $WEB_CONCURRENCY workers"
else
    echo "Using configured $WEB_CONCURRENCY workers"
fi

# Start the server
if [ "$RELOAD_MODE" = "true" ]; then
    # Development mode: use uvicorn directly with reload
    echo "Starting uvicorn in reload mode (single worker)..."
    exec uvicorn omoi_os.api.main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --reload
else
    # Production mode: use gunicorn with uvicorn workers
    echo "Starting gunicorn with $WEB_CONCURRENCY uvicorn workers..."
    exec gunicorn omoi_os.api.main:app \
        --bind "0.0.0.0:$PORT" \
        --workers "$WEB_CONCURRENCY" \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --graceful-timeout 30 \
        --keep-alive 5 \
        --access-logfile - \
        --error-logfile -
fi
