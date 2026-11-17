import { useEffect, useState } from "react";
import { api } from "../api";

export function JobPostingsView({ onOpenJobCandidates }) {
  const [jobs, setJobs] = useState([]);
  const [legacyCount, setLegacyCount] = useState(0);
  const [confirmId, setConfirmId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.listJobs();
      setJobs(res.jobs || []);
      setLegacyCount(res.legacy_candidate_count || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (jobId) => {
    setBusyId(jobId);
    setError("");
    try {
      await api.deleteJob(jobId);
      setConfirmId(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ margin: 0, color: "var(--ra-text-muted)", fontSize: "0.9rem" }}>
          Saved job descriptions and linked candidate batches. Deleting a job removes its linked CSV candidates while keeping audit history.
        </p>
        <button type="button" className="ra-btn ra-btn-secondary" onClick={load}>
          Refresh
        </button>
      </div>

      {error && (
        <div className="ra-card" style={{ borderColor: "var(--ra-accent-hover)", color: "var(--ra-accent-rose)" }}>
          {error}
        </div>
      )}

      {legacyCount > 0 && (
        <div className="ra-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>Older results without a job ID ({legacyCount} candidate record(s))</span>
          <button
            type="button"
            className="ra-btn ra-btn-secondary"
            onClick={() => onOpenJobCandidates("")}
          >
            View Older Results
          </button>
        </div>
      )}

      {loading ? (
        <div className="ra-card">Loading saved jobs...</div>
      ) : !jobs.length ? (
        <div className="ra-card" style={{ color: "var(--ra-text-muted)" }}>
          No saved jobs yet. Run a screening batch to create one.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
          {jobs.map((job) => (
            <div key={job.job_id} className="ra-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
                <div>
                  <h3 style={{ margin: "0 0 0.35rem" }}>
                    {job.job_id} — {job.title}
                  </h3>
                  <div style={{ color: "var(--ra-text-muted)", fontSize: "0.84rem" }}>
                    Min Experience: {job.min_experience} yrs · Qualifying Score: {job.min_qualifying_score ?? 60} · Education: {job.education || "Unspecified"}
                  </div>
                  <div style={{ marginTop: "0.5rem", fontSize: "0.86rem" }}>
                    <strong>Required:</strong> {(job.required_skills || []).join(", ") || "None"}
                    {" · "}
                    <strong>Preferred:</strong> {(job.preferred || []).join(", ") || "None"}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="ra-btn ra-btn-secondary"
                    onClick={() => onOpenJobCandidates(job.job_id)}
                  >
                    Candidates ({job.candidate_count})
                  </button>
                  {job.candidate_count > 0 && (
                    <a className="ra-btn ra-btn-secondary" href={api.jobPdfUrl(job.job_id)}>
                      Batch PDF
                    </a>
                  )}
                  {confirmId === job.job_id ? (
                    <>
                      <button
                        type="button"
                        className="ra-btn"
                        disabled={busyId === job.job_id}
                        onClick={() => handleDelete(job.job_id)}
                      >
                        {busyId === job.job_id ? "Deleting..." : "Confirm Delete"}
                      </button>
                      <button
                        type="button"
                        className="ra-btn ra-btn-secondary"
                        onClick={() => setConfirmId(null)}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="ra-btn ra-btn-secondary"
                      onClick={() => setConfirmId(job.job_id)}
                    >
                      Delete Job
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
