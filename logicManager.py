import json
import re
import sys
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
DEFAULT_WEIGHTS = {"skills": 0.50, "experience": 0.30, "education": 0.20}

VALID_CONFIDENCE = ("low", "medium", "high")


REQUIRED_KEYS = {"skills", "experience_score", "education_score",
                 "overall_score", "confidence"}


# get data from ai_manager
def get_inputs() -> tuple[dict, dict]:

    from io_manager import collect_job_description, collect_screening_preferences
    job_description = collect_job_description()
    preferences = collect_screening_preferences()
    return job_description, preferences


def build_config(job_description: dict, preferences: dict | None = None) -> dict:
    cfg = dict(DEFAULT_RULES)
    preferences = preferences or {}

    
    cfg["min_score"] = preferences.get("min_qualifying_score", cfg["min_score"])
    cfg["weights"] = dict(DEFAULT_WEIGHTS)


    cfg["job_title"] = job_description["title"]
    cfg["required_skills"] = [s for s in job_description["required_skills"] if s]
    cfg["preferred_skills"] = [s for s in job_description["preferred"] if s]
    cfg["min_experience"] = job_description["min_experience"]
    cfg["education_requirement"] = job_description["education"]
    return cfg

def parse_ai_response(raw) -> dict | None:
    """Accepts the AI reply (string) or an already-parsed dict."""
    if isinstance(raw, dict):
        return raw
    if not raw or not isinstance(raw, str):
        return None
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def clamp_score(value) -> float:
    return max(0.0, min(100.0, float(value)))


def clean_year(value, today_year: int) -> int | None:
    """last_used_year: integer year, or None if null/invalid/out of range."""
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year if 1950 <= year <= today_year else None


def extract_ai_fields(ai_data: dict | None, today_year: int | None = None) -> dict | None:
    """Maps every field of the AI JSON schema to a variable.
    Returns None if unusable (resume is marked RE_ENTRY)."""
    today_year = today_year or date.today().year
    if not ai_data or not REQUIRED_KEYS.issubset(ai_data):
        return None
    if not isinstance(ai_data["skills"], list) or not ai_data["skills"]:
        return None

    try:
        skills = []
        for s in ai_data["skills"]:
            if not isinstance(s, dict):
                continue
            present = s.get("present") is True or str(s.get("present")).lower() == "true"
            skills.append({
                "name": str(s.get("name", "")).strip(),                     # skills[].name
                "category": str(s.get("category", "")).strip().lower(),     # skills[].category
                "present": present,                                         # skills[].present
                "last_used_year": (clean_year(s.get("last_used_year"), today_year)
                                   if present else None),                   # skills[].last_used_year
                "evidence": str(s.get("evidence") or "").strip(),           # skills[].evidence
            })

        confidence = str(ai_data["confidence"]).strip().lower()
        return {
            "skills": skills,
            "experience_score": clamp_score(ai_data["experience_score"]),
            "experience_summary": str(ai_data.get("experience_summary", "")).strip(),
            "education_score": clamp_score(ai_data["education_score"]),
            "education_summary": str(ai_data.get("education_summary", "")).strip(),
            "overall_score": clamp_score(ai_data["overall_score"]),
            "confidence": confidence if confidence in VALID_CONFIDENCE else "low",
            "summary": str(ai_data.get("summary", "")).strip(),
        }
    except (TypeError, ValueError):
        return None
