# Phase 1 - Overall Results Summary

## Objective

Build and honestly evaluate three vehicle-data analytical modules - anomaly
detection, fault classification, and driver-behaviour analysis - on real, publicly
available data, and produce a structured combined output for Phase 2.

## Datasets

- carOBD (real OBD-II logs, Toyota Etios, 126 trips, 298,306 rows) - used for
  anomaly detection and driver behaviour.
- **edgeimpulse/obd-automotive-data** (real BMW N53, real induced intake
  air-leak vs. healthy, 2 sessions, 4,800 rows at 2 Hz) - used for fault
  classification. **Replaces** the originally-used EngineFaultDB (lab-bench
  exhaust-gas/dyno data) - see
  `documentation/fault_classification_replacement_report.md` for the full
  replacement story and `phase1_fault_classification.md` for the (superseded)
  original.

See `phase1_dataset_selection.md` for the reasoning behind the original three
dataset choices, and `fault_classification_replacement_report.md` for why fault
classification's dataset was later replaced.

## Models and results (current, as of the fault-classification replacement)

| Module | Method | Key metric | Value |
|---|---|---|---|
| Anomaly Detection | One-Class SVM (vs. Isolation Forest, LOF) | Synthetic-validation F1 | 0.500 |
| Fault Classification | Logistic Regression (vs. Random Forest, XGBoost) | Test macro-F1 (temporal holdout) | 1.000 |
| Driver Behaviour | K-Means (K=3) | Silhouette score | 0.589 |

Full detail and honest caveats for each: `phase1_anomaly_detection.md`,
`fault_classification_replacement_report.md` (current fault classifier),
`phase1_fault_classification.md` (superseded original), `phase1_driver_behaviour.md`.

## What changed from the original (PDF) results, and why

| PDF claim | What we found | Why it changed |
|---|---|---|
| LSTM, 95.08% "accuracy" for anomaly detection | One-Class SVM, 0.500 synthetic-validation F1 (no real fault labels exist, so "accuracy" was never a valid metric here) | carOBD has no fault labels; one-class methods are the technically correct family, matching the dataset's own source thesis |
| Random Forest/XGBoost, 94.69% on **synthetic injected faults** | XGBoost, 75.9% macro-F1 on **real lab-induced faults** (EngineFaultDB) | Switched to a dataset with real (if lab-induced) fault labels instead of training on our own injected anomalies - a stronger basis, honestly caveated as lab, not in-service, data |
| K-Means, "99.8% accuracy" | K-Means (K=3), 0.589 silhouette score | Accuracy is not a valid metric for unsupervised clustering with no ground truth; silhouette score is the correct replacement |

## The most important limitation of the whole Phase 1 system (UPDATED)

**This was previously the project's biggest limitation and has since been
resolved for the live-OBD2-compatibility question, with a new, smaller
limitation taking its place.** Originally, fault classification needed
exhaust-gas-analyzer and dynamometer readings a consumer OBD-II port cannot
provide. After the replacement documented in
`fault_classification_replacement_report.md`, all three modules - anomaly
detection, fault classification, and driver behaviour - now use only standard,
real OBD-II PIDs, and every combined output JSON now reports
`fault.input_compatible_with_live_obd2 = true`.

**The new limitation:** the fault classifier's training data covers only **one
real vehicle and one real fault type** (an induced intake air leak on a BMW
N53). It has not been tested on any other vehicle or fault condition. This is
a much narrower, more honest limitation than "cannot run on live OBD-II at
all" - see `fault_classification_replacement_report.md` section 21 for the
full detail.

## What's done vs. what remains

**Done:** all three models trained, evaluated with honest/appropriate metrics,
saved, and combined into one structured JSON via `src/combined_inference.py` and
the FastAPI service (`ml_service/main.py`), both verified working end-to-end.

**Remains / recommended:** an LSTM-Autoencoder comparison for anomaly detection
(TensorFlow is confirmed working in this environment, just not yet used); a
multi-vehicle real-world fault dataset to broaden the fault classifier's scope
beyond its current single-vehicle training data (see
`fault_classification_replacement_report.md`). ~~MongoDB wired up with an
actual running instance~~ - **RESOLVED**, see
`mongodb_implementation_report.md`.
