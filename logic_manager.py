import json
from datetime import date


DEFAULT_RULES = {
    "min_score": 60,
    "fast_track_score": 90,
    "fast_track_min_criterion": 80,
    "must_have_bonus": 5,
    "must_have_missing_cap": 59,
    "recency_years": 5,
    "recency_factor": 0.5,
    "preferred_weight": 0.5,
    "ai_disagree_gap": 25,
}

DEFAULT_WEIGHTS = {
    "skills": 0.50,
    "experience": 0.30,
    "education": 0.20,
}

VALID_CONFIDENCE = ("low", "medium", "high")

REQUIRED_KEYS = [
    "skills",
    "experience_score",
    "education_score",
    "overall_score",
    "confidence",
]


def get_inputs():
    from io_manager import collect_job_description, collect_screening_preferences

    job_description = collect_job_description()
    preferences = collect_screening_preferences()

    return job_description, preferences


def load_ai_results(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            ai_results = json.load(file)

    except OSError:
        print("Could not open:", json_path)
        return {}

    except (json.JSONDecodeError, UnicodeDecodeError):
        print("The file does not contain valid UTF-8 JSON.")
        return {}

    if not isinstance(ai_results, dict):
        print("Expected a dictionary of candidate names and AI results.")
        return {}

    if "skills" in ai_results and isinstance(ai_results["skills"], list):
        print("Put each candidate's AI result under their filename.")
        return {}

    return ai_results