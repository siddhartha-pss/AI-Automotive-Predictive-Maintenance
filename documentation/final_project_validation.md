# Final Project Validation Report

Date of validation: 2026-10-04. This report was produced by re-running the actual
system (not by re-reading old claims) - every number and endpoint response below
was checked live during this validation pass. No model, dataset, or architecture
decision was changed. One real bug was found and fixed (see Section 5).

> **Point-in-time snapshot - since superseded in places.** The fault classifier
> (originally EngineFaultDB/XGBoost) and MongoDB's status (originally "not
> implemented", Section 4/8 below) have both changed since this report was
> written - see `fault_classification_replacement_report.md` and
> `mongodb_implementation_report.md` for the current state. The rest of this
> report (anomaly detection, driver behaviour, LLM mock/error-fallback testing
> methodology) remains accurate and is left as originally written.

---

## 1. Complete end-to-end workflow

```
Raw sensor-style input (JSON: anomaly_input + fault_input + behaviour_input)
  -> POST /api/analyze (Express, :5000)
    -> POST /predict/combined (FastAPI, :8000)
         loads 3 saved models (OneClassSVM, XGBoost, KMeans) from models/*.joblib
         -> runs anomaly detection, fault classification, driver-behaviour clustering
         -> returns one combined JSON {vehicle_meta, anomaly, fault, driver_behaviour, schema_version}
    -> combined JSON passed to generateReport() (backend/src/llm/reportGenerator.js)
         -> if ANTHROPIC_API_KEY set: calls Claude Haiku 4.5, parses its JSON reply
         -> if not set (or the call fails): returns a rule-based template report instead
    -> Express returns {vehicle_context, llm_report} to the caller
  -> React dashboard (Vite, :5173) renders both the ML context and the plain-language report
```

This exact chain was executed live during this validation (Section 6) and produced
correct, consistent output.

---

## 2. Phase 1 - per module

### Anomaly Detection

- **Dataset:** carOBD (real Toyota Etios OBD-II logs, 126 trips, 298,303 usable rows)
- **Input features:** ENGINE_RPM, VEHICLE_SPEED, THROTTLE, ENGINE_LOAD,
  COOLANT_TEMPERATURE, LONG_TERM_FUEL_TRIM_BANK_1, SHORT_TERM_FUEL_TRIM_BANK_1,
  INTAKE_MANIFOLD_PRESSURE, INTAKE_AIR_TEMP, TIMING_ADVANCE, CONTROL_MODULE_VOLTAGE
- **Preprocessing:** numeric coercion (source files had leading-space string
  artifacts), rows with missing feature values dropped, trip-level (not random-row)
  train/test split to avoid leaking near-identical consecutive seconds
- **Model:** One-Class SVM (compared against Isolation Forest and Local Outlier
  Factor)
- **Why selected:** best synthetic-validation F1 (0.500) among the three, and a
  real-data anomaly rate (3.59%) close to the 3% contamination assumption used to
  train it - a reasonable sanity signal. carOBD has no fault labels at all, so a
  one-class/unsupervised approach is the technically correct family for this
  dataset (confirmed by the dataset's own source thesis).
- **Output:** `{status: Normal|Abnormal, raw_decision_score, method}`
- **Evaluation metrics:** synthetic-validation precision/recall/F1 (from injected
  perturbations, used ONLY for validation) + real-data anomaly rate (sanity check)
- **Limitations:** no real-world fault ground truth exists for this dataset, so no
  number here proves real-fault detection accuracy. One-Class SVM was trained on a
  10,000-row subsample (full 239K rows doesn't scale to its O(n^2) cost).

### Fault Classification

- **Dataset:** EngineFaultDB (real lab-bench engine data, 55,999 rows, 4 classes)
- **Input features:** MAP, TPS, Force, Power, RPM, Consumption L/H,
  Consumption L/100KM, Speed, CO, HC, CO2, O2, Lambda, AFR
- **Preprocessing:** 1 duplicate row dropped; otherwise no missing values, 70/15/15
  stratified train/val/test split
- **Model:** XGBoost (compared against Logistic Regression and Random Forest)
- **Why selected:** best validation macro-F1 (0.7528) among the three, consistent
  with the project's own literature review (XGBoost outperforming Random
  Forest/Decision Tree on engineered vehicle signals)
- **Output:** `{predicted_fault_class, confidence, label_source, input_compatible_with_live_obd2}`
- **Evaluation metrics:** accuracy, macro-precision/recall/F1, confusion matrix
  (test set, evaluated once) - test macro-F1 = 0.7589
- **Limitations:**
  1. Labels are real but **lab-induced**, not from an in-service vehicle.
  2. Classes 2 and 3 are confused roughly 50/50 by the model (see confusion matrix
     in `phase1_fault_classification.md`) - overall accuracy alone hides this.
  3. **Input schema does not match live OBD-II** - needs exhaust-gas-analyzer and
     dynamometer readings (CO, HC, CO2, O2, Lambda, AFR, Force, Power) that a
     consumer ELM327 connection cannot supply. Confirmed still true in this
     validation pass (`input_compatible_with_live_obd2: false` in every live test).

### Driver Behaviour Analysis

- **Dataset:** carOBD (same source as anomaly detection, aggregated per trip)
- **Input features:** per-trip speed (mean/std/max), acceleration (mean abs, max,
  harsh-accel rate, harsh-brake rate), RPM (mean/std), throttle (mean/std), engine
  load (mean) - 126 trips
- **Preprocessing:** per-trip feature engineering from the 1 Hz speed series;
  standardized before clustering
- **Model:** K-Means (K=3, chosen from K=2..5 by silhouette score)
- **Why selected:** this is **not** a predictive model - there is no ground-truth
  driving-style label in the dataset, so it's feature engineering + unsupervised
  clustering. K=3 gave the best silhouette score (0.589) among K=2..5.
- **Output:** `{behaviour_profile: Low/Moderate/High Intensity, cluster_id}`
- **Evaluation metrics:** silhouette score (0.589 for the selected K) - NOT
  accuracy, since no ground truth exists to be "accurate" against
- **Limitations:** only 126 trips (small for clustering); the "High Intensity"
  cluster has only 8 trips, so that profile's centroid is less statistically
  stable than the other two.

---

## 3. Phase 2 - LLM integration

- **How the three ML outputs are combined:** `build_vehicle_health_context()` in
  `src/combined_inference.py` (and mirrored in `ml_service/main.py`) assembles the
  anomaly, fault, and driver_behaviour results plus vehicle_meta into one flat JSON
  object - no mathematical combination, just structured assembly.
- **Schema:** `{vehicle_meta, anomaly, fault, driver_behaviour, schema_version}` -
  confirmed unchanged in this validation pass (see Section 6 live responses).
- **What is sent to the LLM:** exactly that JSON object, serialized with
  `JSON.stringify(vehicleContext, null, 2)` - never raw sensor rows, never the full
  dataset.
- **LLM instructions (system prompt):** explain only what's in the given JSON;
  never invent a fault/value/diagnosis not present in it; state uncertainty
  honestly; return ONLY a JSON object with 8 fixed fields (overall_condition,
  detected_abnormality, probable_fault, severity, driver_behaviour_summary,
  possible_link_to_wear, recommended_action, confidence_note) - no markdown, no
  extra text.
- **What the LLM returns:** that 8-field JSON object, parsed with `JSON.parse()`.
- **Error/unavailability handling - RE-TESTED in this validation with a real
  invalid API key:**
  - No API key set -> `mode: "mock"`, rule-based template report, clearly labeled.
  - API key set but call fails (tested live with an invalid key, got a real 401
    from the Anthropic API) -> **before the fix found in this validation, this
    incorrectly also returned `mode: "mock"` and silently discarded the real error
    message.** After the fix (Section 5), it correctly returns
    `mode: "error_fallback"` with the actual error message included, and falls
    back to the same template report so the pipeline never crashes.

---

## 4. Phase 3 - React / Express / FastAPI / MongoDB

- **React (Vite, :5173):** one dashboard page, fetches `/api/vehicle/sample` then
  `/api/report` from the backend, renders Vehicle Overview / Anomaly / Fault /
  Driver Behaviour / Maintenance Report sections. Confirmed building (`npm run
  build`) and serving (HTTP 200) in this validation. **Not** confirmed in an actual
  browser - no browser is available in this environment, so click-through/console
  behaviour remains unverified.
- **Express (:5000):** thin orchestrator - `routes/report.js` calls the LLM step
  only, `routes/analyze.js` calls FastAPI then the LLM step, `routes/vehicle.js`
  serves the saved sample context. No ML logic lives here.
- **FastAPI (:8000):** the only place the 3 trained models are loaded (once, at
  startup) and run. Confirmed models load correctly and startup log prints "Models
  loaded successfully at startup."
- **MongoDB:** **not implemented.** No local MongoDB instance and no running
  Docker daemon were available in this environment (`docker ps` fails to connect;
  no `mongod`/`mongosh` on PATH) - confirmed still the case in this validation
  pass. No Mongoose code exists in the repo. This is not a bug, it's an
  intentionally-skipped feature pending a database instance to test against.
- **Communication between components:** plain HTTP/JSON (`fetch` in Express ->
  FastAPI; Anthropic SDK in Express -> Claude API; `fetch` in React -> Express).
  No message queue, no gRPC - kept simple per the project's own "don't
  over-engineer" instruction.

---

## 5. Bug found and fixed during this validation

**Bug:** `generateReport()`'s error-handling branch in
`backend/src/llm/reportGenerator.js` built its return object as
`{mode: "error_fallback", note: ..., ...mockReport(vehicleContext)}`. Because the
spread came last, `mockReport()`'s own `mode: "mock"` and `note: "..."` fields
silently overwrote the `error_fallback` labeling and the real error message was
lost. This was found by actually starting the backend with an invalid API key and
observing the real response, not by reading the code alone.

**Fix applied:** reordered the object literal so the spread comes first:
```js
return {
  ...mockReport(vehicleContext),
  mode: "error_fallback",
  note: `LLM call failed (${err.message}); falling back to template report.`,
};
```

**Re-verified after the fix:** same invalid-key test now correctly returns
`mode: "error_fallback"` with the real Anthropic API error
(`"401 ... authentication_error ... API key is invalid."`) surfaced in `note`.

No other code was changed. Model selections, datasets, metrics, and architecture
are exactly as previously documented.

---

## 6. Live endpoint checks performed in this validation (actual requests, not assumed)

| Endpoint | Method | Result |
|---|---|---|
| `GET /health` (FastAPI) | checked | `{"status":"ok"}` |
| `GET /api/health` (Express) | checked | correctly reports `live` vs `mock` LLM mode depending on `.env` |
| `POST /predict/anomaly` | checked | correct, deterministic result (matches earlier runs exactly) |
| `POST /predict/fault` | checked | correct, deterministic result |
| `POST /predict/behaviour` | checked | correct, deterministic result |
| `POST /predict/combined` | checked | correct, matches the sum of the three individual calls |
| `GET /api/vehicle/sample` | checked | serves the saved Phase 1 sample context correctly |
| `POST /api/report` (mock mode) | checked | correct template report |
| `POST /api/report` (invalid key, before fix) | checked | **bug found** - mislabeled as mock |
| `POST /api/report` (invalid key, after fix) | checked | correct `error_fallback` with real error |
| `POST /api/analyze` (full chain) | checked | correct combined response |
| FastAPI input validation (missing fields) | checked | returns proper 422 with field-level detail, does not crash |
| Express behaviour on malformed `/api/analyze` body | checked | returns a clean 502 with the FastAPI validation detail, does not crash |
| Model artifact loading (`joblib.load` on all 10 files) | checked | all 10 load correctly as the expected types (OneClassSVM, XGBClassifier, KMeans, 2x StandardScaler, 3x feature-list, 1x cluster-label dict) |

All documented metrics in `phase1_anomaly_detection.md`, `phase1_fault_classification.md`,
and `phase1_driver_behaviour.md` were cross-checked against the raw
`outputs/phase1_*.json` files in this pass and match exactly - no discrepancy found.

---

## 7. Claims we should NOT make (not experimentally verified)

- **"The dashboard works"** - only the build and HTTP-serving were confirmed; the
  actual rendered UI in a browser (layout, click behaviour, console errors) was
  never tested, because no browser is available in this environment.
- **"The LLM produces good-quality reports"** - only mock-mode and the
  error-fallback path (triggered by a deliberately invalid key) were tested. No
  real Claude API call has ever succeeded in this environment - there is no
  evidence about real report quality, only that the request-building and
  response-parsing code is correct up to the point the real API would respond
  (confirmed by getting a real, well-formed 401 from Anthropic's servers, which
  proves the request reaches the API correctly).
- **"Fault classification works on real vehicle data"** - it only works on
  EngineFaultDB-shaped lab data. This has been stated throughout the docs and
  remains true.
- **"History/trends are tracked"** - no database is implemented; nothing persists
  between requests.
- **"95%/94.7%/99.8% accuracy" (the original PDF's numbers)** - these used invalid
  metrics for their respective problems and should not be quoted anywhere going
  forward; see `phase1_results.md` for the full explanation.

---

## 8. Final status list

### VERIFIED (actually executed and checked in this validation)

- All 3 Phase 1 models load correctly from disk and produce deterministic,
  reproducible predictions.
- FastAPI ML service: all 4 prediction endpoints work correctly, including input
  validation on bad requests.
- Express backend: all 4 routes work correctly, including the full
  FastAPI -> LLM chain.
- Phase 1 -> Phase 2 data flow: the combined JSON schema is correctly assembled
  and correctly consumed by the report generator.
- Phase 2 -> dashboard data flow: `/api/vehicle/sample` and `/api/report` return
  exactly the shape `App.jsx` expects to render.
- Mock-mode LLM fallback (no API key).
- Error-fallback LLM path (invalid API key) - after the bug fix.
- Frontend builds cleanly and the dev server serves HTTP 200.
- All documented Phase 1 metrics match the raw output JSON files exactly.

### NEEDS TESTING (not yet verified, needs something from the user)

- A real, valid `ANTHROPIC_API_KEY` to confirm actual LLM-generated report quality
  (`mode: "live"` has never successfully returned a real report in this
  environment).
- The dashboard in an actual browser (visual rendering, click-through, console
  errors).
- MongoDB integration - not even written yet, needs a running instance first.

### LIMITATIONS (known, permanent unless the underlying data/architecture changes)

- Fault classification's input schema is incompatible with live OBD-II/ELM327
  data - lab-only for now.
- No real-world (in-service vehicle) fault-labeled dataset was found or used.
- Anomaly-detection and driver-behaviour metrics are validated against synthetic
  perturbations or internal cluster-separation scores, not real-world ground
  truth - because no real-world ground truth exists for this dataset.
- Driver-behaviour clustering is based on only 126 trips from a single vehicle.

### FUTURE WORK (recommended, not essential)

- LSTM-Autoencoder comparison for anomaly detection (TensorFlow 2.22 is confirmed
  installable and importable in this environment, just not yet used in the final
  model).
- A real in-service-vehicle fault-labeled dataset, to make fault classification
  live-OBD2-compatible.
- MongoDB wiring for history/trends, once an instance is available.
- Real LLM-quality evaluation once a valid API key is available.
- Manual browser testing of the dashboard.
