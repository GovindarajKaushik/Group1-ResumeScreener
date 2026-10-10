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