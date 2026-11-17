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
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "0.55rem",
          }}
        >
          <div
            style={{
              background: "#ffffff",
              border: "1px solid var(--ra-border)",
              borderRadius: "10px",
              padding: "0.3rem 0.5rem",
              boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flex: "1 1 auto",
              minWidth: 0,
            }}
          >
            <img
              src={logoImg}
              alt="Candidate Insight"
              style={{
                width: "100%",
                maxWidth: "132px",
                height: "44px",
                objectFit: "contain",
                display: "block",
                mixBlendMode: "multiply",
              }}
            />
          </div>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "0.2rem 0.55rem",
              borderRadius: "999px",
              fontSize: "0.7rem",
              fontWeight: 700,
              flexShrink: 0,
              background: "rgba(22, 163, 74, 0.14)",
              border: "1px solid rgba(22, 163, 74, 0.4)",
              color: "#15803d",
            }}
          >
            v{pkg.version}
          </span>
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
