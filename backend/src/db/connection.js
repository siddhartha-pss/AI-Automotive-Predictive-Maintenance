import mongoose from "mongoose";

/**
 * MongoDB connection layer.
 *
 * Design goals (see documentation/mongodb_implementation_plan.md):
 * - Connect once at startup, not per-request.
 * - Never crash the backend if MongoDB is unavailable - the ML/LLM pipeline
 *   must keep working even with no database. Every route that touches the DB
 *   checks isConnected() first and degrades gracefully instead of throwing.
 * - Expose a simple status string for the health endpoint.
 * - Shut down cleanly on process exit.
 */

let connectionState = "disconnected"; // "disconnected" | "connecting" | "connected" | "error"
let lastError = null;

export async function connectDB() {
  const uri = process.env.MONGODB_URI;
  if (!uri) {
    connectionState = "disconnected";
    lastError = "MONGODB_URI is not set";
    console.log("MongoDB: MONGODB_URI not set - persistence/history features disabled, rest of the app continues normally.");
    return;
  }

  connectionState = "connecting";
  try {
    await mongoose.connect(uri, {
      dbName: process.env.MONGODB_DB_NAME || "predictive_maintenance",
      serverSelectionTimeoutMS: 5000,
    });
    connectionState = "connected";
    lastError = null;
    console.log(`MongoDB: connected (db: ${process.env.MONGODB_DB_NAME || "predictive_maintenance"})`);
  } catch (err) {
    connectionState = "error";
    lastError = err.message;
    console.log(`MongoDB: connection failed (${err.message}) - persistence/history features disabled, rest of the app continues normally.`);
  }

  // The MongoDB driver retries dropped connections automatically in the
  // background - these listeners keep our reported status in sync with that,
  // instead of latching on the first disconnect forever (a real bug found by
  // actually stopping and restarting the MongoDB container during testing).
  mongoose.connection.on("disconnected", () => {
    connectionState = "disconnected";
  });
  mongoose.connection.on("reconnected", () => {
    connectionState = "connected";
    lastError = null;
  });
  mongoose.connection.on("connected", () => {
    connectionState = "connected";
    lastError = null;
  });
  mongoose.connection.on("error", (err) => {
    connectionState = "error";
    lastError = err.message;
  });
}

export function isConnected() {
  return connectionState === "connected" && mongoose.connection.readyState === 1;
}

export function getStatus() {
  return { state: connectionState, error: lastError };
}

export async function disconnectDB() {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.connection.close();
  }
  connectionState = "disconnected";
}
