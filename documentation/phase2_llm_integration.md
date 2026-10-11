# Phase 2 - LLM Integration

## 1. What the LLM does in this project

The three ML models (anomaly detection, fault classification, driver behaviour)
already do the real analysis. The LLM's only job is to turn their technical
results into a short, plain-language report a non-technical vehicle owner can
read - it does not do any prediction itself.

## 2. Why an LLM is needed after the ML models

A line like `{"predicted_fault_class": 0, "confidence": 0.9999}` means nothing to
a vehicle owner. The LLM reads that structured result and writes a sentence like
"the model's best guess is fault category 0, with very high confidence, based on
lab-trained data" - same information, understandable language.

## 3. What data is sent to the LLM

Only the structured combined JSON from Phase 1 (`vehicle_meta`, `anomaly`,
`fault`, `driver_behaviour`, `schema_version`) - never raw sensor rows, never the
full dataset. Same input shape regardless of which provider is active.

## 4. What the LLM returns

A JSON object with 8 fixed fields:
```json
{
  "overall_status": "...",
  "summary": "...",
  "anomaly_explanation": "...",
  "fault_explanation": "...",
  "driver_behaviour_explanation": "...",
  "recommended_actions": ["...", "..."],
  "severity": "Low | Moderate | High | Unknown",
  "limitations": "..."
}
```
This schema is shared by every provider (`backend/src/llm/prompt.js`), so the
report looks the same no matter which LLM generated it.

## 5. Why the LLM does not perform the actual vehicle prediction

The system prompt explicitly forbids it: the LLM is told it must only explain
the given JSON, never invent a fault/value/confidence, and never state a fault as
confirmed - the fault result is a probable classification from a trained model,
not a diagnosis. See `backend/src/llm/prompt.js` for the exact wording.

## 6. How Gemini is integrated

- **Package:** `@google/genai` (v2.27.0 at time of writing) - confirmed to be the
  current, actively maintained official Google SDK (the older
  `@google/generative-ai` package is legacy and was not used).
- **Model actually confirmed working:** `gemini-3.8-flash`. Two other model
  names were tried first and genuinely failed live:
  `gemini-flash-latest` returned a real `503 UNAVAILABLE` ("high demand"), and
  `gemini-2.5-flash` returned a real `404 NOT_FOUND` whose error message said it
  is "no longer available to new users" and recommended `gemini-3.8-flash` -
  which was then tried and worked. This is documented as a real finding, not a
  guess.
- **Structured output:** the Gemini call uses `responseMimeType: "application/json"`
  plus a `responseSchema` (built from the same shared schema in `prompt.js`), so
  Gemini is constrained to return valid JSON matching the shape above, rather
  than relying on prompt instructions alone.
- File: `backend/src/llm/providers/gemini.js`.

## 7. How API keys are protected

- Keys are read only from environment variables (`GEMINI_API_KEY`,
  `ANTHROPIC_API_KEY`) via `backend/.env` - never hard-coded anywhere.
- `.env` is excluded by `.gitignore` (already was, confirmed unchanged).
- Keys are never logged - error messages surface the API's own error text, which
  does not include the key.
- All LLM calls happen inside the Express backend
  (`backend/src/llm/providers/*.js`); the frontend never sees a key and never
  calls Gemini/Anthropic directly - it only calls the Express backend.

## 8. How the provider-independent architecture works

```
routes/report.js, routes/analyze.js
        |
        v
generateMaintenanceReport(vehicleContext)   <- backend/src/llm/reportGenerator.js
        |
        | reads process.env.LLM_PROVIDER
        v
  "gemini"    -> providers/gemini.js    -> Google Gemini API
  "anthropic" -> providers/anthropic.js -> Anthropic Claude API
  "mock" / unset / unrecognised -> providers/mock.js (no network call)
```

Every provider module has the same contract: given a `vehicleContext`, either
return `{provider, model, report}` or throw. `reportGenerator.js` is the only
place that catches provider errors - every failure (missing key, invalid key,
API error, timeout, malformed JSON) is turned into the same safe response:
`{mode: "error_fallback", note: "<real error>", report: <mock template>}`. The
rest of the app (routes, frontend) never has to know which provider is active or
how it failed.

## 9. How Gemini can later be replaced with Groq or another provider

1. Create `backend/src/llm/providers/groq.js` exporting an async function with
   the same `(vehicleContext) -> {provider, model, report}` contract (or throw),
   using the same shared prompt/schema from `prompt.js`.
2. Add one line to the `PROVIDERS` map in `reportGenerator.js`:
   `groq: generateGroqReport`.
3. Set `LLM_PROVIDER=groq` and the relevant API key in `.env`.

No other file changes - not `routes/`, not `server.js`, not the frontend.
This was verified by actually testing `LLM_PROVIDER=anthropic` and
`LLM_PROVIDER=groq` (unimplemented) against the already-written code with zero
code changes - see `documentation/llm_provider_integration_report.md` for the
exact test results.

## 10. Current limitations

- **Gemini has been genuinely tested and has produced one real, successful
  response** (captured in `llm_provider_integration_report.md`), but the free-tier
  endpoint was observed to return `503 UNAVAILABLE` ("high demand") intermittently
  on repeated calls in this environment - this is Google's server-side load, not a
  bug in this code, but it means "live" mode is not 100% reliably available on
  every single request right now.
- The Anthropic provider's own API key was never supplied in this environment, so
  only its missing-key error path was exercised (and worked correctly) - no
  example of a real, successful Anthropic response exists from this session (one
  did exist from earlier Phase 2 validation work with a deliberately invalid key,
  which correctly produced a real 401 error).
- ~~Fault classification's lab-only limitation~~ - **RESOLVED**, see
  `fault_classification_replacement_report.md`; the LLM now explicitly echoes
  the new (narrower) single-vehicle scope limitation instead.
- ~~No history/persistence~~ - **RESOLVED**. `/api/report` and `/api/analyze`
  now save every generated analysis to MongoDB (when connected) and it can be
  retrieved via the new history endpoints - see
  `mongodb_implementation_report.md`.
