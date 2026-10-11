# Phase 1 - Dataset Selection

## What was done

Researched publicly available, real (not fabricated) datasets for each of the three ML
tasks, instead of assuming the datasets mentioned in the reference PDF were final.

## Datasets selected

### 1. carOBD (anomaly detection + driver behaviour)

- Source: https://github.com/eron93br/carOBD (open, no login/API key needed)
- Real OBD-II logs from a Toyota Etios (2014), 27 PIDs, 1 Hz sampling
- 126 real trips downloaded (idle / drive / live-commute / campus / long-trip modes)
- 298,306 total rows after cleaning
- No fault labels exist in this dataset - confirmed by its own source thesis
  ("Detecting Anomalies in the Engine Coolant Sensor Using One-Class Classifiers",
  IEEE 2019), which is why anomaly detection here uses one-class/unsupervised methods.
- License: open-source, cite the author's thesis if used in a paper.

### 2. EngineFaultDB (fault classification)

- Source: https://github.com/leoxthomas/EngineFaultDB (GPL-3.0)
- Paper: Vergara, Ramos, Rivera-Campoverde, Rivas-Echeverria, IEEE Access 2023
- Real lab-bench data from a C14NE spark-ignition engine under controlled,
  lab-induced fault conditions (4 classes, 55,999 rows, 14 variables including
  MAP, RPM, Speed, and exhaust-gas readings CO/HC/CO2/O2/Lambda/AFR)
- Not from an in-service vehicle - this is a documented limitation, not hidden.

## Why not the PDF's original datasets?

The PDF referenced a "19drivers OBD-II dataset" and "KIT route files". The KIT
Automotive OBD-II dataset (radar.kit.edu, DOI 10.35097/1130) was located and
confirmed to be real, but its download requires accepting click-through terms via
a JavaScript-gated repository UI, which could not be scripted reliably in this
environment. carOBD was selected instead because it provides the same kind of
real OBD-II signals (similar PID set, comparable size) and is directly downloadable
without authentication, which matters for a reproducible pipeline.

## Important limitation (see also phase1_results.md)

The carOBD dataset (used for anomaly detection and driver behaviour) and
EngineFaultDB (used for fault classification) do NOT share the same input schema.
EngineFaultDB requires exhaust-gas-analyzer and dynamometer readings that a
standard consumer OBD-II/ELM327 connection cannot provide. This means, as currently
built, fault classification cannot run on the same live OBD-II stream as the other
two modules. This is flagged throughout the code and documentation rather than
glossed over - see `documentation/phase1_results.md` for the full discussion.
