import { Router } from "express";
import { getHistory, getLatest, getById } from "../db/repositories/vehicleAnalysisRepository.js";

const router = Router();

function handleRepoError(err, res) {
  if (err.code === "DB_UNAVAILABLE") {
    return res.status(503).json({ error: "Database unavailable", detail: err.message });
  }
  if (err.code?.startsWith("INVALID")) {
    return res.status(400).json({ error: "Invalid request", detail: err.message });
  }
  return res.status(500).json({ error: "Unexpected error", detail: err.message });
}

// NOTE ON ROUTE ORDER: the literal "/vehicle/analysis/:id" path is registered
// BEFORE the "/vehicle/:vehicleId/..." param routes below, so a vehicleId can
// never accidentally shadow it (Express matches in registration order, and a
// param segment would otherwise greedily match the literal "analysis" segment).

/** GET /api/vehicle/analysis/:id - a single analysis by its Mongo _id */
router.get("/vehicle/analysis/:id", async (req, res) => {
  try {
    const analysis = await getById(req.params.id);
    if (!analysis) {
      return res.status(404).json({ error: "Analysis not found" });
    }
    res.json(analysis);
  } catch (err) {
    handleRepoError(err, res);
  }
});

/** GET /api/vehicle/:vehicleId/history?limit=20 - newest first */
router.get("/vehicle/:vehicleId/history", async (req, res) => {
  try {
    const history = await getHistory(req.params.vehicleId, { limit: req.query.limit });
    res.json({ vehicleId: req.params.vehicleId, count: history.length, history });
  } catch (err) {
    handleRepoError(err, res);
  }
});

/** GET /api/vehicle/:vehicleId/latest */
router.get("/vehicle/:vehicleId/latest", async (req, res) => {
  try {
    const latest = await getLatest(req.params.vehicleId);
    if (!latest) {
      return res.status(404).json({ error: "No analysis found for this vehicleId" });
    }
    res.json(latest);
  } catch (err) {
    handleRepoError(err, res);
  }
});

export default router;
