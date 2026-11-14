"""Data manager (Phase 2, object-oriented).

Saves and loads jobs, candidate results and the audit log (CSV), plus the
optional debug JSON. Other managers only talk to ScreeningStore.

Class relationships (for the UML / report)
  Inheritance   CsvRepository (abstract) -> JobRepository, CandidateRepository, AuditLog
                DebugResultStore (logic_manager) -> AtomicDebugResultStore
                Job (logic_manager) -> SavedJob
                ValueError -> StorageError
  Composition   ScreeningStore creates and owns its repositories and the debug store
  Aggregation   one CsvFile is injected into every repository and can exist without them
  Association   CandidateRepository <-> AuditLog (collaborate, neither owns the other)
  Polymorphism  ScreeningStore and the tests call load_all() on any CsvRepository
"""

import csv
import json
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile

from OOP.logic_manager import (
    VALID_RECOMMENDATIONS,
    DebugResultStore,
    Job,
    ScreeningPreferences,
    _MappingCompatMixin,
)


class StorageError(ValueError):
    """A saved file is missing data, is corrupt, or could not be written.

    It subclasses ValueError so callers that already catch ValueError keep working.
    """


@dataclass(frozen=True)
class AuditEntry:
    """One line of the audit log. candidate_id may list several IDs (job deletion)."""

    timestamp: str
    action: str
    candidate_id: str
    details: str


class FieldCodec:
    """Converts values to and from the text stored in CSV cells."""

    SEPARATOR = " | "

    @staticmethod
    def utc_timestamp() -> str:
        # explicit UTC offset so local and Docker records share one time basis
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @classmethod
    def list_to_text(cls, items) -> str:
        return cls.SEPARATOR.join(str(item) for item in items)

    @classmethod
    def text_to_list(cls, text) -> list[str]:
        if not text:
            return []
        return [part for part in text.split(cls.SEPARATOR) if part]

    @staticmethod
    def text_to_number(text, as_int: bool = False):
        # blank or unreadable text means "no value", never a fake 0
        if text is None or text == "":
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        if not math.isfinite(number):
            return None
        return int(number) if as_int else number

    @staticmethod
    def number_to_text(value) -> str:
        if value is None or value == "":
            return ""
        number = float(value)
        return str(int(number)) if number.is_integer() else str(number)

    @staticmethod
    def bool_to_text(value) -> str:
        return "yes" if str(value).lower() in ("true", "yes") else "no"


class AtomicFileWriter:
    """Writes a complete temporary file, then replaces the real one.

    A failed save therefore never leaves a half-written file behind.
    """

    def write(self, path: str, write_content, newline=None) -> None:
        temporary_path = None
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with NamedTemporaryFile(
                mode="w", newline=newline, encoding="utf-8",
                dir=os.path.dirname(os.path.abspath(path)),
                prefix="update_", suffix=".tmp", delete=False,
            ) as file:
                temporary_path = file.name
                write_content(file)
            # the temp file is closed first so replacing also works on Windows
            os.replace(temporary_path, path)
            temporary_path = None
        except (OSError, ValueError, TypeError, csv.Error) as error:
            note = self._remove_temporary(temporary_path)
            temporary_path = None
            raise StorageError(f"Could not save '{path}': {error}{note}") from error
        finally:
            # also covers interruptions such as Ctrl+C
            self._remove_temporary(temporary_path)

    @staticmethod
    def _remove_temporary(temporary_path) -> str:
        # returns a message when cleanup fails so the caller can report both problems
        if temporary_path is None:
            return ""
        try:
            os.remove(temporary_path)
        except FileNotFoundError:
            return ""
        except OSError as error:
            return f" Temporary file '{temporary_path}' could not be removed: {error}"
        return ""


class CsvFile:
    """File adapter: the only class that reads or writes CSV files."""

    def __init__(self, writer: AtomicFileWriter | None = None):
        self._writer = writer or AtomicFileWriter()

    def read(self, path: str, fields) -> list[dict]:
        """Return the rows as dicts; a missing file means no rows (and is not created)."""
        if not os.path.exists(path):
            return []
        try:
            # utf-8-sig also accepts files that Excel saved with a byte-order mark
            with open(path, "r", newline="", encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames and not set(reader.fieldnames) & set(fields):
                    raise StorageError(f"'{path}' does not have the expected columns.")
                return list(reader)
        except (OSError, ValueError, csv.Error) as error:
            if isinstance(error, StorageError):
                raise
            raise StorageError(f"Could not read '{path}': {error}") from error

    def write_atomic(self, path: str, fields, rows) -> None:
        def write_content(file):
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        self._writer.write(path, write_content, newline="")

    def append(self, path: str, fields, row: dict) -> None:
        self._create_if_missing(path, fields)
        try:
            with open(path, "a", newline="", encoding="utf-8") as file:
                csv.DictWriter(file, fieldnames=fields).writerow(row)
        except (OSError, ValueError, csv.Error) as error:
            raise StorageError(f"Could not append to '{path}': {error}") from error

    def _create_if_missing(self, path: str, fields) -> None:
        if not os.path.exists(path):
            self.write_atomic(path, fields, [])


class CandidateRecord(_MappingCompatMixin):
    """One job-specific screening result as it is saved and shown to recruiters.

    The resume text is never stored here. status, recruiter_decision and
    feedback_rating are read-only properties; change them through the methods
    so the business rules always run.
    """

    FIELDS = (
        "candidate_id", "job_id", "job_title", "file_name", "file_path",
        "final_score", "skills_score", "experience_score", "education_score",
        "ai_overall_score", "confidence", "status", "fast_track",
        "skills_present", "skills_missing", "missing_must_haves", "stale_skills",
        "evidence", "summary", "notes", "recruiter_decision", "feedback_rating",
        "created_at", "updated_at",
    )
    LIST_FIELDS = ("skills_present", "skills_missing", "missing_must_haves", "stale_skills", "notes")
    NUMBER_FIELDS = ("final_score", "skills_score", "experience_score", "education_score", "ai_overall_score")
    VALID_DECISIONS = ("pending", "shortlisted", "rejected")

    def __init__(
        self, file_name="", file_path="", candidate_id="", job_id="", job_title="",
        final_score=None, skills_score=None, experience_score=None,
        education_score=None, ai_overall_score=None, confidence="",
        status="RE_ENTRY", fast_track=False, skills_present=None,
        skills_missing=None, missing_must_haves=None, stale_skills=None,
        evidence="", summary="", notes=None, recruiter_decision="",
        feedback_rating=None, created_at="", updated_at="",
    ):
        self.candidate_id = str(candidate_id)
        self.job_id = str(job_id)
        self.job_title = str(job_title)
        self.file_name = str(file_name)
        self.file_path = str(file_path)
        # a score of None means "not scored"; a real 0 must stay 0
        self.final_score = final_score
        self.skills_score = skills_score
        self.experience_score = experience_score
        self.education_score = education_score
        self.ai_overall_score = ai_overall_score
        self.confidence = str(confidence)
        self.fast_track = bool(fast_track)
        self.skills_present = list(skills_present or [])
        self.skills_missing = list(skills_missing or [])
        self.missing_must_haves = list(missing_must_haves or [])
        self.stale_skills = list(stale_skills or [])
        self.evidence = str(evidence)
        self.summary = str(summary)
        self.notes = list(notes or [])
        self.created_at = str(created_at)
        self.updated_at = str(updated_at)
        self._status = self._checked_status(status)
        self._recruiter_decision = self._checked_decision(recruiter_decision)
        self._feedback_rating = None if feedback_rating is None else self._checked_rating(feedback_rating)

    @property
    def status(self) -> str:
        return self._status

    @property
    def recruiter_decision(self) -> str:
        return self._recruiter_decision

    @property
    def feedback_rating(self):
        return self._feedback_rating

    def can_record_decision(self) -> bool:
        # failed or unscored records cannot receive a recruiter decision
        return self._status != "RE_ENTRY" and self.final_score is not None

    def set_decision(self, decision: str) -> None:
        decision = self._checked_decision(decision)
        if decision == "":
            raise ValueError(f"Invalid decision ''. Use one of {list(self.VALID_DECISIONS)}")
        if not self.can_record_decision():
            raise ValueError("Failed or unscored records cannot receive a recruiter decision.")
        self._recruiter_decision = decision

    def set_feedback(self, rating) -> None:
        self._feedback_rating = self._checked_rating(rating)

    def to_dict(self) -> dict:
        data = {}
        for field in self.FIELDS:
            value = getattr(self, field)
            data[field] = list(value) if isinstance(value, list) else value
        return data

    @staticmethod
    def _checked_status(status) -> str:
        status = str(status).upper()
        if status not in VALID_RECOMMENDATIONS:
            raise ValueError(f"Invalid status '{status}'. Use one of {list(VALID_RECOMMENDATIONS)}")
        return status

    @classmethod
    def _checked_decision(cls, decision) -> str:
        # an empty decision means "not set yet"; the repository fills in "pending"
        decision = str(decision or "").strip().lower()
        if decision and decision not in cls.VALID_DECISIONS:
            raise ValueError(f"Invalid decision '{decision}'. Use one of {list(cls.VALID_DECISIONS)}")
        return decision

    @staticmethod
    def _checked_rating(rating) -> int:
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            raise ValueError("Rating must be a whole number from 1 to 10") from None
        if not 1 <= rating <= 10:
            raise ValueError("Rating must be between 1 and 10")
        return rating


class SavedJob(Job):
    """A job restored from jobs.csv.

    Adds the saved qualifying score as an attribute, because the console's job
    display reads job.min_qualifying_score. Everything else behaves like Job.
    """

    def __init__(self, min_qualifying_score=None, **job_fields):
        preferences = None
        if min_qualifying_score is not None:
            preferences = ScreeningPreferences(min_qualifying_score)
        super().__init__(preferences=preferences, **job_fields)
        self._saved_threshold = min_qualifying_score

    @property
    def min_qualifying_score(self):
        return self._saved_threshold

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["min_qualifying_score"] = self._saved_threshold
        return data


class CandidateMapper:
    """Turns screening results into CandidateRecords, and records into CSV rows and back."""

    def __init__(self, codec: FieldCodec | None = None):
        self._codec = codec or FieldCodec()

    def from_screening(self, record, resume, evaluation, job) -> CandidateRecord:
        """Build the record to save; failed or unscorable screenings become unscored RE_ENTRY."""
        job_id = self._read(job, "job_id")
        job_title = self._read(job, "title") or self._read(job, "job_title")
        file_name = self._read(record, "file_name") or self._read(resume, "file_name")
        file_path = self._read(resume, "file_path")

        failure = self._failure_reason(record, evaluation)
        if failure is not None:
            return CandidateRecord(
                file_name=file_name, file_path=file_path, job_id=job_id,
                job_title=job_title, status="RE_ENTRY", notes=[failure],
            )

        present, missing, evidence_parts = self._split_skills(self._read(evaluation, "skill_details", []))
        return CandidateRecord(
            file_name=file_name, file_path=file_path, job_id=job_id, job_title=job_title,
            final_score=self._read(evaluation, "final_score", None),
            skills_score=self._read(evaluation, "skills_score", None),
            experience_score=self._read(evaluation, "experience_score", None),
            education_score=self._read(evaluation, "education_score", None),
            ai_overall_score=self._read(evaluation, "ai_overall_score", None),
            confidence=self._read(evaluation, "confidence"),
            status=self._read(evaluation, "status", "RE_ENTRY"),
            fast_track=self._read(evaluation, "fast_track", False),
            skills_present=present, skills_missing=missing,
            missing_must_haves=self._read(evaluation, "missing_must_haves", []),
            stale_skills=self._read(evaluation, "stale_skills", []),
            evidence="; ".join(evidence_parts),
            summary=self._read(evaluation, "summary"),
            notes=self._read(evaluation, "notes", []),
        )

    def to_row(self, candidate: CandidateRecord) -> dict:
        row = {}
        data = candidate.to_dict()
        for field in CandidateRecord.FIELDS:
            value = data[field]
            if value is None:
                value = ""
            elif field == "fast_track":
                value = self._codec.bool_to_text(value)
            elif isinstance(value, list):
                value = self._codec.list_to_text(value)
            row[field] = value
        return row

    def from_row(self, row: dict) -> CandidateRecord:
        # only a missing cell is blank; a stored 0 or 0.0 is a real value
        text = {
            field: "" if row.get(field) is None else str(row.get(field))
            for field in CandidateRecord.FIELDS
        }
        values = dict(text)
        for field in CandidateRecord.LIST_FIELDS:
            values[field] = self._codec.text_to_list(text[field])
        for field in CandidateRecord.NUMBER_FIELDS:
            values[field] = self._codec.text_to_number(text[field])
        values["fast_track"] = text["fast_track"] == "yes"
        values["feedback_rating"] = self._codec.text_to_number(text["feedback_rating"], as_int=True)
        return CandidateRecord(**values)

    def _failure_reason(self, record, evaluation):
        # None means the screening produced a usable score
        scoring_failed = evaluation is not None and self._read(evaluation, "status") == "RE_ENTRY"
        record_failed = self._read(record, "status", "success") != "success"
        if not (record_failed or evaluation is None or scoring_failed):
            return None
        if scoring_failed:
            return "; ".join(self._read(evaluation, "notes", [])) or "AI result could not be scored."
        return self._read(record, "error") or "No AI result"

    def _split_skills(self, skill_details):
        present, missing, evidence_parts = [], [], []
        for skill in skill_details:
            name = self._read(skill, "name")
            if self._read(skill, "present", False):
                present.append(name)
                evidence = self._read(skill, "evidence")
                if evidence:
                    evidence_parts.append(f"{name}: {evidence}")
                else:
                    evidence_parts.append(f"{name}: claimed by AI without supporting evidence")
            else:
                missing.append(name)
        return present, missing, evidence_parts

    @staticmethod
    def _read(source, key, default=""):
        # the managers pass either dicts or objects, so accept both
        if source is None:
            return default
        value = source.get(key, default) if isinstance(source, dict) else getattr(source, key, default)
        return default if value is None else value


class CsvRepository(ABC):
    """Abstract base for the CSV-backed repositories.

    Holds the shared CsvFile and path, and lets subclasses add their own
    validation by overriding _read_rows (template method).
    """

    FIELDS: tuple = ()

    def __init__(self, csv_file: CsvFile, path: str):
        self._csv = csv_file
        self._path = str(path)

    @property
    def path(self) -> str:
        return self._path

    def _read_rows(self) -> list[dict]:
        return self._csv.read(self._path, self.FIELDS)

    def _write_rows(self, rows: list[dict]) -> None:
        self._csv.write_atomic(self._path, self.FIELDS, rows)

    @abstractmethod
    def load_all(self) -> list:
        """Return every saved item; a missing file means an empty list."""


class AuditLog(CsvRepository):
    """Append-only history of every change."""

    FIELDS = ("timestamp", "action", "candidate_id", "details")

    def append(self, action: str, details: str = "", candidate_ids="") -> None:
        if not isinstance(candidate_ids, str):
            candidate_ids = ",".join(candidate_ids)
        self._csv.append(self._path, self.FIELDS, {
            "timestamp": FieldCodec.utc_timestamp(),
            "action": action,
            "candidate_id": candidate_ids,
            "details": details,
        })

    def load_all(self) -> list[AuditEntry]:
        return [
            AuditEntry(
                row.get("timestamp") or "", row.get("action") or "",
                row.get("candidate_id") or "", row.get("details") or "",
            )
            for row in self._read_rows()
        ]

    def historical_candidate_ids(self) -> list[str]:
        # one entry (job deletion) can list several IDs, so split them
        ids = []
        for entry in self.load_all():
            ids.extend(part for part in entry.candidate_id.split(",") if part)
        return ids


class JobRepository(CsvRepository):
    """Saved screening jobs (jobs.csv)."""

    FIELDS = (
        "job_id", "title", "required_skills", "preferred", "min_experience",
        "education", "min_qualifying_score", "created_at",
    )

    def __init__(self, csv_file: CsvFile, path: str, codec: FieldCodec | None = None):
        super().__init__(csv_file, path)
        self._codec = codec or FieldCodec()

    def save(self, job, preferences=None) -> str:
        """Save one job and return its new ID; identical titles stay separate jobs."""
        source = job
        job = Job.from_any(source)
        if preferences is None:
            preferences = getattr(source, "preferences", None)
        threshold = ScreeningPreferences.from_any(preferences).min_qualifying_score

        rows = self._read_rows()
        job_id = self._next_id(rows)
        rows.append({
            "job_id": job_id,
            "title": job.title,
            "required_skills": self._codec.list_to_text(job.required_skills),
            "preferred": self._codec.list_to_text(job.preferred),
            "min_experience": self._codec.number_to_text(job.min_experience),
            "education": job.education,
            "min_qualifying_score": self._codec.number_to_text(threshold),
            "created_at": FieldCodec.utc_timestamp(),
        })
        self._write_rows(rows)
        return job_id

    def load_all(self) -> list[SavedJob]:
        jobs = []
        for row in self._read_rows():
            if not (row.get("job_id") or "").strip() or "title" not in row:
                raise StorageError("Saved job record is missing its job ID or title column.")
            jobs.append(self._from_row(row))
        return jobs

    def find(self, job_id: str):
        for job in self.load_all():
            if job.job_id == job_id:
                return job
        return None

    def delete(self, job_id: str) -> bool:
        rows = self._read_rows()
        remaining = [row for row in rows if row.get("job_id") != job_id]
        if len(remaining) == len(rows):
            return False
        self._write_rows(remaining)
        return True

    @staticmethod
    def _next_id(rows: list[dict]) -> str:
        # next ID comes from the jobs currently saved, so deleted IDs can be reused
        highest = 0
        for row in rows:
            job_id = row.get("job_id") or ""
            if job_id.startswith("J") and job_id[1:].isdigit():
                highest = max(highest, int(job_id[1:]))
        return "J" + str(highest + 1).zfill(3)

    def _from_row(self, row: dict) -> SavedJob:
        return SavedJob(
            title=row.get("title") or "",
            required_skills=self._codec.text_to_list(row.get("required_skills")),
            preferred=self._codec.text_to_list(row.get("preferred")),
            min_experience=self._codec.text_to_number(row.get("min_experience")) or 0.0,
            education=row.get("education") or "",
            job_id=row["job_id"],
            created_at=row.get("created_at") or "",
            min_qualifying_score=self._codec.text_to_number(row.get("min_qualifying_score")),
        )


class CandidateRepository(CsvRepository):
    """Saved screening results (candidate_results.csv), with search and counts."""

    FIELDS = CandidateRecord.FIELDS

    def __init__(self, csv_file: CsvFile, path: str, audit: AuditLog, mapper: CandidateMapper):
        super().__init__(csv_file, path)
        self._audit = audit
        self._mapper = mapper

    def load_all(self) -> list[CandidateRecord]:
        return [self._to_record(row) for row in self._read_rows()]

    def load_job_results(self, job_id: str) -> list[CandidateRecord]:
        # a blank job ID selects older results saved before jobs existed
        return [candidate for candidate in self.load_all() if candidate.job_id == job_id]

    def get(self, candidate_id: str):
        for row in self._read_rows():
            if row["candidate_id"] == candidate_id:
                return self._to_record(row)
        return None

    def save(self, candidate: CandidateRecord) -> str:
        """Insert a new record or update the one with the same ID; return the ID."""
        row = self._mapper.to_row(candidate)
        rows = self._read_rows()
        if not row["candidate_id"]:
            row["candidate_id"] = self._generate_id(rows)
        candidate_id = row["candidate_id"]
        index = self._find_index(rows, candidate_id)
        now = FieldCodec.utc_timestamp()

        if index is None:
            row["created_at"] = row["created_at"] or now
            row["recruiter_decision"] = row["recruiter_decision"] or "pending"
            row["updated_at"] = now
            rows.append(row)
            action = "SAVE_RESULT"
        else:
            # an update that leaves these blank keeps what was already saved
            for field in ("created_at", "recruiter_decision", "feedback_rating", "job_id"):
                if row[field] == "":
                    row[field] = rows[index].get(field) or ""
            row["updated_at"] = now
            rows[index] = row
            action = "UPDATE_RESULT"

        self._write_rows(rows)
        self._audit.append(
            action,
            f"{row['file_name']} | score={row['final_score']} | status={row['status']}",
            candidate_id,
        )
        return candidate_id

    def update_field(self, candidate_id: str, field: str, value, action_name: str) -> bool:
        if field not in self.FIELDS or field == "candidate_id":
            raise ValueError(f"Cannot update field '{field}'.")
        rows = self._read_rows()
        index = self._find_index(rows, candidate_id)
        if index is None:
            return False
        rows[index][field] = value
        rows[index]["updated_at"] = FieldCodec.utc_timestamp()
        self._write_rows(rows)
        self._audit.append(action_name, f"{field} -> {value}", candidate_id)
        return True

    def delete_for_job(self, job_id: str) -> list[str]:
        """Remove every candidate linked to the job and return the removed IDs."""
        rows = self._read_rows()
        kept = [row for row in rows if (row.get("job_id") or "") != job_id]
        removed = [row["candidate_id"] for row in rows if (row.get("job_id") or "") == job_id]
        if removed:
            self._write_rows(kept)
        return removed

    def snapshot(self) -> list[dict]:
        # a copy of the saved rows, so a failed job deletion can be undone
        return [dict(row) for row in self._read_rows()]

    def restore(self, rows: list[dict]) -> None:
        self._write_rows(rows)

    def search(
        self, status=None, decision=None, min_score=None, max_score=None,
        fast_track=None, job_title=None, keyword=None, sort_by_score=True,
    ) -> list[CandidateRecord]:
        matches = []
        for candidate in self.load_all():
            score = candidate.final_score
            if status and candidate.status != status:
                continue
            if decision and candidate.recruiter_decision != decision:
                continue
            if min_score is not None and (score is None or score < min_score):
                continue
            if max_score is not None and (score is None or score > max_score):
                continue
            if fast_track is not None and candidate.fast_track != fast_track:
                continue
            if job_title and candidate.job_title.lower() != job_title.lower():
                continue
            if keyword and keyword.lower() not in self._searchable_text(candidate).lower():
                continue
            matches.append(candidate)
        if sort_by_score:
            # unscored records go last
            matches.sort(key=lambda item: -1 if item.final_score is None else item.final_score, reverse=True)
        return matches

    def count_by_status(self) -> dict:
        counts = {status: 0 for status in VALID_RECOMMENDATIONS}
        for candidate in self.load_all():
            counts[candidate.status] += 1
        return counts

    def _read_rows(self) -> list[dict]:
        # candidate IDs are needed for viewing, updating and creating new IDs
        rows = super()._read_rows()
        if rows and "candidate_id" not in rows[0]:
            raise StorageError(f"Saved candidates in '{self._path}' are missing the candidate_id column.")
        for number, row in enumerate(rows, start=1):
            if not (row.get("candidate_id") or "").strip():
                raise StorageError(
                    f"Saved candidate in '{self._path}' has an empty candidate ID at data row {number}."
                )
        return rows

    def _to_record(self, row: dict) -> CandidateRecord:
        try:
            return self._mapper.from_row(row)
        except ValueError as error:
            raise StorageError(
                f"Saved candidate {row.get('candidate_id')} in '{self._path}' is invalid: {error}"
            ) from error

    def _generate_id(self, rows: list[dict]) -> str:
        # audit history is checked too, so a deleted candidate's ID is never reused
        used_ids = [row["candidate_id"] for row in rows]
        used_ids.extend(self._audit.historical_candidate_ids())
        highest = 0
        for candidate_id in used_ids:
            if candidate_id.startswith("C") and candidate_id[1:].isdigit():
                highest = max(highest, int(candidate_id[1:]))
        return "C" + str(highest + 1).zfill(3)

    @staticmethod
    def _find_index(rows: list[dict], candidate_id: str):
        for index, row in enumerate(rows):
            if row["candidate_id"] == candidate_id:
                return index
        return None

    @staticmethod
    def _searchable_text(candidate: CandidateRecord) -> str:
        return " ".join([
            candidate.file_name, candidate.summary, candidate.evidence,
            " ".join(candidate.skills_present), " ".join(candidate.skills_missing),
            " ".join(candidate.notes),
        ])


class AtomicDebugResultStore(DebugResultStore):
    """logic_manager's debug store, with a crash-safe save.

    load() and load_raw() are inherited unchanged, so RankingService can read
    the file this class writes (Liskov substitution). Only save() is replaced:
    it creates the data folder if needed and writes through AtomicFileWriter.
    """

    def __init__(self, path: str, writer: AtomicFileWriter | None = None):
        super().__init__(path)
        self._writer = writer or AtomicFileWriter()

    @property
    def path(self) -> str:
        return self._path

    def save(self, records, path=None) -> None:
        target = path if path is not None else self._path
        serializable = {
            record_id: record.to_dict() if hasattr(record, "to_dict") else dict(record)
            for record_id, record in records.items()
        }
        self._validate_shape(serializable, target)
        self._writer.write(
            target, lambda file: json.dump(serializable, file, indent=2, ensure_ascii=False)
        )


class ScreeningStore:
    """Facade for the whole data layer: the one class other managers use.

    It creates and owns its repositories (composition). The CsvFile can be
    passed in, so it is shared rather than owned (aggregation).

    Writes across the CSV files and the audit log are not one transaction: a
    CSV write can succeed and the audit write fail. Errors are raised as
    StorageError so the caller can tell the user to reload.
    """

    DEFAULT_DATA_DIRECTORY = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )

    def __init__(self, data_directory: str | None = None, csv_file: CsvFile | None = None):
        self._data_directory = str(data_directory or self.DEFAULT_DATA_DIRECTORY)
        shared_csv = csv_file or CsvFile()
        self._mapper = CandidateMapper()
        self._audit = AuditLog(shared_csv, self._file("audit_log.csv"))
        self._jobs = JobRepository(shared_csv, self._file("jobs.csv"))
        self._candidates = CandidateRepository(
            shared_csv, self._file("candidate_results.csv"), self._audit, self._mapper
        )
        self._debug = AtomicDebugResultStore(self._file("resume_results.json"))

    def _file(self, name: str) -> str:
        return os.path.join(self._data_directory, name)

    @property
    def data_directory(self) -> str:
        return self._data_directory

    @property
    def results_path(self) -> str:
        return self._candidates.path

    @property
    def audit_path(self) -> str:
        return self._audit.path

    @property
    def debug_path(self) -> str:
        return self._debug.path

    # jobs
    def save_job(self, job, preferences=None) -> str:
        """Save a job, record CREATE_JOB in the audit log, and return the new job ID."""
        job_id = self._jobs.save(job, preferences)
        self._audit.append("CREATE_JOB", f"{job_id} | {Job.from_any(job).title}")
        return job_id

    def load_jobs(self) -> list[SavedJob]:
        return self._jobs.load_all()

    def delete_job(self, job_id: str):
        """Delete one job and its linked candidates; return how many candidates, or None if absent.

        If the jobs file cannot be written, the candidate rows are put back.
        """
        if not job_id:
            raise ValueError("A saved job ID is required for deletion.")
        job = self._jobs.find(job_id)
        if job is None:
            return None

        snapshot = self._candidates.snapshot()
        removed_ids = self._candidates.delete_for_job(job_id)
        try:
            self._jobs.delete(job_id)
        except StorageError as error:
            if removed_ids:
                try:
                    self._candidates.restore(snapshot)
                except StorageError as restore_error:
                    raise StorageError(
                        f"Job deletion failed: {error}. Candidate restoration also failed: "
                        f"{restore_error}. Check the saved files before continuing."
                    ) from restore_error
            raise

        # one audit entry keeps the job ID and every removed candidate ID in history
        self._audit.append(
            "DELETE_JOB",
            f"{job_id} | {job.title} | removed {len(removed_ids)} candidate(s)",
            removed_ids,
        )
        return len(removed_ids)

    # candidates
    def save_record(self, record, resume, evaluation, job) -> str:
        """Save one screened resume (or an unscored RE_ENTRY if screening failed)."""
        candidate = self._mapper.from_screening(record, resume, evaluation, job)
        return self._candidates.save(candidate)

    def save_all(self, records: dict, resumes: dict, evaluations: dict, job):
        """Save a whole batch. One failed save does not stop the others.

        Returns (saved_ids, failures) where failures is a list of (file_name, message).
        """
        saved_ids, failures = [], []
        for resume_id, record in records.items():
            resume = resumes.get(resume_id)
            try:
                saved_ids.append(self.save_record(record, resume, evaluations.get(resume_id), job))
            except (OSError, ValueError) as error:
                name = CandidateMapper._read(record, "file_name") or CandidateMapper._read(resume, "file_name")
                failures.append((name, str(error)))
        return saved_ids, failures

    def load_results(self, job_id: str | None = None) -> list[CandidateRecord]:
        if job_id is None:
            return self._candidates.load_all()
        return self._candidates.load_job_results(job_id)

    def get_candidate(self, candidate_id: str):
        return self._candidates.get(candidate_id)

    def update_decision(self, candidate_id: str, decision: str) -> bool:
        """Set shortlisted/rejected/pending; False if the candidate does not exist."""
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            return False
        candidate.set_decision(decision)
        return self._candidates.update_field(
            candidate_id, "recruiter_decision", candidate.recruiter_decision, "RECRUITER_DECISION"
        )

    def save_feedback(self, candidate_id: str, rating) -> bool:
        """Save a 1-10 rating; False if the candidate does not exist."""
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            return False
        candidate.set_feedback(rating)
        return self._candidates.update_field(
            candidate_id, "feedback_rating", candidate.feedback_rating, "FEEDBACK"
        )

    def search_candidates(self, **filters) -> list[CandidateRecord]:
        return self._candidates.search(**filters)

    def count_by_status(self) -> dict:
        return self._candidates.count_by_status()

    # audit and debug output
    def load_audit(self) -> list[AuditEntry]:
        return self._audit.load_all()

    def save_debug(self, records: dict) -> None:
        """Write the optional debug JSON. Callers should treat a failure as a warning."""
        self._debug.save(records)