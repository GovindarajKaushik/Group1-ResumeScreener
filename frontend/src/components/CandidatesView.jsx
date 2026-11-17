import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../api";
import { StatusBadge } from "./StatusBadge";

const QUICK_TABS = [
  {
    id: "all",
    label: "All Candidates",
    status: "",
    decision: "",
    dot: "#09090b",
    activeBg: "#ffffff",
    activeBorder: "rgba(9, 9, 11, 0.25)",
    activeColor: "#09090b",
  },
  {
    id: "shortlisted",
    label: "Shortlisted",
    status: "",
    decision: "shortlisted",
    dot: "#16a34a",
    activeBg: "rgba(22, 163, 74, 0.12)",
    activeBorder: "rgba(22, 163, 74, 0.45)",
    activeColor: "#15803d",
  },
  {
    id: "pending",
    label: "Pending Review",
    status: "",
    decision: "pending",
    dot: "#d97706",
    activeBg: "rgba(217, 119, 6, 0.12)",
    activeBorder: "rgba(217, 119, 6, 0.45)",
    activeColor: "#b45309",
  },
  {
    id: "rejected",
    label: "Rejected",
    status: "",
    decision: "rejected",
    dot: "#dc2626",
    activeBg: "rgba(220, 38, 38, 0.1)",
    activeBorder: "rgba(220, 38, 38, 0.4)",
    activeColor: "#b91c1c",
  },
  {
    id: "re_entry",
    label: "Re-Entry",
    status: "RE_ENTRY",
    decision: "",
    dot: "#ea580c",
    activeBg: "rgba(234, 88, 12, 0.1)",
    activeBorder: "rgba(234, 88, 12, 0.4)",
    activeColor: "#c2410c",
  },
];

const SKILL_DOT_COLORS = ["#6366f1", "#38bdf8", "#34d399", "#fbbf24", "#fb7185", "#a78bfa"];

const TOAST_THEMES = {
  shortlisted: { bg: "rgba(52, 211, 153, 0.18)", color: "var(--ra-green)", icon: "tick" },
  success: { bg: "rgba(52, 211, 153, 0.18)", color: "var(--ra-green)", icon: "tick" },
  rejected: { bg: "rgba(251, 113, 133, 0.18)", color: "var(--ra-accent-rose)", icon: "cross" },
  error: { bg: "rgba(251, 113, 133, 0.18)", color: "var(--ra-accent-rose)", icon: "cross" },
  pending: { bg: "rgba(251, 191, 36, 0.18)", color: "var(--ra-amber)", icon: "clock" },
  info: { bg: "rgba(56, 189, 248, 0.18)", color: "var(--ra-accent-cyan)", icon: "info" },
};

function scoreColor(score) {
  if (score === null || score === undefined) return "#64748b";
  if (score >= 75) return "#34d399";
  if (score >= 55) return "#fbbf24";
  return "#fb7185";
}

function formatScoreCell(value) {
  if (value === null || value === undefined) return "Not scored";
  return `${value} / 100`;
}

function ScoreBar({ label, score, subtitle, color }) {
  const numeric = score !== null && score !== undefined ? Math.max(0, Math.min(100, Number(score))) : null;
  const pctText = numeric !== null ? `${Math.round(numeric)}%` : "N/A";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.42rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", fontSize: "0.84rem" }}>
        <span style={{ fontWeight: 600 }}>{label}</span>
        <span style={{ fontWeight: 700, color: numeric !== null ? "var(--ra-text-primary)" : "var(--ra-text-muted)" }}>
          {pctText}
        </span>
      </div>

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
        color: highlight ? "#ffffff" : "#09090b",
        background: highlight ? "#09090b" : "#e4e4e7",
        border: highlight ? "2px solid #09090b" : "1px solid var(--ra-border-strong)",
      }}
    >
      {label}
    </div>
  );
}

function CompareSubPage({ candidates, compareIds, onChangeCompareIds, onBack }) {
  const candidateA = candidates.find((c) => c.candidate_id === compareIds[0]) || null;
  const candidateB = candidates.find((c) => c.candidate_id === compareIds[1]) || null;

  const setSlot = (slotIdx, nextId) => {
    const next = [...compareIds];
    next[slotIdx] = nextId;
    onChangeCompareIds(next.filter(Boolean));
  };

  const handleSwap = () => {
    if (compareIds.length === 2) {
      onChangeCompareIds([compareIds[1], compareIds[0]]);
    }
  };

  const sharedSkills = useMemo(() => {
    if (!candidateA || !candidateB) return new Set();
    const setB = new Set((candidateB.skills_present || []).map((s) => s.toLowerCase()));
    return new Set(
      (candidateA.skills_present || [])
        .map((s) => s.toLowerCase())
        .filter((s) => setB.has(s)),
    );
  }, [candidateA, candidateB]);

  const compareNumeric = (valA, valB) => {
    if (valA === null || valA === undefined || valB === null || valB === undefined) {
      return [false, false];
    }
    const na = Number(valA);
    const nb = Number(valB);
    return [na > nb, nb > na];
  };

  const [winFinalA, winFinalB] = compareNumeric(candidateA?.final_score, candidateB?.final_score);
  const [winSkillsA, winSkillsB] = compareNumeric(candidateA?.skills_score, candidateB?.skills_score);
  const [winExpA, winExpB] = compareNumeric(candidateA?.experience_score, candidateB?.experience_score);
  const [winEduA, winEduB] = compareNumeric(candidateA?.education_score, candidateB?.education_score);

  return (
    <div className="ra-card ra-view-enter" style={{ display: "flex", flexDirection: "column", gap: "1.15rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "1.05rem" }}>Side-by-Side Candidate Comparison</h3>
          <div style={{ fontSize: "0.8rem", color: "var(--ra-text-muted)", marginTop: "0.2rem" }}>
            Compare scores, routing status, AI confidence, and skill coverage between two candidates.
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            type="button"
            className="ra-btn ra-btn-secondary"
            disabled={compareIds.length < 2}
            onClick={handleSwap}
            style={{ padding: "0.44rem 0.85rem", fontSize: "0.82rem" }}
          >
            Swap A ↔ B
          </button>
          <button
            type="button"
            className="ra-btn ra-btn-secondary"
            onClick={() => onChangeCompareIds([])}
            style={{ padding: "0.44rem 0.85rem", fontSize: "0.82rem" }}
          >
            Clear
          </button>
          <button
            type="button"
            className="ra-btn"
            onClick={onBack}
            style={{ padding: "0.44rem 0.9rem", fontSize: "0.82rem" }}
          >
            ← Back to Candidate Review
          </button>
        </div>
      </div>

      <div className="ra-grid-2">
        <div>
          <label style={{ display: "block", fontSize: "0.76rem", color: "var(--ra-text-muted)", marginBottom: "0.28rem" }}>
            Candidate A
          </label>
          <select
            className="ra-select"
            value={compareIds[0] || ""}
            onChange={(e) => setSlot(0, e.target.value)}
          >
            <option value="">Select first candidate...</option>
            {candidates.map((c) => (
              <option key={c.candidate_id} value={c.candidate_id} disabled={c.candidate_id === compareIds[1]}>
                {c.candidate_id} — {c.file_name} ({c.final_score !== null ? `${c.final_score}%` : "Unscored"})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.76rem", color: "var(--ra-text-muted)", marginBottom: "0.28rem" }}>
            Candidate B
          </label>
          <select
            className="ra-select"
            value={compareIds[1] || ""}
            onChange={(e) => setSlot(1, e.target.value)}
          >
            <option value="">Select second candidate...</option>
            {candidates.map((c) => (
              <option key={c.candidate_id} value={c.candidate_id} disabled={c.candidate_id === compareIds[0]}>
                {c.candidate_id} — {c.file_name} ({c.final_score !== null ? `${c.final_score}%` : "Unscored"})
              </option>
            ))}
          </select>
        </div>
      </div>

      {!candidateA || !candidateB ? (
        <div
          style={{
            padding: "1.25rem",
            borderRadius: "10px",
            background: "var(--ra-bg-elevated)",
            border: "1px dashed var(--ra-border-strong)",
            color: "var(--ra-text-muted)",
            fontSize: "0.86rem",
          }}
        >
          {candidates.length < 2
            ? "At least 2 candidates are required in the current filter to compare side by side."
            : "Choose Candidate A and Candidate B above to view their side-by-side comparison."}
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="ra-table">
            <thead>
              <tr>
                <th style={{ width: "20%" }}>Field</th>
                <th style={{ width: "40%" }}>
                  {candidateA.candidate_id} · {candidateA.file_name}
                </th>
                <th style={{ width: "40%" }}>
                  {candidateB.candidate_id} · {candidateB.file_name}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Resume</td>
                <td>{candidateA.file_name || "-"}</td>
                <td>{candidateB.file_name || "-"}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Role</td>
                <td>{candidateA.job_title || "-"}</td>
                <td>{candidateB.job_title || "-"}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Final Score</td>
                <td style={{ fontWeight: 700, color: winFinalA ? "var(--ra-green)" : undefined }}>
                  {formatScoreCell(candidateA.final_score)} {winFinalA ? "★" : ""}
                </td>
                <td style={{ fontWeight: 700, color: winFinalB ? "var(--ra-green)" : undefined }}>
                  {formatScoreCell(candidateB.final_score)} {winFinalB ? "★" : ""}
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Recommendation</td>
                <td>
                  <StatusBadge value={candidateA.status} />
                </td>
                <td>
                  <StatusBadge value={candidateB.status} />
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Fast-Track</td>
                <td>
                  {candidateA.fast_track ? <StatusBadge value="FAST_TRACK" label="Yes (FAST-TRACK)" /> : "No"}
                </td>
                <td>
                  {candidateB.fast_track ? <StatusBadge value="FAST_TRACK" label="Yes (FAST-TRACK)" /> : "No"}
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Decision</td>
                <td>
                  <StatusBadge value={candidateA.recruiter_decision || "pending"} />
                </td>
                <td>
                  <StatusBadge value={candidateB.recruiter_decision || "pending"} />
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Skills Score (50%)</td>
                <td style={{ color: winSkillsA ? "var(--ra-green)" : undefined, fontWeight: winSkillsA ? 700 : 400 }}>
                  {formatScoreCell(candidateA.skills_score)}
                </td>
                <td style={{ color: winSkillsB ? "var(--ra-green)" : undefined, fontWeight: winSkillsB ? 700 : 400 }}>
                  {formatScoreCell(candidateB.skills_score)}
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Experience Score (30%)</td>
                <td style={{ color: winExpA ? "var(--ra-green)" : undefined, fontWeight: winExpA ? 700 : 400 }}>
                  {formatScoreCell(candidateA.experience_score)}
                </td>
                <td style={{ color: winExpB ? "var(--ra-green)" : undefined, fontWeight: winExpB ? 700 : 400 }}>
                  {formatScoreCell(candidateB.experience_score)}
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Education Score (20%)</td>
                <td style={{ color: winEduA ? "var(--ra-green)" : undefined, fontWeight: winEduA ? 700 : 400 }}>
                  {formatScoreCell(candidateA.education_score)}
                </td>
                <td style={{ color: winEduB ? "var(--ra-green)" : undefined, fontWeight: winEduB ? 700 : 400 }}>
                  {formatScoreCell(candidateB.education_score)}
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>AI Confidence</td>
                <td>{candidateA.confidence || "-"}</td>
                <td>{candidateB.confidence || "-"}</td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Skills Present</td>
                <td>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                    {candidateA.skills_present?.length ? (
                      candidateA.skills_present.map((sk) => {
                        const isShared = sharedSkills.has(sk.toLowerCase());
                        return (
                          <span
                            key={sk}
                            className="ra-badge"
                            style={{
                              background: isShared ? "rgba(52, 211, 153, 0.16)" : "rgba(99, 102, 241, 0.15)",
                              borderColor: isShared ? "#34d399" : "rgba(129, 140, 248, 0.45)",
                              color: isShared ? "#6ee7b7" : "#c7d2fe",
                            }}
                          >
                            {sk}
                          </span>
                        );
                      })
                    ) : (
                      <span style={{ color: "var(--ra-text-muted)" }}>None</span>
                    )}
                  </div>
                </td>
                <td>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                    {candidateB.skills_present?.length ? (
                      candidateB.skills_present.map((sk) => {
                        const isShared = sharedSkills.has(sk.toLowerCase());
                        return (
                          <span
                            key={sk}
                            className="ra-badge"
                            style={{
                              background: isShared ? "rgba(52, 211, 153, 0.16)" : "rgba(99, 102, 241, 0.15)",
                              borderColor: isShared ? "#34d399" : "rgba(129, 140, 248, 0.45)",
                              color: isShared ? "#6ee7b7" : "#c7d2fe",
                            }}
                          >
                            {sk}
                          </span>
                        );
                      })
                    ) : (
                      <span style={{ color: "var(--ra-text-muted)" }}>None</span>
                    )}
                  </div>
                </td>
              </tr>
              <tr>
                <td style={{ color: "var(--ra-text-muted)", fontWeight: 600 }}>Skills Missing</td>
                <td>{candidateA.skills_missing?.length ? candidateA.skills_missing.join(", ") : "None"}</td>
                <td>{candidateB.skills_missing?.length ? candidateB.skills_missing.join(", ") : "None"}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function CandidatesView({ initialJobId = "", onClearJobFilter }) {
  const [subPage, setSubPage] = useState("pipeline");
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
  const [compareIds, setCompareIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [savingDecisionId, setSavingDecisionId] = useState("");
  const [toasts, setToasts] = useState([]);

  const pushToast = useCallback((message, type = "success") => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 3600);
  }, []);

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  };

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
    pushToast("Filters reset.", "info");
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
    try {
      const updated = await api.updateDecision(candidate.candidate_id, nextDecision);
      setCandidates((prev) =>
        prev.map((item) => (item.candidate_id === updated.candidate_id ? updated : item)),
      );
      const actionLabel =
        updated.recruiter_decision === "shortlisted"
          ? "Shortlisted"
          : updated.recruiter_decision === "rejected"
            ? "Rejected"
            : "Moved back to Pending";
      pushToast(`${actionLabel}: ${updated.candidate_id} (${updated.file_name})`, updated.recruiter_decision || "pending");
    } catch (err) {
      pushToast(err.message || "Could not update decision.", "error");
    } finally {
      setSavingDecisionId("");
    }
  };

  const activeFilterCount = [skill, minScore, maxScore, fastTrackOnly ? "ft" : "", status === "SHORTLIST" ? "s" : ""].filter(Boolean).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Floating Toast Container (portaled to body so view transform doesn't trap fixed positioning) */}
      {toasts.length > 0 &&
        createPortal(
          <div className="ra-toast-container" role="status" aria-live="polite">
            {toasts.map((t) => {
              const theme = TOAST_THEMES[t.type] || TOAST_THEMES.info;
              return (
                <div key={t.id} className={`ra-toast ra-toast-${t.type}`}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
                    <span
                      className="ra-toast-icon"
                      style={{ background: theme.bg, color: theme.color }}
                    >
                      {theme.icon === "tick" && (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <path className="ra-tick-path" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      {theme.icon === "cross" && (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round">
                          <path className="ra-tick-path" d="M18 6L6 18" />
                          <path className="ra-tick-path" d="M6 6l12 12" />
                        </svg>
                      )}
                      {theme.icon === "clock" && (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="9" />
                          <path className="ra-tick-path" d="M12 7v5l3 2" />
                        </svg>
                      )}
                      {theme.icon === "info" && (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round">
                          <path d="M12 16v-4M12 8h.01" />
                        </svg>
                      )}
                    </span>
                    <span>{t.message}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => dismissToast(t.id)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--ra-text-muted)",
                      cursor: "pointer",
                      fontSize: "1rem",
                      lineHeight: 1,
                      padding: "0 0.2rem",
                    }}
                    aria-label="Dismiss notification"
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </div>,
          document.body,
        )}

      {/* Sub-Page Switcher Header (centered) */}
      <div
        className="ra-stagger-1"
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <div />
        <div
          style={{
            display: "inline-flex",
            gap: "0.35rem",
            background: "#ffffff",
            padding: "0.28rem",
            borderRadius: "8px",
            border: "1px solid var(--ra-border)",
            justifySelf: "center",
          }}
        >
          <button
            type="button"
            className={`ra-status-pill ${subPage === "pipeline" ? "active" : ""}`}
            onClick={() => setSubPage("pipeline")}
            style={{
              "--pill-hover-fill": "#111827",
              background: "transparent",
              color: subPage === "pipeline" ? "#111827" : "var(--ra-text-muted)",
              border: "1px solid transparent",
              padding: "0.48rem 1rem",
              fontSize: "0.84rem",
              fontWeight: 600,
            }}
          >
            Candidate Review
          </button>
          <button
            type="button"
            className={`ra-status-pill ${subPage === "compare" ? "active" : ""}`}
            onClick={() => setSubPage("compare")}
            style={{
              "--pill-hover-fill": "#111827",
              background: "transparent",
              color: subPage === "compare" ? "#111827" : "var(--ra-text-muted)",
              border: "1px solid transparent",
              padding: "0.48rem 1rem",
              fontSize: "0.84rem",
              fontWeight: 600,
            }}
          >
            Compare Candidates
          </button>
        </div>

        <div style={{ justifySelf: "end" }}>
          {jobId && (
            <a className="ra-btn ra-btn-secondary" href={api.jobPdfUrl(jobId)}>
              Download Batch PDF ({jobId})
            </a>
          )}
        </div>
      </div>

      {subPage === "compare" ? (
        <CompareSubPage
          candidates={sortedCandidates}
          compareIds={compareIds}
          onChangeCompareIds={setCompareIds}
          onBack={() => setSubPage("pipeline")}
        />
      ) : (
        <>
          {/* Clean Two-Part Search & Filter Bar */}
          <div
            className="ra-card ra-stagger-1"
            style={{ display: "flex", flexDirection: "column", gap: "0.9rem", padding: "1rem 1.25rem" }}
          >
            {/* Row 1: Application Status Pills */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "0.75rem",
              }}
            >
              <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--ra-text-muted)" }}>
                Application Status:
              </span>
              <div
                style={{
                  display: "inline-flex",
                  flexWrap: "wrap",
                  gap: "0.3rem",
                  background: "var(--ra-bg-elevated)",
                  padding: "0.28rem",
                  borderRadius: "8px",
                  border: "1px solid var(--ra-border)",
                }}
              >
                {QUICK_TABS.map((tab) => {
                  const active = activeQuickTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      className={`ra-filter-pill ${active ? "active" : ""}`}
                      onClick={() => selectQuickTab(tab)}
                      style={{
                        "--pill-fill": tab.dot,
                        background: "transparent",
                        color: active ? "#ffffff" : "var(--ra-text-muted)",
                        border: "1px solid transparent",
                        fontWeight: active ? 600 : 500,
                      }}
                    >
                      <span
                        className="ra-status-dot"
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: "50%",
                          backgroundColor: tab.dot,
                          opacity: active ? 1 : 0.65,
                          transition: "background-color 240ms ease",
                        }}
                      />
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Row 2: Search + Job Filter + Filters & Sort */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "0.75rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.55rem", flex: "1 1 340px", minWidth: 260 }}>
                <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--ra-text-muted)", whiteSpace: "nowrap" }}>
                  Search:
                </span>
                <div style={{ position: "relative", flex: 1 }}>
                  <svg
                    width="15"
                    height="15"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--ra-text-muted)"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ position: "absolute", left: "0.8rem", top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
                  >
                    <circle cx="11" cy="11" r="8" />
                    <path d="M21 21l-4.35-4.35" />
                  </svg>
                  <input
                    className="ra-input"
                    placeholder="Search by candidate name, ID, skill, or summary..."
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "0.58rem 0.9rem 0.58rem 2.35rem",
                      fontSize: "0.88rem",
                    }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "0.55rem", flexWrap: "wrap" }}>
                <div style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--ra-text-muted)"
                    strokeWidth="2.1"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ position: "absolute", left: "0.75rem", pointerEvents: "none" }}
                  >
                    <rect x="2" y="7" width="20" height="14" rx="2" />
                    <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
                  </svg>
                  <select
                    className="ra-select"
                    value={jobId}
                    onChange={(e) => handleJobChange(e.target.value)}
                    style={{ width: 215, padding: "0.56rem 0.8rem 0.56rem 2.15rem", fontSize: "0.84rem" }}
                  >
                    <option value="">All Job Postings</option>
                    {jobs.map((job) => (
                      <option key={job.job_id} value={job.job_id}>
                        {job.title} ({job.job_id})
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  className="ra-btn ra-btn-secondary"
                  onClick={() => setShowFilterTray((prev) => !prev)}
                  style={{
                    padding: "0.55rem 0.95rem",
                    fontSize: "0.84rem",
                    borderColor: showFilterTray || activeFilterCount > 0 ? "var(--ra-accent-hover)" : undefined,
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                  </svg>
                  Filters {activeFilterCount > 0 ? `(${activeFilterCount})` : ""}
                </button>

                <button
                  type="button"
                  className="ra-btn ra-btn-secondary"
                  onClick={() => setSortAsc((prev) => !prev)}
                  style={{ padding: "0.55rem 0.95rem", fontSize: "0.84rem" }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M7 15l5 5 5-5" />
                    <path d="M7 9l5-5 5 5" />
                  </svg>
                  Score: {sortAsc ? "Low → High" : "High → Low"}
                </button>
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
                    Skills (comma-separated)
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

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem", paddingBottom: "0.2rem" }}>
                  <label style={{ display: "inline-flex", alignItems: "center", gap: "0.45rem", fontSize: "0.83rem", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={fastTrackOnly}
                      onChange={(e) => setFastTrackOnly(e.target.checked)}
                      style={{ width: 15, height: 15, accentColor: "var(--ra-accent-primary)" }}
                    />
                    Fast-Track Only
                  </label>
                  <button
                    type="button"
                    className="ra-btn ra-btn-secondary"
                    onClick={handleReset}
                    style={{ padding: "0.42rem 0.78rem", fontSize: "0.8rem" }}
                  >
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

          {/* Featured Selected Candidate Profile Card */}
          {selected && (
            <div
              className="ra-card ra-stagger-2"
              style={{ display: "flex", flexDirection: "column", gap: "1.25rem", padding: "1.4rem" }}
            >
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
                    style={{ borderColor: "rgba(220, 38, 38, 0.4)", color: "#b91c1c" }}
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
                <div style={{ fontSize: "0.8rem", color: "#b45309" }}>
                  Re-entry or unscored records must be re-screened before a recruiter decision can be recorded.
                </div>
              )}

              {/* Uniform Continuous Score Bars */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "1.2rem",
                  padding: "0.95rem 1.1rem",
                  borderRadius: "11px",
                  background: "var(--ra-bg-elevated)",
                  border: "1px solid var(--ra-border)",
                }}
              >
                <ScoreBar
                  label="Match Score"
                  score={selected.final_score}
                  subtitle="Compatibility, alignment, relevance"
                  color="#6366f1"
                />
                <ScoreBar
                  label="Technical Skills (50%)"
                  score={selected.skills_score}
                  subtitle="Required & preferred skill evidence"
                  color="#34d399"
                />
                <ScoreBar
                  label="Experience Depth (30%)"
                  score={selected.experience_score}
                  subtitle="Years & role responsibility match"
                  color="#fbbf24"
                />
                <ScoreBar
                  label="Education & AI Fit (20%)"
                  score={selected.education_score}
                  subtitle={`Academic match · AI Score: ${selected.ai_overall_score ?? "-"}%`}
                  color="#38bdf8"
                />
              </div>

              {/* 3-Column Detail Cards */}
              <div className="ra-detail-grid">
                <div
                  style={{
                    background: "var(--ra-bg-elevated)",
                    border: "1px solid var(--ra-border)",
                    borderRadius: "11px",
                    padding: "1.05rem 1.15rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.75rem",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: "var(--ra-text-muted)",
                      paddingBottom: "0.45rem",
                      borderBottom: "1px solid var(--ra-border)",
                    }}
                  >
                    Screening Details
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", fontSize: "0.82rem" }}>
                    {[
                      { label: "Candidate ID", value: selected.candidate_id },
                      { label: "Resume File", value: selected.file_name || "-" },
                      { label: "Target Role", value: selected.job_title || "Unlinked" },
                      { label: "System Routing", value: selected.status || "-" },
                    ].map((row, idx, arr) => (
                      <div
                        key={row.label}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "baseline",
                          gap: "0.75rem",
                          padding: "0.42rem 0",
                          borderBottom: idx < arr.length - 1 ? "1px solid rgba(148, 163, 184, 0.1)" : "none",
                        }}
                      >
                        <span style={{ color: "var(--ra-text-muted)", flexShrink: 0 }}>{row.label}</span>
                        <span style={{ fontWeight: 600, textAlign: "right", wordBreak: "break-word" }}>{row.value}</span>
                      </div>
                    ))}
                  </div>

                  {selected.notes?.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                      <div style={{ color: "var(--ra-text-muted)", fontSize: "0.74rem", fontWeight: 600 }}>
                        Scoring Notes
                      </div>
                      <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--ra-text-muted)", lineHeight: 1.5 }}>
                        {selected.notes.join(" · ")}
                      </p>
                    </div>
                  )}
                </div>

                <div
                  style={{
                    background: "var(--ra-bg-elevated)",
                    border: "1px solid var(--ra-border)",
                    borderRadius: "11px",
                    padding: "1.05rem 1.15rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.75rem",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: "var(--ra-text-muted)",
                      paddingBottom: "0.45rem",
                      borderBottom: "1px solid var(--ra-border)",
                    }}
                  >
                    Summary &amp; Evidence
                  </div>
                  <p style={{ margin: 0, fontSize: "0.84rem", lineHeight: 1.55, color: "var(--ra-text-primary)" }}>
                    {selected.summary || "No candidate summary recorded."}
                  </p>
                  {selected.evidence && (
                    <div>
                      <div style={{ fontSize: "0.74rem", fontWeight: 600, color: "var(--ra-text-muted)", marginBottom: "0.3rem" }}>
                        Key Evidence
                      </div>
                      <ul style={{ margin: 0, paddingLeft: "1.15rem", fontSize: "0.81rem", color: "var(--ra-text-muted)", lineHeight: 1.5 }}>
                        {String(selected.evidence)
                          .split(/(?:\r?\n|;\s*|(?<=\.)\s+)/)
                          .map((item) => item.trim())
                          .filter(Boolean)
                          .map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div
                  style={{
                    background: "var(--ra-bg-elevated)",
                    border: "1px solid var(--ra-border)",
                    borderRadius: "11px",
                    padding: "1.05rem 1.15rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.65rem",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.78rem",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: "var(--ra-text-muted)",
                      paddingBottom: "0.45rem",
                      borderBottom: "1px solid var(--ra-border)",
                    }}
                  >
                    Skills
                  </div>

                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                    {selected.skills_present?.length ? (
                      selected.skills_present.map((sk, idx) => (
                        <span
                          key={sk}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.35rem",
                            padding: "0.22rem 0.55rem",
                            borderRadius: "999px",
                            fontSize: "0.74rem",
                            fontWeight: 600,
                            background: "#ffffff",
                            border: "1px solid var(--ra-border-strong)",
                          }}
                        >
                          <span
                            style={{
                              width: 7,
                              height: 7,
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
                              color: "#b91c1c",
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
                      background: isSelected ? "rgba(9, 9, 11, 0.04)" : "transparent",
                      borderRadius: "8px",
                      transition: "background 220ms ease",
                    }}
                  >
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
        </>
      )}
    </div>
  );
}
