from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class CandidateReport:
    def __init__(self, candidate):
        self.candidate = candidate

    def to_markdown(self):
        candidate = self.candidate
        score = candidate.get("final_score")
        score_text = "Unscored"
        if score is not None and score >= 0:
            score_text = f"{score:.1f} / 100"

        lines = [
            "# Resume Screening Report",
            "",
            f"- Candidate ID: {candidate['candidate_id']}",
            f"- Resume: {candidate['file_name']}",
            f"- Job: {candidate.get('job_title') or 'Unspecified'}",
            f"- Final score: {score_text}",
            f"- Screening status: {candidate.get('status') or 'Unavailable'}",
            f"- AI confidence: {candidate.get('confidence') or 'Unavailable'}",
            f"- Recruiter decision: {candidate.get('recruiter_decision') or 'Pending'}",
        ]

        for field, heading in (
            ("summary", "Summary"),
            ("skills_present", "Skills found"),
            ("skills_missing", "Skills missing"),
            ("missing_must_haves", "Missing required skills"),
            ("evidence", "Evidence from the resume"),
            ("notes", "Screening notes"),
        ):
            value = candidate.get(field)
            if isinstance(value, list):
                value = "\n".join(f"- {item}" for item in value)

            lines.extend(["", f"## {heading}", "", value or "None recorded."])

        return "\n".join(lines) + "\n"

    def to_pdf(self):
        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, title="Resume Screening Report")
        styles = getSampleStyleSheet()
        content = []

        for line in self.to_markdown().splitlines():
            if line.startswith("# "):
                content.append(Paragraph(escape(line[2:]), styles["Title"]))
            elif line.startswith("## "):
                content.append(Paragraph(escape(line[3:]), styles["Heading2"]))
            elif line.startswith("- "):
                content.append(
                    Paragraph(escape(line[2:]), styles["Bullet"], bulletText="•")
                )
            elif line:
                content.append(Paragraph(escape(line), styles["BodyText"]))
            else:
                content.append(Spacer(1, 6))

        document.build(content)
        return buffer.getvalue()