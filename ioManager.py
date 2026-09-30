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

def get_required_string(prompt: str) -> str:

    while True:
        value = input(prompt).strip()

        if value:
            return value

        print("Error: This field is required.")
        print("Please try again.")

def get_non_negative_integer(prompt: str) -> int:

    while True:
        value = input(prompt).strip()

        try:
            number = int(value)
        except ValueError:
            print("Error: Please enter a whole number.")
            continue

        if number < 0:
            print("Error: Value cannot be negative.")
            continue

        return number

def get_percentage(prompt: str) -> float:

    while True:
        value = input(prompt).strip()

        try:
            number = float(value)
        except ValueError:
            print("Error: Please enter a number.")
            continue

        if number < 0 or number > 100:
            print("Error: Value must be 0 and 100.")
            continue

        return number

def get_comma_seperated_list(prompt: str) -> list[str]:

    while True:
        value = input(prompt).strip()

        if not value:
            print("Error: At least one value is required.")
            continue

        values = [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

        if values:
            return values

        print("Error: Please enter a vaild values.")

def collect_job_description() -> JobDescription:

    print()
    print("=" * 50)
    print("JOB DESCRIPTION")
    print("=" * 50)

    job_title = get_required_string(
        "Job title: "
    )        

    required_skills = get_comma_seperated_list(
        "Required skills (comma-seperated): "
    )

    minimum_years_experience = get_non_negative_integer(
        "Minimum years of experience: "
    )

    education_requirement = get_required_string(
        "Education requirement: "
    )

    preferred_qualifications = get_comma_seperated_list(
        "Preferred qualifications (comma-seperated): "
    )

    return {
        "job_title": job_title,
        "required_skills": required_skills,
        "minimum_years_experience": minimum_years_experience,
        "education_requirement": education_requirement,
        "preferred_qualifications": preferred_qualifications,
    }
