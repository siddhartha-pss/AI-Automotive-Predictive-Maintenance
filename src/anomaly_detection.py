"""
Phase 1 - Anomaly Detection on the carOBD dataset.

DECISION (documented, see documentation/phase1_anomaly_detection.md for full reasoning):
This dataset (eron93br/carOBD) contains ONLY real driving data with NO fault/anomaly
labels - every row is an unlabeled real OBD-II reading. That makes this an unsupervised
/ one-class problem, not a classification problem. This matches the dataset's own
source thesis ("Detecting Anomalies in the Engine Coolant Sensor Using One-Class
Classifiers"), so we follow the same family of approach rather than assuming LSTM
is required.

We compare three one-class/unsupervised methods:
  - Isolation Forest
  - One-Class SVM (trained on a subsample - O(n^2) does not scale to 298k rows)
  - Local Outlier Factor (novelty mode)

VALIDATION STRATEGY (important - read this):
Because there is no ground truth for "this reading is a real fault", we cannot compute
a true precision/recall against real anomalies. Instead we do two things, and we are
explicit that these are different claims:
  1. Report the anomaly rate each model assigns to real, untouched data (sanity check -
     should be low and roughly matching the chosen contamination assumption).
  2. Build a SEPARATE synthetic validation set by injecting obvious, clearly-abnormal
     perturbations (coolant spike, RPM dropout, MAP instability) into held-out normal
     data. This is used ONLY to verify a model can catch extreme deviations - it is
     NOT training data, and passing this test does NOT prove the model would catch a
     real, subtle fault. This distinction matters and must be kept in the report.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "carobd_combined.parquet"
MODEL_DIR = ROOT / "models"
OUTPUT_PATH = ROOT / "outputs" / "phase1_anomaly_detection_results.json"

FEATURES = [
    "ENGINE_RPM",
    "VEHICLE_SPEED",
    "THROTTLE",
    "ENGINE_LOAD",
    "COOLANT_TEMPERATURE",
    "LONG_TERM_FUEL_TRIM_BANK_1",
    "SHORT_TERM_FUEL_TRIM_BANK_1",
    "INTAKE_MANIFOLD_PRESSURE",
    "INTAKE_AIR_TEMP",
    "TIMING_ADVANCE",
    "CONTROL_MODULE_VOLTAGE",
]

RANDOM_STATE = 42


def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df = df.dropna(subset=FEATURES)
    return df


def trip_level_split(df: pd.DataFrame, test_fraction: float = 0.2):
    trips = df["trip_id"].unique()
    rng = np.random.default_rng(RANDOM_STATE)
    rng.shuffle(trips)
    n_test = max(1, int(len(trips) * test_fraction))
    test_trips = set(trips[:n_test])
    train_df = df[~df["trip_id"].isin(test_trips)].copy()
    test_df = df[df["trip_id"].isin(test_trips)].copy()
    return train_df, test_df


def inject_synthetic_anomalies(df: pd.DataFrame, fraction: float = 0.05) -> pd.DataFrame:
    """Creates a labeled validation set by perturbing a copy of real held-out data.
    Used ONLY for validation, never for training. Labeled rows get is_synthetic_anomaly=1.
    """
    df = df.copy()
    df["is_synthetic_anomaly"] = 0
    n = len(df)
    n_anomalies = int(n * fraction)
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(df.index, size=n_anomalies, replace=False)

    thirds = np.array_split(idx, 3)

    # Coolant overheat spike
    df.loc[thirds[0], "COOLANT_TEMPERATURE"] = df.loc[thirds[0], "COOLANT_TEMPERATURE"] + rng.uniform(40, 70, len(thirds[0]))
    # RPM dropout / misfire-like behaviour
    df.loc[thirds[1], "ENGINE_RPM"] = df.loc[thirds[1], "ENGINE_RPM"] * rng.uniform(0.1, 0.3, len(thirds[1]))
    # MAP instability
    df.loc[thirds[2], "INTAKE_MANIFOLD_PRESSURE"] = df.loc[thirds[2], "INTAKE_MANIFOLD_PRESSURE"] * rng.uniform(2.0, 3.5, len(thirds[2]))

    df.loc[idx, "is_synthetic_anomaly"] = 1
    return df


def evaluate_on_synthetic(model, scaler, val_df: pd.DataFrame, model_name: str) -> dict:
    X_val = scaler.transform(val_df[FEATURES])
    preds = model.predict(X_val)  # 1 = normal, -1 = anomaly (sklearn convention)
    pred_anomaly = (preds == -1).astype(int)
    true_anomaly = val_df["is_synthetic_anomaly"].values

    tp = int(((pred_anomaly == 1) & (true_anomaly == 1)).sum())
    fp = int(((pred_anomaly == 1) & (true_anomaly == 0)).sum())
    fn = int(((pred_anomaly == 0) & (true_anomaly == 1)).sum())
    tn = int(((pred_anomaly == 0) & (true_anomaly == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "model": model_name,
        "synthetic_validation": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        },
    }


def main():
    print("Loading data...")
    df = load_data()
    print(f"Usable rows after dropping NA in feature columns: {len(df)}")

    train_df, test_df = trip_level_split(df)
    print(f"Train rows: {len(train_df)} | Test (held-out) rows: {len(test_df)}")

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_df[FEATURES])

    # Subsample for One-Class SVM (does not scale to 298k rows)
    ocsvm_sample_size = min(10000, len(X_train))
    rng = np.random.default_rng(RANDOM_STATE)
    ocsvm_idx = rng.choice(len(X_train), size=ocsvm_sample_size, replace=False)
    X_train_sample = X_train[ocsvm_idx]

    models = {
        "IsolationForest": IsolationForest(contamination=0.03, random_state=RANDOM_STATE, n_estimators=200),
        "OneClassSVM": OneClassSVM(kernel="rbf", nu=0.03, gamma="scale"),
        "LocalOutlierFactor": LocalOutlierFactor(n_neighbors=35, novelty=True, contamination=0.03),
    }

    synthetic_val = inject_synthetic_anomalies(test_df, fraction=0.05)

    results = []
    fitted_models = {}
    for name, model in models.items():
        print(f"Training {name}...")
        if name == "OneClassSVM":
            model.fit(X_train_sample)
        else:
            model.fit(X_train)
        fitted_models[name] = model

        real_test_preds = model.predict(scaler.transform(test_df[FEATURES]))
        real_anomaly_rate = float((real_test_preds == -1).mean())

        metrics = evaluate_on_synthetic(model, scaler, synthetic_val, name)
        metrics["real_data_anomaly_rate"] = round(real_anomaly_rate, 4)
        results.append(metrics)
        print(f"  {name}: synthetic F1={metrics['synthetic_validation']['f1']}, "
              f"real anomaly rate={real_anomaly_rate:.4f}")

    best = max(results, key=lambda r: r["synthetic_validation"]["f1"])
    print(f"\nBest model by synthetic-validation F1: {best['model']}")

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(fitted_models[best["model"]], MODEL_DIR / "anomaly_detection_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "anomaly_detection_scaler.joblib")
    joblib.dump(FEATURES, MODEL_DIR / "anomaly_detection_features.joblib")

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({
            "dataset": "carOBD (eron93br/carOBD) - real Toyota Etios OBD-II logs",
            "approach": "unsupervised one-class anomaly detection (no real fault labels exist in this dataset)",
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "results": results,
            "selected_model": best["model"],
            "note": "synthetic_validation metrics come from injected perturbations used ONLY "
                    "for validation, not training. They show the model can catch extreme "
                    "deviations; they do not prove real-world fault detection accuracy.",
        }, f, indent=2)

    print(f"\nSaved model to {MODEL_DIR / 'anomaly_detection_model.joblib'}")
    print(f"Saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
