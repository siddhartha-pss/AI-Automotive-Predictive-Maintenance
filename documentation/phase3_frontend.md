# Phase 3 - Frontend (React dashboard)

## What was built

A single-page React app (Vite) with one dashboard view, matching the master
prompt's "do not overload the dashboard" instruction - no router, no auth, no
extra pages, just the sections that matter:

1. Vehicle Overview (vehicle ID, anomaly status, driving profile - quick stat cards)
2. Anomaly Detection (status, method, honest note on what the model actually is)
3. Fault Classification (predicted class, confidence, the live-OBD2-compatibility
   limitation surfaced directly in the UI, not just in docs)
4. Driver Behaviour (profile, honest note that this is clustering, not prediction)
5. Maintenance Report (the LLM output, with a visible warning banner when it's a
   mock/fallback report rather than a real LLM response)

A "Load Sample Vehicle Analysis" button calls the backend
(`GET /api/vehicle/sample` then `POST /api/report`) and renders the real response -
nothing on screen is hardcoded/fake data baked into the frontend.

## What was actually verified in this environment

- `npm run build` completes with no errors (production build succeeds).
- The Vite dev server starts and serves the page (`curl` against
  `http://localhost:5173` returns the expected HTML shell).
- The backend endpoints the frontend calls were independently verified working
  (see `phase3_backend.md`).

## What was NOT verified (be honest about this)

This environment has no browser available, so the actual rendered UI - layout,
click-through behaviour, whether the fetch calls succeed from inside a real browser
tab (CORS, console errors, etc.) - was **not** visually tested. The code compiles
and the API contract it depends on is confirmed correct, but "looks right in code"
is not the same claim as "confirmed working in a browser." Open
`http://localhost:5173` yourself (with both `node src/server.js` in `backend/` and
`uvicorn main:app --port 8000` in `ml_service/` running) and click the button to
get the real confirmation.

## Styling

Plain CSS (`App.css`), dark theme, no UI framework - kept deliberately simple per
the "don't over-engineer, this is a student project" guidance. Stat cards use a
colored left-border (green/amber) to flag normal vs. attention-worthy results at a
glance.
