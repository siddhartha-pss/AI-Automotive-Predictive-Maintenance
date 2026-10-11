# Phase 3 - Backend (FastAPI ML service + Node/Express)

## Architecture

```
React frontend (Vite, port 5173)
    -> Node/Express backend (port 5000)
         -> FastAPI ML service (port 8000) - loads the 3 Phase 1 models, runs inference
         -> Anthropic API (Claude Haiku 4.5) or mock fallback - Phase 2 report
    -> MongoDB (connection code written, not run in this environment - see below)
```

Python owns all ML code (no model logic re-implemented in JavaScript). Express is a
thin orchestrator: it calls the FastAPI service for predictions, then calls the LLM
step, and returns both to the frontend in one response.

## FastAPI ML service (`ml_service/main.py`)

Endpoints:
- `GET /health`
- `POST /predict/anomaly`, `/predict/fault`, `/predict/behaviour` - run one module
- `POST /predict/combined` - runs all three and returns the combined vehicle-health
  context (same shape as `src/combined_inference.py`)

Models are loaded once at startup (`@app.on_event("startup")`), not per-request.

**Verified working in this environment:** started with
`uvicorn main:app --port 8000`, confirmed `/health` returns `{"status": "ok"}` and
`/predict/combined` returns a correct combined JSON for a hand-built test payload
(see the exact curl commands and output captured during development).

## Express backend (`backend/`)

Routes:
- `GET /api/health` - reports whether the LLM is in live or mock mode
- `GET /api/vehicle/sample` - serves the Phase 1 sample combined output for the
  frontend to render before live FastAPI wiring is needed
- `POST /api/report` - runs only the LLM step on a given vehicle-context JSON
- `POST /api/analyze` - the full chain: raw sensor-style input -> FastAPI
  `/predict/combined` -> LLM report -> combined response

**Verified working in this environment:** started with `node src/server.js`,
confirmed all four routes above return correct JSON against real requests (not
assumed - actually executed and checked).

## MongoDB - RESOLVED (previously the biggest open gap)

**Update:** MongoDB persistence is now implemented and was actually connected
and tested in this environment (Docker Desktop was started, a real `mongo:7`
container was run, and the full save/retrieve/reconnect cycle was verified
against it). Full detail: `documentation/mongodb_implementation_report.md`.

## Environment variables

`backend/.env.example` documents `PORT`, `ML_SERVICE_URL`, `MONGODB_URI`,
`MONGODB_DB_NAME`, `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`. Copy to `.env` and fill in real values;
`.env` itself is not committed.
