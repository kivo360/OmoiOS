#!/bin/bash
# Script to run Alembic migrations against Railway database
# Usage: ./scripts/run_migration_railway.sh [DATABASE_PUBLIC_URL]
#
# If DATABASE_PUBLIC_URL is provided as argument, it will be used.
# Otherwise, the script will try to get it from Railway or prompt for it.

set -e

cd "$(dirname "$0")/.."

# If DATABASE_PUBLIC_URL provided as argument, use it
if [ -n "$1" ]; then
    RAILWAY_DB_URL="$1"
        # Note: Railway proxy doesn't require SSL, so we don't add sslmode parameter
    echo "✅ Using provided DATABASE_URL: ${RAILWAY_DB_URL:0:60}..."
else
    # Check if DATABASE_URL is already set in environment
    if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" != *"railway.internal"* ]]; then
        RAILWAY_DB_URL="$DATABASE_URL"
        echo "✅ Using DATABASE_URL from environment: ${RAILWAY_DB_URL:0:60}..."
    else
        echo "🔍 Checking Railway for DATABASE_PUBLIC_URL..."
        
        # Try to get DATABASE_PUBLIC_URL from Railway (may not be in API service vars)
        RAILWAY_DB_URL=$(railway variables 2>&1 | grep -i "DATABASE_PUBLIC_URL" -A 2 | grep -v "DATABASE_PUBLIC_URL" | head -1 | sed 's/│//g' | xargs || true)
        
        if [ -z "$RAILWAY_DB_URL" ] || [[ "$RAILWAY_DB_URL" == *"railway.internal"* ]]; then
            echo ""
            echo "⚠️  DATABASE_PUBLIC_URL not found or is internal URL"
            echo ""
            echo "To connect from local machine, you need DATABASE_PUBLIC_URL:"
            echo "1. Go to Railway dashboard: https://railway.app"
            echo "2. Select your pgvector/PostgreSQL service"
            echo "3. Go to 'Variables' tab"
            echo "4. Copy the value of 'DATABASE_PUBLIC_URL'"
            echo ""
            echo "Then run this script with the URL:"
            echo "  ./scripts/run_migration_railway.sh '<DATABASE_PUBLIC_URL>'"
            echo ""
            echo "Or export it and run migration manually:"
            echo "  export DATABASE_URL='<DATABASE_PUBLIC_URL>?sslmode=require'"
            echo "  uv run alembic upgrade head"
            exit 1
        fi
        
        # Note: Railway proxy doesn't require SSL, so we don't add sslmode parameter
    fi
fi

export DATABASE_URL="$RAILWAY_DB_URL"

echo ""
echo "🚀 Running migration against Railway database..."
uv run alembic upgrade head

echo ""
echo "✅ Migration complete!"
