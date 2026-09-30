import os

def get_valid_folder(prompt_text):
    while True:
        path = input(prompt_text)
        if os.path.isdir(path):
            return path
        else:
            print("Invalid folder path. Please try again.")


if __name__ == "__main__":
    folder = get_valid_folder("Folder containing resumes: ")
    print(f"Valid folder path: {folder}")