import { useEffect, useState } from "react";
import { api } from "./api";
import { DashboardView } from "./components/DashboardView";
import { JobPostingsView } from "./components/JobPostingsView";
import { ScreenResumesView } from "./components/ScreenResumesView";

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
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");

  useEffect(() => {
    api
      .getHealth()
      .then((data) => {
        setHealth(data);
        setHealthError("");
      })
      .catch((err) => {
        setHealth(null);
        setHealthError(err.message || "Backend unreachable");
      });
  }, []);

  const openJobCandidates = (jobId) => {
    setSelectedJobFilter(jobId);
    setActiveTab("candidates");
  };

  const currentNav = NAV_ITEMS.find((item) => item.id === activeTab) || NAV_ITEMS[0];

  return (
    <div className="ra-shell">
      <aside className="ra-sidebar">
        <div className="ra-brand">
          <h1>
            Resume <span>Analyser</span>
          </h1>
          <p>OOP Screener Console</p>
        </div>

        <nav className="ra-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`ra-nav-btn ${activeTab === item.id ? "active" : ""}`}
              onClick={() => setActiveTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="ra-main">
        <header className="ra-topbar">
          <h2>{currentNav.label}</h2>
          <div className="ra-pill">
            <span
              className="ra-dot"
              style={{
                backgroundColor: healthError
                  ? "var(--ra-accent-rose)"
                  : health?.ai_connected
                    ? "var(--ra-green)"
                    : "var(--ra-amber)",
              }}
            />
            {healthError
              ? `Offline: ${healthError}`
              : health
                ? `Backend OK · ${health.ai_connected ? "OpenRouter Ready" : "No API Key"}`
                : "Checking backend..."}
          </div>
        </header>

        <main className="ra-content">
          {activeTab === "dashboard" && <DashboardView onNavigate={setActiveTab} />}
          {activeTab === "screen" && (
            <ScreenResumesView onOpenJobCandidates={openJobCandidates} />
          )}
          {activeTab === "jobs" && <JobPostingsView onOpenJobCandidates={openJobCandidates} />}
          {activeTab !== "dashboard" && activeTab !== "screen" && activeTab !== "jobs" && (
            <div className="ra-card">
              <h3 style={{ marginTop: 0 }}>{currentNav.label}</h3>
              <p style={{ color: "var(--ra-text-muted)", marginBottom: 0 }}>
                {selectedJobFilter && activeTab === "candidates"
                  ? `Filtered to job ${selectedJobFilter} — `
                  : ""}
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
