# Run with: python -B test_logic.py
# Fixed sample responses test the logic without an API key or network connection.

import json
import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import logic_manager


JOB = {"required_skills": ["Python"], "preferred": ["SQL"]}


def sample_ai_response():
    # Return a fresh sample so each test can change it independently.
    return {
        "skills": [
            {"name": "Python", "category": "must_have", "present": True,
             "last_used_year": date.today().year, "evidence": "Built Python tools"},
            {"name": "SQL", "category": "preferred", "present": True,
             "last_used_year": date.today().year, "evidence": "Wrote SQL queries"},
        ],
        "experience_score": 80, "education_score": 80, "overall_score": 90,
        "confidence": "high", "summary": "Relevant development experience",
    }


def test_response_fields():
    response = sample_ai_response()
    cleaned = logic_manager.extract_ai_fields(response)
    assert cleaned["experience_score"] == 80
    assert cleaned["skills"][0]["evidence"] == "Built Python tools"
    for invalid in [None, {}, [], {**response, "skills": []},
                    {**response, "experience_score": "invalid"},
                    {**response, "education_score": float("nan")}]:
        assert logic_manager.extract_ai_fields(invalid) is None
        result = logic_manager.evaluate_candidate(invalid, JOB)
        assert result["status"] == "RE_ENTRY"
        assert result["notes"]


def test_weighted_score_and_bonus():
    response = sample_ai_response()
    result = logic_manager.evaluate_candidate(response, JOB)
    # 100 skills * 0.5 + 80 experience * 0.3 + 80 education * 0.2 + 5 bonus.
    assert result["skills_score"] == 100
    assert result["final_score"] == 95
    assert "Must-have bonus +5" in result["notes"]
    assert response == sample_ai_response()
    response.update(experience_score=100, education_score=100)
    assert logic_manager.evaluate_candidate(response, JOB)["final_score"] == 100


def test_missing_required_skill():
    response = sample_ai_response()
    response["skills"][1].update(category="must_have", present=False, evidence="")
    response.update(experience_score=100, education_score=100)
    job = {"required_skills": ["Python", "SQL"], "preferred": []}
    result = logic_manager.evaluate_candidate(response, job)
    assert result["skills_score"] == 50
    assert result["missing_must_haves"] == ["SQL"]
    assert result["final_score"] == 59
    assert result["status"] == "SECONDARY_REVIEW"
    assert result["fast_track"] is False


def test_preferred_skill_weight():
    response = sample_ai_response()
    response["skills"][1].update(present=False, evidence="")
    result = logic_manager.evaluate_candidate(response, JOB)
    # Python earns 1 point; missing preferred SQL contributes 0.5 to the total.
    assert result["skills_score"] == 66.7
    assert result["final_score"] == 78.3
    assert result["missing_must_haves"] == []


def test_missing_evidence_lowers_score():
    response = sample_ai_response()
    response["skills"][0]["evidence"] = ""
    job = {"required_skills": ["Python"], "preferred": []}
    result = logic_manager.evaluate_candidate(response, job)
    assert result["skills_score"] == 0
    assert result["final_score"] == 40
    assert result["status"] == "SECONDARY_REVIEW"
    assert result["missing_must_haves"] == []
    assert result["fast_track"] is False
    assert any("no skill points" in note for note in result["notes"])


def test_skill_recency():
    job = {"required_skills": ["Python"], "preferred": []}
    for years_ago, expected_score in [(4, 100), (5, 50), (6, 50)]:
        response = sample_ai_response()
        response["skills"][0]["last_used_year"] = date.today().year - years_ago
        result = logic_manager.evaluate_candidate(response, job)
        assert result["skills_score"] == expected_score
        assert result["stale_skills"] == ([] if years_ago == 4 else ["Python"])
    response["skills"][0]["last_used_year"] = None
    result = logic_manager.evaluate_candidate(response, job)
    assert result["skills_score"] == 100
    assert any("dates unknown" in note for note in result["notes"])


def test_threshold_and_fast_track():
    response = sample_ai_response()
    result = logic_manager.evaluate_candidate(response, JOB, {"min_qualifying_score": 95})
    assert result["status"] == "SHORTLIST"
    assert result["fast_track"] is True
    assert logic_manager.evaluate_candidate(response, JOB, {"min_qualifying_score": 96})["status"] == "SECONDARY_REVIEW"
    response["confidence"] = "low"
    assert logic_manager.evaluate_candidate(response, JOB)["fast_track"] is False
    response.update(confidence="high", education_score=79)
    assert logic_manager.evaluate_candidate(response, JOB)["fast_track"] is False


def test_batch_scoring_ranking_and_json():
    weak = sample_ai_response()
    weak.update(experience_score=0, education_score=0, overall_score=0)
    weak["skills"][0].update(present=False, evidence="")
    records = {
        "weak": {"file_name": "weak.pdf", "screening_result": weak},
        "failed": {"file_name": "failed.pdf", "screening_result": None},
        "strong": {"file_name": "strong.pdf", "screening_result": sample_ai_response()},
    }
    evaluations = logic_manager.evaluate_results(records, JOB, {})
    assert "failed" not in evaluations
    assert logic_manager.rank_candidates(evaluations) == ["strong", "weak"]
    rows = logic_manager.build_ranking_rows(records, evaluations)
    assert [row["file_name"] for row in rows] == ["strong.pdf", "weak.pdf"]
    # Only this temporary file is written; it is removed when the test finishes.
    with TemporaryDirectory() as folder:
        path = Path(folder) / "sample_results.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        assert logic_manager.load_results(path) == records
        assert logic_manager.evaluate_and_rank(path, JOB, {}) == rows


def test_empty_batch():
    assert logic_manager.evaluate_results({}, JOB, {}) == {}
    assert logic_manager.rank_candidates({}) == []
    assert logic_manager.build_ranking_rows({}, {}) == []


def test_invalid_json_files():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "sample_results.json"
        for content in [None, "not JSON", "[]", '{"sample": {}}']:
            if content is not None:
                path.write_text(content, encoding="utf-8")
            try:
                logic_manager.load_results(path)
            except ValueError as error:
                assert str(error)
            else:
                raise AssertionError("Missing or invalid JSON should raise ValueError")


def run_tests():
    # Run each test, show failures, and return a terminal exit code.
    tests = [
        test_response_fields, test_weighted_score_and_bonus,
        test_missing_required_skill, test_preferred_skill_weight,
        test_missing_evidence_lowers_score, test_skill_recency,
        test_threshold_and_fast_track, test_batch_scoring_ranking_and_json,
        test_empty_batch, test_invalid_json_files,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as error:
            failures += 1
            print(f"FAIL: {test.__name__}: {type(error).__name__}: {error}")
        else:
            print(f"PASS: {test.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run_tests())
