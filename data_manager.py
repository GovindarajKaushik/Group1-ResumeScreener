import csv
from datetime import datetime

RESULTS_FILE = "candidate_results.csv"
LOG_FILE = "audit_log.csv"

candidate_fields = [
    "candidate_id",
    "job_title",
    "file_name"
    "file_path"
    "final_score",
    "skills_score",
    "ai_overall_score"
    "experience_score",
    "education_score",
    "status",
    "confidence",
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

AI_RESULTS_FIELD = [
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
