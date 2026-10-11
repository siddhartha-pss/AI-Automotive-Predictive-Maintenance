"""
Phase 1 Integration - combines the three trained models into one structured
vehicle-health context.

FAULT CLASSIFICATION UPDATE (see documentation/fault_classification_replacement_report.md):
The fault-classification model was originally trained on EngineFaultDB (lab-bench
exhaust-gas/dyno data, not live-OBD2-compatible). It has been REPLACED with a
model trained on edgeimpulse/obd-automotive-data - a real vehicle with a real
induced intake-air-leak fault, using ONLY standard OBD-II PIDs (RPM, accelerator
pedal position, MAF). As of this update, all three modules
(anomaly detection, fault classification, driver behaviour) use genuinely
live-OBD2-compatible input features. The fault model's scope is still limited to
a single vehicle/single fault type - see the replacement report for the full
honest limitation.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"


FAULT_MODEL_DIR = MODEL_DIR / "fault_classifier"
FAULT_LABEL_NAMES = {
    "healthy": "Healthy / No Fault Detected",
    "airleak_nox": "Probable Intake Air Leak",
}


def load_models():
    fault_metadata = json.loads((FAULT_MODEL_DIR / "metadata.json").read_text())
    return {
        "anomaly_model": joblib.load(MODEL_DIR / "anomaly_detection_model.joblib"),
        "anomaly_scaler": joblib.load(MODEL_DIR / "anomaly_detection_scaler.joblib"),
        "anomaly_features": joblib.load(MODEL_DIR / "anomaly_detection_features.joblib"),
        "fault_model": joblib.load(FAULT_MODEL_DIR / "model.joblib"),
        "fault_scaler": joblib.load(FAULT_MODEL_DIR / "scaler.joblib"),  # may be None - see metadata["uses_scaler"]
        "fault_features": joblib.load(FAULT_MODEL_DIR / "features.joblib"),
        "fault_label_encoding": joblib.load(FAULT_MODEL_DIR / "label_encoding.joblib"),
        "fault_metadata": fault_metadata,
        "behaviour_model": joblib.load(MODEL_DIR / "driver_behaviour_kmeans.joblib"),
        "behaviour_scaler": joblib.load(MODEL_DIR / "driver_behaviour_scaler.joblib"),
        "behaviour_features": joblib.load(MODEL_DIR / "driver_behaviour_features.joblib"),
        "behaviour_labels": joblib.load(MODEL_DIR / "driver_behaviour_cluster_labels.joblib"),
    }


def run_anomaly_detection(models: dict, obd_row: dict) -> dict:
    X = pd.DataFrame([obd_row])[models["anomaly_features"]]
    X_scaled = models["anomaly_scaler"].transform(X)
    pred = models["anomaly_model"].predict(X_scaled)[0]
    status = "Abnormal" if pred == -1 else "Normal"

    score = None
    if hasattr(models["anomaly_model"], "decision_function"):
        score = float(models["anomaly_model"].decision_function(X_scaled)[0])

    return {
        "status": status,
        "raw_decision_score": score,
        "method": type(models["anomaly_model"]).__name__,
        "input_compatible_with_live_obd2": True,
    }


def run_fault_classification(models: dict, obd_window_features: dict) -> dict:
    """obd_window_features: aggregated features over a short window of real OBD-II
    PID readings (RPM, pedal position, MAF) - see
    documentation/fault_classification_replacement_report.md for exactly how
    these are computed from raw PID samples."""
    X = pd.DataFrame([obd_window_features])[models["fault_features"]]
    if models["fault_scaler"] is not None:
        X_input = models["fault_scaler"].transform(X)
    else:
        X_input = X

    pred_code = int(models["fault_model"].predict(X_input)[0])
    proba = None
    confidence = None
    if hasattr(models["fault_model"], "predict_proba"):
        proba = models["fault_model"].predict_proba(X_input)[0]
        confidence = float(np.max(proba))

    code_to_label = {v: k for k, v in models["fault_label_encoding"].items()}
    predicted_fault_code = code_to_label[pred_code]
    predicted_fault = FAULT_LABEL_NAMES.get(predicted_fault_code, predicted_fault_code)

    return {
        "predicted_fault": predicted_fault,
        "predicted_fault_code": predicted_fault_code,
        "confidence": confidence,
        "method": models["fault_metadata"]["model_name"],
        "label_source": "real induced fault on a real vehicle (edgeimpulse/obd-automotive-data, BMW N53), not lab-bench or synthetic data",
        "input_compatible_with_live_obd2": True,
        "note": "Binary fault-vs-normal classifier using only standard OBD-II PIDs (RPM, "
                "accelerator pedal position, MAF). Confidence is the model's own estimated "
                "probability, not a diagnostic certainty.",
        "scope_limitation": models["fault_metadata"]["scope_limitation"],
    }


def run_driver_behaviour(models: dict, trip_features_row: dict) -> dict:
    X = pd.DataFrame([trip_features_row])[models["behaviour_features"]]
    X_scaled = models["behaviour_scaler"].transform(X)
    cluster = int(models["behaviour_model"].predict(X_scaled)[0])
    label = models["behaviour_labels"].get(cluster, f"Cluster {cluster}")

    return {
        "behaviour_profile": label,
        "cluster_id": cluster,
        "method": "KMeans (unsupervised profiling, not a predictive classifier)",
        "input_compatible_with_live_obd2": True,
    }


def build_vehicle_health_context(anomaly_result: dict, fault_result: dict,
                                  behaviour_result: dict, vehicle_meta: dict) -> dict:
    """The single structured object that will be sent to the LLM in Phase 2."""
    return {
        "vehicle_meta": vehicle_meta,
        "anomaly": anomaly_result,
        "fault": fault_result,
        "driver_behaviour": behaviour_result,
        "schema_version": "1.0",
    }


if __name__ == "__main__":
    models = load_models()

    carobd_df = pd.read_parquet(ROOT / "data" / "processed" / "carobd_combined.parquet")
    sample_obd_row = carobd_df.dropna(subset=models["anomaly_features"]).iloc[1000][models["anomaly_features"]].to_dict()
    anomaly_result = run_anomaly_detection(models, sample_obd_row)

    airleak_df = pd.read_csv(ROOT / "data" / "raw" / "obd_airleak" / "n53_airleak_MAF_NOx.csv")
    airleak_df.columns = ["time_ms", "fault_label", "rpm", "pedal", "maf", "nox"]
    window = airleak_df.iloc[100:110]  # a real 5-second window from the real induced-fault session
    sample_fault_window = {
        "rpm_mean": window["rpm"].mean(), "rpm_std": window["rpm"].std(),
        "pedal_mean": window["pedal"].mean(), "pedal_std": window["pedal"].std(),
        "maf_mean": window["maf"].mean(), "maf_std": window["maf"].std(),
        "maf_min": window["maf"].min(), "maf_max": window["maf"].max(),
        "maf_negative_rate": float((window["maf"] < 0).mean()),
    }
    fault_result = run_fault_classification(models, sample_fault_window)

    trip_profiles = pd.read_csv(ROOT / "outputs" / "phase1_driver_behaviour_trip_profiles.csv")
    sample_trip_row = trip_profiles.iloc[0][models["behaviour_features"]].to_dict()
    behaviour_result = run_driver_behaviour(models, sample_trip_row)

    context = build_vehicle_health_context(
        anomaly_result, fault_result, behaviour_result,
        vehicle_meta={"vehicle_id": "demo-vehicle-01", "source": "carOBD sample row (anomaly/behaviour) + edgeimpulse/obd-automotive-data real sample window (fault) - see docstring above"},
    )

    print(json.dumps(context, indent=2))

    out_path = ROOT / "outputs" / "sample_combined_vehicle_context.json"
    with open(out_path, "w") as f:
        json.dump(context, f, indent=2)
    print(f"\nSaved sample combined output to {out_path}")
