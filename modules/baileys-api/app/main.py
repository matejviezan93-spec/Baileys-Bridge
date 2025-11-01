"""FastAPI application exposing health and Prometheus metrics endpoints."""
from __future__ import annotations

import time
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

app = FastAPI(title="Baileys API", version="0.1.0")

REQUEST_COUNT = Counter(
    "baileys_api_request_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status"),
)
REQUEST_LATENCY = Histogram(
    "baileys_api_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    labelnames=("method", "path"),
)
START_TIME = time.time()
UPTIME = Gauge(
    "baileys_api_uptime_seconds",
    "Application uptime in seconds",
)
UPTIME.set_function(lambda: time.time() - START_TIME)


@app.middleware("http")
async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Capture request metrics for every request except the metrics endpoint itself."""
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    elapsed = time.time() - start_time

    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    return response


@app.get("/healthz", response_class=JSONResponse)
async def healthz() -> dict[str, str]:
    """Return a simple OK status so orchestrators can probe the API."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus formatted metrics."""
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
