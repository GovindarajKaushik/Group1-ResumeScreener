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

def screen_all(json_path, job_description=None, preferences=None):
    ai_results = load_ai_results(json_path)

    # Derive the skill requirements if no job description was supplied.
    if job_description is None:
        required = []
        preferred = []
        seen = []

        for candidate_name in ai_results:
            ai_data = ai_results[candidate_name]

            if not isinstance(ai_data, dict):
                continue

            if not isinstance(ai_data.get("skills"), list):
                continue

            for skill in ai_data["skills"]:
                if not isinstance(skill, dict):
                    continue

                name = str(skill.get("name", "")).strip()

                if not name or name.lower() in seen:
                    continue

                seen.append(name.lower())

                if str(skill.get("category", "")).strip().lower() == "must_have":
                    required.append(name)
                else:
                    preferred.append(name)

        job_description = {
            "title": "(derived from ai_results.json)",
            "required_skills": required,
            "preferred": preferred,
            "min_experience": 0.0,
            "education": "",
        }

    results = {}

    for name in ai_results:
        results[name] = evaluate_candidate(
            ai_results[name],
            job_description,
            preferences,
        )

    return results

def print_results(results):
    remaining = list(results)

    while len(remaining) > 0:
        best_name = remaining[0]

        # Find the next candidate to display.
        for name in remaining:
            candidate = results[name]
            best = results[best_name]

            if candidate["fast_track"] and not best["fast_track"]:
                best_name = name

            elif candidate["fast_track"] == best["fast_track"]:
                if candidate["final_score"] > best["final_score"]:
                    best_name = name

        result = results[best_name]

        tag = ""

        if result["fast_track"]:
            tag = " [FAST-TRACK]"

        print(
            f"{best_name}: {result['final_score']} "
            f"({result['status']}){tag}"
        )

        if result["status"] != "RE_ENTRY":
            print(
                f"    skills {result['skills_score']} "
                f"| experience {result['experience_score']:.0f} "
                f"| education {result['education_score']:.0f} "
                f"| confidence {result['confidence']}"
            )

        for note in result["notes"]:
            print("    -", note)

        remaining.remove(best_name)


if __name__ == "__main__":
    # Change to True to collect inputs through io_manager.py.
    use_io_manager = False

    if use_io_manager:
        job_description, preferences = get_inputs()
    else:
        job_description = None
        preferences = None

    results = screen_all(
        "ai_results.json",
        job_description,
        preferences,
    )

    print(
        "\n--- Results from ai_results.json (",
        len(results),
        "candidates) ---",
    )

    print_results(results)