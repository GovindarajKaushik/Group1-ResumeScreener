import os
import pytest
import data_manager as dm

@pytest.fixture
def files(tmp_path):
    return{
        "results_files": str(tmp_path / "results.csv"),
        "log_file": str(tmp_path / "log.csv")
    }

def make_result(**changes):
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
             "last_used_year": 2026, "evidence": "6 years of Python"},
            {"name": "Mircosoft", "category": "preferred", "present": False,
             "last_used_year": None, "evidence": ""}  
        ],
        "summary": "Strong fit",
        "notes": ["Must-have bonus +5"],

    }
    results.update(changes)
    return results

def save_one(files, file_name="alice.pdf", job=None, **changes):
    candidate = dm.results_to_candidate(file_name, "resume/" + file_name, make_result(**changes))
    return dm.save_candidate_results(candidate, job,
        results_file=files["results_file"],
        log_file=files["log_file"])

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

def test_log_action_adds_a_timestamped_line(files):
    dm.log_action("TEST_ACTION", "some details", "C001", files["log_file"])
    log = dm.load_log(files["log_file"])
    assert len(log) == 1
    assert log[0]["action"] == "TEST_ACTION"
    assert log[0]["candidate_id"] == "C001"
    assert log[0]["timestamp"] != ""

def test_skills_are_split_into_present_and_missing():
    candidate = dm.result_to_candidate("a.pdf", "resume/a.pdf", make_result())
    ai_result = candidate["ai_result"]
    assert ai_result["skills_present"] == ["Python"]
    assert ai_result["skills_missing"] == ["Mircosoft"]
    assert ai_result["evidence"] == "Python: 6 years of Python"


def test_candidate_row_round_trip():
    candidate = dm.result_to_candidate("a.pdf", "resume/a.pdf", make_result(fast_track=True))
    candidate["candidate_id"] = "C001"
    row = dm.candidate_to_row(dm.flatten_candidate(candidate))
    loaded = dm.row_to_candidate(row)
    assert loaded["file_name"] == "a.pdf"
    assert loaded["final_score"] == 80.0
    assert loaded["fast_track"] is True
    assert loaded["skills_present"] == ["Python"]
    assert loaded["ai_result"]["confidence"] == "high"
