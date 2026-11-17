# CLI entry point and controllers for the OOP Resume Screener application

from abc import ABC, abstractmethod
import os
from pathlib import Path
import sys

# Ensure project root is on sys.path when executed directly as `python OOP/main.py`
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from OOP.data_manager import ScreeningStore, StorageError
from OOP.io_manager import (
    CandidateReport,
    ConsoleUI,
    PdfCandidateReport,
    ResumeImporter,
)
from OOP.logic_manager import ScreeningBatch
from OOP.screening_service import ScreeningService


# Abstract base class sharing ConsoleUI/ScreeningStore collaborators and helper logic
class CLIController(ABC):

    def __init__(
        self,
        ui: ConsoleUI | None = None,
        store: ScreeningStore | None = None,
    ):
        self._ui = ui or ConsoleUI()
        self._store = store or ScreeningStore()

    @staticmethod
    def _read_field(item, field: str, default=None):
        # read an attribute or dict key uniformly across domain objects and legacy dicts
        if isinstance(item, dict):
            return item.get(field, default)
        return getattr(item, field, default)

    @abstractmethod
    def run(self) -> None:
        # start the controller's interactive CLI flow
        raise NotImplementedError


# Walks saved candidates sequentially while preserving position across jumps
class ReviewSession(CLIController):

    def __init__(self, ui: ConsoleUI, store: ScreeningStore, candidates: list):
        super().__init__(ui=ui, store=store)
        self._candidates = list(candidates)
        self._position = 0
        self._jumped_candidate = None

    def _can_decide(self, candidate) -> bool:
        if hasattr(candidate, "can_record_decision"):
            return bool(candidate.can_record_decision())
        status = self._read_field(candidate, "status")
        final_score = self._read_field(candidate, "final_score")
        return status != "RE_ENTRY" and final_score is not None

    # execute sequential review flow polymorphically via CLIController.run()
    def run(self) -> None:
        while self._position < len(self._candidates):
            paused = self._candidates[self._position]
            paused_id = str(self._read_field(paused, "candidate_id", ""))
            if self._jumped_candidate is None:
                candidate = paused
                self._ui.show_message(
                    f"\nREVIEW {self._position + 1} OF {len(self._candidates)}"
                )
            else:
                candidate = self._jumped_candidate
                self._ui.show_message(
                    f"\nJUMPED REVIEW — return to {paused_id} afterward"
                )

            action = self.review_candidate(candidate)
            if action == "exit":
                return
            if action == "jump":
                target = self._ui.select_saved_candidate(
                    self._candidates,
                    prompt="Enter a candidate ID to jump to, or press Enter to cancel the jump: ",
                )
                if target is not None:
                    self._jumped_candidate = None if target is paused else target
                continue

            if self._jumped_candidate is not None:
                self._jumped_candidate = None
                self._ui.show_message(
                    f"Returning to {paused_id} in the sequential review."
                )
            else:
                self._position += 1

        self._ui.show_message("Sequential review complete. Returning to the main menu.")

    # preserve start() alias matching UML diagrams
    def start(self) -> None:
        self.run()

    # show details, block RE_ENTRY/unscored candidates, and save explicit decisions
    def review_candidate(self, candidate) -> str:
        self._ui.show_candidate_detail(candidate)
        if not self._can_decide(candidate):
            self._ui.show_message(
                "This candidate needs successful screening before a decision can be recorded."
            )
            return "next"

        decision = self._ui.collect_decision()
        if decision in ("jump", "exit"):
            return decision
        if decision is None:
            self._ui.show_message("Skipped. The current recruiter decision is unchanged.")
            return "next"

        candidate_id = str(self._read_field(candidate, "candidate_id", ""))
        try:
            saved = self._store.update_decision(candidate_id, decision)
        except (OSError, StorageError, ValueError) as error:
            self._ui.show_error(
                f"Could not finish saving the decision and its audit entry: {error}"
            )
            self._ui.show_message("Reload saved results to check the current decision.")
            return "exit"

        if not saved:
            self._ui.show_error("Candidate no longer exists in the CSV. Reload saved results.")
            return "exit"

        if hasattr(candidate, "set_decision"):
            candidate.set_decision(decision)
        elif isinstance(candidate, dict):
            candidate["recruiter_decision"] = decision
        self._ui.show_message(f"Decision saved for {candidate_id}: {decision}")
        return "next"


# Top-level CLI controller coordinating IO, screening workflow, review, and persistence
class Main(CLIController):

    def __init__(
        self,
        ui: ConsoleUI | None = None,
        importer: ResumeImporter | None = None,
        store: ScreeningStore | None = None,
        screening: ScreeningService | None = None,
        report_generator: CandidateReport | None = None,
        reports_dir: str | Path | None = None,
    ):
        super().__init__(ui=ui, store=store)
        self._importer = importer or ResumeImporter()
        self._screening = screening or ScreeningService(store=self._store)
        self._report: CandidateReport = report_generator or PdfCandidateReport()
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

    # display successes and failed records for an active ScreeningBatch
    def _report_batch_summary(self, batch: ScreeningBatch) -> None:
        self._ui.show_summary(batch.success_count(), batch.failed_records())

    # Option 1: collect inputs, run AI screening + retries, evaluate/rank, and persist batch
    def screen_new_batch(self) -> None:
        # fail early if the OpenRouter API key is missing before collecting inputs
        try:
            self._screening.ensure_ai_client()
        except ValueError as error:
            self._ui.show_error(f"creating AI client: {error}")
            return

        try:
            try:
                resume_list, job_description, preferences = self._ui.collect_inputs(
                    self._importer
                )
                if not resume_list:
                    self._ui.show_message("No valid resumes to screen.")
                    return

                batch = self._screening.start_batch(
                    job_description, preferences, resume_list
                )
                self._ui.show_message(f"\nScreening role: {batch.job.title}")

                # keep the batch in memory until screening and retry choices finish
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
                    self._screening.retry_failed(
                        batch, on_progress=self._ui.show_progress
                    )
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

    # export either one candidate PDF or a full job batch summary PDF via CandidateReport
    def _export_pdf_menu(self, candidates: list, job) -> None:
        choice = self._ui.get_pdf_export_choice()
        if not choice:
            return
        if choice == "1":
            candidate = self._ui.select_saved_candidate(
                candidates,
                prompt="Enter candidate ID for PDF report (or press Enter to cancel): ",
            )
            if candidate is None:
                return
            cid = self._read_field(candidate, "candidate_id", "candidate")
            target = self._reports_dir / f"{cid}_report.pdf"
            try:
                saved_path = self._report.generate_individual(candidate, target)
            except (OSError, ValueError) as error:
                self._ui.show_error(f"Could not export individual PDF report: {error}")
                return
            self._ui.show_message(f"Saved individual PDF report to {saved_path}")
        elif choice == "2":
            job_id = self._read_field(job, "job_id", "") or "older_results"
            target = self._reports_dir / f"{job_id}_batch_report.pdf"
            try:
                saved_path = self._report.generate_batch(candidates, target, job=job)
            except (OSError, ValueError) as error:
                self._ui.show_error(f"Could not export batch PDF report: {error}")
                return
            self._ui.show_message(f"Saved batch PDF report to {saved_path}")

    # Option 2 / 3: load saved jobs/candidates, then view/filter/compare/export or run ReviewSession
    def view_saved_results(self, review: bool = False) -> None:
        try:
            all_candidates = self._store.load_results()
            jobs = list(self._store.load_jobs())
        except (OSError, StorageError, ValueError) as error:
            self._ui.show_error(f"Could not load saved results: {error}")
            return

        if not all_candidates and not jobs:
            self._ui.show_message("No saved results yet. Screen a batch first.")
            return

        if any(not self._read_field(c, "job_id", "") for c in all_candidates):
            jobs.append(
                {
                    "job_id": "",
                    "title": "Older results without a job ID",
                    "created_at": "",
                }
            )
        if not jobs:
            self._ui.show_error(
                "Candidates have job IDs, but no corresponding saved jobs are available."
            )
            return

        job = self._ui.select_saved_job(jobs)
        if job is None:
            return
        self._ui.show_job_details(job)

        job_id = self._read_field(job, "job_id", "") or ""
        try:
            candidates = self._store.load_results(job_id)
        except (OSError, StorageError, ValueError) as error:
            self._ui.show_error(f"Could not load this job's candidates: {error}")
            return

        if not candidates:
            self._ui.show_message("No candidates have been saved for this job.")
            return

        self._ui.show_saved_results(candidates)
        if review:
            session: CLIController = ReviewSession(self._ui, self._store, candidates)
            session.run()
            return

        self._browse_saved_candidates(candidates, job)

    # interactive post-listing loop for inspecting details, skill filtering, comparison, and PDF export
    def _browse_saved_candidates(self, candidates: list, job) -> None:
        while True:
            choice = self._ui.get_saved_results_action()
            if not choice:
                return
            if choice == "1":
                candidate = self._ui.select_saved_candidate(candidates)
                if candidate is not None:
                    self._ui.show_candidate_detail(candidate)
            elif choice == "2":
                skills = self._ui.collect_skill_filter()
                self._ui.show_skill_filtered_results(candidates, skills)
            elif choice == "3":
                pair = self._ui.select_candidates_for_comparison(candidates)
                if pair is not None:
                    self._ui.show_candidate_comparison(pair[0], pair[1])
            elif choice == "4":
                self._export_pdf_menu(candidates, job)

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
            self._ui.show_error(
                f"Could not finish deleting the job and its audit entry: {error}"
            )
            self._ui.show_message("Reload saved jobs and results to check their current state.")
            return

        if deleted_count is None:
            self._ui.show_error("Job no longer exists. Reload saved jobs.")
            return

        self._ui.show_message(
            f"Deleted job {job.job_id} and {deleted_count} candidate record(s)."
        )


if __name__ == "__main__":
    app: CLIController = Main()
    app.run()
