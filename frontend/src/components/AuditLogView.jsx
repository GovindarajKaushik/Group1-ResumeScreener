import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

const ACTION_STYLES = {
  CREATE_JOB: { bg: "rgba(37, 99, 235, 0.1)", border: "rgba(37, 99, 235, 0.35)", color: "#1d4ed8" },
  DELETE_JOB: { bg: "rgba(220, 38, 38, 0.1)", border: "rgba(220, 38, 38, 0.35)", color: "#b91c1c" },
  SAVE_RESULT: { bg: "rgba(22, 163, 74, 0.1)", border: "rgba(22, 163, 74, 0.35)", color: "#15803d" },
  UPDATE_RESULT: { bg: "rgba(8, 145, 178, 0.1)", border: "rgba(8, 145, 178, 0.35)", color: "#0e7490" },
  RECRUITER_DECISION: { bg: "rgba(217, 119, 6, 0.12)", border: "rgba(217, 119, 6, 0.4)", color: "#b45309" },
  FEEDBACK: { bg: "rgba(17, 24, 39, 0.08)", border: "rgba(17, 24, 39, 0.25)", color: "#111827" },
};

function formatUtcTimestamp(raw) {
  if (!raw) return "Not provided";
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return String(raw);
  }
  return parsed.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}

function escapeCsvCell(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function downloadAuditCsv(rows) {
  const header = ["timestamp", "action", "target_id", "details"];
  const lines = [
    header.join(","),
    ...rows.map((entry) =>
      [entry.timestamp, entry.action, entry.candidate_id, entry.details]
        .map(escapeCsvCell)
        .join(","),
    ),
  ];
  const blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const dateStamp = new Date().toISOString().slice(0, 10);
  link.href = url;
  link.download = `audit_log_${dateStamp}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function AuditLogView() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [search, setSearch] = useState("");

  const fetchAudit = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError("");
    try {
      const res = await api.listAudit();
      setEntries(res.entries || []);
    } catch (err) {
      setError(err.message || "Failed to load audit log.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAudit(false);
  }, []);

  const actionTypes = useMemo(() => {
    return Array.from(new Set(entries.map((e) => e.action).filter(Boolean))).sort();
  }, [entries]);

  const filteredEntries = useMemo(() => {
    const q = search.trim().toLowerCase();
    return entries.filter((entry) => {
      if (actionFilter && entry.action !== actionFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      const haystack = [
        entry.timestamp,
        entry.action,
        entry.candidate_id,
        entry.details,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [entries, actionFilter, search]);

  if (loading && !entries.length) {
    return <div className="ra-card">Loading audit log...</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div
        className="ra-card ra-stagger-1"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>
            Audit Trail ({filteredEntries.length} {filteredEntries.length === 1 ? "event" : "events"})
          </h3>
          <div style={{ fontSize: "0.8rem", color: "var(--ra-text-muted)", marginTop: "0.2rem" }}>
            UTC chronological record of screening runs, job actions, and recruiter decisions.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
          <input
            className="ra-input"
            placeholder="Search candidate ID, action, details..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 250, padding: "0.48rem 0.78rem", fontSize: "0.84rem" }}
          />

          <select
            className="ra-select"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            style={{ width: 195, padding: "0.48rem 0.78rem", fontSize: "0.84rem" }}
          >
            <option value="">All Actions</option>
            {actionTypes.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>

          <button
            type="button"
            className="ra-btn ra-btn-secondary"
            disabled={!filteredEntries.length}
            onClick={() => downloadAuditCsv(filteredEntries)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export CSV
          </button>

          <button
            type="button"
            className="ra-btn ra-btn-secondary"
            disabled={refreshing}
            onClick={() => fetchAudit(true)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div className="ra-card" style={{ borderColor: "var(--ra-accent-rose)", color: "var(--ra-accent-rose)" }}>
          Error: {error}
        </div>
      )}

      <div className="ra-card ra-stagger-2" style={{ padding: "0.5rem 1.25rem" }}>
        {!filteredEntries.length ? (
          <p style={{ color: "var(--ra-text-muted)", padding: "1rem 0", margin: 0 }}>
            {entries.length === 0
              ? "No audit events recorded yet."
              : "No audit events match your current filter."}
          </p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="ra-table">
              <thead>
                <tr>
                  <th style={{ width: "200px" }}>Timestamp (UTC)</th>
                  <th style={{ width: "180px" }}>Action</th>
                  <th style={{ width: "150px" }}>Target ID</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((entry, idx) => {
                  const badgeStyle = ACTION_STYLES[entry.action] || {
                    bg: "var(--ra-bg-elevated)",
                    border: "var(--ra-border-strong)",
                    color: "var(--ra-text-primary)",
                  };
                  return (
                    <tr key={`${entry.timestamp}-${entry.action}-${idx}`}>
                      <td style={{ whiteSpace: "nowrap", fontSize: "0.82rem", color: "var(--ra-text-muted)" }}>
                        {formatUtcTimestamp(entry.timestamp)}
                      </td>
                      <td>
                        <span
                          className="ra-badge"
                          style={{
                            backgroundColor: badgeStyle.bg,
                            borderColor: badgeStyle.border,
                            color: badgeStyle.color,
                          }}
                        >
                          {entry.action || "EVENT"}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600, fontSize: "0.84rem" }}>
                        {entry.candidate_id || "—"}
                      </td>
                      <td style={{ fontSize: "0.85rem", color: "var(--ra-text-primary)" }}>
                        {entry.details || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
