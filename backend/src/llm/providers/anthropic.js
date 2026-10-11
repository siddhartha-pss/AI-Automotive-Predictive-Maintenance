import Anthropic from "@anthropic-ai/sdk";
import { SYSTEM_PROMPT, buildUserMessage } from "../prompt.js";

/**
 * Anthropic provider (Claude). Retained from the original single-provider
 * implementation - same model choice and reasoning as before (see
 * documentation/phase2_llm_integration.md), now just one option among several.
 *
 * Throws on any failure - the orchestrator (reportGenerator.js) is responsible
 * for catching and falling back to the mock provider.
 */
export async function generateAnthropicReport(vehicleContext) {
  const apiKey = process.env.ANTHROPIC_API_KEY?.trim();
  if (!apiKey) {
    throw new Error("ANTHROPIC_API_KEY is not set");
  }

  const client = new Anthropic({ apiKey });
  const model = process.env.ANTHROPIC_MODEL || "claude-haiku-4-5";

  const response = await client.messages.create({
    model,
    max_tokens: 1024,
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: buildUserMessage(vehicleContext) }],
  });

  const textBlock = response.content.find((b) => b.type === "text");
  if (!textBlock) {
    throw new Error("Anthropic response contained no text block");
  }

  let parsed;
  try {
    parsed = JSON.parse(textBlock.text);
  } catch {
    throw new Error("Anthropic response was not valid JSON: " + textBlock.text.slice(0, 200));
  }

  return { provider: "anthropic", model, report: parsed };
}
