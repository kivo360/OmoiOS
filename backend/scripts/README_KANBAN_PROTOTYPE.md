# Kanban Board Prototype

A standalone HTML prototype for testing the Kanban board with real-time WebSocket updates.

## Quick Start

1. **Start the API server:**
   ```bash
   uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000 --reload
   ```

2. **Open the prototype:**
   - Open `scripts/kanban_prototype.html` in your browser
   - Or serve it via a local server:
     ```bash
     # Python 3
     cd scripts
     python3 -m http.server 8080
     # Then open http://localhost:8080/kanban_prototype.html
     ```

3. **The prototype will:**
   - Connect to WebSocket at `ws://localhost:18000/api/v1/ws/events`
   - Fetch board data from `http://localhost:18000/api/v1/board/view`
   - Display tickets in columns
   - Allow drag-and-drop to move tickets
   - Show real-time updates via WebSocket

## Features

- ✅ **Real-time Updates**: WebSocket connection shows live ticket movements
- ✅ **Drag & Drop**: Move tickets between columns
- ✅ **WIP Limits**: Visual indicators when columns exceed WIP limits
- ✅ **Priority Badges**: Color-coded priority indicators
- ✅ **Event Log**: Shows recent WebSocket events (bottom-right)
- ✅ **Connection Status**: Visual indicator for WebSocket connection

## Configuration

Edit the constants at the top of the HTML file:

```javascript
const API_BASE = 'http://localhost:18000/api/v1';
const WS_URL = 'ws://localhost:18000/api/v1/ws/events';
```

## Testing

1. **Create some tickets** via the API:
   ```bash
   curl -X POST http://localhost:18000/api/v1/tickets \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Test Ticket",
       "phase_id": "PHASE_BACKLOG",
       "priority": "HIGH"
     }'
   ```

2. **Move tickets** by dragging them in the UI

3. **Watch real-time updates** in the event log

## Troubleshooting

- **"Failed to load board"**: Make sure the API server is running and database is accessible
- **WebSocket disconnected**: Check that Redis is running (required for event bus)
- **No columns shown**: Create board columns first using the `BoardService.create_default_board()` method

## Next Steps

This prototype demonstrates:
- Backend API integration
- WebSocket real-time updates
- Drag-and-drop functionality

For production, you'll want to:
- Add authentication
- Improve error handling
- Add more ticket details
- Implement filtering/search
- Add animations/transitions

