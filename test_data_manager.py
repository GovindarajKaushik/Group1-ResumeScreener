import os
import pytest
import data_manager as dm

@pytest.fixture
def files(tmp_path):
    return{
        "results_files": str(tmp_path / "results.csv"),
        "log_file": str(tmp_path / "log.csv")
    }

def make_results(**changes):
    results = {
        "final_score": 80.0,
        "skills_score": 75.0,
        "experience_score": 90.0,
        "education_score": 70.0,
        "ai_overall_score": 85.0,
        "confidence": "high",
        "status": "SHORTLIST",
        "fast_track": False,
        "missing_must_haves": [],
        "stale_skills": [],
        "skill_detail": [
            {"name": "Python", "category": "must_have", "present": True,
             "last_used_year": 2026, "evidence": "4 years of Python"},
            {"name": "Mircosoft", "category": "preferred", "present": False,
             "last_used_year": None, "evidence": ""}  
        ],
        "summary": "Strong fit",
        "notes": ["Must-have bonus +5"],

    }
    results.update(changes)
    return results

def save_one(files, file_name="alice.pdf", job=None, **changes):
    candidate = dm.results_to_candidate(file_name, "resume/" + file_name, make_results(**changes))
    return dm.save_candidate_results(candidate, job, **files)

def test_list_text_round_trip():
    items = ["Python", "SQL", "C++"]
    assert dm.text_to_list(dm.list_to_text(items)) == items
    assert dm.text_to_list("") == []

def test_text_to_number_bad_values():
    assert dm.text_to_number("92.5") == 92.5
    assert dm.text_to_number("7", as_int=True) == 7
    assert dm.text_to_number("") is None
    assert dm.text_to_number("abc") is None

def test_bool_to_text():
    assert dm.bool_to_text(True) == "yes"
    assert dm.bool_to_text(False) == "no"
    assert dm.bool_to_text("True") == "yes"