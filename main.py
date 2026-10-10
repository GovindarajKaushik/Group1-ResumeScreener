import json
import uuid
import os
from datetime import datetime, timezone

# import main function from ai_manager
from ai_manager import process_resume_ai, validate_ai_result, build_user_prompt
# import io_manager
from iomanager import collect_inputs



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
    # create a tmp file first
    tmp_path = RESULT_FILE_PATH + ".tmp"
    # save the results to json file
    try:
        with open(tmp_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        # Atomically replace the original file
        os.replace(tmp_path, RESULT_FILE_PATH)
    except Exception as e:
        print(f"Error occurred while saving results: {e}")


# screen each resume sequentially and saves it in resume_results.json
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
    # test_prompt = (
    #     "MUST-HAVE SKILLS: Python, SQL\n"
    #     "PREFERRED SKILLS: Airflow\n"
    #     "RESUME:\n"
    #     "Senior data engineer, 6 years of Python ETL jobs and Postgres tuning."
    # )

    # call function from IO manager to collect data for API
    resumes, jobs_description, preferences = collect_inputs()

    if not resumes:
        print("No valid resumes to screen.")
        return

    success = 0
    failed = 0
    # processing each resume
    for resume in resumes:
        try:
            user_prompt = build_user_prompt(jobs_description, resume["raw_text"])
            result = screen_resume(resume["file_name"], user_prompt)
            status = result["record"]["status"]
            print(f"Processed {resume['file_name']}: {status}")
            if status == "success":
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Unexpected error on {resume['file_name']}: {e}")
            failed += 1

    print(f"\nDone. {success} succeeded, {failed} failed.")
    print(f"Results saved to {RESULT_FILE_PATH}")



if __name__ == "__main__":
    main()