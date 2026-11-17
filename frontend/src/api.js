// Centralized REST API client talking to OOP/api_server.py (/api/*)

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }

  if (!response.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || `Request failed (HTTP ${response.status})`;
    const error = new Error(message);
    error.details = detail;
    throw error;
  }
  return data;
}

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const commaIdx = result.indexOf(",");
      resolve(commaIdx >= 0 ? result.slice(commaIdx + 1) : result);
    };
    reader.onerror = () => reject(new Error(`Failed to read '${file.name}'.`));
    reader.readAsDataURL(file);
  });
}

export const api = {
  getHealth: () => requestJson("/api/health"),
  getDashboard: () => requestJson("/api/dashboard"),
  listJobs: () => requestJson("/api/jobs"),
  deleteJob: (jobId) =>
    requestJson(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" }),
  screenResumes: (payload) =>
    requestJson("/api/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  listCandidates: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).trim() !== "") {
        qs.set(k, String(v).trim());
      }
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return requestJson(`/api/candidates${suffix}`);
  },
  updateDecision: (candidateId, decision) =>
    requestJson(`/api/candidates/${encodeURIComponent(candidateId)}/decision`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    }),
  listAudit: () => requestJson("/api/audit"),
  candidatePdfUrl: (candidateId) =>
    `/api/candidates/${encodeURIComponent(candidateId)}/report.pdf`,
  jobPdfUrl: (jobId) =>
    `/api/jobs/${encodeURIComponent(jobId)}/report.pdf`,
};
