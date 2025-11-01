import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest

app = FastAPI(title="Baileys API")

APP_START_TIME = time.time()
METRIC_REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "baileys_api_requests_total",
    "Total number of HTTP requests",
    labelnames=("method", "endpoint", "http_status"),
    registry=METRIC_REGISTRY,
)
REQUEST_LATENCY = Histogram(
    "baileys_api_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    labelnames=("endpoint",),
    registry=METRIC_REGISTRY,
)
UPTIME_GAUGE = Gauge(
    "baileys_api_uptime_seconds",
    "Application uptime in seconds",
    registry=METRIC_REGISTRY,
)
UPTIME_GAUGE.set_function(lambda: time.time() - APP_START_TIME)


def _instrument_endpoint(endpoint: str, method: str, status_code: int, latency_seconds: float) -> None:
    REQUEST_COUNT.labels(method, endpoint, str(status_code)).inc()
    REQUEST_LATENCY.labels(endpoint).observe(latency_seconds)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency = time.perf_counter() - start_time
        _instrument_endpoint(request.url.path, request.method, 500, latency)
        raise

    latency = time.perf_counter() - start_time
    _instrument_endpoint(request.url.path, request.method, response.status_code, latency)
    return response


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    metric_output = generate_latest(METRIC_REGISTRY)
    return Response(content=metric_output, media_type=CONTENT_TYPE_LATEST)
