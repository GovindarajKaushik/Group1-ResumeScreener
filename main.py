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