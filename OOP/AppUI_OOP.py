# UI module for the Streamlit web app

import math
import os
from tempfile import TemporaryDirectory
import uuid
import streamlit as st

from OOP.io_manager import ResumeImporter
from OOP.logic_manager import Job, ScreeningPreferences


# main Streamlit UI class handling layout and user inputs
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

    def __init__(self, title: str = "Resume Analyser", io_manager: ResumeImporter | None = None):
        self._title = str(title)
        # use the provided ResumeImporter or create a default one for file validation and text extraction
        self._io_manager = io_manager or ResumeImporter()

    @property
    def title(self) -> str:
        # read-only access to the app title
        return self._title

    def setup_page(self):
        # set browser tab title, icon, and wide layout
        st.set_page_config(
            page_title=self._title,
            page_icon="📄",
            layout="wide",
        )
        self._inject_global_styles()

    def _inject_global_styles(self):
        # inject Obsidian Black, Dark Red & Cool Silver design system variables, chrome cleanup, and reusable card classes
        st.markdown(
            """
            <style>
            :root {
                --ra-bg-canvas: #09090B;
                --ra-bg-surface: #121216;
                --ra-border: #24242B;
                --ra-text-primary: #F4F4F5;
                --ra-text-muted: #A1A1AA;
                --ra-accent-primary: #991B1B;
                --ra-accent-hover: #DC2626;
                --ra-accent-rose: #F87171;
                --ra-accent-gold: #F59E0B;
                --background-color: #09090B;
                --secondary-background-color: #121216;
                --text-color: #F4F4F5;
                --primary-color: #991B1B;
            }

            /* Clean App Chrome */
            #MainMenu,
            footer,
            header[data-testid="stHeader"],
            div[data-testid="stToolbar"],
            div[data-testid="stDecoration"] {
                display: none !important;
            }

            /* Main Canvas & Sidebar Backgrounds */
            .stApp,
            div[data-testid="stAppViewContainer"],
            section.main {
                background-color: var(--ra-bg-canvas) !important;
                color: var(--ra-text-primary) !important;
            }

            section[data-testid="stSidebar"] {
                background-color: var(--ra-bg-surface) !important;
                border-right: 1px solid var(--ra-border) !important;
            }

            section[data-testid="stSidebar"] > div:first-child {
                display: flex;
                flex-direction: column;
                min-height: 100vh;
                padding-top: 1.25rem !important;
                padding-bottom: 1.25rem !important;
            }

            /* Main Block Container Spacing */
            .block-container {
                padding-top: 1.75rem !important;
                padding-bottom: 2.5rem !important;
                padding-left: 2.25rem !important;
                padding-right: 2.25rem !important;
                max-width: 100% !important;
            }

            /* Typography */
            h1, h2, h3, h4, h5, h6,
            p, span, label, div[data-testid="stMarkdownContainer"] {
                color: var(--ra-text-primary);
            }

            .stCaption, small, .ra-muted {
                color: var(--ra-text-muted) !important;
            }

            /* Primary & Secondary Buttons */
            .stButton > button[kind="primary"],
            .stFormSubmitButton > button[kind="primary"] {
                background-color: var(--ra-accent-primary) !important;
                border: 1px solid var(--ra-accent-hover) !important;
                color: var(--ra-text-primary) !important;
                border-radius: 10px !important;
                font-weight: 600 !important;
                transition: background-color 0.18s ease, border-color 0.18s ease;
            }

            .stButton > button[kind="primary"]:hover,
            .stFormSubmitButton > button[kind="primary"]:hover {
                background-color: var(--ra-accent-hover) !important;
                border-color: var(--ra-accent-rose) !important;
            }

            /* Sidebar Brand Header */
            .ra-brand-header {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 0.25rem 0.25rem 1.25rem 0.25rem;
                margin-bottom: 0.75rem;
                border-bottom: 1px solid var(--ra-border);
            }

            .ra-brand-badge {
                width: 40px;
                height: 40px;
                border-radius: 10px;
                background-color: var(--ra-accent-primary);
                border: 1px solid var(--ra-accent-hover);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.2rem;
                color: #FFFFFF;
                flex-shrink: 0;
                box-shadow: 0 4px 12px rgba(153, 27, 27, 0.35);
            }

            .ra-brand-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: var(--ra-text-primary);
                line-height: 1.2;
                margin: 0;
            }

            .ra-brand-subtitle {
                font-size: 0.76rem;
                color: var(--ra-text-muted);
                line-height: 1.2;
                margin-top: 2px;
            }

            /* Sidebar Navigation Pills */
            section[data-testid="stSidebar"] .stButton > button {
                width: 100% !important;
                justify-content: flex-start !important;
                text-align: left !important;
                padding: 0.6rem 0.9rem !important;
                border-radius: 9999px !important;
                font-size: 0.9rem !important;
                font-weight: 500 !important;
                margin-bottom: 0.2rem !important;
                transition: all 0.16s ease !important;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
                background: transparent !important;
                border: 1px solid transparent !important;
                color: var(--ra-text-muted) !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="secondary"] p,
            section[data-testid="stSidebar"] .stButton > button[kind="secondary"] span {
                color: var(--ra-text-muted) !important;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
                background-color: #1C1C22 !important;
                border-color: var(--ra-border) !important;
                color: var(--ra-text-primary) !important;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover p,
            section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover span {
                color: var(--ra-text-primary) !important;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
                background: linear-gradient(90deg, #991B1B 0%, #DC2626 100%) !important;
                border: 1px solid #DC2626 !important;
                color: #FFFFFF !important;
                font-weight: 600 !important;
                box-shadow: 0 4px 14px rgba(153, 27, 27, 0.4) !important;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="primary"] p,
            section[data-testid="stSidebar"] .stButton > button[kind="primary"] span {
                color: #FFFFFF !important;
            }

            /* Pinned Bottom Mode Indicator */
            .ra-mode-box {
                margin-top: 1.75rem;
                background-color: rgba(153, 27, 27, 0.15);
                border: 1px solid #991B1B;
                border-radius: 12px;
                padding: 0.75rem 0.9rem;
                display: flex;
                align-items: center;
                gap: 0.65rem;
            }

            .ra-mode-icon {
                font-size: 1rem;
                color: var(--ra-accent-rose);
                flex-shrink: 0;
            }

            .ra-mode-title {
                font-size: 0.82rem;
                font-weight: 600;
                color: var(--ra-text-primary);
                line-height: 1.25;
            }

            .ra-mode-desc {
                font-size: 0.72rem;
                color: var(--ra-text-muted);
                line-height: 1.25;
                margin-top: 2px;
            }

            /* Reusable Base Card Styles */
            .ra-card,
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: var(--ra-bg-surface) !important;
                border: 1px solid var(--ra-border) !important;
                border-radius: 14px !important;
                padding: 1.35rem 1.5rem !important;
                box-shadow: 0 10px 28px -6px rgba(0, 0, 0, 0.65) !important;
            }

            .ra-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.25rem 0.7rem;
                border-radius: 9999px;
                font-size: 0.78rem;
                font-weight: 600;
                background-color: rgba(153, 27, 27, 0.22);
                color: var(--ra-accent-rose);
                border: 1px solid var(--ra-accent-primary);
            }

            .ra-pill-gold {
                background-color: rgba(245, 158, 11, 0.16);
                color: var(--ra-accent-gold);
                border: 1px solid rgba(245, 158, 11, 0.45);
            }

            .ra-divider,
            hr {
                border: none !important;
                border-top: 1px solid var(--ra-border) !important;
                margin: 1.15rem 0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def _init_session_state(self):
        # keep form and screening data across Streamlit reruns
        defaults = {
            "active_page": "Resume Analyser",
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
        # show app title at the top of the page
        st.title(f"📄 {self._title}")
        st.caption("INF1103 Phase 2 - Object-Oriented Streamlit Interface")

    def render_sidebar(self) -> str:
        # left sidebar with brand header, vertical pill navigation, and pinned bottom mode box
        current_page = st.session_state.get("active_page", "Resume Analyser")
        if current_page not in self.PAGES:
            current_page = "Resume Analyser"
            st.session_state["active_page"] = current_page

        has_api_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        mode_label = "Live Backend" if has_api_key else "Demo Mode"
        mode_desc = "OpenAI API key configured" if has_api_key else "Offline simulation & local scoring"

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
                    st.rerun()

            st.markdown(
                f"""
                <div class="ra-mode-box">
                    <div class="ra-mode-icon">ℹ️</div>
                    <div>
                        <div class="ra-mode-title">{mode_label}</div>
                        <div class="ra-mode-desc">{mode_desc}</div>
                    </div>
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

    def render_dashboard_page(self):
        st.subheader("Dashboard")

    def render_screen_batch_page(self):
        # batch screening page combining job setup and resume uploads
        st.subheader("Resume Analyser")
        self._render_job_form()
        self._render_active_job_summary()
        self._render_resume_upload_section()

    def render_review_candidates_page(self):
        st.subheader("Candidates")

    def render_manage_jobs_page(self):
        st.subheader("Job Postings")

    def render_analytics_page(self):
        st.subheader("Analytics")

    def render_settings_page(self):
        st.subheader("Settings")

    def render_body(self, selected_page: str):
        # route to whichever page was picked in the sidebar
        page_routes = {
            "Dashboard": self.render_dashboard_page,
            "Resume Analyser": self.render_screen_batch_page,
            "Candidates": self.render_review_candidates_page,
            "Job Postings": self.render_manage_jobs_page,
            "Analytics": self.render_analytics_page,
            "Settings": self.render_settings_page,
        }
        renderer = page_routes.get(selected_page, self.render_screen_batch_page)
        renderer()

    def run(self):
        # main entry point for rendering the Streamlit UI
        self.setup_page()
        self._init_session_state()
        selected_page = self.render_sidebar()
        self.render_header()
        self.render_body(selected_page)
