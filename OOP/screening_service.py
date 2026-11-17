# Shared screening pipeline coordinator used by both main.py (CLI) and APIServer (React GUI)

from OOP.ai_manager import AIManager
from OOP.data_manager import ScreeningStore
from OOP.logic_manager import (
    CandidateEvaluator,
    CandidateRanker,
    Job,
    RankingService,
    ScoringEngine,
    ScreeningBatch,
    ScreeningPreferences,
    ScreeningRecord,
)


# Coordinates AI screening, deterministic evaluation/ranking, and persistence across managers
class ScreeningService:

    def __init__(
        self,
        ai_client=None,
        scorer: CandidateEvaluator | None = None,
        ranker: CandidateRanker | None = None,
        store: ScreeningStore | None = None,
        ai_factory=None,
    ):
        self._ai_client = ai_client
        self._ai_factory = ai_factory or AIManager
        self._evaluator = scorer or ScoringEngine()
        self._ranker = ranker or RankingService(scorer=self._evaluator)
        self._store = store or ScreeningStore()

    # lazily initialize the AI gateway only when screening is actually requested
    def ensure_ai_client(self):
        if self._ai_client is None:
            self._ai_client = self._ai_factory()
        return self._ai_client

    # validate inputs and build a transient ScreeningBatch aggregate
    def start_batch(self, job, preferences, resumes: list) -> ScreeningBatch:
        typed_job = Job.from_any(job)
        typed_prefs = (
            ScreeningPreferences.from_any(preferences)
            if preferences is not None
            else typed_job.preferences
        )
        typed_job.validate()
        typed_prefs.validate()
        return ScreeningBatch(typed_job, typed_prefs, resumes)

    # screen a single anonymized resume via AIManager, capturing retryable vs fatal failures
    def screen_one(self, resume, job) -> ScreeningRecord:
        client = self.ensure_ai_client()
        resume_id = resume["id"] if isinstance(resume, dict) else resume.id
        file_name = resume["file_name"] if isinstance(resume, dict) else resume.file_name
        resume_text = (
            resume["anonymized_text"]
            if isinstance(resume, dict) and "anonymized_text" in resume
            else getattr(resume, "anonymized_text", None)
        )
        if resume_text is None and isinstance(resume, dict):
            resume_text = resume.get("text", "")

        try:
            ai_result = client.process_resume(job, resume_text or "")
            return ScreeningRecord(
                resume_id=resume_id,
                file_name=file_name,
                screening_result=ai_result,
                status="success",
                retryable=False,
            )
        except ConnectionError as exc:
            return ScreeningRecord(
                resume_id=resume_id,
                file_name=file_name,
                screening_result=None,
                status="error",
                retryable=True,
                error=str(exc),
            )
        except ValueError as exc:
            return ScreeningRecord(
                resume_id=resume_id,
                file_name=file_name,
                screening_result=None,
                status="error",
                retryable=False,
                error=str(exc),
            )

    # screen every resume in the batch and notify optional progress callback
    def screen_all(self, batch: ScreeningBatch, on_progress=None) -> ScreeningBatch:
        self.ensure_ai_client()
        for resume in batch.resumes.values():
            record = self.screen_one(resume, batch.job)
            batch.replace_record(record)
            if on_progress is not None:
                on_progress(record)
        return batch

    # retry only records marked retryable=True and return how many were retried
    def retry_failed(self, batch: ScreeningBatch, on_progress=None) -> int:
        retry_ids = batch.retryable_ids()
        if not retry_ids:
            return 0
        self.ensure_ai_client()
        resumes = batch.resumes
        for resume_id in retry_ids:
            resume = resumes[resume_id]
            record = self.screen_one(resume, batch.job)
            batch.replace_record(record)
            if on_progress is not None:
                on_progress(record)
        return len(retry_ids)

    # apply deterministic ScoringEngine rules to all usable AI records in the batch
    def evaluate(self, batch: ScreeningBatch) -> dict:
        evaluations = self._evaluator.evaluate_records(
            batch.records, batch.job, batch.preferences
        )
        for resume_id, evaluation in evaluations.items():
            batch.set_evaluation(resume_id, evaluation)
        return evaluations

    # rank evaluated candidates using CandidateRanker
    def build_rankings(self, batch: ScreeningBatch) -> list:
        return self._ranker.build_rows(batch.records, batch.evaluations)

    # evaluate and return ordered RankingRow objects
    def evaluate_and_rank(self, batch: ScreeningBatch) -> list:
        self.evaluate(batch)
        return self.build_rankings(batch)

    # save job, candidate CSV rows (including RE_ENTRY failures), and optional debug JSON
    def persist_batch(self, batch: ScreeningBatch) -> dict:
        job_id = self._store.save_job(batch.job, batch.preferences)
        batch.job.job_id = job_id

        saved_ids, save_failures = self._store.save_all(
            batch.records, batch.resumes, batch.evaluations, batch.job
        )

        debug_warning = None
        try:
            self._store.save_debug(batch.records)
        except (OSError, ValueError) as exc:
            debug_warning = str(exc)

        return {
            "job_id": job_id,
            "saved_ids": saved_ids,
            "save_failures": save_failures,
            "debug_warning": debug_warning,
        }
