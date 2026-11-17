const STYLES = {
  SHORTLIST: { bg: "rgba(22, 163, 74, 0.1)", border: "rgba(22, 163, 74, 0.35)", color: "#15803d" },
  SECONDARY_REVIEW: { bg: "rgba(217, 119, 6, 0.1)", border: "rgba(217, 119, 6, 0.35)", color: "#b45309" },
  RE_ENTRY: { bg: "rgba(220, 38, 38, 0.1)", border: "rgba(220, 38, 38, 0.35)", color: "#b91c1c" },
  shortlisted: { bg: "rgba(22, 163, 74, 0.1)", border: "rgba(22, 163, 74, 0.35)", color: "#15803d" },
  rejected: { bg: "rgba(220, 38, 38, 0.1)", border: "rgba(220, 38, 38, 0.35)", color: "#b91c1c" },
  pending: { bg: "rgba(9, 9, 11, 0.06)", border: "rgba(9, 9, 11, 0.18)", color: "#3f3f46" },
  FAST_TRACK: { bg: "#09090b", border: "#09090b", color: "#ffffff" },
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
