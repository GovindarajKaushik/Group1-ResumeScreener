import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { StatusBadge } from "./StatusBadge";

const QUICK_TABS = [
  { id: "all", label: "All Candidates", status: "", decision: "" },
  { id: "shortlisted", label: "Shortlisted", status: "", decision: "shortlisted" },
  { id: "pending", label: "Pending Review", status: "", decision: "pending" },
  { id: "rejected", label: "Rejected", status: "", decision: "rejected" },
  { id: "secondary", label: "Final / Secondary Review", status: "SECONDARY_REVIEW", decision: "" },
  { id: "re_entry", label: "Re-Entry", status: "RE_ENTRY", decision: "" },
];

const SKILL_DOT_COLORS = ["#6366f1", "#38bdf8", "#34d399", "#fbbf24", "#fb7185", "#a78bfa"];

function scoreColor(score) {
  if (score === null || score === undefined) return "#64748b";
  if (score >= 75) return "#34d399";
  if (score >= 55) return "#fbbf24";
  return "#fb7185";
}

function SegmentedScoreBar({ label, score, subtitle, color, segmented = true }) {
  const numeric = score !== null && score !== undefined ? Math.max(0, Math.min(100, Number(score))) : null;
  const pctText = numeric !== null ? `${Math.round(numeric)}%` : "N/A";
  const activeSegments = numeric !== null ? Math.round((numeric / 100) * 5) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.42rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontSize: "0.84rem" }}>
        <span style={{ fontWeight: 600 }}>{label}</span>
        <span style={{ fontWeight: 700, color: numeric !== null ? "var(--ra-text-primary)" : "var(--ra-text-muted)" }}>
          {pctText}
        </span>
      </div>

      {!segmented ? (
        <div
          style={{
            height: 8,
            borderRadius: 999,
            background: "rgba(148, 163, 184, 0.14)",
            overflow: "hidden",
          }}
        >
          <div
            className="ra-bar-fill"
            style={{
              width: `${numeric ?? 0}%`,
              height: "100%",
              borderRadius: 999,
              background: color,
            }}
          />
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "5px" }}>
          {[0, 1, 2, 3, 4].map((idx) => (
            <div
              key={idx}
              style={{
                height: 8,
                borderRadius: 4,
                background: idx < activeSegments ? color : "rgba(148, 163, 184, 0.14)",
                transition: "background 280ms ease",
              }}
            />
          ))}
        </div>
      )}

      <div style={{ fontSize: "0.73rem", color: "var(--ra-text-muted)" }}>{subtitle}</div>
    </div>
  );
}

function CandidateAvatar({ candidateId, fileName, highlight = false }) {
  const label = (candidateId || fileName || "C").slice(0, 4).toUpperCase();
  return (
    <div
      style={{
        width: 44,
        height: 44,
        borderRadius: "50%",
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 700,
        fontSize: "0.78rem",
        letterSpacing: "0.02em",
        color: "#f8fafc",
        background: highlight
          ? "linear-gradient(135deg, #6366f1, #38bdf8)"
          : "linear-gradient(135deg, #1e293b, #334155)",
        border: highlight ? "2px solid rgba(129, 140, 248, 0.7)" : "1px solid var(--ra-border-strong)",
      }}
    >
      {label}
    </div>
  );
}

export function CandidatesView({ initialJobId = "", onClearJobFilter }) {
  const [jobs, setJobs] = useState([]);
  const [jobId, setJobId] = useState(initialJobId);
  const [status, setStatus] = useState("");
  const [decision, setDecision] = useState("");
  const [skill, setSkill] = useState("");
  const [keyword, setKeyword] = useState("");
  const [minScore, setMinScore] = useState("");
  const [maxScore, setMaxScore] = useState("");
  const [fastTrackOnly, setFastTrackOnly] = useState(false);
  const [showFilterTray, setShowFilterTray] = useState(false);
  const [sortAsc, setSortAsc] = useState(false);

  const [candidates, setCandidates] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [savingDecisionId, setSavingDecisionId] = useState("");
  const [decisionFeedback, setDecisionFeedback] = useState("");
  const [decisionError, setDecisionError] = useState("");

  useEffect(() => {
    setJobId(initialJobId || "");
  }, [initialJobId]);

  useEffect(() => {
    api
      .listJobs()
      .then((res) => setJobs(res.jobs || []))
      .catch(() => setJobs([]));
  }, []);

  const buildFilterParams = useCallback(
    () => ({
      job_id: jobId,
      status,
      decision,
      skill,
      keyword,
      min_score: minScore,
      max_score: maxScore,
      fast_track: fastTrackOnly ? true : undefined,
    }),
    [jobId, status, decision, skill, keyword, minScore, maxScore, fastTrackOnly],
  );

  const fetchCandidates = useCallback(async (filters) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.listCandidates(filters);
      const rows = res.candidates || [];
      setCandidates(rows);
      setSelectedId((prev) => {
        if (prev && rows.some((c) => c.candidate_id === prev)) {
          return prev;
        }
        return rows[0]?.candidate_id || "";
      });
    } catch (err) {
      setError(err.message || "Failed to load candidates.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchCandidates(buildFilterParams());
    }, 200);
    return () => clearTimeout(timer);
  }, [fetchCandidates, buildFilterParams]);

  const handleReset = () => {
    setJobId("");
    setStatus("");
    setDecision("");
    setSkill("");
    setKeyword("");
    setMinScore("");
    setMaxScore("");
    setFastTrackOnly(false);
    onClearJobFilter?.();
  };

  const handleJobChange = (nextJobId) => {
    setJobId(nextJobId);
    if (!nextJobId) {
      onClearJobFilter?.();
    }
  };

  const selectQuickTab = (tab) => {
    setStatus(tab.status);
    setDecision(tab.decision);
  };

  const activeQuickTab = useMemo(() => {
    const match = QUICK_TABS.find((t) => t.status === status && t.decision === decision);
    return match ? match.id : "";
  }, [status, decision]);

  const sortedCandidates = useMemo(() => {
    const copy = [...candidates];
    copy.sort((a, b) => {
      const sa = a.final_score ?? -1;
      const sb = b.final_score ?? -1;
      return sortAsc ? sa - sb : sb - sa;
    });
    return copy;
  }, [candidates, sortAsc]);

  const selected = sortedCandidates.find((c) => c.candidate_id === selectedId) || null;

  const kpiStats = useMemo(() => {
    const total = sortedCandidates.length;
    const pendingReview = sortedCandidates.filter((c) => (c.recruiter_decision || "pending") === "pending").length;
    const fastTrack = sortedCandidates.filter((c) => c.fast_track).length;
    const scored = sortedCandidates.filter((c) => c.final_score !== null && c.final_score !== undefined);
    const avgScore =
      scored.length > 0
        ? Math.round(scored.reduce((acc, c) => acc + Number(c.final_score), 0) / scored.length)
        : 0;
    return { total, pendingReview, fastTrack, avgScore };
  }, [sortedCandidates]);

  const handleDecision = async (candidate, nextDecision) => {
    if (!candidate || candidate.status === "RE_ENTRY" || candidate.final_score === null) {
      return;
    }
    setSavingDecisionId(`${candidate.candidate_id}:${nextDecision}`);
    setDecisionFeedback("");
    setDecisionError("");
    try {
      const updated = await api.updateDecision(candidate.candidate_id, nextDecision);
      setCandidates((prev) =>
        prev.map((item) => (item.candidate_id === updated.candidate_id ? updated : item)),
      );
      setDecisionFeedback(`Updated ${updated.candidate_id} decision to "${updated.recruiter_decision}".`);
    } catch (err) {
      setDecisionError(err.message || "Could not update decision.");
    } finally {
      setSavingDecisionId("");
    }
  };

  const activeFilterCount = [status, decision, skill, minScore, maxScore, fastTrackOnly ? "ft" : ""].filter(Boolean).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Top Pipeline Toolbar: Quick Tabs + Search, Job Selector, Filter & Sort */}
      <div
        className="ra-card ra-stagger-1"
        style={{ display: "flex", flexDirection: "column", gap: "0.95rem", padding: "1rem 1.25rem" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.75rem",
          }}
        >
          {/* Left Quick Filter Pills */}
          <div
            style={{
              display: "inline-flex",
              flexWrap: "wrap",
              gap: "0.35rem",
              background: "rgba(11, 15, 23, 0.75)",
              padding: "0.3rem",
              borderRadius: "10px",
              border: "1px solid var(--ra-border)",
            }}
          >
            {QUICK_TABS.map((tab) => {
              const active = activeQuickTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => selectQuickTab(tab)}
                  style={{
                    background: active ? "var(--ra-bg-elevated)" : "transparent",
                    color: active ? "var(--ra-text-primary)" : "var(--ra-text-muted)",
                    border: active ? "1px solid var(--ra-border-strong)" : "1px solid transparent",
                    borderRadius: "7px",
                    padding: "0.42rem 0.85rem",
                    fontSize: "0.82rem",
                    fontWeight: active ? 600 : 500,
                    cursor: "pointer",
                    transition: "all 220ms ease",
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Right Search + Job Role + Filter + Sort Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.55rem", flexWrap: "wrap", flex: "1 1 auto", justifyContent: "flex-end" }}>
            <div style={{ minWidth: 210, flex: "0 1 260px" }}>
              <input
                className="ra-input"
                placeholder="Search ID, name, skill, summary..."
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                style={{ padding: "0.48rem 0.75rem", fontSize: "0.84rem" }}
              />
            </div>

            <select
              className="ra-select"
              value={jobId}
              onChange={(e) => handleJobChange(e.target.value)}
              style={{ width: "auto", minWidth: 165, padding: "0.48rem 0.75rem", fontSize: "0.84rem" }}
            >
              <option value="">All Job Postings</option>
              {jobs.map((job) => (
                <option key={job.job_id} value={job.job_id}>
                  {job.title} ({job.job_id})
                </option>
              ))}
            </select>

            <button
              type="button"
              className="ra-btn ra-btn-secondary"
              onClick={() => setShowFilterTray((prev) => !prev)}
              style={{
                padding: "0.48rem 0.85rem",
                fontSize: "0.83rem",
                borderColor: showFilterTray || activeFilterCount > 0 ? "var(--ra-accent-hover)" : undefined,
              }}
            >
              Filter {activeFilterCount > 0 ? `(${activeFilterCount})` : ""}
            </button>

            <button
              type="button"
              className="ra-btn ra-btn-secondary"
              onClick={() => setSortAsc((prev) => !prev)}
              style={{ padding: "0.48rem 0.85rem", fontSize: "0.83rem" }}
            >
              Sort: {sortAsc ? "Low → High" : "High → Low"}
            </button>

            {jobId && (
              <a
                className="ra-btn ra-btn-secondary"
                href={api.jobPdfUrl(jobId)}
                style={{ padding: "0.48rem 0.85rem", fontSize: "0.83rem" }}
              >
                Batch PDF
              </a>
            )}
          </div>
        </div>

        {/* Collapsible Advanced Filter Tray */}
        {showFilterTray && (
          <div
            style={{
              paddingTop: "0.85rem",
              borderTop: "1px solid var(--ra-border)",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(165px, 1fr))",
              gap: "0.75rem",
              alignItems: "end",
            }}
          >
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", color: "var(--ra-text-muted)", marginBottom: "0.28rem" }}>
                System Routing
              </label>
              <select className="ra-select" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">All Statuses</option>
                <option value="SHORTLIST">SHORTLIST</option>
                <option value="SECONDARY_REVIEW">SECONDARY_REVIEW</option>
                <option value="RE_ENTRY">RE_ENTRY</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", color: "var(--ra-text-muted)", marginBottom: "0.28rem" }}>
                Recruiter Decision
              </label>
              <select className="ra-select" value={decision} onChange={(e) => setDecision(e.target.value)}>
                <option value="">All Decisions</option>
                <option value="pending">Pending</option>
                <option value="shortlisted">Shortlisted</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", color: "var(--ra-text-muted)", marginBottom: "0.28rem" }}>
                Required Skills (comma-separated)
              </label>
              <input
                className="ra-input"
                placeholder="e.g. Python, Docker"
                value={skill}
                onChange={(e) => setSkill(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", color: "var(--ra-text-muted)", marginBottom: "0.28rem" }}>
                Min Score
              </label>
              <input
                type="number"
                min="0"
                max="100"
                className="ra-input"
                placeholder="0"
                value={minScore}
                onChange={(e) => setMinScore(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", color: "var(--ra-text-muted)", marginBottom: "0.28rem" }}>
                Max Score
              </label>
              <input
                type="number"
                min="0"
                max="100"
                className="ra-input"
                placeholder="100"
                value={maxScore}
                onChange={(e) => setMaxScore(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
              <label style={{ display: "inline-flex", alignItems: "center", gap: "0.45rem", fontSize: "0.83rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={fastTrackOnly}
                  onChange={(e) => setFastTrackOnly(e.target.checked)}
                  style={{ width: 15, height: 15, accentColor: "var(--ra-accent-primary)" }}
                />
                Fast-Track Only
              </label>
              <button type="button" className="ra-btn ra-btn-secondary" onClick={handleReset} style={{ padding: "0.42rem 0.75rem", fontSize: "0.8rem" }}>
                Reset
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 4 Pipeline Summary KPI Strip Cards */}
      <div className="ra-grid-4 ra-stagger-1">
        <div className="ra-card" style={{ padding: "1rem 1.2rem" }}>
          <div style={{ fontSize: "0.78rem", color: "var(--ra-text-muted)" }}>Total Candidates</div>
          <div style={{ fontSize: "1.65rem", fontWeight: 700, marginTop: "0.3rem" }}>{kpiStats.total}</div>
        </div>
        <div className="ra-card" style={{ padding: "1rem 1.2rem" }}>
          <div style={{ fontSize: "0.78rem", color: "var(--ra-text-muted)" }}>Pending Review</div>
          <div style={{ fontSize: "1.65rem", fontWeight: 700, marginTop: "0.3rem" }}>{kpiStats.pendingReview}</div>
        </div>
        <div className="ra-card" style={{ padding: "1rem 1.2rem" }}>
          <div style={{ fontSize: "0.78rem", color: "var(--ra-text-muted)" }}>Fast-Track Ready</div>
          <div style={{ fontSize: "1.65rem", fontWeight: 700, marginTop: "0.3rem", color: "var(--ra-accent-cyan)" }}>
            {kpiStats.fastTrack}
          </div>
        </div>
        <div className="ra-card" style={{ padding: "1rem 1.2rem" }}>
          <div style={{ fontSize: "0.78rem", color: "var(--ra-text-muted)" }}>AVG. Match Score</div>
          <div style={{ fontSize: "1.65rem", fontWeight: 700, marginTop: "0.3rem", color: "var(--ra-green)" }}>
            {kpiStats.avgScore}%
          </div>
        </div>
      </div>

      {error && (
        <div className="ra-card" style={{ borderColor: "var(--ra-accent-rose)", color: "var(--ra-accent-rose)" }}>
          Error: {error}
        </div>
      )}

      {decisionFeedback && (
        <div className="ra-card" style={{ padding: "0.7rem 1.1rem", borderColor: "rgba(52, 211, 153, 0.4)", color: "var(--ra-green)", fontSize: "0.85rem" }}>
          {decisionFeedback}
        </div>
      )}
      {decisionError && (
        <div className="ra-card" style={{ padding: "0.7rem 1.1rem", borderColor: "var(--ra-accent-rose)", color: "var(--ra-accent-rose)", fontSize: "0.85rem" }}>
          {decisionError}
        </div>
      )}

      {/* Featured Selected Candidate Profile Card */}
      {selected && (
        <div
          className="ra-card ra-stagger-2"
          style={{ display: "flex", flexDirection: "column", gap: "1.25rem", padding: "1.4rem" }}
        >
          {/* Featured Header Row */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.9rem" }}>
              <CandidateAvatar candidateId={selected.candidate_id} fileName={selected.file_name} highlight />
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                  <h3 style={{ margin: 0, fontSize: "1.1rem" }}>{selected.file_name}</h3>
                  <StatusBadge value={selected.status} />
                  {selected.fast_track && <StatusBadge value="FAST_TRACK" label="FAST-TRACK" />}
                  <StatusBadge value={selected.recruiter_decision || "pending"} />
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--ra-text-muted)", marginTop: "0.25rem" }}>
                  {selected.job_title || "Unlinked Role"}
                  {selected.job_id ? ` (${selected.job_id})` : ""} · ID {selected.candidate_id} · Confidence:{" "}
                  <strong style={{ color: "var(--ra-text-primary)" }}>{selected.confidence || "unknown"}</strong>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <a
                className="ra-btn ra-btn-secondary"
                href={api.candidatePdfUrl(selected.candidate_id)}
                target="_blank"
                rel="noreferrer"
              >
                Download Report
              </a>
              <button
                type="button"
                className="ra-btn"
                disabled={
                  selected.status === "RE_ENTRY" ||
                  selected.final_score === null ||
                  selected.recruiter_decision === "shortlisted" ||
                  Boolean(savingDecisionId)
                }
                onClick={() => handleDecision(selected, "shortlisted")}
              >
                {savingDecisionId === `${selected.candidate_id}:shortlisted` ? "Saving..." : "Shortlist"}
              </button>
              <button
                type="button"
                className="ra-btn ra-btn-secondary"
                disabled={
                  selected.status === "RE_ENTRY" ||
                  selected.final_score === null ||
                  selected.recruiter_decision === "rejected" ||
                  Boolean(savingDecisionId)
                }
                onClick={() => handleDecision(selected, "rejected")}
                style={{ borderColor: "rgba(251, 113, 133, 0.45)", color: "#fda4af" }}
              >
                {savingDecisionId === `${selected.candidate_id}:rejected` ? "Saving..." : "Reject"}
              </button>
              {selected.recruiter_decision && selected.recruiter_decision !== "pending" && (
                <button
                  type="button"
                  className="ra-btn ra-btn-secondary"
                  disabled={Boolean(savingDecisionId)}
                  onClick={() => handleDecision(selected, "pending")}
                >
                  Reset Pending
                </button>
              )}
            </div>
          </div>

          {(selected.status === "RE_ENTRY" || selected.final_score === null) && (
            <div style={{ fontSize: "0.8rem", color: "#fcd34d" }}>
              Re-entry or unscored records must be re-screened before a recruiter decision can be recorded.
            </div>
          )}

          {/* 4 Segmented Score Bars Row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "1.2rem",
              padding: "0.95rem 1.1rem",
              borderRadius: "11px",
              background: "rgba(11, 15, 23, 0.55)",
              border: "1px solid var(--ra-border)",
            }}
          >
            <SegmentedScoreBar
              label="Match Score"
              score={selected.final_score}
              subtitle="Compatibility, alignment, relevance"
              color="#6366f1"
              segmented={false}
            />
            <SegmentedScoreBar
              label="Technical Skills (50%)"
              score={selected.skills_score}
              subtitle="Required & preferred skill evidence"
              color="#34d399"
            />
            <SegmentedScoreBar
              label="Experience Depth (30%)"
              score={selected.experience_score}
              subtitle="Years & role responsibility match"
              color="#fbbf24"
            />
            <SegmentedScoreBar
              label="Education & AI Fit (20%)"
              score={selected.education_score}
              subtitle={`Academic match · AI Score: ${selected.ai_overall_score ?? "-"}%`}
              color="#38bdf8"
            />
          </div>

          {/* 3-Column Detail Cards: Screening Metadata | Summary & Evidence | Skills */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "1rem",
            }}
          >
            {/* Card 1: Screening Metadata & Audit Notes */}
            <div
              style={{
                background: "rgba(11, 15, 23, 0.55)",
                border: "1px solid var(--ra-border)",
                borderRadius: "11px",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.6rem",
              }}
            >
              <div style={{ fontSize: "0.84rem", fontWeight: 700, textAlign: "center", paddingBottom: "0.35rem", borderBottom: "1px solid var(--ra-border)" }}>
                Screening Details
              </div>
              <div style={{ fontSize: "0.82rem", display: "flex", flexDirection: "column", gap: "0.45rem" }}>
                <div>
                  <span style={{ color: "var(--ra-text-muted)" }}>Candidate ID:</span>{" "}
                  <strong>{selected.candidate_id}</strong> (Anonymized)
                </div>
                <div>
                  <span style={{ color: "var(--ra-text-muted)" }}>File:</span> {selected.file_name}
                </div>
                <div>
                  <span style={{ color: "var(--ra-text-muted)" }}>Target Role:</span>{" "}
                  {selected.job_title || "Unlinked"}
                </div>
                <div>
                  <span style={{ color: "var(--ra-text-muted)" }}>System Routing:</span> {selected.status}
                </div>
                {selected.notes?.length > 0 && (
                  <div style={{ marginTop: "0.25rem" }}>
                    <div style={{ color: "var(--ra-text-muted)", fontSize: "0.76rem", fontWeight: 600, marginBottom: "0.2rem" }}>
                      Scoring Notes:
                    </div>
                    <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "var(--ra-text-muted)", fontSize: "0.78rem", lineHeight: 1.45 }}>
                      {selected.notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Card 2: Summary & AI Evidence */}
            <div
              style={{
                background: "rgba(11, 15, 23, 0.55)",
                border: "1px solid var(--ra-border)",
                borderRadius: "11px",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.65rem",
              }}
            >
              <div style={{ fontSize: "0.84rem", fontWeight: 700, textAlign: "center", paddingBottom: "0.35rem", borderBottom: "1px solid var(--ra-border)" }}>
                Summary &amp; Evidence
              </div>
              <p style={{ margin: 0, fontSize: "0.83rem", lineHeight: 1.5 }}>
                {selected.summary || "No candidate summary recorded."}
              </p>
              {selected.evidence && (
                <div>
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, marginBottom: "0.2rem", color: "var(--ra-text-muted)" }}>
                    Key Evidence
                  </div>
                  <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--ra-text-muted)", lineHeight: 1.45 }}>
                    {selected.evidence}
                  </p>
                </div>
              )}
            </div>

            {/* Card 3: Skills Pills */}
            <div
              style={{
                background: "rgba(11, 15, 23, 0.55)",
                border: "1px solid var(--ra-border)",
                borderRadius: "11px",
                padding: "1rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.7rem",
              }}
            >
              <div style={{ fontSize: "0.84rem", fontWeight: 700, textAlign: "center", paddingBottom: "0.35rem", borderBottom: "1px solid var(--ra-border)" }}>
                Skills
              </div>

              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.45rem" }}>
                {selected.skills_present?.length ? (
                  selected.skills_present.map((sk, idx) => (
                    <span
                      key={sk}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.4rem",
                        padding: "0.3rem 0.7rem",
                        borderRadius: "999px",
                        fontSize: "0.78rem",
                        fontWeight: 600,
                        background: "rgba(255, 255, 255, 0.05)",
                        border: "1px solid var(--ra-border-strong)",
                      }}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: SKILL_DOT_COLORS[idx % SKILL_DOT_COLORS.length],
                        }}
                      />
                      {sk}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: "0.8rem", color: "var(--ra-text-muted)" }}>No matched skills</span>
                )}
              </div>

              {(selected.missing_must_haves?.length > 0 || selected.skills_missing?.length > 0) && (
                <div>
                  <div style={{ fontSize: "0.74rem", color: "var(--ra-text-muted)", marginBottom: "0.3rem", fontWeight: 600 }}>
                    Missing / Gaps
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                    {(selected.missing_must_haves || selected.skills_missing || []).map((sk) => (
                      <span
                        key={sk}
                        className="ra-badge"
                        style={{
                          background: "rgba(251, 113, 133, 0.12)",
                          borderColor: "rgba(251, 113, 133, 0.35)",
                          color: "#fda4af",
                        }}
                      >
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Candidate Pipeline Horizontal Rows List */}
      <div className="ra-card ra-stagger-3" style={{ padding: "0.5rem 1.1rem" }}>
        {loading ? (
          <p style={{ color: "var(--ra-text-muted)", padding: "1rem 0", margin: 0 }}>
            Loading candidate pipeline...
          </p>
        ) : !sortedCandidates.length ? (
          <p style={{ color: "var(--ra-text-muted)", padding: "1rem 0", margin: 0 }}>
            No candidates match the current filters.
          </p>
        ) : (
          sortedCandidates.map((c, idx) => {
            const isSelected = c.candidate_id === selectedId;
            const numericScore = c.final_score !== null && c.final_score !== undefined ? Math.round(Number(c.final_score)) : null;
            const barColor = scoreColor(numericScore);
            const canDecideRow = c.status !== "RE_ENTRY" && c.final_score !== null;

            return (
              <div
                key={c.candidate_id}
                onClick={() => setSelectedId(c.candidate_id)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(220px, 1.3fr) minmax(200px, 1.2fr) auto",
                  alignItems: "center",
                  gap: "1.25rem",
                  padding: "1rem 0.5rem",
                  borderBottom: idx < sortedCandidates.length - 1 ? "1px solid var(--ra-border)" : "none",
                  cursor: "pointer",
                  background: isSelected ? "rgba(99, 102, 241, 0.08)" : "transparent",
                  borderRadius: "8px",
                  transition: "background 220ms ease",
                }}
              >
                {/* Left: Avatar + Name + Role + Badges */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.85rem", minWidth: 0 }}>
                  <CandidateAvatar candidateId={c.candidate_id} fileName={c.file_name} highlight={isSelected} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", flexWrap: "wrap" }}>
                      <span style={{ fontWeight: 600, fontSize: "0.94rem" }}>{c.file_name}</span>
                      <StatusBadge value={c.recruiter_decision || "pending"} />
                      {c.fast_track && <StatusBadge value="FAST_TRACK" label="FAST-TRACK" />}
                    </div>
                    <div style={{ fontSize: "0.78rem", color: "var(--ra-text-muted)", marginTop: "0.18rem" }}>
                      {c.job_title || "Unlinked Role"} · {c.candidate_id} · {c.status}
                    </div>
                  </div>
                </div>

                {/* Center: Match Score Bar */}
                <div style={{ maxWidth: 340, width: "100%" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "0.3rem" }}>
                    <span style={{ fontWeight: 600 }}>Match Score</span>
                    <span style={{ fontWeight: 700 }}>{numericScore !== null ? `${numericScore}%` : "Unscored"}</span>
                  </div>
                  <div
                    style={{
                      height: 7,
                      borderRadius: 999,
                      background: "rgba(148, 163, 184, 0.14)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      className="ra-bar-fill"
                      style={{
                        width: `${numericScore ?? 0}%`,
                        height: "100%",
                        borderRadius: 999,
                        background: barColor,
                      }}
                    />
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--ra-text-muted)", marginTop: "0.25rem" }}>
                    Compatibility, alignment, relevance
                  </div>
                </div>

                {/* Right: Row Action Buttons */}
                <div
                  style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", justifyContent: "flex-end" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <a
                    className="ra-btn ra-btn-secondary"
                    href={api.candidatePdfUrl(c.candidate_id)}
                    target="_blank"
                    rel="noreferrer"
                    style={{ padding: "0.42rem 0.75rem", fontSize: "0.78rem" }}
                  >
                    Download Report
                  </a>
                  <button
                    type="button"
                    className="ra-btn ra-btn-secondary"
                    disabled={!canDecideRow || c.recruiter_decision === "shortlisted" || Boolean(savingDecisionId)}
                    onClick={() => handleDecision(c, "shortlisted")}
                    style={{ padding: "0.42rem 0.75rem", fontSize: "0.78rem" }}
                  >
                    Shortlist
                  </button>
                  <button
                    type="button"
                    className="ra-btn ra-btn-secondary"
                    onClick={() => setSelectedId(c.candidate_id)}
                    style={{
                      padding: "0.42rem 0.75rem",
                      fontSize: "0.78rem",
                      borderColor: isSelected ? "var(--ra-accent-hover)" : undefined,
                    }}
                  >
                    {isSelected ? "Inspecting" : "••• More"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
