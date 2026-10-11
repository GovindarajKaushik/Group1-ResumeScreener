# Logic manager: all scoring and ranking logic lives here.

"""
Entry point for main.py:
    evaluate_and_rank(json_path, job_description, preferences) -> rows for display

Building blocks (also usable on their own):
    load_results(json_path)                                       -> results dict
    evaluate_candidate(ai_response, job_description, preferences) -> result dict
    evaluate_results(results, job_description, preferences)       -> id -> evaluation
    rank_candidates(evaluations)                                  -> ids, best first
    build_ranking_rows(results, evaluations)                      -> rows, best first

The results file is the JSON that main.py writes: id -> record. This module
only relies on two keys in each record:
    record["file_name"]        the resume's file name
    record["screening_result"] the AI's result dict, or null if the API call failed

Error contract: load_results and evaluate_and_rank raise ONLY ValueError
(file missing, unreadable, corrupt, or the wrong shape).
No printing and no input: io_manager shows the output.
"""

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


def evaluate_candidate(ai_response, job_description, preferences=None):
    rules = DEFAULT_RULES.copy()

    if preferences is None:
        preferences = {}

    rules["min_score"] = preferences.get(
        "min_qualifying_score", rules["min_score"]
    )

    result = {
        "final_score": 0.0,
        "skills_score": 0.0,
        "experience_score": 0.0,
        "education_score": 0.0,
        "ai_overall_score": 0.0,
        "confidence": "",
        "status": "",
        "fast_track": False,
        "missing_must_haves": [],
        "stale_skills": [],
        "skill_details": [],
        "experience_summary": "",
        "education_summary": "",
        "summary": "",
        "notes": [],
    }

    ai = extract_ai_fields(ai_response)

    if ai is None:
        result["status"] = "RE_ENTRY"
        result["notes"].append(
            "AI output missing/invalid; resume marked for re-entry"
        )
        return result

    # Match the job requirements with the candidate's skills.
    skills = []

    for category in ["must_have", "preferred"]:
        if category == "must_have":
            names = job_description["required_skills"]
        else:
            names = job_description["preferred"]

        for name in names:
            if name == "":
                continue

            job_skill = {
                "name": name,
                "category": category,
                "present": False,
                "last_used_year": None,
                "evidence": "",
            }

            found = None

            for ai_skill in ai["skills"]:
                if ai_skill["name"].lower() == name.strip().lower():
                    found = ai_skill

            if found is not None:
                job_skill["present"] = found["present"]
                job_skill["last_used_year"] = found["last_used_year"]
                job_skill["evidence"] = found["evidence"]

                if found["category"] != "" and found["category"] != category:
                    result["notes"].append(
                        f"AI labelled '{name}' as {found['category']}; "
                        f"job description says {category}"
                    )
            else:
                # NEW: make a skill the AI left out (or renamed) visible
                result["notes"].append(
                    f"AI did not report '{name}'; treated as not present"
                )

            skills.append(job_skill)

    # Calculate skill points.
    total = 0.0
    earned = 0.0
    missing = []
    stale = []
    has_must_haves = False
    unknown_dates = False
    today_year = date.today().year

    for skill in skills:
        if skill["category"] == "must_have":
            weight = 1.0
            has_must_haves = True

            if not skill["present"]:
                missing.append(skill["name"])
        else:
            weight = rules["preferred_weight"]

        total += weight

        if skill["present"]:
            multiplier = 1.0
            last_year = skill["last_used_year"]

            if last_year is None:
                unknown_dates = True
            elif today_year - last_year >= rules["recency_years"]:
                multiplier = rules["recency_factor"]

            if multiplier < 1.0:
                stale.append(skill["name"])

            earned += weight * multiplier

    skills_score = 0.0

    if total > 0:
        skills_score = 100 * earned / total

    # Combine skills, experience and education scores.
    computed = (
        skills_score * DEFAULT_WEIGHTS["skills"]
        + ai["experience_score"] * DEFAULT_WEIGHTS["experience"]
        + ai["education_score"] * DEFAULT_WEIGHTS["education"]
    )

    final = computed

    # Add the bonus or apply the missing-skill score cap.
    if has_must_haves and len(missing) == 0:
        final += rules["must_have_bonus"]
        result["notes"].append(
            f"Must-have bonus +{rules['must_have_bonus']}"
        )

    elif len(missing) > 0:
        if final > rules["must_have_missing_cap"]:
            final = rules["must_have_missing_cap"]

        result["notes"].append(
            f"Missing must-haves: {', '.join(missing)}; score capped"
        )

    if stale:
        result["notes"].append(
            f"Recency reduction applied: {', '.join(stale)}"
        )

    if unknown_dates:
        result["notes"].append(
            "Some skill dates unknown; no recency penalty applied"
        )

    # Keep the final score between 0 and 100.
    if final > 100:
        final = 100
    elif final < 0:
        final = 0

    final = round(final, 1)

    # Compare our calculated score with the AI's overall score.
    if abs(ai["overall_score"] - computed) >= rules["ai_disagree_gap"]:
        result["notes"].append(
            f"AI overall {ai['overall_score']:.0f} differs from "
            f"computed {computed:.0f}; recommend human review"
        )

    # Store the results.
    result["final_score"] = final
    result["skills_score"] = round(skills_score, 1)
    result["experience_score"] = ai["experience_score"]
    result["education_score"] = ai["education_score"]
    result["ai_overall_score"] = ai["overall_score"]
    result["confidence"] = ai["confidence"]
    result["missing_must_haves"] = missing
    result["stale_skills"] = stale
    result["skill_details"] = skills
    result["experience_summary"] = ai["experience_summary"]
    result["education_summary"] = ai["education_summary"]
    result["summary"] = ai["summary"]

    # Every condition must be met to receive fast-track status.
    if (
        final >= rules["fast_track_score"]
        and len(missing) == 0
        and skills_score >= rules["fast_track_min_criterion"]
        and ai["experience_score"] >= rules["fast_track_min_criterion"]
        and ai["education_score"] >= rules["fast_track_min_criterion"]
        and ai["confidence"] != "low"
    ):
        result["fast_track"] = True

    if final >= rules["min_score"]:
        result["status"] = "SHORTLIST"
    else:
        result["status"] = "SECONDARY_REVIEW"

    if result["fast_track"]:
        result["notes"].append("Fast-track tag")

    if ai["confidence"] == "low":
        result["notes"].append(
            "Low AI confidence: recommend human review"
        )

    return result


def rank_candidates(evaluations):
    """Return the ids in display order: fast-track first, then highest score.

    evaluations: id -> result dict from evaluate_candidate.
    It only sorts; printing is io_manager's job.
    """
    entries = []
    for resume_id, evaluation in evaluations.items():
        entries.append(
            (evaluation["fast_track"], evaluation["final_score"], resume_id)
        )

    # tuples sort left to right: fast_track first, then score
    entries.sort(reverse=True)

    ranked_ids = []
    for fast_track, final_score, resume_id in entries:
        ranked_ids.append(resume_id)
    return ranked_ids


def load_results(json_path):
    """Read the results file written by main.py and return it as a dict.

    Raises ValueError with a readable message if the file is missing,
    unreadable, not valid JSON, or not shaped like id -> record.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            results = json.load(file)
    except FileNotFoundError:
        raise ValueError(f"Results file not found: {json_path}")
    except OSError as e:
        raise ValueError(f"Could not open {json_path}: {e}")
    except ValueError:
        # JSONDecodeError and UnicodeDecodeError are both kinds of ValueError
        raise ValueError(f"{json_path} is not valid UTF-8 JSON")

    if not isinstance(results, dict):
        raise ValueError(f"{json_path} must contain a dictionary of records")

    for resume_id, record in results.items():
        if (
            not isinstance(record, dict)
            or "file_name" not in record
            or "screening_result" not in record
        ):
            raise ValueError(f"Record '{resume_id}' in {json_path} is malformed")

    return results


def evaluate_results(results, job_description, preferences):
    """Score every resume that has an AI result; returns id -> evaluation.

    Records with no AI result (the API call failed) are skipped.
    """
    evaluations = {}
    for resume_id, record in results.items():
        if record["screening_result"] is None:
            continue

        evaluations[resume_id] = evaluate_candidate(
            record["screening_result"], job_description, preferences
        )
    return evaluations


def build_ranking_rows(results, evaluations):
    """Return display rows, best candidate first.

    Each row is {"file_name": str, "evaluation": result dict}.
    """
    rows = []
    for resume_id in rank_candidates(evaluations):
        rows.append({
            "file_name": results[resume_id]["file_name"],
            "evaluation": evaluations[resume_id],
        })
    return rows


def evaluate_and_rank(json_path, job_description, preferences):
    """Read the results file, score every screened resume, return ranked rows.

    Raises ValueError if the results file can't be used.
    """
    results = load_results(json_path)
    evaluations = evaluate_results(results, job_description, preferences)
    return build_ranking_rows(results, evaluations)