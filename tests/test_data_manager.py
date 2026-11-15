# Unit tests for OOP/data_manager.py (CSV/JSON persistence, validation, rollback, and audit trail)

import csv
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from OOP.data_manager import (
    AtomicDebugResultStore,
    AuditLog,
    CandidateMapper,
    CandidateRecord,
    CsvFile,
    CsvRepository,
    FieldCodec,
    ScreeningStore,
    StorageError,
)
from OOP.logic_manager import Job, ScreeningPreferences


class TestFieldCodecAndCandidateRecord(unittest.TestCase):

    def test_codec_round_trips_lists_numbers_and_booleans(self):
        encoded = FieldCodec.list_to_text(["Python", "SQL", "Docker"])
        self.assertEqual(FieldCodec.text_to_list(encoded), ["Python", "SQL", "Docker"])
        self.assertEqual(FieldCodec.text_to_list(""), [])

        self.assertEqual(FieldCodec.text_to_number("0"), 0.0)
        self.assertEqual(FieldCodec.text_to_number("8", as_int=True), 8)
        for blank_or_bad in ("", None, "nan", "inf", "not-a-number"):
            self.assertIsNone(FieldCodec.text_to_number(blank_or_bad))

        self.assertEqual(FieldCodec.number_to_text(80.0), "80")
        self.assertEqual(FieldCodec.number_to_text(82.5), "82.5")
        self.assertEqual(FieldCodec.number_to_text(None), "")
        self.assertEqual(FieldCodec.bool_to_text(True), "yes")
        self.assertEqual(FieldCodec.bool_to_text(False), "no")

    def test_candidate_record_preserves_zero_score_and_enforces_decision_rules(self):
        scored_zero = CandidateRecord(
            file_name="zero.pdf",
            final_score=0.0,
            status="SECONDARY_REVIEW",
        )
        self.assertTrue(scored_zero.can_record_decision())
        scored_zero.set_decision("rejected")
        self.assertEqual(scored_zero.recruiter_decision, "rejected")
        scored_zero.set_feedback(6)
        self.assertEqual(scored_zero.feedback_rating, 6)

        failed = CandidateRecord(file_name="failed.pdf", final_score=None, status="RE_ENTRY")
        self.assertFalse(failed.can_record_decision())
        with self.assertRaises(ValueError):
            failed.set_decision("shortlisted")
        with self.assertRaises(ValueError):
            scored_zero.set_decision("maybe")
        with self.assertRaises(ValueError):
            scored_zero.set_feedback(11)


class TestCsvFileAndDebugStore(unittest.TestCase):

    def test_missing_csv_returns_empty_without_creating_file_and_rejects_bad_columns(self):
        with TemporaryDirectory() as tmp_dir:
            csv_file = CsvFile()
            missing_path = Path(tmp_dir) / "missing.csv"
            self.assertEqual(csv_file.read(str(missing_path), ("a", "b")), [])
            self.assertFalse(missing_path.exists())

            bad_csv = Path(tmp_dir) / "bad.csv"
            bad_csv.write_text("wrong1,wrong2\n1,2\n", encoding="utf-8")
            with self.assertRaises(StorageError):
                csv_file.read(str(bad_csv), ("candidate_id", "final_score"))

    def test_atomic_debug_store_round_trip_and_failure_cleanup(self):
        with TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "nested" / "resume_results.json"
            store = AtomicDebugResultStore(str(target))
            records = {
                "r1": {
                    "file_name": "alice.pdf",
                    "status": "success",
                    "screening_result": {"skills": [], "overall_score": 88},
                }
            }
            store.save(records)
            loaded = store.load()
            self.assertEqual(loaded["r1"].screening_result["overall_score"], 88)

            # writing over an existing directory path must fail cleanly as StorageError
            dir_target = Path(tmp_dir) / "nested"
            with self.assertRaises(StorageError):
                store._writer.write(str(dir_target), lambda f: f.write("data"))
            leftover_temps = [p for p in dir_target.iterdir() if p.name.endswith(".tmp")]
            self.assertEqual(leftover_temps, [])


class TestScreeningStorePersistenceAndFailures(unittest.TestCase):

    def _make_job(self, title: str = "Backend Developer") -> tuple[Job, ScreeningPreferences]:
        prefs = ScreeningPreferences(min_qualifying_score=70.0)
        job = Job(
            title=title,
            required_skills=["Python", "SQL"],
            preferred=["Docker"],
            min_experience=2.0,
            education="BSc Computer Science",
            preferences=prefs,
        )
        return job, prefs

    def test_jobs_and_candidates_persist_across_store_instances(self):
        with TemporaryDirectory() as tmp_dir:
            store1 = ScreeningStore(data_directory=tmp_dir)
            job, prefs = self._make_job()
            job_id = store1.save_job(job, prefs)
            saved_job = store1.load_jobs()[0]

            records = {
                "res_1": {"file_name": "alice.pdf", "status": "success"},
                "res_2": {"file_name": "broken.pdf", "status": "error", "error": "Timeout"},
            }
            resumes = {
                "res_1": {"file_name": "alice.pdf", "file_path": "/tmp/alice.pdf"},
                "res_2": {"file_name": "broken.pdf", "file_path": "/tmp/broken.pdf"},
            }
            evaluations = {
                "res_1": {
                    "final_score": 88.0,
                    "skills_score": 50.0,
                    "experience_score": 85.0,
                    "education_score": 90.0,
                    "ai_overall_score": 86.0,
                    "confidence": "high",
                    "status": "SHORTLIST",
                    "fast_track": True,
                    "skill_details": [
                        {"name": "Python", "present": True, "evidence": "3 yrs Python APIs"},
                        {"name": "Docker", "present": False, "evidence": ""},
                    ],
                    "missing_must_haves": [],
                    "stale_skills": [],
                    "summary": "Strong backend match.",
                    "notes": [],
                },
                "res_2": None,
            }
            saved_ids, failures = store1.save_all(records, resumes, evaluations, saved_job)
            self.assertEqual(failures, [])
            self.assertEqual(len(saved_ids), 2)

            # reload from a fresh ScreeningStore instance to simulate separate runs
            store2 = ScreeningStore(data_directory=tmp_dir)
            reloaded_jobs = store2.load_jobs()
            self.assertEqual(len(reloaded_jobs), 1)
            self.assertEqual(reloaded_jobs[0].job_id, job_id)
            self.assertEqual(reloaded_jobs[0].min_qualifying_score, 70.0)

            reloaded_results = store2.load_results(job_id)
            self.assertEqual(len(reloaded_results), 2)
            self.assertEqual(reloaded_results[0].status, "SHORTLIST")
            self.assertEqual(reloaded_results[1].status, "RE_ENTRY")

            # polymorphic CsvRepository.load_all() call across repositories
            repos: list[CsvRepository] = [store2._jobs, store2._candidates, store2._audit]
            loaded_counts = [len(repo.load_all()) for repo in repos]
            self.assertEqual(loaded_counts, [1, 2, 3])  # 1 CREATE_JOB + 2 SAVE_RESULT

    def test_decisions_search_counts_and_never_reuses_deleted_candidate_id(self):
        with TemporaryDirectory() as tmp_dir:
            store = ScreeningStore(data_directory=tmp_dir)
            job, prefs = self._make_job("Platform Engineer")
            job_id = store.save_job(job, prefs)
            saved_job = store.load_jobs()[0]

            cid_1 = store.save_record(
                {"file_name": "alice.pdf", "status": "success"},
                {"file_name": "alice.pdf", "file_path": "/tmp/alice.pdf"},
                {
                    "final_score": 91.0,
                    "skills_score": 55.0,
                    "experience_score": 90.0,
                    "education_score": 85.0,
                    "ai_overall_score": 90.0,
                    "confidence": "high",
                    "status": "SHORTLIST",
                    "fast_track": True,
                    "skill_details": [{"name": "Python", "present": True, "evidence": "4 yrs"}],
                    "summary": "Great platform background",
                },
                saved_job,
            )
            self.assertEqual(cid_1, "C001")
            self.assertTrue(store.update_decision("C001", "shortlisted"))
            self.assertTrue(store.save_feedback("C001", 9))
            self.assertFalse(store.update_decision("C999", "rejected"))
            self.assertFalse(store.save_feedback("C999", 5))

            matches = store.search_candidates(status="SHORTLIST", decision="shortlisted", keyword="platform")
            self.assertEqual([c.candidate_id for c in matches], ["C001"])
            self.assertEqual(store.count_by_status()["SHORTLIST"], 1)

            # delete job removes C001, records it in audit log, and next candidate gets C002
            removed_count = store.delete_job(job_id)
            self.assertEqual(removed_count, 1)
            self.assertIsNone(store.delete_job("J999"))

            job2_id = store.save_job(*self._make_job("Data Engineer"))
            saved_job2 = store.load_jobs()[0]
            cid_2 = store.save_record(
                {"file_name": "bob.pdf", "status": "success"},
                {"file_name": "bob.pdf", "file_path": "/tmp/bob.pdf"},
                {"final_score": 65.0, "status": "SECONDARY_REVIEW", "skill_details": []},
                saved_job2,
            )
            self.assertEqual(job2_id, "J001")
            self.assertEqual(cid_2, "C002")

    def test_delete_job_restores_candidates_when_job_write_fails(self):
        with TemporaryDirectory() as tmp_dir:
            store = ScreeningStore(data_directory=tmp_dir)
            job_id = store.save_job(*self._make_job())
            saved_job = store.load_jobs()[0]
            cid = store.save_record(
                {"file_name": "alice.pdf", "status": "success"},
                {"file_name": "alice.pdf", "file_path": "/tmp/alice.pdf"},
                {"final_score": 82.0, "status": "SHORTLIST", "skill_details": []},
                saved_job,
            )

            def _failing_delete(_job_id):
                raise StorageError("Simulated jobs.csv write failure")

            store._jobs.delete = _failing_delete
            with self.assertRaises(StorageError):
                store.delete_job(job_id)

            restored = store.get_candidate(cid)
            self.assertIsNotNone(restored)
            self.assertEqual(restored.file_name, "alice.pdf")

    def test_corrupt_candidate_csv_raises_storage_error(self):
        with TemporaryDirectory() as tmp_dir:
            store = ScreeningStore(data_directory=tmp_dir)
            corrupt_path = Path(store.results_path)
            with open(corrupt_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=CandidateRecord.FIELDS)
                writer.writeheader()
                row = {field: "" for field in CandidateRecord.FIELDS}
                row["file_name"] = "missing_id.pdf"
                writer.writerow(row)

            with self.assertRaises(StorageError):
                store.load_results()


if __name__ == "__main__":
    unittest.main()
