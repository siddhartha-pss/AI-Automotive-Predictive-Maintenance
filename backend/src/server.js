import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import reportRoutes from "./routes/report.js";
import vehicleRoutes from "./routes/vehicle.js";
import analyzeRoutes from "./routes/analyze.js";
import historyRoutes from "./routes/history.js";
import { connectDB, disconnectDB, getStatus } from "./db/connection.js";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const REQUIRED_KEY_ENV_VAR = { gemini: "GEMINI_API_KEY", anthropic: "ANTHROPIC_API_KEY" };

function describeLlmConfig() {
  const provider = (process.env.LLM_PROVIDER || "mock").toLowerCase().trim();
  if (provider === "mock" || provider === "") return "mock (LLM_PROVIDER not set or set to mock)";

  const keyVar = REQUIRED_KEY_ENV_VAR[provider];
  if (!keyVar) return `mock (LLM_PROVIDER="${provider}" is not a recognised provider)`;
  if (!process.env[keyVar]?.trim()) return `mock (LLM_PROVIDER=${provider} but ${keyVar} is not set)`;
  return `live (provider: ${provider})`;
}

app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    llm_mode: describeLlmConfig(),
    database: getStatus(),
  });
});

app.use("/api", reportRoutes);
app.use("/api", vehicleRoutes);
app.use("/api", analyzeRoutes);
app.use("/api", historyRoutes);

const PORT = process.env.PORT || 5000;

async function start() {
  await connectDB(); // never throws - degrades to DB-disabled mode on failure, see db/connection.js
  app.listen(PORT, () => {
    console.log(`Backend listening on http://localhost:${PORT}`);
    console.log(`LLM mode: ${describeLlmConfig()}`);
    console.log(`Database: ${JSON.stringify(getStatus())}`);
  });
}

start();

process.on("SIGINT", async () => {
  await disconnectDB();
  process.exit(0);
});
process.on("SIGTERM", async () => {
  await disconnectDB();
  process.exit(0);
});
