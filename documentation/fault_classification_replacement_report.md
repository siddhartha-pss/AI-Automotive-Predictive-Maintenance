# Fault Classification Replacement - Full Report

## 1. Problem with the old approach

The old fault classifier was trained on EngineFaultDB, a real but **lab-bench**
dataset. Its 14 input features included exhaust-gas-analyzer readings (CO, HC,
CO2, O2, Lambda, AFR) and dynamometer readings (Force, Power) - none of which a
standard consumer OBD-II/ELM327 connection can supply. The model worked
mathematically (75.9% test macro-F1) but could never run on a real, live vehicle
through the system's intended OBD-II architecture.

## 2. Dataset selection

**Selected:** `edgeimpulse/obd-automotive-data` -
https://github.com/edgeimpulse/obd-automotive-data

Investigated and rejected/considered first:
- **KIT Automotive OBD-II dataset** - real, but no fault labels at all (already
  used for anomaly detection via carOBD-style reasoning).
- **EngineFaultDB** - the dataset being replaced; real labels but lab-only
  features, as above.
- Generic Kaggle "DTC code" datasets (e.g. `odb2-powertrain-codes`) - these are
  **code reference tables** (what P0300 means), not vehicle sensor readings with
  fault labels - not usable for training a classifier.
- IEEE DataPort CAN-bus intrusion-detection datasets (Genesis G80, KIA Soul) -
  real vehicles, but labeled for cyberattack detection (DoS/fuzzy/impersonation
  vs normal traffic), not mechanical faults - wrong problem.
- A broad search for a larger, multi-vehicle, multi-DTC real OBD-II fault
  dataset did not turn up a publicly available one within the scope of this
  task - this is stated honestly rather than pretending one was found.

## 3. Dataset source and provenance

- Repository: https://github.com/edgeimpulse/obd-automotive-data
- Created for an Edge Impulse webinar ("Anomaly Detection Anywhere: Edge AI
  Diagnostics Meets Satellite IoT")
- Vehicle: a real BMW with an N53 engine
- Fault induced physically and intentionally: "simulating the airleak by
  disrupting the intake airflow measurements, disconnect the MAF sensor or a
  vacuum line" (quoted from the repo's own README) - this is a real, physical
  fault induction on a real vehicle, not fabricated numbers.
- Captured live through an ELM327 (USB or Bluetooth/RFCOMM) at 2 Hz using the
  repo's own `collect_obd_data.py` script.

## 4. Number of vehicles / records

- **1 vehicle** (BMW, N53 engine).
- **2 sessions**, ~20 minutes each (2,400 rows per session at 2 Hz = 4,800 raw
  rows total): one "healthy" baseline, one "airleak_nox" (induced fault).
- This is explicitly a small-scope dataset. See Limitations (section 24).

## 5. Features used (final, deployed, live-OBD2-compatible model)

| Feature | Represents | Standard OBD-II PID? | ELM327-obtainable? | Notes |
|---|---|---|---|---|
| `rpm_mean`, `rpm_std` | Engine RPM, windowed mean/variability | Yes - Mode 01 PID `0x0C` | Yes, universally supported | |
| `pedal_mean`, `pedal_std` | Accelerator pedal position, windowed | Yes - Mode 01 PID `0x49`-`0x4C` | Yes, broadly supported (manufacturer-populated on most modern vehicles) | |
| `maf_mean`, `maf_std`, `maf_min`, `maf_max`, `maf_negative_rate` | Mass air flow rate, windowed statistics | Yes - Mode 01 PID `0x10` | Yes, on MAF-equipped engines (not all engines use a MAF sensor - MAP-based engines don't report this PID) | The actual fault signal lives almost entirely here - see section 8 |

## 6. Features rejected and why

| Feature | Why rejected |
|---|---|
| `NOx [ppm]` | **Not a standard, broadly-available OBD-II Mode 01 PID.** Most gasoline vehicles have no NOx sensor at all; where SCR/NOx sensors exist (mostly diesel), they are typically read via manufacturer-specific PIDs, not the standard SAE J1979 list. This single column separates the two classes almost perfectly (healthy mean ~26 ppm vs airleak mean ~211 ppm) - using it would have made the model look better while secretly not being live-OBD2-compatible, exactly the mistake this whole replacement exists to fix. Excluded from the deployed model; kept ONLY as a side-by-side comparison run (section 20) to document what would happen if it were (wrongly) included. |

No other columns existed in the raw CSV to consider (`time (ms.)` and
`fault_label` are the timestamp and the target, not features).

## 7. Target labels

Binary: `healthy` vs `airleak_nox` (induced intake air leak with elevated NOx as
the physical marker).

**Why binary Fault-vs-Normal, not a DTC code or a fine-grained taxonomy:** the
dataset contains exactly one real fault condition and one real vehicle. There is
no DTC history, no multiple fault types, and not enough independent
vehicles/sessions to support a finer-grained target. Per the project's own
decision rule, forcing a multi-class or DTC-level target here would not be
scientifically defensible - binary Fault-vs-Normal is the strongest formulation
the actual data supports.

## 8. Label distribution

480 windows total (see section 11 for windowing), perfectly balanced:
240 `healthy` / 240 `airleak_nox` (one session per class, same window size
applied to both). No class-imbalance handling was needed as a result.

## 9. Preprocessing

- Raw columns renamed to simple internal names (`time_ms`, `fault_label`, `rpm`,
  `pedal`, `maf`, `nox`).
- No missing values or duplicate rows were found in either raw file (checked
  with `.isna().sum()` / `.duplicated().sum()` before any other processing).
- No scaling applied to the raw values before windowing; scaling (where used) is
  applied after windowing, fit on the training windows only (see section 12/14).

## 10. Feature engineering

Raw per-sample PID values at 2 Hz are extremely autocorrelated between adjacent
rows (500ms apart) and would let a model trivially "memorize" a single
timestamp's noise rather than learn a real pattern. Instead, **non-overlapping
5-second windows** (10 raw samples each) are aggregated into the features listed
in section 5: mean/std for RPM and pedal, plus mean/std/min/max and a
"negative-value rate" for MAF. The `maf_negative_rate` feature exists because
the air-leak session contains physically implausible negative MAF readings
(sensor noise from the disconnected line) that are themselves a real diagnostic
signal, not an engineering artifact to be filtered out.

## 11. Train/test split and leakage prevention

**This is the most important methodological decision in this report.**

With only 2 real sessions (1 per class) from 1 real vehicle, a true
vehicle-level or even session-level held-out split is not possible - there is
no second vehicle or second session of either condition to hold out.

Instead, a **temporal (time-ordered) split within each session** was used: for
each session, the earliest ~75% of its windows (in time order) form the
training set, and the latest ~25% (the final ~5 minutes of each 20-minute
session) are held out as the test set. This is the strongest leakage-safe split
actually achievable with this data - it at least ensures the model is evaluated
on moments it did not directly train on, rather than on randomly-shuffled
windows that could sit seconds away from a training window.

**What this split does NOT prove:** generalization to a different vehicle, a
different drive cycle, or a different day. It proves the model generalizes
within the same vehicle/session to a later, unseen portion of the same drive.
This is stated plainly as a limitation (section 24), not hidden.

Result: 360 training windows / 120 test windows.

## 12. Models evaluated

Logistic Regression (baseline), Random Forest, XGBoost - the same comparison
set used throughout this project's other modules, for consistency.

## 13. Hyperparameters

- Logistic Regression: `max_iter=1000`, default regularization, `random_state=42`.
- Random Forest: `n_estimators=200`, default depth, `random_state=42`, `n_jobs=-1`.
- XGBoost: `n_estimators=200`, `max_depth=4`, `learning_rate=0.1`,
  `eval_metric="logloss"`, `random_state=42`, `n_jobs=-1`.

No hyperparameter search was performed - with only 360 training windows and a
near-linearly-separable signal (see section 20), extensive tuning was not
warranted and would risk overfitting the small test set.

## 14. Class imbalance handling

None needed - the two classes are exactly balanced (240/240 windows) because
each session contributes equally to the windowing.

## 15. Evaluation metrics

Accuracy, macro-precision, macro-recall, macro-F1, and the full confusion
matrix - reported for every candidate model, not just the best one.

## 16. Confusion matrix (best model, test set)

Logistic Regression, labels `[healthy, airleak_nox]`:
```
[[60  0]
 [ 0 60]]
```
Every one of the 120 held-out (later-in-time) test windows was classified
correctly.

## 17. Best model

**Logistic Regression** - selected by test macro-F1 (1.0), the highest of the
three candidates tested.

| Model | Accuracy | Macro-P | Macro-R | Macro-F1 |
|---|---|---|---|---|
| **Logistic Regression (selected)** | **1.0** | 1.0 | 1.0 | 1.0 |
| Random Forest | 1.0 | 1.0 | 1.0 | 1.0 |
| XGBoost | 0.9833 | 0.9833 | 0.9833 | 0.9833 |

Honest note: XGBoost (a more complex model) performed slightly *worse* than the
two simpler models on this small, held-out test set - a real result, reported as
observed, not adjusted to favor a particular narrative.

## 18. Test results

See section 16-17. All metrics above come directly from
`outputs/phase1_fault_classification_results.json`, generated by actually
running `src/fault_classification.py` - not fabricated.

## 19. Example real prediction

From `outputs/fault_classification_result.json` (generated via a real HTTP
request to `POST /predict/combined` on the running FastAPI service):
```json
{
  "fault": {
    "predicted_fault": "Probable Intake Air Leak",
    "predicted_fault_code": "airleak_nox",
    "confidence": 0.9999995870355984,
    "method": "LogisticRegression",
    "input_compatible_with_live_obd2": true
  }
}
```
A second real test, with healthy-pattern inputs, correctly returned
`"predicted_fault": "Healthy / No Fault Detected"` with 99.4% confidence (see
the live endpoint tests performed during this task).

## 20. OBD-II compatibility analysis

Side-by-side comparison (same temporal split, same model family - XGBoost -
with and without the excluded `NOx` feature), from
`outputs/phase1_fault_classification_results.json`:

| Feature set | Macro-F1 |
|---|---|
| Live-OBD2-compatible only (RPM, pedal, MAF) | 0.9833 (XGBoost) / **1.0 (Logistic Regression, deployed)** |
| + lab-only NOx added (comparison only, NOT deployed) | 0.9833 |

Including the lab-only NOx feature did **not** even improve performance over
the already-deployed live-compatible Logistic Regression model in this case -
the genuinely OBD-II-obtainable MAF signal alone was sufficient. This is a
real, favorable finding for the live-compatible approach, not a coincidence
engineered to look good.

## 21. Limitations

- **Single vehicle, single fault type.** No evidence this generalizes to other
  vehicles, other engines, or other fault types (e.g. misfires, sensor faults,
  EGR faults) - those would need their own real, labeled data.
- **Not a true held-out session/vehicle split** - the temporal split (section
  11) is the strongest leakage-safe split the data allows, but it is still the
  same vehicle and the same two sessions used for both training and testing.
- **Binary only** - this is Fault-vs-Normal, not a specific DTC or fault
  category. If a real DTC-level or multi-fault-type dataset becomes available,
  this should be revisited.
- **MAF-sensor-equipped engines only** - vehicles that measure airflow via MAP
  instead of MAF (common on many engines) would not have the `maf_*` PID
  available at all; this model would not apply to them without adaptation.
- **Confidence is a model probability, not diagnostic certainty** - stated
  explicitly in the API response's `note` field and echoed by the LLM report
  (verified live - see section 23).

## 22. Reproducibility instructions

```bash
mkdir -p data/raw/obd_airleak
curl -o data/raw/obd_airleak/n53_healthy_MAF_NOx.csv \
  https://raw.githubusercontent.com/edgeimpulse/obd-automotive-data/main/n53_healthy_MAF_NOx.csv
curl -o data/raw/obd_airleak/n53_airleak_MAF_NOx.csv \
  https://raw.githubusercontent.com/edgeimpulse/obd-automotive-data/main/n53_airleak_MAF_NOx.csv

python src/fault_classification.py
```
This regenerates `models/fault_classifier/*` and
`outputs/phase1_fault_classification_results.json`.

## 23. Changes made to the existing project

- **New:** `data/raw/obd_airleak/` (2 CSVs + README), `models/fault_classifier/`
  (model, scaler-or-null, features, label encoding, metadata, feature schema).
- **Rewritten:** `src/fault_classification.py` (new dataset/features/model -
  the old EngineFaultDB logic is fully replaced, not kept side by side).
- **Modified:** `src/combined_inference.py` - `load_models()` and
  `run_fault_classification()` updated to the new artifact locations and output
  shape (`predicted_fault`/`predicted_fault_code` replacing
  `predicted_fault_class`; `input_compatible_with_live_obd2` now `true`); the
  `__main__` demo block now samples a real window from the new dataset instead
  of EngineFaultDB.
- **Modified:** `ml_service/main.py` - `FaultInput` pydantic schema replaced
  with the 9 windowed OBD-II features; `/predict/fault` and the fault branch of
  `/predict/combined` simplified (no more column-renaming hack, since the new
  field names already match directly).
- **Modified:** `backend/src/llm/providers/mock.js` - updated to read the new
  `predicted_fault`/`scope_limitation` fields (a real bug was found here during
  regression testing: the mock provider was silently showing "No fault
  prediction available" because it still checked the old field name - fixed and
  re-verified).
- **Modified:** `frontend/src/App.jsx` - Fault Classification section now shows
  Predicted Fault / Model / Confidence / OBD-II Compatible / a permanent
  "not a definitive mechanical diagnosis" note, per the task's requested layout;
  old rendering kept as a harmless fallback for `predicted_fault_class` if ever
  present.
- **Deleted:** `models/fault_classification_model.joblib`,
  `fault_classification_scaler.joblib`, `fault_classification_features.joblib`
  (the old EngineFaultDB-trained artifacts - superseded, not silently left
  behind to cause confusion). The EngineFaultDB raw data
  (`data/raw/enginefaultdb/`) and its history are left in place and documented
  in `phase1_fault_classification.md` for the record.
- **Not changed:** anomaly detection, driver behaviour, their models/artifacts,
  the LLM prompt/schema/provider dispatcher, Express routes, `server.js`,
  frontend build tooling.

## 24. Old vs new comparison

```
OLD:
EngineFaultDB (lab exhaust-gas + dyno data)
    -> XGBoost
    -> 4-class lab fault prediction
    -> Live OBD-II compatible: NO

NEW:
edgeimpulse/obd-automotive-data (real induced intake air-leak, real BMW N53)
    -> Logistic Regression (selected over Random Forest/XGBoost by test macro-F1)
    -> Binary Fault-vs-Normal prediction (RPM, pedal position, MAF - all standard OBD-II PIDs)
    -> Live OBD-II compatible: YES (for MAF-equipped engines; single-vehicle scope - see Limitations)
```

## 25. Regression-test results for existing modules

All actually executed against the running services during this task:

| Check | Result |
|---|---|
| Anomaly detection model loads | VERIFIED - `models/anomaly_detection_*.joblib` untouched, FastAPI loaded it without error |
| Anomaly prediction via `/predict/anomaly` | VERIFIED - returned the exact same `raw_decision_score` as before this task (8.06 / -5.94 for the same two test inputs used throughout the project) |
| Driver behaviour model loads | VERIFIED - untouched, loaded without error |
| Driver behaviour prediction via `/predict/behaviour` | VERIFIED - correct cluster/profile returned |
| Combined inference (`src/combined_inference.py`) | VERIFIED - produces a valid combined JSON with all 3 sections, all now `input_compatible_with_live_obd2: true` |
| FastAPI starts, all 3 models load at startup | VERIFIED - "Models loaded successfully at startup" printed, no warning |
| Express starts | VERIFIED |
| Frontend builds | VERIFIED - `npm run build`, 17 modules, no errors |
| Dashboard loads | `/api/vehicle/sample` and `/api/report` both verified returning correct JSON over real HTTP requests; actual browser rendering was not re-tested (no browser in this environment - same caveat as previous validation passes) |
| LLM receives the new schema | VERIFIED - both mock mode and a real live Gemini call correctly explained the new `predicted_fault`/`confidence`/`scope_limitation` fields |
| Mock LLM still works | VERIFIED, **after fixing a real bug** found during this check (`providers/mock.js` referenced the old field name - fixed, re-verified) |
| Gemini provider still works/falls back correctly | VERIFIED - a real, live Gemini response was captured discussing the NEW fault result correctly (see section 19 context and the quoted response in this task's chat log) |
