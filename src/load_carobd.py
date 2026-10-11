"""
Loads and cleans the carOBD dataset (eron93br/carOBD, real Toyota Etios OBD-II logs, 1 Hz).

Source: https://github.com/eron93br/carOBD
Cited work: Vargas Rivero, "Detecting Anomalies in the Engine Coolant Sensor Using
One-Class Classifiers" (IEEE, 2019) - same dataset, confirms a one-class / unsupervised
anomaly detection approach is appropriate for this data (no labeled faults exist).

Each file in data/raw/carobd/ is one real drive. The filename prefix tells us the
driving mode:
  idle*  -> engine on, vehicle stationary
  drive* -> motion, high-speed roads
  live*  -> a specific commute route (work <-> home)
  ufpe*  -> motion inside a university campus (low speed)
  long*  -> long trips

This script concatenates all files into one DataFrame, tags each row with its
source file (trip_id) and driving mode, cleans column names, and reports basic
data-quality stats. It does NOT invent labels - this dataset has no fault labels.
"""

import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "carobd"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "carobd_combined.parquet"

MODE_PATTERN = re.compile(r"^([a-zA-Z]+?)\d*\.csv$")


def mode_from_filename(filename: str) -> str:
    match = MODE_PATTERN.match(filename)
    if not match:
        return "unknown"
    return match.group(1).lower()


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().replace(" ()", "").replace("()", "").strip() for c in df.columns]
    return df


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    skip = {"trip_id", "driving_mode"}
    for col in df.columns:
        if col in skip:
            continue
        df[col] = pd.to_numeric(df[col].astype(str).str.strip(), errors="coerce")
    return df


def load_all() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"SKIPPED {f.name}: {e}")
            continue
        df = clean_columns(df)
        df = coerce_numeric(df)
        df["trip_id"] = f.stem
        df["driving_mode"] = mode_from_filename(f.name)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    return combined


def report_quality(df: pd.DataFrame) -> None:
    print(f"Total rows: {len(df)}")
    print(f"Total trips: {df['trip_id'].nunique()}")
    print("Rows per driving mode:")
    print(df["driving_mode"].value_counts())
    print("\nMissing values per column (top 10):")
    print(df.isna().sum().sort_values(ascending=False).head(10))
    print(f"\nDuplicate rows: {df.duplicated().sum()}")


if __name__ == "__main__":
    combined = load_all()
    report_quality(combined)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUT_PATH, index=False)
    print(f"\nSaved combined dataset to {OUT_PATH}")
