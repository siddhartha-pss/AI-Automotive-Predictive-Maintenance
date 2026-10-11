import { generateMockReport } from "./providers/mock.js";
import { generateGeminiReport } from "./providers/gemini.js";
import { generateAnthropicReport } from "./providers/anthropic.js";

/**
 * Phase 2 - provider-independent LLM layer.
 *
 * The rest of the application calls ONLY this function. It never talks to
 * Gemini/Anthropic/anything directly. Which provider actually runs is decided
 * entirely by the LLM_PROVIDER environment variable:
 *
 *   LLM_PROVIDER=gemini     -> Google Gemini (providers/gemini.js)
 *   LLM_PROVIDER=anthropic  -> Claude          (providers/anthropic.js)
 *   LLM_PROVIDER=mock       -> rule-based template, no network call
 *   (unset / anything else) -> mock, treated as "not configured"
 *
 * Adding a new provider later (e.g. Groq) means: write providers/groq.js
 * exporting an async function with the same (vehicleContext) -> {provider,
 * model, report} contract, add one case below, and set LLM_PROVIDER=groq.
 * Nothing else in the app changes.
 *
 * Every provider failure (missing key, invalid key, network error, malformed
 * JSON, timeout, rate limit, etc.) is caught here, in ONE place, and turned
 * into the same safe fallback - the caller never sees a provider-specific
 * error type, and the app never crashes because an LLM call failed.
 */

const PROVIDERS = {
  gemini: generateGeminiReport,
  anthropic: generateAnthropicReport,
};

export async function generateMaintenanceReport(vehicleContext) {
  if (!vehicleContext || typeof vehicleContext !== "object") {
    return generateMockReport({}, { reason: "Empty or invalid ML context was supplied - nothing to explain." });
  }

  const providerName = (process.env.LLM_PROVIDER || "mock").toLowerCase().trim();

  if (providerName === "mock" || providerName === "") {
    return generateMockReport(vehicleContext);
  }

  const providerFn = PROVIDERS[providerName];
  if (!providerFn) {
    return generateMockReport(vehicleContext, {
      reason: `LLM_PROVIDER="${providerName}" is not a recognised provider (expected one of: ${Object.keys(PROVIDERS).join(", ")}, mock) - falling back to the mock report.`,
    });
  }

  try {
    const { provider, model, report } = await providerFn(vehicleContext);
    return { mode: "live", provider, model, report };
  } catch (err) {
    return {
      ...generateMockReport(vehicleContext),
      mode: "error_fallback",
      provider: providerName,
      note: `LLM call to provider "${providerName}" failed (${err.message}); falling back to template report.`,
    };
  }
}

// Backward-compatible alias - routes/report.js and routes/analyze.js use this name.
export const generateReport = generateMaintenanceReport;
