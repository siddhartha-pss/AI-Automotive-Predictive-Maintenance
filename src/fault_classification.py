"""
Phase 1 - Fault Classification (REPLACED - see
documentation/fault_classification_replacement_report.md for the full story).

OLD approach (kept only as history in the decision log, no longer used): trained
on EngineFaultDB, a real but LAB-BENCH dataset requiring exhaust-gas-analyzer and
dynamometer inputs (CO, HC, CO2, O2, Lambda, AFR, Force, Power) that a standard
consumer OBD-II/ELM327 connection cannot supply.

NEW approach: trained on a real, genuinely OBD-II-PID-only dataset - a real BMW
(N53 engine) with an actually induced intake air-leak fault vs. a healthy
baseline, captured live through an ELM327 at 2 Hz.
Source: https://github.com/edgeimpulse/obd-automotive-data (MIT-style license,
see its LICENSE file) - README confirms the fault was physically induced by
disconnecting the MAF sensor/a vacuum line on a real vehicle, not simulated
numbers.

HONEST SCOPE: this is ONE vehicle, ONE healthy session and ONE fault session
(2400 rows / 20 minutes each at 2 Hz). This is NOT enough data to claim
cross-vehicle generalization - see the replacement report's Limitations section.
This is a binary Fault-vs-Normal formulation (not exact DTC prediction), chosen
because the dataset does not contain multiple DTCs or multiple vehicles, and
forcing a finer-grained target would not be scientifically defensible.

OBD-II COMPATIBILITY DECISION: the raw CSV also contains a "NOx [ppm]" column,
which separates the two classes almost perfectly (healthy ~26ppm vs airleak
~211ppm). NOx is NOT a standard, broadly-supported OBD-II Mode 01 PID on
consumer vehicles/ELM327 setups (most gasoline vehicles have no NOx sensor at
all, and where one exists it is typically manufacturer-specific / not in the
standard SAE J1979 PID list). Using it would make the model look better while
secretly not being live-OBD2-compatible - exactly the mistake this replacement
is meant to fix. NOx is therefore EXCLUDED from the deployed model and only used
in a side-by-side comparison run for documentation (see OUTPUT below).

Live-compatible features used in the final model: RPM, accelerator PEDAL INPUT,
and MAF (all standard, widely-supported OBD-II Mode 01 PIDs: 0x0C, 0x49-0x4C,
0x10). See the OBD-II compatibility table in the replacement report for the
per-feature justification.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    f1_score, precision_score, recall_score,
)
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "obd_airleak"
MODEL_DIR = ROOT / "models" / "fault_classifier"
OUTPUT_PATH = ROOT / "outputs" / "phase1_fault_classification_results.json"

RANDOM_STATE = 42
WINDOW_SIZE = 10  # 10 samples * 500ms = 5-second windows
TEST_FRACTION = 0.25  # held out from the END of each session's timeline (temporal split, not random)

LIVE_COMPATIBLE_FEATURES = [
    "rpm_mean", "rpm_std",
    "pedal_mean", "pedal_std",
    "maf_mean", "maf_std", "maf_min", "maf_max", "maf_negative_rate",
]
# Included ONLY for the side-by-side "what if we cheated with a lab-only signal"
# comparison documented in the replacement report - never used in the deployed model.
NOX_COMPARISON_FEATURE = "nox_mean"


def load_sessions() -> pd.DataFrame:
    healthy = pd.read_csv(RAW_DIR / "n53_healthy_MAF_NOx.csv")
    airleak = pd.read_csv(RAW_DIR / "n53_airleak_MAF_NOx.csv")
    healthy.columns = ["time_ms", "fault_label", "rpm", "pedal", "maf", "nox"]
    airleak.columns = ["time_ms", "fault_label", "rpm", "pedal", "maf", "nox"]
    healthy["session"] = "healthy"
    airleak["session"] = "airleak_nox"
    return pd.concat([healthy, airleak], ignore_index=True)


def make_windows(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for session, g in df.groupby("session"):
        g = g.sort_values("time_ms").reset_index(drop=True)
        n_windows = len(g) // WINDOW_SIZE
        for i in range(n_windows):
            w = g.iloc[i * WINDOW_SIZE:(i + 1) * WINDOW_SIZE]
            rows.append({
                "session": session,
                "window_index": i,  # preserves time order within the session
                "fault_label": w["fault_label"].iloc[0],
                "rpm_mean": w["rpm"].mean(), "rpm_std": w["rpm"].std(),
                "pedal_mean": w["pedal"].mean(), "pedal_std": w["pedal"].std(),
                "maf_mean": w["maf"].mean(), "maf_std": w["maf"].std(),
                "maf_min": w["maf"].min(), "maf_max": w["maf"].max(),
                "maf_negative_rate": float((w["maf"] < 0).mean()),
                "nox_mean": w["nox"].mean(),
            })
    return pd.DataFrame(rows).fillna(0)


def temporal_split(windows: pd.DataFrame):
    """Splits each session's windows in TIME ORDER - train on the earlier part of
    the drive cycle, test on the later part. This is NOT a vehicle-level split
    (only one vehicle exists in this dataset) - it is the strongest leakage-safe
    split actually possible with this data, and is documented as a limitation."""
    train_parts, test_parts = [], []
    for session, g in windows.groupby("session"):
        g = g.sort_values("window_index")
        n_test = max(1, int(len(g) * TEST_FRACTION))
        train_parts.append(g.iloc[:-n_test])
        test_parts.append(g.iloc[-n_test:])
    return pd.concat(train_parts, ignore_index=True), pd.concat(test_parts, ignore_index=True)


def evaluate(y_true, y_pred) -> dict:
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_precision": round(precision_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "macro_recall": round(recall_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
    }


def main():
    raw = load_sessions()
    print(f"Raw rows: {len(raw)} (2 sessions, {WINDOW_SIZE * 1} samples = {WINDOW_SIZE * 0.5}s per window)")

    windows = make_windows(raw)
    print(f"Windows built: {len(windows)} ({windows['fault_label'].value_counts().to_dict()})")

    train_df, test_df = temporal_split(windows)
    print(f"Train windows: {len(train_df)} | Test windows (later-in-time, held out): {len(test_df)}")

    label_map = {"healthy": 0, "airleak_nox": 1}
    y_train = train_df["fault_label"].map(label_map)
    y_test = test_df["fault_label"].map(label_map)

    # --- Live-OBD2-compatible model (the one actually deployed) ---
    X_train = train_df[LIVE_COMPATIBLE_FEATURES]
    X_test = test_df[LIVE_COMPATIBLE_FEATURES]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            random_state=RANDOM_STATE, eval_metric="logloss", n_jobs=-1,
        ),
    }

    results = []
    fitted = {}
    for name, model in candidates.items():
        if name == "LogisticRegression":
            model.fit(X_train_s, y_train)
            pred = model.predict(X_test_s)
        else:
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
        fitted[name] = model
        metrics = evaluate(y_test, pred)
        print(f"{name}: {metrics}")
        results.append({"model": name, "test_metrics": metrics})

    best_name = max(results, key=lambda r: r["test_metrics"]["macro_f1"])["model"]
    best_model = fitted[best_name]
    best_pred = best_model.predict(X_test_s if best_name == "LogisticRegression" else X_test)
    cm = confusion_matrix(y_test, best_pred, labels=[0, 1]).tolist()
    report = classification_report(y_test, best_pred, output_dict=True)
    print(f"\nBest live-compatible model: {best_name}")
    print("Confusion matrix (rows=true, cols=pred, order=[healthy, airleak_nox]):")
    print(np.array(cm))

    # --- Side-by-side comparison ONLY: same split, same model type, WITH the
    # lab-only NOx feature added - to honestly show how much "free" separability
    # that feature would add if we (incorrectly) used it. NOT saved as a deployable model. ---
    X_train_nox = train_df[LIVE_COMPATIBLE_FEATURES + [NOX_COMPARISON_FEATURE]]
    X_test_nox = test_df[LIVE_COMPATIBLE_FEATURES + [NOX_COMPARISON_FEATURE]]
    nox_model = xgb.XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.1,
                                   random_state=RANDOM_STATE, eval_metric="logloss", n_jobs=-1)
    nox_model.fit(X_train_nox, y_train)
    nox_pred = nox_model.predict(X_test_nox)
    nox_metrics = evaluate(y_test, nox_pred)
    print(f"\n[comparison only, NOT deployed] XGBoost WITH lab-only NOx feature: {nox_metrics}")

    # --- Save the deployed artifacts ---
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_DIR / "model.joblib")
    joblib.dump(scaler if best_name == "LogisticRegression" else None, MODEL_DIR / "scaler.joblib")
    joblib.dump(LIVE_COMPATIBLE_FEATURES, MODEL_DIR / "features.joblib")
    label_encoding = {"healthy": 0, "airleak_nox": 1}
    joblib.dump(label_encoding, MODEL_DIR / "label_encoding.joblib")

    metadata = {
        "model_name": best_name,
        "uses_scaler": best_name == "LogisticRegression",
        "features": LIVE_COMPATIBLE_FEATURES,
        "label_encoding": label_encoding,
        "window_size_samples": WINDOW_SIZE,
        "window_seconds": WINDOW_SIZE * 0.5,
        "trained_on": "edgeimpulse/obd-automotive-data (real BMW N53, induced intake air-leak vs healthy)",
        "input_compatible_with_live_obd2": True,
        "scope_limitation": "Single vehicle, single healthy/fault session pair. No cross-vehicle or cross-session generalization has been tested.",
    }
    with open(MODEL_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    with open(MODEL_DIR / "feature_schema.json", "w") as f:
        json.dump({"features": LIVE_COMPATIBLE_FEATURES}, f, indent=2)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({
            "dataset": "edgeimpulse/obd-automotive-data - real BMW (N53 engine), real induced intake air-leak vs healthy, captured live via ELM327 at 2 Hz",
            "label_source": "real induced fault (physically disconnected MAF sensor/vacuum line on a real vehicle), not synthetic or lab-bench data",
            "formulation": "binary Fault-vs-Normal (airleak_nox vs healthy) - chosen because this dataset has only one fault condition and one vehicle; exact DTC prediction is not supported by the available data",
            "windowing": f"{WINDOW_SIZE} samples ({WINDOW_SIZE*0.5}s) per window, non-overlapping",
            "split_strategy": "temporal (time-ordered) holdout per session - train on the earlier part of each session's timeline, test on the later part. NOT a vehicle-level split (only one vehicle exists in this dataset).",
            "train_windows": len(train_df), "test_windows": len(test_df),
            "live_compatible_features": LIVE_COMPATIBLE_FEATURES,
            "excluded_feature": {
                "name": "NOx [ppm]",
                "reason": "Not a standard, broadly-available OBD-II Mode 01 PID on consumer vehicles - would make the model look better while secretly not being live-OBD2-compatible.",
                "comparison_only_metrics_with_nox": nox_metrics,
            },
            "model_comparison": results,
            "selected_model": best_name,
            "final_test_metrics": evaluate(y_test, best_pred),
            "confusion_matrix": {"labels": ["healthy", "airleak_nox"], "matrix": cm},
            "per_class_report": report,
            "input_compatible_with_live_obd2": True,
            "scope_limitation": metadata["scope_limitation"],
        }, f, indent=2)

    print(f"\nSaved model artifacts to {MODEL_DIR}")
    print(f"Saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
