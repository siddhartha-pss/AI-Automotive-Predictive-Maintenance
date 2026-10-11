# Phase 1 - Driver Behaviour Analysis

## What was done

This is **feature engineering + unsupervised clustering**, explicitly not a
predictive ML model in the same sense as the other two modules. There is no
ground-truth "driving style" label anywhere in the carOBD dataset - we are grouping
126 real trips by engineered behavioural statistics, not predicting a known answer.

## Features engineered (per trip)

Speed (mean/std/max), acceleration derived from the 1 Hz speed series (mean abs,
max, harsh-acceleration event rate, harsh-braking event rate using a threshold),
RPM (mean/std), throttle (mean/std), engine load (mean).

## Method and metric

K-Means with K=2..5, trip-level features standardized first. K selected by
silhouette score (the correct metric here - there are no labels to be "accurate"
against, so the PDF's originally-reported "99.8% accuracy" for K-Means was not a
valid metric and has been replaced).

| K | Silhouette score |
|---|---|
| 2 | 0.479 |
| **3 (selected)** | **0.589** |
| 4 | 0.503 |
| 5 | 0.504 |

## Result

3 clusters, ranked into meaningful labels by a composite intensity score (harsh
event rate + speed/RPM variability), not arbitrary cluster indices:

| Profile | Trips |
|---|---|
| Low Intensity | 49 |
| Moderate Intensity | 69 |
| High Intensity | 8 |

A silhouette score of 0.59 indicates reasonably well-separated clusters (not
perfect, but meaningfully better than random grouping).

## Saved artifacts

- `models/driver_behaviour_kmeans.joblib`
- `models/driver_behaviour_scaler.joblib`
- `models/driver_behaviour_cluster_labels.joblib`
- Per-trip features and assigned profile: `outputs/phase1_driver_behaviour_trip_profiles.csv`
- Full results: `outputs/phase1_driver_behaviour_results.json`
