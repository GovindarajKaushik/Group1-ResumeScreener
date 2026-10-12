from datetime import datetime, timezone

# import main function from ai_manager
from ai_manager import process_resume_ai, create_client
# import scoring functions from logic_manager
from logic_manager import evaluate_results, build_ranking_rows
from data_manager import (
    save_results_json, save_screening_record, load_all_results,
    save_job, load_all_jobs, load_job_results, RESULTS_FILE, LOG_FILE
)
# import io_manager
from io_manager import (
    collect_inputs,
    show_message,
    show_error,
    show_progress,
    show_summary,
    question_api_retry,
    show_rankings,
    get_main_menu_choice,
    display_saved_results,
    select_saved_candidate,
    display_candidate_detail,
    select_saved_job,
    display_job_details,
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


def screen_new_batch():
    # Coordinate one batch of input, AI screening, scoring, display, and storage.

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

        try:
            job_description["job_id"] = save_job(job_description, preferences)
        except (OSError, ValueError) as error:
            show_error(f"Could not finish saving the job and its audit entry: {error}")
            return
        show_message(f"\nScreening job: {job_description['job_id']} — {job_description['title']}")
 
        resumes = {r["id"]: r for r in resume_list}
        results = {}
 
        def on_progress(record):
            # Runs after every resume: show progress and save the debug json
            show_progress(record)
            try:
                save_results_json(results, DEBUG_JSON_PATH)
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
 
        # Score the in-memory results; the debug file is optional.
        evaluations = evaluate_results(results, job_description, preferences)
        ranking_rows = build_ranking_rows(results, evaluations)
        show_rankings(ranking_rows)

        saved_count = 0
        for resume_id, record in results.items():
            try:
                save_screening_record(
                    record, resumes[resume_id], evaluations.get(resume_id), job_description
                )
            except (OSError, ValueError) as error:
                show_error(f"Could not finish saving '{record['file_name']}' and its audit entry: {error}")
            else:
                saved_count += 1
        show_message(f"\nSaved {saved_count}/{len(results)} candidate records to {RESULTS_FILE} with audit entries in {LOG_FILE}.")
 
    except (KeyboardInterrupt, EOFError):
        show_message("\nInterrupted. Any records already saved remain on disk.")


def view_saved_results():
    # Select a saved job before viewing its candidates without changing decisions.
    try:
        candidates = load_all_results()
        jobs = load_all_jobs()
    except (OSError, ValueError) as error:
        show_error(f"Could not load saved results: {error}")
        return
    if not candidates and not jobs:
        show_message("No saved results yet. Screen a batch first.")
        return
    if any(not candidate["job_id"] for candidate in candidates):
        jobs.append({"job_id": "", "title": "Older results without a job ID", "created_at": ""})
    if not jobs:
        show_error("Candidates have job IDs, but no corresponding saved jobs are available.")
        return
    job = select_saved_job(jobs)
    if job is None:
        return
    display_job_details(job)
    try:
        candidates = load_job_results(job["job_id"])
    except (OSError, ValueError) as error:
        show_error(f"Could not load this job's candidates: {error}")
        return
    if not candidates:
        show_message("No candidates have been saved for this job.")
        return
    display_saved_results(candidates)
    while True:
        candidate = select_saved_candidate(candidates)
        if candidate is None:
            return
        display_candidate_detail(candidate)


def main():
    # Coordinate menu actions; create an AI client only when screening is selected.
    show_message("WELCOME TO THE RESUME SCREENING TOOL")
    try:
        while True:
            choice = get_main_menu_choice()
            if choice == "1":
                screen_new_batch()
            elif choice == "2":
                view_saved_results()
            else:
                show_message("Exiting program.")
                return
    except (KeyboardInterrupt, EOFError):
        show_message("\nExiting. Any records already saved remain on disk.")


if __name__ == "__main__":
    main()
