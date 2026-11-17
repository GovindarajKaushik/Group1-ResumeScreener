import { useEffect, useState } from "react";
import { api } from "../api";
import { StatusBadge } from "./StatusBadge";

export function DashboardView({ onNavigate }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setData(await api.getDashboard());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return <div className="ra-card">Loading dashboard metrics...</div>;
  }
  if (error) {
    return (
      <div className="ra-card" style={{ borderColor: "var(--ra-accent-hover)" }}>
        <p style={{ marginTop: 0, color: "var(--ra-accent-rose)" }}>Error: {error}</p>
        <button type="button" className="ra-btn" onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  const maxSkillCount = Math.max(1, ...(data?.top_skills || []).map((s) => s.count));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="ra-grid-4">
        <div className="ra-card">
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.82rem" }}>Total Candidates</div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, marginTop: "0.35rem" }}>
            {data.total_candidates}
          </div>
        </div>
        <div className="ra-card">
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.82rem" }}>Recommended Shortlist</div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, marginTop: "0.35rem", color: "#86efac" }}>
            {data.status_counts?.SHORTLIST ?? 0}
          </div>
        </div>
        <div className="ra-card">
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.82rem" }}>Fast-Track Qualified</div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, marginTop: "0.35rem", color: "#93c5fd" }}>
            {data.fast_track_count}
          </div>
        </div>
        <div className="ra-card">
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.82rem" }}>Saved Jobs</div>
          <div style={{ fontSize: "1.85rem", fontWeight: 700, marginTop: "0.35rem" }}>
            {data.total_jobs}
          </div>
        </div>
      </div>

      <div className="ra-grid-2">
        <div className="ra-card">
          <h3 style={{ marginTop: 0, fontSize: "1rem" }}>Status &amp; Recruiter Decisions</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.65rem", marginBottom: "1rem" }}>
            <StatusBadge value="SHORTLIST" label={`Shortlist: ${data.status_counts?.SHORTLIST ?? 0}`} />
            <StatusBadge
              value="SECONDARY_REVIEW"
              label={`Secondary Review: ${data.status_counts?.SECONDARY_REVIEW ?? 0}`}
            />
            <StatusBadge value="RE_ENTRY" label={`Re-entry: ${data.status_counts?.RE_ENTRY ?? 0}`} />
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.65rem" }}>
            <StatusBadge value="shortlisted" label={`Recruiter Shortlisted: ${data.decision_counts?.shortlisted ?? 0}`} />
            <StatusBadge value="pending" label={`Pending: ${data.decision_counts?.pending ?? 0}`} />
            <StatusBadge value="rejected" label={`Rejected: ${data.decision_counts?.rejected ?? 0}`} />
          </div>
        </div>

        <div className="ra-card">
          <h3 style={{ marginTop: 0, fontSize: "1rem" }}>Top Demonstrated Skills</h3>
          {!data.top_skills?.length ? (
            <p style={{ color: "var(--ra-text-muted)", marginBottom: 0 }}>No skills recorded yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
              {data.top_skills.map((item) => (
                <div key={item.skill}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.84rem", marginBottom: "0.2rem" }}>
                    <span>{item.skill}</span>
                    <span style={{ color: "var(--ra-text-muted)" }}>{item.count}</span>
                  </div>
                  <div style={{ height: "6px", background: "var(--ra-bg-canvas)", borderRadius: "999px", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${Math.round((item.count / maxSkillCount) * 100)}%`,
                        height: "100%",
                        background: "linear-gradient(90deg, var(--ra-accent-primary), var(--ra-accent-cyan))",
                        transition: "width 450ms cubic-bezier(0.16, 1, 0.3, 1)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="ra-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>Recent Screened Candidates</h3>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button type="button" className="ra-btn ra-btn-secondary" onClick={load}>
              Refresh
            </button>
            <button type="button" className="ra-btn" onClick={() => onNavigate("screen")}>
              + New Screening
            </button>
          </div>
        </div>

        {!data.recent_candidates?.length ? (
          <p style={{ color: "var(--ra-text-muted)", marginBottom: 0 }}>
            No candidates screened yet. Go to Screen Resumes to start a batch.
          </p>
        ) : (
          <table className="ra-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Resume</th>
                <th>Role</th>
                <th>Score</th>
                <th>Status</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_candidates.map((c) => (
                <tr key={c.candidate_id}>
                  <td>{c.candidate_id}</td>
                  <td>{c.file_name}</td>
                  <td>{c.job_title || "-"}</td>
                  <td>{c.final_score !== null ? `${c.final_score} / 100` : "Unscored"}</td>
                  <td>
                    <StatusBadge value={c.status} />{" "}
                    {c.fast_track && <StatusBadge value="FAST_TRACK" label="FAST-TRACK" />}
                  </td>
                  <td>
                    <StatusBadge value={c.recruiter_decision || "pending"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
