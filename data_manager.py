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
    "ai_score",
    "experience_score",
    "education_score",
    "match_label",
    "confidence",
    "skills_present",
    "skills_missing",
    "evidence",
    "summary",
    "tags",
    "status",
    "recruiter_decision",
    "feedback_rating",
    "created_at",
    "updated_at",
]

LOG_FIELDS = ["timestamp", "action", "candidate_id", "details"]
VALID_STATUSES = ["ranked", "secondary_review", "needs_reentry"]
VALID_DECISIONS = ["pending", "shortlisted", "rejected"]
LIST_FIELDS = ["skills_present", "skills_missing", "tags"]
NUMBER_FIELDS = ["final_score", "ai_score", "experience_score", "education_score"]

AI_RESULTS_FIELD = [
    "skills_present",
    "skills_missing",
    "evidence",
    "confidence",
    "summary",
    "experience_score",
    "education_score",
]

SEPARATOR = "; "