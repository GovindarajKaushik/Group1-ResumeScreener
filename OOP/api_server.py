# OOP FastAPI server wrapping the Resume Analyser backend for the React frontend

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


# Encapsulates FastAPI configuration, CORS middleware, API routes, and static SPA serving
class APIServer:

    def __init__(
        self,
        title: str = "Resume Analyser API",
        frontend_dist_dir: str | Path | None = None,
    ):
        self._title = str(title)
        default_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
        self._frontend_dist_dir = (
            Path(frontend_dist_dir) if frontend_dist_dir is not None else default_dist
        )
        self._app = FastAPI(title=self._title)
        self._configure_cors()
        self._register_routes()
        self._configure_frontend_serving()

    @property
    def app(self) -> FastAPI:
        # expose the underlying FastAPI instance for ASGI servers like uvicorn
        return self._app

    @property
    def has_frontend_build(self) -> bool:
        # indicate whether compiled React assets are available for single-container serving
        return (self._frontend_dist_dir / "index.html").is_file()

    def _configure_cors(self):
        # allow the local Vite dev server to call the API directly when not using the proxy
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _register_routes(self):
        # register backend JSON routes before static SPA fallbacks
        self._app.add_api_route("/api/health", self.get_health, methods=["GET"])

    def _configure_frontend_serving(self):
        # serve built React assets when running inside the single production/assessor Docker image
        if not self.has_frontend_build:
            return

        assets_dir = self._frontend_dist_dir / "assets"
        if assets_dir.is_dir():
            self._app.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="frontend-assets",
            )

        self._app.add_api_route("/", self.serve_spa_index, methods=["GET"])
        self._app.add_api_route("/{full_path:path}", self.serve_spa_fallback, methods=["GET"])

    def serve_spa_index(self) -> FileResponse:
        return FileResponse(self._frontend_dist_dir / "index.html")

    def serve_spa_fallback(self, full_path: str) -> FileResponse:
        # keep missing /api paths returning 404 JSON instead of serving index.html
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API endpoint not found")
        candidate = (self._frontend_dist_dir / full_path).resolve()
        dist_root = self._frontend_dist_dir.resolve()
        if candidate.is_file() and candidate.is_relative_to(dist_root):
            return FileResponse(candidate)
        return FileResponse(self._frontend_dist_dir / "index.html")

    def get_health(self) -> dict:
        # verify the backend is reachable and report whether an OpenAI key is configured
        has_api_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        return {
            "status": "ok",
            "service": self._title,
            "mode": "Live Backend" if has_api_key else "Demo Mode",
            "ai_connected": has_api_key,
        }


# ASGI entry point for `uvicorn OOP.api_server:app --reload`
server = APIServer()
app = server.app
