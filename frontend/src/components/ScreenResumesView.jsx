import { useRef, useState } from "react";
import { api, fileToBase64 } from "../api";
import { StatusBadge } from "./StatusBadge";

const ACCEPTED_EXTS = new Set([".pdf", ".docx", ".zip"]);

function parseSkills(raw) {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function fileExtension(name = "") {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function ScreenResumesView({ onOpenJobCandidates }) {
  const [title, setTitle] = useState("");
  const [requiredRaw, setRequiredRaw] = useState("");
  const [preferredRaw, setPreferredRaw] = useState("");
  const [minExp, setMinExp] = useState("0");
  const [education, setEducation] = useState("");
  const [minScore, setMinScore] = useState("60");
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [rejectedDetails, setRejectedDetails] = useState([]);
  const [result, setResult] = useState(null);

  const addPickedFiles = (rawList, onlyAllowed = false) => {
    const picked = Array.from(rawList || []).filter((f) => {
      if (!onlyAllowed) return true;
      return ACCEPTED_EXTS.has(fileExtension(f.name));
    });
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
  };

  const handleFilePick = (event, onlyAllowed = false) => {
    addPickedFiles(event.target.files, onlyAllowed);
    event.target.value = "";
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    addPickedFiles(event.dataTransfer?.files, true);
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

        <h3 style={{ margin: "0.5rem 0 0", fontSize: "1rem" }}>2. Upload Candidate Resumes (PDF / DOCX / ZIP)</h3>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.zip"
          multiple
          onChange={(e) => handleFilePick(e, false)}
          style={{ display: "none" }}
        />
        <input
          ref={folderInputRef}
          type="file"
          webkitdirectory=""
          directory=""
          multiple
          onChange={(e) => handleFilePick(e, true)}
          style={{ display: "none" }}
        />

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          style={{
            border: isDragging ? "2px dashed #111827" : "1.5px dashed var(--ra-border-strong)",
            background: isDragging ? "rgba(17, 24, 39, 0.04)" : "var(--ra-bg-elevated)",
            borderRadius: "8px",
            padding: "1.4rem 1.25rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
            gap: "0.75rem",
            transition: "border-color 220ms ease, background 220ms ease",
          }}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--ra-text-muted)"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
              Drag &amp; drop resumes or a ZIP batch here
            </div>
            <div style={{ fontSize: "0.78rem", color: "var(--ra-text-muted)", marginTop: "0.2rem" }}>
              Supports multi-select files, entire folders, or .zip archives (.pdf, .docx)
            </div>
          </div>
          <div style={{ display: "flex", gap: "0.55rem", flexWrap: "wrap", justifyContent: "center" }}>
            <button
              type="button"
              className="ra-btn ra-btn-secondary"
              onClick={() => fileInputRef.current?.click()}
            >
              Choose Files
            </button>
            <button
              type="button"
              className="ra-btn ra-btn-secondary"
              onClick={() => folderInputRef.current?.click()}
            >
              Select Folder
            </button>
          </div>
        </div>

        {files.length > 0 && (
          <div
            style={{
              border: "1px solid var(--ra-border)",
              borderRadius: "8px",
              background: "#ffffff",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.6rem 0.9rem",
                background: "var(--ra-bg-elevated)",
                borderBottom: "1px solid var(--ra-border)",
                fontSize: "0.82rem",
              }}
            >
              <span style={{ fontWeight: 600 }}>
                Queued Files ({files.length}) · {formatBytes(files.reduce((sum, f) => sum + (f.size || 0), 0))}
              </span>
              <button
                type="button"
                className="ra-btn ra-btn-secondary"
                onClick={() => setFiles([])}
                style={{ padding: "0.28rem 0.65rem", fontSize: "0.76rem" }}
              >
                Clear All
              </button>
            </div>
            <div style={{ maxHeight: 220, overflowY: "auto" }}>
              {files.map((file, idx) => {
                const ext = fileExtension(file.name).replace(".", "").toUpperCase() || "FILE";
                return (
                  <div
                    key={`${file.name}-${idx}`}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "0.75rem",
                      padding: "0.52rem 0.9rem",
                      borderBottom: idx < files.length - 1 ? "1px solid var(--ra-border)" : "none",
                      fontSize: "0.83rem",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", minWidth: 0 }}>
                      <span
                        className="ra-badge"
                        style={{
                          fontSize: "0.68rem",
                          padding: "0.14rem 0.45rem",
                          background: "var(--ra-bg-elevated)",
                          borderColor: "var(--ra-border-strong)",
                          color: "var(--ra-text-primary)",
                          flexShrink: 0,
                        }}
                      >
                        {ext}
                      </span>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {file.name}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexShrink: 0 }}>
                      <span style={{ fontSize: "0.76rem", color: "var(--ra-text-muted)" }}>
                        {formatBytes(file.size)}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeFile(idx)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--ra-accent-rose)",
                          cursor: "pointer",
                          fontWeight: 700,
                          fontSize: "1rem",
                          lineHeight: 1,
                          padding: "0 0.2rem",
                        }}
                        aria-label={`Remove ${file.name}`}
                      >
                        ×
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
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
