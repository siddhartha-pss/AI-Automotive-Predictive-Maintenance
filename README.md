# AI-Driven Automotive Predictive Maintenance System

Final-year project. Full plan, reasoning, and honest results/limitations are in
`documentation/` - start with `documentation/final_project_report.md`.

## How to run everything

The step numbers below show startup order; phase labels refer to the project phases.

### 1. Train/regenerate the ML models (Phase 1, Python)

```bash
pip install -r requirements.txt
python src/load_carobd.py          # combines the 126 raw carOBD trip files
python src/anomaly_detection.py    # trains + compares 3 anomaly models, saves the best
python src/fault_classification.py # trains + compares 3 fault classifiers, saves the best
python src/driver_behaviour.py     # engineers features + K-Means clustering
python src/combined_inference.py   # sanity-checks all 3 models together, writes a sample output
```

### 2. Start the ML service (Phase 3, Python/FastAPI)

```bash
cd ml_service
uvicorn main:app --reload --port 8000
```

### 3. Start the backend (Phase 2 LLM integration + Phase 3 orchestration, Node/Express)

```bash
cd backend
npm install
cp .env.example .env   # fill in ANTHROPIC_API_KEY for live LLM reports (optional - mock mode works without it)
npm start
```

### 4. Start the frontend (Phase 3, React/Vite)

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`) and click
"Load Sample Vehicle Analysis".

## Datasets (not committed - see .gitignore)

- `data/raw/carobd/` - download from https://github.com/eron93br/carOBD (`obdiidata/` folder)
- `data/raw/enginefaultdb/` - download `EngineFaultDB_Final.csv` from
  https://github.com/leoxthomas/EngineFaultDB

Full dataset reasoning: `documentation/phase1_dataset_selection.md`.

## What's honestly done vs. not

See `documentation/final_project_report.md` section 10-11 for the full, honest
breakdown - including what was verified running in this environment vs. what still
needs a real API key, a MongoDB instance, or a browser to confirm.
