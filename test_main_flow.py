"""Check the orchestrator with real scoring/storage and simulated AI responses."""

import importlib.util
import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import data_manager


def test_main_scores_and_saves_when_debug_write_fails():
    """Keep a successful candidate and an unscored failure despite debug errors."""
    ai_response = {
        "skills": [{
            "name": "Python", "category": "must_have", "present": True,
            "last_used_year": date.today().year, "evidence": "Built Python tools",
        }],
        "experience_score": 80, "education_score": 80,
        "overall_score": 80, "confidence": "high", "summary": "Python developer",
    }
    simulated_ai = SimpleNamespace(
        create_client=Mock(return_value=object()),
        process_resume_ai=Mock(side_effect=[ai_response, ValueError("Invalid API response")]),
    )
    # Replace the AI module before loading main: no .env loading or API access.
    module_spec = importlib.util.spec_from_file_location(
        "screening_flow_test", Path(__file__).with_name("main.py")
    )
    orchestrator = importlib.util.module_from_spec(module_spec)
    with patch.dict(sys.modules, {"ai_manager": simulated_ai}):
        module_spec.loader.exec_module(orchestrator)

    resumes = [
        {"id": "one", "file_name": "good.pdf", "file_path": "good.pdf", "text": "Built Python tools"},
        {"id": "two", "file_name": "failed.pdf", "file_path": "failed.pdf", "text": "Sample text"},
    ]
    job = {"title": "Developer", "required_skills": ["Python"], "preferred": []}

    with TemporaryDirectory() as folder:
        results_file = str(Path(folder) / "results.csv")
        log_file = str(Path(folder) / "audit.csv")

        def save_record(record, resume, evaluation, job_description):
            """Use real storage with temporary output paths for this test."""
            return data_manager.save_screening_record(
                record, resume, evaluation, job_description, results_file, log_file
            )

        with patch.multiple(
            orchestrator,
            collect_inputs=Mock(return_value=(resumes, job, {"min_qualifying_score": 60})),
            save_results_json=Mock(side_effect=ValueError("Debug folder is read-only")),
            save_screening_record=save_record,
            show_message=Mock(), show_error=Mock(), show_progress=Mock(),
            show_summary=Mock(), show_rankings=Mock(),
        ):
            orchestrator.main()
            rows = orchestrator.show_rankings.call_args.args[0]
            assert len(rows) == 1
            assert rows[0]["file_name"] == "good.pdf"
            assert any("Warning:" in call.args[0] for call in orchestrator.show_message.call_args_list)
            orchestrator.show_error.assert_not_called()

        candidates = data_manager.load_all_results(results_file)
        audit = data_manager.load_log(log_file)

    assert len(candidates) == 2
    assert candidates[0]["skills_present"] == ["Python"]
    assert candidates[0]["evidence"] == "Python: Built Python tools"
    assert candidates[0]["recruiter_decision"] == "pending"
    assert candidates[1]["status"] == "RE_ENTRY"
    assert candidates[1]["final_score"] is None
    assert candidates[1]["notes"] == ["Invalid API response"]
    assert len(audit) == 2
    assert all(entry["action"] == "SAVE_RESULT" for entry in audit)


if __name__ == "__main__":
    test_main_scores_and_saves_when_debug_write_fails()
    print("Main orchestration integration test passed.")
