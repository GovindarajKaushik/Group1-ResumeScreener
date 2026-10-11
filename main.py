import json
import os
from datetime import datetime, timezone

# import main function from ai_manager
from ai_manager import process_resume_ai, create_client
# import scoring functions from logic_manager
from logic_manager import evaluate_and_rank
# import io_manager
from io_manager import (
    collect_inputs,
    show_message,
    show_error,
    show_progress,
    show_summary,
    question_api_retry,
    show_rankings
)



# constant result file path
DEBUG_JSON_PATH = "resume_results.json"

STATUS_SUCCESS = "success"
STATUS_ERROR = "error"


# screen each resume sequentially
def screen_resume(client, resume, job_description):

    try:
        # ai manager calls the API
        screening_result = process_resume_ai(client, job_description, resume["text"])
        status, error, retryable = STATUS_SUCCESS, None, False
    except ConnectionError as e:
        screening_result, status, error, retryable = None, STATUS_ERROR, str(e), True
    except ValueError as e:
        screening_result, status, error, retryable = None, STATUS_ERROR, str(e), False

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

    # resumes is a dictionary (id -> resume), so use .items() to get both parts
    for resume_id, resume in resumes.items():
        record = screen_resume(client, resume, job_description)
        results[resume_id] = record
        if on_progress:
            on_progress(record)

# get number of failed API calls from AI manager API call (any reason)
def get_failed_ids(results):
    failed_ids = []
    for resume_id, record in results.items():
        if record["status"] == STATUS_ERROR:
            failed_ids.append(resume_id)
    return failed_ids


# number of failed API calls that can be retried
def get_retryable_ids(results):
    retryable_ids = []
    for resume_id in get_failed_ids(results):
        if results[resume_id]["retryable"]:
            retryable_ids.append(resume_id)
    return retryable_ids

# call ai manager again to retry faield attempts
def retry_failed(client, resumes, job_description, results, on_progress=None):
    # re-screens only failed resumes

    # list of failed resumes
    retry_ids = get_retryable_ids(results)
    # loop through each failed resume and call ai manager
    for resume_id in retry_ids:
        record = screen_resume(client, resumes[resume_id], job_description)
        results[resume_id] = record
        if on_progress:
            on_progress(record)
    return len(retry_ids)


# reports a summary for IO manager to display
def report_summary(results):

    failed_ids = get_failed_ids(results)

    failed_records = []
    for resume_id in failed_ids:
        failed_records.append(results[resume_id])

    success_count = len(results) - len(failed_ids)
    # function from io manager
    show_summary(success_count, failed_records)


# saves results to a JSON file (for debugging)
def save_results_json(results):
    # raises ValueError if the file can't be written; main() shows the warning
    tmp_path = DEBUG_JSON_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, DEBUG_JSON_PATH)
    except (OSError, TypeError, ValueError) as e:
        raise ValueError(f"could not save results to {DEBUG_JSON_PATH}: {e}")

def main():

    # Fail early if API key is not found
    try:
        client = create_client()
    except ValueError as e:
        # printing function from io manager
        show_error(f"creating AI client: {e}")
        return

    try:
        resume_list, job_description, preferences = collect_inputs()
        if not resume_list:
            show_message("No valid resumes to screen.")
            return
 
        resumes = {r["id"]: r for r in resume_list}
        results = {}
 
        def on_progress(record):
            # Runs after every resume: show progress and save the debug json
            show_progress(record)
            try:
                save_results_json(results)
            except ValueError as e:
                show_message(f"Warning: {e}")
 
        show_message("\nScreening...")
        screen_all_resumes(client, resumes, job_description, results, on_progress)
        report_summary(results)
 
        # Ask only about failures a retry could fix (connection, timeout,
        # rate limit, server error). Repeat until none are left or the user says no.
        while True:
            retryable_ids = get_retryable_ids(results)
            if not retryable_ids:
                break
            if not question_api_retry(len(retryable_ids)):
                break
            show_message("\nRetrying...")
            retry_failed(client, resumes, job_description, results, on_progress)
            report_summary(results)
 
        show_message(f"\nDebug copy of the results: {DEBUG_JSON_PATH}")
 
        # Next: logic_manager scores `results`, io_manager displays them
        try:
            # save results after retry
            save_results_json(results)
        except ValueError as e:
            show_error(f"Cannot score the results: {e}")
            return

        # logic manager
        try:
            ranking_rows = evaluate_and_rank(DEBUG_JSON_PATH, job_description, preferences)
        except ValueError as e:
            show_error(f"Cannot score the results: {e}")
            return
        show_rankings(ranking_rows)

        # data_manager.save_to_csv(...) persists them.
 
    except (KeyboardInterrupt, EOFError):
        show_message("\nInterrupted. Unsaved results were discarded.")


if __name__ == "__main__":
    main()