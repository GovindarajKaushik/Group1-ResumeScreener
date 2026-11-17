# Minimal offline smoke tests for OOP/api_server.py

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
