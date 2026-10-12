import uuid
import os
import math
import re

VALID_RESUME_EXTENSIONS = ('.pdf', '.docx')


def validate_resume_file(file_path):
    # Check the file format and reject empty files with a clear reason.
    if not os.path.isfile(file_path):
        raise ValueError("Path must point to a regular file.")
    extension = os.path.splitext(file_path)[1].lower()
    if extension not in VALID_RESUME_EXTENSIONS:
        raise ValueError("Unsupported file type. Use .pdf or .docx.")
    try:
        size = os.path.getsize(file_path)
    except OSError as error:
        raise ValueError(f"Could not check file size: {error}") from error
    if size == 0:
        raise ValueError("File is empty.")

def get_valid_folder(prompt_text):
    """Check for a valid folder path and return it; re-prompt if invalid."""
    while True:
        path = input(prompt_text).strip()
        if os.path.isdir(path):
            return path
        else:
            print("Invalid folder path. Please try again.")

def collect_resume_batch(folder):
    # Return files passing basic validation; report rejected paths clearly.
    try:
        names = sorted(os.listdir(folder))
    except OSError as error:
        print(f"Could not read folder '{folder}': {error}")
        return []
    valid_files = []
    for name in names:
        file_path = os.path.join(folder, name)
        try:
            validate_resume_file(file_path)
        except ValueError as error:
            print(f"Rejected '{name}': {error}")
        else:
            valid_files.append(file_path)

    print(f"Found {len(valid_files)} nonempty PDF/DOCX file(s).")
    return valid_files

def clean_resume_text(text):
    """Normalize line endings and strip blank/whitespace-only lines."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


def anonymize_resume_text(text):
    # Remove labelled personal details and replace recognizable contact details.
    # Unlabelled names and personal details inside sentences may remain.
    personal_label = (
        r"^\s*(?:[-*•]\s*)?(?:full name|candidate name|name|"
        r"home address|postal address|address|date of birth|dob|age|"
        r"gender|sex|race|ethnicity|marital status|nationality|"
        r"e-?mail|phone(?: number)?|telephone|mobile(?: number)?|contact number)\s*[:：-]"
    )
    email_pattern = r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"
    # Recognize international numbers, Singapore numbers, and US-style numbers.
    # Avoid broad digit matching so employment year ranges remain unchanged.
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
        remaining_text = line.replace("[EMAIL REMOVED]", "").replace("[PHONE REMOVED]", "")
        # Omit lines containing only removed contacts or punctuation.
        if re.search(r"\w", remaining_text):
            lines.append(line.strip())
    return "\n".join(lines)

def extract_pdf_text(file_path):
    """Extract plain text from a PDF file, page by page."""
    from pypdf import PdfReader

    text_parts = []
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    except Exception as e:
        print(f"Error reading PDF '{file_path}': {e}")
        return ""

    return "\n".join(text_parts)

def extract_docx_text(file_path):
    """Extract plain text from a DOCX file, including table cells."""
    from docx import Document

    text_parts = []
    try:
        document = Document(file_path)
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

    except Exception as e:
        print(f"Error reading DOCX '{file_path}': {e}")
        return ""

    return "\n".join(text_parts)

def extract_resume_text(file_path):
    """Extract and clean text from a resume file, based on its extension."""
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        raw_text = extract_pdf_text(file_path)

    elif extension == ".docx":
        raw_text = extract_docx_text(file_path)

    else:
        print(f"Unsupported resume type: {file_path}")
        return ""

    return clean_resume_text(raw_text)


def prepare_resumes_for_ai(files):
    """Extract text from each resume file, skipping any that fail."""
    resumes = []

    for file_path in files:
        try:
            validate_resume_file(file_path)
        except ValueError as error:
            print(f"Rejected '{os.path.basename(file_path)}': {error}")
            continue
        text = extract_resume_text(file_path)

        if not text:
            print(
                f"Skipping '{os.path.basename(file_path)}': "
                "No readable text found. Use a readable PDF or DOCX file."
            )
            continue
        text = anonymize_resume_text(text)
        if not text:
            print(
                f"Skipping '{os.path.basename(file_path)}': "
                "No resume content remains after removing personal details."
            )
            continue
        resume = {
            "id": uuid.uuid4().hex,
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "text": text
        }
        resumes.append(resume)

    return resumes


def collect_resumes():
    # Collect readable resumes, allowing folder re-entry while keeping accepted files.
    folder = get_valid_folder("Folder containing resumes: ")
    resumes = []
    accepted_paths = set()
    while True:
        files = collect_resume_batch(folder)
        new_files = []
        for file_path in files:
            if os.path.normcase(os.path.abspath(file_path)) not in accepted_paths:
                new_files.append(file_path)
        for resume in prepare_resumes_for_ai(new_files):
            resumes.append(resume)
            accepted_paths.add(os.path.normcase(os.path.abspath(resume["file_path"])))
        print(f"{len(resumes)} readable resume(s) ready to screen.")
        folder = input(
            "Enter a folder path to add/retry resumes, or press Enter to continue: "
        ).strip()
        if not folder:
            return resumes


def parse_skill_list(text):
    # Return trimmed, nonempty skills without case-insensitive duplicates.
    skills = []
    seen = set()
    for item in text.split(","):
        skill = item.strip()
        if skill and skill.lower() not in seen:
            skills.append(skill)
            seen.add(skill.lower())
    return skills

def collect_job_description():
    """Collect job description details from user input."""
    title = input("Job Title: ")

    skills_input = input("Required skills (comma-separated): ")
    skills = parse_skill_list(skills_input)

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

    education = input("Education requirements: ")

    preferred_input = input("Preferred skills (comma-separated): ")
    preferred_qualifications = parse_skill_list(preferred_input)
    required_names = {skill.lower() for skill in skills}
    preferred_qualifications = [
        skill for skill in preferred_qualifications if skill.lower() not in required_names
    ]

    job_description = {
        "title": title,
        "required_skills": skills,
        "min_experience": min_experience,
        "education": education,
        "preferred": preferred_qualifications,
    }
    return job_description

def collect_screening_preferences():
    """Collect screening preferences (minimum qualifying score) from user input."""
    while True:
        min_score_input = input("Minimum score for screening (0-100, press Enter for default 60): ")
        if min_score_input.strip() == "":
            min_score = 60.0
            break
        else:
            try:
                min_score = float(min_score_input)
                if 0 <= min_score <= 100:
                    break
                else:
                    print("Invalid input. Score must be between 0 and 100.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    preferences = {
        "min_qualifying_score": min_score,
    }

    return preferences

def display_result(candidates):
    """Display the final screening results in descending order of score."""
    sorted_candidates = sorted(candidates, key=lambda c: c["final_score"], reverse=True)
    for c in sorted_candidates:
        print(c["file_name"], c["final_score"])

def display_candidate_detail(candidate):
    """Display detailed information about a single candidate."""
    print("\n" + "=" * 60)
    print("SAVED CANDIDATE DETAILS")
    print("=" * 60)
    print(f"Candidate ID: {candidate.get('candidate_id') or 'Not provided'}")
    print(f"Resume: {candidate['file_name']}")
    print(f"Role: {candidate.get('job_title') or 'Not provided'}")
    print(f"Job ID: {candidate.get('job_id') or 'Not recorded (older result)'}")
    print(f"Final score: {format_saved_score(candidate['final_score'])}")
    print(f"System recommendation: {candidate.get('status') or 'Not provided'}")
    print(f"Fast-track: {'Yes' if candidate.get('fast_track') else 'No'}")
    print(f"Recruiter decision: {candidate.get('recruiter_decision') or 'pending'}")
    ai_result = candidate["ai_result"]
    print(f"AI confidence: {ai_result.get('confidence') or 'Not provided'}")
    print("\nCRITERION SCORES")
    print(f"Skills: {format_saved_score(candidate.get('skills_score'))}")
    print(f"Experience: {format_saved_score(ai_result.get('experience_score'))}")
    print(f"Education: {format_saved_score(ai_result.get('education_score'))}")
    print("\nSKILLS AND EVIDENCE")
    print(f"AI-reported present: {', '.join(ai_result['skills_present']) or 'None reported'}")
    print(f"Not demonstrated: {', '.join(ai_result['skills_missing']) or 'None reported'}")
    print(f"Evidence: {ai_result['evidence'] or 'Not provided'}")
    print("\nAI SUMMARY")
    print(ai_result.get('summary') or "Not provided")
    print("\nSCORING NOTES / PROCESSING ERRORS")
    for note in candidate.get("notes", []):
        print(f"- {note}")
    if not candidate.get("notes"):
        print("None recorded")
    print(f"\nSaved: {candidate.get('created_at') or 'Not provided'}")
    print("Viewing details does not change the recruiter decision.")
    print("=" * 60)


def format_saved_score(score):
    # Format stored numeric scores while keeping API failures visibly unscored.
    if score is None:
        return "Not scored"
    return f"{score:g} / 100"


def display_saved_results(candidates):
    # List stored candidates in CSV order, including failed screening records.
    print(f"\n--- Saved results ({len(candidates)} candidate(s)) ---")
    for candidate in candidates:
        print(
            f"{candidate['candidate_id']} | {candidate['job_title'] or 'Role not provided'} "
            f"| {candidate['file_name']} | {format_saved_score(candidate['final_score'])} "
            f"| {candidate['status']} | Decision: {candidate['recruiter_decision'] or 'pending'}"
        )


def select_saved_job(jobs):
    # Show distinct screening jobs and return the selected record, or None to exit.
    print("\nSAVED JOBS")
    for number, job in enumerate(jobs, start=1):
        print(
            f"{number}. {job['job_id'] or 'Older results'} | {job['title']} "
            f"| Created: {job.get('created_at') or 'Not recorded'}"
        )
    while True:
        choice = input("Select a job number, or press Enter for the main menu: ").strip()
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


def display_job_details(job):
    # Display stored requirements without inventing details for older candidates.
    print(f"\n--- JOB {job['job_id'] or 'NOT RECORDED'} — {job['title']} ---")
    if not job["job_id"]:
        print("Job requirements were not stored for these older results.")
        return
    print(f"Required skills: {', '.join(job['required_skills']) or 'None specified'}")
    print(f"Preferred skills: {', '.join(job['preferred']) or 'None specified'}")
    experience = job["min_experience"]
    print(f"Minimum experience: {experience if experience is not None else 'Not provided'} years")
    print(f"Education: {job.get('education') or 'Not specified'}")
    threshold = job["min_qualifying_score"]
    print(f"Qualifying score: {threshold if threshold is not None else 'Not provided'}")


def select_saved_candidate(candidates):
    # Return a selected candidate, or None when the user returns to the main menu.
    while True:
        candidate_id = input("\nEnter a candidate ID to view details, or press Enter for the main menu: ").strip().upper()
        if not candidate_id:
            return None
        for candidate in candidates:
            if candidate["candidate_id"].upper() == candidate_id:
                return candidate
        print("Candidate ID not found. Enter an ID from the saved results list.")

# create a main menu function to import to main.py
def collect_inputs():
    # Return validated resumes, job requirements, and screening preferences.
    resumes = collect_resumes()
    if not resumes:
        return [], {}, {}

    job_description = collect_job_description()
    preferences = collect_screening_preferences()

    return resumes, job_description, preferences

# ask user to retry API req if failed
def ask_api_retry(question):
    while True:
        response = input(question).lower()
        if response in ["yes", "no"]:
            return response == "yes"
        else:
            print("Please enter 'yes' or 'no'.")

# print a line information to user
def show_message(text):
    print(text)

# print error message to user
def show_error(text):
    print(f"Error: {text}")

# print progress information to user
def show_progress(record):
    print(f"Progress: {record['file_name']} - {record['status']}")

# prints number of resumes successfully processed by API and also failed (with reason)
def show_summary(success_count, failed_record):
    print(f"\n--- Summary ---")
    print(f"Successfully processed: {success_count}")
    print(f"No. of failed resumes: {len(failed_record)}")
    for record in failed_record:
        print(f"  - {record['file_name']}: {record['error']}")

# uses the ask_api_retry function to ask user if they want to retry failed resumes
def question_api_retry(count):
    question = f"{count} resumes failed to process. Would you like to retry them? (yes/no): "
    return ask_api_retry(question)

# replaces the print result from logic manager
def show_rankings(rows):
    """Print candidates in the order given (best first).

    rows: list of {"file_name": str, "evaluation": result dict from logic_manager}
    """
    if not rows:
        print("\nNo resumes were screened successfully, so there is nothing to rank.")
        return

    print(f"\n--- Results ({len(rows)} candidate(s), best first) ---")

    for row in rows:
        name = row["file_name"]
        result = row["evaluation"]

        tag = ""
        if result["fast_track"]:
            tag = " [FAST-TRACK]"

        print(f"{name}: {result['final_score']} ({result['status']}){tag}")

        if result["status"] != "RE_ENTRY":
            print(
                f"    skills {result['skills_score']} "
                f"| experience {result['experience_score']:.0f} "
                f"| education {result['education_score']:.0f} "
                f"| confidence {result['confidence']}"
            )

            # Show the evidence behind skill points without treating missing evidence as absence.
            for skill in result["skill_details"]:
                if not skill["present"]:
                    print(f"    {skill['name']}: NOT DEMONSTRATED")
                elif not skill["evidence"]:
                    print(f"    {skill['name']}: CLAIMED WITHOUT EVIDENCE (no skill points)")
                else:
                    print(f"    {skill['name']}: PRESENT")
                    print(f"      Evidence: {skill['evidence']}")

        for note in result["notes"]:
            print("    -", note)

def get_main_menu_choice():
    # Display available actions and return a valid choice to main.py.
    while True:
        print("\nMAIN MENU")
        print("1. Screen a new batch of resumes")
        print("2. View saved screening results")
        print("3. Exit")
        choice = input("Choose an option (1-3): ").strip()
        if choice in ("1", "2", "3"):
            return choice
        print("Invalid choice. Enter 1, 2, or 3.")


if __name__ == "__main__":
    print("Start the application with: python main.py")
