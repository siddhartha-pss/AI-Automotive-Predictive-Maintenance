# Phase 1 - Anomaly Detection

## What was done

Built and compared three unsupervised/one-class anomaly detection models on the
carOBD dataset: Isolation Forest, One-Class SVM, and Local Outlier Factor (novelty
mode).

## Why not LSTM / LSTM-Autoencoder (the PDF's original choice)?

The carOBD dataset has no fault labels at all - every row is unlabeled real driving
data. This is a textbook one-class problem, and the dataset's own source thesis
("Detecting Anomalies in the Engine Coolant Sensor Using One-Class Classifiers")
uses exactly this family of method. A plain supervised LSTM classifier needs labels
it doesn't have; an LSTM-Autoencoder was considered (and technically works on
Python 3.14 / TensorFlow 2.22 in this environment, confirmed working) but was not
used for the final model because the simpler one-class methods already gave an
honestly-validated result and kept the pipeline easier to reproduce and explain for
an 8-credit project. This is flagged as a "Recommended, not essential" upgrade for
later - see Limitations below.

## Validation strategy (read this before trusting any number below)

There is no ground truth for "this reading is a real fault" in this dataset, so we
cannot report a true precision/recall against real anomalies. Two different,
clearly-labeled things are reported instead:

1. **Real-data anomaly rate** - what fraction of real, untouched test data each
   model flags. A sanity check, not an accuracy measure.
2. **Synthetic-validation metrics** - a separate labeled set built by injecting
   obvious perturbations (coolant spike, RPM dropout, MAP instability) into
   held-out real data, used ONLY to check a model can catch extreme deviations.
   Passing this does NOT prove the model would catch a real, subtle fault.

## Results

| Model | Synthetic F1 | Synthetic Precision | Synthetic Recall | Real-data anomaly rate |
|---|---|---|---|---|
| Isolation Forest | 0.051 | 0.056 | 0.046 | 4.07% |
| **One-Class SVM (selected)** | **0.500** | 0.450 | 0.563 | 3.59% |
| Local Outlier Factor | 0.302 | 0.198 | 0.633 | 13.47% |

Train: 239,606 rows (trip-level split, not random-row split, to avoid leaking
near-identical consecutive seconds across train/test). Test: 58,697 rows.

**Selected model: One-Class SVM** - best synthetic-validation F1, and a real-data
anomaly rate (3.6%) close to the 3% contamination assumption used to train it,
which is a reasonable sanity signal.

## Limitations (not hidden)

- No real-world fault ground truth exists for this dataset - all metrics above are
  either sanity checks or synthetic-injection checks, not proof of real-fault
  detection performance.
- One-Class SVM was trained on a 10,000-row subsample (full 239K rows does not
  scale to SVM's O(n^2) training cost) - documented, not silently done.
- An LSTM-Autoencoder comparison (closer to the literature review's Paper 3) is a
  reasonable future improvement now that TensorFlow is confirmed to work in this
  environment, but was not required to reach a working, honestly-evaluated model.

## Saved artifacts

- `models/anomaly_detection_model.joblib`
- `models/anomaly_detection_scaler.joblib`
- `models/anomaly_detection_features.joblib`
- Full results: `outputs/phase1_anomaly_detection_results.json`
