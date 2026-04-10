from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class HealthcheckTests(unittest.TestCase):
    def test_healthcheck_returns_ok_when_dependencies_are_ready(self) -> None:
        with patch("app.api.routes.health.check_database", return_value=None), patch(
            "app.api.routes.health.check_redis",
            return_value=None,
        ):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "checks": {"postgres": "ok", "redis": "ok"}},
        )

    def test_healthcheck_returns_503_when_dependency_check_fails(self) -> None:
        with patch(
            "app.api.routes.health.check_database",
            side_effect=RuntimeError("database unavailable"),
        ), patch("app.api.routes.health.check_redis", return_value=None):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unhealthy", "checks": {"postgres": "error", "redis": "ok"}},
        )


if __name__ == "__main__":
    unittest.main()
