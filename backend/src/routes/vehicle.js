import { Router } from "express";

const router = Router();

/**
 * GET /api/vehicle/sample
 * Returns the sample combined vehicle-health context produced by Phase 1
 * (src/combined_inference.py) so the frontend has something real to render
 * before the FastAPI ML service is wired up live in Phase 3.
 */
router.get("/vehicle/sample", async (req, res) => {
  try {
    const fs = await import("fs/promises");
    const path = await import("path");
    const { fileURLToPath } = await import("url");
    const __dirname = path.dirname(fileURLToPath(import.meta.url));
    const samplePath = path.join(__dirname, "../../../outputs/sample_combined_vehicle_context.json");
    const data = await fs.readFile(samplePath, "utf-8");
    res.json(JSON.parse(data));
  } catch (err) {
    res.status(404).json({ error: "Sample vehicle context not found. Run src/combined_inference.py first.", detail: err.message });
  }
});

export default router;
