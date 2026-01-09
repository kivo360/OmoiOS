#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Determine number of workers
if [ -z "$WEB_CONCURRENCY" ]; then
    # Auto-detect CPU cores
    CPU_CORES=$(nproc 2>/dev/null || echo 2)

    # Calculate workers: 2 * cores + 1, but cap based on available memory
    # Each worker uses ~150-300MB RAM, so for 8GB RAM, max ~25-50 workers
    # Default cap at 32 workers unless MAX_WORKERS is set
    MAX_WORKERS=${MAX_WORKERS:-32}
    CALCULATED=$((CPU_CORES * 2 + 1))

    if [ "$CALCULATED" -gt "$MAX_WORKERS" ]; then
        WEB_CONCURRENCY=$MAX_WORKERS
    else
        WEB_CONCURRENCY=$CALCULATED
    fi

    echo "Auto-detected $CPU_CORES CPU cores, using $WEB_CONCURRENCY workers (max: $MAX_WORKERS)"
else
    echo "Using configured $WEB_CONCURRENCY workers"
fi

export WEB_CONCURRENCY

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
    echo "Starting gunicorn with $WEB_CONCURRENCY uvicorn workers on port $PORT..."
    exec gunicorn omoi_os.api.main:app \
        --bind "0.0.0.0:$PORT" \
        --workers "$WEB_CONCURRENCY" \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --graceful-timeout 30 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --access-logfile - \
        --error-logfile - \
        --capture-output \
        --enable-stdio-inheritance
fi
