import streamlit as st


# UI module for Streamlit application
class AppUI:

    def __init__(self, title: str = "AI Resume Screener"):
        self.title = title

    def setup_page(self):
        # page settings and metadata configs
        st.set_page_config(
            page_title=self.title,
            page_icon="📄",
            layout="wide",
        )

    def render_header(self):
        # application title and intro
        st.title(f"📄 {self.title}")
        st.caption("DevOps Project 1 - Class-based Streamlit UI")

    def render_sidebar(self):
        # sidebar and navigation controls
        with st.sidebar:
            st.header("⚙️ Controls")
            st.info("System running in Docker container.")

    def render_body(self):
        # initial dashboard content
        st.success("✅ Streamlit UI successfully connected and running!")
        
        with st.expander("📌 Quick Health Check", expanded=True):
            st.write("Status: **Active**")
            st.write("Environment: **Docker containerized**")
            st.write("Architecture: **Object-Oriented (Class-based)**")

    def run(self):
        # UI presentation lifecycle
        self.setup_page()
        self.render_sidebar()
        self.render_header()
        self.render_body()
