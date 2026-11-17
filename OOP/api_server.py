# OOP FastAPI server wrapping the Resume Screener backend for the React frontend

import base64
import binascii
from collections import Counter
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from OOP.data_manager import ScreeningStore, StorageError
from OOP.io_manager import CandidateReport, PdfCandidateReport, ResumeImporter
from OOP.logic_manager import Job, ScreeningPreferences
from OOP.screening_service import ScreeningService


class UploadedResumePayload(BaseModel):
    file_name: str
    content_base64: str


class ScreenBatchRequest(BaseModel):
    title: str
    required_skills: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)
    min_experience: float = 0.0
    education: str = ""
    min_qualifying_score: float = 60.0
    files: list[UploadedResumePayload] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    decision: str


# Encapsulates FastAPI setup, CORS, REST endpoints, and static React SPA serving
class APIServer:

    def __init__(
        self,
        title: str = "Resume Analyser API",
        frontend_dist_dir: str | Path | None = None,
        store: ScreeningStore | None = None,
        importer: ResumeImporter | None = None,
        screening: ScreeningService | None = None,
        report_generator: CandidateReport | None = None,
        data_directory: str | Path | None = None,
    ):
        self._title = str(title)
        default_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
        self._frontend_dist_dir = Path(frontend_dist_dir) if frontend_dist_dir is not None else default_dist
        self._store = store or ScreeningStore(data_directory=str(data_directory) if data_directory is not None else None)
        self._importer = importer or ResumeImporter()
        self._screening = screening or ScreeningService(store=self._store)
        self._report = report_generator or PdfCandidateReport()
        self._app = FastAPI(title=self._title)
        self._configure_cors()
        self._register_routes()
        self._configure_frontend_serving()

    @property
    def app(self) -> FastAPI:
        return self._app

    @property
    def has_frontend_build(self) -> bool:
        return (self._frontend_dist_dir / "index.html").is_file()

    def _configure_cors(self):
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _register_routes(self):
        routes = [
            ("/api/health", self.get_health, ["GET"]),
            ("/api/dashboard", self.get_dashboard, ["GET"]),
            ("/api/jobs", self.list_jobs, ["GET"]),
            ("/api/jobs/{job_id}", self.delete_job, ["DELETE"]),
            ("/api/jobs/{job_id}/report.pdf", self.download_job_report_pdf, ["GET"]),
            ("/api/screen", self.screen_resumes, ["POST"]),
            ("/api/candidates", self.list_candidates, ["GET"]),
            ("/api/candidates/{candidate_id}/decision", self.update_decision, ["PATCH"]),
            ("/api/candidates/{candidate_id}/report.pdf", self.download_report_pdf, ["GET"]),
            ("/api/audit", self.list_audit, ["GET"]),
        ]
        for path, handler, methods in routes:
            self._app.add_api_route(path, handler, methods=methods)

    def _configure_frontend_serving(self):
        if not self.has_frontend_build:
            return
        assets_dir = self._frontend_dist_dir / "assets"
        if assets_dir.is_dir():
            self._app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")
        self._app.add_api_route("/", self.serve_spa_index, methods=["GET"])
        self._app.add_api_route("/{full_path:path}", self.serve_spa_fallback, methods=["GET"])

    def serve_spa_index(self) -> FileResponse:
        return FileResponse(self._frontend_dist_dir / "index.html")

    def serve_spa_fallback(self, full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API endpoint not found")
        candidate = (self._frontend_dist_dir / full_path).resolve()
        dist_root = self._frontend_dist_dir.resolve()
        if candidate.is_file() and candidate.is_relative_to(dist_root):
            return FileResponse(candidate)
        return FileResponse(self._frontend_dist_dir / "index.html")

    @staticmethod
    def _run_store(action):
        try:
            return action()
        except (OSError, StorageError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    def get_health(self) -> dict:
        load_dotenv()
        has_key = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
        return {"status": "ok", "service": self._title, "mode": "Live Backend" if has_key else "Demo Mode", "ai_connected": has_key}

    def get_dashboard(self) -> dict:
        jobs = self._run_store(self._store.load_jobs)
        candidates = self._run_store(self._store.load_results)
        status_counts = self._run_store(self._store.count_by_status)
        decisions = Counter((c.recruiter_decision or "pending") for c in candidates)
        skills = Counter(s for c in candidates for s in c.skills_present)
        return {
            "total_candidates": len(candidates),
            "total_jobs": len(jobs),
            "fast_track_count": sum(1 for c in candidates if c.fast_track),
            "status_counts": status_counts,
            "decision_counts": {k: decisions.get(k, 0) for k in ("pending", "shortlisted", "rejected")},
            "top_skills": [{"skill": name, "count": cnt} for name, cnt in skills.most_common(8)],
            "recent_candidates": [c.to_dict() for c in reversed(candidates[-6:])],
        }

    def list_jobs(self) -> dict:
        jobs = self._run_store(self._store.load_jobs)
        counts = Counter(c.job_id for c in self._run_store(self._store.load_results))
        return {
            "jobs": [{**j.to_dict(), "candidate_count": counts.get(j.job_id, 0)} for j in jobs],
            "legacy_candidate_count": counts.get("", 0),
        }

    def delete_job(self, job_id: str) -> dict:
        deleted = self._run_store(lambda: self._store.delete_job(job_id))
        if deleted is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        return {"deleted_job_id": job_id, "deleted_candidates": deleted}

    def screen_resumes(self, payload: ScreenBatchRequest) -> dict:
        req = list(dict.fromkeys(s.strip() for s in payload.required_skills if s.strip()))
        req_lower = {s.lower() for s in req}
        pref = [s for s in dict.fromkeys(s.strip() for s in payload.preferred if s.strip()) if s.lower() not in req_lower]
        job = Job(title=payload.title, required_skills=req, preferred=pref, min_experience=payload.min_experience, education=payload.education)
        prefs = ScreeningPreferences(min_qualifying_score=payload.min_qualifying_score)
        try:
            job.validate()
            prefs.validate()
            self._screening.ensure_ai_client()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not payload.files:
            raise HTTPException(status_code=400, detail="Upload at least one PDF or DOCX resume.")

        rejected, resumes = [], []
        with TemporaryDirectory() as tmp_dir:
            for idx, item in enumerate(payload.files):
                name = Path(item.file_name or f"resume_{idx}").name
                target = Path(tmp_dir) / f"{idx}_{name}"
                try:
                    target.write_bytes(base64.b64decode(item.content_base64, validate=True))
                    self._importer.validate_resume_file(target)
                except (binascii.Error, ValueError) as exc:
                    rejected.append({"file_name": name, "reason": str(exc)})
                    continue
                prepared = self._importer.prepare([target])
                if not prepared:
                    rejected.append({"file_name": name, "reason": "No readable text remained after anonymization."})
                    continue
                prepared[0].file_name = name
                resumes.append(prepared[0])

        if not resumes:
            raise HTTPException(status_code=400, detail={"message": "No readable PDF/DOCX resumes remained.", "rejected_files": rejected})

        batch = self._screening.start_batch(job, prefs, resumes)
        self._screening.screen_all(batch)
        rows = self._screening.evaluate_and_rank(batch)
        outcome = self._run_store(lambda: self._screening.persist_batch(batch))
        saved = self._store.load_results(outcome["job_id"])
        return {
            "job_id": outcome["job_id"],
            "job": {**batch.job.to_dict(), "min_qualifying_score": prefs.min_qualifying_score},
            "ranked_results": [r.to_dict() for r in rows],
            "saved_candidates": [c.to_dict() for c in saved],
            "failed_records": [r.to_dict() for r in batch.failed_records()],
            "rejected_files": rejected,
            "save_failures": outcome["save_failures"],
            "debug_warning": outcome["debug_warning"],
        }

    def list_candidates(self, job_id: str | None = None, status: str | None = None, decision: str | None = None, skill: str | None = None, keyword: str | None = None) -> dict:
        candidates = self._run_store(lambda: self._store.search_candidates(status=status or None, decision=decision or None, keyword=keyword or None))
        if job_id is not None:
            candidates = [c for c in candidates if c.job_id == job_id]
        if skill:
            wanted = [s.strip().lower() for s in skill.split(",") if s.strip()]
            candidates = [c for c in candidates if all(w in {p.lower() for p in c.skills_present} for w in wanted)]
        return {"candidates": [c.to_dict() for c in candidates], "total": len(candidates)}

    def update_decision(self, candidate_id: str, payload: DecisionRequest) -> dict:
        try:
            updated = self._store.update_decision(candidate_id, payload.decision)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (OSError, StorageError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if not updated:
            raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found.")
        return self._store.get_candidate(candidate_id).to_dict()

    def download_report_pdf(self, candidate_id: str) -> Response:
        candidate = self._run_store(lambda: self._store.get_candidate(candidate_id))
        if candidate is None:
            raise HTTPException(status_code=404, detail=f"Candidate '{candidate_id}' not found.")
        return Response(content=self._report.to_pdf_bytes(candidate.to_dict()), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{candidate_id}_report.pdf"'})

    def download_job_report_pdf(self, job_id: str) -> Response:
        candidates = self._run_store(lambda: self._store.load_results(job_id))
        if not candidates:
            raise HTTPException(status_code=404, detail=f"No candidates found for job '{job_id}'.")
        jobs = {j.job_id: j for j in self._run_store(self._store.load_jobs)}
        with TemporaryDirectory() as tmp_dir:
            path = self._report.generate_batch([c.to_dict() for c in candidates], Path(tmp_dir) / f"{job_id}_batch.pdf", job=jobs.get(job_id).to_dict() if job_id in jobs else {"job_id": job_id, "title": "Saved Job"})
            return Response(content=path.read_bytes(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{job_id}_batch_report.pdf"'})

    def list_audit(self) -> dict:
        entries = self._run_store(self._store.load_audit)
        return {"entries": [{"timestamp": e.timestamp, "action": e.action, "candidate_id": e.candidate_id, "details": e.details} for e in reversed(entries)]}


server = APIServer()
app = server.app
