import os
import pytest
import data_manager as dm

@pytest.fixture
def files(tmp_path):
    return{
        "results_file": str(tmp_path / "results.csv"),
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
    candidate = dm.result_to_candidate(file_name, "resume/" + file_name, make_result(**changes))
    return dm.save_candidate_result(candidate, job,
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

def test_ids_count_up(files):
    assert save_one(files, "a.pdf") == "C001"
    assert save_one(files, "b.pdf") == "C002"


def test_job_title_comes_from_job_description(files):
    candidate_id = save_one(files, job={"title": "Data Engineer"})
    assert dm.get_candidate(candidate_id, files["results_file"])["job_title"] == "Data Engineer"


def test_invalid_status_is_rejected(files):
    with pytest.raises(ValueError):
        save_one(files, status="MAYBE")


def test_resume_text_and_sensitive_fields_are_not_saved(files):
    candidate = dm.result_to_candidate("a.pdf", "resume/a.pdf", make_result())
    candidate["raw_text"] = "full resume text"
    candidate["age"] = 30
    candidate["gender"] = "F"
    candidate_id = dm.save_candidate_result(candidate, None,
        results_file=files["results_file"],
        log_file=files["log_file"])
    loaded = dm.get_candidate(candidate_id, files["results_file"])
    for key in ["raw_text", "age", "gender"]:
        assert key not in loaded
    with open(files["results_file"], encoding="utf-8") as file:
        assert "full resume text" not in file.read()


def test_notes_with_semicolons_survive_a_round_trip(files):
    notes = ["AI labelled 'Docker' as preferred; job description says must_have", "Missing must-haves: SQL, ETL; score capped"]
    candidate_id = save_one(files, notes=notes)
    assert dm.get_candidate(candidate_id, files["results_file"])["notes"] == notes


def test_save_screening_record_success(files):
    record = {"resume_name": "a.pdf", "status": "success", "error": None}
    resume = {"file_name": "a.pdf", "file_path": "resume/a.pdf"}
    candidate_id = dm.save_screening_record(
        record, resume, make_result(), {"title": "Software Engineer"},
        results_file=files["results_file"],
        log_file=files["log_file"])
    loaded = dm.get_candidate(candidate_id, files["results_file"])
    assert loaded["file_name"] == "a.pdf"
    assert loaded["file_path"] == "resume/a.pdf"
    assert loaded["job_title"] == "Software Engineer"
    assert loaded["final_score"] == 80.0
    assert loaded["status"] == "SHORTLIST"


def test_save_screening_record_failed_ai_call(files):
    record = {"resume_name": "b.docx", "status": "error", "error": "Failed after 3 attempts: timeout", "screening_result": None}
    resume = {"file_name": "b.docx", "file_path": "resume/b.docx"}
    candidate_id = dm.save_screening_record(
        record, resume, None, {"title": "Software Engineer"},
        results_file=files["results_file"],
        log_file=files["log_file"])
    loaded = dm.get_candidate(candidate_id, files["results_file"])
    assert loaded["status"] == "RE_ENTRY"
    assert loaded["final_score"] == 0.0
    assert loaded["file_path"] == "resume/b.docx"
    assert loaded["notes"] == ["Failed after 3 attempts: timeout"]


def test_save_all_results_uses_resume_paths(files):
    results = {"a.pdf": make_result(), "b.pdf": make_result(final_score=50.0, status="SECONDARY_REVIEW")}
    resumes = [{"file_name": "a.pdf", "file_path": "folder/a.pdf"}]
    ids = dm.save_all_results(results, resumes, {"title": "Analyst"},
        results_file=files["results_file"],
        log_file=files["log_file"])
    assert ids == ["C001", "C002"]
    assert dm.get_candidate("C001", files["results_file"])["file_path"] == "folder/a.pdf"
    assert dm.get_candidate("C002", files["results_file"])["file_path"] == ""
