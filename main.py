import json
import uuid

from datetime import datetime, timezone

# import main function from ai_manager
from ai_manager import process_resume_ai, validate_ai_result



# constant result file path
RESULT_FILE_PATH = "resume_results.json"


# load existing results
def load_results():
    try:
        with open(RESULT_FILE_PATH, "r") as f:
            content = f.read().strip()
            # if empty
            if not content:          
                return {}
            results = json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        raise ValueError(f"{RESULT_FILE_PATH} contains invalid JSON")

    if not isinstance(results, dict):
        raise ValueError("Invalid results format in JSON file")
    return results


def save_results(results):
    # save the results to json file
    try:
        with open(RESULT_FILE_PATH, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error occurred while saving results: {e}")


# screen each resume sequentially
def screen_resume(file_name, user_prompt):

    # unique ID
    unique_id = f"resume_{uuid.uuid4().hex}"

    try:
        # calls the API using function from ai_manager
        screening_result = process_resume_ai(user_prompt)
        # validates the raw response
        validated_screening_result = validate_ai_result(json.dumps(screening_result))
        status = "success"
        error = None
    except Exception as e:
        validated_screening_result = None
        status = "error"
        error = str(e)

    # skeleton of data
    record = {
        "resume_name": file_name,
        "unique_id": unique_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "screening_result": validated_screening_result,
        "error": error
    }

    # load existing data (if any)
    current_results = load_results()
    current_results[unique_id] = record
    # Save results
    save_results(current_results)

    return {
        "resume_id": unique_id,
        "record": record
    }



def main():

    # Example usage
    test_prompt = (
        "MUST-HAVE SKILLS: Python, SQL\n"
        "PREFERRED SKILLS: Airflow\n"
        "RESUME:\n"
        "Senior data engineer, 6 years of Python ETL jobs and Postgres tuning."
    )

    try:
         result = screen_resume("test_resume.pdf", test_prompt)

         print("screening completed successfully.")
         print(f"Resume ID: {result['resume_id']}")
         print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, Exception) as e:
        print(f"Error occurred: {e}")


if __name__ == "__main__":
    main()