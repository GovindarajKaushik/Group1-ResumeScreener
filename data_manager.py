import csv
from datetime import datetime

RESULTS_FILE = "candidate_results.csv"
LOG_FILE = "audit_log.csv"

CANDIDATE_FIELDS = [
    "candidate_id",
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
VALID_STATUSES = ["SHORTLISTED", "SECONDARY_REVIEW", "RE_ENTRY"]
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

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()

def read_csv(path, fields):
    create_file_if_missing(path, fields)
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows.append(row)
    return rows

def write_csv(path, fields, rows):
    try:
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    except OSError as error:
        print(f"Error saving '{path}': {error}")
        raise

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
            missing.append(skill["name"])
    return present, missing, evidence_parts


def result_to_candidate(file_name, file_path, result):
    present, missing, evidence_parts = split_skills(result.get("skill_detail", []))

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
        for field in ["created_at", "recruiter_decision", "feedback_rating"]:
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