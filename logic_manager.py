# logic_manager.py
from datetime import date

# ---------- Default rules (non-weight settings) ----------
DEFAULT_RULES = {
    "min_score": 60,
    "fast_track_score": 90,
    "fast_track_min_criterion": 80,
    "must_have_bonus": 5,
    "must_have_missing_cap": 59,
    "recency_years": 5,
    "recency_factor": 0.5,
    "preferred_weight": 0.5,
}

REQUIRED_KEYS = {"skills", "experience_score", "education_score",
                 "overall_score", "confidence"}


# ---------- Config: weights come from the I/O Manager ----------
def build_config(preferences: dict | None = None) -> dict:
    """Turn ScreeningPreferences (percentages) into the config used below.
    Falls back to 50/30/20 and the default minimum score if none given."""
    cfg = dict(DEFAULT_RULES)
    if preferences:
        total = (preferences["skill_weight"]
                 + preferences["experience_weight"]
                 + preferences["education_weight"])
        cfg["weights"] = {
            "skills": preferences["skill_weight"] / total,
            "experience": preferences["experience_weight"] / total,
            "education": preferences["education_weight"] / total,
        }
        cfg["min_score"] = preferences["minimum_score"]
    else:
        cfg["weights"] = {"skills": 0.50, "experience": 0.30, "education": 0.20}
    return cfg


# ---------- Result builder (replaces the dataclass) ----------
def new_result() -> dict:
    return {
        "final_score": 0.0,
        "skills_score": 0.0,
        "experience_score": 0.0,
        "education_score": 0.0,
        "status": "",                # SHORTLIST / SECONDARY_REVIEW / RE_ENTRY
        "fast_track": False,
        "missing_must_haves": [],
        "stale_skills": [],
        "notes": [],                 # goes to the audit log
    }


# ---------- 1. Assign scores from parsed AI data ----------
def assign_scores(ai_data: dict) -> dict | None:
    """Validate and clamp scores. Returns None if unusable (mark for re-entry)."""
    if not ai_data or not REQUIRED_KEYS.issubset(ai_data):
        return None
    clamp = lambda v: max(0, min(100, float(v)))
    try:
        return {
            "experience": clamp(ai_data["experience_score"]),
            "education": clamp(ai_data["education_score"]),
            "ai_overall": clamp(ai_data["overall_score"]),
            "confidence": ai_data["confidence"],
            "skills": ai_data["skills"],
        }
    except (TypeError, ValueError):
        return None


# ---------- 2. Experience / recency rules ----------
def recency_multiplier(skill: dict, cfg: dict, today_year: int | None = None) -> float:
    today_year = today_year or date.today().year
    last = skill.get("last_used_year")
    if last is None:
        return 1.0   # unknown: no penalty
    if today_year - int(last) >= cfg["recency_years"]:
        return cfg["recency_factor"]
    return 1.0


# ---------- 3. Must-have skill rules ----------
def check_must_haves(skills: list) -> list:
    return [s["name"] for s in skills
            if s.get("category") == "must_have" and not s.get("present")]


# ---------- 4. Match score calculation ----------
def skills_match_score(skills: list, cfg: dict) -> tuple[float, list]:
    total = earned = 0.0
    stale = []
    for s in skills:
        w = 1.0 if s.get("category") == "must_have" else cfg["preferred_weight"]
        total += w
        if s.get("present"):
            m = recency_multiplier(s, cfg)
            if m < 1.0:
                stale.append(s["name"])
            earned += w * m
    return (100 * earned / total if total else 0.0), stale


def calculate_match_score(skills_score: float, exp_score: float,
                          edu_score: float, cfg: dict) -> float:
    w = cfg["weights"]
    return (skills_score * w["skills"]
            + exp_score * w["experience"]
            + edu_score * w["education"])


# ---------- 5. Fast-track filter ----------
def is_fast_track(final: float, skills_score: float, exp: float, edu: float,
                  missing: list, confidence: str, cfg: dict) -> bool:
    return (final >= cfg["fast_track_score"]
            and not missing
            and min(skills_score, exp, edu) >= cfg["fast_track_min_criterion"]
            and confidence != "low")


# ---------- Orchestrator: final score + candidate status ----------
def evaluate_candidate(ai_data: dict, preferences: dict | None = None) -> dict:
    cfg = build_config(preferences)
    res = new_result()

    scores = assign_scores(ai_data)
    if scores is None:
        res["status"] = "RE_ENTRY"
        res["notes"].append("AI output missing/invalid; resume marked for re-entry")
        return res

    skills_score, stale = skills_match_score(scores["skills"], cfg)
    missing = check_must_haves(scores["skills"])
    final = calculate_match_score(skills_score, scores["experience"],
                                  scores["education"], cfg)

    has_must_haves = any(s.get("category") == "must_have" for s in scores["skills"])
    if has_must_haves and not missing:
        final += cfg["must_have_bonus"]
        res["notes"].append(f"Must-have bonus +{cfg['must_have_bonus']}")
    elif missing:
        final = min(final, cfg["must_have_missing_cap"])
        res["notes"].append(f"Missing must-haves: {', '.join(missing)}; score capped")

    if stale:
        res["notes"].append(f"Recency reduction applied: {', '.join(stale)}")
    if any(s.get("present") and s.get("last_used_year") is None
           for s in scores["skills"]):
        res["notes"].append("Some skill dates unknown; no recency penalty applied")

    final = round(max(0, min(100, final)), 1)

    res["final_score"] = final
    res["skills_score"] = round(skills_score, 1)
    res["experience_score"] = scores["experience"]
    res["education_score"] = scores["education"]
    res["missing_must_haves"] = missing
    res["stale_skills"] = stale
    res["fast_track"] = is_fast_track(final, skills_score, scores["experience"],
                                      scores["education"], missing,
                                      scores["confidence"], cfg)
    res["status"] = "SHORTLIST" if final >= cfg["min_score"] else "SECONDARY_REVIEW"
    if res["fast_track"]:
        res["notes"].append("Fast-track tag")
    if scores["confidence"] == "low":
        res["notes"].append("Low AI confidence: recommend human review")
    return res


def rank_candidates(results: dict) -> list:
    """results = {candidate_id: result dict}; fast-track first, then score."""
    return sorted(results.items(),
                  key=lambda kv: (kv[1]["fast_track"], kv[1]["final_score"]),
                  reverse=True)