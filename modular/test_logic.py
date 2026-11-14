import json
import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import logic_manager


JOB = {"required_skills": ["Python"], "preferred": ["SQL"]}


def check(description, actual, expected):
    # Display a readable comparison and fail if the result is incorrect.
    print(f"  {description}")
    print(f"    Expected: {expected} | Actual: {actual}")
    assert actual == expected, description


def sample_ai_response():
    # Return a fresh sample so tests can change it independently.
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


def test_response_validation():
    cleaned = logic_manager.extract_ai_fields(sample_ai_response())
    check("Read experience from the sample", cleaned["experience_score"], 80)
    check("Reject a response with missing fields", logic_manager.extract_ai_fields({}), None)
    result = logic_manager.evaluate_candidate({}, JOB)
    check("Invalid response needs re-entry", result["status"], "RE_ENTRY")


def test_candidate_scoring():
    result = logic_manager.evaluate_candidate(sample_ai_response(), JOB)
    check("Score: 100*0.5 + 80*0.3 + 80*0.2 + 5 bonus", result["final_score"], 95)
    check("Candidate meets the shortlist threshold", result["status"], "SHORTLIST")
    check("Strong candidate receives fast-track", result["fast_track"], True)


def test_skill_rules():
    # Change one sample field at a time to demonstrate the main skill rules.
    for field, value, expected, description in [
        ("present", False, 59, "Missing required Python: final score capped at 59"),
        ("evidence", "", 56.7, "Python without evidence: lower final score"),
        ("last_used_year", date.today().year - 5, 78.3, "Python last used 5 years ago: reduced points"),
    ]:
        response = sample_ai_response()
        response["skills"][0][field] = value
        if field == "present":
            response.update(experience_score=100, education_score=100)
        result = logic_manager.evaluate_candidate(response, JOB)
        check(description, result["final_score"], expected)
    response = sample_ai_response()
    response["skills"][1].update(present=False, evidence="")
    result = logic_manager.evaluate_candidate(response, JOB)
    check("Missing preferred SQL: smaller score reduction", result["final_score"], 78.3)


def test_ranking_and_storage():
    weak = sample_ai_response()
    weak.update(experience_score=0, education_score=0)
    records = {
        "weak": {"file_name": "weak.pdf", "screening_result": weak},
        "failed": {"file_name": "failed.pdf", "screening_result": None},
        "strong": {"file_name": "strong.pdf", "screening_result": sample_ai_response()},
    }
    evaluations = logic_manager.evaluate_results(records, JOB, {})
    check("Failed response excluded; strongest candidate first",
          logic_manager.rank_candidates(evaluations), ["strong", "weak"])
    rows = logic_manager.build_ranking_rows(records, evaluations)
    check("Display follows ranking", [row["file_name"] for row in rows], ["strong.pdf", "weak.pdf"])
    # Temporary files are automatically removed after the test.
    with TemporaryDirectory() as folder:
        path = Path(folder) / "sample_results.json"
        path.write_text(json.dumps(records), encoding="utf-8")
        check("Reloaded JSON matches the samples", logic_manager.load_results(path) == records, True)
        check("Combined load, score and rank matches", logic_manager.evaluate_and_rank(path, JOB, {}) == rows, True)


def test_invalid_json():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "sample_results.json"
        path.write_text("not JSON", encoding="utf-8")
        try:
            logic_manager.load_results(path)
        except ValueError as error:
            check("Invalid JSON produces a readable error", bool(str(error)), True)
        else:
            raise AssertionError("Invalid JSON should raise ValueError")


def test_threshold_and_fast_track():
    # Check the shortlist boundary and conditions that prevent fast-track.
    for threshold, expected in [(95, "SHORTLIST"), (96, "SECONDARY_REVIEW")]:
        result = logic_manager.evaluate_candidate(
            sample_ai_response(), JOB, {"min_qualifying_score": threshold})
        check(f"Score 95 with threshold {threshold}", result["status"], expected)
    for field, value in [("confidence", "low"), ("experience_score", 79), ("education_score", 79)]:
        response = sample_ai_response()
        response[field] = value
        result = logic_manager.evaluate_candidate(response, JOB)
        check(f"{field.replace('_', ' ').capitalize()} = {value}: no fast-track",
              result["fast_track"], False)


def test_score_limits_and_invalid_numbers():
    response = sample_ai_response()
    response.update(experience_score=100, education_score=100)
    result = logic_manager.evaluate_candidate(response, JOB)
    check("Perfect scores plus bonus cannot exceed 100", result["final_score"], 100)
    for value in ["invalid", float("nan"), float("inf")]:
        response = sample_ai_response()
        response["experience_score"] = value
        result = logic_manager.evaluate_candidate(response, JOB)
        check(f"Experience score {value}: needs re-entry", result["status"], "RE_ENTRY")


def test_empty_batch_and_missing_file():
    check("Empty batch has no evaluations", logic_manager.evaluate_results({}, JOB, {}), {})
    check("Empty batch has no ranking", logic_manager.rank_candidates({}), [])
    check("Empty batch has no display rows", logic_manager.build_ranking_rows({}, {}), [])
    with TemporaryDirectory() as folder:
        path = Path(folder) / "missing_results.json"
        try:
            logic_manager.load_results(path)
        except ValueError as error:
            check("Missing JSON file produces a clear error", "not found" in str(error), True)
        else:
            raise AssertionError("Missing JSON should raise ValueError")


def run_tests():
    # Run each test and return a nonzero exit code if any fail.
    print("RESUME SCREENING - OFFLINE LOGIC TESTS")
    print("Sample: Python and SQL supported, experience 80, education 80, confidence high.")
    print("Job: Python required, SQL preferred. No API calls are made.")
    tests = [test_response_validation, test_candidate_scoring, test_skill_rules,
             test_ranking_and_storage, test_invalid_json,
             test_threshold_and_fast_track, test_score_limits_and_invalid_numbers,
             test_empty_batch_and_missing_file]
    failures = 0
    for number, test in enumerate(tests, 1):
        title = test.__name__.removeprefix("test_").replace("_", " ").capitalize()
        print(f"\n[{number}/{len(tests)}] {title}")
        try:
            test()
        except Exception as error:
            failures += 1
            print(f"  FAIL - {type(error).__name__}: {error}")
        else:
            print("  PASS")
    print(f"\nRESULT: {len(tests) - failures}/{len(tests)} tests passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run_tests())
