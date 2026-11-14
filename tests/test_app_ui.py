# tests for the helper and upload logic inside OOP/AppUI_OOP.py

import io
import sys
import types
import unittest
from tempfile import TemporaryDirectory

from docx import Document

# fall back to a lightweight stub when running in a local venv without streamlit installed
try:
    import streamlit  # noqa: F401
except ModuleNotFoundError:
    sys.modules["streamlit"] = types.SimpleNamespace(session_state={})

from OOP.AppUI_OOP import AppUI


class TestAppUIHelpers(unittest.TestCase):

    def setUp(self):
        self.ui = AppUI()

    def test_skill_list_is_trimmed_and_deduplicated(self):
        skills = AppUI._parse_skill_list(" Python, sql , python,, SQL ,Docker")
        self.assertEqual(skills, ["Python", "sql", "Docker"])

    def test_valid_job_is_built_and_preferred_skips_required(self):
        job, prefs = self.ui._build_job_and_preferences(
            title="  Backend Dev  ",
            required_raw="Python, SQL",
            preferred_raw="sql, Docker",
            min_experience=2.0,
            education="BSc",
            min_qualifying_score=75.0,
        )
        self.assertEqual(job.title, "Backend Dev")
        self.assertEqual(job.required_skills, ["Python", "SQL"])
        self.assertEqual(job.preferred, ["Docker"])
        self.assertEqual(prefs.min_qualifying_score, 75.0)

    def test_invalid_job_inputs_are_rejected(self):
        bad_inputs = [
            ("", "Python", "", 0.0, "", 60.0),              # empty title
            ("Dev", "", "", 0.0, "", 60.0),                 # no skills at all
            ("Dev", "Python", "", -1.0, "", 60.0),          # negative experience
            ("Dev", "Python", "", float("inf"), "", 60.0),  # infinite experience
            ("Dev", "Python", "", 0.0, "", 150.0),          # score above 100
        ]
        for args in bad_inputs:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    self.ui._build_job_and_preferences(*args)

    def test_uploaded_docx_is_extracted_and_anonymized(self):
        doc = Document()
        doc.add_paragraph("Name: Alice Tan")
        doc.add_paragraph("Reach me at alice@example.com or +65 9123 4567")
        doc.add_paragraph("Built Python REST APIs for 3 years.")
        buffer = io.BytesIO()
        doc.save(buffer)

        with TemporaryDirectory() as temp_dir:
            record = self.ui._process_uploaded_file("alice.docx", buffer.getvalue(), temp_dir)
            self.assertEqual(record["file_name"], "alice.docx")
            self.assertNotIn("Alice Tan", record["text"])
            self.assertIn("[EMAIL REMOVED]", record["text"])
            self.assertIn("[PHONE REMOVED]", record["text"])
            self.assertIn("Built Python REST APIs", record["text"])

    def test_empty_uploaded_file_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                self.ui._process_uploaded_file("empty.pdf", b"", temp_dir)


if __name__ == "__main__":
    unittest.main()
