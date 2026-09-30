import os

valid_resume_extensions = ('.pdf', '.docx')

def get_valid_folder(prompt_text):
    while True:
        path = input(prompt_text)
        if os.path.isdir(path):
            return path
        else:
            print("Invalid folder path. Please try again.")

def is_valid_file(file_path):
    if not file_path.endswith(valid_resume_extensions):
        return False, "Unsupported file type (use .pdf or .docx)"
    return True, ""

if __name__ == "__main__":
    folder = get_valid_folder("Folder containing resumes: ")
    print(f"Valid folder path: {folder}")

    result = is_valid_file("test.pdf")
    print(result)

    result2 = is_valid_file("test.txt")
    print(result2)