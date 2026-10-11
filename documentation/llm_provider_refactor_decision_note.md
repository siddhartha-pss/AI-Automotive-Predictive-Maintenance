# Decision Note - LLM Provider-Independent Refactor

Written before making any changes, per the inspection-first requirement.

## Current LLM flow (as found)

```
routes/report.js  --calls-->  generateReport(vehicleContext)  (in llm/reportGenerator.js)
routes/analyze.js --calls-->  generateReport(vehicleContext)  (same function)
```

`generateReport()` in `backend/src/llm/reportGenerator.js` currently:
1. Reads `process.env.ANTHROPIC_API_KEY` directly.
2. If unset -> returns `mockReport(vehicleContext)` (a hand-written rule-based
   report, flat schema: overall_condition, detected_abnormality, probable_fault,
   severity, driver_behaviour_summary, possible_link_to_wear, recommended_action,
   confidence_note).
3. If set -> constructs an `Anthropic` client inline, calls
   `client.messages.create(...)` with a hard-coded `SYSTEM_PROMPT` string, parses
   the text response as JSON.
4. On any error -> falls back to `mockReport()` but overrides `mode`/`note` to
   `error_fallback` (this was the object-spread-ordering bug fixed during the
   previous validation pass - already correct in the current file).

Response envelope shape returned to both routes: `{mode, note?, model?, report}`.

## Files involved

- `backend/src/llm/reportGenerator.js` - the only place Anthropic is called, and
  the only place `ANTHROPIC_API_KEY` is referenced.
- `backend/src/routes/report.js` - `POST /api/report`, takes a vehicle-context
  JSON body, calls `generateReport()`, returns its result directly.
- `backend/src/routes/analyze.js` - `POST /api/analyze`, calls FastAPI
  `/predict/combined` then `generateReport()`, returns
  `{vehicle_context, llm_report}`.
- `backend/src/server.js` - `GET /api/health` reports
  `llm_mode: process.env.ANTHROPIC_API_KEY ? "live" : "mock"` - also
  provider-specific and needs generalizing.
- `backend/package.json` - only `@anthropic-ai/sdk` is currently installed for
  LLM access.
- `backend/.env.example` / `backend/.env` - currently `ANTHROPIC_API_KEY`,
  `LLM_MODEL`. The real `.env` on disk already has `LLM_PROVIDER=gemini` and a
  `GEMINI_API_KEY` value added by the user ahead of this task.
- `frontend/src/App.jsx` - **does not hardcode any report field names.** It reads
  `report.mode`, `report.note`, and renders `Object.entries(report.report)`
  generically. This means the inner report schema can change freely without
  breaking the frontend - confirmed by reading the component before deciding
  anything.
- `documentation/phase2_llm_integration.md` - describes the current
  Anthropic-only design; will need updating, not deleting (the Anthropic
  reasoning/history stays valid, it's just no longer the only provider).

## What must remain unchanged

- `FastAPI` ML service, the 3 trained models, datasets, preprocessing, and the
  combined-output JSON schema (`vehicle_meta, anomaly, fault, driver_behaviour,
  schema_version`) - none of this is touched.
- The outer response envelope contract the frontend depends on:
  `{mode, note?, model?, report: {...flat object...}}`.
- `routes/report.js` and `routes/analyze.js` public behavior (same endpoints,
  same request/response shape at the HTTP level) - only their internal import
  changes (function name).
- Existing env vars `PORT`, `ML_SERVICE_URL` (already read with a sane default in
  `analyze.js`) - preserved, not deleted.
- The Anthropic integration itself is not deleted - it already works (verified in
  the previous validation pass) and the task rules say to retain existing
  provider code that's useful. It becomes one provider among several instead of
  the only option.

## What needs to change

1. Extract the Anthropic-calling code out of `reportGenerator.js` into its own
   provider module.
2. Extract the mock report into its own provider module (same logic, same
   output).
3. Add a new Gemini provider module using the current official SDK
   (`@google/genai` - confirmed as the actively maintained package; the older
   `@google/generative-ai` is legacy/lower-churn and not the recommended choice
   for new code).
4. Turn `reportGenerator.js` into a thin orchestrator:
   `generateMaintenanceReport(vehicleContext)` that reads `LLM_PROVIDER` and
   dispatches to the right provider module, with a shared error-handling /
   fallback-to-mock path so every provider gets the same safety net.
5. Share one prompt/schema definition across providers (currently the prompt text
   lives only inside the Anthropic call) so Gemini and Anthropic explain the ML
   results the same way.
6. Update `.env.example` to document `LLM_PROVIDER`, `GEMINI_API_KEY`,
   `GEMINI_MODEL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (renamed from the
   generic `LLM_MODEL` now that there are multiple providers), `ML_SERVICE_URL`.
7. Update `server.js`'s health check to report the configured provider generically
   instead of checking `ANTHROPIC_API_KEY` specifically.
8. Small, necessary frontend tweak: the new schema's `recommended_actions` field
   is an array (per the task's suggested schema); `App.jsx`'s generic renderer
   needs a one-line adjustment so an array renders as a readable list instead of
   concatenated text. Nothing else in the frontend changes.
9. Update `documentation/phase2_llm_integration.md` and add the new
   provider-architecture documentation and decision log entries.

No other files need to change.
