# UI module for the Streamlit web app

import math
import os
from tempfile import TemporaryDirectory
import uuid
import streamlit as st

from OOP.io_manager import IOManager
from OOP.logic_manager import Job, ScreeningPreferences


# main Streamlit UI class handling layout and user inputs
class AppUI:

    PAGES = (
        "Screen New Batch",
        "View Saved Results",
        "Review Candidates",
        "Manage Jobs",
    )

    def __init__(self, title: str = "AI Resume Screener", io_manager: IOManager | None = None):
        self._title = str(title)
        # use the provided IOManager or create a default one for file validation and text extraction
        self._io_manager = io_manager or IOManager()
        # guard against the typo in IOManager.__init__ (__vaild_resume_extensions)
        if not hasattr(self._io_manager, "_IOManager__valid_resume_extensions"):
            setattr(self._io_manager, "_IOManager__valid_resume_extensions", (".pdf", ".docx"))

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

    def _init_session_state(self):
        # keep form and screening data across Streamlit reruns
        defaults = {
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
        # write uploaded bytes to a temp file so IOManager can validate, extract, and anonymize it
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
        # sidebar for switching pages and seeing quick session stats
        with st.sidebar:
            st.header("Navigation")
            selected_page = st.radio("Go to", self.PAGES, key="active_page")

            st.divider()
            st.subheader("Session Summary")
            job = st.session_state.get("job_description")
            job_label = job["title"] if job and job.get("title") else "Not set"
            st.write(f"**Active Role:** {job_label}")
            st.write(f"**Resumes Loaded:** {len(st.session_state.get('resumes', []))}")
            st.write(f"**Screened:** {len(st.session_state.get('results', {}))}")

        return selected_page

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
        # let the recruiter upload PDF or DOCX resumes and process them with IOManager
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

    def render_screen_batch_page(self):
        # batch screening page combining job setup and resume uploads
        st.subheader("Screen New Batch")
        self._render_job_form()
        self._render_active_job_summary()
        self._render_resume_upload_section()
        st.info("Step 4 will connect AIManager and ScoringEngine to screen the loaded resumes.")

    def render_saved_results_page(self):
        # placeholder until DataManager is ready
        st.subheader("View Saved Results")
        st.info("Will connect to DataManager once completed.")

    def render_review_candidates_page(self):
        # placeholder until DataManager is ready
        st.subheader("Review Candidates")
        st.info("Will connect to DataManager once completed.")

    def render_manage_jobs_page(self):
        # placeholder until DataManager is ready
        st.subheader("Manage Jobs")
        st.info("Will connect to DataManager once completed.")

    def render_body(self, selected_page: str):
        # route to whichever page was picked in the sidebar
        page_routes = {
            "Screen New Batch": self.render_screen_batch_page,
            "View Saved Results": self.render_saved_results_page,
            "Review Candidates": self.render_review_candidates_page,
            "Manage Jobs": self.render_manage_jobs_page,
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
