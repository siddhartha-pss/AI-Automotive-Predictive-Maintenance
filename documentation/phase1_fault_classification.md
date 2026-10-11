# Phase 1 - Fault Classification (SUPERSEDED - see note)

> **This document describes the ORIGINAL EngineFaultDB-based fault classifier,
> which has been REPLACED.** It is kept here as historical record, not deleted,
> per the project's decision-log practice. The current, deployed fault
> classifier uses a different, genuinely OBD-II-compatible dataset and model -
> see `documentation/fault_classification_replacement_report.md` for the full
> replacement story, and `documentation/phase1_results.md` for the updated
> summary table. The content below is left exactly as originally written for
> the record.

## What was done

Compared Logistic Regression (baseline), Random Forest, and XGBoost on EngineFaultDB
(real lab-bench engine data, 4 fault classes, 55,999 rows). 70/15/15 stratified
train/validation/test split. Model selected by validation macro-F1; test metrics
computed once, at the end, on the held-out test set only.

## Label honesty

The 4 classes in EngineFaultDB come from a real engine test rig under
**lab-induced** fault conditions (controlled by the dataset's original authors using
a gas analyzer and DAQ card) - not from an in-service vehicle, and not purely
synthetic/fabricated numbers either. This is a real improvement over the project's
earlier approach (injecting synthetic anomalies into our own data), but it is still
a lab environment, not real-world driving. This distinction is kept explicit in the
model's saved metadata and in the combined output JSON
(`fault.label_source` field).

## Results (validation set, used for model selection)

| Model | Accuracy | Macro-Precision | Macro-Recall | Macro-F1 |
|---|---|---|---|---|
| Logistic Regression | 0.591 | 0.594 | 0.589 | 0.591 |
| Random Forest | 0.743 | 0.751 | 0.751 | 0.751 |
| **XGBoost (selected)** | **0.744** | 0.753 | 0.753 | 0.753 |

## Final test-set results (XGBoost, evaluated once)

- Accuracy: 0.751
- Macro-Precision: 0.759
- Macro-Recall: 0.759
- Macro-F1: 0.759

Confusion matrix:
```
            pred0  pred1  pred2  pred3
true0        2399      0      1      0
true1           0   1650      0      0
true2           0      0   1194   1056
true3           0      0   1039   1061
```

## Honest finding - do not hide this

Classes 0 and 1 are almost perfectly separable. **Classes 2 and 3 are not** - the
model confuses them roughly 50/50. This is a real, interesting result: whatever
distinguishes fault type 2 from fault type 3 in this dataset is not well captured
by these 14 sensor variables with these models. This should be reported honestly in
any presentation, not smoothed over by only quoting the overall 75% accuracy.

## Important integration limitation

This model's input features (MAP, TPS, Force, Power, RPM, fuel consumption,
Speed, CO, HC, CO2, O2, Lambda, AFR) include exhaust-gas and dynamometer readings
that a standard consumer OBD-II/ELM327 setup cannot provide. As currently trained,
this model can only run on EngineFaultDB-shaped input, not on a live OBD-II stream
from a real vehicle. This is reflected in the combined output schema
(`fault.input_compatible_with_live_obd2 = false`) - see
`documentation/phase1_results.md` for the full discussion and what it means for the
project's real-vehicle story.

## Saved artifacts

- `models/fault_classification_model.joblib`
- `models/fault_classification_scaler.joblib`
- `models/fault_classification_features.joblib`
- Full results: `outputs/phase1_fault_classification_results.json`
