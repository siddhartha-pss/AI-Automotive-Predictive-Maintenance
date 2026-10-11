# Decision Note - Fault Classification Replacement

Written before touching any code, per the inspection-first requirement.

## 1. Current fault-classification implementation

- `src/fault_classification.py` - trains Logistic Regression / Random Forest /
  XGBoost on `data/raw/enginefaultdb/EngineFaultDB_Final.csv`, selects XGBoost by
  validation macro-F1, saves `models/fault_classification_{model,scaler,features}.joblib`.
- `src/combined_inference.py` - `run_fault_classification()` loads those
  artifacts and predicts on a feature row shaped like EngineFaultDB's columns.
- `ml_service/main.py` - `FaultInput` pydantic model mirrors EngineFaultDB's
  columns (MAP, TPS, Force, Power, RPM, Consumption L/H, Consumption L/100KM,
  Speed, CO, HC, CO2, O2, Lambda, AFR); `/predict/fault` and the fault branch of
  `/predict/combined` call `run_fault_classification()`.
- `backend/src/llm/providers/{gemini,anthropic}.js` and `prompt.js` - already
  provider-agnostic; the shared prompt already instructs the LLM to flag
  lab-only/non-live-compatible fault results using whatever
  `input_compatible_with_live_obd2` / `label_source` fields are present in the
  JSON it's given. **No LLM code needs to change** - only the data it receives.
- `frontend/src/App.jsx` - Fault Classification section reads
  `context.fault.predicted_fault_class`, `.confidence`, `.note`,
  `.input_compatible_with_live_obd2` generically.

## 2. Why it is not live OBD-II compatible

EngineFaultDB's 14 input features include CO, HC, CO2, O2, Lambda, AFR (exhaust
gas analyzer), and Force/Power (engine dynamometer) - none of these are produced
by a standard consumer OBD-II/ELM327 connection. Confirmed unchanged from the
original Phase 1 finding.

## 3. What needs to change

- Dataset: replace EngineFaultDB with a genuinely OBD-II-PID-only, real-fault
  dataset (see `fault_classification_replacement_report.md` for the selection).
- `src/fault_classification.py`: rewritten to train on the new dataset/features.
- `models/fault_classification_*.joblib`: regenerated from the new training run
  (old artifacts overwritten - this is an intentional, in-scope replacement, not
  accidental damage).
- `ml_service/main.py`: `FaultInput` pydantic schema updated to the new,
  OBD-II-only feature set.
- `src/combined_inference.py`: `run_fault_classification()` output fields stay
  conceptually the same shape (`predicted_fault_class`/equivalent, confidence,
  `input_compatible_with_live_obd2`, `label_source`, `note`) but
  `input_compatible_with_live_obd2` can now honestly be `true` (see the
  replacement report for the exact final verdict).
- `frontend/src/App.jsx`: no structural change needed (fields are read
  generically) - only the displayed `note`/limitation text will differ because
  the data itself differs.

## 4. What must remain untouched

- `src/anomaly_detection.py`, `src/driver_behaviour.py`, their saved model
  artifacts, and `carOBD`/`data/processed/carobd_combined.parquet` - not opened
  for editing in this task.
- `backend/src/llm/*` (prompt, provider dispatcher, gemini/anthropic/mock
  providers) - the schema they consume from `fault` is being kept
  field-compatible, so no code changes needed there.
- `backend/src/routes/*`, `backend/src/server.js` - no changes needed; they call
  the same FastAPI/LLM functions regardless of what's inside `fault`.
- `frontend` build tooling, CSS, other dashboard sections.

## Plan

1. Find and download a real, OBD-II-PID-only dataset with an actual induced
   fault vs. healthy label (not lab exhaust-gas/dyno data).
2. Inspect it fully (source, vehicle count, sample count, columns, label
   balance, leakage risk).
3. Build the honest OBD-II-compatibility table for every candidate feature.
4. Preprocess with a leakage-safe split (session/time-block level, since this is
   time-series data from very few real sessions).
5. Train and compare multiple models, select the best by macro-F1 (not raw
   accuracy, since any residual imbalance matters).
6. Save new artifacts under `models/fault_classifier/` (kept separate from the
   old `models/fault_classification_*.joblib` so the old artifacts are not
   silently deleted - see the report for whether they're removed or kept for
   comparison).
7. Update `ml_service/main.py` and `src/combined_inference.py` fault branch only.
8. Regression-test anomaly detection, driver behaviour, combined inference,
   FastAPI, Express, frontend build, and the LLM mock/Gemini paths.
9. Write `documentation/fault_classification_replacement_report.md`.
