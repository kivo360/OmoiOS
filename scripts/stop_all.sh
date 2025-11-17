#!/bin/bash
# Stop all OmoiOS services

echo "🛑 Stopping OmoiOS services..."

# Stop API
echo "  • Stopping API..."
pkill -f "uvicorn omoi_os.api.main" && echo "    ✓ API stopped" || echo "    - No API running"

# Stop Worker
echo "  • Stopping Worker..."
pkill -f "omoi_os.worker" && echo "    ✓ Worker stopped" || echo "    - No Worker running"

# Stop Docker containers (optional - keep them running for faster restart)
read -p "Stop Docker containers too? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "  • Stopping Docker containers..."
  docker-compose down
  echo "    ✓ Docker stopped"
else
  echo "  • Keeping Docker containers running for faster restart"
fi

echo ""
echo "✅ All services stopped"
echo ""
echo "To restart:"
echo "  ./scripts/quick_start.sh 2"

