const STYLES = {
  SHORTLIST: { bg: "rgba(34, 197, 94, 0.16)", border: "#22c55e", color: "#86efac" },
  SECONDARY_REVIEW: { bg: "rgba(245, 158, 11, 0.16)", border: "#f59e0b", color: "#fcd34d" },
  RE_ENTRY: { bg: "rgba(239, 68, 68, 0.18)", border: "#ef4444", color: "#fca5a5" },
  shortlisted: { bg: "rgba(34, 197, 94, 0.16)", border: "#22c55e", color: "#86efac" },
  rejected: { bg: "rgba(239, 68, 68, 0.18)", border: "#ef4444", color: "#fca5a5" },
  pending: { bg: "rgba(161, 161, 170, 0.14)", border: "#52525b", color: "#d4d4d8" },
  FAST_TRACK: { bg: "rgba(59, 130, 246, 0.18)", border: "#3b82f6", color: "#93c5fd" },
};

export function StatusBadge({ value, label }) {
  const style = STYLES[value] || STYLES.pending;
  return (
    <span
      className="ra-badge"
      style={{
        backgroundColor: style.bg,
        borderColor: style.border,
        color: style.color,
      }}
    >
      {label || value}
    </span>
  );
}
