# Final System Architecture

## Conceptual vehicle data flow

```
Vehicle sensors
-> ECU
-> OBD-II port
-> ELM327 (translator, real-vehicle future step - not used yet, see below)
-> PID requests/responses
-> Vehicle parameters (RPM, speed, coolant temp, throttle, MAP, ...)
-> Our data-processing / ML system
-> Vehicle-health analysis
-> Dashboard
```

**Current implementation uses datasets, not a live vehicle.** The anomaly-detection
and driver-behaviour feature schema matches real OBD-II PIDs exactly, so a real
ELM327 feed could replace the dataset CSVs without changing those two models. Fault
classification currently needs lab-grade inputs a live OBD-II connection can't
supply (see `phase1_results.md`) - that module is not yet real-vehicle-ready.

## System architecture (implemented and verified)

```
React frontend (Vite, :5173)
-> Node/Express backend (:5000)
     -> FastAPI ML service (:8000)
          -> anomaly_detection_model.joblib (One-Class SVM)
          -> fault_classification_model.joblib (XGBoost)
          -> driver_behaviour_kmeans.joblib (K-Means)
     -> Anthropic API (Claude Haiku 4.5) or mock fallback
-> MongoDB (RESOLVED - now implemented and tested; see documentation/mongodb_implementation_report.md)
```

> Note: this diagram's FastAPI model list (XGBoost fault classifier) and the
> Anthropic-only LLM line predate later changes - see
> `fault_classification_replacement_report.md` and
> `llm_provider_integration_report.md` for what actually runs today. Only the
> MongoDB line is updated here, per the scope of the MongoDB implementation task.

## Data flow through the system

```
Raw sensor-style input (JSON)
-> POST /api/analyze (Express)
-> POST /predict/combined (FastAPI)
-> combined vehicle-health context JSON
   {vehicle_meta, anomaly, fault, driver_behaviour, schema_version}
-> LLM report generator
-> {vehicle_context, llm_report}
-> React dashboard renders both
```

## Why this architecture

- ML stays entirely in Python (FastAPI service) - no model logic duplicated in
  JavaScript.
- Express is a thin orchestrator, not a second ML layer - keeps the system
  understandable for an 8-credit project, per the master prompt's "don't
  over-engineer" instruction.
- The LLM call lives in the Node backend (not the frontend), so the API key never
  reaches the browser.

## Honest gaps (do not present these as solved)

1. ~~Fault classification's input schema does not match live OBD-II~~ -
   **RESOLVED**, see `fault_classification_replacement_report.md`.
2. ~~MongoDB has no running instance~~ - **RESOLVED**, a real MongoDB instance
   was connected, saved to, and queried from in this environment - see
   `mongodb_implementation_report.md`.
3. The frontend was verified to build and serve correctly, but not visually tested
   in an actual browser (no browser available in this environment) - still true.
4. No real vehicle/ELM327 hardware was used anywhere - everything runs on real
   public datasets described in `phase1_dataset_selection.md` and
   `fault_classification_replacement_report.md` - still true.
