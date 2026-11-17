import { useState } from "react";
import { api, fileToBase64 } from "../api";
import { StatusBadge } from "./StatusBadge";

function parseSkills(raw) {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function ScreenResumesView({ onOpenJobCandidates }) {
  const [title, setTitle] = useState("");
  const [requiredRaw, setRequiredRaw] = useState("");
  const [preferredRaw, setPreferredRaw] = useState("");
  const [minExp, setMinExp] = useState("0");
  const [education, setEducation] = useState("");
  const [minScore, setMinScore] = useState("60");
  const [files, setFiles] = useState([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [rejectedDetails, setRejectedDetails] = useState([]);
  const [result, setResult] = useState(null);

  const handleFilePick = (event) => {
    const picked = Array.from(event.target.files || []);
    if (!picked.length) return;
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => `${f.name}:${f.size}`));
      const next = [...prev];
      picked.forEach((f) => {
        if (!existing.has(`${f.name}:${f.size}`)) {
          next.push(f);
        }
      });
      return next;
    });
    event.target.value = "";
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setRejectedDetails([]);
    setResult(null);

    const requiredSkills = parseSkills(requiredRaw);
    const preferred = parseSkills(preferredRaw);
    if (!title.trim()) {
      setError("Job title cannot be empty.");
      return;
    }
    if (!requiredSkills.length && !preferred.length) {
      setError("Enter at least one required or preferred skill.");
      return;
    }
    if (!files.length) {
      setError("Select at least one PDF or DOCX resume.");
      return;
    }

    setSubmitting(true);
    try {
      const encodedFiles = await Promise.all(
        files.map(async (file) => ({
          file_name: file.name,
          content_base64: await fileToBase64(file),
        }))
      );

      const res = await api.screenResumes({
        title: title.trim(),
        required_skills: requiredSkills,
        preferred,
        min_experience: Number(minExp) || 0,
        education: education.trim(),
        min_qualifying_score: minScore === "" ? 60 : Number(minScore),
        files: encodedFiles,
      });
      setResult(res);
      setRejectedDetails(res.rejected_files || []);
    } catch (err) {
      setError(err.message || "Screening failed.");
      if (err.details?.rejected_files) {
        setRejectedDetails(err.details.rejected_files);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <form className="ra-card" onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <h3 style={{ margin: 0, fontSize: "1rem" }}>1. Job Requirements &amp; Screening Threshold</h3>

        <div className="ra-grid-2">
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--ra-text-muted)", marginBottom: "0.35rem" }}>
              Job Title *
            </label>
            <input
              className="ra-input"
              placeholder="e.g. Senior Data Engineer"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--ra-text-muted)", marginBottom: "0.35rem" }}>
              Education Requirement
            </label>
            <input
              className="ra-input"
              placeholder="e.g. Bachelor's degree in Computer Science"
              value={education}
              onChange={(e) => setEducation(e.target.value)}
            />
          </div>
        </div>

        <div className="ra-grid-2">
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--ra-text-muted)", marginBottom: "0.35rem" }}>
              Required Skills (comma-separated) *
            </label>
            <input
              className="ra-input"
              placeholder="e.g. Python, SQL, Apache Airflow"
              value={requiredRaw}
              onChange={(e) => setRequiredRaw(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--ra-text-muted)", marginBottom: "0.35rem" }}>
              Preferred Skills (comma-separated)
            </label>
            <input
              className="ra-input"
              placeholder="e.g. AWS, Docker"
              value={preferredRaw}
              onChange={(e) => setPreferredRaw(e.target.value)}
            />
          </div>
        </div>

        <div className="ra-grid-2">
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--ra-text-muted)", marginBottom: "0.35rem" }}>
              Minimum Years of Experience
            </label>
            <input
              type="number"
              min="0"
              step="0.5"
              className="ra-input"
              value={minExp}
              onChange={(e) => setMinExp(e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: "var(--ra-text-muted)", marginBottom: "0.35rem" }}>
              Minimum Qualifying Score (0–100, default 60)
            </label>
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              className="ra-input"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
            />
          </div>
        </div>

        <h3 style={{ margin: "0.5rem 0 0", fontSize: "1rem" }}>2. Upload Candidate Resumes (PDF / DOCX)</h3>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          <input
            type="file"
            accept=".pdf,.docx"
            multiple
            onChange={handleFilePick}
            style={{ color: "var(--ra-text-muted)" }}
          />
          {files.length > 0 && (
            <button type="button" className="ra-btn ra-btn-secondary" onClick={() => setFiles([])}>
              Clear All ({files.length})
            </button>
          )}
        </div>

        {files.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {files.map((file, idx) => (
              <span
                key={`${file.name}-${idx}`}
                className="ra-badge"
                style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", padding: "0.3rem 0.65rem" }}
              >
                {file.name}
                <button
                  type="button"
                  onClick={() => removeFile(idx)}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--ra-accent-rose)",
                    cursor: "pointer",
                    fontWeight: 700,
                    padding: 0,
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        <div>
          <button type="submit" className="ra-btn" disabled={submitting}>
            {submitting ? "Screening Resumes via OpenRouter..." : "Run AI Screening Batch"}
          </button>
        </div>
      </form>

      {error && (
        <div className="ra-card" style={{ borderColor: "var(--ra-accent-hover)", color: "var(--ra-accent-rose)" }}>
          {error}
        </div>
      )}

      {rejectedDetails.length > 0 && (
        <div className="ra-card" style={{ borderColor: "var(--ra-amber)" }}>
          <h4 style={{ margin: "0 0 0.5rem", color: "#fcd34d" }}>Rejected / Skipped Files</h4>
          <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.88rem" }}>
            {rejectedDetails.map((item, idx) => (
              <li key={idx}>
                <strong>{item.file_name}:</strong> {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result && (
        <div className="ra-card" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
            <div>
              <h3 style={{ margin: 0 }}>
                Screening Complete — {result.job_id}: {result.job?.title}
              </h3>
              <p style={{ margin: "0.25rem 0 0", color: "var(--ra-text-muted)", fontSize: "0.86rem" }}>
                Saved {result.saved_candidates?.length || 0} candidate record(s) to CSV &amp; audit log.
              </p>
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <a className="ra-btn ra-btn-secondary" href={api.jobPdfUrl(result.job_id)}>
                Download Batch PDF
              </a>
              <button
                type="button"
                className="ra-btn"
                onClick={() => onOpenJobCandidates(result.job_id)}
              >
                Review &amp; Decide in Candidates
              </button>
            </div>
          </div>

          {result.debug_warning && (
            <div style={{ color: "#fcd34d", fontSize: "0.86rem" }}>
              Warning: {result.debug_warning}
            </div>
          )}

          <table className="ra-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Resume</th>
                <th>Final Score</th>
                <th>Skills / Exp / Edu</th>
                <th>Status</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {(result.saved_candidates || []).map((c) => (
                <tr key={c.candidate_id}>
                  <td>{c.candidate_id}</td>
                  <td>{c.file_name}</td>
                  <td>{c.final_score !== null ? `${c.final_score} / 100` : "Unscored"}</td>
                  <td style={{ fontSize: "0.82rem", color: "var(--ra-text-muted)" }}>
                    {c.skills_score ?? "-"} / {c.experience_score ?? "-"} / {c.education_score ?? "-"}
                  </td>
                  <td>
                    <StatusBadge value={c.status} />{" "}
                    {c.fast_track && <StatusBadge value="FAST_TRACK" label="FAST-TRACK" />}
                  </td>
                  <td style={{ fontSize: "0.82rem", color: "var(--ra-text-muted)" }}>
                    {(c.notes || []).slice(0, 2).join(" · ") || "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
