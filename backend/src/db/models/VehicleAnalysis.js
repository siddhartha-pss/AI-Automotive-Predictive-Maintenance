import mongoose from "mongoose";

/**
 * Wraps the EXISTING combined-output and LLM-report shapes unchanged (see
 * documentation/mongodb_implementation_plan.md section 4) rather than
 * inventing a new flattened schema. `vehicleContext` and `llmReport` are
 * stored as loosely-typed sub-documents (Mixed) because their exact inner
 * shape is owned by combined_inference.py / the LLM providers, not by this
 * schema - duplicating every nested field here would mean this file silently
 * drifting out of sync with the Python side. `vehicleId` and `timestamp` are
 * promoted top-level fields purely for indexing/querying.
 */
const VehicleAnalysisSchema = new mongoose.Schema({
  vehicleId: {
    type: String,
    required: true,
    trim: true,
    minlength: 1,
    maxlength: 128,
  },
  timestamp: {
    type: Date,
    required: true,
    default: Date.now,
  },
  vehicleContext: {
    type: mongoose.Schema.Types.Mixed,
    required: true,
    validate: {
      validator: (v) => v && typeof v === "object" && !Array.isArray(v),
      message: "vehicleContext must be a non-array object",
    },
  },
  llmReport: {
    type: mongoose.Schema.Types.Mixed,
    required: true,
    validate: {
      validator: (v) => v && typeof v === "object" && !Array.isArray(v),
      message: "llmReport must be a non-array object",
    },
  },
  metadata: {
    savedAt: { type: Date, default: Date.now },
    source: { type: String, default: "api/analyze", maxlength: 64 },
  },
}, {
  // Caps how large a single stored analysis can be, as a basic defence
  // against an accidentally huge payload (the task explicitly asks for this).
  strict: true,
});

VehicleAnalysisSchema.index({ vehicleId: 1, timestamp: -1 });

export const VehicleAnalysis = mongoose.model("VehicleAnalysis", VehicleAnalysisSchema, "vehicle_analyses");
