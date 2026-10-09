import os

VALID_RESUME_EXTENSIONS = ('.pdf', '.docx')

def get_valid_folder(prompt_text):
    """Check for a valid folder path and return it; re-prompt if invalid."""
    while True:
        path = input(prompt_text)
        if os.path.isdir(path):
            return path
        else:
            print("Invalid folder path. Please try again.")

def collect_resume_batch(folder):
    """Collect all valid resume files from the specified folder."""
    all_files = []
    for f in os.listdir(folder):
        all_files.append(os.path.join(folder, f))

    valid_files = []
    for f in all_files:
        if not f.endswith(VALID_RESUME_EXTENSIONS):
            print(f"Skipping '{f}': Unsupported file type (use .pdf or .docx)")
        else:
            valid_files.append(f)

    print(f"Found {len(valid_files)} valid resume(s).")
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

    return text.strip()

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
        raw_text = extract_resume_text(file_path)

        if not raw_text:
            print(
                f"Skipping '{os.path.basename(file_path)}': "
                "Could not extract resume text."
            )
            continue 
        resume = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "raw_text": raw_text
        }
        resumes.append(resume)

    return resumes

def collect_job_description():
    """Collect job description details from user input."""
    title = input("Job Title: ")

    skills_input = input("Required skills (comma-separated): ")
    skills = []
    for skill in skills_input.split(","):
        skills.append(skill.strip())

    while True:
        experience_input = input("Minimum years of experience: ")
        try:
            min_experience = float(experience_input)
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    education = input("Education requirements: ")

    preferred_input = input("Preferred skills (comma-separated): ")
    preferred_qualifications = []
    for item in preferred_input.split(","):
        preferred_qualifications.append(item.strip())

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

def main_menu():
    """Main menu loop for user interaction."""
    while True:
        print("\n1. Screen new batch of resumes")
        print("2. Exit program")
        choice = input("Choose an option (1 or 2): ")

        if choice == "1":
            folder = get_valid_folder("Folder containing resumes: ")
            files = collect_resume_batch(folder)
            resumes = prepare_resumes_for_ai(files)

            job_description = collect_job_description()
            preferences = collect_screening_preferences()

            print("\n--- Collected so far ---\n")
            print(f"{len(files)} resume(s) ready to screen.")
            print(job_description)
            print(preferences)

            print("\n--- Resumes prepared for AI ---\n")
            for r in resumes:
                print(f"File: {r['file_name']}")
                print(f"Path: {r['file_path']}")
                print(f"Raw text length: {len(r['raw_text'])} characters")
                print("Raw text: ")
                print(r["raw_text"])
                print("\n-------------------------------")

        elif choice == "2":
            print("Exiting program....")
            break

        else:
            print("\nInvalid choice. Please enter 1 or 2.")


if __name__ == "__main__":
    print("\nWELCOME TO THE RESUME SCREENING TOOL")
    main_menu()