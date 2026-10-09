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