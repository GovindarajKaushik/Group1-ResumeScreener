import { useState } from "react";
import pkg from "../package.json";
import logoImg from "./logo.png";
import { CandidatesView } from "./components/CandidatesView";
import { DashboardView } from "./components/DashboardView";
import { JobPostingsView } from "./components/JobPostingsView";
import { ScreenResumesView } from "./components/ScreenResumesView";

function NavIcon({ id }) {
  const props = {
    width: 16,
    height: 16,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: { flexShrink: 0 },
  };
  if (id === "dashboard") {
    return (
      <svg {...props}>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    );
  }
  if (id === "screen") {
    return (
      <svg {...props}>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <path d="M12 18v-6" />
        <path d="M9 15l3-3 3 3" />
      </svg>
    );
  }
  if (id === "candidates") {
    return (
      <svg {...props}>
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    );
  }
  if (id === "jobs") {
    return (
      <svg {...props}>
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      </svg>
    );
  }
  if (id === "settings") {
    return (
      <svg {...props}>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.79 1 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    );
  }
  if (id === "help") {
    return (
      <svg {...props}>
        <circle cx="12" cy="12" r="10" />
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    );
  }
  return (
    <svg {...props}>
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="M9 12h6" />
      <path d="M9 16h6" />
    </svg>
  );
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "screen", label: "Screen Resumes" },
  { id: "candidates", label: "Candidates & Review" },
  { id: "jobs", label: "Job Postings" },
  { id: "audit", label: "Audit Log" },
];

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [selectedJobFilter, setSelectedJobFilter] = useState("");

  const openJobCandidates = (jobId) => {
    setSelectedJobFilter(jobId);
    setActiveTab("candidates");
  };

  const currentNav = NAV_ITEMS.find((item) => item.id === activeTab) || NAV_ITEMS[0];

  return (
    <div className="ra-shell">
      <aside className="ra-sidebar">
        <div
          className="ra-brand"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.7rem",
          }}
        >
          <img
            src={logoImg}
            alt="Candidate Insight"
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              objectFit: "contain",
              background: "#ffffff",
              padding: "3px",
              flexShrink: 0,
              border: "1px solid var(--ra-border)",
              boxShadow: "0 2px 6px rgba(0, 0, 0, 0.06)",
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem", minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--ra-text-primary)", letterSpacing: "-0.02em" }}>
                ResumeScreenerAI
              </span>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "0.1rem 0.45rem",
                  borderRadius: "999px",
                  fontSize: "0.66rem",
                  fontWeight: 700,
                  background: "rgba(22, 163, 74, 0.14)",
                  border: "1px solid rgba(22, 163, 74, 0.4)",
                  color: "#15803d",
                }}
              >
                v{pkg.version}
              </span>
            </div>
          </div>
        </div>

        <div>
          <div
            style={{
              fontSize: "0.68rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--ra-text-muted)",
              padding: "0 0.35rem 0.45rem",
            }}
          >
            Menu
          </div>
          <nav className="ra-nav">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`ra-nav-btn ${activeTab === item.id ? "active" : ""}`}
                onClick={() => setActiveTab(item.id)}
                style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}
              >
                <NavIcon id={item.id} />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div style={{ marginTop: "auto", paddingTop: "1rem", borderTop: "1px solid var(--ra-border)" }}>
          <nav className="ra-nav">
            <button
              type="button"
              className="ra-nav-btn"
              style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}
            >
              <NavIcon id="settings" />
              <span>Settings</span>
            </button>
            <button
              type="button"
              className="ra-nav-btn"
              style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}
            >
              <NavIcon id="help" />
              <span>Help</span>
            </button>
          </nav>
        </div>
      </aside>

      <div className="ra-main">
        <header className="ra-topbar">
          <h2>{currentNav.label}</h2>
        </header>

        <main key={activeTab} className="ra-content ra-view-enter">
          {activeTab === "dashboard" && <DashboardView onNavigate={setActiveTab} />}
          {activeTab === "screen" && (
            <ScreenResumesView onOpenJobCandidates={openJobCandidates} />
          )}
          {activeTab === "candidates" && (
            <CandidatesView
              initialJobId={selectedJobFilter}
              onClearJobFilter={() => setSelectedJobFilter("")}
            />
          )}
          {activeTab === "jobs" && <JobPostingsView onOpenJobCandidates={openJobCandidates} />}
          {activeTab === "audit" && (
            <div className="ra-card">
              <h3 style={{ marginTop: 0 }}>{currentNav.label}</h3>
              <p style={{ color: "var(--ra-text-muted)", marginBottom: 0 }}>
                View not available yet.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
