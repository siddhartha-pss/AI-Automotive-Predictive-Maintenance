"""
Phase 3 - Python FastAPI ML service.

This is the only place the three trained models (Phase 1) get loaded and run.
The Node/Express backend calls this service over HTTP instead of re-implementing
any ML logic in JavaScript - keeping ML code in Python, as recommended in
documentation/phase3_backend.md.

Run with:  uvicorn main:app --reload --port 8000   (from inside ml_service/)
"""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from combined_inference import (  # noqa: E402
    load_models, run_anomaly_detection, run_fault_classification,
    run_driver_behaviour, build_vehicle_health_context,
)

app = FastAPI(title="Automotive Predictive Maintenance - ML Service", version="1.0")

_models = None


def get_models():
    global _models
    if _models is None:
        _models = load_models()
    return _models


class AnomalyInput(BaseModel):
    ENGINE_RPM: float
    VEHICLE_SPEED: float
    THROTTLE: float
    ENGINE_LOAD: float
    COOLANT_TEMPERATURE: float
    LONG_TERM_FUEL_TRIM_BANK_1: float
    SHORT_TERM_FUEL_TRIM_BANK_1: float
    INTAKE_MANIFOLD_PRESSURE: float
    INTAKE_AIR_TEMP: float
    TIMING_ADVANCE: float
    CONTROL_MODULE_VOLTAGE: float


class FaultInput(BaseModel):
    """A ~5-second window of aggregated, standard OBD-II PID readings (RPM,
    accelerator pedal position, MAF) - see
    documentation/fault_classification_replacement_report.md for exactly how
    these are computed from raw PID samples. All fields here are genuinely
    obtainable from a standard ELM327/OBD-II connection."""
    rpm_mean: float
    rpm_std: float
    pedal_mean: float
    pedal_std: float
    maf_mean: float
    maf_std: float
    maf_min: float
    maf_max: float
    maf_negative_rate: float


class BehaviourInput(BaseModel):
    speed_mean: float
    speed_std: float
    speed_max: float
    accel_abs_mean: float
    accel_max: float
    harsh_accel_rate: float
    harsh_brake_rate: float
    rpm_mean: float
    rpm_std: float
    throttle_mean: float
    throttle_std: float
    engine_load_mean: float


class CombinedRequest(BaseModel):
    vehicle_id: str
    anomaly_input: AnomalyInput
    fault_input: FaultInput
    behaviour_input: BehaviourInput


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict/anomaly")
def predict_anomaly(payload: AnomalyInput):
    models = get_models()
    return run_anomaly_detection(models, payload.model_dump())


@app.post("/predict/fault")
def predict_fault(payload: FaultInput):
    models = get_models()
    return run_fault_classification(models, payload.model_dump())


@app.post("/predict/behaviour")
def predict_behaviour(payload: BehaviourInput):
    models = get_models()
    return run_driver_behaviour(models, payload.model_dump())


@app.post("/predict/combined")
def predict_combined(payload: CombinedRequest):
    models = get_models()

    anomaly_result = run_anomaly_detection(models, payload.anomaly_input.model_dump())

    fault_result = run_fault_classification(models, payload.fault_input.model_dump())

    behaviour_result = run_driver_behaviour(models, payload.behaviour_input.model_dump())

    context = build_vehicle_health_context(
        anomaly_result, fault_result, behaviour_result,
        vehicle_meta={"vehicle_id": payload.vehicle_id},
    )
    return context


@app.on_event("startup")
def preload_models():
    try:
        get_models()
        print("Models loaded successfully at startup.")
    except FileNotFoundError as e:
        print(f"WARNING: models not found ({e}). Run the Phase 1 scripts in src/ first.")
