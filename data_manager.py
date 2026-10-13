import csv
import json
import os
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile

# Keep generated files beside the application, regardless of the launch directory.
DATA_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RESULTS_FILE = os.path.join(DATA_DIRECTORY, "candidate_results.csv")
LOG_FILE = os.path.join(DATA_DIRECTORY, "audit_log.csv")
JOBS_FILE = os.path.join(DATA_DIRECTORY, "jobs.csv")
DEBUG_JSON_PATH = os.path.join(DATA_DIRECTORY, "resume_results.json")

JOB_FIELDS = [
    "job_id", "title", "required_skills", "preferred", "min_experience",
    "education", "min_qualifying_score", "created_at",
]

CANDIDATE_FIELDS = [
    "candidate_id",
    "job_id",
    "job_title",
    "file_name",
    "file_path",
    "final_score",
    "skills_score",
    "experience_score",
    "education_score",
    "ai_overall_score",
    "confidence",
    "status",
    "fast_track",
    "skills_present",
    "skills_missing",
    "missing_must_haves",
    "stale_skills",
    "evidence",
    "summary",
    "notes",
    "recruiter_decision",
    "feedback_rating",
    "created_at",
    "updated_at",
]

LOG_FIELDS = ["timestamp", "action", "candidate_id", "details"]
VALID_STATUSES = ["SHORTLIST", "SECONDARY_REVIEW", "RE_ENTRY"]
VALID_DECISIONS = ["pending", "shortlisted", "rejected"]
LIST_FIELDS = [
    "skills_present", 
    "skills_missing",
    "missing_must_haves",
    "stale_skills", 
    "notes",
]
NUMBER_FIELDS = [
    "final_score", 
    "skills_score", 
    "experience_score", 
    "education_score",
    "ai_overall_score",
    ]

AI_RESULT_FIELD = [
    "skills_present",
    "skills_missing",
    "evidence",
    "confidence",
    "summary",
    "experience_score",
    "education_score",
]

SEPARATOR = " | "

def ensure_storage_folder(path):
    # Create the destination's parent folder if it does not exist.
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def save_results_json(results, path=DEBUG_JSON_PATH):
    # Save screening records as debug JSON; raise ValueError on write failure.
    temporary_path = None
    try:
        ensure_storage_folder(path)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8",
            dir=os.path.dirname(os.path.abspath(path)),
            prefix="json_update_", suffix=".tmp", delete=False,
        ) as file:
            temporary_path = file.name
            json.dump(results, file, indent=2, ensure_ascii=False)
        os.replace(temporary_path, path)
        temporary_path = None
    except (OSError, TypeError, ValueError) as error:
        raise ValueError(f"Could not save results to {path}: {error}") from error
    finally:
        # Remove partial output without hiding the original saving error.
        if temporary_path is not None:
            try:
                os.remove(temporary_path)
            except OSError as error:
                print(f"Could not remove temporary JSON '{temporary_path}': {error}")

def get_timestamp():
    # Use an explicit UTC offset so local and Docker records share a time basis.
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def list_to_text(items):
    texts = []
    for item in items:
        texts.append(str(item))
    return SEPARATOR.join(texts)

def text_to_list(text):
    items = []
    if text:
        for part in text.split(SEPARATOR):
            if part:
                items.append(part)
    return items

def text_to_number(text, as_int=False):
    if text == "" or text is None:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if as_int:
        return int(number)
    return number

def bool_to_text(value):
    if str(value).lower() in ["true", "yes"]:
        return "yes"
    return "no"

def create_file_if_missing(path, fields):
    try:
        with open(path, "r", newline="", encoding="utf-8") as file:
            pass
    except FileNotFoundError:
        write_csv(path, fields, [])

def read_csv(path, fields):
    create_file_if_missing(path, fields)
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        # Candidate IDs are needed for viewing, updates, and generating new IDs.
        if fields == CANDIDATE_FIELDS and "candidate_id" not in (reader.fieldnames or []):
            raise ValueError(f"Saved candidates in '{path}' are missing the candidate_id column.")
        for row in reader:
            if fields == CANDIDATE_FIELDS and not (row.get("candidate_id") or "").strip():
                raise ValueError(f"Saved candidate in '{path}' has an empty candidate ID at CSV line {reader.line_num}.")
            rows.append(row)
    return rows

def write_csv(path, fields, rows):
    # Write a complete temporary CSV before replacing the saved file.
    temporary_path = None
    try:
        ensure_storage_folder(path)
        with NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8",
            dir=os.path.dirname(os.path.abspath(path)),
            prefix="csv_update_", suffix=".tmp", delete=False,
        ) as file:
            temporary_path = file.name
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        # Close the temporary file first so replacement also works on Windows.
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as error:
        print(f"Error saving '{path}': {error}")
        raise
    finally:
        if temporary_path is not None:
            try:
                os.remove(temporary_path)
            except OSError as error:
                print(f"Could not remove temporary CSV '{temporary_path}': {error}")

def log_action(actions, details="", candidate_id="", log_file=LOG_FILE):
    create_file_if_missing(log_file, LOG_FIELDS)
    row = {
        "timestamp": get_timestamp(),
        "action": actions,
        "candidate_id": candidate_id,
        "details": details,
    }
    with open(log_file, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDS)
        writer.writerow(row)

def load_log(log_file=LOG_FILE):
    return read_csv(log_file, LOG_FIELDS)


def save_job(job_description, preferences, jobs_file=JOBS_FILE, log_file=LOG_FILE):
    # Save one screening job and return its ID, keeping identical titles separate.
    rows = read_csv(jobs_file, JOB_FIELDS)
    highest = 0
    for row in rows:
        job_id = row.get("job_id", "")
        if job_id.startswith("J") and job_id[1:].isdigit():
            highest = max(highest, int(job_id[1:]))
    job_id = "J" + str(highest + 1).zfill(3)
    rows.append({
        "job_id": job_id,
        "title": job_description.get("title", ""),
        "required_skills": list_to_text(job_description.get("required_skills", [])),
        "preferred": list_to_text(job_description.get("preferred", [])),
        "min_experience": job_description.get("min_experience", ""),
        "education": job_description.get("education", ""),
        "min_qualifying_score": preferences.get("min_qualifying_score", 60),
        "created_at": get_timestamp(),
    })
    write_csv(jobs_file, JOB_FIELDS, rows)
    log_action("CREATE_JOB", f"{job_id} | {job_description.get('title', '')}", log_file=log_file)
    return job_id


def load_all_jobs(jobs_file=JOBS_FILE):
    # Return saved jobs with lists/numbers restored; missing storage means no jobs.
    if not os.path.exists(jobs_file):
        return []
    jobs = read_csv(jobs_file, JOB_FIELDS)
    for job in jobs:
        if not job.get("job_id") or "title" not in job:
            raise ValueError("Saved job record is missing its job ID or title column.")
        for field in ("required_skills", "preferred"):
            job[field] = text_to_list(job.get(field, ""))
        for field in ("min_experience", "min_qualifying_score"):
            job[field] = text_to_number(job.get(field, ""))
    return jobs


def load_job_results(job_id, results_file=RESULTS_FILE):
    # Return only the selected job's candidates; a blank ID selects older records.
    candidates = load_all_results(results_file)
    return [candidate for candidate in candidates if candidate["job_id"] == job_id]

def split_skills(skill_detail):
    present = []
    missing = []
    evidence_parts = []
    for skill in skill_detail:
        if skill.get("present"):
            present.append(skill["name"])
            if skill.get("evidence"):
                evidence_parts.append(f"{skill['name']}: {skill['evidence']}")
            else:
                evidence_parts.append(f"{skill['name']}: claimed by AI without supporting evidence")
        else:
            missing.append(skill["name"])
    return present, missing, evidence_parts


def result_to_candidate(file_name, file_path, result):
    # Convert a logic result and resume file details into a storage record.
    present, missing, evidence_parts = split_skills(result.get("skill_details", []))

    # The "box inside a box" that io_manager.display_candidate_detail() reads
    ai_result = {
        "skills_present": present,
        "skills_missing": missing,
        "evidence": "; ".join(evidence_parts),
        "confidence": result.get("confidence", ""),
        "summary": result.get("summary", ""),
        "experience_score": result.get("experience_score"),
        "education_score": result.get("education_score"),
    }

    candidate = {
        "file_name": file_name,
        "file_path": file_path,
        "final_score": result.get("final_score"),
        "skills_score": result.get("skills_score"),
        "ai_overall_score": result.get("ai_overall_score"),
        "status": result.get("status", "RE_ENTRY"),
        "fast_track": result.get("fast_track", False),
        "missing_must_haves": result.get("missing_must_haves", []),
        "stale_skills": result.get("stale_skills", []),
        "notes": result.get("notes", []),
        "ai_result": ai_result,
    }
    return candidate


def flatten_candidate(candidate):
    flat = {}
    for key in candidate:
        if key != "ai_result":
            flat[key] = candidate[key]

    ai_result = candidate.get("ai_result", {})
    for key in ai_result:
        if key in CANDIDATE_FIELDS and key not in flat:
            flat[key] = ai_result[key]
    return flat


def candidate_to_row(flat):
    row = {}
    for field in CANDIDATE_FIELDS:
        value = flat.get(field, "")
        if value is None:
            value = ""
        elif field == "fast_track":
            value = bool_to_text(value)
        elif isinstance(value, list):
            value = list_to_text(value)
        row[field] = value
    return row


def row_to_candidate(row):
    candidate = {}
    for field in CANDIDATE_FIELDS:
        candidate[field] = row.get(field) or ""

    for field in LIST_FIELDS:
        candidate[field] = text_to_list(candidate[field])
    for field in NUMBER_FIELDS:
        candidate[field] = text_to_number(candidate[field])
    candidate["fast_track"] = candidate["fast_track"] == "yes"
    candidate["feedback_rating"] = text_to_number(candidate["feedback_rating"], True)

    ai_result = {}
    for field in AI_RESULT_FIELD:
        ai_result[field] = candidate[field]
    candidate["ai_result"] = ai_result
    return candidate

def generate_candidate_id(results_file=RESULTS_FILE):
    rows = read_csv(results_file, CANDIDATE_FIELDS)
    highest = 0
    for row in rows:
        candidate_id = row["candidate_id"]
        if candidate_id.startswith("C") and candidate_id[1:].isdigit():
            number = int(candidate_id[1:])
            if number > highest:
                highest = number
    return "C" + str(highest + 1).zfill(3)

def save_candidate_result(candidate, job_description=None, results_file=RESULTS_FILE, log_file=LOG_FILE):
    flat = flatten_candidate(candidate)

    if job_description and not flat.get("job_title"):
        flat["job_title"] = job_description.get("title") or job_description.get("job_title", "")
    if job_description and not flat.get("job_id"):
        flat["job_id"] = job_description.get("job_id", "")

    status = str(flat.get("status", "")).upper()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Use one of {VALID_STATUSES}")
    flat["status"] = status

    if not flat.get("candidate_id"):
        flat["candidate_id"] = generate_candidate_id(results_file)
    candidate_id = flat["candidate_id"]

    rows = read_csv(results_file, CANDIDATE_FIELDS)
    new_row = candidate_to_row(flat)

    existing_index = -1
    for index in range(len(rows)):
        if rows[index]["candidate_id"] == candidate_id:
            existing_index = index
            break

    if existing_index == -1:
        if new_row["created_at"] == "":
            new_row["created_at"] = get_timestamp()
        if new_row["recruiter_decision"] == "":
            new_row["recruiter_decision"] = "pending"
        new_row["updated_at"] = get_timestamp()
        rows.append(new_row)
        action = "SAVE_RESULT"
    else:
        old_row = rows[existing_index]
        for field in ["created_at", "recruiter_decision", "feedback_rating", "job_id"]:
            if new_row[field] == "":
                new_row[field] = old_row.get(field, "")
        new_row["updated_at"] = get_timestamp()
        rows[existing_index] = new_row
        action = "UPDATE_RESULT"

    write_csv(results_file, CANDIDATE_FIELDS, rows)
    log_action(
        action,
        f"{new_row['file_name']} | score={new_row['final_score']} | status={status}",
        candidate_id,
        log_file,
    )
    return candidate_id

def save_all_results(results, resumes=None, job_description=None, results_file=RESULTS_FILE, log_file=LOG_FILE):
    paths = {}
    if resumes:
        for resume in resumes:
            paths[resume["file_name"]] = resume["file_path"]

    saved_ids = []
    for file_name in results:
        file_path = paths.get(file_name, "")
        candidate = result_to_candidate(file_name, file_path, results[file_name])
        candidate_id = save_candidate_result(
            candidate, job_description, results_file, log_file
        )
        saved_ids.append(candidate_id)
    return saved_ids

def save_failed_resume(file_name, file_path="", job_title="", reason="", results_file=RESULTS_FILE, log_file=LOG_FILE, job_id=""):
    candidate = {
        "file_name": file_name,
        "file_path": file_path,
        "job_title": job_title,
        "job_id": job_id,
        "final_score": None,
        "status": "RE_ENTRY",
        "notes": [reason],
    }
    return save_candidate_result(candidate, None, results_file, log_file)

def save_screening_record(record, resume, logic_result=None, job_description=None, results_file=RESULTS_FILE, log_file=LOG_FILE):
    file_name = record.get("resume_name") or resume.get("file_name", "")
    file_path = resume.get("file_path", "")

    job_title = ""
    if job_description:
        job_title = job_description.get("title") or job_description.get("job_title", "")

    # A successful API request can still produce a result that cannot be scored.
    scoring_failed = logic_result is not None and logic_result.get("status") == "RE_ENTRY"
    if record.get("status") != "success" or logic_result is None or scoring_failed:
        reason = record.get("error") or "No AI result"
        if scoring_failed:
            reason = "; ".join(logic_result.get("notes", [])) or "AI result could not be scored."
        return save_failed_resume(file_name, file_path, job_title, reason,
                                  results_file, log_file,
                                  job_id=job_description.get("job_id", "") if job_description else "")

    candidate = result_to_candidate(file_name, file_path, logic_result)
    return save_candidate_result(candidate, job_description, results_file, log_file)

def load_all_results(results_file=RESULTS_FILE):
    # Viewing a missing results file should return an empty list without creating it.
    if not os.path.exists(results_file):
        return []
    candidates = []
    for row in read_csv(results_file, CANDIDATE_FIELDS):
        candidates.append(row_to_candidate(row))
    return candidates


def get_candidate(candidate_id, results_file=RESULTS_FILE):
    for row in read_csv(results_file, CANDIDATE_FIELDS):
        if row["candidate_id"] == candidate_id:
            return row_to_candidate(row)
    return None

def update_field(candidate_id, field, value, action_name, results_file=RESULTS_FILE, log_file=LOG_FILE):
    rows = read_csv(results_file, CANDIDATE_FIELDS)
    for row in rows:
        if row["candidate_id"] == candidate_id:
            row[field] = value
            row["updated_at"] = get_timestamp()
            write_csv(results_file, CANDIDATE_FIELDS, rows)
            log_action(action_name, f"{field} -> {value}", candidate_id, log_file)
            return True
    return False

def update_recruiter_decision(candidate_id, decision, results_file=RESULTS_FILE, log_file=LOG_FILE):
    if decision not in VALID_DECISIONS:
        raise ValueError(f"Invalid decision '{decision}'. Use one of {VALID_DECISIONS}")
    return update_field(candidate_id, "recruiter_decision", decision, "RECRUITER_DECISION", results_file, log_file)

def save_feedback(candidate_id, rating, results_file=RESULTS_FILE, log_file=LOG_FILE):
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        raise ValueError("Rating must be a whole number from 1 to 10")

    if rating < 1 or rating > 10:
        raise ValueError("Rating must be between 1 and 10")
    return update_field(candidate_id, "feedback_rating", rating, "FEEDBACK", results_file, log_file)

def get_sort_score(candidate):
    if candidate["final_score"] is None:
        return -1
    return candidate["final_score"]

def search_candidates(status=None, decision=None, min_score=None, max_score=None, fast_track=None, job_title=None, keyword=None, sort_by_score=True, results_file=RESULTS_FILE):
    matches = []
    for candidate in load_all_results(results_file):
        score = candidate["final_score"]

        if status and candidate["status"] != status:
            continue
        if decision and candidate["recruiter_decision"] != decision:
            continue
        if min_score is not None and (score is None or score < min_score):
            continue
        if max_score is not None and (score is None or score > max_score):
            continue
        if fast_track is not None and candidate["fast_track"] != fast_track:
            continue
        if job_title and candidate["job_title"].lower() != job_title.lower():
            continue

        if keyword:
            text = " ".join([
                candidate["file_name"],
                candidate["summary"],
                candidate["evidence"],
                " ".join(candidate["skills_present"]),
                " ".join(candidate["skills_missing"]),
                " ".join(candidate["notes"]),
            ])
            if keyword.lower() not in text.lower():
                continue

        matches.append(candidate)

    if sort_by_score:
        matches.sort(key=get_sort_score, reverse=True)
    return matches

def count_by_status(results_file=RESULTS_FILE):
    counts = {}
    for status in VALID_STATUSES:
        counts[status] = 0
    for candidate in load_all_results(results_file):
        if candidate["status"] in counts:
            counts[candidate["status"]] += 1
    return counts

def main():
    results_file = os.path.join(DATA_DIRECTORY, "demo_results.csv")
    log_file = os.path.join(DATA_DIRECTORY, "demo_log.csv")
    job = {"title": "Data Engineer"}

    result = {
        "final_score": 92.5,
        "skills_score": 95.0,
        "experience_score": 90.0,
        "education_score": 85.0,
        "ai_overall_score": 91.0,
        "confidence": "high",
        "status": "SHORTLIST",
        "fast_track": True,
        "missing_must_haves": [],
        "stale_skills": [],
        "skill_details": [
            {"name": "Python", "category": "must_have", "present": True,
             "last_used_year": 2026, "evidence": "6 years of Python"},
            {"name": "Airflow", "category": "preferred", "present": False,
             "last_used_year": None, "evidence": ""},
        ],
        "summary": "Strong fit for the role.",
        "notes": ["Must-have bonus +5", "Fast-track tag"],
    }

    candidate = result_to_candidate("alice.pdf", "resume/alice.pdf", result)
    candidate_id = save_candidate_result(candidate, job, results_file, log_file)
    update_recruiter_decision(candidate_id, "shortlisted", results_file, log_file)
    save_feedback(candidate_id, 9, results_file, log_file)

    print("Fast-track:")
    for c in search_candidates(fast_track=True, results_file=results_file):
        print(" ", c["file_name"], c["final_score"], c["recruiter_decision"])
    print("Counts:", count_by_status(results_file))
    print("Audit log entries:", len(load_log(log_file)))


if __name__ == "__main__":
    main()
