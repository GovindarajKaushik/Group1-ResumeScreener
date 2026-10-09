
import json
import re
import sys
from datetime import date

# ---------- Default rules ----------
DEFAULT_RULES = {
    "min_score": 60,
    "fast_track_score": 90,
    "fast_track_min_criterion": 80,
    "must_have_bonus": 5,
    "must_have_missing_cap": 59,
    "recency_years": 5,
    "recency_factor": 0.5,
    "preferred_weight": 0.5,
    "ai_disagree_gap": 25,       # flag if AI overall_score differs this much
}
DEFAULT_WEIGHTS = {"skills": 0.50, "experience": 0.30, "education": 0.20}

VALID_CONFIDENCE = ("low", "medium", "high")

# Top-level keys the AI JSON must contain
REQUIRED_KEYS = {"skills", "experience_score", "education_score",
                 "overall_score", "confidence"}

FENCE = r"^```(?:json)?|```$"    # markdown code fence around JSON



def assign_scores(json_path: str) -> dict:
    """Reads the AI manager's JSON file and returns {candidate_name: fields}.
    fields is None when that candidate's AI output is unusable (-> RE_ENTRY).
    The file may hold a dict of {file_name: AI object}, a list of AI objects,
    or one AI object; markdown fences around the JSON are tolerated."""
    today_year = date.today().year

    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"Could not read '{json_path}': {e}")
        return {}

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        cleaned = re.sub(FENCE, "", text.strip(), flags=re.MULTILINE).strip()
        match = re.search(r"\{.*\}|\[.*\]", cleaned, re.DOTALL)
        try:
            data = json.loads(match.group()) if match else None
        except json.JSONDecodeError:
            data = None
    if data is None:
        print(f"'{json_path}' does not contain valid JSON.")
        return {}

    
    if isinstance(data, dict) and REQUIRED_KEYS.issubset(data):
        entries = {"candidate_1": data}
    elif isinstance(data, dict):
        entries = {str(name): obj for name, obj in data.items()}
    elif isinstance(data, list):
        entries = {}
        for i, obj in enumerate(data, start=1):
            name = (str(obj["file_name"]) if isinstance(obj, dict) and obj.get("file_name")
                    else f"candidate_{i}")
            entries[name] = obj
    else:
        return {}


    results = {}
    for name, ai in entries.items():
        results[name] = None
        if isinstance(ai, str):                       # raw AI reply stored as text
            try:
                ai = json.loads(re.sub(FENCE, "", ai.strip(), flags=re.MULTILINE).strip())
            except json.JSONDecodeError:
                continue
        if (not isinstance(ai, dict) or not REQUIRED_KEYS.issubset(ai)
                or not isinstance(ai["skills"], list) or not ai["skills"]):
            continue

        try:
            skills = []
            for s in ai["skills"]:
                if not isinstance(s, dict):
                    continue
                present = s.get("present") is True or str(s.get("present")).lower() == "true"
                year = None
                if present:
                    try:
                        year = int(s.get("last_used_year"))
                    except (TypeError, ValueError):
                        year = None
                    if year is not None and not 1950 <= year <= today_year:
                        year = None
                skills.append({
                    "name": str(s.get("name", "")).strip(),                  # skills[].name
                    "category": str(s.get("category", "")).strip().lower(),  # skills[].category
                    "present": present,                                      # skills[].present
                    "last_used_year": year,                                  # skills[].last_used_year
                    "evidence": str(s.get("evidence") or "").strip(),        # skills[].evidence
                })

            confidence = str(ai["confidence"]).strip().lower()
            results[name] = {
                "skills": skills,
                "experience_score": max(0.0, min(100.0, float(ai["experience_score"]))),
                "experience_summary": str(ai.get("experience_summary", "")).strip(),
                "education_score": max(0.0, min(100.0, float(ai["education_score"]))),
                "education_summary": str(ai.get("education_summary", "")).strip(),
                "overall_score": max(0.0, min(100.0, float(ai["overall_score"]))),
                "confidence": confidence if confidence in VALID_CONFIDENCE else "low",
                "summary": str(ai.get("summary", "")).strip(),
            }
        except (TypeError, ValueError):
            results[name] = None
    return results



def build_config(ai_results: dict, job_description: dict | None = None,
                 preferences: dict | None = None) -> dict:
    """preferences["min_qualifying_score"] -> cfg["min_score"].
    job_description (from io_manager) supplies the required/preferred skills.
    If job_description is None it is derived from the skills named in ai_results."""
    cfg = dict(DEFAULT_RULES)
    cfg["weights"] = dict(DEFAULT_WEIGHTS)
    cfg["min_score"] = (preferences or {}).get("min_qualifying_score", cfg["min_score"])

    if job_description is None:
        required, preferred, seen = [], [], set()
        for ai in ai_results.values():
            if not ai:
                continue
            for s in ai["skills"]:
                if not s["name"] or s["name"].lower() in seen:
                    continue
                seen.add(s["name"].lower())
                (required if s["category"] == "must_have" else preferred).append(s["name"])
        job_description = {"title": "(derived from ai_results.json)",
                           "required_skills": required, "min_experience": 0.0,
                           "education": "", "preferred": preferred}

    cfg["job_title"] = job_description["title"]
    cfg["required_skills"] = [s for s in job_description["required_skills"] if s]
    cfg["preferred_skills"] = [s for s in job_description["preferred"] if s]
    cfg["min_experience"] = job_description["min_experience"]
    cfg["education_requirement"] = job_description["education"]
    return cfg



def apply_skill_rules(ai_skills: list, cfg: dict) -> tuple[list, float, list, list, list]:
    """One entry per skill in the job description (category comes from the job
    description; the AI supplies present / last_used_year / evidence).
      must-have rule : a required skill that is not present is recorded as missing
      recency rule   : a present skill unused for cfg["recency_years"]+ years
                       counts at cfg["recency_factor"]; unknown year = no penalty
    Returns (skills, skills_score, missing_must_haves, stale_skills, notes)."""
    today_year = date.today().year
    by_name = {s["name"].lower(): s for s in ai_skills}
    skills, missing, stale, notes = [], [], [], []
    total = earned = 0.0

    for category, names in (("must_have", cfg["required_skills"]),
                            ("preferred", cfg["preferred_skills"])):
        for name in names:
            found = by_name.get(name.strip().lower())
            if found and found["category"] and found["category"] != category:
                notes.append(f"AI labelled '{name}' as {found['category']}; "
                             f"job description says {category}")
            present = bool(found and found["present"])
            last_year = found["last_used_year"] if found else None
            skills.append({
                "name": name,
                "category": category,
                "present": present,
                "last_used_year": last_year,
                "evidence": found["evidence"] if found else "",
            })

            weight = 1.0 if category == "must_have" else cfg["preferred_weight"]
            total += weight
            if present:
                factor = 1.0
                if last_year is not None and today_year - last_year >= cfg["recency_years"]:
                    factor = cfg["recency_factor"]
                    stale.append(name)
                earned += weight * factor
            elif category == "must_have":
                missing.append(name)

    skills_score = 100 * earned / total if total else 0.0
    return skills, skills_score, missing, stale, notes



def evaluate_candidate(ai: dict | None, cfg: dict) -> dict:
    """ai is one entry from assign_scores (or None -> RE_ENTRY)."""
    res = {
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
    if ai is None:
        res["status"] = "RE_ENTRY"
        res["notes"].append("AI output missing/invalid; resume marked for re-entry")
        return res

    skills, skills_score, missing, stale, notes = apply_skill_rules(ai["skills"], cfg)
    res["notes"].extend(notes)

    
    w = cfg["weights"]
    computed = (skills_score * w["skills"]
                + ai["experience_score"] * w["experience"]
                + ai["education_score"] * w["education"])
    final = computed

    
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

    
    if abs(ai["overall_score"] - computed) >= cfg["ai_disagree_gap"]:
        res["notes"].append(f"AI overall {ai['overall_score']:.0f} differs from "
                            f"computed {computed:.0f}; recommend human review")

    
    fast_track = (final >= cfg["fast_track_score"]
                  and not missing
                  and min(skills_score, ai["experience_score"], ai["education_score"])
                      >= cfg["fast_track_min_criterion"]
                  and ai["confidence"] != "low")
    if fast_track:
        res["notes"].append("Fast-track tag")
    if ai["confidence"] == "low":
        res["notes"].append("Low AI confidence: recommend human review")

    res.update({
        "final_score": final,
        "skills_score": round(skills_score, 1),
        "experience_score": ai["experience_score"],
        "education_score": ai["education_score"],
        "ai_overall_score": ai["overall_score"],
        "confidence": ai["confidence"],
        "status": "SHORTLIST" if final >= cfg["min_score"] else "SECONDARY_REVIEW",
        "fast_track": fast_track,
        "missing_must_haves": missing,
        "stale_skills": stale,
        "skill_details": skills,
        "experience_summary": ai["experience_summary"],
        "education_summary": ai["education_summary"],
        "summary": ai["summary"],
    })
    return res



def screen_all(json_path: str, job_description: dict | None = None,
               preferences: dict | None = None) -> dict:
    """ai_results.json -> {candidate_name: result}, ranked fast-track first,
    then by final score (ties keep file order)."""
    ai_results = assign_scores(json_path)                               
    cfg = build_config(ai_results, job_description, preferences)         
    results = {name: evaluate_candidate(ai, cfg)                         
               for name, ai in ai_results.items()}

    order = sorted((not r["fast_track"], -r["final_score"], i, name)
                   for i, (name, r) in enumerate(results.items()))
    return {name: results[name] for _, _, _, name in order}



if __name__ == "__main__":
    args = sys.argv[1:]
    ask = "--ask" in args
    args = [a for a in args if a != "--ask"]
    path = args[0] if args else "ai_results.json"

    job_description, preferences = None, None      # derived from JSON / default 60
    if ask:
        from io_manager import collect_job_description, collect_screening_preferences
        job_description = collect_job_description()
        preferences = collect_screening_preferences()

    results = screen_all(path, job_description, preferences)

    print(f"\n--- Results from {path} ({len(results)} candidate(s)) ---")
    for name, r in results.items():
        tag = " [FAST-TRACK]" if r["fast_track"] else ""
        print(f"{name}: {r['final_score']} ({r['status']}){tag}")
        if r["status"] != "RE_ENTRY":
            print(f"    skills {r['skills_score']} | experience {r['experience_score']:.0f} "
                  f"| education {r['education_score']:.0f} | confidence {r['confidence']}")
        for note in r["notes"]:
            print(f"    - {note}")