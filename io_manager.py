import os

valid_resume_extensions = ('.pdf', '.docx')

#Check for valid folder path and return it. If invalid, prompt user to re-enter.
def get_valid_folder(prompt_text):
    while True:
        path = input(prompt_text)
        if os.path.isdir(path):
            return path
        else:
            print("Invalid folder path. Please try again.")

#Collect all valid resume files from the specified folder.
def collect_resume_batch(folder):
    all_files = []
    for f in os.listdir(folder):
        all_files.append(os.path.join(folder, f))

    valid_files = []
    for f in all_files:
        if not f.endswith(valid_resume_extensions):
            print(f"Skipping '{f}': Unsupported file type (use .pdf or .docx)")

        else:
            valid_files.append(f)

    print(f"Found {len(valid_files)} valid resume(s).")
    return valid_files

#Collect job description details from user input.
def collect_job_description():
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
    preferred = []
    for item in preferred_input.split(","):
        preferred.append(item.strip())

    job_description = {
        "title": title,
        "required_skills": skills,
        "min_experience": min_experience,
        "education": education,
        "preferred": preferred
    }

    return job_description  

#Collect screening preferences from user input.
def collect_screening_preferences():
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
        "min_qualifying_score": min_score
    }

    return preferences  

#Display the final screening results in descending order of score.
def display_result(candidates):
    sorted_candidates = sorted(candidates, key=lambda c: c["final_score"], reverse=True)
    for c in sorted_candidates:
        print(c["file_name"], c["final_score"])

#Define a function to display detailed information about a candidate
def display_candidate_detail(candidate):
    print(f"File: {candidate['file_name']}")
    print(f"Score: {candidate['final_score']}")

    ai_result = candidate["ai_result"]
    print(f"Skills present: {ai_result['skills_present']}")
    print(f"Skills missing: {ai_result['skills_missing']}")
    print(f"Evidence: {ai_result['evidence']}")
    print(f"Confidence: {ai_result['confidence']}")

#Define the main menu for user interaction
def main_menu():
    while True:
        print("\n1. Screen new batch of resumes")
        print("2. Exit program")
        choice = input("Choose an option (1 or 2): ")

        if choice == "1":
            folder = get_valid_folder("Folder containing resumes: ")
            files = collect_resume_batch(folder)

            job_description = collect_job_description()
            preferences = collect_screening_preferences()

            print("\n--- Collected so far ---\n")
            print(f"{len(files)} resume(s) ready to screen.")
            print(job_description)
            print(preferences)

        elif choice == "2":
            print("Exiting program....")
            break

        else:
            print("\nInvalid choice. Please enter 1 or 2.")

if __name__ == "__main__":
    print("\nWELCOME TO THE RESUME SCREENING TOOL")
    main_menu()

    """test code for testing purposes"""
    """
    job_description = collect_job_description()
    print(job_description)

    preferences = collect_screening_preferences()
    print(preferences)

    fake_candidates = {
        "file_name": "resume1.pdf",s
        "final_score": 85.0,
        "ai_result": {
            "skills_present": ["Python", "SQL"],
            "skills_missing": ["AWS"],
            "evidence": "3 years Python experience at Company X",
            "confidence": "high",
        }
    }
    display_candidate_detail(fake_candidates)
    """