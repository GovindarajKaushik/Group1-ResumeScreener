import copy
import json
import os
import tempfile
import unittest
from datetime import date

from OOP.logic_manager import (
    AIResult,
    DebugResultStore,
    Job,
    MustHaveSkillEvidence,
    PreferredSkillEvidence,
    RankingRow,
    RankingService,
    ReEntryEvaluation,
    ScoredEvaluation,
    ScoringEngine,
    ScoringRules,
    ScreeningPreferences,
    ScreeningRecord,
    SkillEvidence,
)


THIS_YEAR = date.today().year


def build_sample_job():
    return Job(
        title="Backend Engineer",
        required_skills=["Python", "SQL"],
        preferred=["Docker"],
        min_experience=3.0,
        education="BSc Computer Science",
    )


def build_strong_ai_payload():
    # Base payload where all required and preferred skills are recent and supported by evidence
    return {
        "skills": [
            {
                "name": "Python",
                "category": "must_have",
                "present": True,
                "last_used_year": THIS_YEAR,
                "evidence": "Built production APIs in Python",
            },
            {
                "name": "SQL",
                "category": "must_have",
                "present": True,
                "last_used_year": THIS_YEAR - 1,
                "evidence": "Wrote PostgreSQL queries and migrations",
            },
            {
                "name": "Docker",
                "category": "preferred",
                "present": True,
                "last_used_year": THIS_YEAR,
                "evidence": "Packaged services into Docker containers",
            },
        ],
        "experience_score": 80,
        "education_score": 80,
        "overall_score": 85,
        "confidence": "high",
        "experience_summary": "4 years backend engineering",
        "education_summary": "BSc Computer Science",
        "summary": "Strong backend fit",
    }


class TestDomainModelsAndPolymorphism(unittest.TestCase):

    def test_skill_evidence_polymorphism_and_weights(self):
        # MustHaveSkillEvidence and PreferredSkillEvidence should behave polymorphically under SkillEvidence
        rules = ScoringRules()
        must_have = SkillEvidence.create_for_category(
            "Python", "must_have", True, THIS_YEAR, "Used Python daily"
        )
        preferred = SkillEvidence.create_for_category(
            "Docker", "preferred", True, THIS_YEAR, "Built Docker images"
        )

        self.assertIsInstance(must_have, MustHaveSkillEvidence)
        self.assertIsInstance(preferred, PreferredSkillEvidence)
        self.assertTrue(must_have.is_mandatory())
        self.assertFalse(preferred.is_mandatory())
        self.assertEqual(must_have.get_weight(rules), 1.0)
        self.assertEqual(preferred.get_weight(rules), 0.5)
        self.assertEqual(must_have.calculate_earned_points(THIS_YEAR, rules), 1.0)
        self.assertEqual(preferred.calculate_earned_points(THIS_YEAR, rules), 0.5)

    def test_job_and_preferences_validation(self):
        # Valid job and preferences pass validation
        job = build_sample_job()
        job.validate()

        # Job without any skills should fail validation
        empty_job = Job(title="Empty Role", required_skills=[], preferred=[])
        with self.assertRaises(ValueError):
            empty_job.validate()

        # Negative minimum experience should fail validation
        neg_exp_job = Job(title="Bad Exp", required_skills=["Python"], min_experience=-1)
        with self.assertRaises(ValueError):
            neg_exp_job.validate()

        # Out-of-range qualifying score should fail validation
        with self.assertRaises(ValueError):
            ScreeningPreferences(min_qualifying_score=105).validate()
        with self.assertRaises(ValueError):
            ScreeningPreferences(min_qualifying_score=-5).validate()


class TestScoringEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ScoringEngine()
        self.job = build_sample_job()

    def test_strong_candidate_gets_bonus_shortlist_and_fast_track(self):
        # 100*0.5 + 80*0.3 + 80*0.2 = 90, plus +5 must-have bonus = 95.0
        result = self.engine.evaluate(build_strong_ai_payload(), self.job)

        self.assertIsInstance(result, ScoredEvaluation)
        self.assertTrue(result.is_scored())
        self.assertEqual(result.skills_score, 100.0)
        self.assertEqual(result.final_score, 95.0)
        self.assertEqual(result.status, "SHORTLIST")
        self.assertTrue(result.fast_track)
        self.assertEqual(result.missing_must_haves, [])

    def test_missing_must_have_caps_score_at_59_and_blocks_fast_track(self):
        # Missing SQL should cap a high-scoring candidate at 59.0
        payload = copy.deepcopy(build_strong_ai_payload())
        payload["skills"][1]["present"] = False
        payload["skills"][1]["evidence"] = ""
        payload["experience_score"] = 95
        payload["education_score"] = 95

        result = self.engine.evaluate(payload, self.job)

        self.assertEqual(result.final_score, 59.0)
        self.assertEqual(result.status, "SECONDARY_REVIEW")
        self.assertFalse(result.fast_track)
        self.assertIn("SQL", result.missing_must_haves)

    def test_present_skill_without_evidence_earns_zero_points(self):
        # Python marked present=True with empty evidence should earn 0 skill points and block the must-have bonus
        payload = copy.deepcopy(build_strong_ai_payload())
        payload["skills"][0]["evidence"] = "   "

        result = self.engine.evaluate(payload, self.job)

        # Earned = 1.0 (SQL) + 0.5 (Docker) = 1.5 out of 2.5 -> 60.0 skills_score
        # Final = 60*0.5 + 80*0.3 + 80*0.2 = 70.0 (no +5 bonus because Python lacked evidence)
        self.assertEqual(result.skills_score, 60.0)
        self.assertEqual(result.final_score, 70.0)
        self.assertFalse(result.fast_track)
        self.assertTrue(any("without supporting evidence" in n for n in result.notes))

    def test_stale_skill_halves_points_and_records_stale_note(self):
        # Skill last used 5+ years ago gets 0.5x recency multiplier
        payload = copy.deepcopy(build_strong_ai_payload())
        payload["skills"][0]["last_used_year"] = THIS_YEAR - 6

        result = self.engine.evaluate(payload, self.job)

        # Earned = 0.5 (stale Python) + 1.0 (SQL) + 0.5 (Docker) = 2.0 / 2.5 = 80.0
        # Computed = 80*0.5 + 80*0.3 + 80*0.2 = 80.0 + 5 bonus = 85.0
        self.assertEqual(result.skills_score, 80.0)
        self.assertEqual(result.final_score, 85.0)
        self.assertIn("Python", result.stale_skills)
        self.assertTrue(any("Recency reduction applied" in n for n in result.notes))

    def test_missing_preferred_skill_reduces_score_less_than_must_have(self):
        # Missing Docker (preferred, weight 0.5) still keeps the must-have bonus
        payload = copy.deepcopy(build_strong_ai_payload())
        payload["skills"][2]["present"] = False
        payload["skills"][2]["evidence"] = ""

        result = self.engine.evaluate(payload, self.job)

        # Earned = 2.0 / 2.5 = 80.0 -> 80*0.5 + 80*0.3 + 80*0.2 + 5 bonus = 85.0
        self.assertEqual(result.skills_score, 80.0)
        self.assertEqual(result.final_score, 85.0)
        self.assertEqual(result.status, "SHORTLIST")
        self.assertEqual(result.missing_must_haves, [])

    def test_preferences_threshold_changes_shortlist_routing(self):
        # Candidate with final_score 85.0 is SHORTLIST at default 60, but SECONDARY_REVIEW if min_qualifying_score=90
        payload = copy.deepcopy(build_strong_ai_payload())
        payload["skills"][2]["present"] = False
        payload["skills"][2]["evidence"] = ""

        strict_prefs = ScreeningPreferences(min_qualifying_score=90.0)
        result = self.engine.evaluate(payload, self.job, preferences=strict_prefs)

        self.assertEqual(result.final_score, 85.0)
        self.assertEqual(result.status, "SECONDARY_REVIEW")

    def test_low_confidence_or_low_criterion_blocks_fast_track(self):
        # Low AI confidence must never fast-track even when final_score >= 90
        low_conf = copy.deepcopy(build_strong_ai_payload())
        low_conf["confidence"] = "low"
        res_low_conf = self.engine.evaluate(low_conf, self.job)
        self.assertEqual(res_low_conf.final_score, 95.0)
        self.assertFalse(res_low_conf.fast_track)

        # Education score below 80 blocks fast-track even if total score >= 90
        low_edu = copy.deepcopy(build_strong_ai_payload())
        low_edu["experience_score"] = 100
        low_edu["education_score"] = 75
        res_low_edu = self.engine.evaluate(low_edu, self.job)
        self.assertGreaterEqual(res_low_edu.final_score, 90.0)
        self.assertFalse(res_low_edu.fast_track)

    def test_final_score_is_clamped_to_100(self):
        # 100 across all criteria + 5 bonus should clamp cleanly at 100.0
        perfect = copy.deepcopy(build_strong_ai_payload())
        perfect["experience_score"] = 100
        perfect["education_score"] = 100

        result = self.engine.evaluate(perfect, self.job)
        self.assertEqual(result.final_score, 100.0)

    def test_malformed_ai_outputs_return_re_entry_evaluation(self):
        # Empty dicts, None, non-dicts, NaN/inf scores, or non-string evidence should safely return ReEntryEvaluation
        bad_nan = copy.deepcopy(build_strong_ai_payload())
        bad_nan["experience_score"] = float("nan")

        bad_inf = copy.deepcopy(build_strong_ai_payload())
        bad_inf["overall_score"] = float("inf")

        bad_evidence = copy.deepcopy(build_strong_ai_payload())
        bad_evidence["skills"][0]["evidence"] = ["not-a-string"]

        for invalid_input in ({}, None, "invalid", 123, {"skills": []}, bad_nan, bad_inf, bad_evidence):
            ev = self.engine.evaluate(invalid_input, self.job)
            self.assertIsInstance(ev, ReEntryEvaluation)
            self.assertFalse(ev.is_scored())
            self.assertEqual(ev.status, "RE_ENTRY")


class TestRankingServiceAndDebugStore(unittest.TestCase):

    def setUp(self):
        self.engine = ScoringEngine()
        self.ranker = RankingService(scorer=self.engine)
        self.job = build_sample_job()

    def test_rank_orders_fast_track_first_then_by_score_and_excludes_failed_records(self):
        strong = build_strong_ai_payload()
        medium = copy.deepcopy(strong)
        medium["experience_score"] = 70
        medium["education_score"] = 70

        weak = copy.deepcopy(strong)
        weak["skills"][1]["present"] = False
        weak["skills"][1]["evidence"] = ""

        records = {
            "cand_weak": ScreeningRecord("cand_weak", "weak.pdf", weak, status="success"),
            "cand_strong": ScreeningRecord("cand_strong", "strong.pdf", strong, status="success"),
            "cand_medium": ScreeningRecord("cand_medium", "medium.pdf", medium, status="success"),
            "cand_failed": ScreeningRecord("cand_failed", "failed.pdf", None, status="error", retryable=True, error="Timeout"),
        }

        evaluations = self.engine.evaluate_records(records, self.job)
        # Failed record with screening_result=None is skipped during evaluation
        self.assertNotIn("cand_failed", evaluations)

        ordered_ids = self.ranker.rank(evaluations)
        self.assertEqual(ordered_ids, ["cand_strong", "cand_medium", "cand_weak"])

        rows = self.ranker.build_rows(records, evaluations)
        self.assertEqual(len(rows), 3)
        self.assertIsInstance(rows[0], RankingRow)
        self.assertEqual(rows[0].file_name, "strong.pdf")
        self.assertEqual(rows[-1].file_name, "weak.pdf")

        # Empty evaluations dictionary returns empty list
        self.assertEqual(self.ranker.rank({}), [])

    def test_debug_result_store_round_trip_and_corrupt_file_handling(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = os.path.join(tmp_dir, "results.json")
            store = DebugResultStore(json_path)

            records = {
                "r1": ScreeningRecord("r1", "alice.pdf", build_strong_ai_payload(), status="success")
            }
            store.save(records)

            loaded = store.load()
            self.assertIn("r1", loaded)
            self.assertIsInstance(loaded["r1"], ScreeningRecord)
            self.assertEqual(loaded["r1"].file_name, "alice.pdf")

            # Missing file raises ValueError
            with self.assertRaises(ValueError):
                store.load(os.path.join(tmp_dir, "does_not_exist.json"))

            # Corrupt JSON raises ValueError
            corrupt_path = os.path.join(tmp_dir, "corrupt.json")
            with open(corrupt_path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            with self.assertRaises(ValueError):
                store.load(corrupt_path)

            # Valid JSON with wrong record shape raises ValueError
            bad_shape_path = os.path.join(tmp_dir, "bad_shape.json")
            with open(bad_shape_path, "w", encoding="utf-8") as f:
                json.dump({"r1": {"wrong_key": 123}}, f)
            with self.assertRaises(ValueError):
                store.load(bad_shape_path)


if __name__ == "__main__":
    unittest.main()
