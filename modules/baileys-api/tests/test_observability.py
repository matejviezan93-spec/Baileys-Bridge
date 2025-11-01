from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


def test_healthz_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metrics_endpoint_exposes_key_metrics() -> None:
    client = TestClient(app)

    # Trigger at least one request so counters and histograms emit samples.
    client.get("/healthz")

    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text

    assert "baileys_api_request_total" in body
    assert "baileys_api_request_latency_seconds" in body
    assert "baileys_api_uptime_seconds" in body
