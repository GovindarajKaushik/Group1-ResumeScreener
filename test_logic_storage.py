"""Check scoring-to-storage integration without API calls or extra packages."""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import data_manager
import logic_manager


def test_scored_skills_and_evidence_survive_storage():
    """Score a sample response, save it, and verify skills and evidence reload."""
    job_description = {
        "title": "Developer",
        "required_skills": ["Python", "SQL"],
        "preferred": [],
    }
    ai_response = {
        "skills": [
            {
                "name": "Python",
                "category": "must_have",
                "present": True,
                "last_used_year": date.today().year,
                "evidence": "Built Python tools",
            },
            {
                "name": "SQL",
                "category": "must_have",
                "present": False,
                "last_used_year": None,
                "evidence": "",
            },
        ],
        "experience_score": 80,
        "education_score": 80,
        "overall_score": 70,
        "confidence": "high",
        "summary": "Python experience; SQL not demonstrated.",
    }

    result = logic_manager.evaluate_candidate(ai_response, job_description)
    candidate = data_manager.result_to_candidate("sample.pdf", "sample.pdf", result)

    with TemporaryDirectory() as folder:
        results_file = str(Path(folder) / "results.csv")
        log_file = str(Path(folder) / "audit.csv")
        candidate_id = data_manager.save_candidate_result(
            candidate, job_description, results_file, log_file
        )
        loaded = data_manager.get_candidate(candidate_id, results_file)

    assert loaded["ai_result"]["skills_present"] == ["Python"]
    assert loaded["ai_result"]["skills_missing"] == ["SQL"]
    assert loaded["ai_result"]["evidence"] == "Python: Built Python tools"
    assert loaded["final_score"] == result["final_score"]
    assert loaded["missing_must_haves"] == ["SQL"]
    assert loaded["summary"] == ai_response["summary"]


if __name__ == "__main__":
    test_scored_skills_and_evidence_survive_storage()
    print("Scoring-to-storage integration test passed.")
