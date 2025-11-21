# Ticket Panel Prototype

Quick React prototype for testing the ticket agent API.

## Setup

```bash
cd examples/frontend
npm install
```

## Run

```bash
npm run dev
```

The app will be available at `http://localhost:3000` and will proxy API requests to the FastAPI backend at `http://localhost:18001`.

Make sure the FastAPI backend is running:
```bash
uv run uvicorn examples.example2_api_backend:app --host 0.0.0.0 --port 18001 --reload
```

