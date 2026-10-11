import { Router } from "express";
import { generateReport } from "../llm/reportGenerator.js";
import { saveAnalysis } from "../db/repositories/vehicleAnalysisRepository.js";

const router = Router();

/**
 * POST /api/report
 * Body: a structured vehicle-health context, exactly the shape produced by
 * src/combined_inference.py (anomaly, fault, driver_behaviour, vehicle_meta).
 * This route does not run any ML itself - it only calls the LLM step.
 * Phase 3 wires this up to the FastAPI ML service so the context is produced
 * automatically instead of being passed in by hand.
 */
router.post("/report", async (req, res) => {
  const vehicleContext = req.body;

  if (!vehicleContext || typeof vehicleContext !== "object") {
    return res.status(400).json({ error: "Request body must be a vehicle-health context JSON object." });
  }

  try {
    const result = await generateReport(vehicleContext);

    let persistence;
    try {
      const saved = await saveAnalysis(vehicleContext, result, { source: "api/report" });
      persistence = { saved: true, id: saved.id, timestamp: saved.timestamp };
    } catch (err) {
      persistence = { saved: false, reason: err.message };
    }

    res.json({ ...result, persistence });
  } catch (err) {
    res.status(500).json({ error: "Report generation failed", detail: err.message });
  }
});

export default router;
