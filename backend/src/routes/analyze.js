import { Router } from "express";
import { generateReport } from "../llm/reportGenerator.js";
import { saveAnalysis } from "../db/repositories/vehicleAnalysisRepository.js";

const router = Router();

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || "http://localhost:8000";

/**
 * POST /api/analyze
 * The full Phase 1 -> Phase 2 chain in one call:
 *   request body (raw sensor-style inputs)
 *     -> FastAPI ML service (/predict/combined) for the 3 ML results
 *     -> LLM report generator
 *     -> structured response with both the ML context and the plain-language report
 */
router.post("/analyze", async (req, res) => {
  try {
    const mlResponse = await fetch(`${ML_SERVICE_URL}/predict/combined`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });

    if (!mlResponse.ok) {
      const detail = await mlResponse.text();
      return res.status(502).json({ error: "ML service error", detail });
    }

    const vehicleContext = await mlResponse.json();
    const reportResult = await generateReport(vehicleContext);

    // Persist the completed analysis. MongoDB being unavailable must never
    // fail the request - the ML/LLM result the user asked for was already
    // produced successfully; persistence is reported alongside it, not instead of it.
    let persistence;
    try {
      const saved = await saveAnalysis(vehicleContext, reportResult, { source: "api/analyze" });
      persistence = { saved: true, id: saved.id, timestamp: saved.timestamp };
    } catch (err) {
      persistence = { saved: false, reason: err.message };
    }

    res.json({ vehicle_context: vehicleContext, llm_report: reportResult, persistence });
  } catch (err) {
    res.status(500).json({
      error: "Analyze pipeline failed",
      detail: err.message,
      hint: "Is the FastAPI ML service running on " + ML_SERVICE_URL + "?",
    });
  }
});

export default router;
