import os

valid_resume_extensions = ('.pdf', '.docx')

def get_valid_folder(prompt_text):
    while True:
        path = input(prompt_text)
        if os.path.isdir(path):
            return path
        else:
            print("Invalid folder path. Please try again.")

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
        "skills": skills,
        "min_experience": min_experience,
        "education": education,
        "preferred": preferred
    }

    return job_description  

if __name__ == "__main__":
    folder = get_valid_folder("Folder containing resumes: ")
    files = collect_resume_batch(folder)
    for f in files:
        print(f)

    job_description = collect_job_description()
    print(job_description)
