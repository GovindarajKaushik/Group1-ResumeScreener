# Unit tests for OOP/io_manager.py (validation, extraction, anonymization, and console IO helpers)

import io
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from contextlib import redirect_stdout
from types import SimpleNamespace
from docx import Document

from OOP.io_manager import (
    CandidateReport,
    ConsoleUI,
    DocxTextExtractor,
    Job,
    PdfCandidateReport,
    PdfTextExtractor,
    Resume,
    ResumeImporter,
    ScreeningPreferences,
    TextExtractor,
)


class _DummyTextExtractor(TextExtractor):

    def extract(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")


class TestIOManagerModels(unittest.TestCase):

    def test_screening_preferences_and_job_validation(self):
        prefs = ScreeningPreferences(min_qualifying_score=72)
        prefs.validate()
        self.assertEqual(prefs["min_qualifying_score"], 72.0)

        for bad_score in (-1, 101, float("nan"), "high"):
            with self.subTest(bad_score=bad_score):
                with self.assertRaises(ValueError):
                    ScreeningPreferences(min_qualifying_score=bad_score).validate()

        job = Job(title="  Backend Engineer  ", required_skills=["Python"], min_experience=2)
        job.validate()
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.min_experience, 2.0)
        self.assertEqual(job["title"], "Backend Engineer")

        for bad_job in (
            Job(title="   ", required_skills=["Python"], min_experience=1.0),
            Job(title="Dev", required_skills=[], preferred=[], min_experience=1.0),
            Job(title="Dev", required_skills=["Python"], min_experience=-0.5),
            Job(title="Dev", required_skills=["Python"], min_experience=float("inf")),
        ):
            with self.subTest(bad_job=bad_job):
                with self.assertRaises(ValueError):
                    bad_job.validate()

    def test_resume_entity_compatibility_and_readability(self):
        readable = Resume("alice.pdf", "/tmp/alice.pdf", "Python developer with SQL")
        blank = Resume("empty.pdf", "/tmp/empty.pdf", "   \n  ")

        self.assertTrue(readable.has_readable_text())
        self.assertFalse(blank.has_readable_text())
        self.assertEqual(readable["text"], "Python developer with SQL")
        self.assertEqual(readable.get("text"), "Python developer with SQL")


class TestExtractorsAndImporter(unittest.TestCase):

    def _build_docx(self, path: Path, paragraphs: list[str], table_rows: list[list[str]] | None = None):
        doc = Document()
        for line in paragraphs:
            doc.add_paragraph(line)
        if table_rows:
            table = doc.add_table(rows=len(table_rows), cols=len(table_rows[0]))
            for row_idx, row in enumerate(table_rows):
                for col_idx, cell_text in enumerate(row):
                    table.cell(row_idx, col_idx).text = cell_text
        doc.save(path)

    def test_docx_extractor_reads_paragraphs_and_tables_and_handles_corrupt_files(self):
        with TemporaryDirectory() as tmp_dir:
            valid_docx = Path(tmp_dir) / "candidate.docx"
            self._build_docx(
                valid_docx,
                paragraphs=["Backend Developer", "Built REST APIs in Python"],
                table_rows=[["Skill", "Years"], ["Docker", "3"]],
            )
            corrupt_docx = Path(tmp_dir) / "broken.docx"
            corrupt_docx.write_bytes(b"not a valid zip docx archive")

            extractor = DocxTextExtractor()
            text = extractor.extract(valid_docx)
            self.assertIn("Backend Developer", text)
            self.assertIn("Docker | 3", text)
            self.assertEqual(extractor.extract(corrupt_docx), "")

    def test_pdf_extractor_reads_pages_and_handles_corrupt_files(self):
        class _FakePage:
            def __init__(self, content):
                self._content = content

            def extract_text(self):
                return self._content

        class _FakePdfReader:
            def __init__(self, _path):
                self.pages = [_FakePage("Page 1 Python"), _FakePage(""), _FakePage("Page 3 SQL")]

        extractor = PdfTextExtractor()
        with patch("pypdf.PdfReader", _FakePdfReader):
            self.assertEqual(extractor.extract("fake.pdf"), "Page 1 Python\nPage 3 SQL")

        with TemporaryDirectory() as tmp_dir:
            corrupt_pdf = Path(tmp_dir) / "corrupt.pdf"
            corrupt_pdf.write_bytes(b"%PDF-corrupt-content")
            self.assertEqual(extractor.extract(corrupt_pdf), "")

    def test_importer_validates_files_and_registers_custom_extractor(self):
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            empty_pdf = root / "empty.pdf"
            empty_pdf.write_bytes(b"")
            unsupported = root / "notes.txt"
            unsupported.write_text("Python SQL FastAPI", encoding="utf-8")

            importer = ResumeImporter()
            with self.assertRaises(ValueError):
                importer.validate_resume_file(root)
            with self.assertRaises(ValueError):
                importer.validate_resume_file(empty_pdf)
            with self.assertRaises(ValueError):
                importer.validate_resume_file(unsupported)

            # custom TextExtractor subclass handles .txt without modifying ResumeImporter (OCP)
            importer.register_extractor("txt", _DummyTextExtractor())
            importer.validate_resume_file(unsupported)
            resumes = importer.prepare([unsupported])
            self.assertEqual(len(resumes), 1)
            self.assertEqual(resumes[0].text, "Python SQL FastAPI")

    def test_importer_collect_batch_and_prepare_anonymizes_and_skips_pii_only_resumes(self):
        with TemporaryDirectory() as tmp_dir:
            folder = Path(tmp_dir)
            good_docx = folder / "alice_cv.docx"
            pii_only_docx = folder / "only_pii.docx"
            empty_pdf = folder / "blank.pdf"
            ignored_csv = folder / "other.csv"

            self._build_docx(
                good_docx,
                paragraphs=[
                    "Name: Alice Tan",
                    "Email: alice.tan@example.com",
                    "Reach out at +65 9123 4567 or backup@example.org",
                    "   ",
                    "Built Python microservices and PostgreSQL pipelines for 4 years.",
                ],
            )
            self._build_docx(
                pii_only_docx,
                paragraphs=[
                    "Full Name: Bob Lee",
                    "Phone: 9876 5432",
                    "bob@example.com",
                ],
            )
            empty_pdf.write_bytes(b"")
            ignored_csv.write_text("col1,col2\n1,2\n", encoding="utf-8")

            importer = ResumeImporter()
            self.assertEqual(importer.collect_batch(folder / "does_not_exist"), [])

            batch = importer.collect_batch(folder)
            self.assertEqual([p.name for p in batch], ["alice_cv.docx", "only_pii.docx"])

            prepared = importer.prepare(batch)
            self.assertEqual(len(prepared), 1)
            text = prepared[0].anonymized_text
            self.assertNotIn("Alice Tan", text)
            self.assertNotIn("alice.tan@example.com", text)
            self.assertIn("[PHONE REMOVED]", text)
            self.assertIn("[EMAIL REMOVED]", text)
            self.assertIn("Built Python microservices", text)


class TestConsoleUIHelpers(unittest.TestCase):

    def test_skill_parsing_formatting_and_menu_input(self):
        ui = ConsoleUI()
        self.assertEqual(ui._parse_skill_list(" Python, sql , PYTHON , , Docker "), ["Python", "sql", "Docker"])
        self.assertEqual(ui._format_score(None), "Not scored")
        self.assertEqual(ui._format_score(84.5), "84.5 / 100")

        with patch("builtins.input", side_effect=["9", "2"]), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(ui.get_main_menu_choice(), "2")


class TestPdfCandidateReport(unittest.TestCase):

    def test_individual_and_batch_pdf_generation(self):
        report: CandidateReport = PdfCandidateReport()
        candidate = {
            "candidate_id": "C001",
            "file_name": "alice.pdf",
            "job_title": "Backend Engineer",
            "job_id": "J001",
            "final_score": 88.5,
            "status": "SHORTLIST",
            "fast_track": False,
            "recruiter_decision": "pending",
            "skills_score": 90.0,
            "experience_score": 85.0,
            "education_score": 88.0,
            "confidence": "high",
            "skills_present": ["Python", "SQL"],
            "skills_missing": ["Docker"],
            "evidence": "Built Python services",
            "summary": "Strong backend match.",
            "notes": ["All required skills verified."],
        }
        with TemporaryDirectory() as tmp_dir:
            indiv_path = report.generate_individual(candidate, Path(tmp_dir) / "alice_report")
            self.assertTrue(indiv_path.is_file())
            self.assertEqual(indiv_path.suffix, ".pdf")
            self.assertGreater(indiv_path.stat().st_size, 0)

            batch_path = report.generate_batch([candidate], Path(tmp_dir) / "batch.pdf", job={"title": "Backend Engineer", "job_id": "J001"})
            self.assertTrue(batch_path.is_file())
            self.assertGreater(batch_path.stat().st_size, 0)

        pdf_bytes = PdfCandidateReport().to_pdf_bytes(candidate)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertIn("C001", PdfCandidateReport().to_markdown(candidate))

        with self.assertRaises(ValueError):
            report.generate_individual(None, "ignored.pdf")
        with self.assertRaises(ValueError):
            report.generate_batch([], "ignored.pdf")


class TestConsoleUISkillFilter(unittest.TestCase):
    def setUp(self):
        self.ui = ConsoleUI()
        self.c1 = {
            "candidate_id": "C001",
            "file_name": "resume_01_strong.docx",
            "job_id": "J001",
            "job_title": "Data Analyst",
            "final_score": 59,
            "skills_score": 62.5,
            "status": "SECONDARY_REVIEW",
            "fast_track": False,
            "recruiter_decision": "shortlisted",
            "skills_present": ["Python", "SQL", "AWS"],
            "skills_missing": ["Excel", "Agile"],
            "experience_score": 95.0,
            "education_score": 100.0,
            "confidence": "high",
        }
        self.c2 = SimpleNamespace(
            candidate_id="C002",
            file_name="resume_02_missing.docx",
            job_id="J001",
            job_title="Data Analyst",
            final_score=59,
            skills_score=50.0,
            status="SECONDARY_REVIEW",
            fast_track=False,
            recruiter_decision="pending",
            skills_present=["Python", "SQL"],
            skills_missing=["Excel", "AWS", "Agile"],
            experience_score=95.0,
            education_score=75.0,
            confidence="high",
        )
        self.c3 = {
            "candidate_id": "C003",
            "file_name": "resume_03_weak.docx",
            "job_id": "J001",
            "job_title": "Data Analyst",
            "final_score": 23,
            "skills_score": 0.0,
            "status": "SECONDARY_REVIEW",
            "fast_track": False,
            "recruiter_decision": "rejected",
            "skills_present": [],
            "skills_missing": ["Python", "SQL", "Excel"],
            "experience_score": 50.0,
            "education_score": 40.0,
            "confidence": "high",
        }
        self.candidates = [self.c3, self.c1, self.c2]
    def test_collect_skill_filter_parses_and_deduplicates(self):
        with patch("builtins.input", return_value=" Python, sql , python , AWS "):
            skills = self.ui.collect_skill_filter()
        self.assertEqual(skills, ["Python", "sql", "AWS"])
    def test_filter_candidates_by_skills_matches_and_sorts_by_score(self):
        matches = self.ui.filter_candidates_by_skills(
            self.candidates, ["python", "sql"]
        )
        self.assertEqual(len(matches), 2)
        ids = [self.ui._get_candidate_field(c, "candidate_id") for c in matches]
        self.assertEqual(ids, ["C001", "C002"])
    def test_filter_candidates_by_skills_narrows_to_aws(self):
        matches = self.ui.filter_candidates_by_skills(self.candidates, ["AWS"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["candidate_id"], "C001")
    def test_show_skill_filtered_results_prints_no_match_message(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = self.ui.show_skill_filtered_results(
                self.candidates, ["Kubernetes"]
            )
        self.assertEqual(result, [])
        self.assertIn("No candidates matched all requested skills.", buf.getvalue())
class TestConsoleUICandidateComparison(unittest.TestCase):

    def setUp(self):
        self.ui = ConsoleUI()
        self.c1 = {
            "candidate_id": "C001",
            "file_name": "resume_01_strong.docx",
            "job_title": "Data Analyst",
            "final_score": 59,
            "skills_score": 62.5,
            "experience_score": 95.0,
            "education_score": 100.0,
            "status": "SECONDARY_REVIEW",
            "fast_track": False,
            "recruiter_decision": "shortlisted",
            "confidence": "high",
            "skills_present": ["Python", "SQL", "AWS"],
            "skills_missing": ["Excel", "Agile"],
        }
        self.c2 = {
            "candidate_id": "C002",
            "file_name": "resume_02_missing.docx",
            "job_title": "Data Analyst",
            "final_score": 59,
            "skills_score": 50.0,
            "experience_score": 95.0,
            "education_score": 75.0,
            "status": "SECONDARY_REVIEW",
            "fast_track": False,
            "recruiter_decision": "pending",
            "confidence": "high",
            "skills_present": ["Python", "SQL"],
            "skills_missing": ["Excel", "AWS", "Agile"],
        }
    def test_select_candidates_for_comparison_requires_at_least_two(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = self.ui.select_candidates_for_comparison([self.c1])
        self.assertIsNone(result)
        self.assertIn("At least 2 candidates are required", buf.getvalue())
    def test_select_candidates_for_comparison_rejects_duplicate_and_returns_pair(self):
        with patch("builtins.input", side_effect=["C001", "C001", "C002"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                pair = self.ui.select_candidates_for_comparison([self.c1, self.c2])
        self.assertEqual(pair, (self.c1, self.c2))
        self.assertIn("Please select a different candidate ID", buf.getvalue())
    def test_show_candidate_comparison_prints_side_by_side_table(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.ui.show_candidate_comparison(self.c1, self.c2)
        output = buf.getvalue()
        self.assertIn("CANDIDATE SIDE-BY-SIDE COMPARISON", output)
        self.assertIn("C001", output)
        self.assertIn("C002", output)
        self.assertIn("62.5 / 100", output)
        self.assertIn("50 / 100", output)
        self.assertIn("Python, SQL, AWS", output)


if __name__ == "__main__":
    unittest.main()
