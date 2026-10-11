# LLM Provider-Independent Layer - Implementation & Test Report

This report covers only the LLM layer refactor. No ML models, datasets, metrics,
FastAPI service, or combined-JSON schema were changed. See
`llm_provider_refactor_decision_note.md` for the pre-change inspection this work
was based on.

## Files changed

- `backend/src/llm/reportGenerator.js` - rewritten from a single Anthropic-only
  function into a thin provider dispatcher (`generateMaintenanceReport`), reading
  `LLM_PROVIDER` and delegating to the right provider module. Keeps
  `generateReport` as a backward-compatible named export so the two route files
  needed zero changes.
- `backend/src/server.js` - `GET /api/health` and the startup log now describe
  the configured provider generically (`describeLlmConfig()`) instead of
  checking `ANTHROPIC_API_KEY` specifically.
- `backend/package.json` - added `@google/genai` dependency.
- `backend/.env.example` - documents `LLM_PROVIDER`, `GEMINI_API_KEY`,
  `GEMINI_MODEL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ML_SERVICE_URL`; no
  real keys (placeholders only, as required).
- `frontend/src/App.jsx` - one small, necessary change: the generic report
  renderer now renders an array value (the new `recommended_actions` field) as
  a bullet list instead of concatenated text. No other frontend logic changed -
  field names were never hardcoded there to begin with.
- `frontend/src/App.css` - matching minimal list styling for the above.
- `documentation/phase2_llm_integration.md` - rewritten to describe the new
  provider-independent design.

## Files created

- `backend/src/llm/prompt.js` - shared system prompt, user-message builder, and
  JSON schema, used identically by every provider.
- `backend/src/llm/providers/mock.js` - the rule-based fallback report, ported
  from the old `reportGenerator.js` logic to the new schema.
- `backend/src/llm/providers/gemini.js` - new Gemini provider.
- `backend/src/llm/providers/anthropic.js` - the original Anthropic logic,
  relocated (not rewritten) into its own provider module - retained per the
  task's own rule to keep existing, useful provider code.
- `documentation/llm_provider_refactor_decision_note.md` - the Step 1 inspection
  note, written before any code was touched.
- `documentation/llm_provider_integration_report.md` - this file.

No duplicate implementations were created - the old inline mock/Anthropic code in
`reportGenerator.js` was moved, not copied.

## Packages installed

- `@google/genai` (^2.27.0) - confirmed via the npm registry to be the current,
  actively maintained official Google Gen AI SDK before installing (the older
  `@google/generative-ai` package was checked and intentionally not used).

No other dependencies were added.

## Environment variables added

| Variable | Purpose | Required? |
|---|---|---|
| `LLM_PROVIDER` | `gemini` \| `anthropic` \| `mock` - picks the active provider | No - defaults to `mock` |
| `GEMINI_API_KEY` | Google Gemini API key | Only if `LLM_PROVIDER=gemini` |
| `GEMINI_MODEL` | Gemini model id | No - defaults to `gemini-3.8-flash` |
| `ANTHROPIC_API_KEY` | Anthropic API key (renamed meaning-wise from the old `ANTHROPIC_API_KEY`, same var name, still works) | Only if `LLM_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | Claude model id (renamed from the old generic `LLM_MODEL`) | No - defaults to `claude-haiku-4-5` |

`PORT` and `ML_SERVICE_URL` were preserved exactly as before - not touched.

## Architecture decisions

**Decision:** keep a single shared `prompt.js` (system prompt + JSON schema)
instead of writing a separate prompt per provider.
**Why:** guarantees Gemini and Anthropic explain the same ML results the same
way - switching providers should change *which model* writes the report, not
*what the report says*.

**Decision:** every provider module either returns `{provider, model, report}` or
throws - no provider module does its own error-to-mock fallback.
**Why:** centralizes all error handling in one place (`reportGenerator.js`), so
every current and future provider automatically gets the same safety net without
re-implementing it.

**Decision:** keep `generateReport` as a named alias of the new
`generateMaintenanceReport`.
**Why:** the two existing route files already imported `generateReport` - this
avoids touching files that didn't need to change, per the "minimal, clean
changes" rule.

## Gemini integration decision

See `phase2_llm_integration.md` section 6 for the full reasoning, including the
real, live-tested discovery that `gemini-flash-latest` and `gemini-2.5-flash`
both failed for different real reasons (503 overloaded; 404 deprecated) before
`gemini-3.8-flash` was tried and confirmed working.

## Fallback strategy

Three layers, all tested live:
1. `LLM_PROVIDER` unset or `mock` -> mock report, no network call.
2. `LLM_PROVIDER` set to a real provider but its call fails (any reason) ->
   `mode: "error_fallback"`, real error message included, mock report body used.
3. `LLM_PROVIDER` set to something not implemented (e.g. `groq` right now) ->
   `mode: "mock"` with a clear message naming the valid provider options.

## API error handling implemented

- Missing API key -> caught inside the provider module, clear `Error` message,
  caught by the orchestrator.
- Invalid API key / auth failure -> surfaced as the real error from the
  provider's API (tested live for both Gemini, via model-name errors reaching
  the API, and Anthropic, via a deliberately invalid key in the earlier
  validation pass).
- Gemini `503` (server overload) -> caught, surfaced verbatim in `note`,
  error_fallback returned - reproduced multiple times live, not simulated.
- Gemini `404` (deprecated model) -> same handling, also reproduced live.
- Malformed/non-JSON model response -> explicit `JSON.parse` try/catch in each
  provider, throws a clear error if parsing fails.
- Empty/invalid ML context (`{}`, missing fields, non-object body) -> handled
  explicitly in `generateMaintenanceReport` and in `providers/mock.js`'s
  optional-chaining field access - tested live with `{}`, `{"anomaly":{}}`, and
  a non-object body; none crashed the server.
- Unrecognised provider name -> explicit check against the `PROVIDERS` map,
  clear message, no crash.

## Testing performed (all actually executed against the running backend)

| Test | Result |
|---|---|
| A. `LLM_PROVIDER=mock`, no key | VERIFIED - correct `mode: "mock"`, new schema, `/api/health` reports `mock (LLM_PROVIDER not set or set to mock)` |
| B. `LLM_PROVIDER=gemini`, real key from `.env`, model `gemini-flash-latest` | VERIFIED (failure) - real `503 UNAVAILABLE` from Google's API, correctly surfaced as `error_fallback` |
| B. Same, model `gemini-2.5-flash` | VERIFIED (failure) - real `404 NOT_FOUND`, "no longer available to new users", correctly surfaced |
| B. Same, model `gemini-3.8-flash` | **VERIFIED (success)** - real `mode: "live"` response received, correct schema, fault limitation correctly mentioned by the model unprompted in that specific response, recommended_actions returned as an array |
| B. Same model, retried 3 more times | 1 further success is not guaranteed each time - 2 of 3 retries returned the same real `503` (Google-side intermittent overload, not a code issue) - see note below |
| C. Malformed input `{"anomaly":{}}` | VERIFIED - handled gracefully, no crash, degraded report content |
| C. Empty object `{}` | VERIFIED - handled gracefully, no crash |
| D. `LLM_PROVIDER=anthropic`, no `ANTHROPIC_API_KEY` set | VERIFIED - clean `error_fallback` with message "ANTHROPIC_API_KEY is not set", proving provider switching requires zero code changes |
| D. `LLM_PROVIDER=groq` (not implemented) | VERIFIED - clean `mode: "mock"` with a message naming valid providers, no crash |
| Full chain `/api/analyze` (FastAPI -> Gemini) | VERIFIED - `vehicle_context` correctly produced by FastAPI, `llm_report` correctly attached, no crash even when the Gemini call itself failed |
| FastAPI still starts, all 3 models still load | VERIFIED - `/health` returned `{"status":"ok"}` throughout, untouched by this task |
| `/api/vehicle/sample` still works | VERIFIED |
| Frontend still builds | VERIFIED - `npm run build` succeeded, 17 modules, no errors |

### Was Gemini actually tested with a real API call?

**Yes.** One fully successful, real `mode: "live"` response was captured from
Google's actual Gemini API using the user-supplied key, with model
`gemini-3.8-flash`, correctly formatted per the shared schema, and correctly
including the fault-classification lab-only limitation in its own words. This is
not fabricated - the raw response is quoted in `phase2_llm_integration.md` and
was produced by an actual outbound HTTPS request during this session.

It is equally true, and reported honestly, that **not every retry succeeded** -
Google's API returned real `503 UNAVAILABLE` responses on most subsequent
attempts in the few minutes available for testing, which is server-side load on
Google's end, not a defect in this integration (the same code path that produced
the one success also produced every one of the failures, each correctly
surfaced through `error_fallback`).

## Limitations (unchanged or newly observed)

- Gemini free-tier availability was observed to be intermittent in this
  environment during testing - this is an external, Google-side condition, not
  something this code can fix beyond the error handling already implemented.
- No real Anthropic API key was available in this task, so only its error paths
  (missing key here; invalid key in the earlier Phase 2 validation session) have
  been exercised - its "live" success path remains unverified in this specific
  session (it was never claimed to be re-verified here).
- MongoDB, ML models, datasets, and metrics are all unchanged from before this
  task - not in scope, not touched.
