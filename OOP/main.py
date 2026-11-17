# CLI entry point for the OOP Resume Screener application

import os
from pathlib import Path
import sys

# Ensure project root is on sys.path when executed directly as `python OOP/main.py`
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from OOP.data_manager import ScreeningStore, StorageError
from OOP.io_manager import ConsoleUI, PdfCandidateReport, ResumeImporter
from OOP.logic_manager import ScreeningBatch
from OOP.screening_service import ScreeningService


# Top-level CLI controller coordinating IO, screening workflow, review, and persistence
class Application:

    def __init__(
        self,
        ui: ConsoleUI | None = None,
        importer: ResumeImporter | None = None,
        store: ScreeningStore | None = None,
        screening: ScreeningService | None = None,
        report_generator: PdfCandidateReport | None = None,
        reports_dir: str | Path | None = None,
    ):
        self._ui = ui or ConsoleUI()
        self._importer = importer or ResumeImporter()
        self._store = store or ScreeningStore()
        self._screening = screening or ScreeningService(store=self._store)
        self._report = report_generator or PdfCandidateReport()
        self._reports_dir = (
            Path(reports_dir)
            if reports_dir is not None
            else Path(self._store.data_directory) / "reports"
        )

    # main menu loop driving all CLI operations
    def run(self) -> None:
        self._ui.show_message("WELCOME TO THE RESUME SCREENING TOOL")
        try:
            while True:
                choice = self._ui.get_main_menu_choice()
                if choice == "1":
                    self.screen_new_batch()
                elif choice == "2":
                    self.view_saved_results(review=False)
                elif choice == "3":
                    self.view_saved_results(review=True)
                elif choice == "4":
                    self.delete_saved_job()
                else:
                    self._ui.show_message("Exiting program.")
                    return
        except (KeyboardInterrupt, EOFError):
            self._ui.show_message("\nExiting. Any records already saved remain on disk.")

    # Display successes and failed records for an active ScreeningBatch
    def _report_batch_summary(self, batch: ScreeningBatch) -> None:
        self._ui.show_summary(batch.success_count(), batch.failed_records())

    # Option 1: collect inputs, run AI screening + retries, evaluate/rank, and persist batch
    def screen_new_batch(self) -> None:
        # Fail early if the OpenRouter API key is missing before collecting inputs
        try:
            self._screening.ensure_ai_client()
        except ValueError as error:
            self._ui.show_error(f"creating AI client: {error}")
            return

        try:
            try:
                resume_list, job_description, preferences = self._ui.collect_inputs(self._importer)
                if not resume_list:
                    self._ui.show_message("No valid resumes to screen.")
                    return

                batch = self._screening.start_batch(job_description, preferences, resume_list)
                self._ui.show_message(f"\nScreening role: {batch.job.title}")

                # Keep the batch in memory until screening and retry decisions complete
                self._ui.show_message("\nScreening...")
                self._screening.screen_all(batch, on_progress=self._ui.show_progress)
                self._report_batch_summary(batch)

                while True:
                    retryable_ids = batch.retryable_ids()
                    if not retryable_ids:
                        break
                    if not self._ui.question_api_retry(len(retryable_ids)):
                        break
                    self._ui.show_message("\nRetrying...")
                    self._screening.retry_failed(batch, on_progress=self._ui.show_progress)
                    self._report_batch_summary(batch)
            except (KeyboardInterrupt, EOFError):
                self._ui.show_message(
                    "\nBatch cancelled. No data from this batch was saved. Start a new batch to try again."
                )
                return

            ranking_rows = self._screening.evaluate_and_rank(batch)
            self._ui.show_rankings(ranking_rows)

            try:
                outcome = self._screening.persist_batch(batch)
            except (OSError, StorageError, ValueError) as error:
                self._ui.show_error(
                    f"Could not finish saving the job and its audit entry: {error}"
                )
                return

            self._ui.show_message(
                f"\nScreening job: {outcome['job_id']} — {batch.job.title}"
            )
            for file_name, failure_msg in outcome["save_failures"]:
                self._ui.show_error(
                    f"Could not finish saving '{file_name}' and its audit entry: {failure_msg}"
                )
            self._ui.show_message(
                f"\nSaved {len(outcome['saved_ids'])}/{len(batch.records)} candidate records "
                f"to {self._store.results_path} with audit entries in {self._store.audit_path}."
            )
            if outcome["debug_warning"]:
                self._ui.show_message(f"Warning: {outcome['debug_warning']}")
        except (KeyboardInterrupt, EOFError):
            self._ui.show_message("\nInterrupted. Any records already saved remain on disk.")

    # Option 2 / 3: view or review saved screening results (implemented in Parts 3-4)
    def view_saved_results(self, review: bool = False) -> None:
        self._ui.show_message("Saved results view/review will be wired in Parts 3-4.")

    # Option 4: select a saved job, confirm, and delete it along with linked candidate rows
    def delete_saved_job(self) -> None:
        try:
            jobs = self._store.load_jobs()
        except (OSError, StorageError, ValueError) as error:
            self._ui.show_error(f"Could not load saved jobs: {error}")
            return

        if not jobs:
            self._ui.show_message("No saved jobs to delete.")
            return

        job = self._ui.select_saved_job(jobs)
        if job is None:
            return

        try:
            candidates = self._store.load_results(job.job_id)
        except (OSError, StorageError, ValueError) as error:
            self._ui.show_error(f"Could not load this job's candidates: {error}")
            return

        self._ui.show_job_details(job)
        if not self._ui.confirm_delete(job, len(candidates)):
            self._ui.show_message("Deletion cancelled. No records were removed.")
            return

        try:
            deleted_count = self._store.delete_job(job.job_id)
        except (OSError, StorageError, ValueError) as error:
            self._ui.show_error(f"Could not finish deleting the job and its audit entry: {error}")
            self._ui.show_message("Reload saved jobs and results to check their current state.")
            return

        if deleted_count is None:
            self._ui.show_error("Job no longer exists. Reload saved jobs.")
            return

        self._ui.show_message(
            f"Deleted job {job.job_id} and {deleted_count} candidate record(s)."
        )


if __name__ == "__main__":
    Application().run()
