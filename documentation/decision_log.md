# Project Decision Log

Format: Decision / Why / Alternatives considered / Reason for final choice.

---

**Decision:** Replace the EngineFaultDB-based fault classifier entirely with a
new model trained on `edgeimpulse/obd-automotive-data` (real BMW N53, real
induced intake-air-leak fault, standard OBD-II PIDs only).
**Why:** EngineFaultDB required lab-grade exhaust-gas/dyno inputs that a
consumer OBD-II/ELM327 connection cannot supply - the single biggest
architectural gap in the project.
**Alternatives considered:** DTC-code reference datasets (rejected - these are
code lookup tables, not labeled sensor data); CAN-bus intrusion-detection
datasets (rejected - labeled for cyberattacks, not mechanical faults); a
broader multi-vehicle real-fault dataset was searched for and not found within
scope.
**Reason for final choice:** this is the only dataset found that is
simultaneously real (not synthetic), genuinely OBD-II-PID-only, and has an
actually-induced (not lab-simulated) fault condition on a real vehicle. Its
small scope (1 vehicle, 1 fault type) is a real limitation, documented
explicitly rather than hidden - see `fault_classification_replacement_report.md`.

**Decision:** Exclude the dataset's own `NOx` column from the deployed model
despite it separating the two classes almost perfectly.
**Why:** NOx is not a standard, broadly-available OBD-II Mode 01 PID - using it
would have produced a better-looking but secretly non-live-compatible model,
the exact problem being fixed.
**Alternatives considered:** including it anyway for a higher headline metric.
**Reason for final choice:** a side-by-side comparison (documented in the
report) showed the genuinely OBD-II-compatible features (RPM, pedal, MAF) alone
already reach perfect test macro-F1 - there was no accuracy cost to doing this
correctly.

---

**Decision:** Refactor the LLM step into a provider-independent layer
(`LLM_PROVIDER` env var selecting gemini/anthropic/mock), with Gemini as the
first real provider, instead of keeping the original Anthropic-only
implementation.
**Why:** needed to add Google Gemini support without hard-coding it alongside
the existing Anthropic code, and without changing the ML pipeline or dashboard.
**Alternatives considered:** keeping two separate, hand-maintained code paths in
`reportGenerator.js`; rewriting the frontend to know about providers (rejected -
the frontend already renders the report generically and never needed to know).
**Reason for final choice:** one shared prompt/schema (`llm/prompt.js`) + one
dispatcher (`llm/reportGenerator.js`) + one file per provider
(`llm/providers/*.js`) keeps every provider's error handling identical and lets
a future provider (e.g. Groq) be added with one new file and one line, with zero
changes to routes or the frontend - verified by actually switching providers via
env var alone. Full detail: `llm_provider_integration_report.md`.

**Decision:** Use `@google/genai` (not the older `@google/generative-ai`) for
Gemini, and `gemini-3.8-flash` (not `gemini-flash-latest` or `gemini-2.5-flash`)
as the default model.
**Why:** confirmed via the npm registry that `@google/genai` is the actively
maintained package. The model choice was decided by actually calling the live
API, not guessed.
**Alternatives considered:** `gemini-flash-latest` (real API call returned a
genuine `503 UNAVAILABLE`); `gemini-2.5-flash` (real API call returned a genuine
`404`, with Google's own error message stating it is deprecated for new users
and recommending `gemini-3.8-flash`).
**Reason for final choice:** `gemini-3.8-flash` is the only one of the three that
was confirmed, with a real successful API response, to actually work.

---

**Decision:** Use carOBD (real Toyota Etios OBD-II logs) for anomaly detection and
driver behaviour, instead of the PDF's "19drivers"/KIT dataset.
**Why:** Needed a real, directly-downloadable (no login/click-through) dataset.
**Alternatives considered:** KIT Automotive OBD-II dataset (confirmed real, but
download is gated behind a JS click-through terms flow that could not be scripted
reliably).
**Reason for final choice:** carOBD has a comparable real OBD-II PID set, is larger
(126 trips / 298K rows vs. KIT's smaller release), and downloads directly via
GitHub's raw content API.

---

**Decision:** Use One-Class SVM / Isolation Forest / Local Outlier Factor
(unsupervised one-class methods) for anomaly detection instead of LSTM.
**Why:** carOBD has no fault labels at all - a supervised LSTM has nothing to learn
from, and the dataset's own source thesis uses one-class classifiers for this exact
problem.
**Alternatives considered:** LSTM-Autoencoder (literature-supported, and confirmed
technically possible - TensorFlow 2.22 installs and imports on Python 3.14 in this
environment).
**Reason for final choice:** the simpler one-class methods already gave an
honestly-validated result (synthetic-validation F1 0.50 for One-Class SVM);
LSTM-Autoencoder is left as a documented "Recommended" future improvement rather
than adding deep-learning complexity that wasn't required to reach a working,
defensible model.

---

**Decision:** Use EngineFaultDB (real lab-induced fault data) for fault
classification instead of injecting synthetic anomalies into our own data.
**Why:** The master prompt explicitly flagged synthetic-label training as a
limitation to avoid where possible.
**Alternatives considered:** continuing with synthetic injection on carOBD (as the
PDF's "work done so far" slide originally did); Kaggle's generic industrial
"Machine Predictive Maintenance" dataset (not vehicle-specific, rejected as
misleading to label "vehicle fault").
**Reason for final choice:** EngineFaultDB is real, peer-reviewed (IEEE Access
2023), vehicle-engine-specific data with genuinely induced (not fabricated) fault
conditions - a stronger basis, honestly caveated as lab-only, not in-service.

---

**Decision:** Treat driver behaviour as feature engineering + K-Means clustering,
not a "model" reported with "accuracy".
**Why:** No ground-truth driving-style labels exist in carOBD; accuracy is not a
valid metric for unsupervised clustering.
**Alternatives considered:** keeping the PDF's original "99.8% accuracy" framing.
**Reason for final choice:** silhouette score is the technically correct metric
here; using "accuracy" would be a known-wrong metric.

---

**Decision:** Claude Haiku 4.5 as the Phase 2 LLM.
**Why:** short, structured summarization task; cost and student-project budget
matter.
**Alternatives considered:** a second paid backup LLM (not added - the mock
fallback already covers "no API key" testing); escalation to Claude Sonnet 5.5 if
report quality needs to improve later.
**Reason for final choice:** cheapest current-generation Anthropic model, official
SDK, reliable JSON-following, more than enough context window for this payload.

---

**Decision:** FastAPI (Python) owns all ML inference; Node/Express only
orchestrates.
**Why:** avoid re-implementing model logic in JavaScript.
**Alternatives considered:** running models directly inside Node via a Python
subprocess call per-request (rejected - slower, harder to debug than a persistent
FastAPI service with models loaded once at startup).
**Reason for final choice:** cleanest separation of concerns for an 8-credit
project; verified working end-to-end in this environment.

---

**Decision:** MongoDB integration code was not written in this session.
**Why:** No running MongoDB instance or Docker daemon was available to test
against (`docker ps` failed; no `mongod`/`mongosh` found).
**Alternatives considered:** writing untested Mongoose code anyway.
**Reason for final choice:** per the master prompt's own rule ("never fabricate...
if something has not been tested, say so"), writing DB code with zero ability to
verify it would risk shipping broken, unverified code. This is flagged as the next
step once a MongoDB instance (local, Docker, or Atlas) is available.
