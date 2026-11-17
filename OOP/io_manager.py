import math
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ScreeningPreferences:
    """Value object representing screening configuration thresholds."""

    min_qualifying_score: float = 60.0

    def validate(self) -> None:
        """Validate that the qualifying score is a finite number between 0 and 100."""
        if (
            not isinstance(self.min_qualifying_score, (int, float))
            or not math.isfinite(self.min_qualifying_score)
            or not (0 <= float(self.min_qualifying_score) <= 100)
        ):
            raise ValueError("Minimum qualifying score must be between 0 and 100.")
        self.min_qualifying_score = float(self.min_qualifying_score)

    def __getitem__(self, key: str):
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


@dataclass
class Job:
    """Entity representing a job description and its screening requirements."""

    title: str
    required_skills: list[str] = field(default_factory=list)
    preferred: list[str] = field(default_factory=list)
    min_experience: float = 0.0
    education: str = ""
    job_id: str | None = None
    created_at: datetime | str | None = None
    min_qualifying_score: float | None = None

    def validate(self) -> None:
        """Validate job fields according to domain rules."""
        if not self.title or not self.title.strip():
            raise ValueError("Job title cannot be empty.")
        self.title = self.title.strip()

        if (
            not isinstance(self.min_experience, (int, float))
            or not math.isfinite(self.min_experience)
            or self.min_experience < 0
        ):
            raise ValueError(
                "Minimum experience must be a finite, nonnegative number."
            )
        self.min_experience = float(self.min_experience)

    def __getitem__(self, key: str):
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


class Resume:
    """Transient entity representing an imported and anonymized candidate resume."""

    def __init__(
        self,
        file_name: str,
        file_path: str,
        anonymized_text: str = "",
        resume_id: str | None = None,
    ):
        self.id: str = resume_id or uuid.uuid4().hex
        self.file_name: str = file_name
        self.file_path: str = str(file_path)
        self._anonymized_text: str = anonymized_text

    @property
    def anonymized_text(self) -> str:
        """Return the anonymized resume text."""
        return self._anonymized_text

    @property
    def text(self) -> str:
        """Alias for anonymized_text for backward compatibility."""
        return self._anonymized_text

    def has_readable_text(self) -> bool:
        """Return True if non-empty readable text remains after cleaning and anonymization."""
        return bool(self._anonymized_text and self._anonymized_text.strip())

    def __getitem__(self, key: str):
        if key == "text":
            return self._anonymized_text
        return getattr(self, key)

    def get(self, key: str, default=None):
        if key == "text":
            return self._anonymized_text
        return getattr(self, key, default)

class TextExtractor(ABC):
    """Abstract base class defining the contract for resume text extractors."""

    @abstractmethod
    def extract(self, path: str | Path) -> str:
        """Extract raw plain text from the given document path."""
        raise NotImplementedError

class PdfTextExtractor(TextExtractor):
    """Concrete extractor for PDF resume files."""

    def extract(self, path: str | Path) -> str:
        from pypdf import PdfReader

        text_parts = []
        try:
            reader = PdfReader(str(path))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        except Exception as error:
            print(f"Error reading PDF '{path}': {error}")
            return ""

        return "\n".join(text_parts)

class DocxTextExtractor(TextExtractor):
    """Concrete extractor for DOCX resume files, including paragraphs and table cells."""

    def extract(self, path: str | Path) -> str:
        from docx import Document

        text_parts = []
        try:
            document = Document(str(path))
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            for table in document.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))

        except Exception as error:
            print(f"Error reading DOCX '{path}': {error}")
            return ""

        return "\n".join(text_parts)

class ConsoleUI:
    """Boundary class handling all terminal input and output responsibilities."""

    def get_main_menu_choice(self) -> str:
        """Display available actions and return a valid choice to the controller."""
        while True:
            print("\nMAIN MENU")
            print("1. Screen a new batch of resumes")
            print("2. View saved screening results")
            print("3. Review saved candidates")
            print("4. Delete a saved job")
            print("5. Exit")
            choice = input("Choose an option (1-5): ").strip()
            if choice in ("1", "2", "3", "4", "5"):
                return choice
            print("Invalid choice. Enter 1, 2, 3, 4, or 5.")

    def _get_valid_folder(self, prompt_text: str) -> str:
        """Check for a valid folder path and return it; re-prompt if invalid."""
        while True:
            path = input(prompt_text).strip()
            if os.path.isdir(path):
                return path
            print("Invalid folder path. Please try again.")

    def collect_resumes(self, importer: "ResumeImporter | None" = None) -> list[Resume]:
        """Collect readable resumes, allowing folder re-entry while keeping accepted files."""
        if importer is None:
            importer = ResumeImporter()

        folder = self._get_valid_folder("Folder containing resumes: ")
        resumes: list[Resume] = []
        accepted_paths: set[str] = set()

        while True:
            files = importer.collect_batch(folder)
            new_files = []
            for file_path in files:
                normalized = os.path.normcase(os.path.abspath(str(file_path)))
                if normalized not in accepted_paths:
                    new_files.append(file_path)

            for resume in importer.prepare(new_files):
                resumes.append(resume)
                accepted_paths.add(
                    os.path.normcase(os.path.abspath(resume.file_path))
                )

            print(f"{len(resumes)} readable resume(s) ready to screen.")
            folder = input(
                "Enter a folder path to add/retry resumes, or press Enter to continue: "
            ).strip()
            if not folder:
                return resumes

    def _parse_skill_list(self, text: str) -> list[str]:
        """Return trimmed, nonempty skills without case-insensitive duplicates."""
        skills = []
        seen = set()
        for item in text.split(","):
            skill = item.strip()
            if skill and skill.lower() not in seen:
                skills.append(skill)
                seen.add(skill.lower())
        return skills

    def collect_job(self) -> Job:
        """Collect and validate job description details from user input."""
        while True:
            title = input("Job Title: ").strip()
            if title:
                break
            print("Job title cannot be empty. Please enter a job title.")

        skills_input = input("Required skills (comma-separated): ")
        skills = self._parse_skill_list(skills_input)

        while True:
            experience_input = input("Minimum years of experience: ")
            try:
                min_experience = float(experience_input)
            except ValueError:
                print("Invalid input. Enter a finite, nonnegative number.")
                continue
            if math.isfinite(min_experience) and min_experience >= 0:
                break
            print("Invalid input. Enter a finite, nonnegative number.")

        education = input("Education requirements: ").strip()

        preferred_input = input("Preferred skills (comma-separated): ")
        preferred_qualifications = self._parse_skill_list(preferred_input)
        required_names = {skill.lower() for skill in skills}
        preferred_qualifications = [
            skill
            for skill in preferred_qualifications
            if skill.lower() not in required_names
        ]

        job = Job(
            title=title,
            required_skills=skills,
            preferred=preferred_qualifications,
            min_experience=min_experience,
            education=education,
        )
        job.validate()
        return job

    def collect_preferences(self) -> ScreeningPreferences:
        """Collect screening preferences (minimum qualifying score) from user input."""
        while True:
            min_score_input = input(
                "Minimum score for screening (0-100, press Enter for default 60): "
            )
            if min_score_input.strip() == "":
                min_score = 60.0
                break
            try:
                min_score = float(min_score_input)
                if math.isfinite(min_score) and 0 <= min_score <= 100:
                    break
                print("Invalid input. Score must be between 0 and 100.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        preferences = ScreeningPreferences(min_qualifying_score=min_score)
        preferences.validate()
        return preferences

    def collect_inputs(
        self, importer: "ResumeImporter | None" = None
    ) -> tuple[list[Resume], Job | dict, ScreeningPreferences | dict]:
        """Return validated resumes, job requirements, and screening preferences."""
        resumes = self.collect_resumes(importer)
        if not resumes:
            return [], {}, {}

        job_description = self.collect_job()
        preferences = self.collect_preferences()
        return resumes, job_description, preferences

    def select_saved_job(self, jobs: list) -> Job | dict | None:
        """Show distinct screening jobs and return the selected record, or None to exit."""
        print("\nSAVED JOBS")
        for number, job in enumerate(jobs, start=1):
            job_id = job.get("job_id") if isinstance(job, dict) else getattr(job, "job_id", None)
            title = job.get("title") if isinstance(job, dict) else getattr(job, "title", "")
            created_at = job.get("created_at") if isinstance(job, dict) else getattr(job, "created_at", None)
            print(
                f"{number}. {job_id or 'Older results'} | {title} "
                f"| Created: {self._format_timestamp(created_at)}"
            )
        while True:
            choice = input(
                "Select a job number, or press Enter for the main menu: "
            ).strip()
            if not choice:
                return None
            try:
                number = int(choice)
            except ValueError:
                print("Enter a job number from the list.")
                continue
            if 1 <= number <= len(jobs):
                return jobs[number - 1]
            print("Enter a job number from the list.")

    def select_saved_candidate(
        self,
        candidates: list,
        prompt: str = "\nEnter a candidate ID to view details, or press Enter for the main menu: ",
    ):
        """Return a selected candidate, or None when the user returns to the main menu."""
        while True:
            candidate_id = input(prompt).strip().upper()
            if not candidate_id:
                return None
            for candidate in candidates:
                cid = (
                    candidate["candidate_id"]
                    if isinstance(candidate, dict)
                    else getattr(candidate, "candidate_id", "")
                )
                if cid.upper() == candidate_id:
                    return candidate
            print("Candidate ID not found. Enter an ID from the saved results list.")

    def collect_decision(self) -> str | None:
        """Return a decision or navigation action; None skips without changing a decision."""
        print("\nYOUR DECISION")
        print("1. Shortlist")
        print("2. Reject")
        print("3. Skip — keep the current decision")
        print("4. Jump to a candidate ID — return here afterward")
        print("5. Return to the main menu")
        while True:
            choice = input("Enter your choice (1-5): ").strip()
            if choice == "1":
                return "shortlisted"
            if choice == "2":
                return "rejected"
            if choice == "3":
                return None
            if choice == "4":
                return "jump"
            if choice == "5":
                return "exit"
            print("Invalid choice. Enter 1, 2, 3, 4, or 5.")

    def confirm_delete(self, job: Job | dict, count: int) -> bool:
        """Ask the user to confirm deleting a saved job and its linked candidate records."""
        job_id = job.get("job_id") if isinstance(job, dict) else getattr(job, "job_id", None)
        title = job.get("title") if isinstance(job, dict) else getattr(job, "title", "")
        question = (
            f"Delete job '{job_id or 'Older results'} - {title}' "
            f"and {count} linked candidate record(s)? (yes/no): "
        )
        return self._ask_yes_no(question)

    def _ask_yes_no(self, question: str) -> bool:
        """Prompt the user for a yes/no response and return a boolean."""
        while True:
            response = input(question).strip().lower()
            if response in ("yes", "no"):
                return response == "yes"
            print("Please enter 'yes' or 'no'.")

    def question_api_retry(self, count: int) -> bool:
        """Ask the user if they want to retry failed resumes."""
        question = (
            f"{count} resumes failed to process. Would you like to retry them? (yes/no): "
        )
        return self._ask_yes_no(question)

    def show_progress(self, record) -> None:
        """Print progress information for a single resume screening record."""
        file_name = (
            record["file_name"]
            if isinstance(record, dict)
            else getattr(record, "file_name", "")
        )
        status = (
            record["status"]
            if isinstance(record, dict)
            else getattr(record, "status", "")
        )
        print(f"Progress: {file_name} - {status}")

    def show_summary(self, success_count: int, failures: list) -> None:
        """Print number of resumes successfully processed by API and failed records."""
        print("\n--- Summary ---")
        print(f"Successfully processed: {success_count}")
        print(f"No. of failed resumes: {len(failures)}")
        for record in failures:
            file_name = (
                record["file_name"]
                if isinstance(record, dict)
                else getattr(record, "file_name", "")
            )
            error = (
                record["error"]
                if isinstance(record, dict)
                else getattr(record, "error", "")
            )
            print(f"  - {file_name}: {error}")

    def show_rankings(self, rows: list) -> None:
        """Print candidates in the order given (best first)."""
        if not rows:
            print(
                "\nNo resumes were screened successfully, so there is nothing to rank."
            )
            return

        print(f"\n--- Results ({len(rows)} candidate(s), best first) ---")

        for row in rows:
            name = row["file_name"] if isinstance(row, dict) else getattr(row, "file_name", "")
            result = row["evaluation"] if isinstance(row, dict) else getattr(row, "evaluation", {})

            fast_track = (
                result["fast_track"]
                if isinstance(result, dict)
                else getattr(result, "fast_track", False)
            )
            final_score = (
                result["final_score"]
                if isinstance(result, dict)
                else getattr(result, "final_score", None)
            )
            status = (
                result["status"]
                if isinstance(result, dict)
                else getattr(result, "status", "")
            )

            tag = " [FAST-TRACK]" if fast_track else ""
            print(f"{name}: {final_score} ({status}){tag}")

            if status != "RE_ENTRY":
                skills_score = (
                    result["skills_score"]
                    if isinstance(result, dict)
                    else getattr(result, "skills_score", 0)
                )
                experience_score = (
                    result["experience_score"]
                    if isinstance(result, dict)
                    else getattr(result, "experience_score", 0)
                )
                education_score = (
                    result["education_score"]
                    if isinstance(result, dict)
                    else getattr(result, "education_score", 0)
                )
                confidence = (
                    result["confidence"]
                    if isinstance(result, dict)
                    else getattr(result, "confidence", "")
                )
                skill_details = (
                    result["skill_details"]
                    if isinstance(result, dict)
                    else getattr(result, "skill_details", [])
                )

                print(
                    f"    skills {skills_score} "
                    f"| experience {experience_score:.0f} "
                    f"| education {education_score:.0f} "
                    f"| confidence {confidence}"
                )

                for skill in skill_details:
                    s_name = skill["name"] if isinstance(skill, dict) else getattr(skill, "name", "")
                    s_present = skill["present"] if isinstance(skill, dict) else getattr(skill, "present", False)
                    s_evidence = skill["evidence"] if isinstance(skill, dict) else getattr(skill, "evidence", "")

                    if not s_present:
                        print(f"    {s_name}: NOT DEMONSTRATED")
                    elif not s_evidence:
                        print(
                            f"    {s_name}: CLAIMED WITHOUT EVIDENCE (no skill points)"
                        )
                    else:
                        print(f"    {s_name}: PRESENT")
                        print(f"      Evidence: {s_evidence}")

            notes = (
                result["notes"]
                if isinstance(result, dict)
                else getattr(result, "notes", [])
            )
            for note in notes:
                print("    -", note)

    def show_saved_results(self, candidates: list) -> None:
        """List stored candidates in CSV order, including failed screening records."""
        print(f"\n--- Saved results ({len(candidates)} candidate(s)) ---")
        for candidate in candidates:
            cid = candidate["candidate_id"] if isinstance(candidate, dict) else getattr(candidate, "candidate_id", "")
            job_title = candidate.get("job_title") if isinstance(candidate, dict) else getattr(candidate, "job_title", "")
            file_name = candidate["file_name"] if isinstance(candidate, dict) else getattr(candidate, "file_name", "")
            final_score = candidate["final_score"] if isinstance(candidate, dict) else getattr(candidate, "final_score", None)
            status = candidate["status"] if isinstance(candidate, dict) else getattr(candidate, "status", "")
            decision = candidate.get("recruiter_decision") if isinstance(candidate, dict) else getattr(candidate, "recruiter_decision", "pending")
            print(
                f"{cid} | {job_title or 'Role not provided'} "
                f"| {file_name} | {self._format_score(final_score)} "
                f"| {status} | Decision: {decision or 'pending'}"
            )

    def show_candidate_detail(self, candidate) -> None:
        """Display detailed information about a single saved candidate."""
        is_dict = isinstance(candidate, dict)
        cid = candidate.get("candidate_id") if is_dict else getattr(candidate, "candidate_id", None)
        file_name = candidate["file_name"] if is_dict else getattr(candidate, "file_name", "")
        job_title = candidate.get("job_title") if is_dict else getattr(candidate, "job_title", None)
        job_id = candidate.get("job_id") if is_dict else getattr(candidate, "job_id", None)
        final_score = candidate["final_score"] if is_dict else getattr(candidate, "final_score", None)
        status = candidate.get("status") if is_dict else getattr(candidate, "status", None)
        fast_track = candidate.get("fast_track") if is_dict else getattr(candidate, "fast_track", False)
        decision = candidate.get("recruiter_decision") if is_dict else getattr(candidate, "recruiter_decision", "pending")
        skills_score = candidate.get("skills_score") if is_dict else getattr(candidate, "skills_score", None)
        notes = candidate.get("notes", []) if is_dict else getattr(candidate, "notes", [])
        created_at = candidate.get("created_at") if is_dict else getattr(candidate, "created_at", None)

        if is_dict and "ai_result" in candidate:
            ai_result = candidate["ai_result"]
            confidence = ai_result.get("confidence")
            exp_score = ai_result.get("experience_score")
            edu_score = ai_result.get("education_score")
            skills_present = ai_result.get("skills_present", [])
            skills_missing = ai_result.get("skills_missing", [])
            evidence = ai_result.get("evidence", "")
            summary = ai_result.get("summary")
        else:
            confidence = getattr(candidate, "confidence", None)
            exp_score = getattr(candidate, "experience_score", None)
            edu_score = getattr(candidate, "education_score", None)
            skills_present = getattr(candidate, "skills_present", [])
            skills_missing = getattr(candidate, "skills_missing", [])
            evidence = getattr(candidate, "evidence", "")
            summary = getattr(candidate, "summary", None)

        print("\n" + "=" * 60)
        print("SAVED CANDIDATE DETAILS")
        print("=" * 60)
        print(f"Candidate ID: {cid or 'Not provided'}")
        print(f"Resume: {file_name}")
        print(f"Role: {job_title or 'Not provided'}")
        print(f"Job ID: {job_id or 'Not recorded (older result)'}")
        print(f"Final score: {self._format_score(final_score)}")
        print(f"System recommendation: {status or 'Not provided'}")
        print(f"Fast-track: {'Yes' if fast_track else 'No'}")
        print(f"Recruiter decision: {decision or 'pending'}")
        print(f"AI confidence: {confidence or 'Not provided'}")
        print("\nCRITERION SCORES")
        print(f"Skills: {self._format_score(skills_score)}")
        print(f"Experience: {self._format_score(exp_score)}")
        print(f"Education: {self._format_score(edu_score)}")
        print("\nSKILLS AND EVIDENCE")
        print(
            f"AI-reported present: {', '.join(skills_present) or 'None reported'}"
        )
        print(
            f"Not demonstrated: {', '.join(skills_missing) or 'None reported'}"
        )
        print(f"Evidence: {evidence or 'Not provided'}")
        print("\nAI SUMMARY")
        print(summary or "Not provided")
        print("\nSCORING NOTES / PROCESSING ERRORS")
        for note in notes:
            print(f"- {note}")
        if not notes:
            print("None recorded")
        print(f"\nSaved: {self._format_timestamp(created_at)}")
        print("System recommendations do not change the recruiter decision.")
        print("=" * 60)

    def show_job_details(self, job: Job | dict) -> None:
        """Display stored requirements without inventing details for older candidates."""
        job_id = job.get("job_id") if isinstance(job, dict) else getattr(job, "job_id", None)
        title = job.get("title") if isinstance(job, dict) else getattr(job, "title", "")
        print(f"\n--- JOB {job_id or 'NOT RECORDED'} — {title} ---")
        if not job_id:
            print("Job requirements were not stored for these older results.")
            return
        req_skills = job.get("required_skills", []) if isinstance(job, dict) else getattr(job, "required_skills", [])
        pref_skills = job.get("preferred", []) if isinstance(job, dict) else getattr(job, "preferred", [])
        experience = job.get("min_experience") if isinstance(job, dict) else getattr(job, "min_experience", None)
        education = job.get("education") if isinstance(job, dict) else getattr(job, "education", "")
        threshold = job.get("min_qualifying_score") if isinstance(job, dict) else getattr(job, "min_qualifying_score", None)

        print(f"Required skills: {', '.join(req_skills) or 'None specified'}")
        print(f"Preferred skills: {', '.join(pref_skills) or 'None specified'}")
        print(
            f"Minimum experience: {experience if experience is not None else 'Not provided'} years"
        )
        print(f"Education: {education or 'Not specified'}")
        print(
            f"Qualifying score: {threshold if threshold is not None else 'Not provided'}"
        )

    def show_message(self, text: str) -> None:
        """Print an informational message to the user."""
        print(text)

    def show_error(self, text: str) -> None:
        """Print an error message to the user."""
        print(f"Error: {text}")

    def _get_candidate_field(self, candidate, key: str, default=None):
        """Read a field from a dict or object candidate, falling back to nested ai_result."""
        if isinstance(candidate, dict):
            if key in candidate and candidate[key] is not None:
                return candidate[key]
            ai_result = candidate.get("ai_result")
            if isinstance(ai_result, dict) and key in ai_result:
                return ai_result[key]
            return default
        value = getattr(candidate, key, None)
        if value is not None:
            return value
        ai_result = getattr(candidate, "ai_result", None)
        if isinstance(ai_result, dict):
            return ai_result.get(key, default)
        return getattr(ai_result, key, default) if ai_result is not None else default

    def collect_skill_filter(self) -> list[str]:
        """Prompt for comma-separated skills to filter candidates (Enter to skip)."""
        raw = input(
            "\nEnter skill(s) to filter by (comma-separated, or press Enter for all): "
        ).strip()
        if not raw:
            return []
        return self._parse_skill_list(raw)

    def filter_candidates_by_skills( self, candidates: list, required_skills: list[str]) -> list:
        """Return candidates matching all requested skills, sorted by final_score descending."""
        wanted = [skill.strip().lower() for skill in required_skills if skill.strip()]
        if not wanted:
            matched = list(candidates)
        else:
            matched = []
            for candidate in candidates:
                present = self._get_candidate_field(candidate, "skills_present", []) or []
                present_lower = {str(s).strip().lower() for s in present}
                if all(req in present_lower for req in wanted):
                    matched.append(candidate)

        def sort_key(cand):
            score = self._get_candidate_field(cand, "final_score", None)
            return (score is not None, float(score) if score is not None else -1.0)

        return sorted(matched, key=sort_key, reverse=True)

    def show_skill_filtered_results(
        self, candidates: list, required_skills: list[str]
    ) -> list:
        """Filter candidates by skills, display ranked matches, and return the filtered list."""
        filtered = self.filter_candidates_by_skills(candidates, required_skills)
        skill_label = ", ".join(required_skills) if required_skills else "All skills"
        print(
            f"\n--- Skill Filter [{skill_label}]: "
            f"{len(filtered)} of {len(candidates)} candidate(s) matched (ranked best first) ---"
        )
        if not filtered:
            print("No candidates matched all requested skills.")
            return []
        self.show_saved_results(filtered)
        return filtered

    def select_candidates_for_comparison(
        self, candidates: list
    ) -> tuple | None:
        """Prompt the user to select two distinct candidates from the list for comparison."""
        if len(candidates) < 2:
            print("At least 2 candidates are required for side-by-side comparison.")
            return None
        first = self.select_saved_candidate(
            candidates,
            prompt="\nEnter first candidate ID to compare (or press Enter to cancel): ",
        )
        if first is None:
            return None
        first_id = str(self._get_candidate_field(first, "candidate_id", "")).upper()
        while True:
            second = self.select_saved_candidate(
                candidates,
                prompt="Enter second candidate ID to compare (or press Enter to cancel): ",
            )
            if second is None:
                return None
            second_id = str(
                self._get_candidate_field(second, "candidate_id", "")
            ).upper()
            if second_id != first_id:
                return first, second
            print("Please select a different candidate ID for comparison.")

    def show_candidate_comparison(self, candidate_a, candidate_b) -> None:
        """Display a side-by-side comparison table for two candidates in the terminal."""
        def fmt_list(items) -> str:
            if not items:
                return "None"
            return ", ".join(str(x) for x in items)
        def cell(value, width: int = 26) -> str:
            text = str(value if value is not None else "Not provided")
            return text if len(text) <= width else text[: width - 3] + "..."
        id_a = self._get_candidate_field(candidate_a, "candidate_id", "Candidate A")
        id_b = self._get_candidate_field(candidate_b, "candidate_id", "Candidate B")
        rows = [
            (
                "Resume",
                self._get_candidate_field(candidate_a, "file_name", "-"),
                self._get_candidate_field(candidate_b, "file_name", "-"),
            ),
            (
                "Role",
                self._get_candidate_field(candidate_a, "job_title", "-"),
                self._get_candidate_field(candidate_b, "job_title", "-"),
            ),
            (
                "Final Score",
                self._format_score(self._get_candidate_field(candidate_a, "final_score")),
                self._format_score(self._get_candidate_field(candidate_b, "final_score")),
            ),
            (
                "Recommendation",
                self._get_candidate_field(candidate_a, "status", "-"),
                self._get_candidate_field(candidate_b, "status", "-"),
            ),
            (
                "Fast-Track",
                "Yes" if self._get_candidate_field(candidate_a, "fast_track", False) else "No",
                "Yes" if self._get_candidate_field(candidate_b, "fast_track", False) else "No",
            ),
            (
                "Decision",
                self._get_candidate_field(candidate_a, "recruiter_decision", "pending") or "pending",
                self._get_candidate_field(candidate_b, "recruiter_decision", "pending") or "pending",
            ),
            (
                "Skills Score",
                self._format_score(self._get_candidate_field(candidate_a, "skills_score")),
                self._format_score(self._get_candidate_field(candidate_b, "skills_score")),
            ),
            (
                "Experience Score",
                self._format_score(self._get_candidate_field(candidate_a, "experience_score")),
                self._format_score(self._get_candidate_field(candidate_b, "experience_score")),
            ),
            (
                "Education Score",
                self._format_score(self._get_candidate_field(candidate_a, "education_score")),
                self._format_score(self._get_candidate_field(candidate_b, "education_score")),
            ),
            (
                "AI Confidence",
                self._get_candidate_field(candidate_a, "confidence", "-"),
                self._get_candidate_field(candidate_b, "confidence", "-"),
            ),
            (
                "Skills Present",
                fmt_list(self._get_candidate_field(candidate_a, "skills_present", [])),
                fmt_list(self._get_candidate_field(candidate_b, "skills_present", [])),
            ),
            (
                "Skills Missing",
                fmt_list(self._get_candidate_field(candidate_a, "skills_missing", [])),
                fmt_list(self._get_candidate_field(candidate_b, "skills_missing", [])),
            ),
        ]
        print("\n" + "=" * 78)
        print("CANDIDATE SIDE-BY-SIDE COMPARISON")
        print("=" * 78)
        print(f"{'Field':<18} | {cell(id_a):<26} | {cell(id_b):<26}")
        print("-" * 18 + "-+-" + "-" * 26 + "-+-" + "-" * 26)
        for label, val_a, val_b in rows:
            print(f"{label:<18} | {cell(val_a):<26} | {cell(val_b):<26}")
        print("=" * 78)
 
    def _format_timestamp(self, value) -> str:
        """Display ISO dates readably without changing stored data or guessing old timezones."""
        if not value:
            return "Not provided"
        if isinstance(value, datetime):
            saved_time = value
        else:
            try:
                saved_time = datetime.fromisoformat(str(value))
            except ValueError:
                return str(value)
        if saved_time.tzinfo is not None:
            return saved_time.astimezone(timezone.utc).strftime(
                "%d %b %Y, %H:%M:%S UTC"
            )
        return saved_time.strftime("%d %b %Y, %H:%M:%S")

    def _format_score(self, value) -> str:
        """Format stored numeric scores while keeping API failures visibly unscored."""
        if value is None:
            return "Not scored"
        return f"{value:g} / 100"

    # Legacy method aliases for backward compatibility
    collect_job_description = collect_job
    collect_screening_preferences = collect_preferences
    collect_recruiter_decision = collect_decision
    display_saved_results = show_saved_results
    display_candidate_detail = show_candidate_detail
    display_job_details = show_job_details
    format_timestamp = _format_timestamp
    format_saved_score = _format_score


class ResumeImporter:
    """Service class responsible for validating, extracting, cleaning, and anonymizing resumes."""

    def __init__(self, extractors: dict[str, TextExtractor] | None = None):
        if extractors is None:
            self._extractors ={
                ".pdf": PdfTextExtractor(),
                ".docx": DocxTextExtractor(),
            }
        else:
            self._extractors = {
                extension.lower(): extractor
                for extension, extractor in extractors.items()
            }

        self._supported_extensions = tuple(self._extractors.keys())

    def register_extractor(
            self,
            extension: str,
            extractor: TextExtractor
    ) -> None:
        """Register an additional document text extractor."""

        extension = extension.lower()

        if not extension.startswith("."):
            extension = "." + extension

        self._extractors[extension] = extractor

        self._supported_extensions = tuple(self._extractors.keys())

    def collect_batch(self, folder: str | Path) -> list[Path]:
        """Return files passing basic validation; report rejected paths clearly."""
        try:
            names = sorted(os.listdir(folder))
        except OSError as error:
            print(f"Could not read folder '{folder}': {error}")
            return []

        valid_files: list[Path] = []
        for name in names:
            file_path = Path(folder) / name
            try:
                self._validate_file(file_path)
            except ValueError as error:
                print(f"Rejected '{name}': {error}")
            else:
                valid_files.append(file_path)

        print(f"Found {len(valid_files)} nonempty PDF/DOCX file(s).")
        return valid_files

    def prepare(self, files: list[str | Path]) -> list[Resume]:
        """Extract and anonymize text from each resume file, returning Resume domain objects."""
        resumes: list[Resume] = []

        for file_path in files:
            path_obj = Path(file_path)
            try:
                self._validate_file(path_obj)
            except ValueError as error:
                print(f"Rejected '{path_obj.name}': {error}")
                continue

            text = self._extract_text(path_obj)
            if not text:
                print(
                    f"Skipping '{path_obj.name}': "
                    "No readable text found. Use a readable PDF or DOCX file."
                )
                continue

            text = self._anonymize_text(text)
            resume = Resume(
                file_name=path_obj.name,
                file_path=str(path_obj),
                anonymized_text=text,
            )
            if not resume.has_readable_text():
                print(
                    f"Skipping '{path_obj.name}': "
                    "No resume content remains after removing personal details."
                )
                continue

            resumes.append(resume)

        return resumes

    def _validate_file(self, path: str | Path) -> None:
        """Check the file format and reject empty files with a clear reason."""
        file_path = str(path)
        if not os.path.isfile(file_path):
            raise ValueError("Path must point to a regular file.")

        extension = os.path.splitext(file_path)[1].lower()
        if extension not in self._extractors:
            supported = ", ".join(self._supported_extensions)
            raise ValueError(f"Unsupported file type. Supported formats: {supported}")

        try:
            size = os.path.getsize(file_path)
        except OSError as error:
            raise ValueError(f"Could not check file size: {error}") from error
        if size == 0:
            raise ValueError("File is empty.")

    def _extract_text(self, path: str | Path) -> str:
        """Extract and clean text from a resume file based on its extension."""
        file_path = str(path)
        extension = os.path.splitext(file_path)[1].lower()

        extractor = self._extractors.get(extension)

        if extractor is None:
            print(f"Unsupported resume type: {path}")
            return ""

        raw_text = extractor.extract(path)

        return self._clean_text(raw_text)

    def _extract_pdf(self, path: str | Path) -> str:
        """Extract plain text from a PDF file, page by page."""
        from pypdf import PdfReader

        text_parts = []
        try:
            reader = PdfReader(str(path))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        except Exception as error:
            print(f"Error reading PDF '{path}': {error}")
            return ""

        return "\n".join(text_parts)

    def _extract_docx(self, path: str | Path) -> str:
        """Extract plain text from a DOCX file, including table cells."""
        from docx import Document

        text_parts = []
        try:
            document = Document(str(path))
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            for table in document.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))
        except Exception as error:
            print(f"Error reading DOCX '{path}': {error}")
            return ""

        return "\n".join(text_parts)

    def _clean_text(self, text: str) -> str:
        """Normalize line endings and strip blank/whitespace-only lines."""
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)

        return "\n".join(lines)

    def _anonymize_text(self, text: str) -> str:
        """Remove labelled personal details and replace recognizable contact details."""
        personal_label = (
            r"^\s*(?:[-*•]\s*)?(?:full name|candidate name|name|"
            r"home address|postal address|address|date of birth|dob|age|"
            r"gender|sex|race|ethnicity|marital status|nationality|"
            r"e-?mail|phone(?: number)?|telephone|mobile(?: number)?|contact number)\s*[:：-]"
        )
        email_pattern = r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"
        phone_pattern = (
            r"(?<!\w)(?:"
            r"(?:\+65[ .-]?)?[689]\d{3}[ .-]?\d{4}|"
            r"(?:\+1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]\d{4}|"
            r"\+\d{1,3}[ .-]\d{1,4}[ .-]\d{3,4}[ .-]\d{4}"
            r")(?!\w)"
        )
        lines = []
        for line in text.splitlines():
            if re.match(personal_label, line, flags=re.IGNORECASE):
                continue
            line = re.sub(email_pattern, "[EMAIL REMOVED]", line)
            line = re.sub(phone_pattern, "[PHONE REMOVED]", line)
            remaining_text = line.replace("[EMAIL REMOVED]", "").replace(
                "[PHONE REMOVED]", ""
            )
            if re.search(r"\w", remaining_text):
                lines.append(line.strip())
        return "\n".join(lines)

    # Legacy method aliases
    validate_resume_file = _validate_file
    collect_resume_batch = collect_batch
    prepare_resumes_for_ai = prepare
    extract_resume_text = _extract_text
    clean_resume_text = _clean_text
    anonymize_resume_text = _anonymize_text

if __name__ == "__main__":
    print("Start the application with: python main.py")