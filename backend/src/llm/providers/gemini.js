import { GoogleGenAI } from "@google/genai";
import { SYSTEM_PROMPT, buildUserMessage, RESPONSE_JSON_SCHEMA } from "../prompt.js";

/**
 * Gemini provider (Google), using the current official unified SDK
 * (@google/genai - the actively maintained package; the older
 * @google/generative-ai package is legacy and was not used for new code).
 *
 * Uses Gemini's structured-output mode (responseMimeType + responseSchema) so
 * the model is constrained to return valid JSON matching our shared schema,
 * instead of relying on prompt instructions alone.
 *
 * Throws on any failure - the orchestrator (reportGenerator.js) is responsible
 * for catching and falling back to the mock provider.
 */
export async function generateGeminiReport(vehicleContext) {
  const apiKey = process.env.GEMINI_API_KEY?.trim();
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not set");
  }

  const ai = new GoogleGenAI({ apiKey });
  // "gemini-flash-latest" returned 503 (overloaded) and "gemini-2.5-flash" returned
  // 404 (deprecated for new users, API itself recommended this replacement) when
  // tested live - gemini-3.8-flash is the model actually confirmed working.
  const model = process.env.GEMINI_MODEL || "gemini-3.8-flash";

  const response = await ai.models.generateContent({
    model,
    systemInstruction: SYSTEM_PROMPT,
    contents: buildUserMessage(vehicleContext),
    config: {
      responseMimeType: "application/json",
      responseSchema: RESPONSE_JSON_SCHEMA,
    },
  });

  const text = response.text;
  if (!text) {
    throw new Error("Gemini response contained no text output");
  }

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("Gemini response was not valid JSON: " + text.slice(0, 200));
  }

  return { provider: "gemini", model, report: parsed };
}
