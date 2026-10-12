import uuid
import os
import math

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
    print(f"File: {candidate['file_name']}")
    print(f"Score: {candidate['final_score']}")

    ai_result = candidate["ai_result"]
    print(f"Skills present: {ai_result['skills_present']}")
    print(f"Skills missing: {ai_result['skills_missing']}")
    print(f"Evidence: {ai_result['evidence']}")
    print(f"Confidence: {ai_result['confidence']}")

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

        for note in result["notes"]:
            print("    -", note)

def main_menu():
    """Main menu loop for user interaction."""
    while True:
        print("\n1. Screen new batch of resumes")
        print("2. Exit program")
        choice = input("Choose an option (1 or 2): ")

        if choice == "1":
            resumes, job_description, preferences = collect_inputs()
            if not resumes:
                print("No valid resumes to screen.")
                continue

            print("\n--- Collected so far ---\n")
            print(f"{len(resumes)} resume(s) ready to screen.")
            print(job_description)
            print(preferences)

            print("\n--- Resumes prepared for AI ---\n")
            for r in resumes:
                print(f"File: {r['file_name']}")
                print(f"Path: {r['file_path']}")
                print(f"Raw text length: {len(r['text'])} characters")
                print("Raw text: ")
                print(r["text"])
                print("\n-------------------------------")

        elif choice == "2":
            print("Exiting program....")
            break

        else:
            print("\nInvalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    print("\nWELCOME TO THE RESUME SCREENING TOOL")
    main_menu()
