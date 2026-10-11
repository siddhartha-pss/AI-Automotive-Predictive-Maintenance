import { VehicleAnalysis } from "../models/VehicleAnalysis.js";
import { isConnected } from "../connection.js";

const MAX_PAYLOAD_BYTES = 256 * 1024; // 256KB - generous for this JSON shape, rejects anything pathological
const VEHICLE_ID_PATTERN = /^[a-zA-Z0-9_-]{1,128}$/;

function assertConnected() {
  if (!isConnected()) {
    const err = new Error("MongoDB is not connected - analysis was not persisted.");
    err.code = "DB_UNAVAILABLE";
    throw err;
  }
}

/** Basic shape/size validation before anything touches MongoDB - never trust the raw request body. */
function validateForSave(vehicleContext, llmReport) {
  if (!vehicleContext || typeof vehicleContext !== "object" || Array.isArray(vehicleContext)) {
    throw Object.assign(new Error("vehicleContext must be an object"), { code: "INVALID_INPUT" });
  }
  const vehicleId = vehicleContext?.vehicle_meta?.vehicle_id;
  if (!vehicleId || typeof vehicleId !== "string" || !VEHICLE_ID_PATTERN.test(vehicleId)) {
    throw Object.assign(
      new Error("vehicleContext.vehicle_meta.vehicle_id must be a non-empty string matching [a-zA-Z0-9_-]{1,128}"),
      { code: "INVALID_VEHICLE_ID" }
    );
  }
  if (!llmReport || typeof llmReport !== "object" || Array.isArray(llmReport)) {
    throw Object.assign(new Error("llmReport must be an object"), { code: "INVALID_INPUT" });
  }
  const size = Buffer.byteLength(JSON.stringify({ vehicleContext, llmReport }), "utf-8");
  if (size > MAX_PAYLOAD_BYTES) {
    throw Object.assign(new Error(`Analysis payload too large (${size} bytes > ${MAX_PAYLOAD_BYTES} limit)`), { code: "PAYLOAD_TOO_LARGE" });
  }
  return vehicleId;
}

/** Saves a complete analysis. Throws DB_UNAVAILABLE/INVALID_* - callers decide how to degrade (see routes/analyze.js). */
export async function saveAnalysis(vehicleContext, llmReport, { source = "api/analyze" } = {}) {
  assertConnected();
  const vehicleId = validateForSave(vehicleContext, llmReport);

  const doc = await VehicleAnalysis.create({
    vehicleId,
    timestamp: new Date(), // backend-authoritative, never taken from the request
    vehicleContext,
    llmReport,
    metadata: { savedAt: new Date(), source },
  });

  return { id: doc._id.toString(), vehicleId, timestamp: doc.timestamp };
}

export async function getHistory(vehicleId, { limit = 20 } = {}) {
  assertConnected();
  if (!VEHICLE_ID_PATTERN.test(vehicleId || "")) {
    throw Object.assign(new Error("Invalid vehicleId"), { code: "INVALID_VEHICLE_ID" });
  }
  const safeLimit = Math.min(Math.max(parseInt(limit, 10) || 20, 1), 100);

  const docs = await VehicleAnalysis.find({ vehicleId })
    .sort({ timestamp: -1 })
    .limit(safeLimit)
    .lean();

  return docs.map(formatDoc);
}

export async function getLatest(vehicleId) {
  assertConnected();
  if (!VEHICLE_ID_PATTERN.test(vehicleId || "")) {
    throw Object.assign(new Error("Invalid vehicleId"), { code: "INVALID_VEHICLE_ID" });
  }
  const doc = await VehicleAnalysis.findOne({ vehicleId }).sort({ timestamp: -1 }).lean();
  return doc ? formatDoc(doc) : null;
}

export async function getById(id) {
  assertConnected();
  if (!/^[a-f0-9]{24}$/i.test(id || "")) {
    throw Object.assign(new Error("Invalid analysis id"), { code: "INVALID_ID" });
  }
  const doc = await VehicleAnalysis.findById(id).lean();
  return doc ? formatDoc(doc) : null;
}

/** Strips raw MongoDB internals (__v, etc.) before returning to the API layer. */
function formatDoc(doc) {
  return {
    id: doc._id.toString(),
    vehicleId: doc.vehicleId,
    timestamp: doc.timestamp,
    vehicleContext: doc.vehicleContext,
    llmReport: doc.llmReport,
    metadata: doc.metadata,
  };
}
