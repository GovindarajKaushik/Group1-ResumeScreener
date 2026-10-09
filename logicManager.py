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
def align_skills(ai_skills: list, cfg: dict) -> tuple[list, list]:
    """One entry per skill in job_description. Category comes from
    job_description; AI supplies present / last_used_year / evidence.
    Returns (aligned_skills, notes)."""
    by_name = {s["name"].lower(): s for s in ai_skills}
    aligned, notes = [], []
    for category, names in (("must_have", cfg["required_skills"]),
                            ("preferred", cfg["preferred_skills"])):
        for name in names:
            found = by_name.get(name.strip().lower())
            if found and found["category"] and found["category"] != category:
                notes.append(f"AI labelled '{name}' as {found['category']}; "
                             f"job description says {category}")
            aligned.append({
                "name": name,
                "category": category,
                "present": bool(found and found["present"]),
                "last_used_year": found["last_used_year"] if found else None,
                "evidence": found["evidence"] if found else "",
            })
    return aligned, notes

def new_result() -> dict:
    return {
        "final_score": 0.0,
        "skills_score": 0.0,
        "experience_score": 0.0,
        "education_score": 0.0,
        "ai_overall_score": 0.0,
        "confidence": "",
        "status": "",                 # SHORTLIST / SECONDARY_REVIEW / RE_ENTRY
        "fast_track": False,
        "missing_must_haves": [],
        "stale_skills": [],
        "skill_details": [],          # name, category, present, last_used_year, evidence
        "experience_summary": "",
        "education_summary": "",
        "summary": "",
        "notes": [],                  # goes to the audit log
    }


# recency
def recency_multiplier(skill: dict, cfg: dict, today_year: int | None = None) -> float:
    today_year = today_year or date.today().year
    last = skill["last_used_year"]
    if last is None:
        return 1.0                    # unknown: no penalty
    return cfg["recency_factor"] if today_year - last >= cfg["recency_years"] else 1.0


# skill rules
def check_must_haves(skills: list) -> list:
    return [s["name"] for s in skills
            if s["category"] == "must_have" and not s["present"]]


# match score
def skills_match_score(skills: list, cfg: dict) -> tuple[float, list]:
    total = earned = 0.0
    stale = []
    for s in skills:
        w = 1.0 if s["category"] == "must_have" else cfg["preferred_weight"]
        total += w
        if s["present"]:
            m = recency_multiplier(s, cfg)
            if m < 1.0:
                stale.append(s["name"])
            earned += w * m
    return (100 * earned / total if total else 0.0), stale


def calculate_match_score(skills_score: float, experience_score: float,
                          education_score: float, cfg: dict) -> float:
    w = cfg["weights"]
    return (skills_score * w["skills"]
            + experience_score * w["experience"]
            + education_score * w["education"])


# fast track
def is_fast_track(final: float, skills_score: float, experience_score: float,
                  education_score: float, missing: list, confidence: str,
                  cfg: dict) -> bool:
    return (final >= cfg["fast_track_score"]
            and not missing
            and min(skills_score, experience_score, education_score)
                >= cfg["fast_track_min_criterion"]
            and confidence != "low")

def evaluate_candidate(ai_response, job_description: dict,
                       preferences: dict | None = None) -> dict:
    """ai_response: raw AI reply (str) or parsed dict, in the agreed JSON schema."""
    cfg = build_config(job_description, preferences)
    res = new_result()

    ai = extract_ai_fields(parse_ai_response(ai_response))
    if ai is None:
        res["status"] = "RE_ENTRY"
        res["notes"].append("AI output missing/invalid; resume marked for re-entry")
        return res

    skills, align_notes = align_skills(ai["skills"], cfg)
    res["notes"].extend(align_notes)

    skills_score, stale = skills_match_score(skills, cfg)
    missing = check_must_haves(skills)
    final = calculate_match_score(skills_score, ai["experience_score"],
                                  ai["education_score"], cfg)
    computed = final

    if any(s["category"] == "must_have" for s in skills) and not missing:
        final += cfg["must_have_bonus"]
        res["notes"].append(f"Must-have bonus +{cfg['must_have_bonus']}")
    elif missing:
        final = min(final, cfg["must_have_missing_cap"])
        res["notes"].append(f"Missing must-haves: {', '.join(missing)}; score capped")

    if stale:
        res["notes"].append(f"Recency reduction applied: {', '.join(stale)}")
    if any(s["present"] and s["last_used_year"] is None for s in skills):
        res["notes"].append("Some skill dates unknown; no recency penalty applied")

    final = round(max(0, min(100, final)), 1)

    # AI's own overall_score is a cross-check, not part of the final score
    if abs(ai["overall_score"] - computed) >= cfg["ai_disagree_gap"]:
        res["notes"].append(f"AI overall {ai['overall_score']:.0f} differs from "
                            f"computed {computed:.0f}; recommend human review")

    res.update({
        "final_score": final,
        "skills_score": round(skills_score, 1),
        "experience_score": ai["experience_score"],
        "education_score": ai["education_score"],
        "ai_overall_score": ai["overall_score"],
        "confidence": ai["confidence"],
        "missing_must_haves": missing,
        "stale_skills": stale,
        "skill_details": skills,
        "experience_summary": ai["experience_summary"],
        "education_summary": ai["education_summary"],
        "summary": ai["summary"],
    })
    res["fast_track"] = is_fast_track(final, skills_score, ai["experience_score"],
                                      ai["education_score"], missing,
                                      ai["confidence"], cfg)
    res["status"] = "SHORTLIST" if final >= cfg["min_score"] else "SECONDARY_REVIEW"
    if res["fast_track"]:
        res["notes"].append("Fast-track tag")
    if ai["confidence"] == "low":
        res["notes"].append("Low AI confidence: recommend human review")
    return res


def rank_candidates(results: dict) -> list:
    """results = {file_name: result dict}; fast-track first, then score."""
    return sorted(results.items(),
                  key=lambda kv: (kv[1]["fast_track"], kv[1]["final_score"]),
                  reverse=True)

def load_ai_results(json_path: str) -> dict:
    """Reads the AI manager's JSON file. Returns {candidate_name: ai_json_object}.
    Accepts a file holding:
      - a dict of {file_name: AI object}   (your ai_results.json)
      - a list of AI objects               (keyed by "file_name" or candidate_N)
      - a single AI object                 (keyed "candidate_1")"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"Could not read '{json_path}': {e}")
        return {}

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = parse_ai_response(text)      # tolerates ``` fences / extra text
    if data is None:
        print(f"'{json_path}' does not contain valid JSON.")
        return {}

    if isinstance(data, dict) and REQUIRED_KEYS.issubset(data):
        return {"candidate_1": data}
    if isinstance(data, dict):
        return {str(name): obj for name, obj in data.items()}
    if isinstance(data, list):
        results = {}
        for i, obj in enumerate(data, start=1):
            name = f"candidate_{i}"
            if isinstance(obj, dict) and obj.get("file_name"):
                name = str(obj["file_name"])
            results[name] = obj
        return results
    return {}


def job_description_from_ai_results(ai_results: dict) -> dict:
    """Builds a job_description (same shape io_manager returns) from the skills
    named in the AI results, so ai_results.json can be screened without typing
    the job requirements again. Skill order follows first appearance."""
    required, preferred, seen = [], [], set()
    for ai_data in ai_results.values():
        if not isinstance(ai_data, dict) or not isinstance(ai_data.get("skills"), list):
            continue
        for s in ai_data["skills"]:
            if not isinstance(s, dict):
                continue
            name = str(s.get("name", "")).strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            if str(s.get("category", "")).strip().lower() == "must_have":
                required.append(name)
            else:
                preferred.append(name)
    return {
        "title": "(derived from ai_results.json)",
        "required_skills": required,
        "min_experience": 0.0,
        "education": "",
        "preferred": preferred,
    }

def screen_all(json_path: str, job_description: dict | None = None,
               preferences: dict | None = None) -> dict:
    """Loads ai_results.json and runs every candidate through evaluate_candidate.
    job_description / preferences normally come from get_inputs() (io_manager);
    if job_description is None it is derived from the JSON's own skill list."""
    ai_results = load_ai_results(json_path)
    if job_description is None:
        job_description = job_description_from_ai_results(ai_results)
    return {name: evaluate_candidate(obj, job_description, preferences)
            for name, obj in ai_results.items()}


def print_results(results: dict) -> None:
    for name, r in rank_candidates(results):
        tag = " [FAST-TRACK]" if r["fast_track"] else ""
        print(f"{name}: {r['final_score']} ({r['status']}){tag}")
        if r["status"] != "RE_ENTRY":
            print(f"    skills {r['skills_score']} | experience {r['experience_score']:.0f} "
                  f"| education {r['education_score']:.0f} | confidence {r['confidence']}")
        for note in r["notes"]:
            print(f"    - {note}")


if __name__ == "__main__":
    args = sys.argv[1:]
    ask = "--ask" in args
    args = [a for a in args if a != "--ask"]
    path = args[0] if args else "ai_results.json"

    if ask:
        job_description, preferences = get_inputs()      # from io_manager
    else:
        job_description, preferences = None, None        # derived from JSON / default 60

    results = screen_all(path, job_description, preferences)
    print(f"\n--- Results from {path} ({len(results)} candidate(s)) ---")
    print_results(results)
