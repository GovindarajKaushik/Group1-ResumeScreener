import json
import uuid

from datetime import datetime, timezone

# import main function from ai_manager
from ai_manager import process_resume_ai



# constant result file path
RESULT_FILE_PATH = "resume_results.json"


def load_results():
    # load existing results from the JSON file or create empty dict
    try:
        with open(RESULT_FILE_PATH, "r") as f:
            results = json.load(f)

            if not isinstance(results, dict):
                raise ValueError("Invalid results format in JSON file")
    except FileNotFoundError:
        results = {}
    return results


def save_results(results):
    # save the results to json file
    try:
        with open(RESULT_FILE_PATH, "w") as f:
            json.dump(results, f)
    except Exception as e:
        print(f"Error occurred while saving results: {e}")


# screen each resume sequentially
def screen_resume(file_name, user_prompt):
    # API call
    result = process_resume_ai(user_prompt)

    # load existing data (if any)
    results = load_results()

    # unique ID
    unique_id = f"resume_{uuid.uuid4().hex}"


    # skeleton of data
    record = {
        "resume_name": file_name,
        "unique_id": unique_id,
        "screening_result": result
    }

    results[unique_id] = record

    return {
        "resume_id": unique_id
        **record
    }