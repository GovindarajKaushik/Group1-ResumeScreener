import json
import uuid
import os
from datetime import datetime, timezone

# import main function from ai_manager
from ai_manager import process_resume_ai, validate_ai_result, build_user_prompt
# import io_manager
from io_manager import collect_inputs, ask_API_retry



# constant result file path
DEBUG_JSON_PATH = "resume_results.json"

STATUS_SUCCESS = "success"
STATUS_ERROR = "error"



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


# screen each resume sequentially
def screen_resume(client, resume, job_description):

    try:
        # ai manager calls the API
        screening_result = process_resume_ai(client, job_description, resume["text"])
        status, error, retryable = STATUS_SUCCESS, None, False
    except ConnectionError as e:
        result, status, error, retryable = None, STATUS_ERROR, str(e), True
    except ValueError as e:
        result, status, error, retryable = None, STATUS_ERROR, str(e), False

    # skeleton of data in resume_results.json
    return {
        "id": resume["id"],
        "file_name": resume["file_name"],
        "status": status,
        "retryable": retryable,
        "screening_result": screening_result,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# Screen all resumes storing each record in results dictionary temp
def screen_all_resumes(client, resumes, job_description, results, on_progress=None):

    for resume in resumes:
        record = screen_resume(client, resume, job_description)
        results[resume["id"]] = record
        if on_progress:
            on_progress(resume["id"], record)

# get number of failed API calls from AI manager API call (any reason)
def get_failed_ids(results):
    for resume_id, record in results.items():
        if record["status"] == STATUS_ERROR:
            return resume_id

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