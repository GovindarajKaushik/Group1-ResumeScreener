# Page view classes and reusable dashboard widgets for the Streamlit UI

from abc import ABC, abstractmethod
from datetime import datetime
import math
import os
import streamlit as st

from OOP.candidate_report import CandidateReport
from OOP.data_manager import ScreeningStore, StorageError


# Shared dashboard/analytics card and SVG chart components
class OverviewWidgets:

    @staticmethod
    def extract_initials(file_name: str) -> str:
        # build 2-letter uppercase initials from a resume filename
        stem = os.path.splitext(os.path.basename(file_name))[0]
        parts = [p for p in stem.replace("-", "_").split("_") if p and p.lower() != "resume"]
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        if parts:
            return parts[0][:2].upper()
        return "CA"

    def get_top_skills_data(self) -> list[tuple[str, int]]:
        # aggregate detected skills from current session evaluations or fall back to realistic demo counts
        evaluations = st.session_state.get("evaluations", {})
        counts: dict[str, int] = {}
        for ev in evaluations.values():
            for skill in ev.get("skill_details", []):
                if skill.get("present"):
                    name = str(skill.get("name", "")).strip()
                    if name:
                        counts[name] = counts.get(name, 0) + 1

        if counts:
            sorted_skills = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            return sorted_skills[:5]

        return [
            ("Python", 2),
            ("Django", 1),
            ("PostgreSQL", 1),
            ("Docker", 1),
            ("REST APIs", 1),
        ]

    def get_recent_resumes_rows(self) -> list[dict]:
        # build recent resume rows from session evaluations or fall back to realistic demo entries
        ranking_rows = st.session_state.get("ranking_rows", [])
        today_label = datetime.now().strftime("%b %d, %Y")

        if ranking_rows:
            rows = []
            for row in ranking_rows[:4]:
                fname = row.get("file_name", "candidate_resume.pdf")
                ev = row.get("evaluation", {})
                score = int(round(float(ev.get("final_score", 0.0))))
                rows.append(
                    {
                        "initials": self.extract_initials(fname),
                        "file_name": fname,
                        "date": today_label,
                        "score": f"{score}%",
                        "status": "completed",
                    }
                )
            return rows

        return [
            {
                "initials": "AT",
                "file_name": "alex_tan_backend_resume.pdf",
                "date": "Nov 14, 2026",
                "score": "92%",
                "status": "completed",
            },
            {
                "initials": "SL",
                "file_name": "sarah_lim_fullstack_cv.pdf",
                "date": "Nov 14, 2026",
                "score": "86%",
                "status": "completed",
            },
            {
                "initials": "RK",
                "file_name": "ryan_kumar_devops_resume.docx",
                "date": "Nov 13, 2026",
                "score": "79%",
                "status": "completed",
            },
            {
                "initials": "MC",
                "file_name": "michelle_chua_data_eng.pdf",
                "date": "Nov 12, 2026",
                "score": "74%",
                "status": "completed",
            },
        ]

    def render_status_banner(self):
        # full-width onboarding and system status banner card directly below the top header
        nav_tick = int(st.session_state.get("nav_tick", 0))
        has_api_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        heading = "Backend Connected" if has_api_key else "Demo Mode Active"
        description = (
            "Connected to the live AI evaluation service for real-time resume extraction, "
            "evidence verification, and candidate ranking."
            if has_api_key
            else "Explore the Resume Analyser interface with interactive candidate scoring, "
            "anonymized file ingestion, and recruitment analytics."
        )

        st.markdown(
            f"""
            <div class="ra-card ra-status-banner" data-tick="{nav_tick}">
                <div class="ra-banner-top">
                    <div class="ra-banner-icon">ℹ️</div>
                    <div style="flex: 1;">
                        <h3 class="ra-banner-heading">{heading}</h3>
                        <div class="ra-banner-desc">{description}</div>
                        <div class="ra-capability-row">
                            <span class="ra-capability-badge">
                                <span class="ra-capability-check">✓</span> Interactive UI demonstration
                            </span>
                            <span class="ra-capability-badge">
                                <span class="ra-capability-check">✓</span> Realistic mock analysis results
                            </span>
                            <span class="ra-capability-badge">
                                <span class="ra-capability-check">✓</span> File upload simulation
                            </span>
                            <span class="ra-capability-badge">
                                <span class="ra-capability-check">✓</span> Chart visualisations
                            </span>
                        </div>
                    </div>
                </div>
                <hr class="ra-divider" />
                <div class="ra-banner-footer">
                    <a class="ra-setup-link" href="#settings">
                        Configure live OpenAI API credentials &amp; screening rules →
                    </a>
                    <div class="ra-banner-actions">
                        <span class="ra-btn-crimson">Try Connect</span>
                        <span class="ra-btn-outline">Setup Guide</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_kpi_summary_row(self):
        # 4-column KPI summary row directly below the status banner
        nav_tick = int(st.session_state.get("nav_tick", 0))
        resumes = st.session_state.get("resumes", [])
        evaluations = st.session_state.get("evaluations", {})

        total_resumes = len(resumes) if resumes else 24
        analysed_count = len(evaluations) if evaluations else 18

        if evaluations:
            scores = [
                float(ev.get("final_score", 0.0))
                for ev in evaluations.values()
                if ev.get("status") != "RE_ENTRY"
            ]
            avg_score_val = sum(scores) / len(scores) if scores else 0.0
            avg_score_str = f"{avg_score_val:.0f}%"
        else:
            avg_score_str = "78%"

        kpi_cards = [
            {
                "icon": "📄",
                "icon_class": "ra-kpi-icon ra-kpi-icon-solid",
                "trend": "↗ +12%",
                "trend_class": "ra-kpi-trend",
                "value": str(total_resumes),
                "label": "Total Resumes",
            },
            {
                "icon": "👥",
                "icon_class": "ra-kpi-icon",
                "trend": "↗ +8%",
                "trend_class": "ra-kpi-trend",
                "value": str(analysed_count),
                "label": "Analysed Candidates",
            },
            {
                "icon": "🎯",
                "icon_class": "ra-kpi-icon",
                "trend": "↗ +5%",
                "trend_class": "ra-kpi-trend ra-kpi-trend-gold",
                "value": avg_score_str,
                "label": "Avg. Match Score",
            },
            {
                "icon": "⚡",
                "icon_class": "ra-kpi-icon",
                "trend": "↘ -2 days",
                "trend_class": "ra-kpi-trend ra-kpi-trend-gold",
                "value": "1.2s",
                "label": "Avg. Processing Time",
            },
        ]

        cols = st.columns(4)
        for idx, (col, card) in enumerate(zip(cols, kpi_cards)):
            with col:
                st.markdown(
                    f"""
                    <div class="ra-card ra-kpi-card ra-kpi-stagger-{idx}" data-tick="{nav_tick}">
                        <div class="ra-kpi-top">
                            <div class="{card['icon_class']}">{card['icon']}</div>
                            <span class="{card['trend_class']}">{card['trend']}</span>
                        </div>
                        <div>
                            <div class="ra-kpi-value">{card['value']}</div>
                            <div class="ra-kpi-label">{card['label']}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    def render_charts_row(self):
        # middle 2-column data visualisation row with animated SVG spline & circular donut charts
        nav_tick = int(st.session_state.get("nav_tick", 0))
        col_left, col_right = st.columns(2)

        with col_left:
            points = [
                ("Jan", 8, 55, 146, "0.85s"),
                ("Feb", 14, 145, 108, "1.30s"),
                ("Mar", 11, 235, 127, "1.75s"),
                ("Apr", 19, 325, 76, "2.20s"),
                ("May", 16, 415, 95, "2.65s"),
                ("Jun", 24, 505, 44, "3.10s"),
            ]
            spline_d = (
                "M 55 146 "
                "C 95 146, 110 108, 145 108 "
                "C 180 108, 200 127, 235 127 "
                "C 270 127, 290 76, 325 76 "
                "C 360 76, 380 95, 415 95 "
                "C 450 95, 470 44, 505 44"
            )
            area_d = f"{spline_d} L 505 182 L 55 182 Z"

            dots_svg = "".join(
                f'<g>'
                f'<circle class="ra-spline-dot" cx="{cx}" cy="{cy}" r="5.5" '
                f'fill="#F87171" stroke="#121216" stroke-width="2" style="animation-delay: {delay};">'
                f'<title>{month}: {val} applications</title>'
                f'</circle>'
                f'<text x="{cx}" y="204" fill="#A1A1AA" font-size="11.5" text-anchor="middle">{month}</text>'
                f'</g>'
                for month, val, cx, cy, delay in points
            )

            st.markdown(
                f"""
                <div class="ra-card ra-chart-stagger-0" data-tick="{nav_tick}">
                    <div class="ra-chart-header">
                        <h3 class="ra-chart-title">Monthly Applications</h3>
                        <span class="ra-chart-options" title="Chart options">⋮</span>
                    </div>
                    <svg viewBox="0 0 545 218" width="100%" height="238" style="overflow: visible; display: block;">
                        <defs>
                            <linearGradient id="raCrimsonGrad-{nav_tick}" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stop-color="#DC2626" stop-opacity="0.38" />
                                <stop offset="100%" stop-color="#DC2626" stop-opacity="0.0" />
                            </linearGradient>
                        </defs>
                        <line x1="42" y1="32" x2="520" y2="32" stroke="#24242B" stroke-dasharray="3 3" />
                        <text x="32" y="36" fill="#A1A1AA" font-size="11" text-anchor="end">25</text>
                        <line x1="42" y1="70" x2="520" y2="70" stroke="#24242B" stroke-dasharray="3 3" />
                        <text x="32" y="74" fill="#A1A1AA" font-size="11" text-anchor="end">20</text>
                        <line x1="42" y1="108" x2="520" y2="108" stroke="#24242B" stroke-dasharray="3 3" />
                        <text x="32" y="112" fill="#A1A1AA" font-size="11" text-anchor="end">15</text>
                        <line x1="42" y1="146" x2="520" y2="146" stroke="#24242B" stroke-dasharray="3 3" />
                        <text x="32" y="150" fill="#A1A1AA" font-size="11" text-anchor="end">10</text>
                        <line x1="42" y1="182" x2="520" y2="182" stroke="#24242B" />
                        <text x="32" y="186" fill="#A1A1AA" font-size="11" text-anchor="end">5</text>
                        <path class="ra-spline-area" d="{area_d}" fill="url(#raCrimsonGrad-{nav_tick})" />
                        <path class="ra-spline-line" d="{spline_d}" fill="none" stroke="#DC2626" stroke-width="3" stroke-linecap="round" pathLength="1000" />
                        {dots_svg}
                    </svg>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_right:
            palette = ["#DC2626", "#7F1D1D", "#F87171", "#F59E0B", "#64748B"]
            skills_data = self.get_top_skills_data()
            skill_colors = [palette[i % len(palette)] for i in range(len(skills_data))]
            total_count = sum(item[1] for item in skills_data) or 1

            radius = 68.0
            circumference = 2.0 * math.pi * radius
            gap = 4.5
            offset_accum = 0.0
            arcs_svg = []

            for (name, count), color in zip(skills_data, skill_colors):
                seg_len = max(2.0, (count / total_count) * circumference - gap)
                arcs_svg.append(
                    f'<circle class="ra-donut-segment" cx="110" cy="102" r="{radius:.1f}" '
                    f'fill="none" stroke="{color}" stroke-width="28" '
                    f'stroke-dasharray="{seg_len:.2f} {circumference:.2f}" '
                    f'stroke-dashoffset="{-offset_accum:.2f}">'
                    f'<title>{name}: {count}</title>'
                    f'</circle>'
                )
                offset_accum += (count / total_count) * circumference

            legend_items_html = "".join(
                f'<span class="ra-skill-legend-item">'
                f'<span class="ra-skill-swatch" style="background-color: {color};"></span>'
                f'<span>{name} ({count})</span>'
                f'</span>'
                for (name, count), color in zip(skills_data, skill_colors)
            )

            st.markdown(
                f"""
                <div class="ra-card ra-chart-stagger-1" data-tick="{nav_tick}">
                    <div class="ra-chart-header">
                        <h3 class="ra-chart-title">Top Skills Detected</h3>
                        <span class="ra-chart-options" title="Chart options">⋮</span>
                    </div>
                    <svg viewBox="0 0 220 200" width="100%" height="192" style="display: block; margin: 0 auto;">
                        <g class="ra-donut-ring">
                            {"".join(arcs_svg)}
                        </g>
                        <text x="110" y="98" fill="#F4F4F5" font-size="20" font-weight="800" text-anchor="middle">{total_count}</text>
                        <text x="110" y="116" fill="#A1A1AA" font-size="10.5" font-weight="500" text-anchor="middle">Skills</text>
                    </svg>
                    <div class="ra-skill-legend">{legend_items_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    def render_operational_row(self):
        # bottom 2-column operational row with Processing Queue on the left and Recent Resumes on the right
        nav_tick = int(st.session_state.get("nav_tick", 0))
        resumes = st.session_state.get("resumes", [])
        results = st.session_state.get("results", {})
        pending_resumes = [r for r in resumes if r.get("id") not in results]
        active_count = len(pending_resumes)

        col_left, col_right = st.columns(2)

        with col_left:
            if active_count == 0:
                queue_body_html = (
                    '<div class="ra-queue-empty">'
                    '<div class="ra-queue-clock">🕒</div>'
                    '<div class="ra-queue-empty-title">No resumes currently processing</div>'
                    '<div class="ra-queue-empty-sub">'
                    'Upload candidate PDF or DOCX files in Resume Analyser to queue them for AI screening.'
                    '</div>'
                    '</div>'
                )
            else:
                queued_items = "".join(
                    f'<div class="ra-candidate-row">'
                    f'<div class="ra-candidate-left">'
                    f'<div class="ra-avatar">{self.extract_initials(r["file_name"])}</div>'
                    f'<div class="ra-candidate-meta">'
                    f'<div class="ra-candidate-file">{r["file_name"]}</div>'
                    f'<div class="ra-candidate-date">Queued for AI screening</div>'
                    f'</div>'
                    f'</div>'
                    f'<div class="ra-candidate-right">'
                    f'<span class="ra-pill">queued</span>'
                    f'</div>'
                    f'</div>'
                    for r in pending_resumes[:4]
                )
                queue_body_html = f'<div class="ra-candidate-list">{queued_items}</div>'

            st.markdown(
                f"""
                <div class="ra-card ra-op-card ra-op-stagger-0" data-tick="{nav_tick}">
                    <div class="ra-op-header">
                        <h3 class="ra-op-title">Processing Queue</h3>
                        <span class="ra-active-counter">{active_count} active</span>
                    </div>
                    {queue_body_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_right:
            recent_rows = self.get_recent_resumes_rows()
            candidate_rows_html = "".join(
                f'<div class="ra-candidate-row">'
                f'<div class="ra-candidate-left">'
                f'<div class="ra-avatar">{row["initials"]}</div>'
                f'<div class="ra-candidate-meta">'
                f'<div class="ra-candidate-file" title="{row["file_name"]}">{row["file_name"]}</div>'
                f'<div class="ra-candidate-date">{row["date"]}</div>'
                f'</div>'
                f'</div>'
                f'<div class="ra-candidate-right">'
                f'<span class="ra-score-badge">★ {row["score"]}</span>'
                f'<span class="ra-completed-pill">{row["status"]}</span>'
                f'<span class="ra-eye-btn" title="Quick view candidate">👁</span>'
                f'</div>'
                f'</div>'
                for row in recent_rows
            )

            st.markdown(
                f"""
                <div class="ra-card ra-op-card ra-op-stagger-1" data-tick="{nav_tick}">
                    <div class="ra-op-header">
                        <h3 class="ra-op-title">Recent Resumes</h3>
                        <a class="ra-view-all-link" href="#candidates">View All →</a>
                    </div>
                    <div class="ra-candidate-list">
                        {candidate_rows_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# Abstract base class for all sidebar page views (LSP & OCP)
class BasePageView(ABC):

    def __init__(self, page_name: str, icon: str):
        self._page_name = str(page_name)
        self._icon = str(icon)

    @property
    def page_name(self) -> str:
        return self._page_name

    @property
    def icon(self) -> str:
        return self._icon

    @abstractmethod
    def render(self):
        pass


class DashboardView(BasePageView):

    def __init__(self, widgets: OverviewWidgets):
        super().__init__("Dashboard", "📊")
        self._widgets = widgets

    def render(self):
        self._widgets.render_status_banner()
        self._widgets.render_kpi_summary_row()
        self._widgets.render_charts_row()
        self._widgets.render_operational_row()


class AnalyticsView(BasePageView):

    def __init__(self, widgets: OverviewWidgets):
        super().__init__("Analytics", "📈")
        self._widgets = widgets

    def render(self):
        self._widgets.render_status_banner()
        self._widgets.render_kpi_summary_row()
        self._widgets.render_charts_row()


class ResumeAnalyserView(BasePageView):

    def __init__(self, controller):
        super().__init__("Resume Analyser", "📄")
        self._controller = controller

    def render(self):
        st.subheader("Resume Analyser")
        self._controller._render_job_form()
        self._controller._render_active_job_summary()
        self._controller._render_resume_upload_section()


class CandidatesView(BasePageView):

    def __init__(self):
        super().__init__("Candidates", "👥")

    def render(self):
        # load saved candidates and allow Markdown preview + PDF download via CandidateReport
        st.subheader("Candidates")
        try:
            candidates = [
                record.to_dict() for record in ScreeningStore().load_results()
            ]
        except StorageError as error:
            st.error(f"Could not load saved results: {error}")
            return

        if not candidates:
            st.info("No saved screening results found.")
            return

        candidate = st.selectbox(
            "Select a candidate",
            candidates,
            format_func=lambda row: f"{row['candidate_id']} | {row['file_name']}",
        )
        report = CandidateReport(candidate)
        st.markdown(report.to_markdown())
        st.download_button(
            label="Download candidate report (PDF)",
            data=report.to_pdf(),
            file_name=f"{candidate['candidate_id']}-screening-report.pdf",
            mime="application/pdf",
        )


class JobPostingsView(BasePageView):

    def __init__(self):
        super().__init__("Job Postings", "💼")

    def render(self):
        st.subheader("Job Postings")


class SettingsView(BasePageView):

    def __init__(self):
        super().__init__("Settings", "⚙️")

    def render(self):
        st.subheader("Settings")
