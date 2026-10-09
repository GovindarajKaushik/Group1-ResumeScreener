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

def extract_ai_fields(raw):
    if not isinstance(raw, dict):
        return None

    # Check that all required fields exist.
    for key in REQUIRED_KEYS:
        if key not in raw:
            return None

    if not isinstance(raw["skills"], list):
        return None

    if len(raw["skills"]) == 0:
        return None

    ai = {}

    # Convert scores to numbers and keep them between 0 and 100.
    score_fields = [
        "experience_score",
        "education_score",
        "overall_score",
    ]

    for field in score_fields:
        try:
            score = float(raw[field])
        except (TypeError, ValueError, OverflowError):
            return None

        # Reject invalid numeric values such as infinity and NaN.
        if not (float("-inf") < score < float("inf")):
            return None

        if score < 0:
            score = 0.0
        elif score > 100:
            score = 100.0

        ai[field] = score

    ai["skills"] = []
    current_year = date.today().year

    # Clean each skill's information.
    for skill in raw["skills"]:
        if not isinstance(skill, dict):
            continue

        cleaned_skill = {}
        cleaned_skill["name"] = str(skill.get("name", "")).strip()
        cleaned_skill["category"] = str(
            skill.get("category", "")
        ).strip().lower()

        cleaned_skill["present"] = False

        if str(skill.get("present")).lower() == "true":
            cleaned_skill["present"] = True

        cleaned_skill["last_used_year"] = None

        if cleaned_skill["present"]:
            try:
                year = int(skill.get("last_used_year"))

                if year >= 1950 and year <= current_year:
                    cleaned_skill["last_used_year"] = year

            except (TypeError, ValueError, OverflowError):
                cleaned_skill["last_used_year"] = None

        evidence = skill.get("evidence", "")

        if evidence is None:
            evidence = ""

        cleaned_skill["evidence"] = str(evidence).strip()
        ai["skills"].append(cleaned_skill)

    if len(ai["skills"]) == 0:
        return None

    confidence = str(raw["confidence"]).strip().lower()

    if confidence not in VALID_CONFIDENCE:
        confidence = "low"

    ai["confidence"] = confidence

    for field in ["experience_summary", "education_summary", "summary"]:
        ai[field] = str(raw.get(field, "")).strip()

    return ai