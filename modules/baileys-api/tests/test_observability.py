from pathlib import Path
import sys

from fastapi.testclient import TestClient

# Ensure the application package is importable when tests run from the repository root.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402  pylint: disable=wrong-import-position


def test_healthz_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint_exposes_prometheus_metrics() -> None:
    client = TestClient(app)
    # Trigger a request to populate the request counter metric.
    client.get("/healthz")

    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "baileys_api_requests_total" in body
    assert "baileys_api_uptime_seconds" in body
