# Main controller module for the Object-Oriented Streamlit UI

from datetime import datetime
import math
import os
from tempfile import TemporaryDirectory
import uuid
import streamlit as st

from OOP.io_manager import ResumeImporter
from OOP.logic_manager import Job, ScreeningPreferences
from OOP.ui.ui_theme import UITheme
from OOP.ui.ui_views import (
    AnalyticsView,
    BasePageView,
    CandidatesView,
    DashboardView,
    JobPostingsView,
    OverviewWidgets,
    ResumeAnalyserView,
    SettingsView,
)


# Coordinates sidebar navigation, session state, file ingestion, and polymorphic page views
class AppUI:

    PAGES = (
        "Dashboard",
        "Resume Analyser",
        "Candidates",
        "Job Postings",
        "Analytics",
        "Settings",
    )

    NAV_ICONS = {
        "Dashboard": "📊",
        "Resume Analyser": "📄",
        "Candidates": "👥",
        "Job Postings": "💼",
        "Analytics": "📈",
        "Settings": "⚙️",
    }

    def __init__(
        self,
        title: str = "Resume Analyser",
        io_manager: ResumeImporter | None = None,
        theme: UITheme | None = None,
    ):
        self._title = str(title)
        # aggregation/composition of IO, theme, and view objects
        self._io_manager = io_manager or ResumeImporter()
        self._theme = theme or UITheme()
        self._widgets = OverviewWidgets()
        self._views: dict[str, BasePageView] = {
            "Dashboard": DashboardView(self._widgets),
            "Resume Analyser": ResumeAnalyserView(self),
            "Candidates": CandidatesView(),
            "Job Postings": JobPostingsView(),
            "Analytics": AnalyticsView(self._widgets),
            "Settings": SettingsView(),
        }

    @property
    def title(self) -> str:
        # read-only access to the app title
        return self._title

    def register_view(self, view: BasePageView):
        # allow new BasePageView subclasses to be registered without modifying routing logic (OCP)
        if not isinstance(view, BasePageView):
            raise TypeError("view must be an instance of BasePageView")
        self._views[view.page_name] = view

    def setup_page(self):
        # set browser tab title, icon, and wide layout
        st.set_page_config(
            page_title=self._title,
            page_icon="📄",
            layout="wide",
        )

    def _inject_global_styles(self):
        self._theme.apply_global_styles()

    def _init_session_state(self):
        # keep form and screening data across Streamlit reruns
        defaults = {
            "active_page": "Dashboard",
            "nav_tick": 0,
            "job_description": None,
            "preferences": ScreeningPreferences().to_dict(),
            "resumes": [],
            "rejected_resumes": [],
            "results": {},
            "evaluations": {},
            "ranking_rows": [],
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def _parse_skill_list(raw_text: str) -> list[str]:
        # split comma-separated skills and drop empty or duplicate entries
        skills = []
        seen = set()
        for item in raw_text.split(","):
            skill = item.strip()
            if skill and skill.lower() not in seen:
                skills.append(skill)
                seen.add(skill.lower())
        return skills

    def _build_job_and_preferences(
        self,
        title: str,
        required_raw: str,
        preferred_raw: str,
        min_experience: float,
        education: str,
        min_qualifying_score: float,
    ) -> tuple[Job, ScreeningPreferences]:
        # clean up inputs and validate them using the Job and ScreeningPreferences classes
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Job title cannot be empty.")
        if not math.isfinite(min_experience) or min_experience < 0:
            raise ValueError("Minimum years of experience must be a finite, nonnegative number.")

        required_skills = self._parse_skill_list(required_raw)
        required_lower = {skill.lower() for skill in required_skills}
        # don't repeat required skills inside preferred skills
        preferred_skills = [
            skill
            for skill in self._parse_skill_list(preferred_raw)
            if skill.lower() not in required_lower
        ]

        preferences = ScreeningPreferences(min_qualifying_score=min_qualifying_score)
        job = Job(
            title=clean_title,
            required_skills=required_skills,
            preferred=preferred_skills,
            min_experience=min_experience,
            education=education,
            preferences=preferences,
        )
        job.validate()
        return job, preferences

    def _process_uploaded_file(self, file_name: str, file_bytes: bytes, temp_dir: str) -> dict:
        # write uploaded bytes to a temp file so ResumeImporter can validate, extract, and anonymize it
        safe_name = os.path.basename(file_name)
        temp_path = os.path.join(temp_dir, safe_name)
        with open(temp_path, "wb") as handle:
            handle.write(file_bytes)

        self._io_manager.validate_resume_file(temp_path)

        extracted_text = self._io_manager.extract_resume_text(temp_path)
        if not extracted_text:
            raise ValueError("No readable text found. Use a readable PDF or DOCX file.")

        anonymized_text = self._io_manager.anonymize_resume_text(extracted_text)
        if not anonymized_text:
            raise ValueError("No resume content remains after removing personal details.")

        return {
            "id": uuid.uuid4().hex,
            "file_name": safe_name,
            "file_path": safe_name,
            "text": anonymized_text,
        }

    def _ingest_uploaded_resumes(self, uploaded_files: list) -> tuple[int, list[dict]]:
        # process a batch of uploaded files while keeping previously accepted resumes in session
        existing_resumes = list(st.session_state.get("resumes", []))
        accepted_names = {r["file_name"].lower() for r in existing_resumes}
        added_count = 0
        rejected = []

        with TemporaryDirectory() as temp_dir:
            for uploaded in uploaded_files:
                file_name = os.path.basename(uploaded.name)
                if file_name.lower() in accepted_names:
                    continue
                try:
                    resume_record = self._process_uploaded_file(
                        file_name=file_name,
                        file_bytes=uploaded.getvalue(),
                        temp_dir=temp_dir,
                    )
                except ValueError as error:
                    rejected.append({"file_name": file_name, "reason": str(error)})
                else:
                    existing_resumes.append(resume_record)
                    accepted_names.add(file_name.lower())
                    added_count += 1

        st.session_state["resumes"] = existing_resumes
        st.session_state["rejected_resumes"] = rejected
        return added_count, rejected

    def render_header(self):
        # top split header bar with title/subtitle on the left and utility controls on the right
        has_api_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        mode_text = "Live Backend" if has_api_key else "Demo Mode"
        action_text = "Connected" if has_api_key else "Connect"
        last_updated = st.session_state.get("last_updated") or datetime.now().strftime("%H:%M:%S")
        st.session_state["last_updated"] = last_updated

        st.markdown(
            f"""
            <div class="ra-top-header">
                <div>
                    <h1 class="ra-header-title">
                        Resume <span class="ra-header-title-accent">Analyser</span>
                    </h1>
                    <div class="ra-header-subtitle">
                        AI-powered recruitment insights and candidate analysis.
                    </div>
                </div>
                <div class="ra-header-controls">
                    <div class="ra-status-pill">
                        <span class="ra-status-dot"></span>
                        <span>{mode_text}</span>
                        <span class="ra-inline-connect-btn">{action_text}</span>
                    </div>
                    <div class="ra-refresh-btn" title="Refresh workspace">↻</div>
                    <div class="ra-updated-pill">
                        <span>🕒</span>
                        <span>Last Updated: {last_updated}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def render_status_banner(self):
        self._widgets.render_status_banner()

    def render_kpi_summary_row(self):
        self._widgets.render_kpi_summary_row()

    def render_charts_row(self):
        self._widgets.render_charts_row()

    def render_operational_row(self):
        self._widgets.render_operational_row()

    def render_sidebar(self) -> str:
        # sidebar with brand header, vertical pill navigation, and pinned bottom mode box
        current_page = st.session_state.get("active_page", "Dashboard")
        if current_page not in self.PAGES:
            current_page = "Dashboard"
            st.session_state["active_page"] = current_page

        has_api_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        mode_label = "Live Backend" if has_api_key else "Demo Mode"
        mode_sub = "OpenAI API connected" if has_api_key else "Using local/mock screening mode"

        with st.sidebar:
            st.markdown(
                """
                <div class="ra-brand-header">
                    <div class="ra-brand-badge">📄</div>
                    <div>
                        <div class="ra-brand-title">Resume Analyser</div>
                        <div class="ra-brand-subtitle">AI-Powered Recruitment</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for page in self.PAGES:
                icon = self.NAV_ICONS.get(page, "•")
                is_active = page == current_page
                if st.button(
                    f"{icon}  {page}",
                    key=f"nav_btn_{page}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["active_page"] = page
                    st.session_state["nav_tick"] = int(st.session_state.get("nav_tick", 0)) + 1
                    st.rerun()

            st.markdown(
                f"""
                <div class="ra-mode-box">
                    <div class="ra-mode-title">ℹ️ <span>{mode_label}</span></div>
                    <div class="ra-mode-sub">{mode_sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        return st.session_state["active_page"]

    def _render_job_form(self):
        # pre-fill the form if a job was already saved in this session
        existing_job = st.session_state.get("job_description") or {}
        existing_prefs = st.session_state.get("preferences") or {}

        with st.form("job_requirements_form"):
            st.markdown("#### 1. Job Requirements & Screening Preferences")

            col_left, col_right = st.columns(2)
            with col_left:
                title = st.text_input(
                    "Job Title *",
                    value=existing_job.get("title", ""),
                    placeholder="e.g. Junior Backend Developer",
                )
                required_raw = st.text_input(
                    "Required Skills (comma-separated)",
                    value=", ".join(existing_job.get("required_skills", [])),
                    placeholder="e.g. Python, REST APIs, SQL",
                )
                preferred_raw = st.text_input(
                    "Preferred Skills (comma-separated)",
                    value=", ".join(existing_job.get("preferred", [])),
                    placeholder="e.g. Docker, Git",
                )

            with col_right:
                min_experience = st.number_input(
                    "Minimum Years of Experience",
                    min_value=0.0,
                    step=0.5,
                    value=float(existing_job.get("min_experience", 0.0)),
                )
                education = st.text_input(
                    "Education Requirements",
                    value=existing_job.get("education", ""),
                    placeholder="e.g. Bachelor's in Computer Science",
                )
                min_qualifying_score = st.slider(
                    "Minimum Qualifying Score",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    value=float(existing_prefs.get("min_qualifying_score", 60.0)),
                )

            submitted = st.form_submit_button("Save Job & Preferences", type="primary")

        if submitted:
            try:
                job, preferences = self._build_job_and_preferences(
                    title=title,
                    required_raw=required_raw,
                    preferred_raw=preferred_raw,
                    min_experience=min_experience,
                    education=education,
                    min_qualifying_score=min_qualifying_score,
                )
            except ValueError as error:
                st.error(f"Invalid job configuration: {error}")
            else:
                st.session_state["job_description"] = job.to_dict()
                st.session_state["preferences"] = preferences.to_dict()
                st.success(f"Saved requirements for '{job.title}'.")

    def _render_active_job_summary(self):
        # show the saved job details below the form so the user can double-check them
        job = st.session_state.get("job_description")
        prefs = st.session_state.get("preferences") or {}
        if not job:
            return

        with st.expander("Configured Job Summary", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Title:** {job['title']}")
                st.write(f"**Required Skills:** {', '.join(job['required_skills']) or 'None'}")
                st.write(f"**Preferred Skills:** {', '.join(job['preferred']) or 'None'}")
            with col2:
                st.write(f"**Min Experience:** {job['min_experience']} year(s)")
                st.write(f"**Education:** {job['education'] or 'Not specified'}")
                st.write(f"**Qualifying Score:** {prefs.get('min_qualifying_score', 60.0):g} / 100")

            if st.button("Clear Job Configuration"):
                st.session_state["job_description"] = None
                st.session_state["preferences"] = ScreeningPreferences().to_dict()
                st.rerun()

    def _render_resume_upload_section(self):
        # let the recruiter upload PDF or DOCX resumes and process them with ResumeImporter
        st.divider()
        st.markdown("#### 2. Upload Candidate Resumes")

        uploaded_files = st.file_uploader(
            "Select one or more PDF or DOCX resumes (you can upload additional batches to add more)",
            type=["pdf", "docx"],
            accept_multiple_files=True,
        )

        if st.button("Process Uploaded Resumes", disabled=not uploaded_files):
            added_count, rejected = self._ingest_uploaded_resumes(uploaded_files)
            if added_count > 0:
                st.success(f"Added {added_count} readable resume(s) to the current batch.")
            elif not rejected:
                st.info("All selected files are already loaded in the current batch.")

        # show any rejected files from the latest upload attempt
        for item in st.session_state.get("rejected_resumes", []):
            st.warning(f"Rejected '{item['file_name']}': {item['reason']}")

        resumes = st.session_state.get("resumes", [])
        if resumes:
            with st.expander(f"Loaded Resumes Ready for Screening ({len(resumes)})", expanded=True):
                for idx, resume in enumerate(resumes, start=1):
                    st.markdown(f"**{idx}. {resume['file_name']}**")
                    st.text_area(
                        f"Anonymized text preview ({resume['file_name']})",
                        value=resume["text"],
                        height=120,
                        disabled=True,
                        key=f"preview_{resume['id']}",
                    )

                if st.button("Clear Loaded Resumes"):
                    st.session_state["resumes"] = []
                    st.session_state["rejected_resumes"] = []
                    st.rerun()

    def render_body(self, selected_page: str):
        # apply view transition animation and polymorphically render the active BasePageView
        nav_tick = int(st.session_state.get("nav_tick", 0))
        self._theme.apply_view_transition(nav_tick)

        view = self._views.get(selected_page, self._views["Dashboard"])
        view.render()

    def run(self):
        # main entry point for rendering the Streamlit UI
        self.setup_page()
        self._init_session_state()
        self._inject_global_styles()
        selected_page = self.render_sidebar()
        self.render_header()
        self.render_body(selected_page)
