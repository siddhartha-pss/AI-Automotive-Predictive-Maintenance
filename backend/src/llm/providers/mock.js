/**
 * Mock / rule-based provider - no API key, no network call.
 * Used when LLM_PROVIDER=mock, when no provider is configured, and as the
 * fallback body whenever a real provider call fails (see reportGenerator.js).
 */
export function generateMockReport(vehicleContext, { reason } = {}) {
  const anomaly = vehicleContext?.anomaly || {};
  const fault = vehicleContext?.fault || {};
  const behaviour = vehicleContext?.driver_behaviour || {};

  const isAbnormal = anomaly.status === "Abnormal";
  const isLabOnly = fault.input_compatible_with_live_obd2 === false;

  const recommended_actions = [];
  if (isAbnormal) {
    recommended_actions.push("Consider having the vehicle checked by a mechanic soon, especially if the behaviour persists.");
  } else {
    recommended_actions.push("No immediate action needed - continue normal maintenance schedule.");
  }
  if (behaviour.behaviour_profile === "High Intensity") {
    recommended_actions.push("Consider a smoother driving style to reduce long-term wear.");
  }

  return {
    mode: "mock",
    note: reason || "LLM_PROVIDER is not configured (or is set to \"mock\") - this is a rule-based template report, NOT a real LLM response.",
    report: {
      overall_status: isAbnormal ? "Unusual reading detected" : "Normal operation",
      summary: isAbnormal
        ? "The system flagged an unusual reading in the vehicle's recent data. This does not confirm a fault by itself."
        : "The vehicle's recent data looks consistent with normal operation.",
      anomaly_explanation: isAbnormal
        ? `An anomaly was detected (method: ${anomaly.method || "unknown"}).`
        : "No anomaly detected in the analysed data.",
      fault_explanation: (fault.predicted_fault || fault.predicted_fault_class) !== undefined
        ? `The fault-classification model's best guess is "${fault.predicted_fault || fault.predicted_fault_class}" ` +
          `(confidence: ${fault.confidence !== null && fault.confidence !== undefined ? Math.round(fault.confidence * 100) + "%" : "unknown"}). ` +
          "This is a probable classification from a trained model, not a confirmed diagnosis." +
          (isLabOnly ? " It is trained on laboratory engine data and is NOT a confirmed live OBD-II diagnosis." : "") +
          (fault.scope_limitation ? ` ${fault.scope_limitation}` : "")
        : "No fault prediction available.",
      driver_behaviour_explanation: behaviour.behaviour_profile
        ? `Recent driving has been classified as "${behaviour.behaviour_profile}" based on speed, RPM, and braking patterns.`
        : "No driver-behaviour profile available.",
      recommended_actions,
      severity: isAbnormal ? "Moderate" : "Low",
      limitations: "This is a template report generated without an LLM call - treat it as a placeholder. " +
        (isLabOnly ? "The fault result is from lab-induced data, not a real in-service vehicle. " : "") +
        "No history is stored between requests.",
    },
  };
}
