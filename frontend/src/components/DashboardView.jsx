import { useEffect, useState } from "react";
import { api } from "../api";
import { StatusBadge } from "./StatusBadge";

const PIE_COLORS = [
  "#6366f1",
  "#38bdf8",
  "#34d399",
  "#fbbf24",
  "#fb7185",
  "#a78bfa",
  "#2dd4bf",
  "#94a3b8",
];

function SkillsPieChart({ skills }) {
  const [hovered, setHovered] = useState(null);

  if (!skills?.length) {
    return (
      <p style={{ color: "var(--ra-text-muted)", marginBottom: 0 }}>
        No demonstrated skills recorded yet.
      </p>
    );
  }

  const topItems = skills.slice(0, 6);
  const totalMentions = topItems.reduce((sum, item) => sum + item.count, 0) || 1;
  const radius = 58;
  const circumference = 2 * Math.PI * radius;

  let cumulativeOffset = 0;
  const slices = topItems.map((item, idx) => {
    const fraction = item.count / totalMentions;
    const dashLength = fraction * circumference;
    const slice = {
      ...item,
      color: PIE_COLORS[idx % PIE_COLORS.length],
      pct: Math.round(fraction * 100),
      dashArray: `${dashLength} ${circumference - dashLength}`,
      dashOffset: -cumulativeOffset,
    };
    cumulativeOffset += dashLength;
    return slice;
  });

  const activeSlice = hovered !== null ? slices[hovered] : null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "1.5rem", flexWrap: "wrap" }}>
      <div style={{ position: "relative", width: 164, height: 164, flexShrink: 0 }}>
        <svg viewBox="0 0 160 160" width="164" height="164" style={{ transform: "rotate(-90deg)" }}>
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke="rgba(148, 163, 184, 0.1)"
            strokeWidth="22"
          />
          {slices.map((slice, idx) => (
            <circle
              key={slice.skill}
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke={slice.color}
              strokeWidth={hovered === idx ? 26 : 22}
              strokeDasharray={slice.dashArray}
              strokeDashoffset={slice.dashOffset}
              className="ra-donut-slice"
              style={{
                opacity: hovered === null || hovered === idx ? 1 : 0.45,
                animationDelay: `${idx * 110}ms`,
              }}
              onMouseEnter={() => setHovered(idx)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}
        </svg>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
            textAlign: "center",
            padding: "0 1.5rem",
          }}
        >
          <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>
            {activeSlice ? `${activeSlice.pct}%` : totalMentions}
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--ra-text-muted)", lineHeight: 1.2 }}>
            {activeSlice ? activeSlice.skill : "Skill Matches"}
          </div>
        </div>
      </div>

      <div style={{ flex: 1, minWidth: 180, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {slices.map((slice, idx) => (
          <div
            key={slice.skill}
            onMouseEnter={() => setHovered(idx)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0.3rem 0.5rem",
              borderRadius: "7px",
              fontSize: "0.84rem",
              cursor: "pointer",
              background: hovered === idx ? "rgba(255, 255, 255, 0.05)" : "transparent",
              transition: "background 250ms ease",
            }}
          >
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "3px",
                  backgroundColor: slice.color,
                }}
              />
              {slice.skill}
            </span>
            <span style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>
              {slice.count} ({slice.pct}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FunnelMeterRow({ label, count, total, color }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.28rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.84rem" }}>
        <span>{label}</span>
        <span style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>
          {count} <span style={{ opacity: 0.75 }}>({pct}%)</span>
        </span>
      </div>
      <div
        style={{
          height: "7px",
          borderRadius: "999px",
          background: "rgba(11, 15, 23, 0.9)",
          overflow: "hidden",
        }}
      >
        <div
          className="ra-bar-fill"
          style={{
            width: `${pct}%`,
            height: "100%",
            borderRadius: "999px",
            background: color,
          }}
        />
      </div>
    </div>
  );
}

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
    return <div className="ra-card">Loading analytics dashboard...</div>;
  }
  if (error) {
    return (
      <div className="ra-card" style={{ borderColor: "var(--ra-accent-rose)" }}>
        <p style={{ marginTop: 0, color: "var(--ra-accent-rose)" }}>Error: {error}</p>
        <button type="button" className="ra-btn" onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  const total = data.total_candidates || 0;
  const shortlistCount = data.status_counts?.SHORTLIST ?? 0;
  const secondaryCount = data.status_counts?.SECONDARY_REVIEW ?? 0;
  const reEntryCount = data.status_counts?.RE_ENTRY ?? 0;
  const scoredCount = Math.max(0, total - reEntryCount);
  const shortlistRate = scoredCount > 0 ? Math.round((shortlistCount / scoredCount) * 100) : 0;

  const pendingCount = data.decision_counts?.pending ?? 0;
  const humanShortlisted = data.decision_counts?.shortlisted ?? 0;
  const humanRejected = data.decision_counts?.rejected ?? 0;
  const reviewedCount = humanShortlisted + humanRejected;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div className="ra-grid-4">
        <div className="ra-card ra-kpi-card ra-stagger-1" style={{ "--kpi-accent": "#6366f1" }}>
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.8rem", fontWeight: 600 }}>
            Total Screened vs Pending
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: 700, marginTop: "0.35rem" }}>
            {total}{" "}
            <span style={{ fontSize: "0.95rem", fontWeight: 500, color: "var(--ra-amber)" }}>
              / {pendingCount} pending
            </span>
          </div>
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.78rem", marginTop: "0.35rem" }}>
            {reviewedCount} reviewed across {data.total_jobs} saved job(s)
          </div>
        </div>

        <div className="ra-card ra-kpi-card ra-stagger-2" style={{ "--kpi-accent": "#34d399" }}>
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.8rem", fontWeight: 600 }}>
            Shortlist Rate (%)
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: 700, marginTop: "0.35rem", color: "var(--ra-green)" }}>
            {shortlistRate}%
          </div>
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.78rem", marginTop: "0.35rem" }}>
            {shortlistCount}/{scoredCount} system · {humanShortlisted} human shortlisted
          </div>
        </div>

        <div className="ra-card ra-kpi-card ra-stagger-3" style={{ "--kpi-accent": "#38bdf8" }}>
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.8rem", fontWeight: 600 }}>
            Fast-Track Candidates
          </div>
          <div style={{ fontSize: "1.9rem", fontWeight: 700, marginTop: "0.35rem", color: "var(--ra-accent-cyan)" }}>
            {data.fast_track_count}
          </div>
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.78rem", marginTop: "0.35rem" }}>
            Ready for immediate interview scheduling
          </div>
        </div>

        <div
          className="ra-card ra-kpi-card ra-stagger-4"
          style={{ "--kpi-accent": reEntryCount > 0 ? "#fb7185" : "#34d399" }}
        >
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.8rem", fontWeight: 600 }}>
            Failed / Re-Entry Count
          </div>
          <div
            style={{
              fontSize: "1.9rem",
              fontWeight: 700,
              marginTop: "0.35rem",
              color: reEntryCount > 0 ? "var(--ra-accent-rose)" : "var(--ra-green)",
            }}
          >
            {reEntryCount}
          </div>
          <div style={{ color: "var(--ra-text-muted)", fontSize: "0.78rem", marginTop: "0.35rem" }}>
            {reEntryCount > 0 ? "Batch API or parse issues need attention" : "All records processed cleanly"}
          </div>
        </div>
      </div>

      <div className="ra-grid-2">
        <div className="ra-card ra-stagger-2">
          <h3 style={{ marginTop: 0, marginBottom: "1rem", fontSize: "1rem" }}>
            Pipeline Funnel &amp; Human Decisions
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ fontSize: "0.76rem", color: "var(--ra-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                System Routing
              </div>
              <FunnelMeterRow label="Shortlist" count={shortlistCount} total={total} color="#34d399" />
              <FunnelMeterRow label="Secondary Review" count={secondaryCount} total={total} color="#fbbf24" />
              <FunnelMeterRow label="Re-Entry" count={reEntryCount} total={total} color="#fb7185" />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div style={{ fontSize: "0.76rem", color: "var(--ra-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Recruiter Confirmation
              </div>
              <FunnelMeterRow label="Shortlisted" count={humanShortlisted} total={total} color="#38bdf8" />
              <FunnelMeterRow label="Pending Review" count={pendingCount} total={total} color="#94a3b8" />
              <FunnelMeterRow label="Rejected" count={humanRejected} total={total} color="#fb7185" />
            </div>
          </div>
        </div>

        <div className="ra-card ra-stagger-3">
          <h3 style={{ marginTop: 0, marginBottom: "1rem", fontSize: "1rem" }}>
            Top Demonstrated Skills
          </h3>
          <SkillsPieChart skills={data.top_skills} />
        </div>
      </div>

      <div className="ra-card ra-stagger-4">
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
