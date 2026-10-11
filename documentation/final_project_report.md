# Final Project Report (Unofficial, Working Draft)

## 1. Objective

Use real vehicle OBD-II/engine data and ML to detect abnormal vehicle behaviour,
classify probable faults, and profile driving behaviour, then use an LLM to explain
these results in plain language on a web dashboard - moving maintenance from
reactive to predictive.

## 2. Datasets selected

- carOBD (real Toyota Etios OBD-II logs, 126 trips, 298K rows) - anomaly detection
  + driver behaviour.
- EngineFaultDB (real lab-induced engine fault data, 55,999 rows, 4 classes) -
  fault classification.

Full reasoning: `phase1_dataset_selection.md`.

## 3. Preprocessing

carOBD: 126 CSV files concatenated, columns cleaned, values coerced to numeric
(source files had leading-space string artifacts), driving mode tagged from
filename, missing-value and duplicate-row report generated (not silently dropped).
EngineFaultDB: 1 duplicate row dropped, otherwise clean (no missing values).

## 4. Models tested and selected

| Module | Models compared | Selected | Key metric |
|---|---|---|---|
| Anomaly Detection | Isolation Forest, One-Class SVM, Local Outlier Factor | One-Class SVM | Synthetic-validation F1 = 0.500 |
| Fault Classification | Logistic Regression, Random Forest, XGBoost | XGBoost | Test macro-F1 = 0.759 |
| Driver Behaviour | K-Means, K=2..5 | K=3 | Silhouette = 0.589 |

Full detail per module: `phase1_anomaly_detection.md`, `phase1_fault_classification.md`,
`phase1_driver_behaviour.md`.

## 5. Why these results differ from the original PDF

The PDF reported 95%/94.7%/99.8% "accuracy" across the three modules. Those numbers
used metrics that don't actually fit the underlying problems (accuracy on
unlabeled/unsupervised tasks, and training/testing fault classification on
synthetic injected labels). This report replaces them with metrics that are
actually valid for each task, and a real (if lab-induced) fault dataset instead of
synthetic injection. See `phase1_results.md` for the full before/after table.

## 6. Inputs and outputs

Each model takes real sensor-style numeric features and outputs either a
status/class + confidence (anomaly, fault) or a cluster/profile label (driver
behaviour). All three are combined into one JSON
(`src/combined_inference.py` / `ml_service/main.py` -> `/predict/combined`), which
is what gets sent to the LLM.

## 7. Phase 2 - LLM

Claude Haiku 4.5, called from the Node/Express backend, with a verified-working
mock fallback for when no API key is present. Full reasoning and verified test
results: `phase2_llm_integration.md`.

## 8. Phase 3 - Backend and frontend

FastAPI ML service (Python, owns all model inference) + Node/Express (orchestrator)
+ React dashboard (Vite). All three were started and independently tested against
real HTTP requests in this environment; see `phase3_backend.md` and
`phase3_frontend.md` for exactly what was and wasn't verified (the frontend's
compiled/served correctly but was not visually tested in an actual browser - no
browser available here).

## 9. Files created

See the repository tree - key ones: `src/*.py` (Phase 1 pipelines),
`ml_service/main.py` (FastAPI), `backend/src/*` (Express + LLM),
`frontend/src/App.jsx` (dashboard), `models/*.joblib` (trained models),
`outputs/*.json` (results + sample combined context), `documentation/*.md` (this
report and its companions).

## 10. What's complete

All of Phase 1 (three modules, trained, evaluated, saved). Phase 2 fully working in
mock mode (real-LLM mode untested - no API key available here). Phase 3 backend and
ML service fully working and verified; frontend code-complete and build-verified
but not browser-tested.

> **Update:** this report predates several later changes - the fault classifier,
> LLM provider architecture, and MongoDB persistence were all since
> implemented/replaced. See `fault_classification_replacement_report.md`,
> `llm_provider_integration_report.md`, and `mongodb_implementation_report.md`
> for the current state. MongoDB specifically is **no longer "not implemented"**
> - it was connected and tested for real.

## 11. What remains

1. A real `ANTHROPIC_API_KEY` to verify the live LLM path (the one genuinely
   unavoidable external requirement).
2. A running MongoDB instance (local, Docker, or Atlas) to implement and test
   history storage.
3. Open the dashboard in an actual browser to confirm the UI renders and behaves
   as the code intends.
4. (Recommended, not essential) an LSTM-Autoencoder anomaly-detection comparison,
   now that TensorFlow is confirmed working in this environment.
5. (Recommended, not essential) a real in-service-vehicle fault-labeled dataset, to
   close the gap documented in `phase1_results.md` between fault classification's
   lab-only input requirements and the live-OBD2-compatible other two modules.
