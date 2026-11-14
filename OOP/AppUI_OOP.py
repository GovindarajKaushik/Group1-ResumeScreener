"""UI module for Streamlit application."""

import streamlit as st


class AppUI:
    """Class-based UI container for the Streamlit dashboard."""

    PAGES = (
        "Screen New Batch",
        "View Saved Results",
        "Review Candidates",
        "Manage Jobs",
    )

    def __init__(self, title: str = "AI Resume Screener"):
        self.title = title

    def setup_page(self):
        """Configure page settings and metadata."""
        st.set_page_config(
            page_title=self.title,
            page_icon="📄",
            layout="wide",
        )

    def init_session_state(self):
        """Initialize persistent session keys across Streamlit reruns."""
        defaults = {
            "job_description": None,
            "preferences": {"min_qualifying_score": 60.0},
            "resumes": [],
            "results": {},
            "evaluations": {},
            "ranking_rows": [],
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def render_header(self):
        """Render application title and introductory text."""
        st.title(f"📄 {self.title}")
        st.caption("DevOps Project 1 - Class-based Streamlit UI")

    def render_sidebar(self):
        """Render sidebar navigation and session overview."""
        with st.sidebar:
            st.header("Navigation")
            selected_page = st.radio(
                "Go to",
                self.PAGES,
                key="active_page",
            )

            st.divider()
            st.subheader("Session Summary")
            job = st.session_state.get("job_description")
            job_label = job["title"] if job and job.get("title") else "Not set"
            st.write(f"**Active Role:** {job_label}")
            st.write(f"**Resumes Loaded:** {len(st.session_state.get('resumes', []))}")
            st.write(f"**Screened:** {len(st.session_state.get('results', {}))}")

        return selected_page

    def render_screen_batch_page(self):
        """Placeholder for job input, resume upload, and screening workflow."""
        st.subheader("Screen New Batch")
        st.info("Step 2 will add the Job Description & Preferences form here.")

    def render_saved_results_page(self):
        """Placeholder for viewing saved jobs and candidate scores."""
        st.subheader("View Saved Results")
        st.info("Will connect to DataManager once completed.")

    def render_review_candidates_page(self):
        """Placeholder for recruiter shortlist/reject workflow."""
        st.subheader("Review Candidates")
        st.info("Will connect to DataManager once completed.")

    def render_manage_jobs_page(self):
        """Placeholder for viewing or deleting saved jobs."""
        st.subheader("Manage Jobs")
        st.info("Will connect to DataManager once completed.")

    def render_body(self, selected_page: str):
        """Route to the selected page renderer."""
        page_routes = {
            "Screen New Batch": self.render_screen_batch_page,
            "View Saved Results": self.render_saved_results_page,
            "Review Candidates": self.render_review_candidates_page,
            "Manage Jobs": self.render_manage_jobs_page,
        }
        renderer = page_routes.get(selected_page, self.render_screen_batch_page)
        renderer()

    def run(self):
        """Run the UI presentation lifecycle."""
        self.setup_page()
        self.init_session_state()
        selected_page = self.render_sidebar()
        self.render_header()
        self.render_body(selected_page)
