# Integration unit tests for ScreeningBatch, ScreeningService, ReviewSession, and Main
# All AI calls are mocked so the suite runs offline without an API key

import io
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from OOP.data_manager import ScreeningStore
from OOP.io_manager import ConsoleUI, Resume
from OOP.logic_manager import Job, ScreeningBatch, ScreeningPreferences, ScreeningRecord
from OOP.main import CLIController, Main, ReviewSession
from OOP.screening_service import ScreeningService


def sample_job():
    return Job(
        title="Backend Engineer",
        required_skills=["Python", "SQL"],
        preferred=["Docker"],
        min_experience=2.0,
        education="BSc Computer Science",
    )


def sample_ai_response(python_present=True, sql_present=True, overall=88):
    return {
        "skills": [
            {
                "name": "Python",
                "category": "must_have",
                "present": python_present,
                "last_used_year": 2026,
                "evidence": "Built FastAPI services in Python" if python_present else "",
            },
            {
                "name": "SQL",
                "category": "must_have",
                "present": sql_present,
                "last_used_year": 2025,
                "evidence": "Wrote PostgreSQL queries" if sql_present else "",
            },
            {
                "name": "Docker",
                "category": "preferred",
                "present": True,
                "last_used_year": 2026,
                "evidence": "Packaged apps in Docker",
            },
        ],
        "experience_score": 85,
        "experience_summary": "Strong backend experience.",
        "education_score": 80,
        "education_summary": "Relevant degree.",
        "overall_score": overall,
        "confidence": "high",
        "summary": "Solid backend candidate.",
    }


class _StubAI:

    def __init__(self, outcomes):
        # outcomes maps resume_text substring or call order to dict or Exception
        self._outcomes = list(outcomes)
        self.calls = []

    def process_resume(self, job_description, resume_text):
        self.calls.append((job_description, resume_text))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class TestScreeningService(unittest.TestCase):

    def test_end_to_end_batch_screening_retry_and_persistence(self):
        # verify retryable ConnectionError vs fatal ValueError and full CSV/JSON persistence
        with TemporaryDirectory() as tmp_dir:
            store = ScreeningStore(data_directory=tmp_dir)
            ai = _StubAI(
                [
                    ConnectionError("temporary timeout"),
                    ValueError("malformed json"),
                    sample_ai_response(),
                ]
            )
            service = ScreeningService(ai_client=ai, store=store)

            r1 = Resume("alice.pdf", str(Path(tmp_dir) / "alice.pdf"), "Python SQL Docker dev")
            r2 = Resume("bob.pdf", str(Path(tmp_dir) / "bob.pdf"), "Other experience")
            batch = service.start_batch(
                sample_job(), ScreeningPreferences(60.0), [r1, r2]
            )
            self.assertIsInstance(batch, ScreeningBatch)

            progressed = []
            service.screen_all(batch, on_progress=progressed.append)
            self.assertEqual(len(progressed), 2)
            self.assertEqual(batch.success_count(), 0)
            self.assertEqual(batch.retryable_ids(), [r1.id])
            self.assertEqual(len(batch.failed_ids()), 2)

            # only the retryable failure (r1) is re-run; r2 stays non-retryable error
            retried = service.retry_failed(batch)
            self.assertEqual(retried, 1)
            self.assertEqual(batch.success_count(), 1)
            self.assertEqual(batch.retryable_ids(), [])

            rows = service.evaluate_and_rank(batch)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].file_name, "alice.pdf")

            outcome = service.persist_batch(batch)
            self.assertEqual(outcome["job_id"], "J001")
            self.assertEqual(len(outcome["saved_ids"]), 2)
            self.assertEqual(outcome["save_failures"], [])
            self.assertIsNone(outcome["debug_warning"])

            saved = store.load_results("J001")
            self.assertEqual(len(saved), 2)
            by_file = {rec.file_name: rec for rec in saved}
            self.assertEqual(by_file["alice.pdf"].job_id, "J001")
            self.assertEqual(by_file["alice.pdf"].status, "SHORTLIST")
            self.assertEqual(by_file["bob.pdf"].status, "RE_ENTRY")
            self.assertIsNone(by_file["bob.pdf"].final_score)

    def test_debug_json_failure_becomes_warning_without_blocking_csvs(self):
        # verify debug JSON write errors warn cleanly instead of failing persist_batch
        with TemporaryDirectory() as tmp_dir:
            store = ScreeningStore(data_directory=tmp_dir)
            ai = _StubAI([sample_ai_response()])
            service = ScreeningService(ai_client=ai, store=store)
            r1 = Resume("alice.pdf", str(Path(tmp_dir) / "alice.pdf"), "Python SQL")
            batch = service.start_batch(sample_job(), ScreeningPreferences(60.0), [r1])
            service.screen_all(batch)
            service.evaluate_and_rank(batch)

            with patch.object(store, "save_debug", side_effect=OSError("disk full")):
                outcome = service.persist_batch(batch)

            self.assertEqual(outcome["job_id"], "J001")
            self.assertEqual(len(outcome["saved_ids"]), 1)
            self.assertIn("disk full", outcome["debug_warning"])
            self.assertEqual(len(store.load_results("J001")), 1)


class TestReviewSessionAndMainCLI(unittest.TestCase):

    def _seed_store(self, tmp_dir):
        store = ScreeningStore(data_directory=tmp_dir)
        job = sample_job()
        prefs = ScreeningPreferences(60.0)
        ai = _StubAI(
            [
                sample_ai_response(),
                sample_ai_response(python_present=False, overall=40),
                ValueError("bad AI output"),
            ]
        )
        service = ScreeningService(ai_client=ai, store=store)
        resumes = [
            Resume("alice.pdf", str(Path(tmp_dir) / "alice.pdf"), "Python SQL Docker"),
            Resume("bob.pdf", str(Path(tmp_dir) / "bob.pdf"), "SQL Docker"),
            Resume("carol.pdf", str(Path(tmp_dir) / "carol.pdf"), "Some text"),
        ]
        batch = service.start_batch(job, prefs, resumes)
        service.screen_all(batch)
        service.evaluate_and_rank(batch)
        service.persist_batch(batch)
        return store, store.load_results("J001")

    def test_cli_controller_inheritance_and_polymorphism(self):
        # verify Main and ReviewSession both implement CLIController ABC
        self.assertTrue(issubclass(Main, CLIController))
        self.assertTrue(issubclass(ReviewSession, CLIController))

    def test_review_session_skip_jump_resume_and_reentry_block(self):
        # verify jump returns to paused position, skip does not audit, and RE_ENTRY blocks decisions
        with TemporaryDirectory() as tmp_dir:
            store, candidates = self._seed_store(tmp_dir)
            # order: C001 (alice, scored), C002 (bob, scored), C003 (carol, RE_ENTRY)
            # sequence:
            # 1) at C001 -> choose jump ("4") -> target "C002" -> shortlist ("1")
            # 2) returns to paused C001 -> skip ("3")
            # 3) advances to C002 -> reject ("2")
            # 4) advances to C003 (RE_ENTRY, automatically blocked without prompting)
            inputs = ["4", "C002", "1", "3", "2"]
            buf = io.StringIO()
            with patch("builtins.input", side_effect=inputs), redirect_stdout(buf):
                session = ReviewSession(ConsoleUI(), store, candidates)
                session.run()

            output = buf.getvalue()
            self.assertIn("JUMPED REVIEW — return to C001 afterward", output)
            self.assertIn("Returning to C001 in the sequential review.", output)
            self.assertIn("needs successful screening before a decision", output)

            refreshed = {c.candidate_id: c for c in store.load_results("J001")}
            self.assertEqual(refreshed["C001"].recruiter_decision, "pending")
            self.assertEqual(refreshed["C002"].recruiter_decision, "rejected")

            decision_logs = [
                e for e in store.load_audit() if e.action == "RECRUITER_DECISION"
            ]
            # two explicit decisions (shortlist C002 then reject C002); skip is not logged
            self.assertEqual(len(decision_logs), 2)

    def test_main_pre_save_cancellation_writes_nothing(self):
        # Ctrl+C/EOF during retry prompt cancels batch before any CSV/audit/debug file is written
        with TemporaryDirectory() as tmp_dir:
            store = ScreeningStore(data_directory=tmp_dir)
            resumes = [
                Resume("alice.pdf", str(Path(tmp_dir) / "alice.pdf"), "Python SQL")
            ]
            ai = _StubAI([ConnectionError("network down")])
            service = ScreeningService(ai_client=ai, store=store)
            ui = ConsoleUI()

            buf = io.StringIO()
            with (
                patch.object(ui, "collect_inputs", return_value=(resumes, sample_job(), ScreeningPreferences(60))),
                patch.object(ui, "question_api_retry", side_effect=KeyboardInterrupt),
                redirect_stdout(buf),
            ):
                app = Main(ui=ui, store=store, screening=service)
                app.screen_new_batch()

            self.assertIn("Batch cancelled. No data from this batch was saved.", buf.getvalue())
            self.assertEqual(store.load_jobs(), [])
            self.assertEqual(store.load_results(), [])
            self.assertEqual(store.load_audit(), [])
            self.assertFalse(Path(store.debug_path).exists())

    def test_main_missing_api_key_reports_error_early(self):
        # Option 1 fails fast when OPENROUTER_API_KEY is absent; Options 2-4 still work without key
        with TemporaryDirectory() as tmp_dir:
            store = ScreeningStore(data_directory=tmp_dir)
            with patch.dict(os.environ, {}, clear=True), patch("OOP.ai_manager.load_dotenv", lambda: None):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    app = Main(store=store)
                    app.screen_new_batch()
                self.assertIn("Error: creating AI client:", buf.getvalue())

    def test_main_view_filter_compare_pdf_export_and_delete_job(self):
        # exercise Option 2 (view, filter, compare, PDF export) and Option 4 (delete job)
        with TemporaryDirectory() as tmp_dir:
            store, _ = self._seed_store(tmp_dir)
            reports_dir = Path(tmp_dir) / "reports"
            app = Main(store=store, reports_dir=reports_dir)

            # Option 2: select job 1 -> action 2 (filter "Python") -> action 3 (compare C001, C002)
            # -> action 4 (export individual C001 PDF) -> action 4 (export batch PDF) -> Enter -> Option 5 exit
            menu_inputs = [
                "2",
                "1",
                "2",
                "Python",
                "3",
                "C001",
                "C002",
                "4",
                "1",
                "C001",
                "4",
                "2",
                "",
                "4",
                "1",
                "yes",
                "5",
            ]
            buf = io.StringIO()
            with patch("builtins.input", side_effect=menu_inputs), redirect_stdout(buf):
                app.run()

            output = buf.getvalue()
            self.assertIn("CANDIDATE SIDE-BY-SIDE COMPARISON", output)
            self.assertIn("Deleted job J001 and 3 candidate record(s).", output)
            self.assertTrue((reports_dir / "C001_report.pdf").is_file())
            self.assertTrue((reports_dir / "J001_batch_report.pdf").is_file())
            self.assertEqual(store.load_jobs(), [])
            self.assertEqual(store.load_results(), [])


if __name__ == "__main__":
    unittest.main()
