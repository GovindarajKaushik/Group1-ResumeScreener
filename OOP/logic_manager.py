from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
import json
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Union


DEFAULT_RULES = {
    "min_score": 60,
    "fast_track_score": 90,
    "fast_track_min_criterion": 80,
    "must_have_bonus": 5,
    "must_have_missing_cap": 59,
    "recency_years": 5,
    "recency_factor": 0.5,
    "preferred_weight": 0.5,
    "ai_disagree_gap": 25,
}

DEFAULT_WEIGHTS = {
    "skills": 0.50,
    "experience": 0.30,
    "education": 0.20,
}

VALID_CONFIDENCE = ("low", "medium", "high")
VALID_RECOMMENDATIONS = ("SHORTLIST", "SECONDARY_REVIEW", "RE_ENTRY")

REQUIRED_KEYS = [
    "skills",
    "experience_score",
    "education_score",
    "overall_score",
    "confidence",
]


class _MappingCompatMixin:

    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def __getitem__(self, key: str) -> Any:
        data = self.to_dict()
        if key in data:
            return data[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def keys(self) -> Iterable[str]:
        return self.to_dict().keys()

    def values(self) -> Iterable[Any]:
        return self.to_dict().values()

    def items(self) -> Iterable[Tuple[str, Any]]:
        return self.to_dict().items()

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _MappingCompatMixin):
            return self.to_dict() == other.to_dict()
        if isinstance(other, dict):
            return self.to_dict() == other
        return False


class CandidateEvaluator(ABC):

    @abstractmethod
    def evaluate(
        self,
        ai_result: Any,
        job: Any,
        preferences: Any = None,
    ) -> "Evaluation":
        pass

    @abstractmethod
    def evaluate_records(
        self,
        records: Mapping[str, Any],
        job: Any,
        preferences: Any = None,
    ) -> Dict[str, "Evaluation"]:
        pass


class CandidateRanker(ABC):

    @abstractmethod
    def rank(self, evaluations: Mapping[str, Any]) -> List[str]:
        pass

    @abstractmethod
    def build_rows(
        self,
        records: Mapping[str, Any],
        evaluations: Mapping[str, Any],
    ) -> List["RankingRow"]:
        pass


class ResultRepository(ABC):

    @abstractmethod
    def load(self, path: Optional[str] = None) -> Dict[str, "ScreeningRecord"]:
        pass

    @abstractmethod
    def save(
        self,
        records: Mapping[str, Any],
        path: Optional[str] = None,
    ) -> None:
        pass


class ScoringRules(_MappingCompatMixin):

    def __init__(
        self,
        skills_weight: float = DEFAULT_WEIGHTS["skills"],
        experience_weight: float = DEFAULT_WEIGHTS["experience"],
        education_weight: float = DEFAULT_WEIGHTS["education"],
        preferred_weight: float = DEFAULT_RULES["preferred_weight"],
        must_have_bonus: float = DEFAULT_RULES["must_have_bonus"],
        must_have_missing_cap: float = DEFAULT_RULES["must_have_missing_cap"],
        recency_years: int = DEFAULT_RULES["recency_years"],
        recency_factor: float = DEFAULT_RULES["recency_factor"],
        ai_disagree_gap: float = DEFAULT_RULES["ai_disagree_gap"],
        fast_track_score: float = DEFAULT_RULES["fast_track_score"],
        fast_track_min_criterion: float = DEFAULT_RULES["fast_track_min_criterion"],
        min_score: float = DEFAULT_RULES["min_score"],
    ) -> None:
        self._skills_weight = float(skills_weight)
        self._experience_weight = float(experience_weight)
        self._education_weight = float(education_weight)
        self._preferred_weight = float(preferred_weight)
        self._must_have_bonus = float(must_have_bonus)
        self._must_have_missing_cap = float(must_have_missing_cap)
        self._recency_years = int(recency_years)
        self._recency_factor = float(recency_factor)
        self._ai_disagree_gap = float(ai_disagree_gap)
        self._fast_track_score = float(fast_track_score)
        self._fast_track_min_criterion = float(fast_track_min_criterion)
        self._min_score = float(min_score)

    @property
    def skills_weight(self) -> float:
        return self._skills_weight

    @property
    def experience_weight(self) -> float:
        return self._experience_weight

    @property
    def education_weight(self) -> float:
        return self._education_weight

    @property
    def preferred_weight(self) -> float:
        return self._preferred_weight

    @property
    def must_have_bonus(self) -> float:
        return self._must_have_bonus

    @property
    def must_have_missing_cap(self) -> float:
        return self._must_have_missing_cap

    @property
    def recency_years(self) -> int:
        return self._recency_years

    @property
    def recency_factor(self) -> float:
        return self._recency_factor

    @property
    def ai_disagree_gap(self) -> float:
        return self._ai_disagree_gap

    @property
    def fast_track_score(self) -> float:
        return self._fast_track_score

    @property
    def fast_track_min_criterion(self) -> float:
        return self._fast_track_min_criterion

    @property
    def min_score(self) -> float:
        return self._min_score

    def with_preferences(
        self, preferences: Optional[Union["ScreeningPreferences", Mapping[str, Any]]]
    ) -> "ScoringRules":
        if preferences is None:
            return self
        if isinstance(preferences, ScreeningPreferences):
            min_qualifying = preferences.min_qualifying_score
        elif isinstance(preferences, Mapping):
            min_qualifying = preferences.get("min_qualifying_score", self._min_score)
        else:
            min_qualifying = getattr(preferences, "min_qualifying_score", self._min_score)

        return ScoringRules(
            skills_weight=self._skills_weight,
            experience_weight=self._experience_weight,
            education_weight=self._education_weight,
            preferred_weight=self._preferred_weight,
            must_have_bonus=self._must_have_bonus,
            must_have_missing_cap=self._must_have_missing_cap,
            recency_years=self._recency_years,
            recency_factor=self._recency_factor,
            ai_disagree_gap=self._ai_disagree_gap,
            fast_track_score=self._fast_track_score,
            fast_track_min_criterion=self._fast_track_min_criterion,
            min_score=float(min_qualifying),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skills_weight": self._skills_weight,
            "experience_weight": self._experience_weight,
            "education_weight": self._education_weight,
            "preferred_weight": self._preferred_weight,
            "must_have_bonus": int(self._must_have_bonus)
            if self._must_have_bonus.is_integer()
            else self._must_have_bonus,
            "must_have_missing_cap": int(self._must_have_missing_cap)
            if self._must_have_missing_cap.is_integer()
            else self._must_have_missing_cap,
            "recency_years": self._recency_years,
            "recency_factor": self._recency_factor,
            "ai_disagree_gap": int(self._ai_disagree_gap)
            if self._ai_disagree_gap.is_integer()
            else self._ai_disagree_gap,
            "fast_track_score": int(self._fast_track_score)
            if self._fast_track_score.is_integer()
            else self._fast_track_score,
            "fast_track_min_criterion": int(self._fast_track_min_criterion)
            if self._fast_track_min_criterion.is_integer()
            else self._fast_track_min_criterion,
            "min_score": self._min_score,
        }


class ScreeningPreferences(_MappingCompatMixin):

    def __init__(self, min_qualifying_score: float = 60.0) -> None:
        self._min_qualifying_score = float(min_qualifying_score)

    @property
    def min_qualifying_score(self) -> float:
        return self._min_qualifying_score

    @min_qualifying_score.setter
    def min_qualifying_score(self, value: float) -> None:
        self._min_qualifying_score = float(value)

    def validate(self) -> None:
        if not (0.0 <= self._min_qualifying_score <= 100.0):
            raise ValueError("min_qualifying_score must be between 0 and 100")

    @classmethod
    def from_any(
        cls, raw: Optional[Union["ScreeningPreferences", Mapping[str, Any]]]
    ) -> "ScreeningPreferences":
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, Mapping):
            return cls(
                min_qualifying_score=raw.get(
                    "min_qualifying_score", DEFAULT_RULES["min_score"]
                )
            )
        if raw is not None and hasattr(raw, "min_qualifying_score"):
            return cls(min_qualifying_score=getattr(raw, "min_qualifying_score"))
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        return {"min_qualifying_score": self._min_qualifying_score}


class Job(_MappingCompatMixin):

    def __init__(
        self,
        title: str = "",
        required_skills: Optional[List[str]] = None,
        preferred: Optional[List[str]] = None,
        min_experience: float = 0.0,
        education: str = "",
        job_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        preferences: Optional[ScreeningPreferences] = None,
    ) -> None:
        self.job_id = job_id
        self.title = str(title).strip()
        self.required_skills = list(required_skills or [])
        self.preferred = list(preferred or [])
        self.min_experience = float(min_experience)
        self.education = str(education).strip()
        self.created_at = created_at
        self._preferences = preferences or ScreeningPreferences()

    @property
    def preferences(self) -> ScreeningPreferences:
        return self._preferences

    def validate(self) -> None:
        if not self.required_skills and not self.preferred:
            raise ValueError("Job must specify at least one required or preferred skill")
        if self.min_experience < 0:
            raise ValueError("min_experience cannot be negative")
        self._preferences.validate()

    @classmethod
    def from_any(cls, raw: Union["Job", Mapping[str, Any]]) -> "Job":
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, Mapping):
            return cls(
                title=raw.get("title", ""),
                required_skills=list(raw.get("required_skills", [])),
                preferred=list(raw.get("preferred", [])),
                min_experience=float(raw.get("min_experience", 0.0) or 0.0),
                education=raw.get("education", ""),
                job_id=raw.get("job_id"),
                created_at=raw.get("created_at"),
            )
        return cls(
            title=getattr(raw, "title", ""),
            required_skills=list(getattr(raw, "required_skills", [])),
            preferred=list(getattr(raw, "preferred", [])),
            min_experience=float(getattr(raw, "min_experience", 0.0) or 0.0),
            education=getattr(raw, "education", ""),
            job_id=getattr(raw, "job_id", None),
            created_at=getattr(raw, "created_at", None),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "required_skills": list(self.required_skills),
            "preferred": list(self.preferred),
            "min_experience": self.min_experience,
            "education": self.education,
            "created_at": self.created_at,
        }


class AbstractSkillRequirement(ABC, _MappingCompatMixin):

    def __init__(
        self,
        name: str,
        present: bool = False,
        last_used_year: Optional[int] = None,
        evidence: str = "",
    ) -> None:
        self._name = str(name).strip()
        self._present = bool(present)
        self._last_used_year = int(last_used_year) if last_used_year is not None else None
        self._evidence = "" if evidence is None else str(evidence).strip()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = str(value).strip()

    @property
    def present(self) -> bool:
        return self._present

    @present.setter
    def present(self, value: bool) -> None:
        self._present = bool(value)

    @property
    def last_used_year(self) -> Optional[int]:
        return self._last_used_year

    @last_used_year.setter
    def last_used_year(self, value: Optional[int]) -> None:
        self._last_used_year = int(value) if value is not None else None

    @property
    def evidence(self) -> str:
        return self._evidence

    @evidence.setter
    def evidence(self, value: str) -> None:
        self._evidence = "" if value is None else str(value).strip()

    def has_evidence(self) -> bool:
        return bool(self._evidence)

    def is_stale(self, current_year: int, recency_years: int) -> bool:
        if not self._present or self._last_used_year is None:
            return False
        return (current_year - self._last_used_year) >= recency_years

    def recency_multiplier(self, current_year: int, rules: ScoringRules) -> float:
        if self.is_stale(current_year, rules.recency_years):
            return rules.recency_factor
        return 1.0

    def calculate_earned_points(self, current_year: int, rules: ScoringRules) -> float:
        if not self._present or not self.has_evidence():
            return 0.0
        return self.get_weight(rules) * self.recency_multiplier(current_year, rules)

    @property
    @abstractmethod
    def category(self) -> str:
        pass

    @abstractmethod
    def get_weight(self, rules: ScoringRules) -> float:
        pass

    @abstractmethod
    def is_mandatory(self) -> bool:
        pass


class SkillEvidence(AbstractSkillRequirement):

    def __init__(
        self,
        name: str,
        category: str = "",
        present: bool = False,
        last_used_year: Optional[int] = None,
        evidence: str = "",
    ) -> None:
        super().__init__(
            name=name,
            present=present,
            last_used_year=last_used_year,
            evidence=evidence,
        )
        self._category = str(category).strip().lower()

    @property
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = str(value).strip().lower()

    def get_weight(self, rules: ScoringRules) -> float:
        if self._category == "must_have":
            return 1.0
        return rules.preferred_weight

    def is_mandatory(self) -> bool:
        return self._category == "must_have"

    @classmethod
    def create_for_category(
        cls,
        name: str,
        category: str,
        present: bool = False,
        last_used_year: Optional[int] = None,
        evidence: str = "",
    ) -> "SkillEvidence":
        normalized = str(category).strip().lower()
        if normalized == "must_have":
            return MustHaveSkillEvidence(
                name=name,
                present=present,
                last_used_year=last_used_year,
                evidence=evidence,
            )
        if normalized == "preferred":
            return PreferredSkillEvidence(
                name=name,
                present=present,
                last_used_year=last_used_year,
                evidence=evidence,
            )
        return cls(
            name=name,
            category=normalized,
            present=present,
            last_used_year=last_used_year,
            evidence=evidence,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "category": self._category,
            "present": self._present,
            "last_used_year": self._last_used_year,
            "evidence": self._evidence,
        }


class MustHaveSkillEvidence(SkillEvidence):

    def __init__(
        self,
        name: str,
        present: bool = False,
        last_used_year: Optional[int] = None,
        evidence: str = "",
    ) -> None:
        super().__init__(
            name=name,
            category="must_have",
            present=present,
            last_used_year=last_used_year,
            evidence=evidence,
        )

    def get_weight(self, rules: ScoringRules) -> float:
        return 1.0

    def is_mandatory(self) -> bool:
        return True


class PreferredSkillEvidence(SkillEvidence):

    def __init__(
        self,
        name: str,
        present: bool = False,
        last_used_year: Optional[int] = None,
        evidence: str = "",
    ) -> None:
        super().__init__(
            name=name,
            category="preferred",
            present=present,
            last_used_year=last_used_year,
            evidence=evidence,
        )

    def get_weight(self, rules: ScoringRules) -> float:
        return rules.preferred_weight

    def is_mandatory(self) -> bool:
        return False


class AIResult(_MappingCompatMixin):

    def __init__(
        self,
        skills: Iterable[Union[SkillEvidence, Mapping[str, Any]]],
        experience_score: float,
        education_score: float,
        overall_score: float,
        confidence: str = "low",
        experience_summary: str = "",
        education_summary: str = "",
        summary: str = "",
    ) -> None:
        self._skills: List[SkillEvidence] = [
            s
            if isinstance(s, SkillEvidence)
            else SkillEvidence.create_for_category(
                name=s.get("name", ""),
                category=s.get("category", ""),
                present=bool(s.get("present", False)),
                last_used_year=s.get("last_used_year"),
                evidence=s.get("evidence", ""),
            )
            for s in skills
        ]
        self._experience_score = float(experience_score)
        self._education_score = float(education_score)
        self._overall_score = float(overall_score)
        conf = str(confidence).strip().lower()
        self._confidence = conf if conf in VALID_CONFIDENCE else "low"
        self._experience_summary = str(experience_summary).strip()
        self._education_summary = str(education_summary).strip()
        self._summary = str(summary).strip()

    @property
    def skills(self) -> List[SkillEvidence]:
        return self._skills

    @property
    def experience_score(self) -> float:
        return self._experience_score

    @property
    def education_score(self) -> float:
        return self._education_score

    @property
    def overall_score(self) -> float:
        return self._overall_score

    @property
    def confidence(self) -> str:
        return self._confidence

    @property
    def experience_summary(self) -> str:
        return self._experience_summary

    @property
    def education_summary(self) -> str:
        return self._education_summary

    @property
    def summary(self) -> str:
        return self._summary

    def is_usable(self) -> bool:
        if not self._skills:
            return False
        for score in (
            self._experience_score,
            self._education_score,
            self._overall_score,
        ):
            if not (float("-inf") < score < float("inf")):
                return False
            if score < 0.0 or score > 100.0:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skills": [skill.to_dict() for skill in self._skills],
            "experience_score": self._experience_score,
            "education_score": self._education_score,
            "overall_score": self._overall_score,
            "confidence": self._confidence,
            "experience_summary": self._experience_summary,
            "education_summary": self._education_summary,
            "summary": self._summary,
        }


class Evaluation(_MappingCompatMixin):

    def __init__(
        self,
        final_score: Optional[float] = 0.0,
        skills_score: Optional[float] = 0.0,
        experience_score: Optional[float] = 0.0,
        education_score: Optional[float] = 0.0,
        ai_overall_score: Optional[float] = 0.0,
        confidence: str = "",
        status: str = "",
        fast_track: bool = False,
        missing_must_haves: Optional[List[str]] = None,
        stale_skills: Optional[List[str]] = None,
        skill_details: Optional[Iterable[Union[SkillEvidence, Mapping[str, Any]]]] = None,
        experience_summary: str = "",
        education_summary: str = "",
        summary: str = "",
        notes: Optional[List[str]] = None,
    ) -> None:
        self.final_score = float(final_score) if final_score is not None else None
        self.skills_score = float(skills_score) if skills_score is not None else None
        self.experience_score = (
            float(experience_score) if experience_score is not None else None
        )
        self.education_score = (
            float(education_score) if education_score is not None else None
        )
        self.ai_overall_score = (
            float(ai_overall_score) if ai_overall_score is not None else None
        )
        self.confidence = str(confidence)
        self.status = str(status)
        self.fast_track = bool(fast_track)
        self.missing_must_haves: List[str] = list(missing_must_haves or [])
        self.stale_skills: List[str] = list(stale_skills or [])
        self.skill_details: List[SkillEvidence] = [
            SkillEvidence.create_for_category(
                name=s.name if isinstance(s, SkillEvidence) else s.get("name", ""),
                category=(
                    s.category if isinstance(s, SkillEvidence) else s.get("category", "")
                ),
                present=(
                    s.present
                    if isinstance(s, SkillEvidence)
                    else bool(s.get("present", False))
                ),
                last_used_year=(
                    s.last_used_year
                    if isinstance(s, SkillEvidence)
                    else s.get("last_used_year")
                ),
                evidence=(
                    s.evidence if isinstance(s, SkillEvidence) else s.get("evidence", "")
                ),
            )
            for s in (skill_details or [])
        ]
        self.experience_summary = str(experience_summary)
        self.education_summary = str(education_summary)
        self.summary = str(summary)
        self.notes: List[str] = list(notes or [])

    def is_scored(self) -> bool:
        return self.status != "RE_ENTRY" and self.final_score is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_score": 0.0 if self.final_score is None else self.final_score,
            "skills_score": 0.0 if self.skills_score is None else self.skills_score,
            "experience_score": (
                0.0 if self.experience_score is None else self.experience_score
            ),
            "education_score": (
                0.0 if self.education_score is None else self.education_score
            ),
            "ai_overall_score": (
                0.0 if self.ai_overall_score is None else self.ai_overall_score
            ),
            "confidence": self.confidence,
            "status": self.status,
            "fast_track": self.fast_track,
            "missing_must_haves": list(self.missing_must_haves),
            "stale_skills": list(self.stale_skills),
            "skill_details": [s.to_dict() for s in self.skill_details],
            "experience_summary": self.experience_summary,
            "education_summary": self.education_summary,
            "summary": self.summary,
            "notes": list(self.notes),
        }


class ScoredEvaluation(Evaluation):

    def is_scored(self) -> bool:
        return True


class ReEntryEvaluation(Evaluation):

    def __init__(self, note: str = "AI output missing/invalid; resume marked for re-entry") -> None:
        super().__init__(
            final_score=0.0,
            skills_score=0.0,
            experience_score=0.0,
            education_score=0.0,
            ai_overall_score=0.0,
            confidence="",
            status="RE_ENTRY",
            fast_track=False,
            missing_must_haves=[],
            stale_skills=[],
            skill_details=[],
            experience_summary="",
            education_summary="",
            summary="",
            notes=[note] if note else [],
        )

    def is_scored(self) -> bool:
        return False


class RankingRow(_MappingCompatMixin):

    def __init__(self, file_name: str, evaluation: Evaluation) -> None:
        self.file_name = str(file_name)
        self.evaluation = (
            evaluation
            if isinstance(evaluation, Evaluation)
            else Evaluation(**evaluation)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "evaluation": self.evaluation.to_dict(),
        }


class Resume(_MappingCompatMixin):

    def __init__(
        self,
        resume_id: str,
        file_name: str,
        file_path: str = "",
        anonymized_text: str = "",
    ) -> None:
        self.id = str(resume_id)
        self.file_name = str(file_name)
        self.file_path = str(file_path)
        self._anonymized_text = str(anonymized_text)

    @property
    def anonymized_text(self) -> str:
        return self._anonymized_text

    def has_readable_text(self) -> bool:
        return bool(self._anonymized_text.strip())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_path": self.file_path,
        }


class ScreeningRecord(_MappingCompatMixin):

    def __init__(
        self,
        resume_id: str,
        file_name: str,
        screening_result: Optional[Any] = None,
        status: str = "success",
        retryable: bool = False,
        error: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        self.resume_id = str(resume_id)
        self.file_name = str(file_name)
        self.status = str(status)
        self.retryable = bool(retryable)
        self.screening_result = screening_result
        self.error = error
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def can_retry(self) -> bool:
        return self.status == "error" and self.retryable

    def to_dict(self) -> Dict[str, Any]:
        screening_payload = (
            self.screening_result.to_dict()
            if isinstance(self.screening_result, AIResult)
            else self.screening_result
        )
        return {
            "resume_id": self.resume_id,
            "file_name": self.file_name,
            "status": self.status,
            "retryable": self.retryable,
            "screening_result": screening_payload,
            "error": self.error,
        }


class ScreeningBatch:

    def __init__(
        self,
        job: Job,
        preferences: ScreeningPreferences,
        resumes: Optional[Mapping[str, Resume]] = None,
    ) -> None:
        self._job = Job.from_any(job)
        self._preferences = ScreeningPreferences.from_any(preferences)
        self._resumes: Dict[str, Resume] = dict(resumes or {})
        self._records: Dict[str, ScreeningRecord] = {}
        self._evaluations: Dict[str, Evaluation] = {}

    @property
    def job(self) -> Job:
        return self._job

    @property
    def preferences(self) -> ScreeningPreferences:
        return self._preferences

    @property
    def resumes(self) -> Dict[str, Resume]:
        return self._resumes

    @property
    def records(self) -> Dict[str, ScreeningRecord]:
        return self._records

    @property
    def evaluations(self) -> Dict[str, Evaluation]:
        return self._evaluations

    def failed_ids(self) -> List[str]:
        return [
            rid
            for rid, rec in self._records.items()
            if rec.status == "error" or rec.screening_result is None
        ]

    def retryable_ids(self) -> List[str]:
        return [rid for rid, rec in self._records.items() if rec.can_retry()]

    def success_count(self) -> int:
        return sum(
            1
            for rec in self._records.values()
            if rec.status == "success" and rec.screening_result is not None
        )

    def replace_record(self, record: ScreeningRecord) -> None:
        self._records[record.resume_id] = record


class ScoringRuleStep(ABC):

    def __init__(self, rules: ScoringRules) -> None:
        self._rules = rules

    @property
    def rules(self) -> ScoringRules:
        return self._rules

    @staticmethod
    def _clamp_score(score: float) -> float:
        if score > 100.0:
            return 100.0
        if score < 0.0:
            return 0.0
        return score

    @staticmethod
    def _add_note(evaluation: Evaluation, note: str) -> None:
        if note:
            evaluation.notes.append(note)

    @abstractmethod
    def apply(self, context: Dict[str, Any], evaluation: Evaluation) -> None:
        pass


class MustHaveAdjustmentStep(ScoringRuleStep):

    def apply(self, context: Dict[str, Any], evaluation: Evaluation) -> None:
        has_must_haves = context["has_must_haves"]
        missing = context["missing"]
        unsupported_must_have = context["unsupported_must_have"]
        final = context["final"]

        if has_must_haves and len(missing) == 0 and not unsupported_must_have:
            bonus = (
                int(self._rules.must_have_bonus)
                if self._rules.must_have_bonus.is_integer()
                else self._rules.must_have_bonus
            )
            final += self._rules.must_have_bonus
            self._add_note(evaluation, f"Must-have bonus +{bonus}")
        elif len(missing) > 0:
            if final > self._rules.must_have_missing_cap:
                final = self._rules.must_have_missing_cap
            self._add_note(
                evaluation,
                f"Missing must-haves: {', '.join(missing)}; score capped",
            )

        context["final"] = final


class RecencyAuditStep(ScoringRuleStep):

    def apply(self, context: Dict[str, Any], evaluation: Evaluation) -> None:
        stale = context["stale"]
        unknown_dates = context["unknown_dates"]

        if stale:
            self._add_note(
                evaluation,
                f"Recency reduction applied: {', '.join(stale)}",
            )

        if unknown_dates:
            self._add_note(
                evaluation,
                "Some skill dates unknown; no recency penalty applied",
            )

        clamped = self._clamp_score(context["final"])
        context["final"] = round(clamped, 1)
        evaluation.final_score = context["final"]


class DisagreementAuditStep(ScoringRuleStep):

    def apply(self, context: Dict[str, Any], evaluation: Evaluation) -> None:
        ai_overall = context["ai_overall_score"]
        computed = context["computed"]
        if abs(ai_overall - computed) >= self._rules.ai_disagree_gap:
            self._add_note(
                evaluation,
                f"AI overall {ai_overall:.0f} differs from "
                f"computed {computed:.0f}; recommend human review",
            )


class QualificationDecisionStep(ScoringRuleStep):

    def apply(self, context: Dict[str, Any], evaluation: Evaluation) -> None:
        final = context["final"]
        missing = context["missing"]
        unsupported_must_have = context["unsupported_must_have"]
        skills_score = context["skills_score"]
        experience_score = context["experience_score"]
        education_score = context["education_score"]
        confidence = context["confidence"]

        if (
            final >= self._rules.fast_track_score
            and len(missing) == 0
            and not unsupported_must_have
            and skills_score >= self._rules.fast_track_min_criterion
            and experience_score >= self._rules.fast_track_min_criterion
            and education_score >= self._rules.fast_track_min_criterion
            and confidence != "low"
        ):
            evaluation.fast_track = True

        if final >= self._rules.min_score:
            evaluation.status = "SHORTLIST"
        else:
            evaluation.status = "SECONDARY_REVIEW"

        if evaluation.fast_track:
            self._add_note(evaluation, "Fast-track tag")

        if confidence == "low":
            self._add_note(
                evaluation,
                "Low AI confidence: recommend human review",
            )


class ScoringEngine(CandidateEvaluator):

    def __init__(self, rules: Optional[ScoringRules] = None) -> None:
        self._rules = rules or ScoringRules()
        self.__rule_steps: List[ScoringRuleStep] = self.__build_rule_steps(self._rules)

    @property
    def rules(self) -> ScoringRules:
        return self._rules

    @staticmethod
    def __build_rule_steps(rules: ScoringRules) -> List[ScoringRuleStep]:
        return [
            MustHaveAdjustmentStep(rules),
            RecencyAuditStep(rules),
            DisagreementAuditStep(rules),
            QualificationDecisionStep(rules),
        ]

    def _normalize_ai_fields(self, raw: Any) -> Optional[AIResult]:
        if isinstance(raw, AIResult):
            return raw if raw.is_usable() else None

        if not isinstance(raw, Mapping):
            return None

        for key in REQUIRED_KEYS:
            if key not in raw:
                return None

        if not isinstance(raw["skills"], list) or len(raw["skills"]) == 0:
            return None

        scores: Dict[str, float] = {}
        for field in ("experience_score", "education_score", "overall_score"):
            try:
                score = float(raw[field])
            except (TypeError, ValueError, OverflowError):
                return None

            if not (float("-inf") < score < float("inf")):
                return None

            if score < 0.0:
                score = 0.0
            elif score > 100.0:
                score = 100.0

            scores[field] = score

        cleaned_skills: List[SkillEvidence] = []
        current_year = date.today().year

        for skill in raw["skills"]:
            if isinstance(skill, SkillEvidence):
                skill_dict = skill.to_dict()
            elif isinstance(skill, Mapping):
                skill_dict = skill
            else:
                continue

            name = str(skill_dict.get("name", "")).strip()
            category = str(skill_dict.get("category", "")).strip().lower()
            present = str(skill_dict.get("present")).lower() == "true"

            last_used_year: Optional[int] = None
            if present:
                try:
                    year = int(skill_dict.get("last_used_year"))
                    if 1950 <= year <= current_year:
                        last_used_year = year
                except (TypeError, ValueError, OverflowError):
                    last_used_year = None

            evidence = skill_dict.get("evidence", "")
            if evidence is None:
                evidence = ""
            if not isinstance(evidence, str):
                return None

            cleaned_skills.append(
                SkillEvidence.create_for_category(
                    name=name,
                    category=category,
                    present=present,
                    last_used_year=last_used_year,
                    evidence=evidence.strip(),
                )
            )

        if len(cleaned_skills) == 0:
            return None

        confidence = str(raw["confidence"]).strip().lower()
        if confidence not in VALID_CONFIDENCE:
            confidence = "low"

        return AIResult(
            skills=cleaned_skills,
            experience_score=scores["experience_score"],
            education_score=scores["education_score"],
            overall_score=scores["overall_score"],
            confidence=confidence,
            experience_summary=str(raw.get("experience_summary", "")).strip(),
            education_summary=str(raw.get("education_summary", "")).strip(),
            summary=str(raw.get("summary", "")).strip(),
        )

    def _match_job_skills(
        self,
        ai_result: AIResult,
        job: Job,
        notes: Optional[List[str]] = None,
    ) -> List[SkillEvidence]:
        matched_skills: List[SkillEvidence] = []
        target_notes = notes if notes is not None else []

        category_sources = (
            ("must_have", job.required_skills),
            ("preferred", job.preferred),
        )

        for category, names in category_sources:
            for name in names:
                if name == "":
                    continue

                found: Optional[SkillEvidence] = None
                for ai_skill in ai_result.skills:
                    if ai_skill.name.lower() == name.strip().lower():
                        found = ai_skill

                if found is not None:
                    job_skill = SkillEvidence.create_for_category(
                        name=name,
                        category=category,
                        present=found.present,
                        last_used_year=found.last_used_year,
                        evidence=found.evidence,
                    )
                    if found.category != "" and found.category != category:
                        target_notes.append(
                            f"AI labelled '{name}' as {found.category}; "
                            f"job description says {category}"
                        )
                else:
                    job_skill = SkillEvidence.create_for_category(
                        name=name,
                        category=category,
                        present=False,
                        last_used_year=None,
                        evidence="",
                    )
                    target_notes.append(
                        f"AI did not report '{name}'; treated as not present"
                    )

                matched_skills.append(job_skill)

        return matched_skills

    def _score_skills(
        self,
        skills: List[SkillEvidence],
        active_rules: Optional[ScoringRules] = None,
        notes: Optional[List[str]] = None,
    ) -> float:
        rules = active_rules or self._rules
        target_notes = notes if notes is not None else []
        total = 0.0
        earned = 0.0
        today_year = date.today().year

        for skill in skills:
            weight = skill.get_weight(rules)
            total += weight

            if skill.present:
                if not skill.has_evidence():
                    target_notes.append(
                        f"{skill.name}: claimed by AI without supporting evidence; "
                        "no skill points awarded. Review the resume."
                    )
                    continue
                earned += skill.calculate_earned_points(today_year, rules)

        if total > 0.0:
            return 100.0 * earned / total
        return 0.0

    def _apply_rules(
        self,
        scores: Dict[str, Any],
        skills: List[SkillEvidence],
        active_rules: Optional[ScoringRules] = None,
        initial_notes: Optional[List[str]] = None,
    ) -> Evaluation:
        rules = active_rules or self._rules
        notes = list(initial_notes or [])
        today_year = date.today().year

        missing: List[str] = []
        stale: List[str] = []
        has_must_haves = False
        unsupported_must_have = False
        unknown_dates = False

        for skill in skills:
            if skill.is_mandatory():
                has_must_haves = True
                if not skill.present:
                    missing.append(skill.name)

            if skill.present:
                if not skill.has_evidence():
                    if skill.is_mandatory():
                        unsupported_must_have = True
                    continue
                if skill.last_used_year is None:
                    unknown_dates = True
                elif skill.is_stale(today_year, rules.recency_years):
                    stale.append(skill.name)

        skills_score = float(scores["skills_score"])
        experience_score = float(scores["experience_score"])
        education_score = float(scores["education_score"])
        ai_overall_score = float(scores["ai_overall_score"])
        confidence = str(scores.get("confidence", "low"))

        computed = (
            skills_score * rules.skills_weight
            + experience_score * rules.experience_weight
            + education_score * rules.education_weight
        )

        evaluation = ScoredEvaluation(
            final_score=round(computed, 1),
            skills_score=round(skills_score, 1),
            experience_score=experience_score,
            education_score=education_score,
            ai_overall_score=ai_overall_score,
            confidence=confidence,
            status="SECONDARY_REVIEW",
            fast_track=False,
            missing_must_haves=missing,
            stale_skills=stale,
            skill_details=skills,
            experience_summary=str(scores.get("experience_summary", "")),
            education_summary=str(scores.get("education_summary", "")),
            summary=str(scores.get("summary", "")),
            notes=notes,
        )

        context: Dict[str, Any] = {
            "computed": computed,
            "final": computed,
            "skills_score": skills_score,
            "experience_score": experience_score,
            "education_score": education_score,
            "ai_overall_score": ai_overall_score,
            "confidence": confidence,
            "missing": missing,
            "stale": stale,
            "has_must_haves": has_must_haves,
            "unsupported_must_have": unsupported_must_have,
            "unknown_dates": unknown_dates,
        }

        rule_steps = (
            self.__rule_steps
            if rules is self._rules
            else self.__build_rule_steps(rules)
        )
        for step in rule_steps:
            step.apply(context, evaluation)

        return evaluation

    def evaluate(
        self,
        ai_result: Any,
        job: Union[Job, Mapping[str, Any]],
        preferences: Optional[Union[ScreeningPreferences, Mapping[str, Any]]] = None,
    ) -> Evaluation:
        active_rules = self._rules.with_preferences(preferences)
        normalized_ai = self._normalize_ai_fields(ai_result)

        if normalized_ai is None:
            return ReEntryEvaluation()

        job_obj = Job.from_any(job)
        notes: List[str] = []
        matched_skills = self._match_job_skills(normalized_ai, job_obj, notes=notes)
        skills_score = self._score_skills(
            matched_skills, active_rules=active_rules, notes=notes
        )

        scores_payload = {
            "skills_score": skills_score,
            "experience_score": normalized_ai.experience_score,
            "education_score": normalized_ai.education_score,
            "ai_overall_score": normalized_ai.overall_score,
            "confidence": normalized_ai.confidence,
            "experience_summary": normalized_ai.experience_summary,
            "education_summary": normalized_ai.education_summary,
            "summary": normalized_ai.summary,
        }

        return self._apply_rules(
            scores=scores_payload,
            skills=matched_skills,
            active_rules=active_rules,
            initial_notes=notes,
        )

    def evaluate_records(
        self,
        records: Mapping[str, Any],
        job: Union[Job, Mapping[str, Any]],
        preferences: Optional[Union[ScreeningPreferences, Mapping[str, Any]]] = None,
    ) -> Dict[str, Evaluation]:
        evaluations: Dict[str, Evaluation] = {}
        for resume_id, record in records.items():
            screening_result = (
                record.screening_result
                if isinstance(record, ScreeningRecord)
                else record.get("screening_result")
            )
            if screening_result is None:
                continue
            evaluations[resume_id] = self.evaluate(
                screening_result, job, preferences
            )
        return evaluations


class DebugResultStore(ResultRepository):

    def __init__(self, path: str = "data/resume_results.json") -> None:
        self._path = str(path)

    @property
    def path(self) -> str:
        return self._path

    def _validate_shape(self, data: Any, source_path: str) -> None:
        if not isinstance(data, dict):
            raise ValueError(f"{source_path} must contain a dictionary of records")

        for resume_id, record in data.items():
            if (
                not isinstance(record, dict)
                or "file_name" not in record
                or "screening_result" not in record
            ):
                raise ValueError(
                    f"Record '{resume_id}' in {source_path} is malformed"
                )

    def load_raw(self, path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        target_path = path if path is not None else self._path
        try:
            with open(target_path, "r", encoding="utf-8") as file:
                results = json.load(file)
        except FileNotFoundError:
            raise ValueError(f"Results file not found: {target_path}")
        except OSError as exc:
            raise ValueError(f"Could not open {target_path}: {exc}")
        except ValueError:
            raise ValueError(f"{target_path} is not valid UTF-8 JSON")

        self._validate_shape(results, target_path)
        return results

    def load(self, path: Optional[str] = None) -> Dict[str, ScreeningRecord]:
        raw_results = self.load_raw(path)
        records: Dict[str, ScreeningRecord] = {}
        for resume_id, raw_record in raw_results.items():
            records[resume_id] = ScreeningRecord(
                resume_id=resume_id,
                file_name=raw_record["file_name"],
                screening_result=raw_record["screening_result"],
                status=raw_record.get(
                    "status",
                    "success"
                    if raw_record.get("screening_result") is not None
                    else "error",
                ),
                retryable=bool(raw_record.get("retryable", False)),
                error=raw_record.get("error"),
            )
        return records

    def save(
        self,
        records: Mapping[str, Any],
        path: Optional[str] = None,
    ) -> None:
        target_path = path if path is not None else self._path
        serializable: Dict[str, Any] = {}
        for resume_id, record in records.items():
            if isinstance(record, ScreeningRecord):
                serializable[resume_id] = record.to_dict()
            elif isinstance(record, Mapping):
                serializable[resume_id] = dict(record)
            else:
                raise ValueError(f"Invalid record type for '{resume_id}'")

        self._validate_shape(serializable, target_path)
        try:
            with open(target_path, "w", encoding="utf-8") as file:
                json.dump(serializable, file, indent=2)
        except OSError as exc:
            raise ValueError(f"Could not write {target_path}: {exc}")


class RankingService(CandidateRanker):

    def __init__(
        self,
        debug_store: Optional[ResultRepository] = None,
        scorer: Optional[CandidateEvaluator] = None,
    ) -> None:
        self._debug_store: ResultRepository = debug_store or DebugResultStore()
        self._scorer: CandidateEvaluator = scorer or ScoringEngine()

    @property
    def debug_store(self) -> ResultRepository:
        return self._debug_store

    @property
    def scorer(self) -> CandidateEvaluator:
        return self._scorer

    def rank(self, evaluations: Mapping[str, Union[Evaluation, Mapping[str, Any]]]) -> List[str]:
        entries: List[Tuple[bool, float, str]] = []
        for resume_id, evaluation in evaluations.items():
            if isinstance(evaluation, Evaluation):
                fast_track = bool(evaluation.fast_track)
                score = (
                    float(evaluation.final_score)
                    if evaluation.final_score is not None
                    else 0.0
                )
            else:
                fast_track = bool(evaluation["fast_track"])
                raw_score = evaluation["final_score"]
                score = float(raw_score) if raw_score is not None else 0.0

            entries.append((fast_track, score, resume_id))

        entries.sort(reverse=True)
        return [resume_id for _, _, resume_id in entries]

    def build_rows(
        self,
        records: Mapping[str, Union[ScreeningRecord, Mapping[str, Any]]],
        evaluations: Mapping[str, Union[Evaluation, Mapping[str, Any]]],
    ) -> List[RankingRow]:
        rows: List[RankingRow] = []
        for resume_id in self.rank(evaluations):
            record = records[resume_id]
            file_name = (
                record.file_name
                if isinstance(record, ScreeningRecord)
                else record["file_name"]
            )
            evaluation = evaluations[resume_id]
            eval_obj = (
                evaluation
                if isinstance(evaluation, Evaluation)
                else Evaluation(**evaluation)
            )
            rows.append(RankingRow(file_name=file_name, evaluation=eval_obj))
        return rows

    def evaluate_and_rank(
        self,
        path: str,
        job: Union[Job, Mapping[str, Any]],
        preferences: Optional[Union[ScreeningPreferences, Mapping[str, Any]]] = None,
    ) -> List[RankingRow]:
        records = self._debug_store.load(path)
        evaluations = self._scorer.evaluate_records(records, job, preferences)
        return self.build_rows(records, evaluations)


_DEFAULT_ENGINE = ScoringEngine()
_DEFAULT_STORE = DebugResultStore()
_DEFAULT_RANKER = RankingService(debug_store=_DEFAULT_STORE, scorer=_DEFAULT_ENGINE)


def extract_ai_fields(raw: Any) -> Optional[Dict[str, Any]]:
    normalized = _DEFAULT_ENGINE._normalize_ai_fields(raw)
    if normalized is None:
        return None
    return normalized.to_dict()


def evaluate_candidate(
    ai_response: Any,
    job_description: Union[Job, Mapping[str, Any]],
    preferences: Optional[Union[ScreeningPreferences, Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    evaluation = _DEFAULT_ENGINE.evaluate(ai_response, job_description, preferences)
    return evaluation.to_dict()


def rank_candidates(
    evaluations: Mapping[str, Union[Evaluation, Mapping[str, Any]]]
) -> List[str]:
    return _DEFAULT_RANKER.rank(evaluations)


def load_results(json_path: str) -> Dict[str, Dict[str, Any]]:
    return _DEFAULT_STORE.load_raw(json_path)


def evaluate_results(
    results: Mapping[str, Any],
    job_description: Union[Job, Mapping[str, Any]],
    preferences: Optional[Union[ScreeningPreferences, Mapping[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    evaluations = _DEFAULT_ENGINE.evaluate_records(
        results, job_description, preferences
    )
    return {
        resume_id: evaluation.to_dict()
        for resume_id, evaluation in evaluations.items()
    }


def build_ranking_rows(
    results: Mapping[str, Any],
    evaluations: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    rows = _DEFAULT_RANKER.build_rows(results, evaluations)
    return [row.to_dict() for row in rows]


def evaluate_and_rank(
    json_path: str,
    job_description: Union[Job, Mapping[str, Any]],
    preferences: Optional[Union[ScreeningPreferences, Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    rows = _DEFAULT_RANKER.evaluate_and_rank(
        json_path, job_description, preferences
    )
    return [row.to_dict() for row in rows]