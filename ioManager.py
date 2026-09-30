#I/O Manager.py

from pathlib import Path 
from typing import TypedDict
import re 

SUPPORTED_FILE_TYPES = {
    ".pdf",
    ".docx",
    ".txt",
}

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024 

class JobDescription(TypedDict):
    job_title: str
    required_skills: list[str]
    minimum_years_experience: int 
    education_requirement: str
    preferred_qualifications: list[str]

class ScreeningPreferences(TypedDict):
    skill_weight: float
    experience_weight: float 
    education_weight: float
    minimum_score: float

class Resume(TypedDict):
    filename: str
    filepath: str
    raw_text: str

class AIInput(TypedDict):
    job_description: JobDescription
    resumes: list[Resume]
    screening_preferences: ScreeningPreferences