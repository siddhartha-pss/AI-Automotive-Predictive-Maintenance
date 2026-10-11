"""
Phase 1 - Driver Behaviour Analysis on the carOBD dataset.

This is explicitly FEATURE ENGINEERING + UNSUPERVISED CLUSTERING, not a trained
predictive model in the same sense as anomaly detection or fault classification.
There is no ground-truth "driving style" label anywhere in this dataset, so there is
nothing to predict against - we are grouping real trips by engineered behavioural
statistics. Accuracy is NOT a valid metric here (no labels exist to be "accurate"
against); we use silhouette score instead, which measures how well-separated the
discovered clusters are.

Per-trip features (one row per real trip, 126 trips total):
  - speed: mean, std, max
  - acceleration (derived from the 1 Hz speed series): mean abs, max, harsh-accel
    event rate, harsh-brake event rate (threshold-based)
  - RPM: mean, std
  - throttle: mean, std (aggressiveness proxy)
  - engine load: mean

We try K=2..5 with K-Means, select K by silhouette score, and label clusters
Low/Moderate/High intensity by ranking cluster centroids on a composite
"driving intensity" score (harsh event rate + speed/RPM variability).
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "carobd_combined.parquet"
MODEL_DIR = ROOT / "models"
OUTPUT_PATH = ROOT / "outputs" / "phase1_driver_behaviour_results.json"

HARSH_ACCEL_THRESHOLD = 2.5   # km/h per second, approx
HARSH_BRAKE_THRESHOLD = -2.5


def build_trip_features(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for trip_id, g in df.groupby("trip_id"):
        g = g.sort_index()
        speed = g["VEHICLE_SPEED"].dropna()
        rpm = g["ENGINE_RPM"].dropna()
        throttle = g["THROTTLE"].dropna()
        load = g["ENGINE_LOAD"].dropna()

        if len(speed) < 10:
            continue

        accel = speed.diff().fillna(0)  # 1 Hz sampling -> diff ~= rate of change per second
        harsh_accel_rate = float((accel > HARSH_ACCEL_THRESHOLD).mean())
        harsh_brake_rate = float((accel < HARSH_BRAKE_THRESHOLD).mean())

        rows.append({
            "trip_id": trip_id,
            "driving_mode": g["driving_mode"].iloc[0],
            "speed_mean": speed.mean(),
            "speed_std": speed.std(),
            "speed_max": speed.max(),
            "accel_abs_mean": accel.abs().mean(),
            "accel_max": accel.max(),
            "harsh_accel_rate": harsh_accel_rate,
            "harsh_brake_rate": harsh_brake_rate,
            "rpm_mean": rpm.mean(),
            "rpm_std": rpm.std(),
            "throttle_mean": throttle.mean(),
            "throttle_std": throttle.std(),
            "engine_load_mean": load.mean(),
            "trip_length_s": len(g),
        })
    return pd.DataFrame(rows).fillna(0)


FEATURE_COLS = [
    "speed_mean", "speed_std", "speed_max",
    "accel_abs_mean", "accel_max", "harsh_accel_rate", "harsh_brake_rate",
    "rpm_mean", "rpm_std", "throttle_mean", "throttle_std", "engine_load_mean",
]


def main():
    df = pd.read_parquet(DATA_PATH)
    trip_features = build_trip_features(df)
    print(f"Built features for {len(trip_features)} trips")

    X = trip_features[FEATURE_COLS]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    silhouette_by_k = {}
    models_by_k = {}
    for k in range(2, 6):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        silhouette_by_k[k] = round(float(score), 4)
        models_by_k[k] = (km, labels)
        print(f"K={k}: silhouette={score:.4f}")

    best_k = max(silhouette_by_k, key=silhouette_by_k.get)
    best_model, best_labels = models_by_k[best_k]
    print(f"\nSelected K={best_k} by silhouette score")

    trip_features["cluster"] = best_labels

    # Rank clusters by a composite driving-intensity score so labels are meaningful,
    # not just arbitrary cluster indices.
    intensity_score = (
        trip_features.groupby("cluster")[["harsh_accel_rate", "harsh_brake_rate", "speed_std", "rpm_std"]]
        .mean()
        .apply(lambda r: r["harsh_accel_rate"] + r["harsh_brake_rate"] + r["speed_std"] / 100 + r["rpm_std"] / 1000, axis=1)
        .sort_values()
    )
    ordered_clusters = list(intensity_score.index)
    label_names = ["Low Intensity", "Moderate Intensity", "High Intensity", "Very High Intensity"][: len(ordered_clusters)]
    cluster_to_label = dict(zip(ordered_clusters, label_names))
    trip_features["behaviour_profile"] = trip_features["cluster"].map(cluster_to_label)

    print("\nTrips per behaviour profile:")
    print(trip_features["behaviour_profile"].value_counts())

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(best_model, MODEL_DIR / "driver_behaviour_kmeans.joblib")
    joblib.dump(scaler, MODEL_DIR / "driver_behaviour_scaler.joblib")
    joblib.dump(FEATURE_COLS, MODEL_DIR / "driver_behaviour_features.joblib")
    joblib.dump(cluster_to_label, MODEL_DIR / "driver_behaviour_cluster_labels.joblib")

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump({
            "dataset": "carOBD (eron93br/carOBD) - real Toyota Etios OBD-II logs",
            "method": "feature engineering + K-Means clustering (unsupervised profiling, not a predictive model)",
            "note": "No ground-truth driving-style labels exist; accuracy is not a valid metric here. "
                    "Silhouette score is used to select K and to assess cluster separation quality.",
            "trips_analyzed": len(trip_features),
            "silhouette_by_k": silhouette_by_k,
            "selected_k": best_k,
            "selected_k_silhouette": silhouette_by_k[best_k],
            "cluster_profile_counts": trip_features["behaviour_profile"].value_counts().to_dict(),
            "cluster_to_label": {str(k): v for k, v in cluster_to_label.items()},
        }, f, indent=2)

    trip_features.to_csv(ROOT / "outputs" / "phase1_driver_behaviour_trip_profiles.csv", index=False)
    print(f"\nSaved model to {MODEL_DIR / 'driver_behaviour_kmeans.joblib'}")
    print(f"Saved results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
