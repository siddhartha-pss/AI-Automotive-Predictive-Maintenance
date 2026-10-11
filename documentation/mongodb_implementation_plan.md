# MongoDB Persistence - Implementation Plan

Written before implementation, based on actually reading the current code
(`backend/src/server.js`, `backend/src/routes/{report,vehicle,analyze}.js`,
`backend/src/llm/*`, `outputs/sample_combined_vehicle_context.json`,
`backend/.env.example`, `backend/package.json`, `frontend/src/App.jsx`).

## 1. Existing architecture

```
React (:5173) -> Express (:5000) -> FastAPI (:8000) -> 3 ML models
                      |
                      -> LLM provider dispatcher (mock/gemini/anthropic)
```

Routes today:
- `POST /api/analyze` (`routes/analyze.js`) - the full chain: raw sensor-style
  body -> FastAPI `/predict/combined` -> `generateMaintenanceReport()` ->
  `{vehicle_context, llm_report}`. **Nothing is persisted after this today.**
- `POST /api/report` (`routes/report.js`) - LLM step only, given an existing
  vehicle-context JSON.
- `GET /api/vehicle/sample` (`routes/vehicle.js`) - serves the one static saved
  sample file, `outputs/sample_combined_vehicle_context.json`.
- `GET /api/health` (`server.js`) - reports LLM provider status.

## 2. Existing combined output schema (source of truth, from the actual saved file)

```json
{
  "vehicle_meta": {"vehicle_id": "demo-vehicle-01", "source": "..."},
  "anomaly": {"status": "Normal|Abnormal", "raw_decision_score": 0.0, "method": "...", "input_compatible_with_live_obd2": true},
  "fault": {"predicted_fault": "...", "predicted_fault_code": "...", "confidence": 0.0, "method": "...", "label_source": "...", "input_compatible_with_live_obd2": true, "note": "...", "scope_limitation": "..."},
  "driver_behaviour": {"behaviour_profile": "...", "cluster_id": 0, "method": "...", "input_compatible_with_live_obd2": true},
  "schema_version": "1.0"
}
```

The LLM report shape (`generateMaintenanceReport()` return value):
```json
{"mode": "live|mock|error_fallback", "provider": "gemini|anthropic|mock?", "model": "...", "note": "...", "report": {"overall_status": "...", "summary": "...", "...": "..."}}
```

**`vehicle_meta.vehicle_id` already exists and is already stable** ("demo-vehicle-01"
in the sample). No new ID scheme is needed - see section "Vehicle ID decision" below.

## 3. Proposed MongoDB architecture

```
POST /api/analyze
   -> FastAPI /predict/combined          (unchanged)
   -> generateMaintenanceReport()         (unchanged)
   -> build analysis document             (new)
   -> save to MongoDB (non-blocking of the response - see Error Handling)  (new)
   -> return {vehicle_context, llm_report, persistence}  (persistence is new, additive)
```

Single new layer: `backend/src/db/` (connection + a small repository module),
following the existing project convention of plain functions in small files
rather than classes - matches `llm/reportGenerator.js`'s style.

## 4. Proposed document structure

One collection, `vehicle_analyses`. The document **wraps the existing schema
unchanged** rather than flattening/renaming it - this avoids inventing a new
shape that duplicates what `combined_inference.py` / FastAPI already produce,
and keeps the Mongo document byte-for-byte consistent with what the dashboard
already renders.

```js
{
  _id: ObjectId,
  vehicleId: "demo-vehicle-01",       // copied from vehicle_context.vehicle_meta.vehicle_id
  timestamp: ISODate("..."),          // backend-generated, authoritative (see Timestamp section)
  vehicleContext: { ... },            // the EXACT existing combined-output object, unmodified
  llmReport: { ... },                 // the EXACT existing generateMaintenanceReport() return value
  metadata: {
    savedAt: ISODate("..."),
    source: "api/analyze" | "manual-sample"
  }
}
```

No field is duplicated between `vehicleId`/`timestamp` (used for indexing/
querying) and the nested objects (used for display) - `vehicleId` is just a
promoted copy of `vehicleContext.vehicle_meta.vehicle_id` for indexing.

## 5. Required APIs

Inspected existing routes first; nothing existing can be cleanly extended for
history (there is no prior persistence route at all), so these are genuinely
new, not duplicates:

- `POST /api/analyze` - **extended** (not duplicated) to save after a
  successful analysis; response gains a `persistence` field, everything else
  unchanged.
- `GET /api/vehicle/:vehicleId/history?limit=20` - chronological (newest
  first) list.
- `GET /api/vehicle/:vehicleId/latest` - most recent analysis for a vehicle.
- `GET /api/vehicle/analysis/:id` - one specific analysis by its Mongo `_id`.
- `GET /api/health` - **extended** (not duplicated) to also report MongoDB
  connection status alongside the existing LLM status.

## 6. Frontend changes

Additive only - `App.jsx` keeps its existing "Load Sample Vehicle Analysis"
button and all 4 existing result sections untouched. One new section,
"Vehicle Analysis History", added below the existing Maintenance Report
section: a simple table (date, anomaly, fault) with each row expandable to
show that record's full anomaly/fault/driver-behaviour/report detail - per the
task's explicit fallback instruction ("if selecting a previous analysis
significantly complicates the UI, implement a simple expandable history entry
instead").

## 7. Environment requirements

New variables (added to `.env.example`, never committed with real values):
```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=predictive_maintenance
```
`PORT`, `ML_SERVICE_URL`, and all LLM variables are preserved unchanged.

## 8. Testing strategy

1. Check what's actually available in this environment first (Docker daemon,
   local `mongod`) before writing a single line of DB code - done, documented
   honestly in the implementation report regardless of outcome.
2. If a real MongoDB instance can be reached: actually connect, actually save
   a real analysis (from the existing real sample, not fabricated data),
   actually query it back via all 4 new endpoints, actually test the
   MongoDB-unavailable graceful-degradation path by stopping it mid-session.
3. If no instance is reachable: implement the full connection/repository layer
   (it does not require a live DB to be correct code), verify every *other*
   part of the regression suite (ML, LLM, existing endpoints, frontend build),
   and clearly mark the DB-specific tests as "NOT VERIFIED - no MongoDB
   instance available", with exact setup commands for both Docker and Atlas
   so the user can complete verification themselves.

## Vehicle ID decision

`vehicle_meta.vehicle_id` already exists in every combined-output object
("demo-vehicle-01" for the sample data) and is already stable (the same string
every time the same sample is analyzed) - this is used directly as `vehicleId`
in Mongo. No new ID generation scheme is introduced.

## Timestamp decision

The Express route generates `timestamp` with `new Date()` at the moment the
document is saved (after the LLM step completes) - never trusted from the
request body or the frontend. This is the one authoritative timestamp.

## Save-on-LLM-failure decision

The task asks whether a fallback (`mock`/`error_fallback`) report should still
be saved. **Decision: yes, save it.** `generateMaintenanceReport()` already
guarantees a usable `report` object in every mode (mock, live, error_fallback)
- that is the whole point of its fallback design. An "incomplete" analysis
would mean the ML step itself failed (no `vehicle_context` at all), which
already short-circuits with a 502 in `routes/analyze.js` before reaching the
save step - so nothing incomplete is ever saved. What IS saved whenever
`vehicle_context` exists is the LLM result as actually generated, honestly
labeled with its real `mode` - exactly like every other part of this project.
