import { useState, useEffect, Fragment } from "react";
import "./App.css";

const API_BASE = "http://localhost:5000/api";

function StatCard({ label, value, tone = "neutral" }) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

const DEFAULT_VEHICLE_ID = "demo-vehicle-01"; // matches outputs/sample_combined_vehicle_context.json

export default function App() {
  const [context, setContext] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [llmMode, setLlmMode] = useState(null);
  const [dbStatus, setDbStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => r.json())
      .then((d) => {
        setLlmMode(d.llm_mode);
        setDbStatus(d.database);
      })
      .catch(() => setLlmMode("unreachable"));
    loadHistory(DEFAULT_VEHICLE_ID);
  }, []);

  async function loadHistory(vehicleId) {
    setHistoryError(null);
    try {
      const res = await fetch(`${API_BASE}/vehicle/${vehicleId}/history?limit=20`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `History request failed (${res.status})`);
      }
      const data = await res.json();
      setHistory(data.history || []);
    } catch (e) {
      setHistoryError(e.message);
    }
  }

  async function loadSample() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/vehicle/sample`);
      if (!res.ok) throw new Error("No sample context found. Run src/combined_inference.py first.");
      const data = await res.json();
      setContext(data);

      const reportRes = await fetch(`${API_BASE}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const reportData = await reportRes.json();
      setReport(reportData);

      // The analysis was just (attempted to be) saved server-side - refresh history
      // to show it. loadHistory tolerates persistence.saved === false gracefully
      // (it will just show whatever was already there).
      await loadHistory(data?.vehicle_meta?.vehicle_id || DEFAULT_VEHICLE_ID);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  const anomalyTone = context?.anomaly?.status === "Abnormal" ? "warning" : "good";
  const behaviourTone =
    context?.driver_behaviour?.behaviour_profile === "High Intensity" ? "warning" : "good";

  return (
    <div className="app">
      <header className="top-bar">
        <h1>Vehicle Health Dashboard</h1>
        <div className="badges">
          <span className={`llm-badge ${llmMode?.startsWith("live") ? "live" : "mock"}`}>
            LLM: {llmMode || "checking..."}
          </span>
          <span className={`llm-badge ${dbStatus?.state === "connected" ? "live" : "mock"}`}>
            DB: {dbStatus?.state || "checking..."}
          </span>
        </div>
      </header>

      <div className="controls">
        <button onClick={loadSample} disabled={loading}>
          {loading ? "Loading..." : "Load Sample Vehicle Analysis"}
        </button>
        {error && <p className="error">{error}</p>}
      </div>

      {context && (
        <>
          <Section title="Vehicle Overview">
            <div className="stat-grid">
              <StatCard label="Vehicle ID" value={context.vehicle_meta?.vehicle_id || "—"} />
              <StatCard
                label="Anomaly Status"
                value={context.anomaly?.status}
                tone={anomalyTone}
              />
              <StatCard
                label="Driving Profile"
                value={context.driver_behaviour?.behaviour_profile}
                tone={behaviourTone}
              />
            </div>
          </Section>

          <Section title="Anomaly Detection">
            <p>Status: <strong>{context.anomaly?.status}</strong></p>
            <p>Method: {context.anomaly?.method}</p>
            <p className="muted">
              Unsupervised one-class model (no real fault labels exist in the training
              data — see documentation for why this approach was chosen).
            </p>
          </Section>

          <Section title="Fault Classification">
            <p>Predicted Fault: <strong>{context.fault?.predicted_fault || context.fault?.predicted_fault_class}</strong></p>
            <p>Model: {context.fault?.method}</p>
            <p>
              Confidence:{" "}
              {context.fault?.confidence != null
                ? `${Math.round(context.fault.confidence * 100)}%`
                : "—"}
            </p>
            <p>
              OBD-II Compatible:{" "}
              <strong>{context.fault?.input_compatible_with_live_obd2 ? "Yes" : "No"}</strong>
            </p>
            <p className="muted">{context.fault?.note}</p>
            <p className="warning-text">
              This is an ML-based fault classification from OBD-II-compatible parameters
              (estimated probability, not a diagnostic certainty) and should not be treated
              as a definitive mechanical diagnosis.
              {context.fault?.scope_limitation ? ` ${context.fault.scope_limitation}` : ""}
            </p>
            {context.fault?.input_compatible_with_live_obd2 === false && (
              <p className="warning-text">
                Note: this model needs lab-grade exhaust-gas inputs, not available from a
                standard OBD-II connection. See the limitation noted in the Phase 1 report.
              </p>
            )}
          </Section>

          <Section title="Driver Behaviour">
            <p>Profile: <strong>{context.driver_behaviour?.behaviour_profile}</strong></p>
            <p className="muted">
              This is unsupervised clustering over engineered driving-style features, not a
              predictive classifier — there is no ground-truth driving-style label to predict.
            </p>
          </Section>

          {report && (
            <Section title="Maintenance Report">
              {report.mode !== "live" && (
                <p className="warning-text">{report.note}</p>
              )}
              <div className="report-grid">
                {Object.entries(report.report || {}).map(([key, value]) => (
                  <div key={key} className="report-item">
                    <div className="report-key">{key.replaceAll("_", " ")}</div>
                    <div className="report-value">
                      {Array.isArray(value) ? (
                        <ul>
                          {value.map((item, i) => <li key={i}>{item}</li>)}
                        </ul>
                      ) : (
                        value
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </>
      )}

      <Section title="Vehicle Analysis History">
        {historyError && <p className="error">{historyError}</p>}
        {!historyError && history.length === 0 && (
          <p className="muted">No saved analyses yet. Click "Load Sample Vehicle Analysis" above to generate and save one.</p>
        )}
        {history.length > 0 && (
          <table className="history-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Anomaly</th>
                <th>Fault</th>
                <th>Driver Behaviour</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => {
                const isOpen = expandedId === h.id;
                const vc = h.vehicleContext || {};
                return (
                  <Fragment key={h.id}>
                    <tr
                      className="history-row"
                      onClick={() => setExpandedId(isOpen ? null : h.id)}
                    >
                      <td>{formatDate(h.timestamp)}</td>
                      <td>{vc.anomaly?.status || "—"}</td>
                      <td>{vc.fault?.predicted_fault || "—"}</td>
                      <td>{vc.driver_behaviour?.behaviour_profile || "—"}</td>
                    </tr>
                    {isOpen && (
                      <tr key={`${h.id}-detail`} className="history-detail-row">
                        <td colSpan={4}>
                          <div className="history-detail">
                            <p><strong>Anomaly:</strong> {vc.anomaly?.status} ({vc.anomaly?.method})</p>
                            <p><strong>Fault:</strong> {vc.fault?.predicted_fault} - confidence{" "}
                              {vc.fault?.confidence != null ? `${Math.round(vc.fault.confidence * 100)}%` : "—"}</p>
                            <p><strong>Driver Behaviour:</strong> {vc.driver_behaviour?.behaviour_profile}</p>
                            <p><strong>Maintenance Report ({h.llmReport?.mode}):</strong>{" "}
                              {h.llmReport?.report?.summary || "—"}</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  );
}
