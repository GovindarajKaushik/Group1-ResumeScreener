import { useEffect, useState } from "react";

// Minimal connection check view to verify React (Vite) <-> FastAPI communication
function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const checkBackend = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/health");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach FastAPI");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkBackend();
  }, []);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
      }}
    >
      <section
        style={{
          width: "100%",
          maxWidth: "560px",
          backgroundColor: "#121216",
          border: "1px solid #24242b",
          borderTop: "2px solid #dc2626",
          borderRadius: "14px",
          padding: "1.75rem",
          boxShadow: "0 12px 32px rgba(0, 0, 0, 0.45)",
        }}
      >
        <h1 style={{ margin: "0 0 0.35rem 0", fontSize: "1.65rem" }}>
          Resume <span style={{ color: "#f87171" }}>Analyser</span>
        </h1>
        <p style={{ margin: "0 0 1.25rem 0", color: "#a1a1aa", fontSize: "0.92rem" }}>
          React (Vite) + FastAPI Initialization Check
        </p>

        <div
          style={{
            padding: "1rem",
            borderRadius: "10px",
            backgroundColor: "#09090b",
            border: "1px solid #24242b",
            marginBottom: "1.25rem",
            fontSize: "0.9rem",
          }}
        >
          {loading && <span style={{ color: "#a1a1aa" }}>Connecting to FastAPI backend...</span>}
          {!loading && error && (
            <span style={{ color: "#f87171" }}>
              Backend unreachable: {error}
            </span>
          )}
          {!loading && health && (
            <pre
              style={{
                margin: 0,
                color: "#f4f4f5",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                whiteSpace: "pre-wrap",
              }}
            >
              {JSON.stringify(health, null, 2)}
            </pre>
          )}
        </div>

        <button
          type="button"
          onClick={checkBackend}
          style={{
            backgroundColor: "#991b1b",
            border: "1px solid #dc2626",
            color: "#f4f4f5",
            padding: "0.55rem 1.1rem",
            borderRadius: "9px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Re-test /api/health
        </button>
      </section>
    </main>
  );
}

export default App;
