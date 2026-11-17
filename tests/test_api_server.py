# Minimal offline smoke tests for OOP/api_server.py

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import zipfile

from fastapi import HTTPException

from OOP.api_server import APIServer


class TestAPIServer(unittest.TestCase):

    def test_health_and_routes(self):
        # verify health check reads OPENROUTER_API_KEY and core API routes exist
        with TemporaryDirectory() as tmp_dir:
            server = APIServer(data_directory=tmp_dir, frontend_dist_dir=Path(tmp_dir) / "dist")
            with patch("OOP.api_server.load_dotenv", lambda: None):
                with patch.dict(os.environ, {}, clear=True):
                    self.assertFalse(server.get_health()["ai_connected"])
                with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-test"}, clear=True):
                    self.assertTrue(server.get_health()["ai_connected"])

            paths = {r.path for r in server.app.routes}
            for expected in ("/api/health", "/api/dashboard", "/api/jobs", "/api/screen", "/api/candidates", "/api/audit"):
                self.assertIn(expected, paths)

            with self.assertRaises(HTTPException) as ctx:
                server.serve_spa_fallback("api/missing")
            self.assertEqual(ctx.exception.status_code, 404)

    def test_zip_archive_extraction_and_corrupt_zip_rejection(self):
        # verify ZIP extraction forwards valid resumes and records bad archives
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            server = APIServer(data_directory=tmp_dir, frontend_dist_dir=root / "dist")
            good_zip = root / "batch.zip"
            with zipfile.ZipFile(good_zip, "w") as zf:
                zf.writestr("notes.txt", "unsupported")
            bad_zip = root / "corrupt.zip"
            bad_zip.write_bytes(b"not-a-zip")

            resumes, rejected = [], []
            server._extract_zip_resumes(good_zip, "batch.zip", root, 0, resumes, rejected)
            server._extract_zip_resumes(bad_zip, "corrupt.zip", root, 1, resumes, rejected)
            self.assertEqual(resumes, [])
            self.assertEqual([r["file_name"] for r in rejected], ["notes.txt", "corrupt.zip"])


if __name__ == "__main__":
    unittest.main()
