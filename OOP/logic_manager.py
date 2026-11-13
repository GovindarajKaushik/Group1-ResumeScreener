from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
import json

DEFAULT_RULES = {
    "min_score": 60, "fast_track_score": 90, "fast_track_min_criterion": 80,
    "must_have_bonus": 5, "must_have_missing_cap": 59, "recency_years": 5,
    "recency_factor": 0.5, "preferred_weight": 0.5, "ai_disagree_gap": 25,
}
DEFAULT_WEIGHTS = {"skills": 0.50, "experience": 0.30, "education": 0.20}
VALID_CONFIDENCE = ("low", "medium", "high")
VALID_RECOMMENDATIONS = ("SHORTLIST", "SECONDARY_REVIEW", "RE_ENTRY")
REQUIRED_KEYS = ["skills", "experience_score", "education_score", "overall_score", "confidence"]


class _MappingCompatMixin:
    def to_dict(self):
        raise NotImplementedError

    def __getitem__(self, key):
        return self.to_dict()[key]

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __contains__(self, key):
        return isinstance(key, str) and key in self.to_dict()

    def get(self, key, default=None):
        return self.to_dict().get(key, default)

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    def items(self):
        return self.to_dict().items()

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self):
        return len(self.to_dict())

    def __eq__(self, other):
        if isinstance(other, _MappingCompatMixin):
            return self.to_dict() == other.to_dict()
        return self.to_dict() == other if isinstance(other, dict) else False


class CandidateEvaluator(ABC):
    @abstractmethod
    def evaluate(self, ai_result, job, preferences=None):
        pass

    @abstractmethod
    def evaluate_records(self, records, job, preferences=None):
        pass


class CandidateRanker(ABC):
    @abstractmethod
    def rank(self, evaluations):
        pass

    @abstractmethod
    def build_rows(self, records, evaluations):
        pass


class ResultRepository(ABC):
    @abstractmethod
    def load(self, path=None):
        pass

    @abstractmethod
    def save(self, records, path=None):
        pass


class ScoringRules(_MappingCompatMixin):
    def __init__(self, **kw):
        self.skills_weight = float(kw.get("skills_weight", DEFAULT_WEIGHTS["skills"]))
        self.experience_weight = float(kw.get("experience_weight", DEFAULT_WEIGHTS["experience"]))
        self.education_weight = float(kw.get("education_weight", DEFAULT_WEIGHTS["education"]))
        for k, v in DEFAULT_RULES.items():
            setattr(self, k, int(kw.get(k, v)) if k == "recency_years" else float(kw.get(k, v)))

    def with_preferences(self, preferences=None):
        if preferences is None:
            return self
        min_q = preferences.get("min_qualifying_score", self.min_score) if isinstance(preferences, dict) else getattr(preferences, "min_qualifying_score", self.min_score)
        return ScoringRules(**{**self.to_dict(), "min_score": float(min_q)})

    def to_dict(self):
        int_keys = {"must_have_bonus", "must_have_missing_cap", "ai_disagree_gap", "fast_track_score", "fast_track_min_criterion"}
        out = {}
        for k in ("skills_weight", "experience_weight", "education_weight", *DEFAULT_RULES.keys()):
            v = getattr(self, k)
            out[k] = int(v) if k in int_keys and isinstance(v, float) and v.is_integer() else v
        return out


class ScreeningPreferences(_MappingCompatMixin):
    def __init__(self, min_qualifying_score=60.0):
        self._min_qualifying_score = float(min_qualifying_score)

    @property
    def min_qualifying_score(self):
        return self._min_qualifying_score

    @min_qualifying_score.setter
    def min_qualifying_score(self, value):
        self._min_qualifying_score = float(value)

    def validate(self):
        if not (0.0 <= self._min_qualifying_score <= 100.0):
            raise ValueError("min_qualifying_score must be between 0 and 100")

    @classmethod
    def from_any(cls, raw=None):
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, dict):
            return cls(raw.get("min_qualifying_score", DEFAULT_RULES["min_score"]))
        return cls(getattr(raw, "min_qualifying_score", DEFAULT_RULES["min_score"]))

    def to_dict(self):
        return {"min_qualifying_score": self._min_qualifying_score}


class Job(_MappingCompatMixin):
    def __init__(self, title="", required_skills=None, preferred=None, min_experience=0.0, education="", job_id=None, created_at=None, preferences=None):
        self.job_id = job_id
        self.title = str(title).strip()
        self.required_skills = list(required_skills or [])
        self.preferred = list(preferred or [])
        self.min_experience = float(min_experience)
        self.education = str(education).strip()
        self.created_at = created_at
        self._preferences = preferences or ScreeningPreferences()

    @property
    def preferences(self):
        return self._preferences

    def validate(self):
        if not self.required_skills and not self.preferred:
            raise ValueError("Job must specify at least one required or preferred skill")
        if self.min_experience < 0:
            raise ValueError("min_experience cannot be negative")
        self._preferences.validate()

    @classmethod
    def from_any(cls, raw):
        if isinstance(raw, cls):
            return raw
        get = raw.get if isinstance(raw, dict) else lambda k, d=None: getattr(raw, k, d)
        return cls(get("title", ""), list(get("required_skills", [])), list(get("preferred", [])), float(get("min_experience", 0.0) or 0.0), get("education", ""), get("job_id"), get("created_at"))

    def to_dict(self):
        return {"job_id": self.job_id, "title": self.title, "required_skills": list(self.required_skills), "preferred": list(self.preferred), "min_experience": self.min_experience, "education": self.education, "created_at": self.created_at}


class AbstractSkillRequirement(ABC, _MappingCompatMixin):
    def __init__(self, name, present=False, last_used_year=None, evidence=""):
        self._name = str(name).strip()
        self._present = bool(present)
        self._last_used_year = int(last_used_year) if last_used_year is not None else None
        self._evidence = "" if evidence is None else str(evidence).strip()

    @property
    def name(self):
        return self._name

    @property
    def present(self):
        return self._present

    @property
    def last_used_year(self):
        return self._last_used_year

    @property
    def evidence(self):
        return self._evidence

    def has_evidence(self):
        return bool(self._evidence)

    def is_stale(self, current_year, recency_years):
        return bool(self._present and self._last_used_year is not None and (current_year - self._last_used_year) >= recency_years)

    def recency_multiplier(self, current_year, rules):
        return rules.recency_factor if self.is_stale(current_year, rules.recency_years) else 1.0

    def calculate_earned_points(self, current_year, rules):
        return self.get_weight(rules) * self.recency_multiplier(current_year, rules) if self._present and self.has_evidence() else 0.0

    @property
    @abstractmethod
    def category(self):
        pass

    @abstractmethod
    def get_weight(self, rules):
        pass

    @abstractmethod
    def is_mandatory(self):
        pass


class SkillEvidence(AbstractSkillRequirement):
    def __init__(self, name, category="", present=False, last_used_year=None, evidence=""):
        super().__init__(name, present, last_used_year, evidence)
        self._category = str(category).strip().lower()

    @property
    def category(self):
        return self._category

    def get_weight(self, rules):
        return 1.0 if self._category == "must_have" else rules.preferred_weight

    def is_mandatory(self):
        return self._category == "must_have"

    @classmethod
    def create_for_category(cls, name, category, present=False, last_used_year=None, evidence=""):
        norm = str(category).strip().lower()
        if norm == "must_have":
            return MustHaveSkillEvidence(name, present, last_used_year, evidence)
        if norm == "preferred":
            return PreferredSkillEvidence(name, present, last_used_year, evidence)
        return cls(name, norm, present, last_used_year, evidence)

    def to_dict(self):
        return {"name": self._name, "category": self._category, "present": self._present, "last_used_year": self._last_used_year, "evidence": self._evidence}


class MustHaveSkillEvidence(SkillEvidence):
    def __init__(self, name, present=False, last_used_year=None, evidence=""):
        super().__init__(name, "must_have", present, last_used_year, evidence)

    def get_weight(self, rules):
        return 1.0

    def is_mandatory(self):
        return True


class PreferredSkillEvidence(SkillEvidence):
    def __init__(self, name, present=False, last_used_year=None, evidence=""):
        super().__init__(name, "preferred", present, last_used_year, evidence)

    def get_weight(self, rules):
        return rules.preferred_weight

    def is_mandatory(self):
        return False


class AIResult(_MappingCompatMixin):
    def __init__(self, skills, experience_score, education_score, overall_score, confidence="low", experience_summary="", education_summary="", summary=""):
        self.skills = [s if isinstance(s, SkillEvidence) else SkillEvidence.create_for_category(s.get("name", ""), s.get("category", ""), bool(s.get("present", False)), s.get("last_used_year"), s.get("evidence", "")) for s in skills]
        self.experience_score = float(experience_score)
        self.education_score = float(education_score)
        self.overall_score = float(overall_score)
        conf = str(confidence).strip().lower()
        self.confidence = conf if conf in VALID_CONFIDENCE else "low"
        self.experience_summary = str(experience_summary).strip()
        self.education_summary = str(education_summary).strip()
        self.summary = str(summary).strip()

    def is_usable(self):
        return bool(self.skills) and all(float("-inf") < s < float("inf") and 0.0 <= s <= 100.0 for s in (self.experience_score, self.education_score, self.overall_score))

    def to_dict(self):
        return {"skills": [s.to_dict() for s in self.skills], "experience_score": self.experience_score, "education_score": self.education_score, "overall_score": self.overall_score, "confidence": self.confidence, "experience_summary": self.experience_summary, "education_summary": self.education_summary, "summary": self.summary}


class Evaluation(_MappingCompatMixin):
    def __init__(self, **kw):
        for k in ("final_score", "skills_score", "experience_score", "education_score", "ai_overall_score"):
            v = kw.get(k, 0.0)
            setattr(self, k, float(v) if v is not None else None)
        self.confidence = str(kw.get("confidence", ""))
        self.status = str(kw.get("status", ""))
        self.fast_track = bool(kw.get("fast_track", False))
        self.missing_must_haves = list(kw.get("missing_must_haves") or [])
        self.stale_skills = list(kw.get("stale_skills") or [])
        self.skill_details = [SkillEvidence.create_for_category(s["name"], s["category"], bool(s["present"]), s["last_used_year"], s["evidence"]) for s in (kw.get("skill_details") or [])]
        self.experience_summary = str(kw.get("experience_summary", ""))
        self.education_summary = str(kw.get("education_summary", ""))
        self.summary = str(kw.get("summary", ""))
        self.notes = list(kw.get("notes") or [])

    def is_scored(self):
        return self.status != "RE_ENTRY" and self.final_score is not None

    def to_dict(self):
        return {
            "final_score": 0.0 if self.final_score is None else self.final_score,
            "skills_score": 0.0 if self.skills_score is None else self.skills_score,
            "experience_score": 0.0 if self.experience_score is None else self.experience_score,
            "education_score": 0.0 if self.education_score is None else self.education_score,
            "ai_overall_score": 0.0 if self.ai_overall_score is None else self.ai_overall_score,
            "confidence": self.confidence, "status": self.status, "fast_track": self.fast_track,
            "missing_must_haves": list(self.missing_must_haves), "stale_skills": list(self.stale_skills),
            "skill_details": [s.to_dict() for s in self.skill_details],
            "experience_summary": self.experience_summary, "education_summary": self.education_summary,
            "summary": self.summary, "notes": list(self.notes),
        }


class ScoredEvaluation(Evaluation):
    def is_scored(self):
        return True


class ReEntryEvaluation(Evaluation):
    def __init__(self, note="AI output missing/invalid; resume marked for re-entry"):
        super().__init__(status="RE_ENTRY", notes=[note] if note else [])

    def is_scored(self):
        return False


class RankingRow(_MappingCompatMixin):
    def __init__(self, file_name, evaluation):
        self.file_name = str(file_name)
        self.evaluation = evaluation if isinstance(evaluation, Evaluation) else Evaluation(**evaluation)

    def to_dict(self):
        return {"file_name": self.file_name, "evaluation": self.evaluation.to_dict()}


class ScreeningRecord(_MappingCompatMixin):
    def __init__(self, resume_id, file_name, screening_result=None, status="success", retryable=False, error=None, timestamp=None):
        self.resume_id = str(resume_id)
        self.file_name = str(file_name)
        self.status = str(status)
        self.retryable = bool(retryable)
        self.screening_result = screening_result
        self.error = error
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def can_retry(self):
        return self.status == "error" and self.retryable

    def to_dict(self):
        payload = self.screening_result.to_dict() if isinstance(self.screening_result, AIResult) else self.screening_result
        return {"resume_id": self.resume_id, "file_name": self.file_name, "status": self.status, "retryable": self.retryable, "screening_result": payload, "error": self.error}


class ScoringRuleStep(ABC):
    def __init__(self, rules):
        self._rules = rules

    @staticmethod
    def _clamp_score(score):
        return max(0.0, min(100.0, score))

    @staticmethod
    def _add_note(evaluation, note):
        if note:
            evaluation.notes.append(note)

    @abstractmethod
    def apply(self, context, evaluation):
        pass


class MustHaveAdjustmentStep(ScoringRuleStep):
    def apply(self, context, evaluation):
        missing, final = context["missing"], context["final"]
        if context["has_must_haves"] and not missing and not context["unsupported_must_have"]:
            bonus = int(self._rules.must_have_bonus) if self._rules.must_have_bonus.is_integer() else self._rules.must_have_bonus
            final += self._rules.must_have_bonus
            self._add_note(evaluation, f"Must-have bonus +{bonus}")
        elif missing:
            final = min(final, self._rules.must_have_missing_cap)
            self._add_note(evaluation, f"Missing must-haves: {', '.join(missing)}; score capped")
        context["final"] = final


class RecencyAuditStep(ScoringRuleStep):
    def apply(self, context, evaluation):
        if context["stale"]:
            self._add_note(evaluation, f"Recency reduction applied: {', '.join(context['stale'])}")
        if context["unknown_dates"]:
            self._add_note(evaluation, "Some skill dates unknown; no recency penalty applied")
        context["final"] = round(self._clamp_score(context["final"]), 1)
        evaluation.final_score = context["final"]


class DisagreementAuditStep(ScoringRuleStep):
    def apply(self, context, evaluation):
        ai_overall, computed = context["ai_overall_score"], context["computed"]
        if abs(ai_overall - computed) >= self._rules.ai_disagree_gap:
            self._add_note(evaluation, f"AI overall {ai_overall:.0f} differs from computed {computed:.0f}; recommend human review")


class QualificationDecisionStep(ScoringRuleStep):
    def apply(self, context, evaluation):
        final, min_c = context["final"], self._rules.fast_track_min_criterion
        if final >= self._rules.fast_track_score and not context["missing"] and not context["unsupported_must_have"] and all(context[k] >= min_c for k in ("skills_score", "experience_score", "education_score")) and context["confidence"] != "low":
            evaluation.fast_track = True
        evaluation.status = "SHORTLIST" if final >= self._rules.min_score else "SECONDARY_REVIEW"
        if evaluation.fast_track:
            self._add_note(evaluation, "Fast-track tag")
        if context["confidence"] == "low":
            self._add_note(evaluation, "Low AI confidence: recommend human review")


class ScoringEngine(CandidateEvaluator):
    def __init__(self, rules=None):
        self._rules = rules or ScoringRules()
        self.__rule_steps = self.__build_rule_steps(self._rules)

    @property
    def rules(self):
        return self._rules

    @staticmethod
    def __build_rule_steps(rules):
        return [MustHaveAdjustmentStep(rules), RecencyAuditStep(rules), DisagreementAuditStep(rules), QualificationDecisionStep(rules)]

    def _normalize_ai_fields(self, raw):
        if isinstance(raw, AIResult):
            return raw if raw.is_usable() else None
        if not isinstance(raw, dict) or any(k not in raw for k in REQUIRED_KEYS) or not isinstance(raw["skills"], list) or not raw["skills"]:
            return None

        scores = {}
        for field in ("experience_score", "education_score", "overall_score"):
            try:
                score = float(raw[field])
            except (TypeError, ValueError, OverflowError):
                return None
            if not (float("-inf") < score < float("inf")):
                return None
            scores[field] = max(0.0, min(100.0, score))

        cleaned_skills, current_year = [], date.today().year
        for skill in raw["skills"]:
            if not isinstance(skill, (dict, SkillEvidence)):
                continue
            name, category = str(skill.get("name", "")).strip(), str(skill.get("category", "")).strip().lower()
            present, last_used_year = str(skill.get("present")).lower() == "true", None
            if present:
                try:
                    year = int(skill.get("last_used_year"))
                    if 1950 <= year <= current_year:
                        last_used_year = year
                except (TypeError, ValueError, OverflowError):
                    last_used_year = None
            evidence = skill.get("evidence", "")
            if evidence is None:
                evidence = ""
            if not isinstance(evidence, str):
                return None
            cleaned_skills.append(SkillEvidence.create_for_category(name, category, present, last_used_year, evidence.strip()))

        if not cleaned_skills:
            return None
        conf = str(raw["confidence"]).strip().lower()
        return AIResult(cleaned_skills, scores["experience_score"], scores["education_score"], scores["overall_score"], conf if conf in VALID_CONFIDENCE else "low", str(raw.get("experience_summary", "")).strip(), str(raw.get("education_summary", "")).strip(), str(raw.get("summary", "")).strip())

    def _match_job_skills(self, ai_result, job, notes=None):
        matched, target_notes = [], notes if notes is not None else []
        for category, names in (("must_have", job.required_skills), ("preferred", job.preferred)):
            for name in names:
                if name == "":
                    continue
                found = None
                for ai_skill in ai_result.skills:
                    if ai_skill.name.lower() == name.strip().lower():
                        found = ai_skill
                if found is not None:
                    job_skill = SkillEvidence.create_for_category(name, category, found.present, found.last_used_year, found.evidence)
                    if found.category != "" and found.category != category:
                        target_notes.append(f"AI labelled '{name}' as {found.category}; job description says {category}")
                else:
                    job_skill = SkillEvidence.create_for_category(name, category, False, None, "")
                    target_notes.append(f"AI did not report '{name}'; treated as not present")
                matched.append(job_skill)
        return matched

    def _score_skills(self, skills, active_rules=None, notes=None):
        rules, target_notes = active_rules or self._rules, notes if notes is not None else []
        total, earned, today_year = 0.0, 0.0, date.today().year
        for skill in skills:
            total += skill.get_weight(rules)
            if skill.present:
                if not skill.has_evidence():
                    target_notes.append(f"{skill.name}: claimed by AI without supporting evidence; no skill points awarded. Review the resume.")
                    continue
                earned += skill.calculate_earned_points(today_year, rules)
        return (100.0 * earned / total) if total > 0.0 else 0.0

    def _apply_rules(self, scores, skills, active_rules=None, initial_notes=None):
        rules, notes, today_year = active_rules or self._rules, list(initial_notes or []), date.today().year
        missing, stale = [], []
        has_must_haves = unsupported_must_have = unknown_dates = False
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

        skills_score, exp_score, edu_score = float(scores["skills_score"]), float(scores["experience_score"]), float(scores["education_score"])
        ai_overall, confidence = float(scores["ai_overall_score"]), str(scores.get("confidence", "low"))
        computed = skills_score * rules.skills_weight + exp_score * rules.experience_weight + edu_score * rules.education_weight

        evaluation = ScoredEvaluation(final_score=round(computed, 1), skills_score=round(skills_score, 1), experience_score=exp_score, education_score=edu_score, ai_overall_score=ai_overall, confidence=confidence, status="SECONDARY_REVIEW", fast_track=False, missing_must_haves=missing, stale_skills=stale, skill_details=skills, experience_summary=str(scores.get("experience_summary", "")), education_summary=str(scores.get("education_summary", "")), summary=str(scores.get("summary", "")), notes=notes)
        context = {"computed": computed, "final": computed, "skills_score": skills_score, "experience_score": exp_score, "education_score": edu_score, "ai_overall_score": ai_overall, "confidence": confidence, "missing": missing, "stale": stale, "has_must_haves": has_must_haves, "unsupported_must_have": unsupported_must_have, "unknown_dates": unknown_dates}
        for step in (self.__rule_steps if rules is self._rules else self.__build_rule_steps(rules)):
            step.apply(context, evaluation)
        return evaluation

    def evaluate(self, ai_result, job, preferences=None):
        active_rules = self._rules.with_preferences(preferences)
        normalized_ai = self._normalize_ai_fields(ai_result)
        if normalized_ai is None:
            return ReEntryEvaluation()
        notes = []
        matched = self._match_job_skills(normalized_ai, Job.from_any(job), notes=notes)
        skills_score = self._score_skills(matched, active_rules=active_rules, notes=notes)
        payload = {**normalized_ai.to_dict(), "skills_score": skills_score, "ai_overall_score": normalized_ai.overall_score}
        return self._apply_rules(payload, matched, active_rules, notes)

    def evaluate_records(self, records, job, preferences=None):
        out = {}
        for rid, rec in records.items():
            res = rec.screening_result if isinstance(rec, ScreeningRecord) else rec.get("screening_result")
            if res is not None:
                out[rid] = self.evaluate(res, job, preferences)
        return out


class DebugResultStore(ResultRepository):
    def __init__(self, path="data/resume_results.json"):
        self._path = str(path)

    def _validate_shape(self, data, source_path):
        if not isinstance(data, dict):
            raise ValueError(f"{source_path} must contain a dictionary of records")
        for rid, rec in data.items():
            if not isinstance(rec, dict) or "file_name" not in rec or "screening_result" not in rec:
                raise ValueError(f"Record '{rid}' in {source_path} is malformed")

    def load_raw(self, path=None):
        target = path if path is not None else self._path
        try:
            with open(target, "r", encoding="utf-8") as file:
                results = json.load(file)
        except FileNotFoundError:
            raise ValueError(f"Results file not found: {target}")
        except OSError as exc:
            raise ValueError(f"Could not open {target}: {exc}")
        except ValueError:
            raise ValueError(f"{target} is not valid UTF-8 JSON")
        self._validate_shape(results, target)
        return results

    def load(self, path=None):
        return {rid: ScreeningRecord(rid, rec["file_name"], rec["screening_result"], rec.get("status", "success" if rec.get("screening_result") is not None else "error"), bool(rec.get("retryable", False)), rec.get("error")) for rid, rec in self.load_raw(path).items()}

    def save(self, records, path=None):
        target = path if path is not None else self._path
        serializable = {rid: rec.to_dict() if isinstance(rec, ScreeningRecord) else dict(rec) for rid, rec in records.items()}
        self._validate_shape(serializable, target)
        try:
            with open(target, "w", encoding="utf-8") as file:
                json.dump(serializable, file, indent=2)
        except OSError as exc:
            raise ValueError(f"Could not write {target}: {exc}")


class RankingService(CandidateRanker):
    def __init__(self, debug_store=None, scorer=None):
        self._debug_store = debug_store or DebugResultStore()
        self._scorer = scorer or ScoringEngine()

    def rank(self, evaluations):
        entries = [(bool(ev["fast_track"]), float(ev["final_score"] or 0.0), rid) for rid, ev in evaluations.items()]
        entries.sort(reverse=True)
        return [rid for _, _, rid in entries]

    def build_rows(self, records, evaluations):
        return [RankingRow(records[rid]["file_name"], evaluations[rid]) for rid in self.rank(evaluations)]

    def evaluate_and_rank(self, path, job, preferences=None):
        records = self._debug_store.load(path)
        return self.build_rows(records, self._scorer.evaluate_records(records, job, preferences))


_DEFAULT_ENGINE = ScoringEngine()
_DEFAULT_STORE = DebugResultStore()
_DEFAULT_RANKER = RankingService(debug_store=_DEFAULT_STORE, scorer=_DEFAULT_ENGINE)


def extract_ai_fields(raw):
    res = _DEFAULT_ENGINE._normalize_ai_fields(raw)
    return res.to_dict() if res is not None else None


def evaluate_candidate(ai_response, job_description, preferences=None):
    return _DEFAULT_ENGINE.evaluate(ai_response, job_description, preferences).to_dict()


def rank_candidates(evaluations):
    return _DEFAULT_RANKER.rank(evaluations)


def load_results(json_path):
    return _DEFAULT_STORE.load_raw(json_path)


def evaluate_results(results, job_description, preferences=None):
    return {rid: ev.to_dict() for rid, ev in _DEFAULT_ENGINE.evaluate_records(results, job_description, preferences).items()}


def build_ranking_rows(results, evaluations):
    return [row.to_dict() for row in _DEFAULT_RANKER.build_rows(results, evaluations)]


def evaluate_and_rank(json_path, job_description, preferences=None):
    return [row.to_dict() for row in _DEFAULT_RANKER.evaluate_and_rank(json_path, job_description, preferences)]